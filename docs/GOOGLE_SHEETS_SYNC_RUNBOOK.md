# Google Sheets Sync Runbook

## Current state
The Google Sheet has been initialized with these tabs:
- Dashboard
- Trade_Groups
- Legs
- Screener_Snapshot
- LLM_Review
- Daily_Equity

The initial backfill was pushed by:
1. building a local JSON bundle with `scripts/build_trade_journal_backfill.py`
2. serving the workspace via a local HTTP server with CORS
3. using the authenticated Google Sheets browser session to write rows through the Sheets API

## Local bundle builder
- Script: `scripts/build_trade_journal_backfill.py`
- Output: `reports/mt5_autotrade_phase1/trade_journal_backfill.json`

## Sync approach used
- Serve workspace root locally, e.g. `http://127.0.0.1:8765/`
- Fetch `reports/mt5_autotrade_phase1/trade_journal_backfill.json`
- Use the authenticated Google Sheets session in the browser to:
  - clear `Trade_Groups!A2:ZZ`, `Legs!A2:ZZ`, `Screener_Snapshot!A2:ZZ`, `LLM_Review!A2:ZZ`, `Daily_Equity!A2:ZZ`
  - write bundle values to those tabs starting at `A2`
  - keep headers intact in row 1
  - keep Dashboard seed/formulas in place

## Why this path
No first-class Google Sheets tool exists in the current environment.
The browser session does have editor access and an OAuth token, which makes the Sheets API route much more reliable than pure UI clicking.

## Next automation step (recommended)
Add a small helper flow that, after each completed MT5 cycle:
1. refreshes/updates the local journal bundle
2. syncs only changed rows to the sheet
3. updates Dashboard formulas/aggregates

## Caveat
The browser-auth Sheets API sync depends on an active authenticated browser session. If that session expires, the sync must be re-authenticated in the browser.
