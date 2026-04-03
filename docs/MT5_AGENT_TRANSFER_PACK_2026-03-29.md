# MT5 Agent Transfer Pack

_Last prepared: 2026-03-29_

## 1) What this project is

This project is the **MT5/OANDA paper-trading execution bridge** for Gray. The goal is to let Gray turn a structured discretionary trade ticket into broker-native MT5 paper orders with SL/TP handling and EA-managed trailing.

This became the preferred execution path after the earlier Pionex route proved unreliable for direct execution. MT5/OANDA is now the preferred long-term route because it fits chat-origin discretionary tickets better, especially for laddered entries and explicit risk structure. Source: `memory/2026-03-26.md`, `MEMORY.md`.

## 2) Authoritative paths

### Workspace-side canonical paths
- Pointer to real MT5 data root:
  - `mql5/MQL5`
- Bridge blueprint:
  - `data_pipeline/docs/MT5_OANDA_PAPER_BRIDGE_PLAN.md`
- Current status / milestone log:
  - `data_pipeline/docs/MT5_OANDA_PAPER_BRIDGE_STATUS.md`
- Ticket schema:
  - `data_pipeline/config/mt5_bridge_ticket.schema.json`
- Result schema:
  - `data_pipeline/config/mt5_bridge_result.schema.json`
- Host emitter:
  - `data_pipeline/scripts/emit_mt5_bridge_ticket.py`
- Health check:
  - `data_pipeline/scripts/check_mt5_bridge_health.ps1`
- Restart/reload helper:
  - `data_pipeline/scripts/reload_mt5_bridge.ps1`
- Git-persistent EA mirror:
  - `data_pipeline/mt5_bridge/GrayPaperBridgeEA.mq5`

### Real live MT5 data root
- `C:\Users\anmar\AppData\Roaming\MetaQuotes\Terminal\47AEB69EDDAD4D73097816C71FB25856\MQL5`

### Live EA files inside terminal data root
- `MQL5\Experts\Gray\GrayPaperBridgeEA.mq5`
- `MQL5\Experts\Gray\GrayPaperBridgeEA.ex5`
- `MQL5\Experts\Gray\GrayPaperBridgeEA.compile.log`
- `MQL5\Experts\Gray\GrayPaperBridgeEA.before_trailing_20260328.mq5`
- `MQL5\Experts\Gray\GrayPaperBridgeEA.before_trailing_20260328.ex5`

### Live bridge folders inside terminal
- `MQL5\Files\gray_bridge\inbox`
- `MQL5\Files\gray_bridge\outbox`
- `MQL5\Files\gray_bridge\archive`
- `MQL5\Files\gray_bridge\errors`
- `MQL5\Files\gray_bridge\trailing`
- `MQL5\Files\gray_bridge\trailing_archive`

## 3) Current architecture

### Core operating model
- Gray / host side creates a validated JSON ticket.
- The ticket is written into `gray_bridge\inbox`.
- `GrayPaperBridgeEA` polls the inbox from inside MT5.
- The EA validates, normalizes, and submits the paper order.
- The EA writes a result JSON into `gray_bridge\outbox`.
- The source ticket is moved to `archive` or `errors`.
- If trailing is enabled and accepted, the EA persists a trailing config file for later post-fill management.

### Important current rule
This is still **paper-only** and **v1 intentionally narrow**.

Despite the schema being more flexible, the actual executable v1 bridge currently supports:
- one ticket at a time
- effectively one active entry object per ticket
- market / limit / stop entry types in the schema
- accepted paper pending-order flow
- SL / TP on submission
- EA-managed trailing config persistence

## 4) Ticket and result contract

### Ticket schema highlights
Bridge version must be:
- `mt5.paper.v1`

Required top-level fields:
- `bridge_version`
- `ticket_id`
- `created_at`
- `mode` = `paper`
- `symbol`
- `side` = `buy` or `sell`
- `order_plan` = `market` / `limit_ladder` / `stop_entry`
- `entries`
- `stop_loss`
- `take_profit`

Optional but important:
- `trailing`
- `max_risk_usdt`
- `strategy_context`
- `note`

### Result schema highlights
Required fields include:
- `bridge_version`
- `ticket_id`
- `status`
- `symbol`
- `side`
- `order_plan`
- `executor_mode`
- `timestamp`
- `message`

Important result fields:
- `mt5_order_ids`
- `mt5_position_ids`
- `retcode`
- `retcode_text`
- `normalized_entry`
- `normalized_stop_loss`
- `normalized_take_profit`
- `account`
- `trailing`

