#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from mt5_fx_autotrade_phase1 import DEFAULT_CONFIG, iso_z, now_utc, preflight_mt5_ticket, run_emit, save_json

try:
    import MetaTrader5 as mt5
except Exception:
    mt5 = None

WORKSPACE = Path(__file__).resolve().parents[1]
REPORTS_DIR = WORKSPACE / 'reports' / 'mt5_autotrade_phase1'
DEFAULT_STRATEGY_MAGIC = 26032601


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding='utf-8-sig'))


def safe_float(value: Any) -> float | None:
    try:
        if value in (None, '', '—'):
            return None
        return float(value)
    except Exception:
        return None


def safe_int(value: Any) -> int | None:
    try:
        if value in (None, '', '—'):
            return None
        return int(value)
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


def normalize_symbol_root(symbol: str | None) -> str:
    sym = str(symbol or '').strip().upper()
    if sym.endswith('.PRO'):
        sym = sym[:-4]
    if sym.endswith('.P'):
        sym = sym[:-2]
    return sym


def active_assets_path(cfg: dict[str, Any]) -> Path:
    return Path(cfg['stateDir']) / 'active_assets.json'


def load_active_assets(cfg: dict[str, Any]) -> dict[str, Any]:
    path = active_assets_path(cfg)
    if not path.exists():
        return {'assets': {}}
    try:
        payload = load_json(path)
        if isinstance(payload, dict) and isinstance(payload.get('assets'), dict):
            return payload
    except Exception:
        pass
    return {'assets': {}}


def save_active_assets(cfg: dict[str, Any], payload: dict[str, Any]) -> None:
    save_json(active_assets_path(cfg), payload)


def strategy_magic_from_cfg(cfg: dict[str, Any]) -> int:
    guard = cfg.get('liveSymbolGuard') or {}
    cleanup = cfg.get('compactReportCleanup') or {}
    value = guard.get('strategyMagic', cleanup.get('strategyMagic', DEFAULT_STRATEGY_MAGIC))
    try:
        return int(value)
    except Exception:
        return DEFAULT_STRATEGY_MAGIC


def live_symbol_guard_cfg(cfg: dict[str, Any]) -> dict[str, Any]:
    raw = cfg.get('liveSymbolGuard') or {}
    return {
        'enabled': bool(raw.get('enabled', True)),
        'mode': str(raw.get('mode') or 'replace_pending_only').strip() or 'replace_pending_only',
        'strategyMagic': strategy_magic_from_cfg(cfg),
        'commentPrefixes': list(raw.get('commentPrefixes') or ['p1-', 'p1llm-']),
    }


def is_strategy_managed_comment(comment: str, prefixes: list[str]) -> bool:
    low = str(comment or '').strip().lower()
    return any(low.startswith(str(prefix).lower()) for prefix in prefixes)


def live_symbol_state(cfg: dict[str, Any], execution_symbol: str) -> dict[str, Any]:
    guard = live_symbol_guard_cfg(cfg)
    root = normalize_symbol_root(execution_symbol)
    terminal = str((cfg.get('analysisDataSource') or {}).get('terminalExe') or '').strip()
    if mt5 is None:
        raise RuntimeError('MetaTrader5 import is unavailable in execute_mt5_llm_live.py')
    if not terminal:
        raise RuntimeError('No MT5 terminal configured for live symbol guard')
    if not mt5.initialize(path=terminal):
        raise RuntimeError(f'MT5 initialize failed for live symbol guard: {mt5.last_error()}')

    try:
        pending_orders: list[dict[str, Any]] = []
        open_positions: list[dict[str, Any]] = []
        for order in (mt5.orders_get() or []):
            magic = safe_int(getattr(order, 'magic', None)) or 0
            comment = str(getattr(order, 'comment', '') or '')
            symbol = str(getattr(order, 'symbol', '') or '')
            if normalize_symbol_root(symbol) != root:
                continue
            if magic != guard['strategyMagic'] and not is_strategy_managed_comment(comment, guard['commentPrefixes']):
                continue
            pending_orders.append(order._asdict())
        for position in (mt5.positions_get() or []):
            magic = safe_int(getattr(position, 'magic', None)) or 0
            comment = str(getattr(position, 'comment', '') or '')
            symbol = str(getattr(position, 'symbol', '') or '')
            if normalize_symbol_root(symbol) != root:
                continue
            if magic != guard['strategyMagic'] and not is_strategy_managed_comment(comment, guard['commentPrefixes']):
                continue
            open_positions.append(position._asdict())

        return {
            'symbol_root': root,
            'execution_symbol': execution_symbol,
            'pending_orders': pending_orders,
            'open_positions': open_positions,
            'pending_count': len(pending_orders),
            'position_count': len(open_positions),
            'group_ids': sorted({str(item.get('comment') or '') for item in pending_orders + open_positions if str(item.get('comment') or '').strip()}),
        }
    finally:
        mt5.shutdown()


