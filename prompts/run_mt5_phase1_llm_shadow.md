# Run MT5 Phase1 LLM Shadow Mode

Use this prompt in an isolated agent run when you want to generate an LLM trade plan for the current screener winner without executing it.

## Goal
Build the shadow bundle, run the LLM planner on the winner, extract the planner JSON, validate it deterministically, and compare it against the current script plan.

## Efficiency rule
- Use deterministic scripts for all prep / extraction / validation work.
- Reserve stronger reasoning only for the actual trade-plan analysis.
- Do **not** place any trade in this flow.

## Do exactly this
1. In `C:\Users\anmar\.openclaw\workspace-mt5`, run:
   - `python scripts\phase1_llm_shadow.py`
2. Read the latest `reports/mt5_autotrade_phase1/llm_shadow/shadow_bundle_*.json`.
3. Read its `planner_prompt_path` file.
4. Produce the planner result by following that prompt exactly.
5. Save the full planner response as markdown to:
   - `reports/mt5_autotrade_phase1/llm_shadow/planner_response_<SYMBOL>_<STAMP>.md`
6. Extract the fenced JSON block by running:
   - `python scripts\extract_mt5_llm_plan_json.py --input <planner_response_md> --out <planner_json>`
7. Validate the planner JSON by running:
   - `python scripts\validate_mt5_llm_plan.py --plan <planner_json> --pack <pack_path> --out <validation_json>`
8. Compare planner vs script plan by running:
   - `python scripts\compare_mt5_phase1_plans.py --script-plan <script_plan_path> --llm-plan <planner_json> --out <comparison_json>`
9. Reply with a concise summary containing:
   - symbol
   - planner validation result
   - key differences vs script plan
   - whether the planner output is safe enough for manual review

## Hard rules
- Do not place or emit a bridge ticket.
- Do not send Discord messages from this flow unless explicitly asked.
- If validation fails, say so clearly and stop before comparison if the JSON cannot be extracted.
