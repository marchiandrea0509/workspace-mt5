# MT5_OANDA_PAPER_BRIDGE_STATUS

_Last updated: 2026-03-27_

## Current scaffold status
Started the paper-bridge scaffold against the real MT5/OANDA terminal data folder referenced by `mql5/MQL5`.

Verified target:
- Workspace pointer file: `mql5/MQL5`
- Real MT5 folder: `C:\Users\anmar\AppData\Roaming\MetaQuotes\Terminal\47AEB69EDDAD4D73097816C71FB25856\MQL5`

## Implemented so far
1. Canonical bridge ticket schema
   - `data_pipeline/config/mt5_bridge_ticket.schema.json`
2. Canonical bridge result schema
   - `data_pipeline/config/mt5_bridge_result.schema.json`
3. Example paper ticket
   - `data_pipeline/examples/mt5_bridge_ticket.paper.limit.single.example.json`
4. Example accepted result
   - `data_pipeline/examples/mt5_bridge_result.accepted.example.json`
5. MT5 bridge folder scaffold under terminal `MQL5\Files\gray_bridge\`
6. EA scaffold under terminal `MQL5\Experts\Gray\GrayPaperBridgeEA.mq5`
7. Host-side emitter helper
   - `data_pipeline/scripts/emit_mt5_bridge_ticket.py`

## Compile status
The EA is now compiled successfully through MetaEditor.

Current compile result:
- `GrayPaperBridgeEA.ex5` present under `MQL5\Experts\Gray\`
- latest compile log result: `0 errors, 0 warnings`

Note:
- The earlier cosmetic version warning was cleaned up by changing the EA version string to a market-compatible `1.100`.

## v1 execution boundary
Paper-only.

The first EA target is intentionally narrow:
- watch `gray_bridge\inbox\`
- read one JSON ticket
- support exactly one pending order only
- place the order with SL/TP
- write one result JSON into `gray_bridge\outbox\`
- move the original ticket into `archive\` or `errors\`

## Important current design choice
The schema already supports ladders and trailing, but the first executable EA scaffold only processes the first entry and rejects multi-entry execution until that path is explicitly finished and tested.

That keeps the bridge honest: no pretending ladder support exists before the EA really does it.

## Host-side helper usage
Dry-run validation only:

```powershell
python data_pipeline\scripts\emit_mt5_bridge_ticket.py \
  --ticket data_pipeline\examples\mt5_bridge_ticket.paper.limit.single.example.json \
  --dry-run
```

Emit a validated ticket into the real MT5 inbox:

```powershell
python data_pipeline\scripts\emit_mt5_bridge_ticket.py \
  --ticket data_pipeline\examples\mt5_bridge_ticket.paper.limit.single.example.json
```

Emit and wait for a result file:

```powershell
python data_pipeline\scripts\emit_mt5_bridge_ticket.py \
  --ticket data_pipeline\examples\mt5_bridge_ticket.paper.limit.single.example.json \
  --wait-seconds 30
