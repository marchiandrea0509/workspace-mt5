#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WORKSPACE = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = WORKSPACE / 'config' / 'mt5_fx_autotrade_phase1.json'
PACK_SCRIPT = WORKSPACE / 'scripts' / 'build_mt5_phase1_llm_pack.py'
DEEP_ANALYSIS_SCRIPT = WORKSPACE / 'scripts' / 'mt5_fx_deep_analysis_v2.py'
PROMPT_TEMPLATE = WORKSPACE / 'prompts' / 'phase1_llm_trade_planner.md'


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding='utf-8'))


def save_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')


def save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def latest_report(reports_dir: Path) -> Path:
    candidates = sorted(reports_dir.glob('pine_screener_*.json'), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        raise FileNotFoundError(f'No screener report found in {reports_dir}')
    return candidates[0]


def safe_float(value: Any) -> float | None:
    try:
        if value in (None, '', '—'):
            return None
        return float(value)
    except Exception:
        return None


def winner_row(report: dict[str, Any], symbol: str | None) -> tuple[dict[str, Any], int]:
    rows = report.get('top10') or report.get('top5') or []
    if not rows:
        raise ValueError('Report contains no top rows')
    if not symbol:
        raw = rows[0].get('raw') or rows[0]
        return raw, 1
    for idx, item in enumerate(rows, start=1):
        raw = item.get('raw') or item
        if str(raw.get('Symbol') or '').upper() == symbol.upper():
            return raw, idx
    raise KeyError(f'Symbol {symbol} not found in report top rows')


def direction_from_row(row: dict[str, Any]) -> str:
    setup_code = safe_float(row.get('02 Best Setup Code'))
    if setup_code is None:
        raise ValueError('02 Best Setup Code missing; cannot infer direction')
    setup = int(setup_code)
    if setup > 0:
        return 'LONG'
    if setup < 0:
        return 'SHORT'
    raise ValueError('Winner setup code is neutral (0); no trade direction available')


def run_json_command(command: list[str], cwd: Path) -> Any:
    proc = subprocess.run(command, cwd=str(cwd), capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout or '').strip() or f'Command failed: {command}')
    return json.loads(proc.stdout)


def build_prompt_text(template_text: str, pack: dict[str, Any]) -> str:
    return (
        template_text.strip()
        + '\n\n'
        + '---\n'
        + 'INPUT PACK (JSON)\n'
        + '---\n\n'
        + '```json\n'
        + json.dumps(pack, indent=2, ensure_ascii=False)
        + '\n```\n'
    )


def summarize_dashboard(row: dict[str, Any]) -> dict[str, Any]:
    interesting = [
        '02 Best Setup Code',
        '03 Best Score',
        '04 Final Long Score',
        '05 Final Short Score',
        '06 Long Continuation',
        '07 Short Continuation',
        '08 Long MeanRev',
        '09 Short MeanRev',
        '11 Trend Dir',
        '12 Macro Dir 1D',
        '13 Position State',
        '14 Breakout Dir',
        '15 Retest Dir',
        '16 ADX',
        '17 Rel Volume',
        '18 Dist Fast EMA ATR',
        '19 Sweep Dir',
        '20 Displacement Dir',
        '21 PD State',
        '24 Tactical Breakout Score',
        '25 Tactical MeanRev Score',
        '26 Fresh Struct Shift',
        '27 Verdict State',
        '28 Momentum State',
        '29 Signed Conviction',
        '30 Break Fresh State',
        '31 Retest Stage',
        '32 Short MR Struct',
        '33 Dist To Resistance %',
        '34 Zone Count',
    ]
    return {key: row.get(key) for key in interesting if key in row}


def main() -> int:
    ap = argparse.ArgumentParser(description='Prepare MT5 Phase1 LLM shadow-mode bundle.')
    ap.add_argument('--config', default=str(DEFAULT_CONFIG))
    ap.add_argument('--report-json', default='')
    ap.add_argument('--symbol', default='')
    ap.add_argument('--out-dir', default='')
    ap.add_argument('--h4-bars', type=int, default=350)
    ap.add_argument('--d1-bars', type=int, default=260)
    ap.add_argument('--horizon-days', type=int, default=5)
    ap.add_argument('--risk-budget-usd', type=float, default=100.0)
    ap.add_argument('--max-margin-usd', type=float, default=1500.0)
    args = ap.parse_args()

    cfg = load_json(Path(args.config))
    report_path = Path(args.report_json) if args.report_json else latest_report(Path(cfg['screenerReportsDir']))
    report = load_json(report_path)
    row, rank = winner_row(report, args.symbol.strip() or None)
    symbol = str(row.get('Symbol') or '').upper()
    direction = direction_from_row(row)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    out_dir = Path(args.out_dir) if args.out_dir else (WORKSPACE / 'reports' / 'mt5_autotrade_phase1' / 'llm_shadow')
    out_dir.mkdir(parents=True, exist_ok=True)

    pack_path = out_dir / f'llm_pack_{symbol}_{stamp}.json'
    script_plan_path = out_dir / f'script_plan_{symbol}_{stamp}.json'
    prompt_path = out_dir / f'planner_prompt_{symbol}_{stamp}.md'
    summary_path = out_dir / f'shadow_bundle_{symbol}_{stamp}.json'

    pack_cmd = [
        sys.executable,
        str(PACK_SCRIPT),
        '--config', str(Path(args.config)),
        '--report-json', str(report_path),
        '--symbol', symbol,
        '--out', str(pack_path),
        '--h4-bars', str(args.h4_bars),
        '--d1-bars', str(args.d1_bars),
        '--horizon-days', str(args.horizon_days),
        '--risk-budget-usd', str(args.risk_budget_usd),
        '--max-margin-usd', str(args.max_margin_usd),
    ]
    deep_cmd = [
        sys.executable,
        str(DEEP_ANALYSIS_SCRIPT),
        '--config', str(Path(args.config)),
        '--report-json', str(report_path),
        '--symbol', symbol,
        '--direction', direction,
    ]

    run_json_command(pack_cmd, WORKSPACE)
    script_plan = run_json_command(deep_cmd, WORKSPACE)
    save_json(script_plan_path, script_plan)

    pack = load_json(pack_path)
    prompt_template = PROMPT_TEMPLATE.read_text(encoding='utf-8')
    prompt_text = build_prompt_text(prompt_template, pack)
    save_text(prompt_path, prompt_text)

    summary = {
        'ok': True,
        'generated_at_utc': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        'report_path': str(report_path),
        'symbol': symbol,
        'direction': direction,
        'winner_rank': rank,
        'pack_path': str(pack_path),
        'planner_prompt_path': str(prompt_path),
        'script_plan_path': str(script_plan_path),
        'dashboard_snapshot': summarize_dashboard(row),
        'next_step': 'Run the planner prompt against the JSON pack, save the planner JSON result, then compare planner output vs script_plan before any execution.',
    }
    save_json(summary_path, summary)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
