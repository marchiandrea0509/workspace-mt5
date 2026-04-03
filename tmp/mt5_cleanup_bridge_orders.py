import json
import MetaTrader5 as mt5
from pathlib import Path

MAGIC = 26032601
TERMINAL = r'C:\MT5_OANDA_PAPER_OC\terminal64.exe'
TRAILING_DIR = Path(r'C:\MT5_OANDA_PAPER_OC\MQL5\Files\gray_bridge\trailing')

ok = mt5.initialize(path=TERMINAL)
if not ok:
    print(json.dumps({'init': False, 'last_error': mt5.last_error()}))
    raise SystemExit(1)

removed_orders = []
failed_orders = []
closed_positions = []
failed_positions = []

orders = list(mt5.orders_get() or [])
for o in orders:
    if int(o.magic) != MAGIC:
        continue
    req = {
        'action': mt5.TRADE_ACTION_REMOVE,
        'order': int(o.ticket),
        'symbol': o.symbol,
        'magic': MAGIC,
        'comment': 'OpenClaw cleanup',
    }
    res = mt5.order_send(req)
    payload = {
        'ticket': int(o.ticket),
        'symbol': o.symbol,
        'retcode': getattr(res, 'retcode', None),
        'comment': getattr(res, 'comment', None),
    }
    if res and getattr(res, 'retcode', None) in {10009, 10008}: 
        removed_orders.append(payload)
    else:
        failed_orders.append(payload)

positions = list(mt5.positions_get() or [])
for p in positions:
    if int(p.magic) != MAGIC:
        continue
    tick = mt5.symbol_info_tick(p.symbol)
    if tick is None:
        failed_positions.append({'ticket': int(p.ticket), 'symbol': p.symbol, 'reason': 'no tick'})
        continue
    order_type = mt5.ORDER_TYPE_SELL if int(p.type) == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY
    price = tick.bid if order_type == mt5.ORDER_TYPE_SELL else tick.ask
    req = {
        'action': mt5.TRADE_ACTION_DEAL,
        'symbol': p.symbol,
        'position': int(p.ticket),
        'volume': float(p.volume),
        'type': order_type,
        'price': price,
        'deviation': 20,
        'magic': MAGIC,
        'comment': 'OpenClaw cleanup close',
        'type_time': mt5.ORDER_TIME_GTC,
        'type_filling': mt5.ORDER_FILLING_RETURN,
    }
    res = mt5.order_send(req)
    payload = {
        'ticket': int(p.ticket),
        'symbol': p.symbol,
        'retcode': getattr(res, 'retcode', None),
        'comment': getattr(res, 'comment', None),
    }
    if res and getattr(res, 'retcode', None) in {10009, 10008}: 
        closed_positions.append(payload)
    else:
        failed_positions.append(payload)

mt5.shutdown()

removed_files = []
for path in TRAILING_DIR.glob('*'):
    try:
        path.unlink()
        removed_files.append(path.name)
    except Exception:
        pass

print(json.dumps({
    'removed_orders': removed_orders,
    'failed_orders': failed_orders,
    'closed_positions': closed_positions,
    'failed_positions': failed_positions,
    'removed_state_files': removed_files,
}, indent=2))