```

## What is still missing
The bridge is **not yet proven end-to-end**.

Remaining milestone:
1. Ensure the EA is attached to a chart in the OANDA paper terminal with Algo Trading enabled.
2. Emit one real paper pending-order ticket into the live inbox.
3. Confirm the outbox result JSON matches the broker outcome.
4. Inspect the paper account/order list manually.
5. Only then extend trailing / partial status / ladder execution.

## Immediate next implementation step
Run the first real single-order paper smoke test once the MT5 terminal is confirmed live with the EA attached.

## 2026-03-28 smoke test update
Executed two real bridge smoke tests against the live OANDA paper terminal.

Observed behavior:
- The attached EA is definitely live and polling `gray_bridge\inbox\`.
- Both tickets were picked up, processed, copied into `errors\`, and result files were written into `outbox\`.
- Broker response for both attempts was `retcode=10017` / `TRADE_RETCODE_TRADE_DISABLED` with terminal log text: `failed buy stop ... [Trade disabled]`.
- This means the host↔EA file bridge loop is proven alive, but broker-side acceptance is not yet proven.

Important implementation note:
- The first smoke test exposed a result-serialization bug in the EA when trailing fields were `null` in the input ticket.
- The EA source was patched to initialize trailing fields safely and emit nullable JSON-compatible values.
- The patched EA recompiled cleanly (`0 errors, 0 warnings`), but the currently attached chart instance has not reloaded yet; MT5 logs still show the old loaded EA session from `10:31`.

Current blocker to the next clean retest:
1. Reload/re-attach the EA (or restart the MT5 terminal) so the running chart picks up the patched build.
2. Re-run the smoke test during a time when the broker allows order placement.

## 2026-03-28 retest after EA reload
A third smoke test was run after the EA was reloaded.

Confirmed:
- The patched EA build is now active; result JSON is valid and parseable.
- Result payload now correctly includes nullable trailing fields plus trade-allowance flags.
- MT5 reports:
  - `account_trade_allowed = true`
  - `terminal_trade_allowed = true`
  - `mql_trade_allowed = true`

Broker outcome is still unchanged:
- ticket status: `rejected`
- retcode: `10017`
- retcode_text: `TRADE_RETCODE_TRADE_DISABLED`
- message: `Trade request failed: Trade disabled`

Interpretation:
- The OpenClaw -> file bridge -> EA -> broker request path is working.
- The remaining blocker is no longer local algo settings or JSON handling.
- The remaining blocker is broker-side trade acceptance, very likely market-closed / trade-disabled timing.

## 2026-03-28 BTC retest on open market
After the EA was attached to `BTCUSD`, a fourth smoke test was run with a far-away BTCUSD buy-stop pending order.

Result:
- status: `accepted`
- retcode: `10009`
- retcode_text: `TRADE_RETCODE_DONE`
- mt5_order_id: `141549112`
- message: `Pending order accepted by GrayPaperBridgeEA`

Meaning:
- The bridge is now proven end-to-end on the paper account.
- Previous EURUSD failures were timing/market-state related, not a local bridge failure.
- Current verified scope remains the narrow v1 path: single pending order with SL/TP, paper-only.

## 2026-03-28 trailing-stop extension
Implemented EA-managed trailing configuration for accepted paper tickets.

New trailing fields supported in ticket JSON:
- `trailing.enabled`
- `trailing.trigger_price` (preferred; legacy alias `activation_price` still accepted)
- `trailing.distance_mode` = `price` | `percent` | `atr`
- `trailing.distance_value`
- `trailing.step_price` (optional, absolute price step for minimum SL improvement)
- `trailing.atr_period` (required for ATR mode)
- `trailing.atr_timeframe` (required for ATR mode)

Behavior:
- Trailing config is persisted under `gray_bridge\trailing\` when the pending order is accepted.
- Once the order fills into a position and the trigger price is reached, the EA will try to move the SL using:
  - absolute asset-price distance, or
  - percent distance from current price, or
  - ATR multiple (`iATR`) on the configured timeframe.
- Broker stop/freeze distance is respected before SL modification.

Current limitation:
- This is still best suited to one active managed position per symbol/magic at a time. Netting-style multi-ticket same-symbol flows can still need a richer position-tracking layer later.
- The new build compiles cleanly, but the attached EA instance must be reloaded/re-attached (or MT5 restarted) before the new trailing logic is active.

Example ticket:
- `data_pipeline/examples/mt5_bridge_ticket.paper.stop.single.btc.trailing.percent.example.json`

## 2026-03-28 robustness automation
Added host-side restart and health-check helpers so Gray no longer has to ask for manual MT5 restarts after every EA edit.

Scripts:
- `data_pipeline/scripts/reload_mt5_bridge.ps1`
  - recompiles the EA
  - stops the current OANDA MT5 terminal process
  - restarts MT5 with profile `Default`
  - waits for a fresh `expert GrayPaperBridgeEA ... loaded successfully` log line
- `data_pipeline/scripts/check_mt5_bridge_health.ps1`
  - reports terminal PID/start time
  - latest compile summary
  - latest EA load/init/processed-ticket log lines
  - inbox/outbox/trailing counts

Live test result:
- automatic restart was executed successfully from the host
- MT5 relaunched and produced a fresh load log line for `GrayPaperBridgeEA`
- current bridge chart/profile can therefore be refreshed without Andrea manually reopening MT5

Repo durability note:
- the live EA source lives under the MT5 data folder outside the workspace, so a tracked mirror copy is now also stored at `data_pipeline/mt5_bridge/GrayPaperBridgeEA.mq5` for Git persistence

## Resume phrase
`continue MT5 bridge`
