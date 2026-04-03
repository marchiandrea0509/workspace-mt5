# MT5_OANDA_PAPER_BRIDGE_PLAN

_Last updated: 2026-03-26_

## Goal
Build a paper-trading execution bridge for MT5 (OANDA) so Gray can turn a structured discretionary trade ticket into broker-native MT5 orders with SL/TP/trailing management.

## Why this route
This is now the preferred execution path because it matches the real goal better than:
- Pionex direct API (blocked for futures execution)
- Pionex Signal Bot workaround (requires TradingView strategy indirection)
- exchange-specific API workarounds

## Execution philosophy
- Gray handles orchestration and ticket generation.
- MT5 EA handles execution and trade management.
- Start on OANDA paper only.
- No live trading until the bridge behaves reliably on paper.

## Real MT5 target
Workspace pointer:
- `mql5/MQL5`

Real MT5 folder:
- `C:\Users\anmar\AppData\Roaming\MetaQuotes\Terminal\47AEB69EDDAD4D73097816C71FB25856\MQL5`

## Planned architecture
### 1) Inbound ticket file
Gray writes a JSON ticket into a watched folder.

Suggested folder:
- `MQL5\Files\gray_bridge\inbox\`

Suggested ticket fields:
- ticket_id
- created_at
- mode (`paper`)
- symbol
- side
- order_plan (`market` | `limit_ladder` | `stop_entry`)
- entries[]
- stop_loss
- take_profit
- trailing
- max_risk_usdt
- note

### 2) EA bridge
EA polls the inbox folder, validates tickets, places orders, and writes back status/results.

Suggested EA responsibilities:
- read new ticket JSON
- validate symbol + price normalization
- enforce broker constraints
- place pending/market orders on paper account
- set SL/TP
- apply trailing logic if configured
- write result JSON to outbox
- move processed tickets to archive

### 3) Outbound status/result files
Suggested folders:
- `MQL5\Files\gray_bridge\outbox\`
- `MQL5\Files\gray_bridge\archive\`
- `MQL5\Files\gray_bridge\errors\`

Suggested result fields:
- ticket_id
- status (`accepted` | `rejected` | `partial` | `filled` | `closed`)
- mt5_order_ids
- mt5_position_ids
- message
- timestamps

## First implementation target
Not a full strategy engine.
Just a minimal proof that the bridge can:
1. read a JSON ticket
2. place one paper pending order with SL/TP
3. write back a result file

## Trailing policy
For paper v1, trailing should be EA-managed rather than assumed broker-native.
That keeps the logic explicit and testable.

## Non-goals for v1
- live account execution
- multi-symbol portfolio logic
- complex scale-out rules
- autonomous strategy generation

## Immediate next build steps
1. create canonical ticket JSON schema/example
2. create bridge folder structure under MT5 Files
3. create EA skeleton in MT5 Experts folder
4. create simple status/result JSON format
5. test with one paper pending order only

## Current rule
Keep this bridge paper-only until the end-to-end loop is proven.
