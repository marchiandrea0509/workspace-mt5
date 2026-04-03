# MT5 Runtime Guardrails

Use this file to keep the MT5 agent from drifting into stale one-off artifacts.

## Authoritative vs non-authoritative

### Authoritative startup sources
Read these first and trust them first:
1. `PROJECT_STATE.md`
2. `SESSION_START.txt`
3. `docs/MT5_AGENT_TRANSFER_PACK_2026-03-29.md`
4. `docs/MT5_OANDA_PAPER_BRIDGE_STATUS.md`
5. `docs/MT5_OANDA_PAPER_BRIDGE_PLAN.md`

### Non-authoritative scratch areas
Treat these as temporary, optional, and per-task only:
- `tmp/`
- ad-hoc comparison scripts
- one-off JSON dumps
- individual `reports/mt5_autotrade_phase1/ticket_*.json` files
- old session artifacts created for a single investigation

Do **not** assume files in those areas exist unless you just created them in the current task.
Do **not** use missing scratch files as a reason to keep looping.

## Runtime rules

- If a user asks a simple question, answer from durable docs/state first.
- Do not inspect `tmp/` unless the task explicitly needs a scratch artifact.
- Do not read individual historical ticket JSON files unless the user explicitly asks for that specific ticket or report.
- If a referenced scratch file is missing, stop and say it is missing; do not keep searching for variations.
- Prefer short bounded replies over long exploratory runs in Discord.
- If the current turn depends on a file you cannot find quickly, summarize what is known and ask the minimum follow-up question.

## Discord behavior

- Keep answers concise and final.
- Avoid long multi-file investigations unless the user explicitly asks for a deep dive.
- Do not start by replaying an old investigation chain just because related scratch files exist in the workspace.

## Current problem to avoid

The mt5 room previously got stuck chasing stale temp/report paths such as scratch files under `tmp/` and historical phase1 ticket JSONs. Treat that as a failure mode to avoid.
