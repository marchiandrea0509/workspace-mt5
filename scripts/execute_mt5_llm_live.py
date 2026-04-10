#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from mt5_fx_autotrade_phase1 import DEFAULT_CONFIG, iso_z, now_utc, preflight_mt5_ticket, run_emit, save_json

WORKSPACE = Path(__file__).resolve().parents[1]
REPORTS_DIR = WORKSPACE / 'reports' / 'mt5_autotrade_phase1'


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding='utf-8-sig'))


def safe_float(value: Any) -> float | None:
    try:
        if value in (None, '', '—'):
            return None
        return float(value)
    except Exception:
        return None


def side_from_bias(bias: str) -> str:
    b = str(bias or '').upper()
    if b == 'LONG':
        return 'buy'
    if b == 'SHORT':
        return 'sell'
    raise ValueError(f'Unsupported planner bias for live execution: {bias}')


def map_order_plan(entry_method: str) -> str:
    mapping = {
        'ladder_limits': 'limit_ladder',
        'stop_entry': 'stop_entry',
        'market': 'market',
    }
    plan = mapping.get(str(entry_method or '').strip())
    if not plan:
        raise ValueError(f'Unsupported planner entry_method: {entry_method}')
    return plan


def map_entry_type(order_type: str, fallback_entry_method: str) -> str:
    ot = str(order_type or '').upper()
    if 'LIMIT' in ot:
        return 'limit'
    if 'STOP' in ot:
        return 'stop'
    if ot == 'MARKET':
        return 'market'
    if fallback_entry_method == 'ladder_limits':
        return 'limit'
    if fallback_entry_method == 'stop_entry':
        return 'stop'
    if fallback_entry_method == 'market':
        return 'market'
    raise ValueError(f'Cannot map planner order_type={order_type!r}')


def build_single_leg_ticket(*, planner: dict[str, Any], pack: dict[str, Any], baseline: dict[str, Any], leg: dict[str, Any], leg_index: int, group_id: str) -> dict[str, Any]:
    primary = planner.get('primary_plan') or {}
    risk = planner.get('risk_sizing') or {}
    tv_symbol = str(pack['market']['symbol'])
    execution_symbol = str((pack.get('mt5_symbol_profile') or {}).get('execution_symbol') or tv_symbol)
    ticket_id = f'{group_id}-leg{leg_index}'
    side = side_from_bias(primary.get('bias'))
    order_plan = map_order_plan(primary.get('entry_method'))
    entry_type = map_entry_type(str(leg.get('order_type') or ''), str(primary.get('entry_method') or ''))
    price = safe_float(leg.get('entry_price'))
    if entry_type != 'market' and price is None:
        raise ValueError(f'Planner leg {leg_index} missing entry_price')

    leg_trailing = leg.get('trailing') or {}
    ticket: dict[str, Any] = {
        'bridge_version': 'mt5.paper.v1',
        'ticket_id': ticket_id,
        'created_at': iso_z(now_utc()),
        'mode': 'paper',
        'symbol': execution_symbol,
        'side': side,
        'order_plan': 'market' if order_plan == 'market' else 'single_entry',
        'entries': [{
            'client_entry_id': f'{tv_symbol.lower()}-phase1-llm-{leg_index}',
            'entry_type': entry_type,
            'price': None if entry_type == 'market' else float(price),
            'volume_lots': float(leg['lots']),
            'comment': f'{tv_symbol} -> {execution_symbol} phase1 LLM live leg {leg_index}',
        }],
        'stop_loss': {'price': float(leg['stop_loss_price'])},
        'take_profit': {'price': float(leg['take_profit_price'])},
        'max_risk_usdt': float(risk.get('risk_budget_usd') or risk.get('total_risk_usd') or 0),
        'strategy_context': {
            'source': f'Phase1 LLM live execution for {tv_symbol}',
            'watchlist': (baseline.get('plan') or {}).get('source_context', {}).get('watchlist'),
            'timeframe': (baseline.get('plan') or {}).get('source_context', {}).get('timeframe'),
            'tv_root_symbol': tv_symbol,
            'mt5_execution_symbol': execution_symbol,
            'orderability_decision': (planner.get('orderability') or {}).get('classification'),
            'execution_template': primary.get('entry_method'),
            'setup': primary.get('execution_style'),
            'planned_total_margin_usd': risk.get('total_margin_usd_estimate'),
            'planned_total_risk_usd': risk.get('total_risk_usd'),
            'execution_model': 'independent_per_leg_orders',
            'group_id': group_id,
            'leg_index': leg_index,
        },
        'note': f'{tv_symbol} phase1 LLM live execution via {execution_symbol} (leg {leg_index}/{len((planner.get("trade_plan_ticket") or {}).get("legs") or [])}).',
    }

    if leg_trailing.get('enabled'):
        ticket['trailing'] = {
            'enabled': True,
            'trigger_price': safe_float(leg_trailing.get('trigger_price')),
            'distance_mode': leg_trailing.get('distance_mode'),
            'distance_value': safe_float(leg_trailing.get('distance_value')),
            'step_price': safe_float(leg_trailing.get('step_price')),
        }
        if ticket['trailing'].get('distance_mode') == 'atr':
            ticket['trailing']['atr_period'] = int(leg_trailing.get('atr_period') or 14)
            ticket['trailing']['atr_timeframe'] = leg_trailing.get('atr_timeframe') or 'H4'

    return ticket


