import csv
import io
import json
import pathlib

MT5 = pathlib.Path(r'C:\MT5_OANDA_PAPER_OC\MQL5\Files\OANDA_All_Symbols.csv')
TV = pathlib.Path(r'C:\Users\anmar\.openclaw\workspace\tradingview\reports\pine_screener\pine_screener_2026-04-03T07-05-25-254Z.csv')
OUT_JSON = pathlib.Path(r'C:\Users\anmar\.openclaw\workspace-mt5\reports\mt5_frx_compare_2026-04-03.json')
OUT_MD = pathlib.Path(r'C:\Users\anmar\.openclaw\workspace-mt5\reports\mt5_frx_compare_2026-04-03.md')


def read_rows(path: pathlib.Path):
    raw = path.read_bytes()
    text = None
    for enc in ('utf-8-sig', 'cp1252', 'latin-1', 'utf-16'):
        try:
            text = raw.decode(enc)
            break
        except Exception:
            continue
    if text is None:
        text = raw.decode('latin-1', errors='replace')
    fh = io.StringIO(text)
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=',;\t')
    except Exception:
        class D(csv.excel):
            delimiter = '\t'
        dialect = D
    return list(csv.DictReader(fh, dialect=dialect))


def normalize_symbol(sym: str) -> str:
    sym = sym.strip().upper()
    if sym.endswith('.PRO'):
        sym = sym[:-4]
    return sym


rows = read_rows(MT5)
tv_rows = read_rows(TV)

fx_rows = []
fx_rows_trade_enabled = []
for r in rows:
    sym = (r.get('Symbol') or '').strip().upper()
    path = (r.get('Path') or '').strip()
    mode = (r.get('TradeMode') or '').strip().upper()
    calc = (r.get('CalcMode') or '').strip().upper()
    is_fx = path.startswith('Forex\\') or calc == 'FOREX'
    if is_fx:
        row = {
            'Symbol': sym,
            'Normalized': normalize_symbol(sym),
            'Path': path,
            'TradeMode': mode,
            'Visible': (r.get('Visible') or '').strip(),
            'Selected': (r.get('Selected') or '').strip(),
            'CalcMode': calc,
        }
        fx_rows.append(row)
        if mode not in {'DISABLED', 'CLOSEONLY'}:
            fx_rows_trade_enabled.append(row)

mt5_all_fx = sorted({r['Symbol'] for r in fx_rows if r['Symbol']})
mt5_all_fx_normalized = sorted({r['Normalized'] for r in fx_rows if r['Normalized']})
mt5_trade_enabled_fx = sorted({r['Symbol'] for r in fx_rows_trade_enabled if r['Symbol']})
mt5_trade_enabled_fx_normalized = sorted({r['Normalized'] for r in fx_rows_trade_enabled if r['Normalized']})
trade_disabled_fx = sorted({r['Symbol'] for r in fx_rows if r['TradeMode'] == 'DISABLED'})

tv_syms = sorted({(r.get('Symbol') or '').strip().upper() for r in tv_rows if (r.get('Symbol') or '').strip()})
intersection_norm = sorted(set(mt5_trade_enabled_fx_normalized) & set(tv_syms))
mt5_trade_enabled_missing_from_tv = sorted(set(mt5_trade_enabled_fx_normalized) - set(tv_syms))
tv_missing_trade_enabled = sorted(set(tv_syms) - set(mt5_trade_enabled_fx_normalized))

payload = {
    'mt5_all_fx_count': len(mt5_all_fx),
    'mt5_all_fx_normalized_count': len(mt5_all_fx_normalized),
    'mt5_trade_enabled_fx_count': len(mt5_trade_enabled_fx),
    'mt5_trade_enabled_fx_normalized_count': len(mt5_trade_enabled_fx_normalized),
    'mt5_trade_disabled_fx_count': len(trade_disabled_fx),
    'tv_watchlist_count': len(tv_syms),
    'intersection_trade_enabled_normalized_count': len(intersection_norm),
    'mt5_trade_enabled_fx': mt5_trade_enabled_fx,
    'mt5_trade_enabled_fx_normalized': mt5_trade_enabled_fx_normalized,
    'mt5_trade_disabled_fx': trade_disabled_fx,
    'tv_watchlist': tv_syms,
    'mt5_trade_enabled_missing_from_tv': mt5_trade_enabled_missing_from_tv,
    'tv_missing_trade_enabled_mt5': tv_missing_trade_enabled,
}
OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
OUT_JSON.write_text(json.dumps(payload, indent=2), encoding='utf-8')

md = []
md.append('# MT5 OANDA FX vs TradingView MT5_FRX')
md.append('')
md.append(f'- MT5 FX symbols marked trade-enabled (raw broker symbols): **{len(mt5_trade_enabled_fx)}**')
md.append(f'- MT5 FX symbols marked trade-enabled (normalized roots): **{len(mt5_trade_enabled_fx_normalized)}**')
md.append(f'- MT5 FX symbols marked disabled: **{len(trade_disabled_fx)}**')
md.append(f'- TradingView MT5_FRX symbols: **{len(tv_syms)}**')
md.append(f'- Normalized intersection (trade-enabled MT5 vs TV): **{len(intersection_norm)}**')
md.append(f'- Trade-enabled MT5 roots missing from TV: **{len(mt5_trade_enabled_missing_from_tv)}**')
md.append(f'- TV symbols missing from trade-enabled MT5 roots: **{len(tv_missing_trade_enabled)}**')
md.append('')
md.append('## Trade-enabled MT5 roots missing from TV')
md.append('')
for sym in mt5_trade_enabled_missing_from_tv:
    md.append(f'- {sym}')
md.append('')
md.append('## TV symbols missing from trade-enabled MT5 roots')
md.append('')
for sym in tv_missing_trade_enabled:
    md.append(f'- {sym}')
md.append('')
OUT_MD.write_text('\n'.join(md) + '\n', encoding='utf-8')

print(json.dumps({
    'summary': {
        'mt5_trade_enabled_fx_count': len(mt5_trade_enabled_fx),
        'mt5_trade_enabled_fx_normalized_count': len(mt5_trade_enabled_fx_normalized),
        'mt5_trade_disabled_fx_count': len(trade_disabled_fx),
        'tv_watchlist_count': len(tv_syms),
        'intersection_trade_enabled_normalized_count': len(intersection_norm),
        'mt5_trade_enabled_missing_from_tv_count': len(mt5_trade_enabled_missing_from_tv),
        'tv_missing_trade_enabled_mt5_count': len(tv_missing_trade_enabled),
    },
    'mt5_trade_enabled_missing_from_tv': mt5_trade_enabled_missing_from_tv,
    'tv_missing_trade_enabled_mt5': tv_missing_trade_enabled,
    'out_json': str(OUT_JSON),
    'out_md': str(OUT_MD),
}, indent=2))
