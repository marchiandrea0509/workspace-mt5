# Cron Prompt — MT5 FX Phase 1 (screen -> deep analysis -> one paper trade)

Run the phase-1 MT5 FX autotrade pipeline once, then post the result to the MT5 trades thread.

## Goal
- Consume latest MT5_FRX screener report.
- Select the first candidate that passes predefined criteria.
- Produce deep analysis + trade ticket.
- Enforce one trade per screener session.
- If executable, emit exactly one paper MT5 ticket.
- Post concise result in the MT5 trades Discord thread.

## Do exactly this
1. In `C:\Users\anmar\.openclaw\workspace-mt5`, run:
   - `python scripts\mt5_fx_autotrade_phase1.py`
2. Read:
   - `C:\Users\anmar\.openclaw\workspace-mt5\reports\mt5_autotrade_phase1\mt5_phase1_latest.json`
3. Build a concise message for Discord thread `channel:1489519869962752000`:
   - Header: `MT5 Phase1 — <result>`
   - Session key
   - Candidate symbol (if any)
   - Orderability decision
   - Planned side / entry / SL / TP2 / lots / risk / margin (if any)
   - Execution status + retcode + order id(s) (if present)
   - If no trade: include first 2 failed-candidate reasons
4. Send with `message` tool to:
   - channel: `discord`
   - to: `channel:1489519869962752000`
5. No extra commentary.
6. After successful send, reply `NO_REPLY`.

## Failure handling
- If the script fails, send a short error message to the same thread with first clear error line.
- Then reply `NO_REPLY`.
