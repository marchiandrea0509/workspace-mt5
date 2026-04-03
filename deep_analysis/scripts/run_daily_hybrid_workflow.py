#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pipeline_lib import REPORT_DIR, setup_logger

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_REPORT_DIR = REPORT_DIR / "workflows"


def ensure_dirs() -> None:
    WORKFLOW_REPORT_DIR.mkdir(parents=True, exist_ok=True)


def parse_json_output(text: str) -> Any:
    text = (text or "").strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        for idx, ch in enumerate(text):
            if ch in "[{":
                try:
                    return json.loads(text[idx:])
                except json.JSONDecodeError:
                    continue
    return None


def run_step(name: str, script_name: str, args: list[str], logger) -> dict[str, Any]:
    script_path = ROOT / "scripts" / script_name
    cmd = [sys.executable, str(script_path), *args]
    logger.info("Running step %s -> %s", name, " ".join(cmd))
    started = datetime.now(timezone.utc)
    proc = subprocess.run(
        cmd,
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    ended = datetime.now(timezone.utc)
    payload = parse_json_output(proc.stdout)
    result = {
        "step": name,
        "script": str(script_path),
        "command": cmd,
        "returncode": proc.returncode,
        "started_at_utc": started.isoformat().replace("+00:00", "Z"),
        "ended_at_utc": ended.isoformat().replace("+00:00", "Z"),
        "ok": proc.returncode == 0,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
        "payload": payload,
    }
    if proc.returncode != 0:
        logger.error("Step failed: %s (code=%s)", name, proc.returncode)
        if proc.stderr.strip():
            logger.error(proc.stderr.strip())
        elif proc.stdout.strip():
            logger.error(proc.stdout.strip())
        raise SystemExit(json.dumps(result, indent=2))
    logger.info("Step complete: %s", name)
    return result


def to_markdown(summary: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# Daily Hybrid Workflow Summary")
    lines.append("")
    lines.append(f"- Generated UTC: `{summary['generated_at_utc']}`")
    lines.append(f"- Workflow mode: **{summary['mode']}**")
    if summary.get("symbol"):
        lines.append(f"- Symbol filter: **{summary['symbol']}**")
    if summary.get("timeframe"):
        lines.append(f"- Timeframe filter: **{summary['timeframe']}**")
    lines.append("")
    lines.append("## Steps")
    lines.append("")
    for item in summary["steps"]:
        status = "OK" if item["ok"] else "FAILED"
        lines.append(f"- {item['step']}: **{status}** (code={item['returncode']})")
    lines.append("")
    hybrid = summary.get("hybrid_report_paths") or {}
    if hybrid:
        lines.append("## Hybrid report outputs")
        lines.append("")
        for key, value in hybrid.items():
            lines.append(f"- {key}: `{value}`")
        lines.append("")
    plan = summary.get("plan_paths") or {}
    if plan:
        lines.append("## Planner outputs")
        lines.append("")
        for key, value in plan.items():
            lines.append(f"- {key}: `{value}`")
        lines.append("")
    lines.append("## Notes")
    lines.append("")
    lines.append("- This workflow refreshes market data, validates normalized outputs, rebuilds feature tables, rebuilds the screener, fetches the free macro/news/sentiment context overlay, and regenerates the hybrid quant report.")
    lines.append("- Optional planner mode also generates a single-market deep-dive trade plan for the selected symbol or current screener winner.")
    lines.append("- Optional visual-confirm mode reuses the TradingView screenshot packet flow, but stays off unless explicitly requested.")
    lines.append("- Use this as the standard repeatable daily run so the learning artifacts stay structurally consistent over time.")
    lines.append("")
    return "\n".join(lines)


def write_outputs(summary: dict[str, Any], markdown: str) -> dict[str, str]:
    ensure_dirs()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    suffix = f"_{summary['symbol'].upper()}" if summary.get("symbol") else ""
    json_path = WORKFLOW_REPORT_DIR / f"daily_hybrid_workflow{suffix}_{stamp}.json"
    md_path = WORKFLOW_REPORT_DIR / f"daily_hybrid_workflow{suffix}_{stamp}.md"
    latest_json = WORKFLOW_REPORT_DIR / f"daily_hybrid_workflow{suffix}_latest.json"
    latest_md = WORKFLOW_REPORT_DIR / f"daily_hybrid_workflow{suffix}_latest.md"

    payload = json.dumps(summary, indent=2)
    for path in [json_path, latest_json]:
        path.write_text(payload, encoding="utf-8")
    for path in [md_path, latest_md]:
        path.write_text(markdown, encoding="utf-8")
    return {
        "json": str(json_path),
        "markdown": str(md_path),
        "latest_json": str(latest_json),
        "latest_markdown": str(latest_md),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the full daily hybrid quant workflow in one command.")
    parser.add_argument("--mode", choices=["incremental", "full"], default="incremental", help="Data refresh mode")
    parser.add_argument("--symbol", help="Optional internal symbol filter, e.g. PAXG")
    parser.add_argument("--timeframe", help="Optional timeframe filter, e.g. 1h or 1d")
    parser.add_argument("--source", help="Optional preferred source override, e.g. bybit or pionex")
    parser.add_argument("--max-pages", type=int, help="Optional page cap for update/backfill step")
    parser.add_argument("--top", type=int, default=5, help="Top N for the hybrid report lists")
    parser.add_argument("--plan", action="store_true", help="Also generate a single-market deep-dive trade plan at the end of the workflow")
    parser.add_argument("--plan-winner", default="top_best", choices=["top_best", "best", "winner", "top_long", "long", "top_short", "short"], help="Winner selector when --plan is used without --symbol")
    parser.add_argument("--free-margin", type=float, help="Required for --plan: available free margin in USDT")
    parser.add_argument("--equity", type=float, help="Optional equity in USDT for --plan")
    parser.add_argument("--risk-budget", type=float, help="Optional absolute risk budget in USDT for --plan")
    parser.add_argument("--brb-percent", type=float, help="Optional risk budget as percent of equity for --plan")
    parser.add_argument("--direction-bias", default="AUTO", choices=["AUTO", "LONG", "SHORT"], help="Optional planner direction override")
    parser.add_argument("--style", default="AUTO", choices=["AUTO", "DIP_LADDER", "BREAKOUT", "SELL_RALLY", "BREAKDOWN"], help="Optional planner style override")
    parser.add_argument("--horizon-days", type=int, default=10, help="Planner horizon in trading days")
    parser.add_argument("--max-ladder-levels", type=int, default=3, help="Planner ladder depth (1-3)")
    parser.add_argument("--visual-confirm", action="store_true", help="Opt-in only: capture TradingView screenshots for visual confirmation as part of the planner step")
    parser.add_argument("--tv-symbol", help="Optional TradingView symbol override for visual confirmation")
    parser.add_argument("--visual-preset", default="deep", choices=["standard", "deep", "ultra"], help="Capture preset for visual confirmation")
    parser.add_argument("--visual-flow-panels", action="store_true", help="Also capture flow-panel screenshots during visual confirmation")
    parser.add_argument("--visual-structure-url", help="Optional TradingView structure layout URL override")
    parser.add_argument("--visual-flow-url", help="Optional TradingView flow layout URL override")
    args = parser.parse_args()

    logger = setup_logger("run_daily_hybrid_workflow")

    if args.plan and args.free_margin is None:
        raise SystemExit("--free-margin is required when --plan is enabled")
    if args.visual_confirm and not args.plan:
        raise SystemExit("--visual-confirm requires --plan because screenshot capture is a planner-side visual confirmation step")

    shared_filter_args: list[str] = []
    if args.symbol:
        shared_filter_args.extend(["--symbol", args.symbol])
    if args.timeframe:
        shared_filter_args.extend(["--timeframe", args.timeframe])
    if args.source:
        shared_filter_args.extend(["--source", args.source])
    if args.max_pages is not None:
        shared_filter_args.extend(["--max-pages", str(args.max_pages)])

    steps: list[dict[str, Any]] = []

    if args.mode == "incremental":
        steps.append(run_step("incremental_update", "incremental_update.py", shared_filter_args, logger))
    else:
        steps.append(run_step("full_backfill", "full_backfill.py", shared_filter_args, logger))

    validate_args: list[str] = []
    if args.symbol:
        validate_args.extend(["--symbol", args.symbol])
    if args.timeframe:
        validate_args.extend(["--timeframe", args.timeframe])
    steps.append(run_step("validate_data", "validate_data.py", validate_args, logger))

    feature_args: list[str] = []
    if args.symbol:
        feature_args.extend(["--symbol", args.symbol])
    if args.timeframe:
        feature_args.extend(["--timeframe", args.timeframe])
    steps.append(run_step("build_feature_tables", "build_feature_tables.py", feature_args, logger))

    screener_args: list[str] = []
    if args.symbol:
        screener_args.extend(["--symbol", args.symbol])
    steps.append(run_step("build_screener", "build_screener.py", screener_args, logger))

    context_args: list[str] = []
    if args.symbol:
        context_args.extend(["--symbol", args.symbol])
    steps.append(run_step("fetch_context_overlay", "fetch_context_overlay.py", context_args, logger))

    report_args: list[str] = ["--top", str(args.top)]
    if args.symbol:
        report_args.extend(["--symbol", args.symbol])
    hybrid_step = run_step("generate_hybrid_quant_report", "generate_hybrid_quant_report.py", report_args, logger)
    steps.append(hybrid_step)

    planner_step: dict[str, Any] | None = None
    if args.plan:
        plan_args: list[str] = ["--free-margin", str(args.free_margin)]
        if args.symbol:
            plan_args.extend(["--symbol", args.symbol])
        else:
            plan_args.extend(["--winner", args.plan_winner])
        if args.equity is not None:
            plan_args.extend(["--equity", str(args.equity)])
        if args.risk_budget is not None:
            plan_args.extend(["--risk-budget", str(args.risk_budget)])
        if args.brb_percent is not None:
            plan_args.extend(["--brb-percent", str(args.brb_percent)])
        if args.direction_bias and args.direction_bias != "AUTO":
            plan_args.extend(["--direction-bias", args.direction_bias])
        if args.style and args.style != "AUTO":
            plan_args.extend(["--style", args.style])
        if args.horizon_days != 10:
            plan_args.extend(["--horizon-days", str(args.horizon_days)])
        if args.max_ladder_levels != 3:
            plan_args.extend(["--max-ladder-levels", str(args.max_ladder_levels)])
        if args.visual_confirm:
            plan_args.append("--visual-confirm")
        if args.tv_symbol:
            plan_args.extend(["--tv-symbol", args.tv_symbol])
        if args.visual_preset != "deep":
            plan_args.extend(["--visual-preset", args.visual_preset])
        if args.visual_flow_panels:
            plan_args.append("--visual-flow-panels")
        if args.visual_structure_url:
            plan_args.extend(["--visual-structure-url", args.visual_structure_url])
        if args.visual_flow_url:
            plan_args.extend(["--visual-flow-url", args.visual_flow_url])
        planner_step = run_step("generate_trade_plan", "generate_trade_plan.py", plan_args, logger)
        steps.append(planner_step)

    generated_at_utc = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    summary = {
        "workflow_type": "DAILY_HYBRID_QUANT_WORKFLOW",
        "generated_at_utc": generated_at_utc,
        "mode": args.mode,
        "symbol": args.symbol,
        "timeframe": args.timeframe,
        "source": args.source,
        "top": args.top,
        "plan_enabled": bool(args.plan),
        "plan_winner": args.plan_winner if args.plan else None,
        "visual_confirm_enabled": bool(args.visual_confirm),
        "steps": [
            {
                "step": item["step"],
                "returncode": item["returncode"],
                "ok": item["ok"],
                "started_at_utc": item["started_at_utc"],
                "ended_at_utc": item["ended_at_utc"],
            }
            for item in steps
        ],
        "hybrid_report_paths": (hybrid_step.get("payload") or {}).get("paths", {}),
        "plan_paths": ((planner_step or {}).get("payload") or {}).get("paths", {}),
    }

    markdown = to_markdown(summary)
    workflow_paths = write_outputs(summary, markdown)
    summary["workflow_paths"] = workflow_paths
    payload = json.dumps(summary, indent=2)
    for path in [Path(workflow_paths["json"]), Path(workflow_paths["latest_json"] )]:
        path.write_text(payload, encoding="utf-8")

    logger.info("Workflow complete -> %s", workflow_paths["latest_markdown"])
    print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
