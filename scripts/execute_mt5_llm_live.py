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
    # fallback from planner entry method
    if fallback_entry_method == 'ladder_limits':
        return 'limit'
    if fallback_entry_method == 'stop_entry':
        return 'stop'
    if fallback_entry_method == 'market':
        return 'market'
    raise ValueError(f'Cannot map planner order_type={order_type!r}')


def build_ticket(planner: dict[str, Any], pack: dict[str, Any], baseline: dict[str, Any]) -> dict[str, Any]:
    primary = planner.get('primary_plan') or {}
    ticket_plan = planner.get('trade_plan_ticket') or {}
    risk = planner.get('risk_sizing') or {}
    trailing = ticket_plan.get('trailing') or {}
    legs = ticket_plan.get('legs') or []
    if not legs:
        raise ValueError('Planner ticket has no legs; refusing live execution')

    tv_symbol = str(pack['market']['symbol'])
    execution_symbol = str((pack.get('mt5_symbol_profile') or {}).get('execution_symbol') or tv_symbol)
    session_key = str(baseline.get('session_key') or '')
    stamp = now_utc().strftime('%m%d%H%M%S')
    ticket_symbol = ''.join(ch for ch in tv_symbol.lower() if ch.isalnum())[:8] or 'asset'
    ticket_id = f'p1llm-{ticket_symbol}-{stamp}'
    side = side_from_bias(primary.get('bias'))
    order_plan = map_order_plan(primary.get('entry_method'))

    entries: list[dict[str, Any]] = []
    for idx, leg in enumerate(legs, start=1):
        entry_type = map_entry_type(str(leg.get('order_type') or ''), str(primary.get('entry_method') or ''))
        price = safe_float(leg.get('entry_price'))
        if entry_type != 'market' and price is None:
            raise ValueError(f'Planner leg {idx} missing entry_price')
        entries.append({
            'client_entry_id': f'{tv_symbol.lower()}-phase1-llm-{idx}',
            'entry_type': entry_type,
            'price': None if entry_type == 'market' else float(price),
            'volume_lots': float(leg['lots']),
            'comment': f'{tv_symbol} -> {execution_symbol} phase1 LLM live entry {idx}',
        })

    ticket: dict[str, Any] = {
        'bridge_version': 'mt5.paper.v1',
        'ticket_id': ticket_id,
        'created_at': iso_z(now_utc()),
        'mode': 'paper',
        'symbol': execution_symbol,
        'side': side,
        'order_plan': order_plan,
        'entries': entries,
        'stop_loss': {'price': float(ticket_plan['shared_stop_loss_price'])},
        'take_profit': {'price': float(ticket_plan['shared_take_profit_price'])},
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
            'bridge_tp_note': 'Live LLM execution still uses one shared live TP/SL/trailing package under bridge v1 constraints.',
        },
        'note': f'{tv_symbol} phase1 LLM live execution via {execution_symbol}.',
    }

    if trailing.get('enabled'):
        ticket['trailing'] = {
            'enabled': True,
            'trigger_price': safe_float(trailing.get('trigger_price')),
            'distance_mode': trailing.get('distance_mode'),
            'distance_value': safe_float(trailing.get('distance_value')),
            'step_price': safe_float(trailing.get('step_price')),
        }
        if ticket['trailing'].get('distance_mode') == 'atr':
            ticket['trailing']['atr_period'] = int(trailing.get('atr_period') or 14)
            ticket['trailing']['atr_timeframe'] = trailing.get('atr_timeframe') or 'H4'

    return ticket


def main() -> int:
    ap = argparse.ArgumentParser(description='Execute a validated MT5 Phase1 LLM planner output as the live paper ticket source.')
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

    ticket = build_ticket(planner, pack, baseline)
    ticket, preflight = preflight_mt5_ticket(ticket, cfg)
    ticket_path = reports_out / f'ticket_{candidate}_{stamp}.json'
    if preflight.get('mode') == 'applied' and preflight.get('valid_entries', 0) <= 0:
        execution = {
            'status': 'skipped',
            'message': 'All LLM candidate entries became invalid at MT5 preflight time.',
            'preflight': preflight,
        }
    else:
        save_json(ticket_path, ticket)
        if args.dry_run:
            execution = {'status': 'dry_run', 'message': 'LLM ticket compiled but not emitted.', 'preflight': preflight}
        else:
            execution = run_emit(ticket_path, cfg)
            execution['preflight'] = preflight
    result = {
        'result': 'trade_review',
        'session_key': baseline.get('session_key'),
        'report_path': baseline.get('report_path'),
        'report_resolution': baseline.get('report_resolution'),
        'candidate': candidate,
        'analysis_path': args.planner_md or None,
        'ticket_path': str(ticket_path),
        'execution': execution,
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
