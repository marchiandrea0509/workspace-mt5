#!/usr/bin/env python3
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

WORKSPACE = Path(__file__).resolve().parents[1]
CONFIG = WORKSPACE / 'config' / 'mt5_fx_autotrade_phase1.json'

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


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding='utf-8-sig'))


def choose_mt5_terminal() -> str:
    if not CONFIG.exists():
        return ''
    try:
        cfg = load_json(CONFIG)
    except Exception:
        return ''
    analysis = cfg.get('analysisDataSource') or {}
    return str(analysis.get('terminalExe') or '').strip()


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


def compact_report() -> str:
    terminal = choose_mt5_terminal()
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
        positions = [p._asdict() for p in (mt5.positions_get() or [])]
    finally:
        try:
            mt5.shutdown()
        except Exception:
            pass

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
            pct_txt = f"{pct:+.0f}%" if pct is not None else '—'
            lines.append(
                f"  - #{order.get('ticket')} {type_name} {fmt_num(order.get('volume_current'), 2)} lots @ {fmt_num(entry, digits)} | SL {fmt_num(sl, digits)} | TP {fmt_num(tp, digits)} | now {fmt_num(now, digits)} | pnl 0.00 (pending) | frac {pct_txt}"
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


if __name__ == '__main__':
    print(compact_report())
