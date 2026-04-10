# Best-Effort Upload — MT5 Excel Journal to Google Drive

Use this only after the local Excel journal was built successfully.

## Goal
Upload the staged MT5 Excel workbook to the existing Google Drive folder as a convenience copy.

Target folder URL:
- `https://drive.google.com/drive/folders/1cdH73aeWo_bAbxKPtuSa_C6P1TlAe27B`

## Inputs
Read:
- `reports/mt5_autotrade_phase1/excel/gdrive_stage_latest.json`

This file contains:
- `stagedPath`
- `filename`

## Do exactly this
1. Use `browser tabs` with:
   - profile: `chrome`
2. Find a connected tab whose URL is the target Drive folder URL.
3. If no such Drive tab exists, **skip the upload silently** and continue the main workflow.
4. Take a role-based snapshot of that tab.
5. Click the `New` button.
6. Take another role-based snapshot.
7. Click the `File upload` menu item.
8. Use `browser upload` on that same tab with:
   - selector: `input[type=file]`
   - paths: `[stagedPath]`
9. Wait about 7 seconds.
10. Verify once by checking whether the page body contains either:
   - `filename`, or
   - `upload complete`
11. If verification succeeds, continue.
12. If verification does not succeed, treat it as a **warning only**, do not retry in a loop, and continue the main workflow.

## Hard rules
- Do not create folders.
- Do not rename files.
- Do not retry more than once.
- Do not fail the MT5 cycle if upload is skipped or verification is inconclusive.
- Keep this best-effort and quiet.
