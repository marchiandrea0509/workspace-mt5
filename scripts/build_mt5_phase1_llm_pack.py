#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from market_source_lib import make_market_source

WORKSPACE = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = WORKSPACE / 'config' / 'mt5_fx_autotrade_phase1.json'


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding='utf-8'))


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


def normalize_setup_code(raw: Any) -> int | None:
    num = safe_float(raw)
    if num is None:
        return None
    return int(num)


def setup_meta(setup_code: int | None) -> dict[str, Any]:
    mapping = {
        3: ('LONG', 'BREAKOUT_LED', 'BREAKOUT'),
        2: ('LONG', 'CONTINUATION', 'DIP_LADDER'),
        1: ('LONG', 'MEAN_REVERSION', 'AUTO'),
        0: ('WAIT', 'NONE', 'AUTO'),
        -1: ('SHORT', 'MEAN_REVERSION', 'AUTO'),
        -2: ('SHORT', 'CONTINUATION', 'SELL_RALLY'),
        -3: ('SHORT', 'BREAKOUT_LED', 'BREAKDOWN'),
    }
    bias, family, execution_style = mapping.get(setup_code, ('WAIT', 'UNKNOWN', 'AUTO'))
    return {
        'setup_code': setup_code,
        'direction_bias': bias,
        'winner_family': family,
        'preferred_execution_style': execution_style,
    }


def pick_row(report: dict[str, Any], symbol: str | None) -> tuple[dict[str, Any], int]:
    rows = report.get('top10') or report.get('top5') or []
    if not rows:
        raise ValueError('Report contains no top10/top5 rows')
    if symbol is None:
        row = rows[0].get('raw') or rows[0]
        return row, 1
    for idx, item in enumerate(rows, start=1):
        raw = item.get('raw') or item
        if str(raw.get('Symbol') or '').upper() == symbol.upper():
            return raw, idx
    raise KeyError(f'Symbol {symbol} not found in screener top list')


def iso_utc_from_epoch(epoch_s: int) -> str:
    return datetime.fromtimestamp(int(epoch_s), tz=timezone.utc).isoformat().replace('+00:00', 'Z')


