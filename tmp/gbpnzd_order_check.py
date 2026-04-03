import json
from pathlib import Path
import MetaTrader5 as mt5
p = Path(r'C:\Users\anmar\.openclaw\workspace-mt5\reports\mt5_autotrade_phase1\ticket_GBPNZD_20260403_150721.json')
o = json.loads(p.read_text(encoding='utf-8'))
assert mt5.initialize(path=r'C:\MT5_OANDA_PAPER_OC\terminal64.exe')
for i,e in enumerate(o['entries']):
    req = {
        'action': mt5.TRADE_ACTION_PENDING,
        'symbol': o['symbol'],
        'magic': 26032601,
        'volume': float(e['volume_lots']),
        'price': float(e['price']),
        'sl': float(o['stop_loss']['price']),
        'tp': float(o['take_profit']['price']),
        'deviation': 20,
        'type_time': mt5.ORDER_TIME_GTC,
        'type_filling': mt5.ORDER_FILLING_RETURN,
        'comment': o['ticket_id'],
        'type': mt5.ORDER_TYPE_BUY_LIMIT if e['entry_type']=='limit' and o['side']=='buy' else mt5.ORDER_TYPE_SELL_LIMIT if e['entry_type']=='limit' else mt5.ORDER_TYPE_BUY_STOP if o['side']=='buy' else mt5.ORDER_TYPE_SELL_STOP,
    }
    chk = mt5.order_check(req)
    print({'i':i,'entry_type':e['entry_type'],'price':e['price'],'retcode': getattr(chk,'retcode',None),'comment': getattr(chk,'comment',None), 'request': getattr(chk,'request',None)._asdict() if getattr(chk,'request',None) else None})
mt5.shutdown()
