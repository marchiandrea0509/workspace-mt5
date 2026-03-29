#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POINTER = WORKSPACE_ROOT / "mql5" / "MQL5"


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def load_pointer_root(pointer_path: Path) -> Path:
    raw = pointer_path.read_text(encoding="utf-8").strip()
    if not raw:
        raise ValueError(f"Pointer file is empty: {pointer_path}")

    if raw.startswith("/mnt/") and len(raw) > 6:
        drive = raw[5]
        remainder = raw[7:].replace("/", "\\")
        return Path(f"{drive.upper()}:\\{remainder}")

    return Path(raw)


def default_bridge_dirs(pointer_path: Path) -> tuple[Path, Path, Path]:
    mql5_root = load_pointer_root(pointer_path)
    bridge_root = mql5_root / "Files" / "gray_bridge"
    return bridge_root / "inbox", bridge_root / "outbox", bridge_root / "errors"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate_ticket_shape(ticket: dict[str, Any]) -> None:
    required = {
        "bridge_version",
        "ticket_id",
        "created_at",
        "mode",
        "symbol",
        "side",
        "order_plan",
        "entries",
        "stop_loss",
        "take_profit",
    }
    missing = sorted(required - set(ticket))
    require(not missing, f"Missing required keys: {', '.join(missing)}")

    require(ticket["bridge_version"] == "mt5.paper.v1", "bridge_version must be mt5.paper.v1")
    require(ticket["mode"] == "paper", "mode must be paper")
    require(ticket["side"] in {"buy", "sell"}, "side must be buy or sell")
    require(ticket["order_plan"] in {"market", "limit_ladder", "stop_entry"}, "order_plan invalid")
    require(isinstance(ticket["entries"], list) and len(ticket["entries"]) == 1, "Current EA scaffold supports exactly one entries[] object")

    entry = ticket["entries"][0]
    require(isinstance(entry, dict), "entries[0] must be an object")
    require(entry.get("entry_type") in {"market", "limit", "stop"}, "entries[0].entry_type invalid")
    require(float(entry.get("volume_lots", 0)) > 0, "entries[0].volume_lots must be > 0")

    if ticket["order_plan"] == "limit_ladder":
        require(entry.get("entry_type") == "limit", "limit_ladder requires entries[0].entry_type == limit")
    elif ticket["order_plan"] == "stop_entry":
        require(entry.get("entry_type") == "stop", "stop_entry requires entries[0].entry_type == stop")
    else:
        require(entry.get("entry_type") == "market", "market order_plan requires entries[0].entry_type == market")

    if entry.get("entry_type") == "market":
        require(entry.get("price") in (None, "", 0) or entry.get("price") is None, "market entries should not carry a price in v1")
    else:
        require(float(entry.get("price", 0)) > 0, "entries[0].price must be > 0 for pending orders")

    stop_loss = ticket["stop_loss"]
    take_profit = ticket["take_profit"]
    require(isinstance(stop_loss, dict) and float(stop_loss.get("price", 0)) > 0, "stop_loss.price must be > 0")
    require(isinstance(take_profit, dict) and float(take_profit.get("price", 0)) > 0, "take_profit.price must be > 0")

    trailing = ticket.get("trailing")
    if trailing is not None:
        require(isinstance(trailing, dict), "trailing must be an object if present")
        if trailing.get("enabled"):
            trigger_price = trailing.get("trigger_price", trailing.get("activation_price"))
            require(trigger_price is not None and float(trigger_price) > 0, "trailing.trigger_price (or activation_price) must be > 0 when trailing is enabled")

            distance_mode = trailing.get("distance_mode")
            distance_value = trailing.get("distance_value")
            if distance_mode is None and trailing.get("distance_price") not in (None, "", 0):
                distance_mode = "price"
                distance_value = trailing.get("distance_price")

            require(distance_mode in {"price", "percent", "atr"}, "trailing.distance_mode must be price, percent, or atr when trailing is enabled")
            require(distance_value is not None and float(distance_value) > 0, "trailing.distance_value must be > 0 when trailing is enabled")

            step_price = trailing.get("step_price")
            if step_price is not None:
                require(float(step_price) >= 0, "trailing.step_price must be >= 0")

            if distance_mode == "atr":
                atr_period = trailing.get("atr_period", 14)
                atr_timeframe = trailing.get("atr_timeframe", "H1")
                require(int(atr_period) > 0, "trailing.atr_period must be > 0 for ATR trailing")
                require(str(atr_timeframe) in {"M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1", "MN1"}, "trailing.atr_timeframe invalid for ATR trailing")



def validate_with_jsonschema_if_available(ticket: dict[str, Any], schema_path: Path) -> str:
    try:
        import jsonschema  # type: ignore
    except Exception:
        return "jsonschema not installed; used built-in validator only"

    schema = load_json(schema_path)
    jsonschema.validate(ticket, schema)
    return "validated with jsonschema"


SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


def safe_slug(text: str) -> str:
    slug = SAFE_NAME_RE.sub("-", text).strip("-._")
    return slug or "ticket"



