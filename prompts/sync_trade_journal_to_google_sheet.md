# Sync MT5 Trade Journal to Google Sheet

Use the authenticated browser session to push the latest local journal bundle into the Google Sheet.

## Preconditions
- The Google Sheet is already shared and editable.
- The browser session has editor access and a valid OAuth token.
- `reports/mt5_autotrade_phase1/trade_journal_backfill.json` exists.

## Do exactly this
1. Run:
   - `python scripts/build_trade_journal_backfill.py`
   - `python scripts/build_trade_journal_sync_payload.py`
2. Start a temporary local HTTP server rooted at the workspace if one is not already running.
3. In the authenticated browser session for the target Google Sheet, fetch:
   - `http://127.0.0.1:8765/reports/mt5_autotrade_phase1/trade_journal_sync_payload.json`
4. Use the browser session OAuth token to call the Google Sheets API and:
   - clear the listed ranges
   - write all `write_data` ranges with RAW values
   - write all `dashboard_formulas` with USER_ENTERED values
5. Verify by reading back these ranges:
   - `Trade_Groups!A1:AG5`
   - `Legs!A1:AC8`
   - `Screener_Snapshot!A1:BK5`
   - `LLM_Review!A1:O5`
   - `Daily_Equity!A1:J5`
6. Stop the temporary local HTTP server if you started it.
7. Report only:
   - whether sync succeeded
   - row counts per tab
   - any blocker

## Hard rules
- Do not change sheet names.
- Keep headers in row 1 intact.
- If OAuth token is unavailable in the browser page, stop and say that browser re-auth is needed.