def main() -> int:
    ap = argparse.ArgumentParser(description='Execute a validated MT5 Phase1 LLM planner output as live per-leg paper tickets.')
    ap.add_argument('--config', default=str(DEFAULT_CONFIG))
    ap.add_argument('--baseline-json', required=True)
    ap.add_argument('--planner-json', required=True)
    ap.add_argument('--pack-json', required=True)
    ap.add_argument('--validation-json', required=True)
    ap.add_argument('--planner-md', default='')
    ap.add_argument('--comparison-json', default='')
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    cfg = load_json(Path(args.config))
    baseline = load_json(Path(args.baseline_json))
    planner = load_json(Path(args.planner_json))
    pack = load_json(Path(args.pack_json))
    validation = load_json(Path(args.validation_json))
    if not validation.get('valid'):
        raise SystemExit('Refusing live execution from invalid LLM plan')

    orderability = str((planner.get('orderability') or {}).get('classification') or '')
    if orderability not in {'PLACEABLE_NOW', 'PLACEABLE_CONDITIONAL_ONLY'}:
        raise SystemExit(f'Planner orderability is not executable: {orderability}')

    reports_out = Path(cfg['reportsDir'])
    reports_out.mkdir(parents=True, exist_ok=True)
    stamp = now_utc().strftime('%Y%m%d_%H%M%S')
    candidate = str(baseline.get('candidate') or pack['market']['symbol'])
    planner_symbol = str((planner.get('final_verdict') or {}).get('symbol') or (planner.get('primary_plan') or {}).get('symbol') or '').upper()
    pack_symbol = str((pack.get('market') or {}).get('symbol') or '').upper()
    if planner_symbol and planner_symbol != candidate.upper():
        raise SystemExit(f'Planner symbol mismatch: baseline candidate={candidate}, planner symbol={planner_symbol}')
    if pack_symbol and pack_symbol != candidate.upper():
        raise SystemExit(f'Pack symbol mismatch: baseline candidate={candidate}, pack symbol={pack_symbol}')

    legs = list((planner.get('trade_plan_ticket') or {}).get('legs') or [])
    if not legs:
        raise SystemExit('Planner has no executable legs')

    group_id = f'p1llm-{candidate.lower()}-{now_utc().strftime("%m%d%H%M%S")}'
    emitted: list[dict[str, Any]] = []
    valid_count = 0

    for idx, leg in enumerate(legs, start=1):
        ticket = build_single_leg_ticket(planner=planner, pack=pack, baseline=baseline, leg=leg, leg_index=idx, group_id=group_id)
        ticket, preflight = preflight_mt5_ticket(ticket, cfg)
        ticket_path = reports_out / f'ticket_{candidate}_{stamp}_leg{idx}.json'
        execution: dict[str, Any]
        if preflight.get('mode') == 'applied' and preflight.get('valid_entries', 0) <= 0:
            execution = {
                'status': 'skipped',
                'message': 'This LLM leg became invalid at MT5 preflight time.',
                'preflight': preflight,
            }
        else:
            valid_count += int(preflight.get('valid_entries', 0) or 0)
            save_json(ticket_path, ticket)
            if args.dry_run:
                execution = {'status': 'dry_run', 'message': 'LLM leg ticket compiled but not emitted.', 'preflight': preflight}
            else:
                execution = run_emit(ticket_path, cfg)
                execution['preflight'] = preflight
        emitted.append({
            'leg_index': idx,
            'ticket_id': ticket['ticket_id'],
            'ticket_path': str(ticket_path),
            'order_type': leg.get('order_type'),
            'units_estimate': leg.get('units_estimate'),
            'notional_usd_estimate': leg.get('notional_usd_estimate'),
            'entry_price': leg.get('entry_price'),
            'lots': leg.get('lots'),
            'stop_loss_price': leg.get('stop_loss_price'),
            'take_profit_price': leg.get('take_profit_price'),
            'trailing': leg.get('trailing'),
            'execution': execution,
        })

    all_statuses = [str((x.get('execution') or {}).get('status') or '') for x in emitted]
    if all(s == 'accepted' for s in all_statuses if s):
        overall_status = 'accepted'
    elif any(s == 'accepted' for s in all_statuses):
        overall_status = 'partial'
    elif any(s == 'timeout' for s in all_statuses):
        overall_status = 'timeout'
    elif any(s == 'rejected' for s in all_statuses):
        overall_status = 'rejected'
    elif all(s == 'dry_run' for s in all_statuses if s):
        overall_status = 'dry_run'
    else:
        overall_status = 'skipped'

    result = {
        'result': 'trade_review',
        'session_key': baseline.get('session_key'),
        'report_path': baseline.get('report_path'),
        'report_resolution': baseline.get('report_resolution'),
        'candidate': candidate,
        'analysis_path': args.planner_md or None,
        'ticket_group_id': group_id,
        'execution': {
            'status': overall_status,
            'message': f'LLM live execution emitted {len(emitted)} independent leg tickets.',
            'valid_entries': valid_count,
            'legs': emitted,
        },
        'audit': baseline.get('audit'),
        'plan_source': 'llm',
        'plan': baseline.get('plan'),
        'planner_plan': planner,
        'validation': validation,
        'comparison_path': args.comparison_json or None,
        'pack_path': args.pack_json,
    }
    out_json = reports_out / f'mt5_phase1_llm_live_{stamp}.json'
    latest_json = reports_out / 'mt5_phase1_llm_live_latest.json'
    save_json(out_json, result)
    save_json(latest_json, result)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
