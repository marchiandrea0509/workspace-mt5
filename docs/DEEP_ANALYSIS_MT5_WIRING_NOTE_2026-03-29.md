# Deep Analysis -> MT5 Wiring Note

## Goal
Wire the single-asset deep-analysis planner into the MT5/OANDA paper bridge so that screened opportunities can become executable MT5 paper tickets when the plan is actually placeable.

## Recommended chain
1. OANDA screener selects candidate(s)
2. Deep analysis planner runs on the selected asset
3. Planner returns structured report + `orderability_decision`
4. A translator converts approved orders into `mt5.paper.v1` ticket JSON
5. `emit_mt5_bridge_ticket.py` writes ticket(s) into `gray_bridge\\inbox`
6. `GrayPaperBridgeEA` executes on paper and writes result JSON to outbox

## Critical gating rule
Never translate a plan into MT5 execution unless the deep-analysis report says one of:
- `placeable_now`
- `placeable_conditional_only`

If the planner says `not_placeable_yet`, the MT5 layer should stop and record a no-trade result.

## Execution mapping proposal

### If `placeable_now`
Possible mapping:
- if planner order is `MARKET` -> create one market ticket
- if planner order is pending-style but still considered executable now -> either place pending orders directly or require a translator rule for whether to convert to market

### If `placeable_conditional_only`
Map directly to MT5 pending orders:
- ladder limits -> separate MT5 limit tickets or one-at-a-time ticket emission, depending on current bridge capability
- stop entry / breakout / breakdown -> MT5 stop pending order(s)

### If `not_placeable_yet`
Do not emit MT5 tickets.
Write a planning artifact only.

## Important bridge constraint
Current MT5 bridge reality:
- paper-only
- current v1 execution path is narrow
- helper validates exactly one entries[] object in practice
- multi-level ladders have been emulated by sending separate tickets

So the translator should initially do this:
- take planner orders
- emit one MT5 bridge ticket per planned order level
- preserve shared SL / TP / trailing logic where possible

## Minimum field mapping

From planner report -> MT5 bridge ticket:
- `symbol`
- `direction` -> `side`
- planner order type -> bridge `order_plan` + `entry_type`
- order price -> entry `price`
- size / risk result -> `volume_lots` after MT5 sizing translation
- `disaster_sl` -> `stop_loss.price`
- `tp1` or selected target -> `take_profit.price`
- optional trailing block -> bridge `trailing`
- context summary -> `strategy_context`
- planner decision note -> `note`

## Practical first implementation

### v1 safe translator target
- only translate the first approved planner order
- only paper mode
- only symbols already proven or verified tradable in MT5/OANDA
- preserve the existing bridge discipline rather than pretending ladder support is richer than it is

### v2 later
- support multiple planner order rows
- emit sibling MT5 tickets for ladders
- add plan-to-ticket audit logging
- add post-execution reconciliation back into the MT5 project memory

## Suggested deliverables for the MT5 project
1. `deep_analysis/scripts/plan_to_mt5_ticket.py`
2. `deep_analysis/config/plan_to_mt5_mapping_v1.yaml`
3. `deep_analysis/docs/PLAN_TO_MT5_EXECUTION_RULES.md`
4. optional command wrapper that runs:
   - screener winner selection
   - deep analysis
   - gate on orderability
   - ticket emission to MT5 bridge

## Hard safety rule
Do not let the planner's narrative override bridge safety.
The bridge should still enforce:
- paper-only mode
- broker-normalized symbol/price handling
- risk gating
- current single-entry bridge limitation unless explicitly extended

## Short verdict
The deep-analysis tool is already the correct decision engine. The missing piece is a disciplined translator into MT5 bridge ticket JSON, not a redesign of the planner itself.
