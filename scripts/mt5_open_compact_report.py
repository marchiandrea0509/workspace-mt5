#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

WORKSPACE = Path(__file__).resolve().parents[1]
CONFIG = WORKSPACE / 'config' / 'mt5_fx_autotrade_phase1.json'
DEFAULT_STRATEGY_MAGIC = 26032601

MT5_ORDER_TYPE_NAMES = {
    0: 'BUY',
    1: 'SELL',
    2: 'BUY_LIMIT',
    3: 'SELL_LIMIT',
    4: 'BUY_STOP',
    5: 'SELL_STOP',
    6: 'BUY_STOP_LIMIT',
    7: 'SELL_STOP_LIMIT',
    8: 'CLOSE_BY',
}

MT5_POSITION_TYPE_NAMES = {
    0: 'BUY',
    1: 'SELL',
}

PENDING_ORDER_TYPES = {2, 3, 4, 5, 6, 7}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding='utf-8-sig'))


def save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def choose_mt5_terminal() -> str:
    if not CONFIG.exists():
        return ''
    try:
        cfg = load_json(CONFIG)
    except Exception:
        return ''
    analysis = cfg.get('analysisDataSource') or {}
    return str(analysis.get('terminalExe') or '').strip()


def load_cfg() -> dict[str, Any]:
    if not CONFIG.exists():
        return {}
    try:
        return load_json(CONFIG)
    except Exception:
        return {}


def normalize_symbol_root(symbol: str | None) -> str:
    sym = str(symbol or '').strip().upper()
    if sym.endswith('.PRO'):
        sym = sym[:-4]
    if sym.endswith('.P'):
        sym = sym[:-2]
    return sym


def fmt_num(value: Any, digits: int = 2) -> str:
    try:
        return f"{float(value):.{digits}f}"
    except Exception:
        return '—'


def fmt_pct(value: float | None, digits: int = 0, suffix: str = '%') -> str:
    if value is None:
        return '—'
    return f"{value:+.{digits}f}{suffix}"


def infer_digits(*values: Any) -> int:
    floats = []
    for value in values:
        try:
            fv = float(value)
        except Exception:
            continue
        if fv == 0:
            continue
        floats.append(abs(fv))
    if not floats:
        return 2
    max_v = max(floats)
    if max_v >= 100:
        return 2
    if max_v >= 1:
        return 5
    return 5


def side_from_order_type(type_name: str) -> str:
    return 'BUY' if 'BUY' in type_name else 'SELL'


