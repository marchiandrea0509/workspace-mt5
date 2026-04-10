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

## Current rollout stage
Current stage is **Option B**:
- build/update the local Excel workbook automatically
- keep the workbook local as the source of truth
- stage the latest versioned workbook into the OpenClaw browser uploads directory
- attempt a single best-effort Google Drive upload only when the expected Drive tab/session is already available
- never fail the MT5 cycle because of Drive upload issues

Later credentialed sync is deferred to Option C.

## Browser-upload helper
- Staging script:
  - `scripts/stage_trade_journal_for_browser_upload.py`
- Best-effort browser prompt:
  - `prompts/upload_mt5_excel_to_gdrive_best_effort.md`

## Recommended automation behavior
After each completed MT5 cycle:
1. build/update thread output
2. build/update local Excel workbook
3. stage the versioned workbook for browser upload
4. if the connected Drive tab is available, attempt one best-effort upload
5. otherwise skip quietly and keep the local workbook as success
