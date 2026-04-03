#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

from pipeline_lib import ROOT, SYMBOLS_PATH, USABLE_STATUSES

TRADINGVIEW_BASE = ROOT.parent / "tradingview"
DAILY_PACKET_SCRIPT = TRADINGVIEW_BASE / "scripts" / "daily_quant_packet.py"

STATUS_ORDER = {
    "preferred": 0,
    "active": 1,
    "active_fallback": 2,
    "fallback_only": 3,
}

STYLE_MAP = {
    "DIP_LADDER": "Dip ladder",
    "BREAKOUT": "Breakout",
    "SELL_RALLY": "Either",
    "BREAKDOWN": "Breakout",
}


def load_symbols_config() -> list[dict[str, Any]]:
    if not SYMBOLS_PATH.exists():
        return []
    payload = yaml.safe_load(SYMBOLS_PATH.read_text(encoding="utf-8")) or {}
    rows = payload.get("symbols") or []
    return [row for row in rows if isinstance(row, dict)]


def candidate_rows(internal_symbol: str) -> list[dict[str, Any]]:
    symbol_upper = str(internal_symbol).upper()
    rows = [
        row for row in load_symbols_config()
        if str(row.get("internal_symbol") or "").upper() == symbol_upper
        and str(row.get("status") or "").lower() in USABLE_STATUSES
    ]
    rows.sort(key=lambda row: (STATUS_ORDER.get(str(row.get("status") or "").lower(), 99), int(row.get("priority") or 999)))
    return rows


def to_tradingview_symbol(candidate: dict[str, Any]) -> str | None:
    source_symbol = str(candidate.get("source_symbol") or "").strip().upper()
    if not source_symbol:
        return None

    source = str(candidate.get("source") or "").strip().lower()
    market_type = str(candidate.get("market_type") or "").strip().lower()
    api_category = str(candidate.get("api_category") or "").strip().lower()

    if source_symbol.endswith("_USDT_PERP"):
        return source_symbol.replace("_USDT_PERP", "USDT.P").replace("_", "")
    if source_symbol.endswith("_PERP"):
        return source_symbol.replace("_PERP", ".P").replace("_", "")
    if source_symbol.endswith("_USDT"):
        return source_symbol.replace("_", "")
    if market_type == "perpetual" or api_category == "linear":
        return f"{source_symbol}.P"
    if source == "bybit" and source_symbol.endswith("USDT"):
        return source_symbol
    return source_symbol.replace("_", "")


def resolve_tradingview_symbol(internal_symbol: str) -> dict[str, Any]:
    candidates = candidate_rows(internal_symbol)
    if not candidates:
        raise SystemExit(f"No symbol mapping found for visual confirmation: {internal_symbol}")

    for candidate in candidates:
        tv_symbol = to_tradingview_symbol(candidate)
        if tv_symbol:
            return {
                "internal_symbol": str(internal_symbol).upper(),
                "tv_symbol": tv_symbol,
                "source": candidate.get("source"),
                "source_symbol": candidate.get("source_symbol"),
                "market_type": candidate.get("market_type"),
                "status": candidate.get("status"),
                "priority": candidate.get("priority"),
            }

    raise SystemExit(f"Unable to derive TradingView symbol for {internal_symbol}")


def parse_key_value_lines(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line or "=" not in line:
            continue
        key, value = line.split("=", 1)
        out[key.strip()] = value.strip()
    return out


def prompt_style_from_report(report: dict[str, Any]) -> str:
    decision = report.get("decision") or {}
    primary = str(decision.get("primary_entry_method") or "AUTO").upper()
    return STYLE_MAP.get(primary, "Either")


def run_visual_confirmation_packet(
    *,
    internal_symbol: str,
    report: dict[str, Any],
    free_margin_usdt: float,
    equity_usdt: float | None = None,
    risk_budget_usdt: float | None = None,
    brb_percent: float | None = None,
    tv_symbol_override: str | None = None,
    preset: str = "deep",
    flow_panels: bool = True,
    structure_url: str | None = None,
    flow_url: str | None = None,
) -> dict[str, Any]:
    if not DAILY_PACKET_SCRIPT.exists():
        raise SystemExit(f"Missing TradingView visual-confirmation script: {DAILY_PACKET_SCRIPT}")

    report_decision = report.get("decision") or {}
    mapping = resolve_tradingview_symbol(internal_symbol)
    tv_symbol = str(tv_symbol_override or mapping.get("tv_symbol"))

    cmd = [
        sys.executable,
        str(DAILY_PACKET_SCRIPT),
        "--symbol",
        tv_symbol,
        "--timezone",
        "Europe/Berlin",
        "--direction",
        str(report_decision.get("direction") or "LONG"),
        "--style",
        prompt_style_from_report(report),
        "--free-margin",
        str(free_margin_usdt),
        "--preset",
        str(preset),
    ]
    if equity_usdt is not None:
        cmd.extend(["--equity", str(equity_usdt)])
    if risk_budget_usdt is not None:
        cmd.extend(["--risk-usdt", str(risk_budget_usdt)])
    elif brb_percent is not None:
        cmd.extend(["--brb", str(brb_percent)])
    if flow_panels:
        cmd.append("--flow-panels")
    if structure_url:
        cmd.extend(["--structure-url", structure_url])
    if flow_url:
        cmd.extend(["--flow-url", flow_url])

    proc = subprocess.run(
        cmd,
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        stderr = proc.stderr.strip() or proc.stdout.strip()
        raise SystemExit(f"Visual confirmation capture failed for {internal_symbol}: {stderr}")

    parsed = parse_key_value_lines(proc.stdout)
    return {
        "requested": True,
        "mode": "TRADINGVIEW_VISUAL_CONFIRMATION",
        "internal_symbol": str(internal_symbol).upper(),
        "tv_symbol": tv_symbol,
        "mapping": mapping,
        "preset": preset,
        "flow_panels": bool(flow_panels),
        "prompt": parsed.get("PROMPT"),
        "structure_1h": parsed.get("SHOT_STRUCTURE_1H") or parsed.get("SHOT_1H"),
        "structure_1d": parsed.get("SHOT_STRUCTURE_1D") or parsed.get("SHOT_1D"),
        "flow_1h": parsed.get("SHOT_FLOW_1H"),
        "flow_1d": parsed.get("SHOT_FLOW_1D"),
        "flow_1h_panels": parsed.get("SHOT_FLOW_1H_PANELS"),
        "flow_1d_panels": parsed.get("SHOT_FLOW_1D_PANELS"),
        "log": parsed.get("LOG"),
        "notes": [
            "Visual confirmation is supplementary only; structured exchange data remains the primary analysis source.",
            "This capture path is opt-in and should only run when the user explicitly asks for chart confirmation.",
        ],
    }