def main() -> int:
    ap = argparse.ArgumentParser(description='Build MT5 Phase1 LLM planner data pack from screener + MT5 market data.')
    ap.add_argument('--config', default=str(DEFAULT_CONFIG))
    ap.add_argument('--report-json', default='')
    ap.add_argument('--symbol', default='')
    ap.add_argument('--out', default='')
    ap.add_argument('--h4-bars', type=int, default=350)
    ap.add_argument('--d1-bars', type=int, default=260)
    ap.add_argument('--horizon-days', type=int, default=5)
    ap.add_argument('--risk-budget-usd', type=float, default=100.0)
    ap.add_argument('--max-margin-usd', type=float, default=1500.0)
    args = ap.parse_args()

    cfg = load_json(Path(args.config))
    reports_dir = Path(cfg['screenerReportsDir'])
    report_path = Path(args.report_json) if args.report_json else latest_report(reports_dir)
    report = load_json(report_path)
    row, rank = pick_row(report, args.symbol.strip() or None)

    tv_symbol = str(row.get('Symbol') or '').upper()
    description = str(row.get('Description') or tv_symbol)
    setup = setup_meta(normalize_setup_code(row.get('02 Best Setup Code')))

    source = make_market_source(cfg['analysisDataSource'])
    try:
        profile = source.resolve_symbol(tv_symbol)
        h4 = source.get_rates(profile.analysis_symbol, 'H4', int(args.h4_bars))
        d1 = source.get_rates(profile.analysis_symbol, 'D1', int(args.d1_bars))
        quote_to_usd = source.fx_to_usd_rate(profile.currency_profit)
        margin_to_usd = source.fx_to_usd_rate(profile.currency_margin)
    finally:
        shutdown = getattr(source, 'shutdown', None)
        if callable(shutdown):
            shutdown()

    payload = {
        'pack_version': 'mt5.phase1.llm.v1',
        'generated_at_utc': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        'report_source': {
            'path': str(report_path),
            'generated_at': report.get('generatedAt'),
            'watchlist': report.get('watchlist'),
            'indicator': report.get('indicator'),
            'timeframe': report.get('timeframe'),
            'row_count': report.get('rowCount'),
            'winner_rank': rank,
        },
        'market': {
            'symbol': tv_symbol,
            'description': description,
            'exchange': 'MT5 OANDA',
            'horizon_trading_days': int(args.horizon_days),
            'direction_bias': setup['direction_bias'],
            'winner_family': setup['winner_family'],
            'preferred_execution_style': setup['preferred_execution_style'],
        },
        'account_limits': {
            'risk_budget_usd_total_trade': float(args.risk_budget_usd),
            'max_margin_usd_total_trade': float(args.max_margin_usd),
        },
        'execution_constraints': {
            'multi_leg_allowed': True,
            'max_legs': 8,
            'execution_model': 'independent_per_leg_orders',
            'one_live_tp_per_leg': True,
            'per_leg_stop_loss_allowed': True,
            'per_leg_take_profit_allowed': True,
            'per_leg_trailing_allowed': True,
            'trailing_supported_by_ea': True,
            'allowed_entry_methods': ['market', 'ladder_limits', 'stop_entry'],
            'allowed_execution_styles': ['AUTO', 'DIP_LADDER', 'BREAKOUT', 'SELL_RALLY', 'BREAKDOWN'],
            'sizing_basis': 'size from stop distance; do not exceed total risk budget or total margin cap',
            'lot_rules_source': 'infer from MT5 symbol metadata',
        },
        'mt5_symbol_profile': {
            'root_symbol': profile.root_symbol,
            'analysis_symbol': profile.analysis_symbol,
            'execution_symbol': profile.execution_symbol,
            'path': profile.path,
            'trade_mode': profile.trade_mode,
            'trade_mode_code': profile.trade_mode_code,
            'digits': profile.digits,
            'point': profile.point,
            'volume_min': profile.volume_min,
            'volume_step': profile.volume_step,
            'volume_max': profile.volume_max,
            'contract_size': profile.contract_size,
            'currency_base': profile.currency_base,
            'currency_profit': profile.currency_profit,
            'currency_margin': profile.currency_margin,
            'quote_to_usd': quote_to_usd,
            'margin_to_usd': margin_to_usd,
            'units_per_1_lot_estimate': profile.contract_size,
            'units_note': 'For FX this is typically base units per lot. For CFDs/other products, treat lots as executable truth and units as an estimate only.',
        },
        'screener_dashboard': {
            'raw_row': row,
            'top_list_headers': report.get('headers') or [],
            'reproducible_dashboard_fields': [
                '01 Signal Dir', '02 Best Setup Code', '03 Best Score', '04 Final Long Score', '05 Final Short Score',
                '06 Long Continuation', '07 Short Continuation', '08 Long MeanRev', '09 Short MeanRev', '10 Conviction State',
                '11 Trend Dir', '12 Macro Dir 1D', '13 Position State', '14 Breakout Dir', '15 Retest Dir', '16 ADX',
                '17 Rel Volume', '18 Dist Fast EMA ATR', '19 Sweep Dir', '20 Displacement Dir', '21 PD State',
                '22 FVG State', '23 Tactical Trend Score', '24 Tactical Breakout Score', '25 Tactical MeanRev Score',
                '26 Fresh Struct Shift', '27 Verdict State', '28 Momentum State', '29 Signed Conviction', '30 Break Fresh State',
                '31 Retest Stage', '32 Short MR Struct', '33 Dist To Resistance %', '34 Zone Count', '35 EMA Trend State',
                '36 VWAP20', '37 Dist To Support %', '38 Lifecycle Long Score', '39 R1 Above', '40 R2 Above',
                '41 S1 Below', '42 S2 Below', '43 Cnt Res Above', '44 Cnt Sup Below', '45 Cnt Res All', '46 Cnt Sup All',
                '47 Lifecycle Short Score', '48 Winner Dir', '49 Winner Family Code', '50 Winner Margin', '51 Winner Base Score',
                '52 Winner Penalty', '53 Winner Tactical', '54 Winner Macro', '55 Winner Structure', '56 Winner ADX Fit',
                '57 Winner Lifecycle', '58 Winner Context Boost', '59 Winner Family Edge'
            ],
            'legend': {
                'best_setup': '+1/-1 mean reversion, +2/-2 continuation, +3/-3 breakout-led, 0 no valid setup',
                'conviction': '0 weak, 1 decent, 2 strong, 3 very strong',
                'directional_states': 'Trend Dir / Macro 1D / Breakout / Retest / Sweep Dir / Disp Dir / Fresh Struct / Momentum / Signed Conv: positive bullish, negative bearish, 0 neutral',
                'pd_state': 'positive = discount, negative = premium',
                'verdict': '+2 strong long, +1 long, 0 neutral, -1 short, -2 strong short',
                'position': 'structural context such as support/resistance touch, breakout, retest, or neutral',
                'break_fresh': 'recent breakout memory state, not breakout on current bar; +2/-2 very fresh, +1/-1 fresh, 0 none',
                'retest_stage': 'signed post-break lifecycle; +1/-1 waiting retest, +2/-2 retest touched, +3/-3 retest confirmed, +4/-4 retest failed, 0 none',
                'short_mr_struct': 'structural quality for short mean reversion; higher = better nearby resistance for short fade',
                'winner_family_code': '0 none, 1 mean reversion, 2 continuation, 3 breakout-led',
                'winner_attribution': 'Winner Dir / Margin / Base / Penalty / Tactical / Macro / Structure / ADX Fit / Lifecycle / Context Boost / Family Edge explain why the final winner side-family combination won the screener comparison',
            },
        },
        'chart_data': {
            'source_of_truth': 'MT5 exported OHLCV + MT5 symbol metadata',
            'lookback_windows': {
                'H4_bars': int(args.h4_bars),
                'D1_bars': int(args.d1_bars),
            },
            'H4': {
                'timeframe': 'H4',
                'bars': [{**bar, 'time_iso_utc': iso_utc_from_epoch(bar['time'])} for bar in h4],
            },
            'D1': {
                'timeframe': 'D1',
                'bars': [{**bar, 'time_iso_utc': iso_utc_from_epoch(bar['time'])} for bar in d1],
            },
        },
        'planner_contract': {
            'human_sections_required': [
                'screener_read',
                'market_state',
                'key_levels',
                'trade_quality',
                'primary_trade_plan',
                'orderability_decision',
                'backup_plan',
                'risk_sizing',
                'trade_plan_ticket',
                'final_verdict',
            ],
            'json_top_level_required': [
                'screener_read',
                'market_state',
                'key_levels',
                'trade_quality',
                'primary_plan',
                'orderability',
                'backup_plan',
                'risk_sizing',
                'trade_plan_ticket',
                'final_verdict',
                'validator_hints',
            ],
        },
    }

    out_path = Path(args.out) if args.out else (WORKSPACE / 'reports' / 'mt5_autotrade_phase1' / f'mt5_phase1_llm_pack_{tv_symbol}_{datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")}.json')
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps({'ok': True, 'out': str(out_path), 'symbol': tv_symbol, 'analysis_symbol': profile.analysis_symbol}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
