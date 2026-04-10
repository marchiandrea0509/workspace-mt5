# Apps Script Journal Deployment

## Goal
Deploy a Google Apps Script Web App that accepts a journal sync payload and writes it into the trade journal Google Sheet.

## Files
- Apps Script code: `templates/google_apps_script/Code.gs`
- Local sender: `scripts/sync_trade_journal_via_webapp.py`
- Payload builder: `scripts/build_trade_journal_sync_payload.py`

## Deployment steps
1. Open Google Apps Script and create a project.
2. Paste `templates/google_apps_script/Code.gs` into the project.
3. Preferred: in **Project Settings > Script properties**, set:
   - `MT5_JOURNAL_SHARED_SECRET=<your secret>`
   Bootstrap alternative: inject the same secret into `FALLBACK_SHARED_SECRET` before first deployment.
4. Deploy as **Web App**:
   - Execute as: **Me**
   - Who has access: **Anyone with the link** (or restricted if your account allows authenticated calls from your environment)
5. Copy the Web App URL.
6. On the local side, set environment variables:
   - `MT5_JOURNAL_WEBAPP_URL`
   - `MT5_JOURNAL_SHARED_SECRET`
   - optionally `MT5_JOURNAL_SPREADSHEET_ID`
7. Run:
   - `python scripts/build_trade_journal_backfill.py`
   - `python scripts/build_trade_journal_sync_payload.py`
   - `python scripts/sync_trade_journal_via_webapp.py`

## Recommended usage in MT5 cycle
After a completed cycle:
1. rebuild backfill bundle
2. build sync payload
3. sync via web app
4. if sync fails, keep trading flow successful and rely on `journal_sync_failures.json` for retry

## Retry behavior
- Failed syncs are stored in:
  - `reports/mt5_autotrade_phase1/journal_sync_failures.json`
- A later retry can simply rerun the sender after fixing URL/secret/auth issues.

## Security note
Use a sufficiently random shared secret and do not expose it in chat logs or committed code.
