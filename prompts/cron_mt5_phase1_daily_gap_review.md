# Daily MT5 Phase1 LLM vs Script Gap Review

Review the last 24 hours of Phase1 LLM-vs-script comparison artifacts and summarize the main recurring discrepancies.

## Goal
- Collect daily learning from the gap between the deterministic script and the LLM planner.
- Do **not** auto-modify code in this job.
- Produce a concise actionable review the user can inspect.

## Do exactly this
1. In `C:\Users\anmar\.openclaw\workspace-mt5`, inspect files under:
   - `reports\mt5_autotrade_phase1\llm_shadow\planner_comparison_*.json`
   - `reports\mt5_autotrade_phase1\llm_shadow\planner_validation_*.json`
2. Consider only files from the last 24 hours.
3. Summarize recurring gaps, focusing on:
   - entry-zone differences
   - SL / TP differences
   - risk-usage differences
   - trailing usage differences
   - validation failures / warnings
4. Write a short markdown report to:
   - `reports\mt5_autotrade_phase1\llm_shadow\daily_gap_review_<YYYYMMDD>.md`
5. End the report with:
   - top 3 deterministic changes worth considering next
   - whether script confidence appears to be converging toward the LLM or not
6. Reply with a concise summary only.

## Hard rules
- Do not place trades.
- Do not edit production code in this job.
- If there are no comparison files in the last 24h, say so clearly.