def progress_pct(price: float, entry: float, sl: float, tp: float, side: str) -> float | None:
    if side == 'BUY':
        if price >= entry:
            den = tp - entry
            return ((price - entry) / den) * 100.0 if den else None
        den = entry - sl
        return -((entry - price) / den) * 100.0 if den else None
    if price <= entry:
        den = entry - tp
        return ((entry - price) / den) * 100.0 if den else None
    den = sl - entry
    return -((price - entry) / den) * 100.0 if den else None


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_z(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def parse_dt_utc(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace('Z', '+00:00')).astimezone(timezone.utc)
    except Exception:
        return None


def order_setup_dt(order: dict[str, Any]) -> datetime | None:
    ms = order.get('time_setup_msc')
    if ms:
        try:
            return datetime.fromtimestamp(float(ms) / 1000.0, tz=timezone.utc)
        except Exception:
            pass
    sec = order.get('time_setup')
    if sec:
        try:
            return datetime.fromtimestamp(float(sec), tz=timezone.utc)
        except Exception:
            pass
    return None


def load_snapshots(state_dir: Path) -> dict[str, Any]:
    path = state_dir / 'pending_order_snapshots.json'
    if not path.exists():
        return {'orders': {}}
    try:
        payload = load_json(path)
        if isinstance(payload, dict) and isinstance(payload.get('orders'), dict):
            return payload
    except Exception:
        pass
    return {'orders': {}}


def save_snapshots(state_dir: Path, payload: dict[str, Any]) -> None:
    save_json(state_dir / 'pending_order_snapshots.json', payload)


def estimate_submission_price(mt5: Any, order: dict[str, Any]) -> tuple[float | None, str]:
    setup_dt = order_setup_dt(order)
    symbol = str(order.get('symbol') or '')
    if not setup_dt or not symbol:
        return None, 'missing_setup_time'

    window_start = setup_dt - timedelta(minutes=2)
    window_end = setup_dt + timedelta(minutes=5)
    try:
        ticks = mt5.copy_ticks_range(symbol, window_start, window_end, mt5.COPY_TICKS_ALL)
    except Exception:
        ticks = None

    if ticks is not None and len(ticks):
        target_ms = int(setup_dt.timestamp() * 1000)
        best_price = None
        best_dist = None
        for tick in ticks:
            try:
                t_ms = int(tick['time_msc']) if 'time_msc' in tick.dtype.names else int(tick['time']) * 1000
            except Exception:
                t_ms = target_ms
            bid = float(tick['bid']) if 'bid' in tick.dtype.names else 0.0
            ask = float(tick['ask']) if 'ask' in tick.dtype.names else 0.0
            last = float(tick['last']) if 'last' in tick.dtype.names else 0.0
            if bid > 0 and ask > 0:
                px = (bid + ask) / 2.0
            elif last > 0:
                px = last
            elif bid > 0:
                px = bid
            elif ask > 0:
                px = ask
            else:
                continue
            dist = abs(t_ms - target_ms)
            if best_dist is None or dist < best_dist:
                best_dist = dist
                best_price = px
        if best_price is not None:
            return float(best_price), 'ticks_range'

    current = order.get('price_current')
    try:
        if current not in (None, ''):
            return float(current), 'current_fallback'
    except Exception:
        pass
    return None, 'unavailable'


def ensure_order_snapshot(mt5: Any, snapshots: dict[str, Any], order: dict[str, Any]) -> dict[str, Any]:
    orders = snapshots.setdefault('orders', {})
    ticket = str(int(order.get('ticket') or 0))
    existing = orders.get(ticket)
    if isinstance(existing, dict):
        return existing

    type_name = MT5_ORDER_TYPE_NAMES.get(int(order.get('type') or -1), str(order.get('type')))
    side = side_from_order_type(type_name)
    entry = float(order.get('price_open') or 0)
    sl = float(order.get('sl') or 0)
    tp = float(order.get('tp') or 0)
    submitted_price, source = estimate_submission_price(mt5, order)
    submitted_frac = progress_pct(submitted_price, entry, sl, tp, side) if submitted_price and entry and sl and tp else None
    gap = abs(float(submitted_price) - entry) if submitted_price is not None and entry else None
    snap = {
        'ticket': int(order.get('ticket') or 0),
        'symbol': order.get('symbol'),
        'type': int(order.get('type') or -1),
        'comment': str(order.get('comment') or ''),
        'magic': int(order.get('magic') or 0),
        'setup_time_utc': iso_z(order_setup_dt(order)),
        'submitted_price': submitted_price,
        'submitted_price_source': source,
        'submitted_frac': submitted_frac,
        'submitted_gap_to_entry': gap,
        'snapshot_created_at': iso_z(utc_now()),
    }
    orders[ticket] = snap
    return snap


def symbol_point(mt5: Any, symbol: str) -> float | None:
    try:
        info = mt5.symbol_info(symbol)
    except Exception:
        info = None
    if info is None:
        return None
    try:
        point = float(getattr(info, 'point', 0.0) or 0.0)
        return point if point > 0 else None
    except Exception:
        return None


def adverse_gap_delta_pct(order: dict[str, Any], snapshot: dict[str, Any], mt5: Any) -> float | None:
    try:
        entry = float(order.get('price_open') or 0.0)
        current = float(order.get('price_current') or 0.0)
    except Exception:
        return None
    submitted = snapshot.get('submitted_price')
    try:
        submitted = float(submitted)
    except Exception:
        return None
    if not entry:
        return None

    submitted_gap = abs(submitted - entry)
    current_gap = abs(current - entry)
    tp = float(order.get('tp') or 0.0)
    sl = float(order.get('sl') or 0.0)
    reward_span = abs(tp - entry) if tp else 0.0
    risk_span = abs(entry - sl) if sl else 0.0
    point = symbol_point(mt5, str(order.get('symbol') or '')) or 0.0
    denom = max(submitted_gap, reward_span * 0.25, risk_span * 0.25, point * 10.0, 1e-9)
    return ((current_gap - submitted_gap) / denom) * 100.0


def order_age_minutes(order: dict[str, Any]) -> float | None:
    setup_dt = order_setup_dt(order)
    if not setup_dt:
        return None
    return max(0.0, (utc_now() - setup_dt).total_seconds() / 60.0)


def is_strategy_managed(order: dict[str, Any], strategy_magic: int) -> bool:
    try:
        if int(order.get('magic') or 0) == int(strategy_magic):
            return True
    except Exception:
        pass
    comment = str(order.get('comment') or '').strip().lower()
    return comment.startswith('p1-') or comment.startswith('p1llm-')


def remove_pending_order(mt5: Any, order: dict[str, Any], reason: str, dry_run: bool) -> dict[str, Any]:
    ticket = int(order.get('ticket') or 0)
    symbol = str(order.get('symbol') or '')
    comment = str(order.get('comment') or '')
    if dry_run:
        return {
            'ticket': ticket,
            'comment': comment,
            'symbol': symbol,
            'status': 'would_cancel',
            'reason': reason,
        }

    req = {
        'action': mt5.TRADE_ACTION_REMOVE,
        'order': ticket,
        'symbol': symbol,
        'magic': int(order.get('magic') or DEFAULT_STRATEGY_MAGIC),
    }
    result = mt5.order_send(req)
    payload = {
        'ticket': ticket,
        'comment': comment,
        'symbol': symbol,
        'status': 'cancel_failed',
        'reason': reason,
        'request': req,
    }
    if result is not None:
        try:
            result_dict = result._asdict()
        except Exception:
            result_dict = {'repr': repr(result)}
        payload['mt5_result'] = result_dict
        try:
            retcode = int(getattr(result, 'retcode', 0) or 0)
        except Exception:
            retcode = 0
        payload['retcode'] = retcode
        payload['status'] = 'cancelled' if retcode in {getattr(mt5, 'TRADE_RETCODE_DONE', 10009), getattr(mt5, 'TRADE_RETCODE_PLACED', 10008)} else 'cancel_failed'
    else:
        try:
            payload['last_error'] = mt5.last_error()
        except Exception:
            pass
    return payload


def cleanup_pending_orders(mt5: Any, cfg: dict[str, Any], orders: list[dict[str, Any]], *, dry_run: bool = False) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    state_dir = Path(cfg.get('stateDir') or (WORKSPACE / 'state' / 'mt5_autotrade_phase1'))
    cleanup_cfg = cfg.get('compactReportCleanup') or {}
    enabled = bool(cleanup_cfg.get('enabled', True))
    strategy_magic = int(cleanup_cfg.get('strategyMagic', DEFAULT_STRATEGY_MAGIC) or DEFAULT_STRATEGY_MAGIC)
    max_adverse_gap_pct = float(cleanup_cfg.get('maxAdverseGapFromSubmissionPct', 75.0) or 75.0)
    min_age_minutes = float(cleanup_cfg.get('minOrderAgeMinutes', 60.0) or 60.0)

    snapshots = load_snapshots(state_dir)
    summary = {
        'enabled': enabled,
        'dry_run': dry_run,
        'strategy_magic': strategy_magic,
        'max_adverse_gap_from_submission_pct': max_adverse_gap_pct,
        'min_order_age_minutes': min_age_minutes,
        'checked': 0,
        'eligible': 0,
        'cancelled': 0,
        'would_cancel': 0,
        'failed': 0,
        'details': [],
    }

    live_tickets = {str(int(o.get('ticket') or 0)) for o in orders if int(o.get('type') or -1) in PENDING_ORDER_TYPES}
    snapshots['orders'] = {k: v for k, v in (snapshots.get('orders') or {}).items() if k in live_tickets}

    if not enabled:
        save_snapshots(state_dir, snapshots)
        return orders, summary, snapshots

    cancelled_tickets: set[int] = set()

    for order in orders:
        if int(order.get('type') or -1) not in PENDING_ORDER_TYPES:
            continue
        summary['checked'] += 1
        if not is_strategy_managed(order, strategy_magic):
            continue

        summary['eligible'] += 1
        snap = ensure_order_snapshot(mt5, snapshots, order)
        gap_delta = adverse_gap_delta_pct(order, snap, mt5)
        age_minutes = order_age_minutes(order)
        type_name = MT5_ORDER_TYPE_NAMES.get(int(order.get('type') or -1), str(order.get('type')))
        side = side_from_order_type(type_name)
        entry = float(order.get('price_open') or 0)
        sl = float(order.get('sl') or 0)
        tp = float(order.get('tp') or 0)
        now = float(order.get('price_current') or 0)
        current_frac = progress_pct(now, entry, sl, tp, side) if entry and sl and tp and now else None
        submit_frac = snap.get('submitted_frac')
        try:
            submit_frac_f = float(submit_frac) if submit_frac is not None else None
        except Exception:
            submit_frac_f = None
        delta_frac = (current_frac - submit_frac_f) if (current_frac is not None and submit_frac_f is not None) else None

        detail = {
            'ticket': int(order.get('ticket') or 0),
            'comment': str(order.get('comment') or ''),
            'symbol': str(order.get('symbol') or ''),
            'type_name': type_name,
            'age_minutes': round(age_minutes, 1) if age_minutes is not None else None,
            'submitted_price': snap.get('submitted_price'),
            'current_price': now,
            'submitted_frac': submit_frac_f,
            'current_frac': current_frac,
            'delta_frac': delta_frac,
            'adverse_gap_delta_pct': gap_delta,
            'snapshot_source': snap.get('submitted_price_source'),
        }

        if age_minutes is None or age_minutes < min_age_minutes:
            detail['decision'] = 'keep_young'
            summary['details'].append(detail)
            continue
        if gap_delta is None or gap_delta < max_adverse_gap_pct:
            detail['decision'] = 'keep'
            summary['details'].append(detail)
            continue

        reason = f'pending order drifted {gap_delta:+.0f}% farther from entry vs submission after {age_minutes:.0f}m (threshold {max_adverse_gap_pct:.0f}%)'
        result = remove_pending_order(mt5, order, reason=reason, dry_run=dry_run)
        detail['decision'] = result['status']
        detail['reason'] = reason
        detail['mt5_result'] = result.get('mt5_result')
        summary['details'].append(detail)
        if result['status'] == 'would_cancel':
            summary['would_cancel'] += 1
        elif result['status'] == 'cancelled':
            summary['cancelled'] += 1
            cancelled_tickets.add(int(order.get('ticket') or 0))
        else:
            summary['failed'] += 1

    save_snapshots(state_dir, snapshots)
    remaining = [o for o in orders if int(o.get('ticket') or 0) not in cancelled_tickets]
    return remaining, summary, snapshots


def compact_report(*, enable_cleanup: bool = True, dry_run_cleanup: bool = False) -> str:
    cfg = load_cfg()
    terminal = str((cfg.get('analysisDataSource') or {}).get('terminalExe') or '').strip() or choose_mt5_terminal()
    if not terminal:
        raise SystemExit('No MT5 terminal configured in config/mt5_fx_autotrade_phase1.json')

    try:
        import MetaTrader5 as mt5
    except Exception as exc:
        raise SystemExit(f'MetaTrader5 import failed: {exc}')

    if not mt5.initialize(path=terminal):
        raise SystemExit(f'MT5 initialize failed: {mt5.last_error()}')
    try:
        orders = [o._asdict() for o in (mt5.orders_get() or [])]
        cleanup_summary = {
            'enabled': False,
            'dry_run': dry_run_cleanup,
            'checked': 0,
            'eligible': 0,
            'cancelled': 0,
            'would_cancel': 0,
            'failed': 0,
            'details': [],
        }
        snapshots = {'orders': {}}
        if enable_cleanup:
            orders, cleanup_summary, snapshots = cleanup_pending_orders(mt5, cfg, orders, dry_run=dry_run_cleanup)
            if cleanup_summary.get('cancelled'):
                orders = [o._asdict() for o in (mt5.orders_get() or [])]
        positions = [p._asdict() for p in (mt5.positions_get() or [])]
    finally:
        try:
            mt5.shutdown()
        except Exception:
            pass

    snapshot_map = snapshots.get('orders') or {}
    groups: dict[str, dict[str, Any]] = defaultdict(lambda: {
        'symbol': '',
        'orders': [],
        'positions': [],
    })

    for order in orders:
        key = str(order.get('comment') or f"order-{order.get('ticket')}")
        groups[key]['symbol'] = normalize_symbol_root(order.get('symbol'))
        groups[key]['orders'].append(order)

    for position in positions:
        key = str(position.get('comment') or f"position-{position.get('ticket')}")
        groups[key]['symbol'] = normalize_symbol_root(position.get('symbol'))
        groups[key]['positions'].append(position)

    symbol_count = len({normalize_symbol_root(o.get('symbol')) for o in orders} | {normalize_symbol_root(p.get('symbol')) for p in positions})

    lines: list[str] = []
    lines.append('MT5 compact open report')
    lines.append(f'- Symbols: {symbol_count}')
    lines.append(f'- Open orders: {len(orders)}')
    lines.append(f'- Open positions: {len(positions)}')
    if enable_cleanup:
        cleanup_mode = 'dry-run' if dry_run_cleanup else 'live'
        lines.append(
            f"- Cleanup ({cleanup_mode}): checked {cleanup_summary.get('checked', 0)} pending | eligible {cleanup_summary.get('eligible', 0)} | cancelled {cleanup_summary.get('cancelled', 0)} | would cancel {cleanup_summary.get('would_cancel', 0)} | failed {cleanup_summary.get('failed', 0)}"
        )
        lines.append(
            f"- Cleanup rule: cancel strategy-managed pending orders aged >= {fmt_num(cleanup_summary.get('min_order_age_minutes'), 0)}m when current gap-to-entry is >= {fmt_num(cleanup_summary.get('max_adverse_gap_from_submission_pct'), 0)}% farther than at submission"
        )

    cancelled_or_would = [d for d in (cleanup_summary.get('details') or []) if d.get('decision') in {'would_cancel', 'cancelled', 'cancel_failed'}]
    for item in cancelled_or_would[:8]:
        lines.append(
            f"- Cleanup {item.get('decision')}: #{item.get('ticket')} {item.get('symbol')} {item.get('type_name')} | age {fmt_num(item.get('age_minutes'), 0)}m | dfrac {fmt_pct(item.get('delta_frac'), 0)} | gap_delta {fmt_pct(item.get('adverse_gap_delta_pct'), 0)}"
        )

    if not groups:
        lines.append('- No open MT5 orders or positions.')
        return '\n'.join(lines)

    grouped_items = sorted(groups.items(), key=lambda kv: (kv[1]['symbol'], kv[0]))
    current_symbol = None
    for group_id, payload in grouped_items:
        symbol = payload['symbol'] or 'UNKNOWN'
        if symbol != current_symbol:
            lines.append(f'\n{symbol}')
            current_symbol = symbol
        lines.append(f'- {group_id} | pending {len(payload["orders"])} | open {len(payload["positions"])}')

        for order in sorted(payload['orders'], key=lambda row: int(row.get('ticket') or 0)):
            type_name = MT5_ORDER_TYPE_NAMES.get(int(order.get('type') or -1), str(order.get('type')))
            side = side_from_order_type(type_name)
            entry = float(order.get('price_open') or 0)
            sl = float(order.get('sl') or 0)
            tp = float(order.get('tp') or 0)
            now = float(order.get('price_current') or 0)
            digits = infer_digits(entry, sl, tp, now)
            pct = progress_pct(now, entry, sl, tp, side) if entry and sl and tp and now else None
            snap = snapshot_map.get(str(int(order.get('ticket') or 0))) or {}
            submit_frac = snap.get('submitted_frac')
            try:
                submit_frac_f = float(submit_frac) if submit_frac is not None else None
            except Exception:
                submit_frac_f = None
            delta_frac = (pct - submit_frac_f) if (pct is not None and submit_frac_f is not None) else None
            gap_delta = adverse_gap_delta_pct(order, snap, None) if False else None
            # recompute without MT5 symbol_info dependency when rendering
            try:
                submitted_price = float(snap.get('submitted_price')) if snap.get('submitted_price') is not None else None
            except Exception:
                submitted_price = None
            if submitted_price is not None and entry:
                submitted_gap = abs(submitted_price - entry)
                current_gap = abs(now - entry)
                reward_span = abs(tp - entry) if tp else 0.0
                risk_span = abs(entry - sl) if sl else 0.0
                denom = max(submitted_gap, reward_span * 0.25, risk_span * 0.25, 1e-9)
                gap_delta = ((current_gap - submitted_gap) / denom) * 100.0
            age_min = order_age_minutes(order)
            lines.append(
                f"  - #{order.get('ticket')} {type_name} {fmt_num(order.get('volume_current'), 2)} lots @ {fmt_num(entry, digits)} | SL {fmt_num(sl, digits)} | TP {fmt_num(tp, digits)} | now {fmt_num(now, digits)} | pnl 0.00 (pending) | frac {fmt_pct(pct, 0)} | dfrac {fmt_pct(delta_frac, 0)} | gap_delta {fmt_pct(gap_delta, 0)} | age {fmt_num(age_min, 0)}m"
            )

        for position in sorted(payload['positions'], key=lambda row: int(row.get('ticket') or 0)):
            type_name = MT5_POSITION_TYPE_NAMES.get(int(position.get('type') or -1), str(position.get('type')))
            side = type_name
            entry = float(position.get('price_open') or 0)
            sl = float(position.get('sl') or 0)
            tp = float(position.get('tp') or 0)
            now = float(position.get('price_current') or 0)
            pnl = float(position.get('profit') or 0)
            digits = infer_digits(entry, sl, tp, now)
            pct = progress_pct(now, entry, sl, tp, side) if entry and sl and tp and now else None
            pct_txt = f"{pct:+.0f}%" if pct is not None else '—'
            lines.append(
                f"  - pos#{position.get('ticket')} {type_name} {fmt_num(position.get('volume'), 2)} lots @ {fmt_num(entry, digits)} | SL {fmt_num(sl, digits)} | TP {fmt_num(tp, digits)} | now {fmt_num(now, digits)} | pnl {fmt_num(pnl, 2)} | frac {pct_txt}"
            )

    return '\n'.join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description='Build compact MT5 open-order/open-position report with optional stale-pending cleanup.')
    ap.add_argument('--no-cleanup', action='store_true', help='Skip pending-order cleanup before building the report.')
    ap.add_argument('--dry-run-cleanup', action='store_true', help='Evaluate cleanup logic but do not actually cancel anything.')
    ap.add_argument('--out', default='', help='Optional path to write the rendered report text.')
    args = ap.parse_args()
    report = compact_report(enable_cleanup=not args.no_cleanup, dry_run_cleanup=args.dry_run_cleanup)
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(report + '\n', encoding='utf-8')
    print(report)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
