#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

from pipeline_lib import setup_logger
from planner_lib import build_plan, load_screener_frame, resolve_symbol, to_markdown, write_outputs
from visual_confirmation_lib import run_visual_confirmation_packet


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a single-market deep-dive trade plan from screener + feature + context artifacts.")
    parser.add_argument("--symbol", help="Internal symbol, e.g. PAXG or USARX")
    parser.add_argument("--winner", default="top_best", choices=["top_best", "best", "winner", "top_long", "long", "top_short", "short"], help="Use the current screener winner instead of an explicit symbol")
    parser.add_argument("--free-margin", required=True, type=float, help="Available free margin in USDT")
    parser.add_argument("--equity", type=float, help="Account equity in USDT")
    parser.add_argument("--risk-budget", type=float, help="Absolute risk budget in USDT")
    parser.add_argument("--brb-percent", type=float, help="Risk budget as percent of equity; stricter value wins if both are set")
    parser.add_argument("--direction-bias", default="AUTO", choices=["AUTO", "LONG", "SHORT"], help="Optional direction override")
    parser.add_argument("--style", default="AUTO", choices=["AUTO", "DIP_LADDER", "BREAKOUT", "SELL_RALLY", "BREAKDOWN"], help="Optional execution-style override")
    parser.add_argument("--horizon-days", type=int, default=10, help="Planning horizon in trading days")
    parser.add_argument("--max-ladder-levels", type=int, default=3, help="Max ladder levels (1-3)")
    parser.add_argument("--visual-confirm", action="store_true", help="Opt-in only: capture TradingView screenshots for visual confirmation using the existing packet workflow")
    parser.add_argument("--tv-symbol", help="Optional TradingView symbol override for visual confirmation, e.g. PAXGUSDT.P")
    parser.add_argument("--visual-preset", default="deep", choices=["standard", "deep", "ultra"], help="Capture preset for visual confirmation")
    parser.add_argument("--visual-flow-panels", action="store_true", help="Also capture the lower flow/indicator panels during visual confirmation")
    parser.add_argument("--visual-structure-url", help="Optional TradingView structure layout URL override")
    parser.add_argument("--visual-flow-url", help="Optional TradingView flow layout URL override")
    args = parser.parse_args()

    logger = setup_logger("generate_trade_plan")
    frame = load_screener_frame()
    symbol = resolve_symbol(frame, symbol=args.symbol, winner=args.winner if not args.symbol else None)

    report = build_plan(
        symbol=symbol,
        frame=frame,
        free_margin_usdt=float(args.free_margin),
        equity_usdt=args.equity,
        risk_budget_usdt=args.risk_budget,
        brb_percent=args.brb_percent,
        direction_bias=args.direction_bias,
        preferred_style=args.style,
        horizon_days=int(args.horizon_days),
        max_ladder_levels=int(args.max_ladder_levels),
    )

    report["visual_confirmation"] = {"requested": False}
    if args.visual_confirm:
        try:
            report["visual_confirmation"] = run_visual_confirmation_packet(
                internal_symbol=symbol,
                report=report,
                free_margin_usdt=float(args.free_margin),
                equity_usdt=args.equity,
                risk_budget_usdt=args.risk_budget,
                brb_percent=args.brb_percent,
                tv_symbol_override=args.tv_symbol,
                preset=args.visual_preset,
                flow_panels=bool(args.visual_flow_panels),
                structure_url=args.visual_structure_url,
                flow_url=args.visual_flow_url,
            )
        except BaseException as exc:
            logger.warning("Visual confirmation capture failed for %s: %s", symbol, exc)
            report["visual_confirmation"] = {
                "requested": True,
                "ok": False,
                "error": str(exc),
                "notes": [
                    "Visual confirmation is supplementary only; the structured-data plan was still generated.",
                    "Fix the TradingView session or symbol mapping and retry if chart confirmation is still needed.",
                ],
            }

    markdown = to_markdown(report)
    paths = write_outputs(report, markdown, symbol=symbol)
    logger.info("Built trade plan for %s -> %s", symbol, paths["latest_markdown"])
    print(json.dumps({"paths": paths, "report": report}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
