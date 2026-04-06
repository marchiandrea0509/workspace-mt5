# MT5 Phase1 LLM Trade Planner — v1

Use this prompt with a single structured JSON pack produced by `scripts/build_mt5_phase1_llm_pack.py`.

## Role
You are a quant trading analyst building a practical, risk-aware swing trade plan for the next 1 to 10 trading days.

## Primary Rule
**PRICE FIRST, CONTEXT SECOND.**
Use MT5 chart-data export as the primary source of truth. Use the screener dashboard only as a contextual interpreter of the winning setup.

## Input
You will receive exactly one JSON object with these top-level keys:
- `market`
- `report_source`
- `account_limits`
- `execution_constraints`
- `mt5_symbol_profile`
- `screener_dashboard`
- `chart_data`
- `planner_contract`

## Hard execution constraints
Treat these as hard constraints, not suggestions:
- Multi-leg orders are allowed.
- Max legs per package: **8**.
- Trailing is supported by the current EA/bridge.
- One live TP per leg is allowed, but the current MT5 bridge package uses **shared live TP/SL/trailing rules across all legs in the package**.
- Therefore, if you output a multi-leg ticket, all legs must share the same live stop-loss, live take-profit, and trailing rule set.
- Size from stop distance.
- Do not exceed the total risk budget.
- Do not exceed the total margin cap.
- Infer lot rules from `mt5_symbol_profile`.

## Lookback windows
Use exactly these chart windows from the pack:
- `chart_data.H4.bars`: **350 bars**
- `chart_data.D1.bars`: **260 bars**

## Analysis rules
1. Use MT5 OHLCV export as the main source of truth for:
   - market structure
   - trend
   - support / resistance
   - volatility regime
   - stretch / extension
   - breakout or rejection zones
   - stop placement logic
2. Use the screener dashboard to interpret:
   - winning setup family
   - conviction / signed conviction
   - macro direction
   - trend direction
   - deterministic support / resistance context
   - tactical continuation / mean reversion context
3. If dashboard and MT5 structure disagree materially, say so explicitly, lower confidence, and prefer WAIT unless orderability remains very clear.
4. Do not invent precise levels not visible or reasonably inferable from the chart data.
5. If exported data are unclear, say so explicitly and reduce confidence.
6. Prefer one main setup and at most one backup setup.
7. Be decisive and execution-oriented.
8. If the winner is not actually tradeable now, say **WAIT** clearly.
9. Use lots as the executable truth. Derived units/notional may be estimated from MT5 symbol metadata.

## Required human-readable output
Use exactly these sections:

## 1) Screener Read
Briefly summarize:
- winning side and setup family
- what the dashboard is saying
- the main scoring components contributing to the winner
- whether MT5 chart data agrees with the screener winner

## 2) Market State
State briefly:
- 1D trend: bullish / bearish / neutral
- 4H trend: bullish / bearish / neutral
- alignment: aligned / mixed
- volatility regime: low / normal / high
- setup type: continuation / pullback / mean reversion / countertrend / breakout / breakdown

## 3) Key Levels
Provide:
- current price area
- nearest tactical support levels
- nearest tactical resistance levels
- higher-timeframe support if visible
- higher-timeframe resistance if visible
Order them nearest to farthest.

## 4) Trade Quality
Classify as exactly one:
- GOOD MARKET + GOOD ENTRY
- GOOD MARKET + BAD ENTRY
- NOT A GOOD TRADE YET
Then explain why in 3 to 6 lines.

## 5) Primary Trade Plan
Provide exactly one preferred setup with:
- Bias: LONG / SHORT / WAIT
- Entry method: market / ladder limits / stop-entry
- Execution style: AUTO / DIP_LADDER / BREAKOUT / SELL_RALLY / BREAKDOWN
- Entry zone or trigger
- Stop loss / invalidation
- TP
- trailing stop logic
- brief R:R comment

## 6) Orderability Decision
Classify as exactly one:
- PLACEABLE_NOW
- PLACEABLE_CONDITIONAL_ONLY
- NOT_PLACEABLE_YET
Then state clearly:
- Market order now: YES / NO
- Ladder limit orders allowed now: YES / NO
- Stop-entry orders allowed now: YES / NO
If YES, specify the exact entry zone or trigger logic.
If NO, write:
- no resting order yet

## 7) Backup Plan
Only if valid. Give at most one backup setup.

## 8) Risk Sizing
Use the provided total risk budget of **100 USD per total trade**.
Never exceed the margin cap.
Size from stop distance.
Keep execution realistic for the product.

## 9) Trade Plan Ticket
Provide a table with:
- order level
- order type
- entry price
- notional size in $
- quantity / units estimate
- lots
- stop loss
- effective loss at stop $ (sum across the package)
- TP with estimated profit $ and R:R
- trailing stop logic
- trigger
- trailing distance
Also state:
- effective risk budget used
- total planned risk
- total margin implication
- short note if margin is too tight

## 10) Final Verdict
End with this exact block:

Final verdict:
- Bias:
- Best setup:
- Orderability:
- Confidence: <0 to 100>
- What would invalidate the idea:
- What I should do now:

## Required machine-readable JSON block
After the human-readable analysis, output one fenced JSON block only.
Use this exact top-level structure:

```json
{
  "screener_read": {},
  "market_state": {},
  "key_levels": {},
  "trade_quality": {},
  "primary_plan": {},
  "orderability": {},
  "backup_plan": null,
  "risk_sizing": {},
  "trade_plan_ticket": {},
  "final_verdict": {},
  "validator_hints": {}
}
```

### JSON requirements
- `primary_plan.bias`: `LONG` | `SHORT` | `WAIT`
- `primary_plan.entry_method`: `market` | `ladder_limits` | `stop_entry`
- `primary_plan.execution_style`: `AUTO` | `DIP_LADDER` | `BREAKOUT` | `SELL_RALLY` | `BREAKDOWN`
- `orderability.classification`: `PLACEABLE_NOW` | `PLACEABLE_CONDITIONAL_ONLY` | `NOT_PLACEABLE_YET`
- `trade_plan_ticket.legs` must be an array of 0..8 legs
- each leg must include: `level`, `order_type`, `entry_price`, `lots`, `units_estimate`, `notional_usd_estimate`
- `trade_plan_ticket.shared_stop_loss_price` is required if any legs exist
- `trade_plan_ticket.shared_take_profit_price` is required if any legs exist
- `trade_plan_ticket.trailing` must describe one shared trailing rule set for the package
- `risk_sizing.total_risk_usd` and `risk_sizing.total_margin_usd_estimate` are required
- `validator_hints` should state whether the plan is executable under the shared TP/SL/trailing package constraint

## Style rules
- Be concise, practical, and decision-oriented.
- Prefer levels and numbers.
- Do not overload with theory.
- If the setup is weak, say so directly.
- If waiting is best, say **WAIT** clearly.

---
INPUT PACK (JSON)
---

