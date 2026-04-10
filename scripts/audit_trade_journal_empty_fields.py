#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

WORKSPACE = Path(__file__).resolve().parents[1]
BACKFILL = WORKSPACE / 'reports' / 'mt5_autotrade_phase1' / 'trade_journal_backfill.json'
OUT = WORKSPACE / 'reports' / 'mt5_autotrade_phase1' / 'trade_journal_empty_field_audit.json'


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding='utf-8-sig'))


def main() -> int:
    data = load_json(BACKFILL)
    report: dict[str, Any] = {'sheets': {}}
    for sheet, rows in data.items():
        if not rows:
            report['sheets'][sheet] = {'rowCount': 0, 'columns': []}
            continue
        headers = rows[0]
        body = rows[1:]
        cols = []
        row_count = len(body)
        for i, header in enumerate(headers):
            empty = 0
            samples = []
            for row in body:
                value = row[i] if i < len(row) else ''
                if value in ('', None):
                    empty += 1
                elif len(samples) < 3:
                    samples.append(value)
            cols.append({
                'column': header,
                'emptyCount': empty,
                'rowCount': row_count,
                'emptyRatio': (empty / row_count) if row_count else 0,
                'sampleValues': samples,
            })
        cols.sort(key=lambda c: (-c['emptyCount'], c['column']))
        report['sheets'][sheet] = {
            'rowCount': row_count,
            'columns': cols,
            'fullyEmptyColumns': [c['column'] for c in cols if row_count and c['emptyCount'] == row_count],
        }
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
