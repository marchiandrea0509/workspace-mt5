# Cron Prompt — MT5 FX Phase 1 (screen -> script plan -> LLM shadow plan -> one paper trade + thread output)

Run the phase-1 MT5 FX autotrade pipeline once, then post both the script result and the LLM shadow-plan output to the MT5 trades thread.

## Goal
- Consume the latest **fresh** MT5_FRX screener report.
- Select the first candidate that passes predefined criteria.
- Produce MT5-native deep analysis + trade ticket.
- If executable, emit exactly one paper MT5 trade package using the current deterministic Phase1 script.
- In parallel, generate the **full LLM planner analysis** for the same winner and compare it to the script plan.
- Post a transparent result in the MT5 trades Discord thread, including:
  - execution summary
  - full manual-prompt-style LLM analysis
  - Phase1_LLM vs Phase1 script comparison

## Do exactly this
1. In `C:\Users\anmar\.openclaw\workspace-mt5`, run:
   - `python scripts\mt5_fx_autotrade_phase1.py`
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
9. Build Discord-safe thread messages:
   - `python scripts\build_mt5_thread_messages.py --phase1-json reports\mt5_autotrade_phase1\mt5_phase1_latest.json --planner-md <planner_response_md> --comparison-json <comparison_json> --validation-json <validation_json> --out <thread_messages_json>`
10. Read `<thread_messages_json>` and send **each** message in order with the `message` tool to:
   - channel: `discord`
   - to: `channel:1489519869962752000`
11. No extra commentary.
12. After successful send, reply `NO_REPLY`.

## Model / efficiency rules
- Use deterministic scripts for prep, extraction, validation, comparison, and formatting.
- Use your own reasoning only for the actual LLM planner analysis.
- Keep the thread output transparent and practical.

## Failure handling
- If the phase1 script fails because the expected screener report is missing/not fresh, send a short failure note to the same thread saying the screener report was not ready and investigation is required.
- If the LLM shadow step fails after the script run succeeds, still send the normal execution summary and add one short note that the LLM shadow/comparison step failed and needs inspection.
- If the phase1 script runs but results in `skipped` or `rejected`, still send the built thread output.
- Then reply `NO_REPLY`.
