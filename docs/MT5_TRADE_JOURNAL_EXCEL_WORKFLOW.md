# MT5 Trade Journal — Excel Workflow

## Goal
Keep a **local Excel workbook** as the source-of-truth journal artifact for MT5 Phase 1.

## Output files
- Versioned workbook directory:
  - `reports/mt5_autotrade_phase1/excel/`
- Latest stable workbook:
  - `reports/mt5_autotrade_phase1/excel/MT5_trade_journal_latest.xlsx`
- Latest build metadata:
  - `reports/mt5_autotrade_phase1/excel/MT5_trade_journal_latest.json`

## Builder
- Backfill/source bundle:
  - `scripts/build_trade_journal_backfill.py`
- Excel builder:
  - `scripts/build_trade_journal_excel.py`

## Standard refresh
Run:
- `python scripts/build_trade_journal_excel.py`

This will:
1. refresh `trade_journal_backfill.json`
2. build a new timestamped `.xlsx`
3. update `MT5_trade_journal_latest.xlsx`
4. write a metadata summary JSON

## Workbook tabs
- Dashboard
- Trade_Groups
- Legs
- Screener_Snapshot
- LLM_Review
- Daily_Equity

## Google Drive upload policy
If a logged-in Google browser session is available, the latest workbook may be uploaded to Drive as a convenience copy.

If Google session/browser access is **not** available:
- treat it as a **warning only**
- do **not** fail the MT5 cycle
- keep the local Excel workbook as the successful output

## Recommended automation behavior
After each completed MT5 cycle:
1. build/update thread output
2. build/update local Excel workbook
3. check whether a Google browser session is available
4. if available, upload the latest workbook to Drive
5. if not available, report a warning but keep the cycle successful
