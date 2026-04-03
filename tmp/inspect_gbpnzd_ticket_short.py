import json
from pathlib import Path
import MetaTrader5 as mt5
p = Path(r'C:\Users\anmar\.openclaw\workspace-mt5\reports\mt5_autotrade_phase1\ticket_GBPNZD_20260403_150721.json')
o = json.loads(p.read_text(encoding='utf-8'))
mt5.initialize(path=r'C:\MT5_OANDA_PAPER_OC\terminal64.exe')
info = mt5.symbol_info(o['symbol'])
tick = mt5.symbol_info_tick(o['symbol'])
pt = info.point
slv = info.trade_stops_level
issues=[]
for i,e in enumerate(o['entries']):
    px=e['price']
    if e['entry_type']=='limit' and o['side']=='buy' and not (px < tick.ask): issues.append(f'e{i}:buy_limit_not_below_ask')
    if e['entry_type']=='stop' and o['side']=='buy' and not (px > tick.ask): issues.append(f'e{i}:buy_stop_not_above_ask')
    if slv:
        askdist = abs(tick.ask-px)/pt
        sldist = abs(px-o['stop_loss']['price'])/pt
        tpdist = abs(o['take_profit']['price']-px)/pt
        if askdist < slv: issues.append(f'e{i}:entry_too_close_to_market<{slv}')
        if sldist < slv: issues.append(f'e{i}:sl_too_close<{slv}')
        if tpdist < slv: issues.append(f'e{i}:tp_too_close<{slv}')
print({'issues':issues,'stops_level':slv,'symbol':o['symbol'],'side':o['side']})
mt5.shutdown()