def cancel_strategy_pending_orders(cfg: dict[str, Any], orders: list[dict[str, Any]], *, reason: str) -> list[dict[str, Any]]:
    terminal = str((cfg.get('analysisDataSource') or {}).get('terminalExe') or '').strip()
    if mt5 is None:
        raise RuntimeError('MetaTrader5 import is unavailable in execute_mt5_llm_live.py')
    if not terminal:
        raise RuntimeError('No MT5 terminal configured for pending-order replacement')
    if not mt5.initialize(path=terminal):
        raise RuntimeError(f'MT5 initialize failed for pending-order replacement: {mt5.last_error()}')

    try:
        results: list[dict[str, Any]] = []
        for order in orders:
            ticket = int(order.get('ticket') or 0)
            req = {
                'action': mt5.TRADE_ACTION_REMOVE,
                'order': ticket,
                'comment': 'replace older unfilled ladder',
            }
            response = mt5.order_send(req)
            response_dict = response._asdict() if response is not None else {'repr': 'None'}
            retcode = safe_int(getattr(response, 'retcode', None)) if response is not None else None
            ok = bool(retcode == getattr(mt5, 'TRADE_RETCODE_DONE', 10009))
            results.append({
                'ticket': ticket,
                'symbol': order.get('symbol'),
                'comment': order.get('comment'),
                'reason': reason,
                'retcode': retcode,
                'ok': ok,
                'mt5_result': response_dict,
            })
        return results
    finally:
        mt5.shutdown()


def enforce_live_symbol_guard(cfg: dict[str, Any], *, execution_symbol: str, candidate: str, group_id: str, dry_run: bool) -> dict[str, Any]:
    guard = live_symbol_guard_cfg(cfg)
    symbol_root = normalize_symbol_root(execution_symbol or candidate)
    if not guard['enabled']:
        return {
            'enabled': False,
            'mode': 'disabled',
            'candidate': candidate,
            'symbol_root': symbol_root,
            'group_id': group_id,
        }

    state = live_symbol_state(cfg, execution_symbol)
    summary: dict[str, Any] = {
        'enabled': True,
        'configured_mode': guard['mode'],
        'candidate': candidate,
        'symbol_root': symbol_root,
        'execution_symbol': execution_symbol,
        'group_id': group_id,
        'pending_count_before': state['pending_count'],
        'position_count_before': state['position_count'],
        'existing_group_ids': state['group_ids'],
        'action': 'none',
        'cancelled_pending': [],
    }

    if state['position_count'] > 0:
        summary['action'] = 'blocked_open_position'
        summary['message'] = f'{candidate} already has {state["position_count"]} active strategy-managed open position(s); refusing to place a new ladder.'
        return summary

    if state['pending_count'] <= 0:
        summary['action'] = 'clear'
        summary['message'] = f'No existing strategy-managed pending ladder found for {candidate}.'
        return summary

    if guard['mode'] == 'strict_lock':
        summary['action'] = 'blocked_existing_pending'
        summary['message'] = f'{candidate} already has {state["pending_count"]} strategy-managed pending order(s); strict symbol lock is active.'
        return summary

    if guard['mode'] != 'replace_pending_only':
        raise RuntimeError(f'Unsupported liveSymbolGuard.mode: {guard["mode"]}')

    reason = f'replacing older unfilled pending ladder(s) for {candidate} before emitting {group_id}'
    if dry_run:
        summary['action'] = 'would_replace_pending'
        summary['message'] = reason
        summary['would_cancel_tickets'] = [int(item.get('ticket') or 0) for item in state['pending_orders']]
        return summary

    cancelled = cancel_strategy_pending_orders(cfg, state['pending_orders'], reason=reason)
    summary['cancelled_pending'] = cancelled
    if not all(item.get('ok') for item in cancelled):
        summary['action'] = 'cancel_failed'
        summary['message'] = f'Failed to cancel all older pending {candidate} orders; refusing to place a replacement ladder.'
        return summary

    summary['action'] = 'replaced_pending'
    summary['message'] = reason
    return summary


