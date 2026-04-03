# Cron Prompt — MT5 FX Phase 1 (screen -> deep analysis -> one paper trade)

Run the phase-1 MT5 FX autotrade pipeline once, then post the result to the MT5 trades thread.

## Goal
- Consume the latest **fresh** MT5_FRX screener report.
- Select the first candidate that passes predefined criteria.
- Produce MT5-native deep analysis + trade ticket.
- Enforce one trade per screener session.
- If executable, emit exactly one paper MT5 trade package.
- Post a transparent result in the MT5 trades Discord thread.

## Do exactly this
1. In `C:\Users\anmar\.openclaw\workspace-mt5`, run:
   - `python scripts\mt5_fx_autotrade_phase1.py`
2. Then run:
   - `python scripts\format_mt5_phase1_report.py`
3. Send the formatter output with `message` tool to:
   - channel: `discord`
   - to: `channel:1489519869962752000`
4. No extra commentary.
5. After successful send, reply `NO_REPLY`.

## Failure handling
- If the phase1 script fails because the expected screener report is missing/not fresh, send a short failure note to the same thread saying the screener report was not ready and investigation is required.
- If the phase1 script runs but results in `skipped` or `rejected`, still send the formatted report output.
- Then reply `NO_REPLY`.
