#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any

WORKSPACE = Path(__file__).resolve().parents[1]
EXCEL_DIR = WORKSPACE / 'reports' / 'mt5_autotrade_phase1' / 'excel'
LATEST_META = EXCEL_DIR / 'MT5_trade_journal_latest.json'
UPLOADS_DIR = Path(r'C:\Users\anmar\AppData\Local\Temp\openclaw\uploads')
OUT = EXCEL_DIR / 'gdrive_stage_latest.json'


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding='utf-8-sig'))


def main() -> int:
    ap = argparse.ArgumentParser(description='Stage the latest MT5 trade journal workbook into the OpenClaw browser uploads directory.')
    ap.add_argument('--use', choices=['versioned', 'latest'], default='versioned', help='Which workbook path from metadata to stage.')
    args = ap.parse_args()

    if not LATEST_META.exists():
        raise SystemExit(f'Missing workbook metadata: {LATEST_META}')

    meta = load_json(LATEST_META)
    source_key = 'workbookPath' if args.use == 'versioned' else 'latestPath'
    source = Path(meta.get(source_key, ''))
    if not source.exists():
        raise SystemExit(f'Missing source workbook for {source_key}: {source}')

    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    staged = UPLOADS_DIR / source.name
    shutil.copyfile(source, staged)

    payload = {
        'ok': True,
        'sourceKey': source_key,
        'sourceWorkbookPath': str(source),
        'stagedPath': str(staged),
        'filename': source.name,
        'sizeBytes': staged.stat().st_size,
    }
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
