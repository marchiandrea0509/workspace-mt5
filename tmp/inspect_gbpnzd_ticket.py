import json
from pathlib import Path
import MetaTrader5 as mt5

TICKET_PATH = Path(r'C:\Users\anmar\.openclaw\workspace-mt5\reports\mt5_autotrade_phase1\ticket_GBPNZD_20260403_150721.json')
obj = json.loads(TICKET_PATH.read_text(encoding='utf-8'))

ok = mt5.initialize(path=r'C:\MT5_OANDA_PAPER_OC\terminal64.exe')
if not ok:
    print({'init': False, 'last_error': mt5.last_error()})
    raise SystemExit(1)

sym = obj['symbol']
info = mt5.symbol_info(sym)
tick = mt5.symbol_info_tick(sym)
pt = info.point if info else None
print('symbol', sym)
print('side', obj['side'])
print('stops_level_points', getattr(info, 'trade_stops_level', None))
print('freeze_level_points', getattr(info, 'trade_freeze_level', None))
print('point', pt)
print('bid', getattr(tick, 'bid', None), 'ask', getattr(tick, 'ask', None))
print('sl', obj['stop_loss']['price'], 'tp', obj['take_profit']['price'])
for i,e in enumerate(obj['entries']):
    price = e['price']
    print('entry', i, e['entry_type'], price, 'vol', e['volume_lots'])
    if obj['side']=='buy' and e['entry_type']=='limit' and tick:
        print('  below_ask', price < tick.ask)
        if pt:
            print('  dist_to_ask_pts', (tick.ask - price)/pt)
            print('  sl_dist_pts', (price - obj['stop_loss']['price'])/pt)
            print('  tp_dist_pts', (obj['take_profit']['price'] - price)/pt)
    if obj['side']=='buy' and e['entry_type']=='stop' and tick:
        print('  above_ask', price > tick.ask)
        if pt:
            print('  dist_to_ask_pts', (price - tick.ask)/pt)
            print('  sl_dist_pts', (price - obj['stop_loss']['price'])/pt)
            print('  tp_dist_pts', (obj['take_profit']['price'] - price)/pt)

mt5.shutdown()
