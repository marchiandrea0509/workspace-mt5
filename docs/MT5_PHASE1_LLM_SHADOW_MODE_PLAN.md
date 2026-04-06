# MT5 Phase1 LLM Shadow Mode Plan

## Goal
Introduce an LLM-based deep-analysis planner for MT5 Phase1 while keeping deterministic validation/execution in front of the bridge.

## Architecture
1. **Deterministic pack builder**
   - Screener winner dashboard export
   - MT5 symbol metadata
   - MT5 H4/D1 OHLCV export
   - Account/risk/execution constraints
2. **LLM planner**
   - Reads structured JSON pack
   - Produces human-readable analysis + machine-readable JSON trade plan
3. **Deterministic validator / executor**
   - Validates lot step, min lot, max margin, shared TP/SL package constraints, trailing constraints, and symbol tradability
   - Converts valid plan into bridge ticket
4. **Shadow comparison**
   - Run current script plan and LLM plan side by side for the same winner
   - Compare levels, bias, orderability, sizing, and actual outcomes

## Confirmed EA / bridge constraints
Confirmed from `mt5_bridge/GrayPaperBridgeEA.mq5` and `scripts/emit_mt5_bridge_ticket.py`:
- Multi-leg package supported (`MAX_TICKET_ENTRIES = 8`)
- Trailing supported (`price`, `percent`, `atr` distance modes)
- Shared live stop-loss across package
- Shared live take-profit across package
- Shared trailing configuration across package
- Package config supports cancel-other-on-fill behavior

## New artifacts
- Prompt: `prompts/phase1_llm_trade_planner.md`
- Pack builder: `scripts/build_mt5_phase1_llm_pack.py`

## Recommended next implementation steps
1. Build exact dashboard parity for all fields needed by the planner
2. Add `phase1_llm_shadow.py` that:
   - builds the pack
   - calls the planner prompt
   - saves planner JSON + markdown report
3. Add deterministic validator that converts planner JSON into current bridge ticket schema
4. Compare script vs LLM outputs during paper trading before promoting LLM planning to primary

## Likely user-side action needed
To reproduce the TradingView dashboard exactly, add any still-missing dashboard fields as exportable screener columns (or provide formulas if TradingView cannot export them directly), especially:
- `01 Signal Dir`
- `10 Conviction State`
- `23 Tactical Trend Score`
- winner attribution block (`A1..A16` if required)
- any dashboard-only fields such as `FVG State`, `EMA Trend`, `VWAP20`, `Dist To Sup`, `Life L / S`, if they are needed for parity
