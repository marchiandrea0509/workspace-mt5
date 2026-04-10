# Cron Prompt — MT5 FX Phase 1 (screen -> deterministic baseline -> LLM live plan -> one paper trade + thread output)

Run the phase-1 MT5 FX pipeline once, using the deterministic script only as baseline/candidate selection and the validated LLM plan as the live ticket source.

## Goal
- Consume the latest **fresh** MT5_FRX screener report.
- Use the deterministic Phase1 script for candidate selection, baseline analysis, and comparison only.
- Generate the **full LLM planner analysis** for that same final candidate.
- If the LLM plan validates and is executable, emit exactly one paper MT5 trade package using the **validated LLM ticket**, not the deterministic script ticket.
- Post a transparent result in the MT5 trades Discord thread, including:
  - execution summary
  - full manual-prompt-style LLM analysis
  - Phase1_LLM vs Phase1 script comparison

## Do exactly this
1. In `C:\Users\anmar\.openclaw\workspace-mt5`, run the deterministic baseline **without emitting a live trade**:
   - `python scripts\mt5_fx_autotrade_phase1.py --dry-run --force`
2. Read `reports\mt5_autotrade_phase1\mt5_phase1_latest.json`.
3. If it has a valid `candidate` and `report_path`, run the LLM shadow prep for the same symbol/report:
   - `python scripts\phase1_llm_shadow.py --report-json "<report_path>" --symbol <candidate>`
4. Read the newest `reports\mt5_autotrade_phase1\llm_shadow\shadow_bundle_*.json`.
5. Read its `planner_prompt_path` and follow that prompt exactly to produce the LLM planner result.
6. Save the full planner response markdown to:
   - `reports\mt5_autotrade_phase1\llm_shadow\planner_response_<SYMBOL>_<STAMP>.md`
7. Extract and validate the planner JSON:
   - `python scripts\extract_mt5_llm_plan_json.py --input <planner_response_md> --out <planner_json>`
   - `python scripts\validate_mt5_llm_plan.py --plan <planner_json> --pack <pack_path> --out <validation_json>`
8. Compare planner vs script:
   - `python scripts\compare_mt5_phase1_plans.py --script-plan <script_plan_path> --llm-plan <planner_json> --out <comparison_json>`
9. Execute the **validated LLM plan** live as **independent per-leg orders**:
   - `python scripts\execute_mt5_llm_live.py --baseline-json reports\mt5_autotrade_phase1\mt5_phase1_latest.json --planner-json <planner_json> --pack-json <pack_path> --validation-json <validation_json> --planner-md <planner_response_md> --comparison-json <comparison_json>`
10. Build Discord-safe thread messages from the LLM-live result:
   - `python scripts\build_mt5_thread_messages.py --phase1-json reports\mt5_autotrade_phase1\mt5_phase1_llm_live_latest.json --planner-md <planner_response_md> --comparison-json <comparison_json> --validation-json <validation_json> --out <thread_messages_json>`
11. Read `<thread_messages_json>` and send **each** message in order with the `message` tool to:
   - channel: `discord`
   - to: `channel:1489519869962752000`
12. Build the versioned local Excel trade journal:
   - `python scripts\build_trade_journal_excel.py`
13. Read `reports\mt5_autotrade_phase1\excel\MT5_trade_journal_latest.json` and note the workbook path + row counts.
14. Do **not** attempt any Google Drive or browser upload in this workflow stage.
15. No extra commentary.
16. After successful send, reply `NO_REPLY`.

## Model / efficiency rules
- Use deterministic scripts for prep, extraction, validation, comparison, and formatting.
- Use your own reasoning only for the actual LLM planner analysis.
- Keep the thread output transparent and practical.

## Failure handling
- If the deterministic baseline fails because the expected screener report is missing/not fresh, send a short failure note to the same thread saying the screener report was not ready and investigation is required.
- If the LLM shadow / extraction / validation step fails, do **not** place a live trade; send a short note that the baseline ran but the LLM live path failed and needs inspection.
- If the validated LLM plan is not executable, do **not** place a live trade; still send the built thread output.
- If the local Excel journal build fails, report that as a pipeline issue.
- Do not attempt Google Drive/browser upload in this workflow stage; that belongs to a later rollout.
- Then reply `NO_REPLY`.