def build_ticket_filename(ticket_id: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{stamp}__{safe_slug(ticket_id)}.json"



def write_ticket_atomically(ticket: dict[str, Any], inbox_dir: Path, filename: str) -> Path:
    inbox_dir.mkdir(parents=True, exist_ok=True)
    final_path = inbox_dir / filename
    temp_path = inbox_dir / f".{filename}.tmp"
    payload = json.dumps(ticket, indent=2, ensure_ascii=False) + "\n"
    temp_path.write_text(payload, encoding="utf-8")
    os.replace(temp_path, final_path)
    return final_path



def wait_for_result(ticket_id: str, outbox_dir: Path, timeout_seconds: float, poll_seconds: float) -> Path | None:
    deadline = time.time() + timeout_seconds
    seen: set[Path] = set()

    while time.time() < deadline:
        if outbox_dir.exists():
            matches = sorted(outbox_dir.glob(f"*{safe_slug(ticket_id)}*__result.json"))
            if not matches:
                matches = sorted(p for p in outbox_dir.glob("*.json") if ticket_id in p.name)
            for path in matches:
                if path not in seen:
                    return path
                seen.add(path)
        time.sleep(poll_seconds)

    return None



def summarize_result(path: Path) -> dict[str, Any]:
    data = load_json(path)
    return {
        "result_file": str(path),
        "status": data.get("status"),
        "message": data.get("message"),
        "symbol": data.get("symbol"),
        "side": data.get("side"),
        "retcode": data.get("retcode"),
        "retcode_text": data.get("retcode_text"),
        "mt5_order_ids": data.get("mt5_order_ids"),
        "timestamp": data.get("timestamp"),
    }



def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate and emit a Gray MT5 paper-bridge ticket into the MT5 inbox.")
    parser.add_argument("--ticket", required=True, help="Path to a bridge ticket JSON file")
    parser.add_argument("--schema", default=str(WORKSPACE_ROOT / "config" / "mt5_bridge_ticket.schema.json"), help="Path to the ticket schema JSON")
    parser.add_argument("--pointer", default=str(DEFAULT_POINTER), help="Path to the workspace MQL5 pointer file")
    parser.add_argument("--inbox", help="Override inbox directory (defaults from pointer file)")
    parser.add_argument("--outbox", help="Override outbox directory (defaults from pointer file)")
    parser.add_argument("--errors", help="Override errors directory (defaults from pointer file)")
    parser.add_argument("--filename", help="Override output filename")
    parser.add_argument("--dry-run", action="store_true", help="Validate only; do not write into inbox")
    parser.add_argument("--wait-seconds", type=float, default=0.0, help="After writing, wait this many seconds for a result file in outbox")
    parser.add_argument("--poll-seconds", type=float, default=2.0, help="Polling interval while waiting for a result")
    return parser.parse_args()



def main() -> int:
    args = parse_args()

    ticket_path = Path(args.ticket).expanduser().resolve()
    schema_path = Path(args.schema).expanduser().resolve()
    pointer_path = Path(args.pointer).expanduser().resolve()

    default_inbox, default_outbox, default_errors = default_bridge_dirs(pointer_path)
    inbox_dir = Path(args.inbox).expanduser().resolve() if args.inbox else default_inbox
    outbox_dir = Path(args.outbox).expanduser().resolve() if args.outbox else default_outbox
    errors_dir = Path(args.errors).expanduser().resolve() if args.errors else default_errors

    ticket = load_json(ticket_path)
    require(isinstance(ticket, dict), "Ticket payload must be a JSON object")
    validate_ticket_shape(ticket)
    schema_note = validate_with_jsonschema_if_available(ticket, schema_path)

    ticket_id = str(ticket["ticket_id"])
    filename = args.filename or build_ticket_filename(ticket_id)

    summary = {
        "ticket_id": ticket_id,
        "ticket_path": str(ticket_path),
        "schema_note": schema_note,
        "inbox_dir": str(inbox_dir),
        "outbox_dir": str(outbox_dir),
        "errors_dir": str(errors_dir),
        "filename": filename,
        "dry_run": bool(args.dry_run),
    }

    if args.dry_run:
        print(json.dumps(summary, indent=2))
        return 0

    final_path = write_ticket_atomically(ticket, inbox_dir, filename)
    summary["written_path"] = str(final_path)
    print(json.dumps(summary, indent=2))

    if args.wait_seconds > 0:
        result_path = wait_for_result(ticket_id, outbox_dir, args.wait_seconds, args.poll_seconds)
        if result_path is None:
            print(json.dumps({
                "result": "timeout",
                "ticket_id": ticket_id,
                "wait_seconds": args.wait_seconds,
                "outbox_dir": str(outbox_dir),
                "hint": f"No result file appeared yet. If the EA is not attached/running, the ticket may still be sitting in {inbox_dir}. Errors copy path would be under {errors_dir}."
            }, indent=2))
            return 2

        print(json.dumps(summarize_result(result_path), indent=2))

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        raise