## 5) Verified milestones and current truth

### Decision pivot
- Preferred execution path was moved from Pionex/Bybit-style exchange execution to MT5/OANDA paper first. Source: `memory/2026-03-26.md`, `MEMORY.md`.

### Compile and scaffold milestone
- EA compiled successfully.
- Version metadata was cleaned to `1.100`.
- Host-side emitter was added and dry-run tested. Source: `memory/2026-03-27.md`, `data_pipeline/docs/MT5_OANDA_PAPER_BRIDGE_STATUS.md`.

### End-to-end bridge proof
The bridge is now proven end-to-end for the current paper v1 flow.

Observed progression:
1. First live smoke tests showed the EA was attached and polling, but broker returned `TRADE_RETCODE_TRADE_DISABLED`.
2. Result serialization bug for nullable trailing fields was discovered and fixed.
3. After EA reload, result JSON became valid and trade-allowance flags were confirmed true.
4. After moving to an appropriate instrument / market state, a BTCUSD buy-stop ticket was accepted with `retcode=10009` / `TRADE_RETCODE_DONE`.
5. ETHUSD test proved symbol routing works even while EA is attached to BTCUSD.
6. Trailing config persistence was implemented and an accepted trailing-config ticket created the expected trailing file.

This means the path:
**OpenClaw host -> ticket file -> MT5 EA -> broker request -> result file**
is working for the current single-ticket paper flow. Source: `memory/2026-03-28.md`, `data_pipeline/docs/MT5_OANDA_PAPER_BRIDGE_STATUS.md`.

## 6) Known limitations / quirks

- Paper-only; no live trading approval.
- v1 helper validates exactly one `entries[]` object, even though the schema can describe more.
- Ladder support is only partial in practice: multi-level ladders were emulated by sending separate tickets.
- Trailing config persistence is proven, but full post-fill trailing behavior is not yet fully proven in live market movement.
- Earlier failures with `TRADE_RETCODE_TRADE_DISABLED` were not local JSON/EA wiring failures; they were most likely instrument/market-state timing issues.
- The live EA source is outside the repo in the MT5 terminal data folder, so the tracked mirror copy in `data_pipeline/mt5_bridge/` is important for durability.

## 7) Exact current evidence files

### Workspace examples
- canonical example ticket
- accepted-result example
- smoke-test tickets
- BTC smoke / tight-stop / ladder / ETH / trailing examples

### Live terminal evidence
Observed result files exist for:
- smoke 001 / 002 / 003
- btc smoke
- btc tight
- btc ladder 001 / 002
- eth smoke
- btc trailing test

Archived and error copies also exist under the matching `archive` / `errors` folders.

## 8) Older MT5/MQL5 reference material that should not be lost

These are not the main execution bridge, but they are relevant reference context for MT5 work:
- `tools/mt5_digest.py`
- `tools/digest_mt5_tester_logs.sh`
- older MQL5 tester/debug experts under the real terminal root:
  - `LimitedTestHarness*`
  - `SLTP_ModifyProbe*`
  - `SLTP_InvalidStopsProbe*`
  - `ExitLogProbeEA*`

Important historical lesson from earlier MT5 debugging:
- invalid stop errors were fixed by snapping to `SYMBOL_TRADE_TICK_SIZE` before `NormalizeDouble`, and by tightening diagnostics around stop/freeze/tick-size constraints. This is useful background knowledge even though it is not the main bridge code path now. Source: `MEMORY.md` snapshot notes.

## 9) Best next steps for the new MT5 agent

1. Make this transfer pack and the status doc the first files loaded on startup.
2. Treat `data_pipeline/mt5_bridge/GrayPaperBridgeEA.mq5` as the durable source-of-truth mirror, but always verify it matches the live EA in the MT5 data folder before edits.
3. Use `check_mt5_bridge_health.ps1` before testing.
4. Use `reload_mt5_bridge.ps1` after EA edits instead of relying on manual restarts.
5. Keep the bridge paper-only until post-fill trailing behavior is also proven.
6. Next meaningful technical milestone: prove actual trailing SL movement after a fill and trigger event.

## 10) Short transfer verdict

The MT5 automation project is real, active, and already beyond scaffold stage. The bridge is **working end-to-end on OANDA paper for the narrow v1 path**. The remaining work is not “does it exist?” but “extend and harden it safely.”
