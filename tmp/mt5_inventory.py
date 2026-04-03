import json
import MetaTrader5 as mt5

ok = mt5.initialize(path=r'C:\MT5_OANDA_PAPER_OC\terminal64.exe')
if not ok:
    print(json.dumps({'init': False, 'last_error': mt5.last_error()}))
    raise SystemExit(1)
orders = mt5.orders_get() or []
positions = mt5.positions_get() or []
summary = {
    'init': True,
    'account': mt5.account_info().login if mt5.account_info() else None,
    'orders_total': len(orders),
    'positions_total': len(positions),
    'orders': [
        {
            'ticket': o.ticket,
            'symbol': o.symbol,
            'type': int(o.type),
            'volume_current': o.volume_current,
            'price_open': o.price_open,
            'sl': o.sl,
            'tp': o.tp,
            'magic': o.magic,
            'comment': o.comment,
        } for o in orders
    ],
    'positions': [
        {
            'ticket': p.ticket,
            'symbol': p.symbol,
            'type': int(p.type),
            'volume': p.volume,
            'price_open': p.price_open,
            'sl': p.sl,
            'tp': p.tp,
            'magic': p.magic,
            'comment': p.comment,
            'profit': p.profit,
        } for p in positions
    ],
    'last_error': mt5.last_error(),
}
print(json.dumps(summary, indent=2))
mt5.shutdown()
