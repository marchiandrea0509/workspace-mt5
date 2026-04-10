#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

WORKSPACE = Path(__file__).resolve().parents[1]
BACKFILL = WORKSPACE / 'reports' / 'mt5_autotrade_phase1' / 'trade_journal_backfill.json'
OUT = WORKSPACE / 'reports' / 'mt5_autotrade_phase1' / 'trade_journal_sync_payload.json'


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding='utf-8-sig'))


def main() -> int:
    bundle = load_json(BACKFILL)
    clear_ranges = [
        'Trade_Groups!A2:ZZ',
        'Legs!A2:ZZ',
        'Screener_Snapshot!A2:ZZ',
        'LLM_Review!A2:ZZ',
        'Daily_Equity!A2:ZZ',
    ]
    write_data = []
    for sheet, values in bundle.items():
        body = values[1:] if values else []
        write_data.append({'range': f'{sheet}!A2', 'values': body})

    dashboard_formulas = [
        {'range': 'Dashboard!B2', 'values': [['']]},
        {'range': 'Dashboard!B3', 'values': [['']]},
        {'range': 'Dashboard!B4', 'values': [['=IFERROR(SUM(Trade_Groups!X2:X),0)']]},
        {'range': 'Dashboard!B5', 'values': [['']]},
        {'range': 'Dashboard!B6', 'values': [['=COUNTA(Trade_Groups!A2:A)']]},
        {'range': 'Dashboard!B7', 'values': [['=COUNTA(Legs!A2:A)']]},
        {'range': 'Dashboard!B8', 'values': [['=IFERROR(COUNTIF(Trade_Groups!AE2:AE,"win")/COUNTIF(Trade_Groups!AF2:AF,"<>"),0)']]},
        {'range': 'Dashboard!B9', 'values': [['=IFERROR(SUMIF(Trade_Groups!AE2:AE,"win",Trade_Groups!X2:X)/ABS(SUMIF(Trade_Groups!AE2:AE,"loss",Trade_Groups!X2:X)),0)']]},
        {'range': 'Dashboard!B10', 'values': [['=IFERROR(AVERAGE(Trade_Groups!X2:X),0)']]},
        {'range': 'Dashboard!B11', 'values': [['=IFERROR(AVERAGE(Trade_Groups!Y2:Y),0)']]},
        {'range': 'Dashboard!B12', 'values': [['=IFERROR(AVERAGEIF(Trade_Groups!X2:X,">0"),0)']]},
        {'range': 'Dashboard!B13', 'values': [['=IFERROR(AVERAGEIF(Trade_Groups!X2:X,"<0"),0)']]},
        {'range': 'Dashboard!B16', 'values': [['=IFERROR(AVERAGE(Trade_Groups!V2:V),0)']]},
        {'range': 'Dashboard!B18', 'values': [['=IFERROR(AVERAGE(Trade_Groups!W2:W),0)']]},
        {'range': 'Dashboard!B19', 'values': [['=IFERROR(COUNTIF(Legs!X2:X,"rejected")/COUNTA(Legs!A2:A),0)']]},
        {'range': 'Dashboard!B20', 'values': [['=IFERROR(COUNTIF(Legs!X2:X,"cancelled")/COUNTA(Legs!A2:A),0)']]},
    ]

    payload = {
        'spreadsheet_tabs_expected': ['Dashboard', 'Trade_Groups', 'Legs', 'Screener_Snapshot', 'LLM_Review', 'Daily_Equity'],
        'clear_ranges': clear_ranges,
        'write_data': write_data,
        'dashboard_formulas': dashboard_formulas,
    }
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps({
        'ok': True,
        'out': str(OUT),
        'tabs': payload['spreadsheet_tabs_expected'],
        'write_ranges': len(write_data),
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