```json
{
  "pack_version": "mt5.phase1.llm.v1",
  "generated_at_utc": "2026-04-06T11:42:05.941358Z",
  "report_source": {
    "path": "C:\\Users\\anmar\\.openclaw\\workspace\\tradingview\\reports\\pine_screener\\pine_screener_2026-04-06T11-40-44-290Z.json",
    "generated_at": "2026-04-06T11:41:57.700Z",
    "watchlist": "MT5_FRX",
    "indicator": "OC Hybrid Edge Screener v6",
    "timeframe": "4 hours",
    "row_count": 42,
    "winner_rank": 1
  },
  "market": {
    "symbol": "EURGBP",
    "description": "EUR/GBP",
    "exchange": "MT5 OANDA",
    "horizon_trading_days": 5,
    "direction_bias": "LONG",
    "winner_family": "CONTINUATION",
    "preferred_execution_style": "DIP_LADDER"
  },
  "account_limits": {
    "risk_budget_usd_total_trade": 100.0,
    "max_margin_usd_total_trade": 1500.0
  },
  "execution_constraints": {
    "multi_leg_allowed": true,
    "max_legs": 8,
    "one_live_tp_per_leg": true,
    "shared_live_sl_across_legs": true,
    "shared_live_tp_across_legs": true,
    "shared_trailing_rules_across_legs": true,
    "trailing_supported_by_ea": true,
    "allowed_entry_methods": [
      "market",
      "ladder_limits",
      "stop_entry"
    ],
    "allowed_execution_styles": [
      "AUTO",
      "DIP_LADDER",
      "BREAKOUT",
      "SELL_RALLY",
      "BREAKDOWN"
    ],
    "sizing_basis": "size from stop distance; do not exceed total risk budget or total margin cap",
    "lot_rules_source": "infer from MT5 symbol metadata"
  },
  "mt5_symbol_profile": {
    "root_symbol": "EURGBP",
    "analysis_symbol": "EURGBP.pro",
    "execution_symbol": "EURGBP.pro",
    "path": "PRO\\FX\\Major\\EURGBP.pro",
    "trade_mode": "FULL",
    "trade_mode_code": 4,
    "digits": 5,
    "point": 1e-05,
    "volume_min": 0.01,
    "volume_step": 0.01,
    "volume_max": 50.0,
    "contract_size": 100000.0,
    "currency_base": "EUR",
    "currency_profit": "GBP",
    "currency_margin": "EUR",
    "quote_to_usd": 1.32398,
    "margin_to_usd": 1.154505,
    "units_per_1_lot_estimate": 100000.0,
    "units_note": "For FX this is typically base units per lot. For CFDs/other products, treat lots as executable truth and units as an estimate only."
  },
  "screener_dashboard": {
    "raw_row": {
      "Symbol": "EURGBP",
      "Description": "EUR/GBP",
      "01 Signal Dir": "0",
      "02 Best Setup Code": "2",
      "03 Best Score": "75.82907699439424",
      "04 Final Long Score": "75.82907699439424",
      "05 Final Short Score": "31.787208865994685",
      "06 Long Continuation": "79.82907699439424",
      "07 Short Continuation": "39.52775816172724",
      "08 Long MeanRev": "65.41279113400532",
      "09 Short MeanRev": "55.787208865994685",
      "10 Conviction State": "3",
      "11 Trend Dir": "1",
      "12 Macro Dir 1D": "1",
      "13 Position State": "0",
      "14 Breakout Dir": "0",
      "15 Retest Dir": "0",
      "16 ADX": "29.318584989082915",
      "17 Rel Volume": "0.5843609937747244",
      "18 Dist Fast EMA ATR": "0.2373474175486855",
      "19 Sweep Dir": "0",
      "20 Displacement Dir": "0",
      "21 PD State": "-1",
      "22 FVG State": "2",
      "23 Tactical Trend Score": "83.4251462268375",
      "24 Tactical Breakout Score": "-6.160890682428008",
      "25 Tactical MeanRev Score": "-11.972876572091938",
      "26 Fresh Struct Shift": "0",
      "27 Verdict State": "2",
      "28 Momentum State": "-1",
      "29 Signed Conviction": "3",
      "30 Break Fresh State": "0",
      "31 Retest Stage": "0",
      "32 Short MR Struct": "100",
      "33 Dist To Resistance %": "0.003176532648333684",
      "34 Zone Count": "5",
      "35 EMA Trend State": "1",
      "36 VWAP20": "0.8721396087755585",
      "37 Dist To Support %": "0.004030870851586025",
      "38 Lifecycle Long Score": "50",
      "39 R1 Above": "0.87479",
      "40 R2 Above": "",
      "41 S1 Below": "0.868505",
      "42 S2 Below": "0.86145",
      "43 Cnt Res Above": "1",
      "44 Cnt Sup Below": "2",
      "45 Cnt Res All": "3",
      "46 Cnt Sup All": "2",
      "47 Lifecycle Short Score": "50",
      "48 Winner Dir": "1",
      "49 Winner Family Code": "2",
      "50 Winner Margin": "44.04186812839956",
      "51 Winner Base Score": "79.82907699439424",
      "52 Winner Penalty": "4",
      "53 Winner Tactical": "72.06131988334191",
      "54 Winner Macro": "93",
      "55 Winner Structure": "70",
      "56 Winner ADX Fit": "93",
      "57 Winner Lifecycle": "50",
      "58 Winner Context Boost": "3",
      "59 Winner Family Edge": "14.416285860388925"
    },
    "top_list_headers": [
      "Symbol",
      "Description",
      "01 Signal Dir",
      "02 Best Setup Code",
      "03 Best Score",
      "04 Final Long Score",
      "05 Final Short Score",
      "06 Long Continuation",
      "07 Short Continuation",
      "08 Long MeanRev",
      "09 Short MeanRev",
      "10 Conviction State",
      "11 Trend Dir",
      "12 Macro Dir 1D",
      "13 Position State",
      "14 Breakout Dir",
      "15 Retest Dir",
      "16 ADX",
      "17 Rel Volume",
      "18 Dist Fast EMA ATR",
      "19 Sweep Dir",
      "20 Displacement Dir",
      "21 PD State",
      "22 FVG State",
      "23 Tactical Trend Score",
      "24 Tactical Breakout Score",
      "25 Tactical MeanRev Score",
      "26 Fresh Struct Shift",
      "27 Verdict State",
      "28 Momentum State",
      "29 Signed Conviction",
      "30 Break Fresh State",
      "31 Retest Stage",
      "32 Short MR Struct",
      "33 Dist To Resistance %",
      "34 Zone Count",
      "35 EMA Trend State",
      "36 VWAP20",
      "37 Dist To Support %",
      "38 Lifecycle Long Score",
      "39 R1 Above",
      "40 R2 Above",
      "41 S1 Below",
      "42 S2 Below",
      "43 Cnt Res Above",
      "44 Cnt Sup Below",
      "45 Cnt Res All",
      "46 Cnt Sup All",
      "47 Lifecycle Short Score",
      "48 Winner Dir",
      "49 Winner Family Code",
      "50 Winner Margin",
      "51 Winner Base Score",
      "52 Winner Penalty",
      "53 Winner Tactical",
      "54 Winner Macro",
      "55 Winner Structure",
      "56 Winner ADX Fit",
      "57 Winner Lifecycle",
      "58 Winner Context Boost",
      "59 Winner Family Edge"
    ],
    "reproducible_dashboard_fields": [
      "01 Signal Dir",
      "02 Best Setup Code",
      "03 Best Score",
      "04 Final Long Score",
      "05 Final Short Score",
      "06 Long Continuation",
      "07 Short Continuation",
      "08 Long MeanRev",
      "09 Short MeanRev",
      "10 Conviction State",
      "11 Trend Dir",
      "12 Macro Dir 1D",
      "13 Position State",
      "14 Breakout Dir",
      "15 Retest Dir",
      "16 ADX",
      "17 Rel Volume",
      "18 Dist Fast EMA ATR",
      "19 Sweep Dir",
      "20 Displacement Dir",
      "21 PD State",
      "22 FVG State",
      "23 Tactical Trend Score",
      "24 Tactical Breakout Score",
      "25 Tactical MeanRev Score",
      "26 Fresh Struct Shift",
      "27 Verdict State",
      "28 Momentum State",
      "29 Signed Conviction",
      "30 Break Fresh State",
      "31 Retest Stage",
      "32 Short MR Struct",
      "33 Dist To Resistance %",
      "34 Zone Count",
      "35 EMA Trend State",
      "36 VWAP20",
      "37 Dist To Support %",
      "38 Lifecycle Long Score",
      "39 R1 Above",
      "40 R2 Above",
      "41 S1 Below",
      "42 S2 Below",
      "43 Cnt Res Above",
      "44 Cnt Sup Below",
      "45 Cnt Res All",
      "46 Cnt Sup All",
      "47 Lifecycle Short Score",
      "48 Winner Dir",
      "49 Winner Family Code",
      "50 Winner Margin",
      "51 Winner Base Score",
      "52 Winner Penalty",
      "53 Winner Tactical",
      "54 Winner Macro",
      "55 Winner Structure",
      "56 Winner ADX Fit",
      "57 Winner Lifecycle",
      "58 Winner Context Boost",
      "59 Winner Family Edge"
    ],
    "legend": {
      "best_setup": "+1/-1 mean reversion, +2/-2 continuation, +3/-3 breakout-led, 0 no valid setup",
      "conviction": "0 weak, 1 decent, 2 strong, 3 very strong",
      "directional_states": "Trend Dir / Macro 1D / Breakout / Retest / Sweep Dir / Disp Dir / Fresh Struct / Momentum / Signed Conv: positive bullish, negative bearish, 0 neutral",
      "pd_state": "positive = discount, negative = premium",
      "verdict": "+2 strong long, +1 long, 0 neutral, -1 short, -2 strong short",
      "position": "structural context such as support/resistance touch, breakout, retest, or neutral",
      "break_fresh": "recent breakout memory state, not breakout on current bar; +2/-2 very fresh, +1/-1 fresh, 0 none",
      "retest_stage": "signed post-break lifecycle; +1/-1 waiting retest, +2/-2 retest touched, +3/-3 retest confirmed, +4/-4 retest failed, 0 none",
      "short_mr_struct": "structural quality for short mean reversion; higher = better nearby resistance for short fade",
      "winner_family_code": "0 none, 1 mean reversion, 2 continuation, 3 breakout-led",
      "winner_attribution": "Winner Dir / Margin / Base / Penalty / Tactical / Macro / Structure / ADX Fit / Lifecycle / Context Boost / Family Edge explain why the final winner side-family combination won the screener comparison"
    }
  },
  "chart_data": {
    "source_of_truth": "MT5 exported OHLCV + MT5 symbol metadata",
    "lookback_windows": {
      "H4_bars": 350,
      "D1_bars": 260
    },
    "H4": {
      "timeframe": "H4",
      "bars": [
        {
          "time": 1768550400,
          "open": 0.86767,
          "high": 0.86781,
          "low": 0.86607,
          "close": 0.8663,
          "tick_volume": 16764.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-16T08:00:00Z"
        },
        {
          "time": 1768564800,
          "open": 0.8663,
          "high": 0.86736,
          "low": 0.86625,
          "close": 0.86716,
          "tick_volume": 22395.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-16T12:00:00Z"
        },
        {
          "time": 1768579200,
          "open": 0.86718,
          "high": 0.86766,
          "low": 0.86641,
          "close": 0.86665,
          "tick_volume": 27930.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-16T16:00:00Z"
        },
        {
          "time": 1768593600,
          "open": 0.86665,
          "high": 0.86728,
          "low": 0.86638,
          "close": 0.867,
          "tick_volume": 8510.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-16T20:00:00Z"
        },
        {
          "time": 1768766400,
          "open": 0.86703,
          "high": 0.86785,
          "low": 0.86691,
          "close": 0.86754,
          "tick_volume": 1367.0,
          "spread": 28.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-18T20:00:00Z"
        },
        {
          "time": 1768780800,
          "open": 0.86746,
          "high": 0.86828,
          "low": 0.86701,
          "close": 0.86785,
          "tick_volume": 26656.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-19T00:00:00Z"
        },
        {
          "time": 1768795200,
          "open": 0.86786,
          "high": 0.86856,
          "low": 0.86773,
          "close": 0.86784,
          "tick_volume": 15162.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-19T04:00:00Z"
        },
        {
          "time": 1768809600,
          "open": 0.86784,
          "high": 0.86861,
          "low": 0.86666,
          "close": 0.86682,
          "tick_volume": 20154.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-19T08:00:00Z"
        },
        {
          "time": 1768824000,
          "open": 0.86683,
          "high": 0.86751,
          "low": 0.86681,
          "close": 0.86733,
          "tick_volume": 14197.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-19T12:00:00Z"
        },
        {
          "time": 1768838400,
          "open": 0.86734,
          "high": 0.8674,
          "low": 0.86661,
          "close": 0.86719,
          "tick_volume": 12112.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-19T16:00:00Z"
        },
        {
          "time": 1768852800,
          "open": 0.86718,
          "high": 0.86797,
          "low": 0.86714,
          "close": 0.86764,
          "tick_volume": 3890.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-19T20:00:00Z"
        },
        {
          "time": 1768867200,
          "open": 0.86743,
          "high": 0.86759,
          "low": 0.86725,
          "close": 0.86744,
          "tick_volume": 10871.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-20T00:00:00Z"
        },
        {
          "time": 1768881600,
          "open": 0.86744,
          "high": 0.86861,
          "low": 0.86734,
          "close": 0.8685,
          "tick_volume": 13313.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-20T04:00:00Z"
        },
        {
          "time": 1768896000,
          "open": 0.8685,
          "high": 0.8705,
          "low": 0.86699,
          "close": 0.87026,
          "tick_volume": 31419.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-20T08:00:00Z"
        },
        {
          "time": 1768910400,
          "open": 0.87026,
          "high": 0.87315,
          "low": 0.87016,
          "close": 0.87082,
          "tick_volume": 37514.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-20T12:00:00Z"
        },
        {
          "time": 1768924800,
          "open": 0.8708,
          "high": 0.87243,
          "low": 0.87059,
          "close": 0.87231,
          "tick_volume": 28446.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-20T16:00:00Z"
        },
        {
          "time": 1768939200,
          "open": 0.87232,
          "high": 0.87252,
          "low": 0.87161,
          "close": 0.87171,
          "tick_volume": 13885.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-20T20:00:00Z"
        },
        {
          "time": 1768953600,
          "open": 0.87219,
          "high": 0.87256,
          "low": 0.87181,
          "close": 0.87225,
          "tick_volume": 11488.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-21T00:00:00Z"
        },
        {
          "time": 1768968000,
          "open": 0.87225,
          "high": 0.87255,
          "low": 0.87174,
          "close": 0.87254,
          "tick_volume": 11440.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-21T04:00:00Z"
        },
        {
          "time": 1768982400,
          "open": 0.87256,
          "high": 0.87338,
          "low": 0.8709,
          "close": 0.87318,
          "tick_volume": 22510.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-21T08:00:00Z"
        },
        {
          "time": 1768996800,
          "open": 0.87319,
          "high": 0.87457,
          "low": 0.87145,
          "close": 0.87166,
          "tick_volume": 31870.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-21T12:00:00Z"
        },
        {
          "time": 1769011200,
          "open": 0.87166,
          "high": 0.87204,
          "low": 0.87098,
          "close": 0.8715,
          "tick_volume": 30196.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-21T16:00:00Z"
        },
        {
          "time": 1769025600,
          "open": 0.8715,
          "high": 0.87174,
          "low": 0.86978,
          "close": 0.87004,
          "tick_volume": 17226.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-21T20:00:00Z"
        },
        {
          "time": 1769040000,
          "open": 0.87013,
          "high": 0.87055,
          "low": 0.86954,
          "close": 0.87042,
          "tick_volume": 12999.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-22T00:00:00Z"
        },
        {
          "time": 1769054400,
          "open": 0.87043,
          "high": 0.87088,
          "low": 0.87021,
          "close": 0.8706,
          "tick_volume": 10649.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-22T04:00:00Z"
        },
        {
          "time": 1769068800,
          "open": 0.87061,
          "high": 0.87143,
          "low": 0.86929,
          "close": 0.8697,
          "tick_volume": 18298.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-22T08:00:00Z"
        },
        {
          "time": 1769083200,
          "open": 0.8697,
          "high": 0.8733,
          "low": 0.86933,
          "close": 0.87167,
          "tick_volume": 32213.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-22T12:00:00Z"
        },
        {
          "time": 1769097600,
          "open": 0.87168,
          "high": 0.8717,
          "low": 0.87002,
          "close": 0.87027,
          "tick_volume": 23811.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-22T16:00:00Z"
        },
        {
          "time": 1769112000,
          "open": 0.87027,
          "high": 0.87126,
          "low": 0.87011,
          "close": 0.87064,
          "tick_volume": 11020.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-22T20:00:00Z"
        },
        {
          "time": 1769126400,
          "open": 0.87062,
          "high": 0.87073,
          "low": 0.87031,
          "close": 0.8705,
          "tick_volume": 11937.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-23T00:00:00Z"
        },
        {
          "time": 1769140800,
          "open": 0.8705,
          "high": 0.8709,
          "low": 0.87041,
          "close": 0.87082,
          "tick_volume": 11511.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-23T04:00:00Z"
        },
        {
          "time": 1769155200,
          "open": 0.8708,
          "high": 0.87087,
          "low": 0.86675,
          "close": 0.86749,
          "tick_volume": 26860.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-23T08:00:00Z"
        },
        {
          "time": 1769169600,
          "open": 0.86749,
          "high": 0.86846,
          "low": 0.86725,
          "close": 0.86776,
          "tick_volume": 21361.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-23T12:00:00Z"
        },
        {
          "time": 1769184000,
          "open": 0.86775,
          "high": 0.86785,
          "low": 0.86583,
          "close": 0.86673,
          "tick_volume": 34100.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-23T16:00:00Z"
        },
        {
          "time": 1769198400,
          "open": 0.86673,
          "high": 0.86737,
          "low": 0.86652,
          "close": 0.86677,
          "tick_volume": 16845.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-23T20:00:00Z"
        },
        {
          "time": 1769371200,
          "open": 0.86797,
          "high": 0.86945,
          "low": 0.86713,
          "close": 0.8692,
          "tick_volume": 1620.0,
          "spread": 13.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-25T20:00:00Z"
        },
        {
          "time": 1769385600,
          "open": 0.8695,
          "high": 0.86973,
          "low": 0.86756,
          "close": 0.8682,
          "tick_volume": 28783.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-26T00:00:00Z"
        },
        {
          "time": 1769400000,
          "open": 0.8682,
          "high": 0.86856,
          "low": 0.86765,
          "close": 0.86787,
          "tick_volume": 17725.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-26T04:00:00Z"
        },
        {
          "time": 1769414400,
          "open": 0.86787,
          "high": 0.86808,
          "low": 0.8669,
          "close": 0.8676,
          "tick_volume": 30299.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-26T08:00:00Z"
        },
        {
          "time": 1769428800,
          "open": 0.86759,
          "high": 0.86829,
          "low": 0.86701,
          "close": 0.86763,
          "tick_volume": 25951.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-26T12:00:00Z"
        },
        {
          "time": 1769443200,
          "open": 0.86763,
          "high": 0.86829,
          "low": 0.86683,
          "close": 0.8678,
          "tick_volume": 30401.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-26T16:00:00Z"
        },
        {
          "time": 1769457600,
          "open": 0.8678,
          "high": 0.86879,
          "low": 0.86772,
          "close": 0.86852,
          "tick_volume": 13399.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-26T20:00:00Z"
        },
        {
          "time": 1769472000,
          "open": 0.86857,
          "high": 0.86872,
          "low": 0.86809,
          "close": 0.86841,
          "tick_volume": 14141.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-27T00:00:00Z"
        },
        {
          "time": 1769486400,
          "open": 0.86843,
          "high": 0.86844,
          "low": 0.86763,
          "close": 0.86772,
          "tick_volume": 13948.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-27T04:00:00Z"
        },
        {
          "time": 1769500800,
          "open": 0.86772,
          "high": 0.86807,
          "low": 0.86707,
          "close": 0.8676,
          "tick_volume": 26163.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-27T08:00:00Z"
        },
        {
          "time": 1769515200,
          "open": 0.8676,
          "high": 0.86861,
          "low": 0.86705,
          "close": 0.86735,
          "tick_volume": 36869.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-27T12:00:00Z"
        },
        {
          "time": 1769529600,
          "open": 0.8673,
          "high": 0.86985,
          "low": 0.86713,
          "close": 0.86938,
          "tick_volume": 37727.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-27T16:00:00Z"
        },
        {
          "time": 1769544000,
          "open": 0.86939,
          "high": 0.8717,
          "low": 0.86881,
          "close": 0.86979,
          "tick_volume": 28349.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-27T20:00:00Z"
        },
        {
          "time": 1769558400,
          "open": 0.86979,
          "high": 0.86989,
          "low": 0.86879,
          "close": 0.86915,
          "tick_volume": 21728.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-28T00:00:00Z"
        },
        {
          "time": 1769572800,
          "open": 0.86913,
          "high": 0.8697,
          "low": 0.8683,
          "close": 0.86884,
          "tick_volume": 17111.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-28T04:00:00Z"
        },
        {
          "time": 1769587200,
          "open": 0.86885,
          "high": 0.86962,
          "low": 0.86822,
          "close": 0.86921,
          "tick_volume": 31143.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-28T08:00:00Z"
        },
        {
          "time": 1769601600,
          "open": 0.86921,
          "high": 0.86938,
          "low": 0.86743,
          "close": 0.86771,
          "tick_volume": 29896.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-28T12:00:00Z"
        },
        {
          "time": 1769616000,
          "open": 0.8677,
          "high": 0.86817,
          "low": 0.86535,
          "close": 0.86543,
          "tick_volume": 42346.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-28T16:00:00Z"
        },
        {
          "time": 1769630400,
          "open": 0.86544,
          "high": 0.86659,
          "low": 0.86492,
          "close": 0.86639,
          "tick_volume": 31424.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-28T20:00:00Z"
        },
        {
          "time": 1769644800,
          "open": 0.86603,
          "high": 0.86697,
          "low": 0.86583,
          "close": 0.86686,
          "tick_volume": 23711.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-29T00:00:00Z"
        },
        {
          "time": 1769659200,
          "open": 0.86685,
          "high": 0.86687,
          "low": 0.86582,
          "close": 0.86609,
          "tick_volume": 18980.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-29T04:00:00Z"
        },
        {
          "time": 1769673600,
          "open": 0.86609,
          "high": 0.8665,
          "low": 0.86496,
          "close": 0.86646,
          "tick_volume": 30450.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-29T08:00:00Z"
        },
        {
          "time": 1769688000,
          "open": 0.86646,
          "high": 0.8665,
          "low": 0.86502,
          "close": 0.86574,
          "tick_volume": 32069.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-29T12:00:00Z"
        },
        {
          "time": 1769702400,
          "open": 0.86574,
          "high": 0.86713,
          "low": 0.86564,
          "close": 0.86665,
          "tick_volume": 53406.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-29T16:00:00Z"
        },
        {
          "time": 1769716800,
          "open": 0.86664,
          "high": 0.86712,
          "low": 0.86632,
          "close": 0.8668,
          "tick_volume": 14671.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-29T20:00:00Z"
        },
        {
          "time": 1769731200,
          "open": 0.86674,
          "high": 0.86694,
          "low": 0.86559,
          "close": 0.86605,
          "tick_volume": 29385.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-30T00:00:00Z"
        },
        {
          "time": 1769745600,
          "open": 0.86606,
          "high": 0.86733,
          "low": 0.86588,
          "close": 0.86681,
          "tick_volume": 22003.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-30T04:00:00Z"
        },
        {
          "time": 1769760000,
          "open": 0.86681,
          "high": 0.86754,
          "low": 0.86632,
          "close": 0.86712,
          "tick_volume": 37883.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-30T08:00:00Z"
        },
        {
          "time": 1769774400,
          "open": 0.86712,
          "high": 0.86742,
          "low": 0.86588,
          "close": 0.86661,
          "tick_volume": 37656.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-30T12:00:00Z"
        },
        {
          "time": 1769788800,
          "open": 0.86658,
          "high": 0.86741,
          "low": 0.86551,
          "close": 0.86633,
          "tick_volume": 52190.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-30T16:00:00Z"
        },
        {
          "time": 1769803200,
          "open": 0.86633,
          "high": 0.8668,
          "low": 0.86563,
          "close": 0.86576,
          "tick_volume": 21368.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-30T20:00:00Z"
        },
        {
          "time": 1769976000,
          "open": 0.86518,
          "high": 0.86633,
          "low": 0.86512,
          "close": 0.86578,
          "tick_volume": 2588.0,
          "spread": 11.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-01T20:00:00Z"
        },
        {
          "time": 1769990400,
          "open": 0.86586,
          "high": 0.86713,
          "low": 0.86581,
          "close": 0.86704,
          "tick_volume": 38398.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-02T00:00:00Z"
        },
        {
          "time": 1770004800,
          "open": 0.86704,
          "high": 0.8674,
          "low": 0.86661,
          "close": 0.86678,
          "tick_volume": 26863.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-02T04:00:00Z"
        },
        {
          "time": 1770019200,
          "open": 0.86679,
          "high": 0.8671,
          "low": 0.86518,
          "close": 0.86591,
          "tick_volume": 32896.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-02T08:00:00Z"
        },
        {
          "time": 1770033600,
          "open": 0.86591,
          "high": 0.86627,
          "low": 0.86488,
          "close": 0.86488,
          "tick_volume": 36394.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-02T12:00:00Z"
        },
        {
          "time": 1770048000,
          "open": 0.8649,
          "high": 0.86559,
          "low": 0.86291,
          "close": 0.863,
          "tick_volume": 39990.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-02T16:00:00Z"
        },
        {
          "time": 1770062400,
          "open": 0.86298,
          "high": 0.86317,
          "low": 0.86252,
          "close": 0.86264,
          "tick_volume": 14942.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-02T20:00:00Z"
        },
        {
          "time": 1770076800,
          "open": 0.86287,
          "high": 0.86331,
          "low": 0.86281,
          "close": 0.86315,
          "tick_volume": 13429.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-03T00:00:00Z"
        },
        {
          "time": 1770091200,
          "open": 0.86315,
          "high": 0.86325,
          "low": 0.86235,
          "close": 0.86275,
          "tick_volume": 15125.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-03T04:00:00Z"
        },
        {
          "time": 1770105600,
          "open": 0.86275,
          "high": 0.86351,
          "low": 0.86248,
          "close": 0.86318,
          "tick_volume": 27030.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-03T08:00:00Z"
        },
        {
          "time": 1770120000,
          "open": 0.86318,
          "high": 0.86368,
          "low": 0.86205,
          "close": 0.86263,
          "tick_volume": 27386.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-03T12:00:00Z"
        },
        {
          "time": 1770134400,
          "open": 0.86263,
          "high": 0.86359,
          "low": 0.86199,
          "close": 0.86339,
          "tick_volume": 31727.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-03T16:00:00Z"
        },
        {
          "time": 1770148800,
          "open": 0.86339,
          "high": 0.86348,
          "low": 0.86246,
          "close": 0.86276,
          "tick_volume": 12997.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-03T20:00:00Z"
        },
        {
          "time": 1770163200,
          "open": 0.86283,
          "high": 0.86315,
          "low": 0.86243,
          "close": 0.86291,
          "tick_volume": 14767.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-04T00:00:00Z"
        },
        {
          "time": 1770177600,
          "open": 0.86292,
          "high": 0.86311,
          "low": 0.86248,
          "close": 0.86266,
          "tick_volume": 13536.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-04T04:00:00Z"
        },
        {
          "time": 1770192000,
          "open": 0.86266,
          "high": 0.86288,
          "low": 0.86128,
          "close": 0.8613,
          "tick_volume": 23405.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-04T08:00:00Z"
        },
        {
          "time": 1770206400,
          "open": 0.8613,
          "high": 0.86324,
          "low": 0.86126,
          "close": 0.86323,
          "tick_volume": 27577.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-04T12:00:00Z"
        },
        {
          "time": 1770220800,
          "open": 0.86323,
          "high": 0.86478,
          "low": 0.86302,
          "close": 0.86451,
          "tick_volume": 37306.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-04T16:00:00Z"
        },
        {
          "time": 1770235200,
          "open": 0.86451,
          "high": 0.86503,
          "low": 0.86417,
          "close": 0.86479,
          "tick_volume": 13743.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-04T20:00:00Z"
        },
        {
          "time": 1770249600,
          "open": 0.86484,
          "high": 0.86532,
          "low": 0.86457,
          "close": 0.86526,
          "tick_volume": 13745.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-05T00:00:00Z"
        },
        {
          "time": 1770264000,
          "open": 0.86526,
          "high": 0.86619,
          "low": 0.86501,
          "close": 0.86579,
          "tick_volume": 12955.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-05T04:00:00Z"
        },
        {
          "time": 1770278400,
          "open": 0.8658,
          "high": 0.86936,
          "low": 0.8658,
          "close": 0.86756,
          "tick_volume": 24107.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-05T08:00:00Z"
        },
        {
          "time": 1770292800,
          "open": 0.86756,
          "high": 0.87164,
          "low": 0.86616,
          "close": 0.87155,
          "tick_volume": 45578.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-05T12:00:00Z"
        },
        {
          "time": 1770307200,
          "open": 0.87154,
          "high": 0.87212,
          "low": 0.87047,
          "close": 0.87084,
          "tick_volume": 33946.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-05T16:00:00Z"
        },
        {
          "time": 1770321600,
          "open": 0.87085,
          "high": 0.87099,
          "low": 0.86993,
          "close": 0.87026,
          "tick_volume": 11716.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-05T20:00:00Z"
        },
        {
          "time": 1770336000,
          "open": 0.87052,
          "high": 0.87137,
          "low": 0.87011,
          "close": 0.8702,
          "tick_volume": 17398.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-06T00:00:00Z"
        },
        {
          "time": 1770350400,
          "open": 0.8702,
          "high": 0.87028,
          "low": 0.86905,
          "close": 0.86926,
          "tick_volume": 12784.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-06T04:00:00Z"
        },
        {
          "time": 1770364800,
          "open": 0.86926,
          "high": 0.86944,
          "low": 0.86845,
          "close": 0.86855,
          "tick_volume": 20200.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-06T08:00:00Z"
        },
        {
          "time": 1770379200,
          "open": 0.86856,
          "high": 0.86939,
          "low": 0.86729,
          "close": 0.86862,
          "tick_volume": 21931.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-06T12:00:00Z"
        },
        {
          "time": 1770393600,
          "open": 0.86862,
          "high": 0.86866,
          "low": 0.86761,
          "close": 0.86814,
          "tick_volume": 22639.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-06T16:00:00Z"
        },
        {
          "time": 1770408000,
          "open": 0.86814,
          "high": 0.86836,
          "low": 0.86774,
          "close": 0.8681,
          "tick_volume": 8019.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-06T20:00:00Z"
        },
        {
          "time": 1770580800,
          "open": 0.86876,
          "high": 0.86876,
          "low": 0.86834,
          "close": 0.8686,
          "tick_volume": 593.0,
          "spread": 25.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-08T20:00:00Z"
        },
        {
          "time": 1770595200,
          "open": 0.86866,
          "high": 0.8697,
          "low": 0.8683,
          "close": 0.86883,
          "tick_volume": 18533.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-09T00:00:00Z"
        },
        {
          "time": 1770609600,
          "open": 0.86883,
          "high": 0.87066,
          "low": 0.86876,
          "close": 0.87047,
          "tick_volume": 10742.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-09T04:00:00Z"
        },
        {
          "time": 1770624000,
          "open": 0.87048,
          "high": 0.87265,
          "low": 0.87048,
          "close": 0.87149,
          "tick_volume": 23685.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-09T08:00:00Z"
        },
        {
          "time": 1770638400,
          "open": 0.87153,
          "high": 0.87418,
          "low": 0.86959,
          "close": 0.8735,
          "tick_volume": 34151.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-09T12:00:00Z"
        },
        {
          "time": 1770652800,
          "open": 0.87353,
          "high": 0.87367,
          "low": 0.86987,
          "close": 0.87042,
          "tick_volume": 24610.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-09T16:00:00Z"
        },
        {
          "time": 1770667200,
          "open": 0.87041,
          "high": 0.87061,
          "low": 0.8696,
          "close": 0.87019,
          "tick_volume": 10677.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-09T20:00:00Z"
        },
        {
          "time": 1770681600,
          "open": 0.86983,
          "high": 0.87039,
          "low": 0.86977,
          "close": 0.87004,
          "tick_volume": 13000.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-10T00:00:00Z"
        },
        {
          "time": 1770696000,
          "open": 0.87004,
          "high": 0.87101,
          "low": 0.87,
          "close": 0.87063,
          "tick_volume": 11644.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-10T04:00:00Z"
        },
        {
          "time": 1770710400,
          "open": 0.87063,
          "high": 0.87204,
          "low": 0.87047,
          "close": 0.87157,
          "tick_volume": 18380.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-10T08:00:00Z"
        },
        {
          "time": 1770724800,
          "open": 0.87157,
          "high": 0.87167,
          "low": 0.86862,
          "close": 0.87114,
          "tick_volume": 28631.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-10T12:00:00Z"
        },
        {
          "time": 1770739200,
          "open": 0.87115,
          "high": 0.8718,
          "low": 0.87064,
          "close": 0.8716,
          "tick_volume": 26603.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-10T16:00:00Z"
        },
        {
          "time": 1770753600,
          "open": 0.8716,
          "high": 0.87218,
          "low": 0.87127,
          "close": 0.87171,
          "tick_volume": 9952.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-10T20:00:00Z"
        },
        {
          "time": 1770768000,
          "open": 0.87193,
          "high": 0.87239,
          "low": 0.87183,
          "close": 0.8719,
          "tick_volume": 12732.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-11T00:00:00Z"
        },
        {
          "time": 1770782400,
          "open": 0.87189,
          "high": 0.87197,
          "low": 0.8715,
          "close": 0.87162,
          "tick_volume": 11032.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-11T04:00:00Z"
        },
        {
          "time": 1770796800,
          "open": 0.87162,
          "high": 0.87186,
          "low": 0.86962,
          "close": 0.86979,
          "tick_volume": 18904.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-11T08:00:00Z"
        },
        {
          "time": 1770811200,
          "open": 0.86979,
          "high": 0.87062,
          "low": 0.86832,
          "close": 0.86852,
          "tick_volume": 37926.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-11T12:00:00Z"
        },
        {
          "time": 1770825600,
          "open": 0.86852,
          "high": 0.87116,
          "low": 0.8683,
          "close": 0.87116,
          "tick_volume": 32642.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-11T16:00:00Z"
        },
        {
          "time": 1770840000,
          "open": 0.87117,
          "high": 0.87174,
          "low": 0.87099,
          "close": 0.87151,
          "tick_volume": 9725.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-11T20:00:00Z"
        },
        {
          "time": 1770854400,
          "open": 0.87146,
          "high": 0.87174,
          "low": 0.87099,
          "close": 0.87121,
          "tick_volume": 12733.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-12T00:00:00Z"
        },
        {
          "time": 1770868800,
          "open": 0.8712,
          "high": 0.8714,
          "low": 0.87054,
          "close": 0.87103,
          "tick_volume": 15387.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-12T04:00:00Z"
        },
        {
          "time": 1770883200,
          "open": 0.8711,
          "high": 0.8715,
          "low": 0.87055,
          "close": 0.87086,
          "tick_volume": 18538.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-12T08:00:00Z"
        },
        {
          "time": 1770897600,
          "open": 0.87087,
          "high": 0.87125,
          "low": 0.86951,
          "close": 0.86964,
          "tick_volume": 23304.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-12T12:00:00Z"
        },
        {
          "time": 1770912000,
          "open": 0.86964,
          "high": 0.87171,
          "low": 0.86941,
          "close": 0.87124,
          "tick_volume": 38906.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-12T16:00:00Z"
        },
        {
          "time": 1770926400,
          "open": 0.87124,
          "high": 0.87176,
          "low": 0.87093,
          "close": 0.87166,
          "tick_volume": 9788.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-12T20:00:00Z"
        },
        {
          "time": 1770940800,
          "open": 0.87147,
          "high": 0.87175,
          "low": 0.87126,
          "close": 0.87146,
          "tick_volume": 10696.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-13T00:00:00Z"
        },
        {
          "time": 1770955200,
          "open": 0.87146,
          "high": 0.87215,
          "low": 0.87136,
          "close": 0.87165,
          "tick_volume": 10924.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-13T04:00:00Z"
        },
        {
          "time": 1770969600,
          "open": 0.87166,
          "high": 0.87194,
          "low": 0.87006,
          "close": 0.87069,
          "tick_volume": 17051.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-13T08:00:00Z"
        },
        {
          "time": 1770984000,
          "open": 0.87068,
          "high": 0.87194,
          "low": 0.87024,
          "close": 0.87034,
          "tick_volume": 27476.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-13T12:00:00Z"
        },
        {
          "time": 1770998400,
          "open": 0.87035,
          "high": 0.87109,
          "low": 0.86966,
          "close": 0.86974,
          "tick_volume": 27813.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-13T16:00:00Z"
        },
        {
          "time": 1771012800,
          "open": 0.86974,
          "high": 0.8699,
          "low": 0.86912,
          "close": 0.86927,
          "tick_volume": 10407.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-13T20:00:00Z"
        },
        {
          "time": 1771185600,
          "open": 0.87016,
          "high": 0.87016,
          "low": 0.86971,
          "close": 0.86992,
          "tick_volume": 2611.0,
          "spread": 31.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-15T20:00:00Z"
        },
        {
          "time": 1771200000,
          "open": 0.86974,
          "high": 0.86998,
          "low": 0.86935,
          "close": 0.86978,
          "tick_volume": 11800.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-16T00:00:00Z"
        },
        {
          "time": 1771214400,
          "open": 0.86978,
          "high": 0.86999,
          "low": 0.86969,
          "close": 0.86977,
          "tick_volume": 6668.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-16T04:00:00Z"
        },
        {
          "time": 1771228800,
          "open": 0.86977,
          "high": 0.86987,
          "low": 0.86871,
          "close": 0.86933,
          "tick_volume": 15183.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-16T08:00:00Z"
        },
        {
          "time": 1771243200,
          "open": 0.86933,
          "high": 0.86987,
          "low": 0.8687,
          "close": 0.86949,
          "tick_volume": 12393.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-16T12:00:00Z"
        },
        {
          "time": 1771257600,
          "open": 0.8695,
          "high": 0.86986,
          "low": 0.86926,
          "close": 0.86942,
          "tick_volume": 8348.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-16T16:00:00Z"
        },
        {
          "time": 1771272000,
          "open": 0.86942,
          "high": 0.86981,
          "low": 0.86915,
          "close": 0.86915,
          "tick_volume": 2633.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-16T20:00:00Z"
        },
        {
          "time": 1771286400,
          "open": 0.86947,
          "high": 0.86994,
          "low": 0.86946,
          "close": 0.86988,
          "tick_volume": 9647.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-17T00:00:00Z"
        },
        {
          "time": 1771300800,
          "open": 0.86988,
          "high": 0.87027,
          "low": 0.86984,
          "close": 0.87008,
          "tick_volume": 8237.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-17T04:00:00Z"
        },
        {
          "time": 1771315200,
          "open": 0.87008,
          "high": 0.87305,
          "low": 0.87008,
          "close": 0.87109,
          "tick_volume": 18677.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-17T08:00:00Z"
        },
        {
          "time": 1771329600,
          "open": 0.8711,
          "high": 0.87456,
          "low": 0.87094,
          "close": 0.8745,
          "tick_volume": 24115.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-17T12:00:00Z"
        },
        {
          "time": 1771344000,
          "open": 0.87451,
          "high": 0.87492,
          "low": 0.87376,
          "close": 0.87383,
          "tick_volume": 25883.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-17T16:00:00Z"
        },
        {
          "time": 1771358400,
          "open": 0.87383,
          "high": 0.87441,
          "low": 0.87349,
          "close": 0.87394,
          "tick_volume": 9577.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-17T20:00:00Z"
        },
        {
          "time": 1771372800,
          "open": 0.87366,
          "high": 0.87387,
          "low": 0.87355,
          "close": 0.87384,
          "tick_volume": 9385.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-18T00:00:00Z"
        },
        {
          "time": 1771387200,
          "open": 0.87384,
          "high": 0.87385,
          "low": 0.87314,
          "close": 0.87327,
          "tick_volume": 6363.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-18T04:00:00Z"
        },
        {
          "time": 1771401600,
          "open": 0.87328,
          "high": 0.87351,
          "low": 0.87172,
          "close": 0.8722,
          "tick_volume": 15563.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-18T08:00:00Z"
        },
        {
          "time": 1771416000,
          "open": 0.8722,
          "high": 0.87322,
          "low": 0.87171,
          "close": 0.87282,
          "tick_volume": 20453.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-18T12:00:00Z"
        },
        {
          "time": 1771430400,
          "open": 0.87282,
          "high": 0.87349,
          "low": 0.87189,
          "close": 0.87245,
          "tick_volume": 21438.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-18T16:00:00Z"
        },
        {
          "time": 1771444800,
          "open": 0.87245,
          "high": 0.87343,
          "low": 0.87239,
          "close": 0.87296,
          "tick_volume": 11345.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-18T20:00:00Z"
        },
        {
          "time": 1771459200,
          "open": 0.87322,
          "high": 0.87407,
          "low": 0.87321,
          "close": 0.87375,
          "tick_volume": 8256.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-19T00:00:00Z"
        },
        {
          "time": 1771473600,
          "open": 0.87375,
          "high": 0.87439,
          "low": 0.87362,
          "close": 0.87395,
          "tick_volume": 7159.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-19T04:00:00Z"
        },
        {
          "time": 1771488000,
          "open": 0.87395,
          "high": 0.87436,
          "low": 0.87315,
          "close": 0.874,
          "tick_volume": 15680.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-19T08:00:00Z"
        },
        {
          "time": 1771502400,
          "open": 0.874,
          "high": 0.875,
          "low": 0.8732,
          "close": 0.87404,
          "tick_volume": 23587.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-19T12:00:00Z"
        },
        {
          "time": 1771516800,
          "open": 0.87405,
          "high": 0.87518,
          "low": 0.87361,
          "close": 0.87434,
          "tick_volume": 26118.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-19T16:00:00Z"
        },
        {
          "time": 1771531200,
          "open": 0.87434,
          "high": 0.87457,
          "low": 0.87398,
          "close": 0.87409,
          "tick_volume": 11612.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-19T20:00:00Z"
        },
        {
          "time": 1771545600,
          "open": 0.8742,
          "high": 0.87488,
          "low": 0.87411,
          "close": 0.87455,
          "tick_volume": 11973.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-20T00:00:00Z"
        },
        {
          "time": 1771560000,
          "open": 0.87455,
          "high": 0.87472,
          "low": 0.87405,
          "close": 0.87411,
          "tick_volume": 8521.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-20T04:00:00Z"
        },
        {
          "time": 1771574400,
          "open": 0.87411,
          "high": 0.87443,
          "low": 0.87265,
          "close": 0.87296,
          "tick_volume": 19074.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-20T08:00:00Z"
        },
        {
          "time": 1771588800,
          "open": 0.87296,
          "high": 0.8736,
          "low": 0.87252,
          "close": 0.87323,
          "tick_volume": 23717.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-20T12:00:00Z"
        },
        {
          "time": 1771603200,
          "open": 0.87323,
          "high": 0.87406,
          "low": 0.8726,
          "close": 0.87335,
          "tick_volume": 47718.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-20T16:00:00Z"
        },
        {
          "time": 1771617600,
          "open": 0.87335,
          "high": 0.87416,
          "low": 0.87323,
          "close": 0.87396,
          "tick_volume": 11845.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-20T20:00:00Z"
        },
        {
          "time": 1771790400,
          "open": 0.87451,
          "high": 0.87506,
          "low": 0.87365,
          "close": 0.87401,
          "tick_volume": 853.0,
          "spread": 28.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-22T20:00:00Z"
        },
        {
          "time": 1771804800,
          "open": 0.87408,
          "high": 0.87496,
          "low": 0.87395,
          "close": 0.87461,
          "tick_volume": 20155.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-23T00:00:00Z"
        },
        {
          "time": 1771819200,
          "open": 0.87461,
          "high": 0.87477,
          "low": 0.8739,
          "close": 0.87398,
          "tick_volume": 9739.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-23T04:00:00Z"
        },
        {
          "time": 1771833600,
          "open": 0.87398,
          "high": 0.87446,
          "low": 0.87321,
          "close": 0.87346,
          "tick_volume": 17812.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-23T08:00:00Z"
        },
        {
          "time": 1771848000,
          "open": 0.87347,
          "high": 0.87389,
          "low": 0.87279,
          "close": 0.87315,
          "tick_volume": 22441.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-23T12:00:00Z"
        },
        {
          "time": 1771862400,
          "open": 0.87315,
          "high": 0.8745,
          "low": 0.87305,
          "close": 0.87409,
          "tick_volume": 24711.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-23T16:00:00Z"
        },
        {
          "time": 1771876800,
          "open": 0.87409,
          "high": 0.87423,
          "low": 0.87335,
          "close": 0.87368,
          "tick_volume": 19579.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-23T20:00:00Z"
        },
        {
          "time": 1771891200,
          "open": 0.87375,
          "high": 0.87396,
          "low": 0.87292,
          "close": 0.87299,
          "tick_volume": 12250.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-24T00:00:00Z"
        },
        {
          "time": 1771905600,
          "open": 0.87297,
          "high": 0.87355,
          "low": 0.87289,
          "close": 0.87341,
          "tick_volume": 8627.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-24T04:00:00Z"
        },
        {
          "time": 1771920000,
          "open": 0.87341,
          "high": 0.87433,
          "low": 0.87295,
          "close": 0.87342,
          "tick_volume": 19606.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-24T08:00:00Z"
        },
        {
          "time": 1771934400,
          "open": 0.87341,
          "high": 0.87363,
          "low": 0.87219,
          "close": 0.87219,
          "tick_volume": 19368.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-24T12:00:00Z"
        },
        {
          "time": 1771948800,
          "open": 0.87219,
          "high": 0.87235,
          "low": 0.87076,
          "close": 0.872,
          "tick_volume": 19677.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-24T16:00:00Z"
        },
        {
          "time": 1771963200,
          "open": 0.872,
          "high": 0.87293,
          "low": 0.87191,
          "close": 0.8726,
          "tick_volume": 7126.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-24T20:00:00Z"
        },
        {
          "time": 1771977600,
          "open": 0.87247,
          "high": 0.87271,
          "low": 0.87197,
          "close": 0.87229,
          "tick_volume": 10741.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-25T00:00:00Z"
        },
        {
          "time": 1771992000,
          "open": 0.8723,
          "high": 0.87294,
          "low": 0.87219,
          "close": 0.87282,
          "tick_volume": 11790.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-25T04:00:00Z"
        },
        {
          "time": 1772006400,
          "open": 0.87282,
          "high": 0.87318,
          "low": 0.87158,
          "close": 0.87185,
          "tick_volume": 17867.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-25T08:00:00Z"
        },
        {
          "time": 1772020800,
          "open": 0.87185,
          "high": 0.87276,
          "low": 0.871,
          "close": 0.87168,
          "tick_volume": 19411.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-25T12:00:00Z"
        },
        {
          "time": 1772035200,
          "open": 0.87169,
          "high": 0.87239,
          "low": 0.87078,
          "close": 0.87104,
          "tick_volume": 20480.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-25T16:00:00Z"
        },
        {
          "time": 1772049600,
          "open": 0.87104,
          "high": 0.87151,
          "low": 0.87085,
          "close": 0.87138,
          "tick_volume": 8444.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-25T20:00:00Z"
        },
        {
          "time": 1772064000,
          "open": 0.87129,
          "high": 0.87164,
          "low": 0.87118,
          "close": 0.87124,
          "tick_volume": 11313.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-26T00:00:00Z"
        },
        {
          "time": 1772078400,
          "open": 0.87124,
          "high": 0.87194,
          "low": 0.87121,
          "close": 0.87188,
          "tick_volume": 10225.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-26T04:00:00Z"
        },
        {
          "time": 1772092800,
          "open": 0.87186,
          "high": 0.87311,
          "low": 0.87152,
          "close": 0.87167,
          "tick_volume": 16824.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-26T08:00:00Z"
        },
        {
          "time": 1772107200,
          "open": 0.87166,
          "high": 0.87231,
          "low": 0.87146,
          "close": 0.87208,
          "tick_volume": 20527.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-26T12:00:00Z"
        },
        {
          "time": 1772121600,
          "open": 0.87207,
          "high": 0.87583,
          "low": 0.87184,
          "close": 0.87518,
          "tick_volume": 30170.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-26T16:00:00Z"
        },
        {
          "time": 1772136000,
          "open": 0.87518,
          "high": 0.87527,
          "low": 0.87457,
          "close": 0.87517,
          "tick_volume": 9219.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-26T20:00:00Z"
        },
        {
          "time": 1772150400,
          "open": 0.87511,
          "high": 0.87518,
          "low": 0.87459,
          "close": 0.87492,
          "tick_volume": 11640.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-27T00:00:00Z"
        },
        {
          "time": 1772164800,
          "open": 0.87491,
          "high": 0.87648,
          "low": 0.87474,
          "close": 0.87638,
          "tick_volume": 9641.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-27T04:00:00Z"
        },
        {
          "time": 1772179200,
          "open": 0.87638,
          "high": 0.87649,
          "low": 0.87459,
          "close": 0.87558,
          "tick_volume": 17790.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-27T08:00:00Z"
        },
        {
          "time": 1772193600,
          "open": 0.87558,
          "high": 0.87739,
          "low": 0.87544,
          "close": 0.87709,
          "tick_volume": 23493.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-27T12:00:00Z"
        },
        {
          "time": 1772208000,
          "open": 0.87709,
          "high": 0.87895,
          "low": 0.87687,
          "close": 0.87718,
          "tick_volume": 26338.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-27T16:00:00Z"
        },
        {
          "time": 1772222400,
          "open": 0.87717,
          "high": 0.8773,
          "low": 0.87618,
          "close": 0.8764,
          "tick_volume": 10046.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-27T20:00:00Z"
        },
        {
          "time": 1772395200,
          "open": 0.87765,
          "high": 0.87797,
          "low": 0.8766,
          "close": 0.87767,
          "tick_volume": 1511.0,
          "spread": 18.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-01T20:00:00Z"
        },
        {
          "time": 1772409600,
          "open": 0.87724,
          "high": 0.87791,
          "low": 0.87622,
          "close": 0.87682,
          "tick_volume": 27826.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-02T00:00:00Z"
        },
        {
          "time": 1772424000,
          "open": 0.87682,
          "high": 0.87735,
          "low": 0.87653,
          "close": 0.87673,
          "tick_volume": 17400.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-02T04:00:00Z"
        },
        {
          "time": 1772438400,
          "open": 0.87673,
          "high": 0.87877,
          "low": 0.87534,
          "close": 0.87563,
          "tick_volume": 35107.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-02T08:00:00Z"
        },
        {
          "time": 1772452800,
          "open": 0.87563,
          "high": 0.87589,
          "low": 0.87317,
          "close": 0.8736,
          "tick_volume": 35225.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-02T12:00:00Z"
        },
        {
          "time": 1772467200,
          "open": 0.87359,
          "high": 0.87451,
          "low": 0.87224,
          "close": 0.87235,
          "tick_volume": 31589.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-02T16:00:00Z"
        },
        {
          "time": 1772481600,
          "open": 0.87235,
          "high": 0.87268,
          "low": 0.87164,
          "close": 0.87196,
          "tick_volume": 15750.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-02T20:00:00Z"
        },
        {
          "time": 1772496000,
          "open": 0.87208,
          "high": 0.87265,
          "low": 0.87193,
          "close": 0.8724,
          "tick_volume": 17588.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-03T00:00:00Z"
        },
        {
          "time": 1772510400,
          "open": 0.8724,
          "high": 0.87354,
          "low": 0.87226,
          "close": 0.87335,
          "tick_volume": 16258.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-03T04:00:00Z"
        },
        {
          "time": 1772524800,
          "open": 0.87335,
          "high": 0.87396,
          "low": 0.87195,
          "close": 0.87253,
          "tick_volume": 37742.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-03T08:00:00Z"
        },
        {
          "time": 1772539200,
          "open": 0.87254,
          "high": 0.87335,
          "low": 0.86997,
          "close": 0.87076,
          "tick_volume": 42897.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-03T12:00:00Z"
        },
        {
          "time": 1772553600,
          "open": 0.87076,
          "high": 0.87093,
          "low": 0.86963,
          "close": 0.86985,
          "tick_volume": 50628.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-03T16:00:00Z"
        },
        {
          "time": 1772568000,
          "open": 0.86986,
          "high": 0.87083,
          "low": 0.86914,
          "close": 0.86956,
          "tick_volume": 21061.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-03T20:00:00Z"
        },
        {
          "time": 1772582400,
          "open": 0.86957,
          "high": 0.8703,
          "low": 0.86925,
          "close": 0.87008,
          "tick_volume": 20183.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-04T00:00:00Z"
        },
        {
          "time": 1772596800,
          "open": 0.87008,
          "high": 0.87128,
          "low": 0.87007,
          "close": 0.87081,
          "tick_volume": 17515.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-04T04:00:00Z"
        },
        {
          "time": 1772611200,
          "open": 0.87078,
          "high": 0.87112,
          "low": 0.86858,
          "close": 0.8696,
          "tick_volume": 34083.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-04T08:00:00Z"
        },
        {
          "time": 1772625600,
          "open": 0.8696,
          "high": 0.87123,
          "low": 0.86911,
          "close": 0.87001,
          "tick_volume": 31830.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-04T12:00:00Z"
        },
        {
          "time": 1772640000,
          "open": 0.87,
          "high": 0.87123,
          "low": 0.86959,
          "close": 0.8707,
          "tick_volume": 28621.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-04T16:00:00Z"
        },
        {
          "time": 1772654400,
          "open": 0.87071,
          "high": 0.87078,
          "low": 0.86971,
          "close": 0.87014,
          "tick_volume": 11320.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-04T20:00:00Z"
        },
        {
          "time": 1772668800,
          "open": 0.87014,
          "high": 0.87045,
          "low": 0.86981,
          "close": 0.86994,
          "tick_volume": 14071.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-05T00:00:00Z"
        },
        {
          "time": 1772683200,
          "open": 0.86993,
          "high": 0.8712,
          "low": 0.8699,
          "close": 0.8706,
          "tick_volume": 17780.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-05T04:00:00Z"
        },
        {
          "time": 1772697600,
          "open": 0.87061,
          "high": 0.87087,
          "low": 0.86963,
          "close": 0.86971,
          "tick_volume": 34990.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-05T08:00:00Z"
        },
        {
          "time": 1772712000,
          "open": 0.8697,
          "high": 0.86982,
          "low": 0.86861,
          "close": 0.8695,
          "tick_volume": 30605.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-05T12:00:00Z"
        },
        {
          "time": 1772726400,
          "open": 0.8695,
          "high": 0.86986,
          "low": 0.86866,
          "close": 0.86908,
          "tick_volume": 37526.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-05T16:00:00Z"
        },
        {
          "time": 1772740800,
          "open": 0.86908,
          "high": 0.87015,
          "low": 0.86849,
          "close": 0.86956,
          "tick_volume": 20407.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-05T20:00:00Z"
        },
        {
          "time": 1772755200,
          "open": 0.86926,
          "high": 0.8696,
          "low": 0.86888,
          "close": 0.86912,
          "tick_volume": 13654.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-06T00:00:00Z"
        },
        {
          "time": 1772769600,
          "open": 0.86913,
          "high": 0.86924,
          "low": 0.86847,
          "close": 0.86859,
          "tick_volume": 12232.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-06T04:00:00Z"
        },
        {
          "time": 1772784000,
          "open": 0.8686,
          "high": 0.86899,
          "low": 0.86785,
          "close": 0.8679,
          "tick_volume": 24565.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-06T08:00:00Z"
        },
        {
          "time": 1772798400,
          "open": 0.86789,
          "high": 0.86842,
          "low": 0.86564,
          "close": 0.86743,
          "tick_volume": 46028.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-06T12:00:00Z"
        },
        {
          "time": 1772812800,
          "open": 0.86742,
          "high": 0.86745,
          "low": 0.86577,
          "close": 0.86641,
          "tick_volume": 43720.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-06T16:00:00Z"
        },
        {
          "time": 1772827200,
          "open": 0.86642,
          "high": 0.86709,
          "low": 0.86621,
          "close": 0.86631,
          "tick_volume": 17885.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-06T20:00:00Z"
        },
        {
          "time": 1773000000,
          "open": 0.86557,
          "high": 0.86634,
          "low": 0.86532,
          "close": 0.86621,
          "tick_volume": 5685.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-08T20:00:00Z"
        },
        {
          "time": 1773014400,
          "open": 0.86621,
          "high": 0.86666,
          "low": 0.86578,
          "close": 0.86624,
          "tick_volume": 28350.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-09T00:00:00Z"
        },
        {
          "time": 1773028800,
          "open": 0.86624,
          "high": 0.86771,
          "low": 0.86615,
          "close": 0.86728,
          "tick_volume": 26149.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-09T04:00:00Z"
        },
        {
          "time": 1773043200,
          "open": 0.86728,
          "high": 0.8676,
          "low": 0.86537,
          "close": 0.86629,
          "tick_volume": 42714.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-09T08:00:00Z"
        },
        {
          "time": 1773057600,
          "open": 0.86627,
          "high": 0.86641,
          "low": 0.865,
          "close": 0.86515,
          "tick_volume": 42742.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-09T12:00:00Z"
        },
        {
          "time": 1773072000,
          "open": 0.86515,
          "high": 0.86567,
          "low": 0.86451,
          "close": 0.8649,
          "tick_volume": 28209.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-09T16:00:00Z"
        },
        {
          "time": 1773086400,
          "open": 0.8649,
          "high": 0.86611,
          "low": 0.86439,
          "close": 0.86578,
          "tick_volume": 25253.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-09T20:00:00Z"
        },
        {
          "time": 1773100800,
          "open": 0.86568,
          "high": 0.86573,
          "low": 0.86501,
          "close": 0.86527,
          "tick_volume": 19391.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-10T00:00:00Z"
        },
        {
          "time": 1773115200,
          "open": 0.86526,
          "high": 0.8654,
          "low": 0.86458,
          "close": 0.86485,
          "tick_volume": 13910.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-10T04:00:00Z"
        },
        {
          "time": 1773129600,
          "open": 0.86483,
          "high": 0.8661,
          "low": 0.86422,
          "close": 0.86534,
          "tick_volume": 26992.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-10T08:00:00Z"
        },
        {
          "time": 1773144000,
          "open": 0.86534,
          "high": 0.86586,
          "low": 0.86464,
          "close": 0.86494,
          "tick_volume": 33967.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-10T12:00:00Z"
        },
        {
          "time": 1773158400,
          "open": 0.86495,
          "high": 0.86581,
          "low": 0.8648,
          "close": 0.86566,
          "tick_volume": 34832.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-10T16:00:00Z"
        },
        {
          "time": 1773172800,
          "open": 0.86567,
          "high": 0.86569,
          "low": 0.86485,
          "close": 0.86519,
          "tick_volume": 18248.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-10T20:00:00Z"
        },
        {
          "time": 1773187200,
          "open": 0.86525,
          "high": 0.86533,
          "low": 0.86448,
          "close": 0.86462,
          "tick_volume": 14040.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-11T00:00:00Z"
        },
        {
          "time": 1773201600,
          "open": 0.86462,
          "high": 0.86528,
          "low": 0.86452,
          "close": 0.86503,
          "tick_volume": 18107.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-11T04:00:00Z"
        },
        {
          "time": 1773216000,
          "open": 0.86503,
          "high": 0.86575,
          "low": 0.86314,
          "close": 0.86326,
          "tick_volume": 33266.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-11T08:00:00Z"
        },
        {
          "time": 1773230400,
          "open": 0.86327,
          "high": 0.86451,
          "low": 0.86275,
          "close": 0.86283,
          "tick_volume": 39526.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-11T12:00:00Z"
        },
        {
          "time": 1773244800,
          "open": 0.86283,
          "high": 0.86372,
          "low": 0.86246,
          "close": 0.86258,
          "tick_volume": 27107.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-11T16:00:00Z"
        },
        {
          "time": 1773259200,
          "open": 0.86258,
          "high": 0.86315,
          "low": 0.86221,
          "close": 0.86266,
          "tick_volume": 10147.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-11T20:00:00Z"
        },
        {
          "time": 1773273600,
          "open": 0.86263,
          "high": 0.86299,
          "low": 0.86236,
          "close": 0.86299,
          "tick_volume": 19764.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-12T00:00:00Z"
        },
        {
          "time": 1773288000,
          "open": 0.86299,
          "high": 0.86371,
          "low": 0.86276,
          "close": 0.86299,
          "tick_volume": 17096.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-12T04:00:00Z"
        },
        {
          "time": 1773302400,
          "open": 0.86299,
          "high": 0.8635,
          "low": 0.86239,
          "close": 0.863,
          "tick_volume": 19305.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-12T08:00:00Z"
        },
        {
          "time": 1773316800,
          "open": 0.863,
          "high": 0.86306,
          "low": 0.86172,
          "close": 0.86252,
          "tick_volume": 32283.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-12T12:00:00Z"
        },
        {
          "time": 1773331200,
          "open": 0.86252,
          "high": 0.86341,
          "low": 0.86246,
          "close": 0.86281,
          "tick_volume": 30696.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-12T16:00:00Z"
        },
        {
          "time": 1773345600,
          "open": 0.8628,
          "high": 0.86303,
          "low": 0.86236,
          "close": 0.86286,
          "tick_volume": 11660.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-12T20:00:00Z"
        },
        {
          "time": 1773360000,
          "open": 0.86282,
          "high": 0.86302,
          "low": 0.86213,
          "close": 0.86233,
          "tick_volume": 15303.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-13T00:00:00Z"
        },
        {
          "time": 1773374400,
          "open": 0.86232,
          "high": 0.86306,
          "low": 0.86228,
          "close": 0.86233,
          "tick_volume": 15957.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-13T04:00:00Z"
        },
        {
          "time": 1773388800,
          "open": 0.86233,
          "high": 0.86435,
          "low": 0.86201,
          "close": 0.86413,
          "tick_volume": 31036.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-13T08:00:00Z"
        },
        {
          "time": 1773403200,
          "open": 0.86413,
          "high": 0.86544,
          "low": 0.86411,
          "close": 0.86435,
          "tick_volume": 36577.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-13T12:00:00Z"
        },
        {
          "time": 1773417600,
          "open": 0.86435,
          "high": 0.86455,
          "low": 0.86351,
          "close": 0.86353,
          "tick_volume": 31490.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-13T16:00:00Z"
        },
        {
          "time": 1773432000,
          "open": 0.86354,
          "high": 0.86366,
          "low": 0.86302,
          "close": 0.86331,
          "tick_volume": 9011.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-13T20:00:00Z"
        },
        {
          "time": 1773604800,
          "open": 0.86344,
          "high": 0.86364,
          "low": 0.86311,
          "close": 0.86337,
          "tick_volume": 3603.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-15T20:00:00Z"
        },
        {
          "time": 1773619200,
          "open": 0.86336,
          "high": 0.86378,
          "low": 0.8631,
          "close": 0.86376,
          "tick_volume": 16536.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-16T00:00:00Z"
        },
        {
          "time": 1773633600,
          "open": 0.86376,
          "high": 0.86383,
          "low": 0.86265,
          "close": 0.86274,
          "tick_volume": 9462.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-16T04:00:00Z"
        },
        {
          "time": 1773648000,
          "open": 0.86274,
          "high": 0.86502,
          "low": 0.86253,
          "close": 0.86461,
          "tick_volume": 23961.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-16T08:00:00Z"
        },
        {
          "time": 1773662400,
          "open": 0.86461,
          "high": 0.86487,
          "low": 0.8636,
          "close": 0.86399,
          "tick_volume": 27239.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-16T12:00:00Z"
        },
        {
          "time": 1773676800,
          "open": 0.86399,
          "high": 0.86421,
          "low": 0.86337,
          "close": 0.86396,
          "tick_volume": 26486.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-16T16:00:00Z"
        },
        {
          "time": 1773691200,
          "open": 0.86396,
          "high": 0.86421,
          "low": 0.86348,
          "close": 0.86374,
          "tick_volume": 10964.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-16T20:00:00Z"
        },
        {
          "time": 1773705600,
          "open": 0.86372,
          "high": 0.86424,
          "low": 0.86359,
          "close": 0.86391,
          "tick_volume": 11110.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-17T00:00:00Z"
        },
        {
          "time": 1773720000,
          "open": 0.86389,
          "high": 0.86422,
          "low": 0.8636,
          "close": 0.86391,
          "tick_volume": 11381.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-17T04:00:00Z"
        },
        {
          "time": 1773734400,
          "open": 0.86389,
          "high": 0.86423,
          "low": 0.86324,
          "close": 0.86357,
          "tick_volume": 20334.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-17T08:00:00Z"
        },
        {
          "time": 1773748800,
          "open": 0.86357,
          "high": 0.86455,
          "low": 0.8633,
          "close": 0.86403,
          "tick_volume": 25002.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-17T12:00:00Z"
        },
        {
          "time": 1773763200,
          "open": 0.86403,
          "high": 0.86416,
          "low": 0.86357,
          "close": 0.86396,
          "tick_volume": 22344.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-17T16:00:00Z"
        },
        {
          "time": 1773777600,
          "open": 0.86396,
          "high": 0.86414,
          "low": 0.86342,
          "close": 0.8638,
          "tick_volume": 8746.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-17T20:00:00Z"
        },
        {
          "time": 1773792000,
          "open": 0.86378,
          "high": 0.86403,
          "low": 0.86363,
          "close": 0.86369,
          "tick_volume": 17969.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-18T00:00:00Z"
        },
        {
          "time": 1773806400,
          "open": 0.86369,
          "high": 0.86378,
          "low": 0.86337,
          "close": 0.86362,
          "tick_volume": 7830.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-18T04:00:00Z"
        },
        {
          "time": 1773820800,
          "open": 0.86363,
          "high": 0.86427,
          "low": 0.86284,
          "close": 0.86407,
          "tick_volume": 13517.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-18T08:00:00Z"
        },
        {
          "time": 1773835200,
          "open": 0.86407,
          "high": 0.8651,
          "low": 0.86358,
          "close": 0.86422,
          "tick_volume": 36194.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-18T12:00:00Z"
        },
        {
          "time": 1773849600,
          "open": 0.86422,
          "high": 0.86486,
          "low": 0.86282,
          "close": 0.86363,
          "tick_volume": 30252.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-18T16:00:00Z"
        },
        {
          "time": 1773864000,
          "open": 0.86363,
          "high": 0.86469,
          "low": 0.86356,
          "close": 0.86405,
          "tick_volume": 14409.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-18T20:00:00Z"
        },
        {
          "time": 1773878400,
          "open": 0.86411,
          "high": 0.86433,
          "low": 0.86356,
          "close": 0.86414,
          "tick_volume": 13624.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-19T00:00:00Z"
        },
        {
          "time": 1773892800,
          "open": 0.86414,
          "high": 0.86453,
          "low": 0.86377,
          "close": 0.86423,
          "tick_volume": 11097.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-19T04:00:00Z"
        },
        {
          "time": 1773907200,
          "open": 0.86423,
          "high": 0.8649,
          "low": 0.86318,
          "close": 0.86405,
          "tick_volume": 32279.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-19T08:00:00Z"
        },
        {
          "time": 1773921600,
          "open": 0.86405,
          "high": 0.86442,
          "low": 0.86154,
          "close": 0.86171,
          "tick_volume": 50069.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-19T12:00:00Z"
        },
        {
          "time": 1773936000,
          "open": 0.86171,
          "high": 0.86325,
          "low": 0.86118,
          "close": 0.86322,
          "tick_volume": 33304.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-19T16:00:00Z"
        },
        {
          "time": 1773950400,
          "open": 0.86322,
          "high": 0.86386,
          "low": 0.86213,
          "close": 0.8624,
          "tick_volume": 20468.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-19T20:00:00Z"
        },
        {
          "time": 1773964800,
          "open": 0.86235,
          "high": 0.86252,
          "low": 0.86195,
          "close": 0.86221,
          "tick_volume": 11373.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-20T00:00:00Z"
        },
        {
          "time": 1773979200,
          "open": 0.86221,
          "high": 0.86262,
          "low": 0.86202,
          "close": 0.86243,
          "tick_volume": 7823.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-20T04:00:00Z"
        },
        {
          "time": 1773993600,
          "open": 0.86242,
          "high": 0.86418,
          "low": 0.86148,
          "close": 0.86404,
          "tick_volume": 23544.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-20T08:00:00Z"
        },
        {
          "time": 1774008000,
          "open": 0.86404,
          "high": 0.86677,
          "low": 0.86338,
          "close": 0.86676,
          "tick_volume": 36062.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-20T12:00:00Z"
        },
        {
          "time": 1774022400,
          "open": 0.86676,
          "high": 0.86792,
          "low": 0.86571,
          "close": 0.86676,
          "tick_volume": 35749.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-20T16:00:00Z"
        },
        {
          "time": 1774036800,
          "open": 0.86675,
          "high": 0.86753,
          "low": 0.86633,
          "close": 0.8673,
          "tick_volume": 11790.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-20T20:00:00Z"
        },
        {
          "time": 1774209600,
          "open": 0.86754,
          "high": 0.86799,
          "low": 0.86739,
          "close": 0.86749,
          "tick_volume": 2897.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-22T20:00:00Z"
        },
        {
          "time": 1774224000,
          "open": 0.86751,
          "high": 0.86754,
          "low": 0.86629,
          "close": 0.86692,
          "tick_volume": 20486.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-23T00:00:00Z"
        },
        {
          "time": 1774238400,
          "open": 0.86692,
          "high": 0.86776,
          "low": 0.86674,
          "close": 0.86761,
          "tick_volume": 16019.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-23T04:00:00Z"
        },
        {
          "time": 1774252800,
          "open": 0.86761,
          "high": 0.86793,
          "low": 0.86571,
          "close": 0.86603,
          "tick_volume": 35507.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-23T08:00:00Z"
        },
        {
          "time": 1774267200,
          "open": 0.86602,
          "high": 0.86685,
          "low": 0.8631,
          "close": 0.86406,
          "tick_volume": 106986.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-23T12:00:00Z"
        },
        {
          "time": 1774281600,
          "open": 0.86406,
          "high": 0.86577,
          "low": 0.86382,
          "close": 0.86478,
          "tick_volume": 59612.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-23T16:00:00Z"
        },
        {
          "time": 1774296000,
          "open": 0.86479,
          "high": 0.86525,
          "low": 0.86423,
          "close": 0.86466,
          "tick_volume": 11980.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-23T20:00:00Z"
        },
        {
          "time": 1774310400,
          "open": 0.86465,
          "high": 0.86531,
          "low": 0.86438,
          "close": 0.86455,
          "tick_volume": 22243.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-24T00:00:00Z"
        },
        {
          "time": 1774324800,
          "open": 0.86454,
          "high": 0.86498,
          "low": 0.8638,
          "close": 0.86428,
          "tick_volume": 18288.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-24T04:00:00Z"
        },
        {
          "time": 1774339200,
          "open": 0.86428,
          "high": 0.86582,
          "low": 0.86377,
          "close": 0.86473,
          "tick_volume": 33882.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-24T08:00:00Z"
        },
        {
          "time": 1774353600,
          "open": 0.86472,
          "high": 0.86568,
          "low": 0.86432,
          "close": 0.86496,
          "tick_volume": 42723.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-24T12:00:00Z"
        },
        {
          "time": 1774368000,
          "open": 0.86495,
          "high": 0.86587,
          "low": 0.86483,
          "close": 0.86542,
          "tick_volume": 36688.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-24T16:00:00Z"
        },
        {
          "time": 1774382400,
          "open": 0.86542,
          "high": 0.866,
          "low": 0.86515,
          "close": 0.86554,
          "tick_volume": 19903.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-24T20:00:00Z"
        },
        {
          "time": 1774396800,
          "open": 0.86553,
          "high": 0.86595,
          "low": 0.8653,
          "close": 0.8658,
          "tick_volume": 17935.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-25T00:00:00Z"
        },
        {
          "time": 1774411200,
          "open": 0.8658,
          "high": 0.8667,
          "low": 0.86557,
          "close": 0.86653,
          "tick_volume": 12148.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-25T04:00:00Z"
        },
        {
          "time": 1774425600,
          "open": 0.86654,
          "high": 0.86683,
          "low": 0.86507,
          "close": 0.86534,
          "tick_volume": 27005.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-25T08:00:00Z"
        },
        {
          "time": 1774440000,
          "open": 0.86534,
          "high": 0.86632,
          "low": 0.86479,
          "close": 0.86561,
          "tick_volume": 33339.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-25T12:00:00Z"
        },
        {
          "time": 1774454400,
          "open": 0.86561,
          "high": 0.86564,
          "low": 0.86456,
          "close": 0.86534,
          "tick_volume": 27955.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-25T16:00:00Z"
        },
        {
          "time": 1774468800,
          "open": 0.86534,
          "high": 0.86538,
          "low": 0.86469,
          "close": 0.86514,
          "tick_volume": 9086.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-25T20:00:00Z"
        },
        {
          "time": 1774483200,
          "open": 0.86515,
          "high": 0.86577,
          "low": 0.86508,
          "close": 0.86574,
          "tick_volume": 8917.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-26T00:00:00Z"
        },
        {
          "time": 1774497600,
          "open": 0.86574,
          "high": 0.86581,
          "low": 0.86503,
          "close": 0.86544,
          "tick_volume": 10173.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-26T04:00:00Z"
        },
        {
          "time": 1774512000,
          "open": 0.86545,
          "high": 0.86625,
          "low": 0.86515,
          "close": 0.86547,
          "tick_volume": 21848.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-26T08:00:00Z"
        },
        {
          "time": 1774526400,
          "open": 0.86547,
          "high": 0.86551,
          "low": 0.86368,
          "close": 0.86426,
          "tick_volume": 32772.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-26T12:00:00Z"
        },
        {
          "time": 1774540800,
          "open": 0.86425,
          "high": 0.86552,
          "low": 0.86408,
          "close": 0.86534,
          "tick_volume": 24506.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-26T16:00:00Z"
        },
        {
          "time": 1774555200,
          "open": 0.86534,
          "high": 0.86557,
          "low": 0.86443,
          "close": 0.8651,
          "tick_volume": 16122.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-26T20:00:00Z"
        },
        {
          "time": 1774569600,
          "open": 0.86512,
          "high": 0.86516,
          "low": 0.86473,
          "close": 0.86486,
          "tick_volume": 13006.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-27T00:00:00Z"
        },
        {
          "time": 1774584000,
          "open": 0.86484,
          "high": 0.86519,
          "low": 0.86478,
          "close": 0.86497,
          "tick_volume": 11440.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-27T04:00:00Z"
        },
        {
          "time": 1774598400,
          "open": 0.86496,
          "high": 0.86595,
          "low": 0.8649,
          "close": 0.86536,
          "tick_volume": 20305.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-27T08:00:00Z"
        },
        {
          "time": 1774612800,
          "open": 0.86537,
          "high": 0.86752,
          "low": 0.8653,
          "close": 0.86609,
          "tick_volume": 28825.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-27T12:00:00Z"
        },
        {
          "time": 1774627200,
          "open": 0.86608,
          "high": 0.86791,
          "low": 0.86587,
          "close": 0.86761,
          "tick_volume": 28316.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-27T16:00:00Z"
        },
        {
          "time": 1774641600,
          "open": 0.86761,
          "high": 0.86804,
          "low": 0.86744,
          "close": 0.86785,
          "tick_volume": 7771.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-27T20:00:00Z"
        },
        {
          "time": 1774814400,
          "open": 0.8674,
          "high": 0.8674,
          "low": 0.86597,
          "close": 0.8667,
          "tick_volume": 426.0,
          "spread": 26.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-29T20:00:00Z"
        },
        {
          "time": 1774828800,
          "open": 0.86747,
          "high": 0.86848,
          "low": 0.86741,
          "close": 0.86829,
          "tick_volume": 25074.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-30T00:00:00Z"
        },
        {
          "time": 1774843200,
          "open": 0.86829,
          "high": 0.86849,
          "low": 0.86727,
          "close": 0.86761,
          "tick_volume": 13227.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-30T04:00:00Z"
        },
        {
          "time": 1774857600,
          "open": 0.86761,
          "high": 0.86876,
          "low": 0.86726,
          "close": 0.86844,
          "tick_volume": 21448.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-30T08:00:00Z"
        },
        {
          "time": 1774872000,
          "open": 0.86843,
          "high": 0.86966,
          "low": 0.86757,
          "close": 0.86955,
          "tick_volume": 26977.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-30T12:00:00Z"
        },
        {
          "time": 1774886400,
          "open": 0.86955,
          "high": 0.86982,
          "low": 0.86789,
          "close": 0.86894,
          "tick_volume": 31131.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-30T16:00:00Z"
        },
        {
          "time": 1774900800,
          "open": 0.86895,
          "high": 0.86973,
          "low": 0.86889,
          "close": 0.86941,
          "tick_volume": 17417.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-30T20:00:00Z"
        },
        {
          "time": 1774915200,
          "open": 0.86944,
          "high": 0.87002,
          "low": 0.86862,
          "close": 0.86874,
          "tick_volume": 18809.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-31T00:00:00Z"
        },
        {
          "time": 1774929600,
          "open": 0.86874,
          "high": 0.86914,
          "low": 0.86817,
          "close": 0.86837,
          "tick_volume": 13293.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-31T04:00:00Z"
        },
        {
          "time": 1774944000,
          "open": 0.86837,
          "high": 0.86909,
          "low": 0.86762,
          "close": 0.86787,
          "tick_volume": 23666.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-31T08:00:00Z"
        },
        {
          "time": 1774958400,
          "open": 0.86787,
          "high": 0.86972,
          "low": 0.86772,
          "close": 0.86963,
          "tick_volume": 30574.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-31T12:00:00Z"
        },
        {
          "time": 1774972800,
          "open": 0.86964,
          "high": 0.87427,
          "low": 0.86943,
          "close": 0.8722,
          "tick_volume": 57901.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-31T16:00:00Z"
        },
        {
          "time": 1774987200,
          "open": 0.8722,
          "high": 0.87391,
          "low": 0.87187,
          "close": 0.87363,
          "tick_volume": 17190.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-31T20:00:00Z"
        },
        {
          "time": 1775001600,
          "open": 0.87362,
          "high": 0.87424,
          "low": 0.87342,
          "close": 0.87381,
          "tick_volume": 15446.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-04-01T00:00:00Z"
        },
        {
          "time": 1775016000,
          "open": 0.87382,
          "high": 0.87394,
          "low": 0.87262,
          "close": 0.87263,
          "tick_volume": 12398.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-04-01T04:00:00Z"
        },
        {
          "time": 1775030400,
          "open": 0.87267,
          "high": 0.87321,
          "low": 0.87181,
          "close": 0.8723,
          "tick_volume": 35960.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-04-01T08:00:00Z"
        },
        {
          "time": 1775044800,
          "open": 0.8723,
          "high": 0.87269,
          "low": 0.871,
          "close": 0.87207,
          "tick_volume": 37823.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-04-01T12:00:00Z"
        },
        {
          "time": 1775059200,
          "open": 0.87209,
          "high": 0.87273,
          "low": 0.87058,
          "close": 0.87059,
          "tick_volume": 31820.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-04-01T16:00:00Z"
        },
        {
          "time": 1775073600,
          "open": 0.87058,
          "high": 0.87165,
          "low": 0.87028,
          "close": 0.87103,
          "tick_volume": 16992.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-04-01T20:00:00Z"
        },
        {
          "time": 1775088000,
          "open": 0.87106,
          "high": 0.87196,
          "low": 0.87087,
          "close": 0.87153,
          "tick_volume": 30810.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-04-02T00:00:00Z"
        },
        {
          "time": 1775102400,
          "open": 0.87153,
          "high": 0.87222,
          "low": 0.87135,
          "close": 0.87213,
          "tick_volume": 19818.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-04-02T04:00:00Z"
        },
        {
          "time": 1775116800,
          "open": 0.87212,
          "high": 0.87336,
          "low": 0.87199,
          "close": 0.87307,
          "tick_volume": 25418.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-04-02T08:00:00Z"
        },
        {
          "time": 1775131200,
          "open": 0.87307,
          "high": 0.87343,
          "low": 0.87197,
          "close": 0.87225,
          "tick_volume": 28118.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-04-02T12:00:00Z"
        },
        {
          "time": 1775145600,
          "open": 0.87224,
          "high": 0.87322,
          "low": 0.87201,
          "close": 0.87243,
          "tick_volume": 37590.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-04-02T16:00:00Z"
        },
        {
          "time": 1775160000,
          "open": 0.87243,
          "high": 0.87301,
          "low": 0.87217,
          "close": 0.87298,
          "tick_volume": 10744.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-04-02T20:00:00Z"
        },
        {
          "time": 1775174400,
          "open": 0.87249,
          "high": 0.87263,
          "low": 0.87181,
          "close": 0.87206,
          "tick_volume": 5170.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-04-03T00:00:00Z"
        },
        {
          "time": 1775188800,
          "open": 0.87207,
          "high": 0.87224,
          "low": 0.87178,
          "close": 0.87187,
          "tick_volume": 4081.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-04-03T04:00:00Z"
        },
        {
          "time": 1775203200,
          "open": 0.87187,
          "high": 0.87226,
          "low": 0.87175,
          "close": 0.87218,
          "tick_volume": 6334.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-04-03T08:00:00Z"
        },
        {
          "time": 1775217600,
          "open": 0.87218,
          "high": 0.87313,
          "low": 0.872,
          "close": 0.8727,
          "tick_volume": 13041.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-04-03T12:00:00Z"
        },
        {
          "time": 1775232000,
          "open": 0.87271,
          "high": 0.87322,
          "low": 0.87202,
          "close": 0.87281,
          "tick_volume": 15455.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-04-03T16:00:00Z"
        },
        {
          "time": 1775246400,
          "open": 0.87281,
          "high": 0.87367,
          "low": 0.87217,
          "close": 0.87217,
          "tick_volume": 7115.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-04-03T20:00:00Z"
        },
        {
          "time": 1775419200,
          "open": 0.87338,
          "high": 0.87357,
          "low": 0.8731,
          "close": 0.87333,
          "tick_volume": 240.0,
          "spread": 14.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-04-05T20:00:00Z"
        },
        {
          "time": 1775433600,
          "open": 0.87322,
          "high": 0.8734,
          "low": 0.87216,
          "close": 0.8722,
          "tick_volume": 17317.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-04-06T00:00:00Z"
        },
        {
          "time": 1775448000,
          "open": 0.87219,
          "high": 0.87231,
          "low": 0.87188,
          "close": 0.87207,
          "tick_volume": 13556.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-04-06T04:00:00Z"
        },
        {
          "time": 1775462400,
          "open": 0.87207,
          "high": 0.87294,
          "low": 0.87186,
          "close": 0.87202,
          "tick_volume": 18862.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-04-06T08:00:00Z"
        },
        {
          "time": 1775476800,
          "open": 0.87203,
          "high": 0.87225,
          "low": 0.87161,
          "close": 0.87201,
          "tick_volume": 7244.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-04-06T12:00:00Z"
        }
      ]
    },
    "D1": {
      "timeframe": "D1",
      "bars": [
        {
          "time": 1749340800,
          "open": 0.84262,
          "high": 0.84279,
          "low": 0.84223,
          "close": 0.84229,
          "tick_volume": 400.0,
          "spread": 50.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-06-08T00:00:00Z"
        },
        {
          "time": 1749427200,
          "open": 0.84229,
          "high": 0.84288,
          "low": 0.84143,
          "close": 0.84279,
          "tick_volume": 43958.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-06-09T00:00:00Z"
        },
        {
          "time": 1749513600,
          "open": 0.84288,
          "high": 0.84687,
          "low": 0.8418,
          "close": 0.84629,
          "tick_volume": 56337.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-06-10T00:00:00Z"
        },
        {
          "time": 1749600000,
          "open": 0.84637,
          "high": 0.84888,
          "low": 0.84627,
          "close": 0.84796,
          "tick_volume": 55062.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-06-11T00:00:00Z"
        },
        {
          "time": 1749686400,
          "open": 0.8481,
          "high": 0.85466,
          "low": 0.84773,
          "close": 0.85095,
          "tick_volume": 63835.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-06-12T00:00:00Z"
        },
        {
          "time": 1749772800,
          "open": 0.85101,
          "high": 0.85312,
          "low": 0.84933,
          "close": 0.85099,
          "tick_volume": 77419.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-06-13T00:00:00Z"
        },
        {
          "time": 1749945600,
          "open": 0.85005,
          "high": 0.85174,
          "low": 0.85005,
          "close": 0.85156,
          "tick_volume": 647.0,
          "spread": 71.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-06-15T00:00:00Z"
        },
        {
          "time": 1750032000,
          "open": 0.85125,
          "high": 0.85319,
          "low": 0.851,
          "close": 0.85137,
          "tick_volume": 64679.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-06-16T00:00:00Z"
        },
        {
          "time": 1750118400,
          "open": 0.85149,
          "high": 0.85555,
          "low": 0.8512,
          "close": 0.85503,
          "tick_volume": 68499.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-06-17T00:00:00Z"
        },
        {
          "time": 1750204800,
          "open": 0.85531,
          "high": 0.85647,
          "low": 0.85415,
          "close": 0.85506,
          "tick_volume": 73044.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-06-18T00:00:00Z"
        },
        {
          "time": 1750291200,
          "open": 0.85538,
          "high": 0.85601,
          "low": 0.85315,
          "close": 0.85384,
          "tick_volume": 57816.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-06-19T00:00:00Z"
        },
        {
          "time": 1750377600,
          "open": 0.8536,
          "high": 0.85696,
          "low": 0.8526,
          "close": 0.85695,
          "tick_volume": 63426.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-06-20T00:00:00Z"
        },
        {
          "time": 1750550400,
          "open": 0.85485,
          "high": 0.85605,
          "low": 0.85484,
          "close": 0.85576,
          "tick_volume": 669.0,
          "spread": 49.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-06-22T00:00:00Z"
        },
        {
          "time": 1750636800,
          "open": 0.85567,
          "high": 0.85751,
          "low": 0.85462,
          "close": 0.85596,
          "tick_volume": 82493.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-06-23T00:00:00Z"
        },
        {
          "time": 1750723200,
          "open": 0.85599,
          "high": 0.85667,
          "low": 0.85197,
          "close": 0.85321,
          "tick_volume": 71860.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-06-24T00:00:00Z"
        },
        {
          "time": 1750809600,
          "open": 0.85279,
          "high": 0.85385,
          "low": 0.85128,
          "close": 0.85324,
          "tick_volume": 63066.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-06-25T00:00:00Z"
        },
        {
          "time": 1750896000,
          "open": 0.85336,
          "high": 0.85396,
          "low": 0.85135,
          "close": 0.85213,
          "tick_volume": 73600.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-06-26T00:00:00Z"
        },
        {
          "time": 1750982400,
          "open": 0.85198,
          "high": 0.85529,
          "low": 0.85083,
          "close": 0.85411,
          "tick_volume": 70181.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-06-27T00:00:00Z"
        },
        {
          "time": 1751155200,
          "open": 0.85542,
          "high": 0.8558,
          "low": 0.85464,
          "close": 0.85501,
          "tick_volume": 454.0,
          "spread": 45.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-06-29T00:00:00Z"
        },
        {
          "time": 1751241600,
          "open": 0.85481,
          "high": 0.85864,
          "low": 0.85397,
          "close": 0.85828,
          "tick_volume": 65940.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-06-30T00:00:00Z"
        },
        {
          "time": 1751328000,
          "open": 0.85831,
          "high": 0.85975,
          "low": 0.85572,
          "close": 0.85874,
          "tick_volume": 63218.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-07-01T00:00:00Z"
        },
        {
          "time": 1751414400,
          "open": 0.85875,
          "high": 0.86705,
          "low": 0.85776,
          "close": 0.86394,
          "tick_volume": 65657.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-07-02T00:00:00Z"
        },
        {
          "time": 1751500800,
          "open": 0.86418,
          "high": 0.86544,
          "low": 0.86064,
          "close": 0.86108,
          "tick_volume": 57165.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-07-03T00:00:00Z"
        },
        {
          "time": 1751587200,
          "open": 0.86122,
          "high": 0.86377,
          "low": 0.86101,
          "close": 0.86362,
          "tick_volume": 66677.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-07-04T00:00:00Z"
        },
        {
          "time": 1751760000,
          "open": 0.86372,
          "high": 0.86372,
          "low": 0.86217,
          "close": 0.8626,
          "tick_volume": 717.0,
          "spread": 115.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-07-06T00:00:00Z"
        },
        {
          "time": 1751846400,
          "open": 0.86265,
          "high": 0.86436,
          "low": 0.85968,
          "close": 0.86044,
          "tick_volume": 62817.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-07-07T00:00:00Z"
        },
        {
          "time": 1751932800,
          "open": 0.8607,
          "high": 0.86432,
          "low": 0.8607,
          "close": 0.86297,
          "tick_volume": 63676.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-07-08T00:00:00Z"
        },
        {
          "time": 1752019200,
          "open": 0.86274,
          "high": 0.86317,
          "low": 0.86059,
          "close": 0.86275,
          "tick_volume": 57042.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-07-09T00:00:00Z"
        },
        {
          "time": 1752105600,
          "open": 0.86276,
          "high": 0.86342,
          "low": 0.86102,
          "close": 0.86184,
          "tick_volume": 48514.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-07-10T00:00:00Z"
        },
        {
          "time": 1752192000,
          "open": 0.86166,
          "high": 0.86672,
          "low": 0.86094,
          "close": 0.86622,
          "tick_volume": 59895.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-07-11T00:00:00Z"
        },
        {
          "time": 1752364800,
          "open": 0.86457,
          "high": 0.86534,
          "low": 0.86452,
          "close": 0.86508,
          "tick_volume": 586.0,
          "spread": 8.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-07-13T00:00:00Z"
        },
        {
          "time": 1752451200,
          "open": 0.86557,
          "high": 0.86931,
          "low": 0.86496,
          "close": 0.86825,
          "tick_volume": 52180.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-07-14T00:00:00Z"
        },
        {
          "time": 1752537600,
          "open": 0.86855,
          "high": 0.86965,
          "low": 0.86606,
          "close": 0.86668,
          "tick_volume": 52139.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-07-15T00:00:00Z"
        },
        {
          "time": 1752624000,
          "open": 0.86673,
          "high": 0.86983,
          "low": 0.86477,
          "close": 0.86716,
          "tick_volume": 65144.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-07-16T00:00:00Z"
        },
        {
          "time": 1752710400,
          "open": 0.86755,
          "high": 0.86797,
          "low": 0.86375,
          "close": 0.86443,
          "tick_volume": 51519.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-07-17T00:00:00Z"
        },
        {
          "time": 1752796800,
          "open": 0.86445,
          "high": 0.86716,
          "low": 0.86435,
          "close": 0.86682,
          "tick_volume": 46995.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-07-18T00:00:00Z"
        },
        {
          "time": 1752969600,
          "open": 0.86609,
          "high": 0.86673,
          "low": 0.86605,
          "close": 0.8667,
          "tick_volume": 945.0,
          "spread": 96.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-07-20T00:00:00Z"
        },
        {
          "time": 1753056000,
          "open": 0.86713,
          "high": 0.86741,
          "low": 0.86503,
          "close": 0.8668,
          "tick_volume": 49259.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-07-21T00:00:00Z"
        },
        {
          "time": 1753142400,
          "open": 0.86674,
          "high": 0.86939,
          "low": 0.86641,
          "close": 0.86867,
          "tick_volume": 46636.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-07-22T00:00:00Z"
        },
        {
          "time": 1753228800,
          "open": 0.86858,
          "high": 0.86868,
          "low": 0.86468,
          "close": 0.86679,
          "tick_volume": 56336.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-07-23T00:00:00Z"
        },
        {
          "time": 1753315200,
          "open": 0.86682,
          "high": 0.87103,
          "low": 0.86664,
          "close": 0.86943,
          "tick_volume": 54510.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-07-24T00:00:00Z"
        },
        {
          "time": 1753401600,
          "open": 0.86976,
          "high": 0.87435,
          "low": 0.86969,
          "close": 0.87391,
          "tick_volume": 53704.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-07-25T00:00:00Z"
        },
        {
          "time": 1753574400,
          "open": 0.87568,
          "high": 0.87572,
          "low": 0.87515,
          "close": 0.87524,
          "tick_volume": 199.0,
          "spread": 9.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-07-27T00:00:00Z"
        },
        {
          "time": 1753660800,
          "open": 0.87522,
          "high": 0.87534,
          "low": 0.86658,
          "close": 0.86753,
          "tick_volume": 59680.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-07-28T00:00:00Z"
        },
        {
          "time": 1753747200,
          "open": 0.86764,
          "high": 0.86853,
          "low": 0.86418,
          "close": 0.86516,
          "tick_volume": 63122.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-07-29T00:00:00Z"
        },
        {
          "time": 1753833600,
          "open": 0.86496,
          "high": 0.86591,
          "low": 0.86119,
          "close": 0.86159,
          "tick_volume": 66407.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-07-30T00:00:00Z"
        },
        {
          "time": 1753920000,
          "open": 0.86166,
          "high": 0.86595,
          "low": 0.8611,
          "close": 0.86467,
          "tick_volume": 65380.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-07-31T00:00:00Z"
        },
        {
          "time": 1754006400,
          "open": 0.86475,
          "high": 0.87303,
          "low": 0.86439,
          "close": 0.87259,
          "tick_volume": 79551.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-08-01T00:00:00Z"
        },
        {
          "time": 1754179200,
          "open": 0.8726,
          "high": 0.87305,
          "low": 0.87254,
          "close": 0.87269,
          "tick_volume": 635.0,
          "spread": 57.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-08-03T00:00:00Z"
        },
        {
          "time": 1754265600,
          "open": 0.87283,
          "high": 0.873,
          "low": 0.86869,
          "close": 0.87105,
          "tick_volume": 67400.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-08-04T00:00:00Z"
        },
        {
          "time": 1754352000,
          "open": 0.87109,
          "high": 0.87131,
          "low": 0.86797,
          "close": 0.8704,
          "tick_volume": 62911.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-08-05T00:00:00Z"
        },
        {
          "time": 1754438400,
          "open": 0.87053,
          "high": 0.8732,
          "low": 0.86967,
          "close": 0.87272,
          "tick_volume": 57545.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-08-06T00:00:00Z"
        },
        {
          "time": 1754524800,
          "open": 0.87292,
          "high": 0.87439,
          "low": 0.86638,
          "close": 0.86792,
          "tick_volume": 62265.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-08-07T00:00:00Z"
        },
        {
          "time": 1754611200,
          "open": 0.86794,
          "high": 0.8682,
          "low": 0.86531,
          "close": 0.86586,
          "tick_volume": 53830.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-08-08T00:00:00Z"
        },
        {
          "time": 1754784000,
          "open": 0.8662,
          "high": 0.86671,
          "low": 0.86581,
          "close": 0.86659,
          "tick_volume": 427.0,
          "spread": 41.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-08-10T00:00:00Z"
        },
        {
          "time": 1754870400,
          "open": 0.86625,
          "high": 0.86724,
          "low": 0.86418,
          "close": 0.86487,
          "tick_volume": 48631.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-08-11T00:00:00Z"
        },
        {
          "time": 1754956800,
          "open": 0.86489,
          "high": 0.86547,
          "low": 0.86186,
          "close": 0.86474,
          "tick_volume": 59715.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-08-12T00:00:00Z"
        },
        {
          "time": 1755043200,
          "open": 0.86475,
          "high": 0.86538,
          "low": 0.86185,
          "close": 0.86236,
          "tick_volume": 50644.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-08-13T00:00:00Z"
        },
        {
          "time": 1755129600,
          "open": 0.86213,
          "high": 0.86251,
          "low": 0.85966,
          "close": 0.86114,
          "tick_volume": 57088.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-08-14T00:00:00Z"
        },
        {
          "time": 1755216000,
          "open": 0.86107,
          "high": 0.86382,
          "low": 0.86058,
          "close": 0.8634,
          "tick_volume": 43671.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-08-15T00:00:00Z"
        },
        {
          "time": 1755388800,
          "open": 0.8641,
          "high": 0.86422,
          "low": 0.86337,
          "close": 0.86362,
          "tick_volume": 656.0,
          "spread": 35.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-08-17T00:00:00Z"
        },
        {
          "time": 1755475200,
          "open": 0.86367,
          "high": 0.86401,
          "low": 0.86187,
          "close": 0.86343,
          "tick_volume": 45029.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-08-18T00:00:00Z"
        },
        {
          "time": 1755561600,
          "open": 0.86356,
          "high": 0.86481,
          "low": 0.86295,
          "close": 0.86356,
          "tick_volume": 44220.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-08-19T00:00:00Z"
        },
        {
          "time": 1755648000,
          "open": 0.86332,
          "high": 0.86672,
          "low": 0.86085,
          "close": 0.8658,
          "tick_volume": 52123.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-08-20T00:00:00Z"
        },
        {
          "time": 1755734400,
          "open": 0.86608,
          "high": 0.8666,
          "low": 0.8646,
          "close": 0.86553,
          "tick_volume": 51759.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-08-21T00:00:00Z"
        },
        {
          "time": 1755820800,
          "open": 0.86538,
          "high": 0.86722,
          "low": 0.86398,
          "close": 0.86689,
          "tick_volume": 53729.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-08-22T00:00:00Z"
        },
        {
          "time": 1755993600,
          "open": 0.8671,
          "high": 0.86739,
          "low": 0.86647,
          "close": 0.86727,
          "tick_volume": 1675.0,
          "spread": 20.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-08-24T00:00:00Z"
        },
        {
          "time": 1756080000,
          "open": 0.86702,
          "high": 0.86712,
          "low": 0.86274,
          "close": 0.86334,
          "tick_volume": 47395.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-08-25T00:00:00Z"
        },
        {
          "time": 1756166400,
          "open": 0.86353,
          "high": 0.86497,
          "low": 0.86231,
          "close": 0.86394,
          "tick_volume": 63990.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-08-26T00:00:00Z"
        },
        {
          "time": 1756252800,
          "open": 0.86388,
          "high": 0.86406,
          "low": 0.86097,
          "close": 0.86227,
          "tick_volume": 49571.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-08-27T00:00:00Z"
        },
        {
          "time": 1756339200,
          "open": 0.86242,
          "high": 0.86487,
          "low": 0.86153,
          "close": 0.86455,
          "tick_volume": 50575.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-08-28T00:00:00Z"
        },
        {
          "time": 1756425600,
          "open": 0.86447,
          "high": 0.8674,
          "low": 0.86356,
          "close": 0.8654,
          "tick_volume": 51858.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-08-29T00:00:00Z"
        },
        {
          "time": 1756598400,
          "open": 0.86652,
          "high": 0.86652,
          "low": 0.8653,
          "close": 0.86553,
          "tick_volume": 624.0,
          "spread": 25.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-08-31T00:00:00Z"
        },
        {
          "time": 1756684800,
          "open": 0.86558,
          "high": 0.86703,
          "low": 0.86379,
          "close": 0.8646,
          "tick_volume": 38289.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-09-01T00:00:00Z"
        },
        {
          "time": 1756771200,
          "open": 0.86456,
          "high": 0.87129,
          "low": 0.86418,
          "close": 0.86917,
          "tick_volume": 67654.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-09-02T00:00:00Z"
        },
        {
          "time": 1756857600,
          "open": 0.86919,
          "high": 0.87115,
          "low": 0.86722,
          "close": 0.86761,
          "tick_volume": 58524.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-09-03T00:00:00Z"
        },
        {
          "time": 1756944000,
          "open": 0.86753,
          "high": 0.8681,
          "low": 0.86597,
          "close": 0.86712,
          "tick_volume": 48787.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-09-04T00:00:00Z"
        },
        {
          "time": 1757030400,
          "open": 0.86719,
          "high": 0.86874,
          "low": 0.86651,
          "close": 0.86733,
          "tick_volume": 57674.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-09-05T00:00:00Z"
        },
        {
          "time": 1757203200,
          "open": 0.86748,
          "high": 0.86806,
          "low": 0.86733,
          "close": 0.86806,
          "tick_volume": 472.0,
          "spread": 30.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-09-07T00:00:00Z"
        },
        {
          "time": 1757289600,
          "open": 0.86776,
          "high": 0.86843,
          "low": 0.86627,
          "close": 0.86825,
          "tick_volume": 52668.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-09-08T00:00:00Z"
        },
        {
          "time": 1757376000,
          "open": 0.86832,
          "high": 0.86845,
          "low": 0.86552,
          "close": 0.86578,
          "tick_volume": 54383.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-09-09T00:00:00Z"
        },
        {
          "time": 1757462400,
          "open": 0.86579,
          "high": 0.86598,
          "low": 0.86399,
          "close": 0.86486,
          "tick_volume": 55519.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-09-10T00:00:00Z"
        },
        {
          "time": 1757548800,
          "open": 0.86455,
          "high": 0.86627,
          "low": 0.86354,
          "close": 0.86458,
          "tick_volume": 59258.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-09-11T00:00:00Z"
        },
        {
          "time": 1757635200,
          "open": 0.86449,
          "high": 0.86647,
          "low": 0.86401,
          "close": 0.86536,
          "tick_volume": 51872.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-09-12T00:00:00Z"
        },
        {
          "time": 1757808000,
          "open": 0.86523,
          "high": 0.86597,
          "low": 0.86476,
          "close": 0.86525,
          "tick_volume": 1477.0,
          "spread": 18.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-09-14T00:00:00Z"
        },
        {
          "time": 1757894400,
          "open": 0.86528,
          "high": 0.86545,
          "low": 0.86325,
          "close": 0.86479,
          "tick_volume": 46839.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-09-15T00:00:00Z"
        },
        {
          "time": 1757980800,
          "open": 0.86494,
          "high": 0.86968,
          "low": 0.86451,
          "close": 0.86918,
          "tick_volume": 59964.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-09-16T00:00:00Z"
        },
        {
          "time": 1758067200,
          "open": 0.86963,
          "high": 0.86967,
          "low": 0.8661,
          "close": 0.8671,
          "tick_volume": 61034.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-09-17T00:00:00Z"
        },
        {
          "time": 1758153600,
          "open": 0.86712,
          "high": 0.8699,
          "low": 0.86648,
          "close": 0.86958,
          "tick_volume": 65149.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-09-18T00:00:00Z"
        },
        {
          "time": 1758240000,
          "open": 0.86967,
          "high": 0.87288,
          "low": 0.86901,
          "close": 0.87203,
          "tick_volume": 60758.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-09-19T00:00:00Z"
        },
        {
          "time": 1758412800,
          "open": 0.8715,
          "high": 0.87231,
          "low": 0.8715,
          "close": 0.87222,
          "tick_volume": 1912.0,
          "spread": 11.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-09-21T00:00:00Z"
        },
        {
          "time": 1758499200,
          "open": 0.87218,
          "high": 0.87345,
          "low": 0.87089,
          "close": 0.87331,
          "tick_volume": 48724.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-09-22T00:00:00Z"
        },
        {
          "time": 1758585600,
          "open": 0.87337,
          "high": 0.87456,
          "low": 0.87173,
          "close": 0.87377,
          "tick_volume": 55253.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-09-23T00:00:00Z"
        },
        {
          "time": 1758672000,
          "open": 0.87374,
          "high": 0.87452,
          "low": 0.87228,
          "close": 0.87308,
          "tick_volume": 54016.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-09-24T00:00:00Z"
        },
        {
          "time": 1758758400,
          "open": 0.87301,
          "high": 0.87511,
          "low": 0.87229,
          "close": 0.87416,
          "tick_volume": 58398.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-09-25T00:00:00Z"
        },
        {
          "time": 1758844800,
          "open": 0.87437,
          "high": 0.87487,
          "low": 0.87209,
          "close": 0.8731,
          "tick_volume": 50501.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-09-26T00:00:00Z"
        },
        {
          "time": 1759017600,
          "open": 0.87316,
          "high": 0.87363,
          "low": 0.87314,
          "close": 0.87317,
          "tick_volume": 1253.0,
          "spread": 19.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-09-28T00:00:00Z"
        },
        {
          "time": 1759104000,
          "open": 0.8732,
          "high": 0.87447,
          "low": 0.87154,
          "close": 0.87339,
          "tick_volume": 48720.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-09-29T00:00:00Z"
        },
        {
          "time": 1759190400,
          "open": 0.87304,
          "high": 0.87452,
          "low": 0.87231,
          "close": 0.87263,
          "tick_volume": 55857.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-09-30T00:00:00Z"
        },
        {
          "time": 1759276800,
          "open": 0.87281,
          "high": 0.8742,
          "low": 0.86895,
          "close": 0.87036,
          "tick_volume": 63462.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-10-01T00:00:00Z"
        },
        {
          "time": 1759363200,
          "open": 0.87047,
          "high": 0.87297,
          "low": 0.87018,
          "close": 0.87205,
          "tick_volume": 50932.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-10-02T00:00:00Z"
        },
        {
          "time": 1759449600,
          "open": 0.87181,
          "high": 0.87298,
          "low": 0.87071,
          "close": 0.87108,
          "tick_volume": 44253.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-10-03T00:00:00Z"
        },
        {
          "time": 1759622400,
          "open": 0.87244,
          "high": 0.87244,
          "low": 0.87168,
          "close": 0.87221,
          "tick_volume": 622.0,
          "spread": 26.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-10-05T00:00:00Z"
        },
        {
          "time": 1759708800,
          "open": 0.87222,
          "high": 0.87283,
          "low": 0.86737,
          "close": 0.86855,
          "tick_volume": 61411.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-10-06T00:00:00Z"
        },
        {
          "time": 1759795200,
          "open": 0.86873,
          "high": 0.87048,
          "low": 0.86758,
          "close": 0.86772,
          "tick_volume": 53299.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-10-07T00:00:00Z"
        },
        {
          "time": 1759881600,
          "open": 0.86836,
          "high": 0.86849,
          "low": 0.8656,
          "close": 0.86783,
          "tick_volume": 57913.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-10-08T00:00:00Z"
        },
        {
          "time": 1759968000,
          "open": 0.86768,
          "high": 0.86986,
          "low": 0.86745,
          "close": 0.86929,
          "tick_volume": 64097.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-10-09T00:00:00Z"
        },
        {
          "time": 1760054400,
          "open": 0.86917,
          "high": 0.87252,
          "low": 0.86911,
          "close": 0.87012,
          "tick_volume": 66214.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-10-10T00:00:00Z"
        },
        {
          "time": 1760227200,
          "open": 0.86989,
          "high": 0.87096,
          "low": 0.86964,
          "close": 0.8708,
          "tick_volume": 1114.0,
          "spread": 30.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-10-12T00:00:00Z"
        },
        {
          "time": 1760313600,
          "open": 0.87023,
          "high": 0.87073,
          "low": 0.86717,
          "close": 0.86764,
          "tick_volume": 56763.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-10-13T00:00:00Z"
        },
        {
          "time": 1760400000,
          "open": 0.86777,
          "high": 0.87222,
          "low": 0.86668,
          "close": 0.87181,
          "tick_volume": 88165.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-10-14T00:00:00Z"
        },
        {
          "time": 1760486400,
          "open": 0.87159,
          "high": 0.87212,
          "low": 0.86839,
          "close": 0.86952,
          "tick_volume": 98859.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-10-15T00:00:00Z"
        },
        {
          "time": 1760572800,
          "open": 0.86911,
          "high": 0.87045,
          "low": 0.86643,
          "close": 0.86992,
          "tick_volume": 118922.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-10-16T00:00:00Z"
        },
        {
          "time": 1760659200,
          "open": 0.86992,
          "high": 0.8725,
          "low": 0.8678,
          "close": 0.86797,
          "tick_volume": 123166.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-10-17T00:00:00Z"
        },
        {
          "time": 1760832000,
          "open": 0.86874,
          "high": 0.86903,
          "low": 0.86826,
          "close": 0.86827,
          "tick_volume": 666.0,
          "spread": 24.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-10-19T00:00:00Z"
        },
        {
          "time": 1760918400,
          "open": 0.8683,
          "high": 0.86953,
          "low": 0.86735,
          "close": 0.8685,
          "tick_volume": 96633.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-10-20T00:00:00Z"
        },
        {
          "time": 1761004800,
          "open": 0.86848,
          "high": 0.86943,
          "low": 0.86701,
          "close": 0.86797,
          "tick_volume": 127236.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-10-21T00:00:00Z"
        },
        {
          "time": 1761091200,
          "open": 0.86781,
          "high": 0.87126,
          "low": 0.86757,
          "close": 0.86949,
          "tick_volume": 121052.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-10-22T00:00:00Z"
        },
        {
          "time": 1761177600,
          "open": 0.86933,
          "high": 0.87215,
          "low": 0.86817,
          "close": 0.87182,
          "tick_volume": 88036.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-10-23T00:00:00Z"
        },
        {
          "time": 1761264000,
          "open": 0.87186,
          "high": 0.87471,
          "low": 0.87057,
          "close": 0.87377,
          "tick_volume": 110926.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-10-24T00:00:00Z"
        },
        {
          "time": 1761436800,
          "open": 0.87302,
          "high": 0.87361,
          "low": 0.87269,
          "close": 0.87282,
          "tick_volume": 3457.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-10-26T00:00:00Z"
        },
        {
          "time": 1761523200,
          "open": 0.87281,
          "high": 0.87366,
          "low": 0.872,
          "close": 0.87335,
          "tick_volume": 91602.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-10-27T00:00:00Z"
        },
        {
          "time": 1761609600,
          "open": 0.87335,
          "high": 0.87898,
          "low": 0.87256,
          "close": 0.87785,
          "tick_volume": 110422.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-10-28T00:00:00Z"
        },
        {
          "time": 1761696000,
          "open": 0.87787,
          "high": 0.88181,
          "low": 0.87775,
          "close": 0.87951,
          "tick_volume": 137108.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-10-29T00:00:00Z"
        },
        {
          "time": 1761782400,
          "open": 0.87953,
          "high": 0.88134,
          "low": 0.87888,
          "close": 0.87947,
          "tick_volume": 124402.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-10-30T00:00:00Z"
        },
        {
          "time": 1761868800,
          "open": 0.87947,
          "high": 0.88178,
          "low": 0.87706,
          "close": 0.87719,
          "tick_volume": 101481.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-10-31T00:00:00Z"
        },
        {
          "time": 1762041600,
          "open": 0.87826,
          "high": 0.87826,
          "low": 0.87753,
          "close": 0.87763,
          "tick_volume": 746.0,
          "spread": 7.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-11-02T00:00:00Z"
        },
        {
          "time": 1762128000,
          "open": 0.87764,
          "high": 0.87838,
          "low": 0.87629,
          "close": 0.877,
          "tick_volume": 96784.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-11-03T00:00:00Z"
        },
        {
          "time": 1762214400,
          "open": 0.87689,
          "high": 0.88215,
          "low": 0.87647,
          "close": 0.88152,
          "tick_volume": 109011.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-11-04T00:00:00Z"
        },
        {
          "time": 1762300800,
          "open": 0.88176,
          "high": 0.88297,
          "low": 0.87994,
          "close": 0.88078,
          "tick_volume": 100375.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-11-05T00:00:00Z"
        },
        {
          "time": 1762387200,
          "open": 0.88072,
          "high": 0.88187,
          "low": 0.87873,
          "close": 0.87928,
          "tick_volume": 106480.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-11-06T00:00:00Z"
        },
        {
          "time": 1762473600,
          "open": 0.87919,
          "high": 0.88163,
          "low": 0.87828,
          "close": 0.87882,
          "tick_volume": 98301.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-11-07T00:00:00Z"
        },
        {
          "time": 1762646400,
          "open": 0.87832,
          "high": 0.87876,
          "low": 0.87819,
          "close": 0.87864,
          "tick_volume": 791.0,
          "spread": 20.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-11-09T00:00:00Z"
        },
        {
          "time": 1762732800,
          "open": 0.87847,
          "high": 0.87946,
          "low": 0.8769,
          "close": 0.8774,
          "tick_volume": 102047.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-11-10T00:00:00Z"
        },
        {
          "time": 1762819200,
          "open": 0.87727,
          "high": 0.88132,
          "low": 0.87715,
          "close": 0.88042,
          "tick_volume": 107924.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-11-11T00:00:00Z"
        },
        {
          "time": 1762905600,
          "open": 0.88085,
          "high": 0.88386,
          "low": 0.88046,
          "close": 0.88271,
          "tick_volume": 93542.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-11-12T00:00:00Z"
        },
        {
          "time": 1762992000,
          "open": 0.88293,
          "high": 0.88436,
          "low": 0.88155,
          "close": 0.88392,
          "tick_volume": 119572.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-11-13T00:00:00Z"
        },
        {
          "time": 1763078400,
          "open": 0.88337,
          "high": 0.88654,
          "low": 0.88129,
          "close": 0.88223,
          "tick_volume": 131840.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-11-14T00:00:00Z"
        },
        {
          "time": 1763251200,
          "open": 0.88338,
          "high": 0.88349,
          "low": 0.88241,
          "close": 0.88267,
          "tick_volume": 1168.0,
          "spread": 22.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-11-16T00:00:00Z"
        },
        {
          "time": 1763337600,
          "open": 0.88244,
          "high": 0.88291,
          "low": 0.87926,
          "close": 0.88096,
          "tick_volume": 98553.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-11-17T00:00:00Z"
        },
        {
          "time": 1763424000,
          "open": 0.8812,
          "high": 0.88241,
          "low": 0.88043,
          "close": 0.88059,
          "tick_volume": 118064.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-11-18T00:00:00Z"
        },
        {
          "time": 1763510400,
          "open": 0.8809,
          "high": 0.88405,
          "low": 0.88075,
          "close": 0.88359,
          "tick_volume": 118672.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-11-19T00:00:00Z"
        },
        {
          "time": 1763596800,
          "open": 0.88362,
          "high": 0.88403,
          "low": 0.87956,
          "close": 0.88189,
          "tick_volume": 119859.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-11-20T00:00:00Z"
        },
        {
          "time": 1763683200,
          "open": 0.88173,
          "high": 0.88315,
          "low": 0.87803,
          "close": 0.87903,
          "tick_volume": 143394.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-11-21T00:00:00Z"
        },
        {
          "time": 1763856000,
          "open": 0.87888,
          "high": 0.87888,
          "low": 0.87838,
          "close": 0.87881,
          "tick_volume": 785.0,
          "spread": 34.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-11-23T00:00:00Z"
        },
        {
          "time": 1763942400,
          "open": 0.87899,
          "high": 0.88201,
          "low": 0.87864,
          "close": 0.87912,
          "tick_volume": 111977.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-11-24T00:00:00Z"
        },
        {
          "time": 1764028800,
          "open": 0.87918,
          "high": 0.8799,
          "low": 0.87657,
          "close": 0.87869,
          "tick_volume": 120230.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-11-25T00:00:00Z"
        },
        {
          "time": 1764115200,
          "open": 0.87869,
          "high": 0.88184,
          "low": 0.87548,
          "close": 0.87595,
          "tick_volume": 139329.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-11-26T00:00:00Z"
        },
        {
          "time": 1764201600,
          "open": 0.87585,
          "high": 0.87705,
          "low": 0.8746,
          "close": 0.87608,
          "tick_volume": 75010.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-11-27T00:00:00Z"
        },
        {
          "time": 1764288000,
          "open": 0.87612,
          "high": 0.8773,
          "low": 0.87474,
          "close": 0.87656,
          "tick_volume": 293013.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-11-28T00:00:00Z"
        },
        {
          "time": 1764460800,
          "open": 0.87674,
          "high": 0.87699,
          "low": 0.87582,
          "close": 0.87672,
          "tick_volume": 2403.0,
          "spread": 13.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-11-30T00:00:00Z"
        },
        {
          "time": 1764547200,
          "open": 0.87662,
          "high": 0.87939,
          "low": 0.87596,
          "close": 0.87864,
          "tick_volume": 131621.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-12-01T00:00:00Z"
        },
        {
          "time": 1764633600,
          "open": 0.87865,
          "high": 0.88035,
          "low": 0.87837,
          "close": 0.8802,
          "tick_volume": 96838.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-12-02T00:00:00Z"
        },
        {
          "time": 1764720000,
          "open": 0.8798,
          "high": 0.87992,
          "low": 0.87372,
          "close": 0.87416,
          "tick_volume": 115135.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-12-03T00:00:00Z"
        },
        {
          "time": 1764806400,
          "open": 0.87421,
          "high": 0.87541,
          "low": 0.87217,
          "close": 0.87396,
          "tick_volume": 115366.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-12-04T00:00:00Z"
        },
        {
          "time": 1764892800,
          "open": 0.87376,
          "high": 0.87417,
          "low": 0.87247,
          "close": 0.87357,
          "tick_volume": 96182.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-12-05T00:00:00Z"
        },
        {
          "time": 1765065600,
          "open": 0.87322,
          "high": 0.87369,
          "low": 0.87316,
          "close": 0.87356,
          "tick_volume": 1508.0,
          "spread": 43.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-12-07T00:00:00Z"
        },
        {
          "time": 1765152000,
          "open": 0.87386,
          "high": 0.87527,
          "low": 0.87253,
          "close": 0.87363,
          "tick_volume": 94942.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-12-08T00:00:00Z"
        },
        {
          "time": 1765238400,
          "open": 0.8736,
          "high": 0.87474,
          "low": 0.87205,
          "close": 0.87411,
          "tick_volume": 104007.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-12-09T00:00:00Z"
        },
        {
          "time": 1765324800,
          "open": 0.87412,
          "high": 0.87513,
          "low": 0.8728,
          "close": 0.87401,
          "tick_volume": 114730.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-12-10T00:00:00Z"
        },
        {
          "time": 1765411200,
          "open": 0.87403,
          "high": 0.87709,
          "low": 0.87387,
          "close": 0.87654,
          "tick_volume": 109807.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-12-11T00:00:00Z"
        },
        {
          "time": 1765497600,
          "open": 0.87662,
          "high": 0.87924,
          "low": 0.87609,
          "close": 0.87799,
          "tick_volume": 102188.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-12-12T00:00:00Z"
        },
        {
          "time": 1765670400,
          "open": 0.87733,
          "high": 0.87817,
          "low": 0.87733,
          "close": 0.8778,
          "tick_volume": 1838.0,
          "spread": 10.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-12-14T00:00:00Z"
        },
        {
          "time": 1765756800,
          "open": 0.87788,
          "high": 0.87924,
          "low": 0.87708,
          "close": 0.87866,
          "tick_volume": 94430.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-12-15T00:00:00Z"
        },
        {
          "time": 1765843200,
          "open": 0.87872,
          "high": 0.87957,
          "low": 0.87469,
          "close": 0.87519,
          "tick_volume": 120963.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-12-16T00:00:00Z"
        },
        {
          "time": 1765929600,
          "open": 0.87523,
          "high": 0.8797,
          "low": 0.875,
          "close": 0.87751,
          "tick_volume": 114003.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-12-17T00:00:00Z"
        },
        {
          "time": 1766016000,
          "open": 0.87781,
          "high": 0.87875,
          "low": 0.87354,
          "close": 0.8762,
          "tick_volume": 116352.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-12-18T00:00:00Z"
        },
        {
          "time": 1766102400,
          "open": 0.87608,
          "high": 0.8774,
          "low": 0.87498,
          "close": 0.87533,
          "tick_volume": 99321.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-12-19T00:00:00Z"
        },
        {
          "time": 1766275200,
          "open": 0.87549,
          "high": 0.87558,
          "low": 0.87512,
          "close": 0.87544,
          "tick_volume": 1200.0,
          "spread": 34.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-12-21T00:00:00Z"
        },
        {
          "time": 1766361600,
          "open": 0.87559,
          "high": 0.87572,
          "low": 0.87262,
          "close": 0.87346,
          "tick_volume": 110040.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-12-22T00:00:00Z"
        },
        {
          "time": 1766448000,
          "open": 0.87361,
          "high": 0.87375,
          "low": 0.872,
          "close": 0.87292,
          "tick_volume": 101473.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-12-23T00:00:00Z"
        },
        {
          "time": 1766534400,
          "open": 0.87276,
          "high": 0.87315,
          "low": 0.87189,
          "close": 0.87212,
          "tick_volume": 97262.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-12-24T00:00:00Z"
        },
        {
          "time": 1766620800,
          "open": 0.87125,
          "high": 0.87185,
          "low": 0.87099,
          "close": 0.87171,
          "tick_volume": 904.0,
          "spread": 43.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-12-25T00:00:00Z"
        },
        {
          "time": 1766707200,
          "open": 0.87223,
          "high": 0.87361,
          "low": 0.87165,
          "close": 0.87202,
          "tick_volume": 117713.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-12-26T00:00:00Z"
        },
        {
          "time": 1766880000,
          "open": 0.87188,
          "high": 0.87258,
          "low": 0.87181,
          "close": 0.87196,
          "tick_volume": 1000.0,
          "spread": 52.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-12-28T00:00:00Z"
        },
        {
          "time": 1766966400,
          "open": 0.87258,
          "high": 0.87402,
          "low": 0.87096,
          "close": 0.87165,
          "tick_volume": 111762.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-12-29T00:00:00Z"
        },
        {
          "time": 1767052800,
          "open": 0.87141,
          "high": 0.87365,
          "low": 0.87029,
          "close": 0.87224,
          "tick_volume": 87633.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-12-30T00:00:00Z"
        },
        {
          "time": 1767139200,
          "open": 0.87239,
          "high": 0.87461,
          "low": 0.87152,
          "close": 0.8718,
          "tick_volume": 100041.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-12-31T00:00:00Z"
        },
        {
          "time": 1767225600,
          "open": 0.87241,
          "high": 0.87324,
          "low": 0.87202,
          "close": 0.87238,
          "tick_volume": 1401.0,
          "spread": 21.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-01T00:00:00Z"
        },
        {
          "time": 1767312000,
          "open": 0.87202,
          "high": 0.87253,
          "low": 0.87007,
          "close": 0.87091,
          "tick_volume": 84261.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-02T00:00:00Z"
        },
        {
          "time": 1767484800,
          "open": 0.87156,
          "high": 0.87156,
          "low": 0.87045,
          "close": 0.87056,
          "tick_volume": 1244.0,
          "spread": 25.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-04T00:00:00Z"
        },
        {
          "time": 1767571200,
          "open": 0.87047,
          "high": 0.87109,
          "low": 0.8653,
          "close": 0.86533,
          "tick_volume": 111646.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-05T00:00:00Z"
        },
        {
          "time": 1767657600,
          "open": 0.86557,
          "high": 0.86635,
          "low": 0.86443,
          "close": 0.86578,
          "tick_volume": 106047.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-06T00:00:00Z"
        },
        {
          "time": 1767744000,
          "open": 0.86576,
          "high": 0.86789,
          "low": 0.86539,
          "close": 0.86751,
          "tick_volume": 97401.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-07T00:00:00Z"
        },
        {
          "time": 1767830400,
          "open": 0.86766,
          "high": 0.86912,
          "low": 0.86704,
          "close": 0.86786,
          "tick_volume": 92187.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-08T00:00:00Z"
        },
        {
          "time": 1767916800,
          "open": 0.86767,
          "high": 0.86867,
          "low": 0.86668,
          "close": 0.86812,
          "tick_volume": 105051.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-09T00:00:00Z"
        },
        {
          "time": 1768089600,
          "open": 0.86825,
          "high": 0.86841,
          "low": 0.86766,
          "close": 0.86832,
          "tick_volume": 958.0,
          "spread": 50.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-11T00:00:00Z"
        },
        {
          "time": 1768176000,
          "open": 0.86833,
          "high": 0.86927,
          "low": 0.86625,
          "close": 0.86667,
          "tick_volume": 100152.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-12T00:00:00Z"
        },
        {
          "time": 1768262400,
          "open": 0.86644,
          "high": 0.86759,
          "low": 0.86517,
          "close": 0.86734,
          "tick_volume": 95147.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-13T00:00:00Z"
        },
        {
          "time": 1768348800,
          "open": 0.86734,
          "high": 0.86743,
          "low": 0.86571,
          "close": 0.86661,
          "tick_volume": 96645.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-14T00:00:00Z"
        },
        {
          "time": 1768435200,
          "open": 0.8663,
          "high": 0.86789,
          "low": 0.86533,
          "close": 0.86756,
          "tick_volume": 94646.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-15T00:00:00Z"
        },
        {
          "time": 1768521600,
          "open": 0.86751,
          "high": 0.86801,
          "low": 0.86607,
          "close": 0.867,
          "tick_volume": 96836.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-16T00:00:00Z"
        },
        {
          "time": 1768694400,
          "open": 0.86703,
          "high": 0.86785,
          "low": 0.86691,
          "close": 0.86754,
          "tick_volume": 1367.0,
          "spread": 28.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-18T00:00:00Z"
        },
        {
          "time": 1768780800,
          "open": 0.86746,
          "high": 0.86861,
          "low": 0.86661,
          "close": 0.86764,
          "tick_volume": 92171.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-19T00:00:00Z"
        },
        {
          "time": 1768867200,
          "open": 0.86743,
          "high": 0.87315,
          "low": 0.86699,
          "close": 0.87171,
          "tick_volume": 135448.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-20T00:00:00Z"
        },
        {
          "time": 1768953600,
          "open": 0.87219,
          "high": 0.87457,
          "low": 0.86978,
          "close": 0.87004,
          "tick_volume": 124730.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-21T00:00:00Z"
        },
        {
          "time": 1769040000,
          "open": 0.87013,
          "high": 0.8733,
          "low": 0.86929,
          "close": 0.87064,
          "tick_volume": 108990.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-22T00:00:00Z"
        },
        {
          "time": 1769126400,
          "open": 0.87062,
          "high": 0.8709,
          "low": 0.86583,
          "close": 0.86677,
          "tick_volume": 122614.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-23T00:00:00Z"
        },
        {
          "time": 1769299200,
          "open": 0.86797,
          "high": 0.86945,
          "low": 0.86713,
          "close": 0.8692,
          "tick_volume": 1620.0,
          "spread": 13.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-25T00:00:00Z"
        },
        {
          "time": 1769385600,
          "open": 0.8695,
          "high": 0.86973,
          "low": 0.86683,
          "close": 0.86852,
          "tick_volume": 146558.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-26T00:00:00Z"
        },
        {
          "time": 1769472000,
          "open": 0.86857,
          "high": 0.8717,
          "low": 0.86705,
          "close": 0.86979,
          "tick_volume": 157197.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-27T00:00:00Z"
        },
        {
          "time": 1769558400,
          "open": 0.86979,
          "high": 0.86989,
          "low": 0.86492,
          "close": 0.86639,
          "tick_volume": 173648.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-28T00:00:00Z"
        },
        {
          "time": 1769644800,
          "open": 0.86603,
          "high": 0.86713,
          "low": 0.86496,
          "close": 0.8668,
          "tick_volume": 173287.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-29T00:00:00Z"
        },
        {
          "time": 1769731200,
          "open": 0.86674,
          "high": 0.86754,
          "low": 0.86551,
          "close": 0.86576,
          "tick_volume": 200485.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-30T00:00:00Z"
        },
        {
          "time": 1769904000,
          "open": 0.86518,
          "high": 0.86633,
          "low": 0.86512,
          "close": 0.86578,
          "tick_volume": 2588.0,
          "spread": 11.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-01T00:00:00Z"
        },
        {
          "time": 1769990400,
          "open": 0.86586,
          "high": 0.8674,
          "low": 0.86252,
          "close": 0.86264,
          "tick_volume": 189483.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-02T00:00:00Z"
        },
        {
          "time": 1770076800,
          "open": 0.86287,
          "high": 0.86368,
          "low": 0.86199,
          "close": 0.86276,
          "tick_volume": 127694.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-03T00:00:00Z"
        },
        {
          "time": 1770163200,
          "open": 0.86283,
          "high": 0.86503,
          "low": 0.86126,
          "close": 0.86479,
          "tick_volume": 130334.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-04T00:00:00Z"
        },
        {
          "time": 1770249600,
          "open": 0.86484,
          "high": 0.87212,
          "low": 0.86457,
          "close": 0.87026,
          "tick_volume": 142047.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-05T00:00:00Z"
        },
        {
          "time": 1770336000,
          "open": 0.87052,
          "high": 0.87137,
          "low": 0.86729,
          "close": 0.8681,
          "tick_volume": 102971.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-06T00:00:00Z"
        },
        {
          "time": 1770508800,
          "open": 0.86876,
          "high": 0.86876,
          "low": 0.86834,
          "close": 0.8686,
          "tick_volume": 593.0,
          "spread": 25.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-08T00:00:00Z"
        },
        {
          "time": 1770595200,
          "open": 0.86866,
          "high": 0.87418,
          "low": 0.8683,
          "close": 0.87019,
          "tick_volume": 122398.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-09T00:00:00Z"
        },
        {
          "time": 1770681600,
          "open": 0.86983,
          "high": 0.87218,
          "low": 0.86862,
          "close": 0.87171,
          "tick_volume": 108210.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-10T00:00:00Z"
        },
        {
          "time": 1770768000,
          "open": 0.87193,
          "high": 0.87239,
          "low": 0.8683,
          "close": 0.87151,
          "tick_volume": 122961.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-11T00:00:00Z"
        },
        {
          "time": 1770854400,
          "open": 0.87146,
          "high": 0.87176,
          "low": 0.86941,
          "close": 0.87166,
          "tick_volume": 118656.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-12T00:00:00Z"
        },
        {
          "time": 1770940800,
          "open": 0.87147,
          "high": 0.87215,
          "low": 0.86912,
          "close": 0.86927,
          "tick_volume": 104367.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-13T00:00:00Z"
        },
        {
          "time": 1771113600,
          "open": 0.87016,
          "high": 0.87016,
          "low": 0.86971,
          "close": 0.86992,
          "tick_volume": 2611.0,
          "spread": 31.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-15T00:00:00Z"
        },
        {
          "time": 1771200000,
          "open": 0.86974,
          "high": 0.86999,
          "low": 0.8687,
          "close": 0.86915,
          "tick_volume": 57025.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-16T00:00:00Z"
        },
        {
          "time": 1771286400,
          "open": 0.86947,
          "high": 0.87492,
          "low": 0.86946,
          "close": 0.87394,
          "tick_volume": 96136.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-17T00:00:00Z"
        },
        {
          "time": 1771372800,
          "open": 0.87366,
          "high": 0.87387,
          "low": 0.87171,
          "close": 0.87296,
          "tick_volume": 84547.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-18T00:00:00Z"
        },
        {
          "time": 1771459200,
          "open": 0.87322,
          "high": 0.87518,
          "low": 0.87315,
          "close": 0.87409,
          "tick_volume": 92412.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-19T00:00:00Z"
        },
        {
          "time": 1771545600,
          "open": 0.8742,
          "high": 0.87488,
          "low": 0.87252,
          "close": 0.87396,
          "tick_volume": 122848.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-20T00:00:00Z"
        },
        {
          "time": 1771718400,
          "open": 0.87451,
          "high": 0.87506,
          "low": 0.87365,
          "close": 0.87401,
          "tick_volume": 853.0,
          "spread": 28.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-22T00:00:00Z"
        },
        {
          "time": 1771804800,
          "open": 0.87408,
          "high": 0.87496,
          "low": 0.87279,
          "close": 0.87368,
          "tick_volume": 114437.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-23T00:00:00Z"
        },
        {
          "time": 1771891200,
          "open": 0.87375,
          "high": 0.87433,
          "low": 0.87076,
          "close": 0.8726,
          "tick_volume": 86654.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-24T00:00:00Z"
        },
        {
          "time": 1771977600,
          "open": 0.87247,
          "high": 0.87318,
          "low": 0.87078,
          "close": 0.87138,
          "tick_volume": 88733.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-25T00:00:00Z"
        },
        {
          "time": 1772064000,
          "open": 0.87129,
          "high": 0.87583,
          "low": 0.87118,
          "close": 0.87517,
          "tick_volume": 98278.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-26T00:00:00Z"
        },
        {
          "time": 1772150400,
          "open": 0.87511,
          "high": 0.87895,
          "low": 0.87459,
          "close": 0.8764,
          "tick_volume": 98948.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-27T00:00:00Z"
        },
        {
          "time": 1772323200,
          "open": 0.87765,
          "high": 0.87797,
          "low": 0.8766,
          "close": 0.87767,
          "tick_volume": 1511.0,
          "spread": 18.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-01T00:00:00Z"
        },
        {
          "time": 1772409600,
          "open": 0.87724,
          "high": 0.87877,
          "low": 0.87164,
          "close": 0.87196,
          "tick_volume": 162897.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-02T00:00:00Z"
        },
        {
          "time": 1772496000,
          "open": 0.87208,
          "high": 0.87396,
          "low": 0.86914,
          "close": 0.86956,
          "tick_volume": 186174.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-03T00:00:00Z"
        },
        {
          "time": 1772582400,
          "open": 0.86957,
          "high": 0.87128,
          "low": 0.86858,
          "close": 0.87014,
          "tick_volume": 143552.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-04T00:00:00Z"
        },
        {
          "time": 1772668800,
          "open": 0.87014,
          "high": 0.8712,
          "low": 0.86849,
          "close": 0.86956,
          "tick_volume": 155379.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-05T00:00:00Z"
        },
        {
          "time": 1772755200,
          "open": 0.86926,
          "high": 0.8696,
          "low": 0.86564,
          "close": 0.86631,
          "tick_volume": 158084.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-06T00:00:00Z"
        },
        {
          "time": 1772928000,
          "open": 0.86557,
          "high": 0.86634,
          "low": 0.86532,
          "close": 0.86621,
          "tick_volume": 5685.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-08T00:00:00Z"
        },
        {
          "time": 1773014400,
          "open": 0.86621,
          "high": 0.86771,
          "low": 0.86439,
          "close": 0.86578,
          "tick_volume": 193417.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-09T00:00:00Z"
        },
        {
          "time": 1773100800,
          "open": 0.86568,
          "high": 0.8661,
          "low": 0.86422,
          "close": 0.86519,
          "tick_volume": 147340.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-10T00:00:00Z"
        },
        {
          "time": 1773187200,
          "open": 0.86525,
          "high": 0.86575,
          "low": 0.86221,
          "close": 0.86266,
          "tick_volume": 142193.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-11T00:00:00Z"
        },
        {
          "time": 1773273600,
          "open": 0.86263,
          "high": 0.86371,
          "low": 0.86172,
          "close": 0.86286,
          "tick_volume": 130804.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-12T00:00:00Z"
        },
        {
          "time": 1773360000,
          "open": 0.86282,
          "high": 0.86544,
          "low": 0.86201,
          "close": 0.86331,
          "tick_volume": 139374.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-13T00:00:00Z"
        },
        {
          "time": 1773532800,
          "open": 0.86344,
          "high": 0.86364,
          "low": 0.86311,
          "close": 0.86337,
          "tick_volume": 3603.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-15T00:00:00Z"
        },
        {
          "time": 1773619200,
          "open": 0.86336,
          "high": 0.86502,
          "low": 0.86253,
          "close": 0.86374,
          "tick_volume": 114648.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-16T00:00:00Z"
        },
        {
          "time": 1773705600,
          "open": 0.86372,
          "high": 0.86455,
          "low": 0.86324,
          "close": 0.8638,
          "tick_volume": 98917.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-17T00:00:00Z"
        },
        {
          "time": 1773792000,
          "open": 0.86378,
          "high": 0.8651,
          "low": 0.86282,
          "close": 0.86405,
          "tick_volume": 120171.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-18T00:00:00Z"
        },
        {
          "time": 1773878400,
          "open": 0.86411,
          "high": 0.8649,
          "low": 0.86118,
          "close": 0.8624,
          "tick_volume": 160841.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-19T00:00:00Z"
        },
        {
          "time": 1773964800,
          "open": 0.86235,
          "high": 0.86792,
          "low": 0.86148,
          "close": 0.8673,
          "tick_volume": 126341.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-20T00:00:00Z"
        },
        {
          "time": 1774137600,
          "open": 0.86754,
          "high": 0.86799,
          "low": 0.86739,
          "close": 0.86749,
          "tick_volume": 2897.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-22T00:00:00Z"
        },
        {
          "time": 1774224000,
          "open": 0.86751,
          "high": 0.86793,
          "low": 0.8631,
          "close": 0.86466,
          "tick_volume": 250590.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-23T00:00:00Z"
        },
        {
          "time": 1774310400,
          "open": 0.86465,
          "high": 0.866,
          "low": 0.86377,
          "close": 0.86554,
          "tick_volume": 173727.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-24T00:00:00Z"
        },
        {
          "time": 1774396800,
          "open": 0.86553,
          "high": 0.86683,
          "low": 0.86456,
          "close": 0.86514,
          "tick_volume": 127468.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-25T00:00:00Z"
        },
        {
          "time": 1774483200,
          "open": 0.86515,
          "high": 0.86625,
          "low": 0.86368,
          "close": 0.8651,
          "tick_volume": 114338.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-26T00:00:00Z"
        },
        {
          "time": 1774569600,
          "open": 0.86512,
          "high": 0.86804,
          "low": 0.86473,
          "close": 0.86785,
          "tick_volume": 109663.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-27T00:00:00Z"
        },
        {
          "time": 1774742400,
          "open": 0.8674,
          "high": 0.8674,
          "low": 0.86597,
          "close": 0.8667,
          "tick_volume": 426.0,
          "spread": 26.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-29T00:00:00Z"
        },
        {
          "time": 1774828800,
          "open": 0.86747,
          "high": 0.86982,
          "low": 0.86726,
          "close": 0.86941,
          "tick_volume": 135274.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-30T00:00:00Z"
        },
        {
          "time": 1774915200,
          "open": 0.86944,
          "high": 0.87427,
          "low": 0.86762,
          "close": 0.87363,
          "tick_volume": 161433.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-31T00:00:00Z"
        },
        {
          "time": 1775001600,
          "open": 0.87362,
          "high": 0.87424,
          "low": 0.87028,
          "close": 0.87103,
          "tick_volume": 150439.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-04-01T00:00:00Z"
        },
        {
          "time": 1775088000,
          "open": 0.87106,
          "high": 0.87343,
          "low": 0.87087,
          "close": 0.87298,
          "tick_volume": 152498.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-04-02T00:00:00Z"
        },
        {
          "time": 1775174400,
          "open": 0.87249,
          "high": 0.87367,
          "low": 0.87175,
          "close": 0.87217,
          "tick_volume": 51196.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-04-03T00:00:00Z"
        },
        {
          "time": 1775347200,
          "open": 0.87338,
          "high": 0.87357,
          "low": 0.8731,
          "close": 0.87333,
          "tick_volume": 240.0,
          "spread": 14.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-04-05T00:00:00Z"
        },
        {
          "time": 1775433600,
          "open": 0.87322,
          "high": 0.8734,
          "low": 0.87161,
          "close": 0.87201,
          "tick_volume": 56979.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-04-06T00:00:00Z"
        }
      ]
    }
  },
  "planner_contract": {
    "human_sections_required": [
      "screener_read",
      "market_state",
      "key_levels",
      "trade_quality",
      "primary_trade_plan",
      "orderability_decision",
      "backup_plan",
      "risk_sizing",
      "trade_plan_ticket",
      "final_verdict"
    ],
    "json_top_level_required": [
      "screener_read",
      "market_state",
      "key_levels",
      "trade_quality",
      "primary_plan",
      "orderability",
      "backup_plan",
      "risk_sizing",
      "trade_plan_ticket",
      "final_verdict",
      "validator_hints"
    ]
  }
}
```
