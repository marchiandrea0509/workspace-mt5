#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import urllib.request
from pathlib import Path
from typing import Any

WORKSPACE = Path(__file__).resolve().parents[1]
SYNC_PAYLOAD = WORKSPACE / 'reports' / 'mt5_autotrade_phase1' / 'trade_journal_sync_payload.json'
QUEUE_FILE = WORKSPACE / 'reports' / 'mt5_autotrade_phase1' / 'journal_sync_failures.json'
LOCAL_CONFIG = WORKSPACE / 'state' / 'trade_journal_sync_config.json'


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding='utf-8-sig'))


def save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def post_json(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'}, method='POST')
    with urllib.request.urlopen(req, timeout=60) as resp:
        body = resp.read().decode('utf-8', errors='replace')
        return json.loads(body)


def main() -> int:
    ap = argparse.ArgumentParser(description='Sync MT5 trade journal to Google Sheet via Apps Script Web App.')
    ap.add_argument('--webapp-url', default='')
    ap.add_argument('--secret', default='')
    ap.add_argument('--spreadsheet-id', default='')
    ap.add_argument('--payload', default=str(SYNC_PAYLOAD))
    args = ap.parse_args()

    local_cfg = load_json(LOCAL_CONFIG) if LOCAL_CONFIG.exists() else {}
    webapp_url = args.webapp_url or os.getenv('MT5_JOURNAL_WEBAPP_URL', '') or local_cfg.get('webappUrl', '')
    secret = args.secret or os.getenv('MT5_JOURNAL_SHARED_SECRET', '') or local_cfg.get('sharedSecret', '')
    spreadsheet_id = args.spreadsheet_id or os.getenv('MT5_JOURNAL_SPREADSHEET_ID', '') or local_cfg.get('spreadsheetId', '1Y2Ky8BsalifDAD3XmB2XAmKheuDUTolrB8tZ3lPKYfY')

    if not webapp_url:
        raise SystemExit('Missing MT5_JOURNAL_WEBAPP_URL / local sync config webappUrl')
    if not secret:
        raise SystemExit('Missing MT5_JOURNAL_SHARED_SECRET / local sync config sharedSecret')

    payload = load_json(Path(args.payload))
    payload['secret'] = secret
    payload['spreadsheetId'] = spreadsheet_id

    try:
        response = post_json(webapp_url, payload)
        print(json.dumps(response, indent=2, ensure_ascii=False))
        if not response.get('ok'):
            save_json(QUEUE_FILE, {'failed_payload': payload, 'response': response})
            raise SystemExit(1)
        if QUEUE_FILE.exists():
            QUEUE_FILE.unlink()
        return 0
    except Exception as err:
        save_json(QUEUE_FILE, {'failed_payload': payload, 'error': str(err)})
        raise


if __name__ == '__main__':
    raise SystemExit(main())