def write_active_asset(cfg: dict[str, Any], candidate: str, payload: dict[str, Any]) -> None:
    active = load_active_assets(cfg)
    assets = dict(active.get('assets') or {})
    assets[candidate.upper()] = payload
    active['assets'] = assets
    save_active_assets(cfg, active)


def remove_active_asset(cfg: dict[str, Any], candidate: str) -> None:
    active = load_active_assets(cfg)
    assets = dict(active.get('assets') or {})
    assets.pop(candidate.upper(), None)
    active['assets'] = assets
    save_active_assets(cfg, active)


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
    execution_symbol = str((pack.get('mt5_symbol_profile') or {}).get('execution_symbol') or candidate)

    symbol_guard = enforce_live_symbol_guard(cfg, execution_symbol=execution_symbol, candidate=candidate, group_id=group_id, dry_run=args.dry_run)
    if symbol_guard.get('action') in {'blocked_open_position', 'blocked_existing_pending', 'cancel_failed'}:
        result = {
            'result': 'trade_review',
            'session_key': baseline.get('session_key'),
            'report_path': baseline.get('report_path'),
            'report_resolution': baseline.get('report_resolution'),
            'candidate': candidate,
            'analysis_path': args.planner_md or None,
            'ticket_group_id': group_id,
            'execution': {
                'status': 'blocked',
                'message': str(symbol_guard.get('message') or 'Symbol guard blocked execution.'),
                'valid_entries': 0,
                'legs': [],
            },
            'symbol_guard': symbol_guard,
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
        live_alias_json = reports_out / 'mt5_phase1_live_latest.json'
        save_json(out_json, result)
        save_json(latest_json, result)
        save_json(live_alias_json, result)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0

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

    if overall_status in {'accepted', 'partial'}:
        write_active_asset(cfg, candidate, {
            'session_key': baseline.get('session_key'),
            'ticket_id': group_id,
            'placed_at': iso_z(now_utc()),
            'status': overall_status,
            'source': 'phase1_llm_live',
            'execution_symbol': execution_symbol,
        })
    elif overall_status == 'blocked':
        pass
    elif symbol_guard.get('action') == 'replaced_pending' and overall_status in {'skipped', 'rejected', 'timeout'}:
        remove_active_asset(cfg, candidate)

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
        'symbol_guard': symbol_guard,
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
    live_alias_json = reports_out / 'mt5_phase1_live_latest.json'
    artifacts_index_json = reports_out / 'mt5_phase1_artifacts_latest.json'
    save_json(out_json, result)
    save_json(latest_json, result)
    save_json(live_alias_json, result)
    save_json(artifacts_index_json, {
        'session_key': baseline.get('session_key'),
        'candidate': candidate,
        'baseline_latest': str((reports_out / 'mt5_phase1_latest.json').resolve()),
        'live_latest': str(live_alias_json.resolve()),
        'live_latest_legacy': str(latest_json.resolve()),
        'live_versioned': str(out_json.resolve()),
        'compact_report_latest': str((reports_out / 'mt5_open_compact_report_latest.txt').resolve()),
        'note': 'Use live_latest first for the actual LLM live execution result. baseline_latest is the deterministic baseline artifact and may be dry-run only.'
    })
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
