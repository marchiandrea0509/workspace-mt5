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
  "generated_at_utc": "2026-04-09T05:07:44.517256Z",
  "report_source": {
    "path": "C:\\Users\\anmar\\.openclaw\\workspace\\tradingview\\reports\\pine_screener\\pine_screener_2026-04-09T05-05-09-493Z.json",
    "generated_at": "2026-04-09T05:06:23.091Z",
    "watchlist": "MT5_FRX",
    "indicator": "OC Hybrid Edge Screener v7",
    "timeframe": "4 hours",
    "row_count": 42,
    "winner_rank": 1
  },
  "market": {
    "symbol": "AUDCAD",
    "description": "AUD/CAD",
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
    "root_symbol": "AUDCAD",
    "analysis_symbol": "AUDCAD.pro",
    "execution_symbol": "AUDCAD.pro",
    "path": "PRO\\FX\\Non-Major\\AUDCAD.pro",
    "trade_mode": "FULL",
    "trade_mode_code": 4,
    "digits": 5,
    "point": 1e-05,
    "volume_min": 0.01,
    "volume_step": 0.01,
    "volume_max": 50.0,
    "contract_size": 100000.0,
    "currency_base": "AUD",
    "currency_profit": "CAD",
    "currency_margin": "AUD",
    "quote_to_usd": 0.7220998664115248,
    "margin_to_usd": 0.70428,
    "units_per_1_lot_estimate": 100000.0,
    "units_note": "For FX this is typically base units per lot. For CFDs/other products, treat lots as executable truth and units as an estimate only."
  },
  "screener_dashboard": {
    "raw_row": {
      "Symbol": "AUDCAD",
      "Description": "AUD/CAD",
      "01 Signal Dir": "0",
      "02 Best Setup Code": "2",
      "03 Best Score": "74.88617627105984",
      "04 Final Long Score": "74.88617627105984",
      "05 Final Short Score": "32.22274342896659",
      "06 Long Continuation": "78.88617627105984",
      "07 Short Continuation": "35.85256863641726",
      "08 Long MeanRev": "59.777256571033405",
      "09 Short MeanRev": "56.22274342896659",
      "10 Conviction State": "3",
      "11 Trend Dir": "1",
      "12 Macro Dir 1D": "1",
      "13 Position State": "0",
      "14 Breakout Dir": "0",
      "15 Retest Dir": "0",
      "16 ADX": "34.516152021629345",
      "17 Rel Volume": "0.04217138521531227",
      "18 Dist Fast EMA ATR": "1.4226905953420208",
      "19 Sweep Dir": "0",
      "20 Displacement Dir": "0",
      "21 PD State": "0",
      "22 FVG State": "2",
      "23 Tactical Trend Score": "88.66039432780971",
      "24 Tactical Breakout Score": "7.689022839214889",
      "25 Tactical MeanRev Score": "-43.361670211461984",
      "26 Fresh Struct Shift": "0",
      "27 Verdict State": "2",
      "28 Momentum State": "0",
      "29 Signed Conviction": "3",
      "30 Break Fresh State": "0",
      "31 Retest Stage": "0",
      "32 Short MR Struct": "50",
      "33 Dist To Resistance %": "",
      "34 Zone Count": "4",
      "35 EMA Trend State": "1",
      "36 VWAP20": "0.9710644195552889",
      "37 Dist To Support %": "0.012766611977030313",
      "38 Lifecycle Long Score": "50",
      "39 R1 Above": "",
      "40 R2 Above": "",
      "41 S1 Below": "0.96275",
      "42 S2 Below": "0.9558766666666667",
      "43 Cnt Res Above": "0",
      "44 Cnt Sup Below": "3",
      "45 Cnt Res All": "1",
      "46 Cnt Sup All": "3",
      "47 Lifecycle Short Score": "50",
      "48 Winner Dir": "1",
      "49 Winner Family Code": "2",
      "50 Winner Margin": "42.66343284209325",
      "51 Winner Base Score": "78.88617627105984",
      "52 Winner Penalty": "4",
      "53 Winner Tactical": "71.37028955913138",
      "54 Winner Macro": "85",
      "55 Winner Structure": "50",
      "56 Winner ADX Fit": "93",
      "57 Winner Lifecycle": "50",
      "58 Winner Context Boost": "4",
      "59 Winner Family Edge": "19.108919700026433"
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
          "time": 1768939200,
          "open": 0.9314,
          "high": 0.93249,
          "low": 0.93102,
          "close": 0.93157,
          "tick_volume": 5685.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-20T20:00:00Z"
        },
        {
          "time": 1768953600,
          "open": 0.93175,
          "high": 0.93236,
          "low": 0.93108,
          "close": 0.93166,
          "tick_volume": 11829.0,
          "spread": 3.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-21T00:00:00Z"
        },
        {
          "time": 1768968000,
          "open": 0.93166,
          "high": 0.93388,
          "low": 0.93106,
          "close": 0.93364,
          "tick_volume": 13739.0,
          "spread": 3.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-21T04:00:00Z"
        },
        {
          "time": 1768982400,
          "open": 0.93366,
          "high": 0.93476,
          "low": 0.93311,
          "close": 0.93344,
          "tick_volume": 9417.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-21T08:00:00Z"
        },
        {
          "time": 1768996800,
          "open": 0.93346,
          "high": 0.93478,
          "low": 0.93306,
          "close": 0.93454,
          "tick_volume": 13833.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-21T12:00:00Z"
        },
        {
          "time": 1769011200,
          "open": 0.93455,
          "high": 0.93527,
          "low": 0.93368,
          "close": 0.93433,
          "tick_volume": 14617.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-21T16:00:00Z"
        },
        {
          "time": 1769025600,
          "open": 0.93433,
          "high": 0.93588,
          "low": 0.9341,
          "close": 0.93482,
          "tick_volume": 9190.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-21T20:00:00Z"
        },
        {
          "time": 1769040000,
          "open": 0.93491,
          "high": 0.93997,
          "low": 0.93465,
          "close": 0.9397,
          "tick_volume": 13565.0,
          "spread": 7.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-22T00:00:00Z"
        },
        {
          "time": 1769054400,
          "open": 0.93972,
          "high": 0.94092,
          "low": 0.93957,
          "close": 0.94064,
          "tick_volume": 16484.0,
          "spread": 6.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-22T04:00:00Z"
        },
        {
          "time": 1769068800,
          "open": 0.94064,
          "high": 0.94117,
          "low": 0.9396,
          "close": 0.94025,
          "tick_volume": 20151.0,
          "spread": 4.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-22T08:00:00Z"
        },
        {
          "time": 1769083200,
          "open": 0.94024,
          "high": 0.94145,
          "low": 0.93988,
          "close": 0.94082,
          "tick_volume": 20962.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-22T12:00:00Z"
        },
        {
          "time": 1769097600,
          "open": 0.94085,
          "high": 0.94346,
          "low": 0.94066,
          "close": 0.94316,
          "tick_volume": 11441.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-22T16:00:00Z"
        },
        {
          "time": 1769112000,
          "open": 0.94317,
          "high": 0.94349,
          "low": 0.94255,
          "close": 0.94305,
          "tick_volume": 5508.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-22T20:00:00Z"
        },
        {
          "time": 1769126400,
          "open": 0.94299,
          "high": 0.94461,
          "low": 0.94248,
          "close": 0.94347,
          "tick_volume": 10844.0,
          "spread": 4.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-23T00:00:00Z"
        },
        {
          "time": 1769140800,
          "open": 0.94347,
          "high": 0.9451,
          "low": 0.94279,
          "close": 0.94465,
          "tick_volume": 12517.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-23T04:00:00Z"
        },
        {
          "time": 1769155200,
          "open": 0.94463,
          "high": 0.94464,
          "low": 0.94262,
          "close": 0.94347,
          "tick_volume": 10913.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-23T08:00:00Z"
        },
        {
          "time": 1769169600,
          "open": 0.94347,
          "high": 0.94521,
          "low": 0.94279,
          "close": 0.94387,
          "tick_volume": 9806.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-23T12:00:00Z"
        },
        {
          "time": 1769184000,
          "open": 0.94383,
          "high": 0.94456,
          "low": 0.9434,
          "close": 0.94366,
          "tick_volume": 14713.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-23T16:00:00Z"
        },
        {
          "time": 1769198400,
          "open": 0.94367,
          "high": 0.9454,
          "low": 0.94354,
          "close": 0.94469,
          "tick_volume": 7285.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-23T20:00:00Z"
        },
        {
          "time": 1769371200,
          "open": 0.94837,
          "high": 0.94989,
          "low": 0.94704,
          "close": 0.94989,
          "tick_volume": 1235.0,
          "spread": 96.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-25T20:00:00Z"
        },
        {
          "time": 1769385600,
          "open": 0.94832,
          "high": 0.94893,
          "low": 0.94637,
          "close": 0.94668,
          "tick_volume": 12573.0,
          "spread": 3.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-26T00:00:00Z"
        },
        {
          "time": 1769400000,
          "open": 0.94668,
          "high": 0.94713,
          "low": 0.94544,
          "close": 0.94583,
          "tick_volume": 10965.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-26T04:00:00Z"
        },
        {
          "time": 1769414400,
          "open": 0.94583,
          "high": 0.94757,
          "low": 0.9455,
          "close": 0.94677,
          "tick_volume": 11000.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-26T08:00:00Z"
        },
        {
          "time": 1769428800,
          "open": 0.94675,
          "high": 0.94995,
          "low": 0.94631,
          "close": 0.94991,
          "tick_volume": 12172.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-26T12:00:00Z"
        },
        {
          "time": 1769443200,
          "open": 0.9499,
          "high": 0.95101,
          "low": 0.94821,
          "close": 0.94984,
          "tick_volume": 12064.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-26T16:00:00Z"
        },
        {
          "time": 1769457600,
          "open": 0.94981,
          "high": 0.94993,
          "low": 0.94737,
          "close": 0.94775,
          "tick_volume": 4816.0,
          "spread": 3.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-26T20:00:00Z"
        },
        {
          "time": 1769472000,
          "open": 0.94747,
          "high": 0.94985,
          "low": 0.9474,
          "close": 0.94944,
          "tick_volume": 11673.0,
          "spread": 4.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-27T00:00:00Z"
        },
        {
          "time": 1769486400,
          "open": 0.94947,
          "high": 0.95031,
          "low": 0.94847,
          "close": 0.95013,
          "tick_volume": 9916.0,
          "spread": 3.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-27T04:00:00Z"
        },
        {
          "time": 1769500800,
          "open": 0.95011,
          "high": 0.95035,
          "low": 0.94804,
          "close": 0.94958,
          "tick_volume": 9860.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-27T08:00:00Z"
        },
        {
          "time": 1769515200,
          "open": 0.94958,
          "high": 0.951,
          "low": 0.94871,
          "close": 0.94932,
          "tick_volume": 12895.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-27T12:00:00Z"
        },
        {
          "time": 1769529600,
          "open": 0.94931,
          "high": 0.9497,
          "low": 0.9477,
          "close": 0.94952,
          "tick_volume": 13054.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-27T16:00:00Z"
        },
        {
          "time": 1769544000,
          "open": 0.9495,
          "high": 0.95248,
          "low": 0.94949,
          "close": 0.95123,
          "tick_volume": 11960.0,
          "spread": 3.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-27T20:00:00Z"
        },
        {
          "time": 1769558400,
          "open": 0.95147,
          "high": 0.95465,
          "low": 0.95028,
          "close": 0.9515,
          "tick_volume": 15859.0,
          "spread": 3.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-28T00:00:00Z"
        },
        {
          "time": 1769572800,
          "open": 0.95152,
          "high": 0.95207,
          "low": 0.94998,
          "close": 0.95094,
          "tick_volume": 13223.0,
          "spread": 4.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-28T04:00:00Z"
        },
        {
          "time": 1769587200,
          "open": 0.95092,
          "high": 0.95258,
          "low": 0.94847,
          "close": 0.95029,
          "tick_volume": 12571.0,
          "spread": 3.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-28T08:00:00Z"
        },
        {
          "time": 1769601600,
          "open": 0.95027,
          "high": 0.9509,
          "low": 0.94783,
          "close": 0.94866,
          "tick_volume": 12283.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-28T12:00:00Z"
        },
        {
          "time": 1769616000,
          "open": 0.94866,
          "high": 0.9512,
          "low": 0.94658,
          "close": 0.95011,
          "tick_volume": 18813.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-28T16:00:00Z"
        },
        {
          "time": 1769630400,
          "open": 0.95014,
          "high": 0.95499,
          "low": 0.94943,
          "close": 0.95435,
          "tick_volume": 12724.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-28T20:00:00Z"
        },
        {
          "time": 1769644800,
          "open": 0.95444,
          "high": 0.95463,
          "low": 0.95117,
          "close": 0.95404,
          "tick_volume": 16083.0,
          "spread": 5.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-29T00:00:00Z"
        },
        {
          "time": 1769659200,
          "open": 0.95403,
          "high": 0.95908,
          "low": 0.95395,
          "close": 0.95733,
          "tick_volume": 18667.0,
          "spread": 6.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-29T04:00:00Z"
        },
        {
          "time": 1769673600,
          "open": 0.95731,
          "high": 0.95745,
          "low": 0.95342,
          "close": 0.95349,
          "tick_volume": 12107.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-29T08:00:00Z"
        },
        {
          "time": 1769688000,
          "open": 0.95351,
          "high": 0.95611,
          "low": 0.95271,
          "close": 0.95331,
          "tick_volume": 13669.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-29T12:00:00Z"
        },
        {
          "time": 1769702400,
          "open": 0.95333,
          "high": 0.95347,
          "low": 0.94531,
          "close": 0.94919,
          "tick_volume": 35924.0,
          "spread": 4.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-29T16:00:00Z"
        },
        {
          "time": 1769716800,
          "open": 0.94919,
          "high": 0.95197,
          "low": 0.94829,
          "close": 0.95082,
          "tick_volume": 7642.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-29T20:00:00Z"
        },
        {
          "time": 1769731200,
          "open": 0.95079,
          "high": 0.95145,
          "low": 0.94453,
          "close": 0.94714,
          "tick_volume": 16218.0,
          "spread": 3.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-30T00:00:00Z"
        },
        {
          "time": 1769745600,
          "open": 0.94714,
          "high": 0.94729,
          "low": 0.94462,
          "close": 0.94469,
          "tick_volume": 14301.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-30T04:00:00Z"
        },
        {
          "time": 1769760000,
          "open": 0.94469,
          "high": 0.94774,
          "low": 0.94436,
          "close": 0.94705,
          "tick_volume": 13923.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-30T08:00:00Z"
        },
        {
          "time": 1769774400,
          "open": 0.94705,
          "high": 0.9495,
          "low": 0.94677,
          "close": 0.94843,
          "tick_volume": 17494.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-30T12:00:00Z"
        },
        {
          "time": 1769788800,
          "open": 0.94843,
          "high": 0.95,
          "low": 0.94462,
          "close": 0.94757,
          "tick_volume": 24176.0,
          "spread": 3.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-30T16:00:00Z"
        },
        {
          "time": 1769803200,
          "open": 0.94757,
          "high": 0.94899,
          "low": 0.94703,
          "close": 0.94833,
          "tick_volume": 9998.0,
          "spread": 4.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-30T20:00:00Z"
        },
        {
          "time": 1769976000,
          "open": 0.94656,
          "high": 0.94701,
          "low": 0.94463,
          "close": 0.94491,
          "tick_volume": 1495.0,
          "spread": 87.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-01T20:00:00Z"
        },
        {
          "time": 1769990400,
          "open": 0.94523,
          "high": 0.9493,
          "low": 0.94468,
          "close": 0.94753,
          "tick_volume": 23002.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-02T00:00:00Z"
        },
        {
          "time": 1770004800,
          "open": 0.94753,
          "high": 0.94841,
          "low": 0.94461,
          "close": 0.94569,
          "tick_volume": 15857.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-02T04:00:00Z"
        },
        {
          "time": 1770019200,
          "open": 0.94569,
          "high": 0.94979,
          "low": 0.94563,
          "close": 0.94842,
          "tick_volume": 14730.0,
          "spread": 3.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-02T08:00:00Z"
        },
        {
          "time": 1770033600,
          "open": 0.94842,
          "high": 0.95093,
          "low": 0.94744,
          "close": 0.95046,
          "tick_volume": 15827.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-02T12:00:00Z"
        },
        {
          "time": 1770048000,
          "open": 0.95032,
          "high": 0.95247,
          "low": 0.94958,
          "close": 0.95028,
          "tick_volume": 17343.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-02T16:00:00Z"
        },
        {
          "time": 1770062400,
          "open": 0.95028,
          "high": 0.95146,
          "low": 0.94956,
          "close": 0.95078,
          "tick_volume": 5539.0,
          "spread": 3.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-02T20:00:00Z"
        },
        {
          "time": 1770076800,
          "open": 0.95082,
          "high": 0.95335,
          "low": 0.9505,
          "close": 0.95211,
          "tick_volume": 10880.0,
          "spread": 3.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-03T00:00:00Z"
        },
        {
          "time": 1770091200,
          "open": 0.95211,
          "high": 0.96046,
          "low": 0.95202,
          "close": 0.9588,
          "tick_volume": 15486.0,
          "spread": 6.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-03T04:00:00Z"
        },
        {
          "time": 1770105600,
          "open": 0.9588,
          "high": 0.96254,
          "low": 0.95795,
          "close": 0.95798,
          "tick_volume": 14042.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-03T08:00:00Z"
        },
        {
          "time": 1770120000,
          "open": 0.95796,
          "high": 0.95862,
          "low": 0.95556,
          "close": 0.95568,
          "tick_volume": 13235.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-03T12:00:00Z"
        },
        {
          "time": 1770134400,
          "open": 0.95567,
          "high": 0.95824,
          "low": 0.95478,
          "close": 0.95564,
          "tick_volume": 18329.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-03T16:00:00Z"
        },
        {
          "time": 1770148800,
          "open": 0.95561,
          "high": 0.95826,
          "low": 0.95502,
          "close": 0.95707,
          "tick_volume": 8445.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-03T20:00:00Z"
        },
        {
          "time": 1770163200,
          "open": 0.95718,
          "high": 0.95935,
          "low": 0.95689,
          "close": 0.95767,
          "tick_volume": 7849.0,
          "spread": 4.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-04T00:00:00Z"
        },
        {
          "time": 1770177600,
          "open": 0.95767,
          "high": 0.95903,
          "low": 0.95747,
          "close": 0.95898,
          "tick_volume": 8427.0,
          "spread": 4.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-04T04:00:00Z"
        },
        {
          "time": 1770192000,
          "open": 0.95896,
          "high": 0.95995,
          "low": 0.95736,
          "close": 0.95898,
          "tick_volume": 10047.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-04T08:00:00Z"
        },
        {
          "time": 1770206400,
          "open": 0.95898,
          "high": 0.96015,
          "low": 0.95807,
          "close": 0.9584,
          "tick_volume": 13811.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-04T12:00:00Z"
        },
        {
          "time": 1770220800,
          "open": 0.95838,
          "high": 0.95883,
          "low": 0.95341,
          "close": 0.9546,
          "tick_volume": 21113.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-04T16:00:00Z"
        },
        {
          "time": 1770235200,
          "open": 0.95461,
          "high": 0.95676,
          "low": 0.95409,
          "close": 0.95623,
          "tick_volume": 6859.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-04T20:00:00Z"
        },
        {
          "time": 1770249600,
          "open": 0.95613,
          "high": 0.95724,
          "low": 0.95207,
          "close": 0.95294,
          "tick_volume": 13000.0,
          "spread": 5.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-05T00:00:00Z"
        },
        {
          "time": 1770264000,
          "open": 0.95294,
          "high": 0.95479,
          "low": 0.95251,
          "close": 0.95478,
          "tick_volume": 16945.0,
          "spread": 5.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-05T04:00:00Z"
        },
        {
          "time": 1770278400,
          "open": 0.95476,
          "high": 0.95619,
          "low": 0.95369,
          "close": 0.95496,
          "tick_volume": 10920.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-05T08:00:00Z"
        },
        {
          "time": 1770292800,
          "open": 0.95494,
          "high": 0.95572,
          "low": 0.95133,
          "close": 0.95185,
          "tick_volume": 18997.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-05T12:00:00Z"
        },
        {
          "time": 1770307200,
          "open": 0.95189,
          "high": 0.95382,
          "low": 0.94926,
          "close": 0.95198,
          "tick_volume": 21483.0,
          "spread": 3.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-05T16:00:00Z"
        },
        {
          "time": 1770321600,
          "open": 0.95196,
          "high": 0.95321,
          "low": 0.94926,
          "close": 0.94985,
          "tick_volume": 7308.0,
          "spread": 3.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-05T20:00:00Z"
        },
        {
          "time": 1770336000,
          "open": 0.94957,
          "high": 0.95128,
          "low": 0.94654,
          "close": 0.9505,
          "tick_volume": 12531.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-06T00:00:00Z"
        },
        {
          "time": 1770350400,
          "open": 0.9505,
          "high": 0.95303,
          "low": 0.95018,
          "close": 0.95253,
          "tick_volume": 11904.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-06T04:00:00Z"
        },
        {
          "time": 1770364800,
          "open": 0.9525,
          "high": 0.95483,
          "low": 0.95191,
          "close": 0.95453,
          "tick_volume": 11317.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-06T08:00:00Z"
        },
        {
          "time": 1770379200,
          "open": 0.9545,
          "high": 0.95574,
          "low": 0.95396,
          "close": 0.95531,
          "tick_volume": 13386.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-06T12:00:00Z"
        },
        {
          "time": 1770393600,
          "open": 0.95532,
          "high": 0.95821,
          "low": 0.95455,
          "close": 0.95796,
          "tick_volume": 12393.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-06T16:00:00Z"
        },
        {
          "time": 1770408000,
          "open": 0.95797,
          "high": 0.95951,
          "low": 0.95786,
          "close": 0.95902,
          "tick_volume": 4282.0,
          "spread": 3.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-06T20:00:00Z"
        },
        {
          "time": 1770580800,
          "open": 0.95949,
          "high": 0.95959,
          "low": 0.95833,
          "close": 0.95887,
          "tick_volume": 581.0,
          "spread": 93.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-08T20:00:00Z"
        },
        {
          "time": 1770595200,
          "open": 0.95932,
          "high": 0.96112,
          "low": 0.95831,
          "close": 0.95993,
          "tick_volume": 7985.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-09T00:00:00Z"
        },
        {
          "time": 1770609600,
          "open": 0.95993,
          "high": 0.96044,
          "low": 0.95901,
          "close": 0.96035,
          "tick_volume": 6759.0,
          "spread": 4.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-09T04:00:00Z"
        },
        {
          "time": 1770624000,
          "open": 0.96033,
          "high": 0.96064,
          "low": 0.95764,
          "close": 0.95817,
          "tick_volume": 9494.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-09T08:00:00Z"
        },
        {
          "time": 1770638400,
          "open": 0.95813,
          "high": 0.96164,
          "low": 0.95796,
          "close": 0.96158,
          "tick_volume": 12533.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-09T12:00:00Z"
        },
        {
          "time": 1770652800,
          "open": 0.96156,
          "high": 0.96277,
          "low": 0.96132,
          "close": 0.96216,
          "tick_volume": 9605.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-09T16:00:00Z"
        },
        {
          "time": 1770667200,
          "open": 0.96216,
          "high": 0.96239,
          "low": 0.96097,
          "close": 0.96152,
          "tick_volume": 4301.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-09T20:00:00Z"
        },
        {
          "time": 1770681600,
          "open": 0.96149,
          "high": 0.96173,
          "low": 0.95984,
          "close": 0.96016,
          "tick_volume": 8242.0,
          "spread": 4.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-10T00:00:00Z"
        },
        {
          "time": 1770696000,
          "open": 0.96016,
          "high": 0.96024,
          "low": 0.95795,
          "close": 0.95831,
          "tick_volume": 7295.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-10T04:00:00Z"
        },
        {
          "time": 1770710400,
          "open": 0.95831,
          "high": 0.96004,
          "low": 0.95822,
          "close": 0.95925,
          "tick_volume": 7906.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-10T08:00:00Z"
        },
        {
          "time": 1770724800,
          "open": 0.95926,
          "high": 0.96006,
          "low": 0.95735,
          "close": 0.95855,
          "tick_volume": 12716.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-10T12:00:00Z"
        },
        {
          "time": 1770739200,
          "open": 0.9585,
          "high": 0.95889,
          "low": 0.95671,
          "close": 0.95823,
          "tick_volume": 12461.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-10T16:00:00Z"
        },
        {
          "time": 1770753600,
          "open": 0.95823,
          "high": 0.95906,
          "low": 0.95734,
          "close": 0.95786,
          "tick_volume": 4461.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-10T20:00:00Z"
        },
        {
          "time": 1770768000,
          "open": 0.95811,
          "high": 0.96384,
          "low": 0.95811,
          "close": 0.96282,
          "tick_volume": 9619.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-11T00:00:00Z"
        },
        {
          "time": 1770782400,
          "open": 0.96282,
          "high": 0.96362,
          "low": 0.96063,
          "close": 0.96119,
          "tick_volume": 8133.0,
          "spread": 4.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-11T04:00:00Z"
        },
        {
          "time": 1770796800,
          "open": 0.96117,
          "high": 0.96209,
          "low": 0.95999,
          "close": 0.96179,
          "tick_volume": 9090.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-11T08:00:00Z"
        },
        {
          "time": 1770811200,
          "open": 0.96179,
          "high": 0.96822,
          "low": 0.96163,
          "close": 0.96784,
          "tick_volume": 22215.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-11T12:00:00Z"
        },
        {
          "time": 1770825600,
          "open": 0.96788,
          "high": 0.96827,
          "low": 0.96566,
          "close": 0.96703,
          "tick_volume": 19040.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-11T16:00:00Z"
        },
        {
          "time": 1770840000,
          "open": 0.96702,
          "high": 0.96804,
          "low": 0.96644,
          "close": 0.96729,
          "tick_volume": 4765.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-11T20:00:00Z"
        },
        {
          "time": 1770854400,
          "open": 0.96756,
          "high": 0.96965,
          "low": 0.9667,
          "close": 0.96826,
          "tick_volume": 9623.0,
          "spread": 6.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-12T00:00:00Z"
        },
        {
          "time": 1770868800,
          "open": 0.96825,
          "high": 0.9685,
          "low": 0.96586,
          "close": 0.96626,
          "tick_volume": 13564.0,
          "spread": 4.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-12T04:00:00Z"
        },
        {
          "time": 1770883200,
          "open": 0.96629,
          "high": 0.96704,
          "low": 0.9652,
          "close": 0.96622,
          "tick_volume": 9417.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-12T08:00:00Z"
        },
        {
          "time": 1770897600,
          "open": 0.9662,
          "high": 0.96896,
          "low": 0.96592,
          "close": 0.96742,
          "tick_volume": 12362.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-12T12:00:00Z"
        },
        {
          "time": 1770912000,
          "open": 0.96743,
          "high": 0.96987,
          "low": 0.96451,
          "close": 0.96564,
          "tick_volume": 22184.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-12T16:00:00Z"
        },
        {
          "time": 1770926400,
          "open": 0.96564,
          "high": 0.96603,
          "low": 0.96438,
          "close": 0.96452,
          "tick_volume": 7058.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-12T20:00:00Z"
        },
        {
          "time": 1770940800,
          "open": 0.96463,
          "high": 0.96613,
          "low": 0.96398,
          "close": 0.96515,
          "tick_volume": 6066.0,
          "spread": 4.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-13T00:00:00Z"
        },
        {
          "time": 1770955200,
          "open": 0.96515,
          "high": 0.96543,
          "low": 0.96115,
          "close": 0.96189,
          "tick_volume": 8464.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-13T04:00:00Z"
        },
        {
          "time": 1770969600,
          "open": 0.96189,
          "high": 0.96276,
          "low": 0.96058,
          "close": 0.96171,
          "tick_volume": 8231.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-13T08:00:00Z"
        },
        {
          "time": 1770984000,
          "open": 0.96171,
          "high": 0.96358,
          "low": 0.9599,
          "close": 0.9605,
          "tick_volume": 20084.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-13T12:00:00Z"
        },
        {
          "time": 1770998400,
          "open": 0.9605,
          "high": 0.96379,
          "low": 0.96045,
          "close": 0.96327,
          "tick_volume": 16803.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-13T16:00:00Z"
        },
        {
          "time": 1771012800,
          "open": 0.96327,
          "high": 0.96399,
          "low": 0.96264,
          "close": 0.9633,
          "tick_volume": 4649.0,
          "spread": 3.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-13T20:00:00Z"
        },
        {
          "time": 1771185600,
          "open": 0.96161,
          "high": 0.96235,
          "low": 0.96112,
          "close": 0.96213,
          "tick_volume": 1151.0,
          "spread": 149.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-15T20:00:00Z"
        },
        {
          "time": 1771200000,
          "open": 0.96254,
          "high": 0.96471,
          "low": 0.96226,
          "close": 0.96422,
          "tick_volume": 5713.0,
          "spread": 4.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-16T00:00:00Z"
        },
        {
          "time": 1771214400,
          "open": 0.96422,
          "high": 0.96544,
          "low": 0.96381,
          "close": 0.96476,
          "tick_volume": 4756.0,
          "spread": 6.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-16T04:00:00Z"
        },
        {
          "time": 1771228800,
          "open": 0.96476,
          "high": 0.96558,
          "low": 0.96428,
          "close": 0.96483,
          "tick_volume": 6442.0,
          "spread": 3.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-16T08:00:00Z"
        },
        {
          "time": 1771243200,
          "open": 0.96483,
          "high": 0.96576,
          "low": 0.96375,
          "close": 0.96464,
          "tick_volume": 4458.0,
          "spread": 3.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-16T12:00:00Z"
        },
        {
          "time": 1771257600,
          "open": 0.96466,
          "high": 0.96489,
          "low": 0.96326,
          "close": 0.96447,
          "tick_volume": 3286.0,
          "spread": 4.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-16T16:00:00Z"
        },
        {
          "time": 1771272000,
          "open": 0.96449,
          "high": 0.96484,
          "low": 0.96393,
          "close": 0.96427,
          "tick_volume": 913.0,
          "spread": 6.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-16T20:00:00Z"
        },
        {
          "time": 1771286400,
          "open": 0.96429,
          "high": 0.9648,
          "low": 0.96218,
          "close": 0.96292,
          "tick_volume": 5936.0,
          "spread": 4.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-17T00:00:00Z"
        },
        {
          "time": 1771300800,
          "open": 0.96292,
          "high": 0.96411,
          "low": 0.96157,
          "close": 0.9639,
          "tick_volume": 6414.0,
          "spread": 5.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-17T04:00:00Z"
        },
        {
          "time": 1771315200,
          "open": 0.96391,
          "high": 0.9652,
          "low": 0.96311,
          "close": 0.96384,
          "tick_volume": 7520.0,
          "spread": 3.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-17T08:00:00Z"
        },
        {
          "time": 1771329600,
          "open": 0.96385,
          "high": 0.96496,
          "low": 0.96194,
          "close": 0.96264,
          "tick_volume": 15303.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-17T12:00:00Z"
        },
        {
          "time": 1771344000,
          "open": 0.96264,
          "high": 0.96677,
          "low": 0.9619,
          "close": 0.96662,
          "tick_volume": 16995.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-17T16:00:00Z"
        },
        {
          "time": 1771358400,
          "open": 0.96662,
          "high": 0.96686,
          "low": 0.96565,
          "close": 0.96623,
          "tick_volume": 5500.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-17T20:00:00Z"
        },
        {
          "time": 1771372800,
          "open": 0.9662,
          "high": 0.96634,
          "low": 0.9645,
          "close": 0.9645,
          "tick_volume": 4757.0,
          "spread": 4.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-18T00:00:00Z"
        },
        {
          "time": 1771387200,
          "open": 0.96452,
          "high": 0.96546,
          "low": 0.96432,
          "close": 0.96523,
          "tick_volume": 3453.0,
          "spread": 7.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-18T04:00:00Z"
        },
        {
          "time": 1771401600,
          "open": 0.96521,
          "high": 0.96706,
          "low": 0.96495,
          "close": 0.96589,
          "tick_volume": 5759.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-18T08:00:00Z"
        },
        {
          "time": 1771416000,
          "open": 0.96589,
          "high": 0.96591,
          "low": 0.96408,
          "close": 0.96518,
          "tick_volume": 9589.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-18T12:00:00Z"
        },
        {
          "time": 1771430400,
          "open": 0.96517,
          "high": 0.96679,
          "low": 0.96515,
          "close": 0.96525,
          "tick_volume": 9273.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-18T16:00:00Z"
        },
        {
          "time": 1771444800,
          "open": 0.96511,
          "high": 0.96543,
          "low": 0.9636,
          "close": 0.96471,
          "tick_volume": 5551.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-18T20:00:00Z"
        },
        {
          "time": 1771459200,
          "open": 0.96468,
          "high": 0.96766,
          "low": 0.9641,
          "close": 0.96758,
          "tick_volume": 5628.0,
          "spread": 6.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-19T00:00:00Z"
        },
        {
          "time": 1771473600,
          "open": 0.96761,
          "high": 0.96787,
          "low": 0.9654,
          "close": 0.96721,
          "tick_volume": 5472.0,
          "spread": 7.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-19T04:00:00Z"
        },
        {
          "time": 1771488000,
          "open": 0.96721,
          "high": 0.96845,
          "low": 0.96468,
          "close": 0.96493,
          "tick_volume": 8071.0,
          "spread": 3.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-19T08:00:00Z"
        },
        {
          "time": 1771502400,
          "open": 0.96493,
          "high": 0.96581,
          "low": 0.96324,
          "close": 0.96419,
          "tick_volume": 10413.0,
          "spread": 3.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-19T12:00:00Z"
        },
        {
          "time": 1771516800,
          "open": 0.96417,
          "high": 0.96649,
          "low": 0.96392,
          "close": 0.96596,
          "tick_volume": 13675.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-19T16:00:00Z"
        },
        {
          "time": 1771531200,
          "open": 0.96598,
          "high": 0.96646,
          "low": 0.9651,
          "close": 0.96572,
          "tick_volume": 5096.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-19T20:00:00Z"
        },
        {
          "time": 1771545600,
          "open": 0.96559,
          "high": 0.96617,
          "low": 0.96124,
          "close": 0.96192,
          "tick_volume": 8301.0,
          "spread": 4.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-20T00:00:00Z"
        },
        {
          "time": 1771560000,
          "open": 0.96192,
          "high": 0.96443,
          "low": 0.96189,
          "close": 0.96437,
          "tick_volume": 8475.0,
          "spread": 4.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-20T04:00:00Z"
        },
        {
          "time": 1771574400,
          "open": 0.96439,
          "high": 0.96693,
          "low": 0.96426,
          "close": 0.96562,
          "tick_volume": 7738.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-20T08:00:00Z"
        },
        {
          "time": 1771588800,
          "open": 0.96562,
          "high": 0.96727,
          "low": 0.9641,
          "close": 0.96722,
          "tick_volume": 12145.0,
          "spread": 3.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-20T12:00:00Z"
        },
        {
          "time": 1771603200,
          "open": 0.96721,
          "high": 0.96988,
          "low": 0.96585,
          "close": 0.9694,
          "tick_volume": 37845.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-20T16:00:00Z"
        },
        {
          "time": 1771617600,
          "open": 0.96943,
          "high": 0.9695,
          "low": 0.96856,
          "close": 0.96901,
          "tick_volume": 6488.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-20T20:00:00Z"
        },
        {
          "time": 1771790400,
          "open": 0.96811,
          "high": 0.96931,
          "low": 0.96787,
          "close": 0.96859,
          "tick_volume": 509.0,
          "spread": 36.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-22T20:00:00Z"
        },
        {
          "time": 1771804800,
          "open": 0.96883,
          "high": 0.97073,
          "low": 0.9662,
          "close": 0.96658,
          "tick_volume": 11382.0,
          "spread": 3.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-23T00:00:00Z"
        },
        {
          "time": 1771819200,
          "open": 0.96658,
          "high": 0.9678,
          "low": 0.96615,
          "close": 0.96764,
          "tick_volume": 6776.0,
          "spread": 4.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-23T04:00:00Z"
        },
        {
          "time": 1771833600,
          "open": 0.96763,
          "high": 0.96875,
          "low": 0.9671,
          "close": 0.96779,
          "tick_volume": 8263.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-23T08:00:00Z"
        },
        {
          "time": 1771848000,
          "open": 0.96779,
          "high": 0.96832,
          "low": 0.96656,
          "close": 0.96785,
          "tick_volume": 9939.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-23T12:00:00Z"
        },
        {
          "time": 1771862400,
          "open": 0.96787,
          "high": 0.96821,
          "low": 0.96531,
          "close": 0.96659,
          "tick_volume": 12048.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-23T16:00:00Z"
        },
        {
          "time": 1771876800,
          "open": 0.96661,
          "high": 0.96725,
          "low": 0.96583,
          "close": 0.96618,
          "tick_volume": 3593.0,
          "spread": 3.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-23T20:00:00Z"
        },
        {
          "time": 1771891200,
          "open": 0.96632,
          "high": 0.9687,
          "low": 0.96621,
          "close": 0.96861,
          "tick_volume": 8843.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-24T00:00:00Z"
        },
        {
          "time": 1771905600,
          "open": 0.96861,
          "high": 0.96877,
          "low": 0.96726,
          "close": 0.9678,
          "tick_volume": 8509.0,
          "spread": 3.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-24T04:00:00Z"
        },
        {
          "time": 1771920000,
          "open": 0.96781,
          "high": 0.96907,
          "low": 0.96661,
          "close": 0.96673,
          "tick_volume": 8214.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-24T08:00:00Z"
        },
        {
          "time": 1771934400,
          "open": 0.96673,
          "high": 0.96685,
          "low": 0.96426,
          "close": 0.96537,
          "tick_volume": 10366.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-24T12:00:00Z"
        },
        {
          "time": 1771948800,
          "open": 0.96537,
          "high": 0.96871,
          "low": 0.96521,
          "close": 0.96765,
          "tick_volume": 10833.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-24T16:00:00Z"
        },
        {
          "time": 1771963200,
          "open": 0.96765,
          "high": 0.96782,
          "low": 0.96674,
          "close": 0.96732,
          "tick_volume": 4007.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-24T20:00:00Z"
        },
        {
          "time": 1771977600,
          "open": 0.96721,
          "high": 0.97092,
          "low": 0.96701,
          "close": 0.97084,
          "tick_volume": 11985.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-25T00:00:00Z"
        },
        {
          "time": 1771992000,
          "open": 0.97085,
          "high": 0.97317,
          "low": 0.97033,
          "close": 0.97276,
          "tick_volume": 10016.0,
          "spread": 4.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-25T04:00:00Z"
        },
        {
          "time": 1772006400,
          "open": 0.97276,
          "high": 0.97321,
          "low": 0.96992,
          "close": 0.97009,
          "tick_volume": 10014.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-25T08:00:00Z"
        },
        {
          "time": 1772020800,
          "open": 0.97009,
          "high": 0.9722,
          "low": 0.96938,
          "close": 0.97158,
          "tick_volume": 9067.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-25T12:00:00Z"
        },
        {
          "time": 1772035200,
          "open": 0.97161,
          "high": 0.97454,
          "low": 0.9709,
          "close": 0.97396,
          "tick_volume": 8820.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-25T16:00:00Z"
        },
        {
          "time": 1772049600,
          "open": 0.97396,
          "high": 0.97472,
          "low": 0.97351,
          "close": 0.97387,
          "tick_volume": 3263.0,
          "spread": 4.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-25T20:00:00Z"
        },
        {
          "time": 1772064000,
          "open": 0.97384,
          "high": 0.97507,
          "low": 0.97253,
          "close": 0.97361,
          "tick_volume": 9680.0,
          "spread": 6.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-26T00:00:00Z"
        },
        {
          "time": 1772078400,
          "open": 0.97361,
          "high": 0.97495,
          "low": 0.97328,
          "close": 0.97401,
          "tick_volume": 8825.0,
          "spread": 7.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-26T04:00:00Z"
        },
        {
          "time": 1772092800,
          "open": 0.97403,
          "high": 0.97423,
          "low": 0.9724,
          "close": 0.97312,
          "tick_volume": 11269.0,
          "spread": 4.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-26T08:00:00Z"
        },
        {
          "time": 1772107200,
          "open": 0.97312,
          "high": 0.9743,
          "low": 0.97226,
          "close": 0.97235,
          "tick_volume": 10008.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-26T12:00:00Z"
        },
        {
          "time": 1772121600,
          "open": 0.97233,
          "high": 0.97254,
          "low": 0.96892,
          "close": 0.97138,
          "tick_volume": 18352.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-26T16:00:00Z"
        },
        {
          "time": 1772136000,
          "open": 0.97141,
          "high": 0.97289,
          "low": 0.97119,
          "close": 0.97142,
          "tick_volume": 4609.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-26T20:00:00Z"
        },
        {
          "time": 1772150400,
          "open": 0.97141,
          "high": 0.97323,
          "low": 0.97078,
          "close": 0.97319,
          "tick_volume": 7804.0,
          "spread": 3.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-27T00:00:00Z"
        },
        {
          "time": 1772164800,
          "open": 0.97319,
          "high": 0.9745,
          "low": 0.97288,
          "close": 0.97391,
          "tick_volume": 8077.0,
          "spread": 4.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-27T04:00:00Z"
        },
        {
          "time": 1772179200,
          "open": 0.97391,
          "high": 0.97425,
          "low": 0.97135,
          "close": 0.97211,
          "tick_volume": 8996.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-27T08:00:00Z"
        },
        {
          "time": 1772193600,
          "open": 0.97211,
          "high": 0.97222,
          "low": 0.96967,
          "close": 0.97072,
          "tick_volume": 13744.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-27T12:00:00Z"
        },
        {
          "time": 1772208000,
          "open": 0.97071,
          "high": 0.97238,
          "low": 0.96943,
          "close": 0.97007,
          "tick_volume": 15937.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-27T16:00:00Z"
        },
        {
          "time": 1772222400,
          "open": 0.97007,
          "high": 0.97128,
          "low": 0.96938,
          "close": 0.97079,
          "tick_volume": 5826.0,
          "spread": 3.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-27T20:00:00Z"
        },
        {
          "time": 1772395200,
          "open": 0.96052,
          "high": 0.96425,
          "low": 0.96052,
          "close": 0.96233,
          "tick_volume": 1196.0,
          "spread": 114.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-01T20:00:00Z"
        },
        {
          "time": 1772409600,
          "open": 0.96395,
          "high": 0.97016,
          "low": 0.96338,
          "close": 0.96985,
          "tick_volume": 19415.0,
          "spread": 6.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-02T00:00:00Z"
        },
        {
          "time": 1772424000,
          "open": 0.96985,
          "high": 0.97087,
          "low": 0.9649,
          "close": 0.96532,
          "tick_volume": 13617.0,
          "spread": 4.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-02T04:00:00Z"
        },
        {
          "time": 1772438400,
          "open": 0.96532,
          "high": 0.96826,
          "low": 0.96322,
          "close": 0.96768,
          "tick_volume": 17820.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-02T08:00:00Z"
        },
        {
          "time": 1772452800,
          "open": 0.96771,
          "high": 0.96821,
          "low": 0.96433,
          "close": 0.96777,
          "tick_volume": 16319.0,
          "spread": 3.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-02T12:00:00Z"
        },
        {
          "time": 1772467200,
          "open": 0.96782,
          "high": 0.97062,
          "low": 0.96677,
          "close": 0.97001,
          "tick_volume": 17335.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-02T16:00:00Z"
        },
        {
          "time": 1772481600,
          "open": 0.96999,
          "high": 0.97248,
          "low": 0.96805,
          "close": 0.97111,
          "tick_volume": 10480.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-02T20:00:00Z"
        },
        {
          "time": 1772496000,
          "open": 0.97113,
          "high": 0.97308,
          "low": 0.96903,
          "close": 0.97072,
          "tick_volume": 12543.0,
          "spread": 5.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-03T00:00:00Z"
        },
        {
          "time": 1772510400,
          "open": 0.97074,
          "high": 0.97211,
          "low": 0.96842,
          "close": 0.96952,
          "tick_volume": 14933.0,
          "spread": 3.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-03T04:00:00Z"
        },
        {
          "time": 1772524800,
          "open": 0.96952,
          "high": 0.97046,
          "low": 0.96169,
          "close": 0.963,
          "tick_volume": 20081.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-03T08:00:00Z"
        },
        {
          "time": 1772539200,
          "open": 0.96297,
          "high": 0.96412,
          "low": 0.95766,
          "close": 0.95793,
          "tick_volume": 26726.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-03T12:00:00Z"
        },
        {
          "time": 1772553600,
          "open": 0.95789,
          "high": 0.96321,
          "low": 0.95455,
          "close": 0.96275,
          "tick_volume": 35211.0,
          "spread": 3.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-03T16:00:00Z"
        },
        {
          "time": 1772568000,
          "open": 0.96278,
          "high": 0.96415,
          "low": 0.96098,
          "close": 0.96252,
          "tick_volume": 12606.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-03T20:00:00Z"
        },
        {
          "time": 1772582400,
          "open": 0.96292,
          "high": 0.96332,
          "low": 0.95704,
          "close": 0.95945,
          "tick_volume": 19021.0,
          "spread": 4.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-04T00:00:00Z"
        },
        {
          "time": 1772596800,
          "open": 0.95945,
          "high": 0.96055,
          "low": 0.95647,
          "close": 0.95997,
          "tick_volume": 17099.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-04T04:00:00Z"
        },
        {
          "time": 1772611200,
          "open": 0.95996,
          "high": 0.96562,
          "low": 0.95928,
          "close": 0.96319,
          "tick_volume": 22837.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-04T08:00:00Z"
        },
        {
          "time": 1772625600,
          "open": 0.96318,
          "high": 0.96533,
          "low": 0.96157,
          "close": 0.96408,
          "tick_volume": 22672.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-04T12:00:00Z"
        },
        {
          "time": 1772640000,
          "open": 0.96403,
          "high": 0.96678,
          "low": 0.96333,
          "close": 0.96636,
          "tick_volume": 20689.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-04T16:00:00Z"
        },
        {
          "time": 1772654400,
          "open": 0.96636,
          "high": 0.96691,
          "low": 0.96473,
          "close": 0.96533,
          "tick_volume": 5911.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-04T20:00:00Z"
        },
        {
          "time": 1772668800,
          "open": 0.96523,
          "high": 0.96624,
          "low": 0.96338,
          "close": 0.96462,
          "tick_volume": 19842.0,
          "spread": 9.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-05T00:00:00Z"
        },
        {
          "time": 1772683200,
          "open": 0.96462,
          "high": 0.96495,
          "low": 0.96043,
          "close": 0.96212,
          "tick_volume": 29064.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-05T04:00:00Z"
        },
        {
          "time": 1772697600,
          "open": 0.9621,
          "high": 0.96354,
          "low": 0.9583,
          "close": 0.96118,
          "tick_volume": 28331.0,
          "spread": 5.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-05T08:00:00Z"
        },
        {
          "time": 1772712000,
          "open": 0.96118,
          "high": 0.96213,
          "low": 0.95803,
          "close": 0.95979,
          "tick_volume": 26565.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-05T12:00:00Z"
        },
        {
          "time": 1772726400,
          "open": 0.9598,
          "high": 0.9605,
          "low": 0.95594,
          "close": 0.95642,
          "tick_volume": 33294.0,
          "spread": 4.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-05T16:00:00Z"
        },
        {
          "time": 1772740800,
          "open": 0.95642,
          "high": 0.95899,
          "low": 0.95539,
          "close": 0.9583,
          "tick_volume": 15110.0,
          "spread": 3.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-05T20:00:00Z"
        },
        {
          "time": 1772755200,
          "open": 0.95823,
          "high": 0.96147,
          "low": 0.9578,
          "close": 0.96122,
          "tick_volume": 11576.0,
          "spread": 5.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-06T00:00:00Z"
        },
        {
          "time": 1772769600,
          "open": 0.96119,
          "high": 0.96173,
          "low": 0.96005,
          "close": 0.96148,
          "tick_volume": 16610.0,
          "spread": 4.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-06T04:00:00Z"
        },
        {
          "time": 1772784000,
          "open": 0.96148,
          "high": 0.96209,
          "low": 0.95663,
          "close": 0.95759,
          "tick_volume": 13211.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-06T08:00:00Z"
        },
        {
          "time": 1772798400,
          "open": 0.95759,
          "high": 0.95846,
          "low": 0.95285,
          "close": 0.95407,
          "tick_volume": 37266.0,
          "spread": 3.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-06T12:00:00Z"
        },
        {
          "time": 1772812800,
          "open": 0.95407,
          "high": 0.95646,
          "low": 0.95318,
          "close": 0.9538,
          "tick_volume": 33280.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-06T16:00:00Z"
        },
        {
          "time": 1772827200,
          "open": 0.9538,
          "high": 0.95476,
          "low": 0.95292,
          "close": 0.95358,
          "tick_volume": 11838.0,
          "spread": 3.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-06T20:00:00Z"
        },
        {
          "time": 1773000000,
          "open": 0.94995,
          "high": 0.95006,
          "low": 0.94687,
          "close": 0.94866,
          "tick_volume": 7156.0,
          "spread": 8.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-08T20:00:00Z"
        },
        {
          "time": 1773014400,
          "open": 0.94896,
          "high": 0.94935,
          "low": 0.94628,
          "close": 0.9492,
          "tick_volume": 20677.0,
          "spread": 5.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-09T00:00:00Z"
        },
        {
          "time": 1773028800,
          "open": 0.94919,
          "high": 0.95143,
          "low": 0.9471,
          "close": 0.94875,
          "tick_volume": 17601.0,
          "spread": 4.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-09T04:00:00Z"
        },
        {
          "time": 1773043200,
          "open": 0.94874,
          "high": 0.9533,
          "low": 0.94735,
          "close": 0.94983,
          "tick_volume": 26714.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-09T08:00:00Z"
        },
        {
          "time": 1773057600,
          "open": 0.94983,
          "high": 0.95601,
          "low": 0.94904,
          "close": 0.95517,
          "tick_volume": 29515.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-09T12:00:00Z"
        },
        {
          "time": 1773072000,
          "open": 0.95518,
          "high": 0.9575,
          "low": 0.95512,
          "close": 0.95629,
          "tick_volume": 16830.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-09T16:00:00Z"
        },
        {
          "time": 1773086400,
          "open": 0.95628,
          "high": 0.96186,
          "low": 0.95617,
          "close": 0.96051,
          "tick_volume": 14816.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-09T20:00:00Z"
        },
        {
          "time": 1773100800,
          "open": 0.96058,
          "high": 0.96199,
          "low": 0.95945,
          "close": 0.95968,
          "tick_volume": 14070.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-10T00:00:00Z"
        },
        {
          "time": 1773115200,
          "open": 0.95971,
          "high": 0.96364,
          "low": 0.95913,
          "close": 0.96287,
          "tick_volume": 10186.0,
          "spread": 5.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-10T04:00:00Z"
        },
        {
          "time": 1773129600,
          "open": 0.96288,
          "high": 0.96687,
          "low": 0.96264,
          "close": 0.96508,
          "tick_volume": 15593.0,
          "spread": 3.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-10T08:00:00Z"
        },
        {
          "time": 1773144000,
          "open": 0.96506,
          "high": 0.96852,
          "low": 0.96339,
          "close": 0.96842,
          "tick_volume": 28670.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-10T12:00:00Z"
        },
        {
          "time": 1773158400,
          "open": 0.96839,
          "high": 0.97277,
          "low": 0.96731,
          "close": 0.96845,
          "tick_volume": 25470.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-10T16:00:00Z"
        },
        {
          "time": 1773172800,
          "open": 0.96845,
          "high": 0.96876,
          "low": 0.96609,
          "close": 0.96649,
          "tick_volume": 9380.0,
          "spread": 3.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-10T20:00:00Z"
        },
        {
          "time": 1773187200,
          "open": 0.96651,
          "high": 0.97257,
          "low": 0.96651,
          "close": 0.9714,
          "tick_volume": 9150.0,
          "spread": 5.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-11T00:00:00Z"
        },
        {
          "time": 1773201600,
          "open": 0.9714,
          "high": 0.97408,
          "low": 0.97093,
          "close": 0.97303,
          "tick_volume": 8595.0,
          "spread": 5.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-11T04:00:00Z"
        },
        {
          "time": 1773216000,
          "open": 0.97298,
          "high": 0.97398,
          "low": 0.96971,
          "close": 0.97183,
          "tick_volume": 18752.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-11T08:00:00Z"
        },
        {
          "time": 1773230400,
          "open": 0.97182,
          "high": 0.97602,
          "low": 0.97056,
          "close": 0.97488,
          "tick_volume": 24271.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-11T12:00:00Z"
        },
        {
          "time": 1773244800,
          "open": 0.97488,
          "high": 0.97552,
          "low": 0.96961,
          "close": 0.97164,
          "tick_volume": 14269.0,
          "spread": 3.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-11T16:00:00Z"
        },
        {
          "time": 1773259200,
          "open": 0.97164,
          "high": 0.97271,
          "low": 0.96989,
          "close": 0.97024,
          "tick_volume": 4146.0,
          "spread": 4.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-11T20:00:00Z"
        },
        {
          "time": 1773273600,
          "open": 0.97026,
          "high": 0.97225,
          "low": 0.96879,
          "close": 0.96938,
          "tick_volume": 8275.0,
          "spread": 8.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-12T00:00:00Z"
        },
        {
          "time": 1773288000,
          "open": 0.9694,
          "high": 0.96981,
          "low": 0.96642,
          "close": 0.96796,
          "tick_volume": 8118.0,
          "spread": 6.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-12T04:00:00Z"
        },
        {
          "time": 1773302400,
          "open": 0.96796,
          "high": 0.9702,
          "low": 0.96763,
          "close": 0.96957,
          "tick_volume": 15874.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-12T08:00:00Z"
        },
        {
          "time": 1773316800,
          "open": 0.96955,
          "high": 0.97112,
          "low": 0.96377,
          "close": 0.96506,
          "tick_volume": 20435.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-12T12:00:00Z"
        },
        {
          "time": 1773331200,
          "open": 0.96501,
          "high": 0.96645,
          "low": 0.9637,
          "close": 0.96444,
          "tick_volume": 22087.0,
          "spread": 4.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-12T16:00:00Z"
        },
        {
          "time": 1773345600,
          "open": 0.96442,
          "high": 0.96564,
          "low": 0.96417,
          "close": 0.96529,
          "tick_volume": 4735.0,
          "spread": 4.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-12T20:00:00Z"
        },
        {
          "time": 1773360000,
          "open": 0.96521,
          "high": 0.96608,
          "low": 0.96371,
          "close": 0.96511,
          "tick_volume": 7454.0,
          "spread": 5.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-13T00:00:00Z"
        },
        {
          "time": 1773374400,
          "open": 0.96511,
          "high": 0.96532,
          "low": 0.96076,
          "close": 0.96088,
          "tick_volume": 8054.0,
          "spread": 4.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-13T04:00:00Z"
        },
        {
          "time": 1773388800,
          "open": 0.96083,
          "high": 0.96369,
          "low": 0.95864,
          "close": 0.96276,
          "tick_volume": 12992.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-13T08:00:00Z"
        },
        {
          "time": 1773403200,
          "open": 0.96276,
          "high": 0.96705,
          "low": 0.96197,
          "close": 0.96321,
          "tick_volume": 22669.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-13T12:00:00Z"
        },
        {
          "time": 1773417600,
          "open": 0.9632,
          "high": 0.96443,
          "low": 0.96061,
          "close": 0.9611,
          "tick_volume": 17319.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-13T16:00:00Z"
        },
        {
          "time": 1773432000,
          "open": 0.96107,
          "high": 0.96114,
          "low": 0.95785,
          "close": 0.9579,
          "tick_volume": 3398.0,
          "spread": 4.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-13T20:00:00Z"
        },
        {
          "time": 1773604800,
          "open": 0.96027,
          "high": 0.9605,
          "low": 0.95838,
          "close": 0.95933,
          "tick_volume": 2364.0,
          "spread": 9.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-15T20:00:00Z"
        },
        {
          "time": 1773619200,
          "open": 0.95961,
          "high": 0.9621,
          "low": 0.959,
          "close": 0.96082,
          "tick_volume": 8775.0,
          "spread": 5.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-16T00:00:00Z"
        },
        {
          "time": 1773633600,
          "open": 0.96084,
          "high": 0.96287,
          "low": 0.96056,
          "close": 0.96278,
          "tick_volume": 6280.0,
          "spread": 4.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-16T04:00:00Z"
        },
        {
          "time": 1773648000,
          "open": 0.96278,
          "high": 0.96538,
          "low": 0.96056,
          "close": 0.96534,
          "tick_volume": 10791.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-16T08:00:00Z"
        },
        {
          "time": 1773662400,
          "open": 0.96532,
          "high": 0.96656,
          "low": 0.96428,
          "close": 0.96524,
          "tick_volume": 14505.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-16T12:00:00Z"
        },
        {
          "time": 1773676800,
          "open": 0.96524,
          "high": 0.96767,
          "low": 0.96423,
          "close": 0.96748,
          "tick_volume": 11953.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-16T16:00:00Z"
        },
        {
          "time": 1773691200,
          "open": 0.96748,
          "high": 0.96847,
          "low": 0.96686,
          "close": 0.96703,
          "tick_volume": 4113.0,
          "spread": 3.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-16T20:00:00Z"
        },
        {
          "time": 1773705600,
          "open": 0.96699,
          "high": 0.9695,
          "low": 0.9664,
          "close": 0.96841,
          "tick_volume": 5352.0,
          "spread": 5.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-17T00:00:00Z"
        },
        {
          "time": 1773720000,
          "open": 0.96841,
          "high": 0.97056,
          "low": 0.96481,
          "close": 0.96836,
          "tick_volume": 13190.0,
          "spread": 3.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-17T04:00:00Z"
        },
        {
          "time": 1773734400,
          "open": 0.96836,
          "high": 0.97101,
          "low": 0.9669,
          "close": 0.97073,
          "tick_volume": 10385.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-17T08:00:00Z"
        },
        {
          "time": 1773748800,
          "open": 0.97073,
          "high": 0.97491,
          "low": 0.97002,
          "close": 0.97307,
          "tick_volume": 12771.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-17T12:00:00Z"
        },
        {
          "time": 1773763200,
          "open": 0.97307,
          "high": 0.97422,
          "low": 0.97205,
          "close": 0.97308,
          "tick_volume": 10440.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-17T16:00:00Z"
        },
        {
          "time": 1773777600,
          "open": 0.97307,
          "high": 0.97333,
          "low": 0.97171,
          "close": 0.97321,
          "tick_volume": 3070.0,
          "spread": 4.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-17T20:00:00Z"
        },
        {
          "time": 1773792000,
          "open": 0.9733,
          "high": 0.97448,
          "low": 0.97258,
          "close": 0.97271,
          "tick_volume": 7708.0,
          "spread": 4.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-18T00:00:00Z"
        },
        {
          "time": 1773806400,
          "open": 0.97271,
          "high": 0.97617,
          "low": 0.97257,
          "close": 0.97565,
          "tick_volume": 7014.0,
          "spread": 3.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-18T04:00:00Z"
        },
        {
          "time": 1773820800,
          "open": 0.97566,
          "high": 0.97587,
          "low": 0.97295,
          "close": 0.97303,
          "tick_volume": 7593.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-18T08:00:00Z"
        },
        {
          "time": 1773835200,
          "open": 0.97303,
          "high": 0.97338,
          "low": 0.96656,
          "close": 0.9693,
          "tick_volume": 21421.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-18T12:00:00Z"
        },
        {
          "time": 1773849600,
          "open": 0.96935,
          "high": 0.97114,
          "low": 0.96698,
          "close": 0.96727,
          "tick_volume": 16443.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-18T16:00:00Z"
        },
        {
          "time": 1773864000,
          "open": 0.96726,
          "high": 0.96782,
          "low": 0.96398,
          "close": 0.96467,
          "tick_volume": 7072.0,
          "spread": 4.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-18T20:00:00Z"
        },
        {
          "time": 1773878400,
          "open": 0.96444,
          "high": 0.96776,
          "low": 0.96423,
          "close": 0.96675,
          "tick_volume": 12919.0,
          "spread": 6.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-19T00:00:00Z"
        },
        {
          "time": 1773892800,
          "open": 0.96675,
          "high": 0.9677,
          "low": 0.96519,
          "close": 0.96579,
          "tick_volume": 12973.0,
          "spread": 6.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-19T04:00:00Z"
        },
        {
          "time": 1773907200,
          "open": 0.96577,
          "high": 0.96981,
          "low": 0.96474,
          "close": 0.96831,
          "tick_volume": 23455.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-19T08:00:00Z"
        },
        {
          "time": 1773921600,
          "open": 0.96832,
          "high": 0.96864,
          "low": 0.96095,
          "close": 0.96718,
          "tick_volume": 32581.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-19T12:00:00Z"
        },
        {
          "time": 1773936000,
          "open": 0.96713,
          "high": 0.97104,
          "low": 0.96461,
          "close": 0.97095,
          "tick_volume": 23687.0,
          "spread": 3.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-19T16:00:00Z"
        },
        {
          "time": 1773950400,
          "open": 0.97097,
          "high": 0.97464,
          "low": 0.97097,
          "close": 0.97292,
          "tick_volume": 13761.0,
          "spread": 6.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-19T20:00:00Z"
        },
        {
          "time": 1773964800,
          "open": 0.9731,
          "high": 0.97389,
          "low": 0.97203,
          "close": 0.9729,
          "tick_volume": 7667.0,
          "spread": 4.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-20T00:00:00Z"
        },
        {
          "time": 1773979200,
          "open": 0.9729,
          "high": 0.97421,
          "low": 0.97205,
          "close": 0.97255,
          "tick_volume": 7262.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-20T04:00:00Z"
        },
        {
          "time": 1773993600,
          "open": 0.97257,
          "high": 0.97395,
          "low": 0.96805,
          "close": 0.96972,
          "tick_volume": 12292.0,
          "spread": 3.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-20T08:00:00Z"
        },
        {
          "time": 1774008000,
          "open": 0.96972,
          "high": 0.97155,
          "low": 0.96486,
          "close": 0.96588,
          "tick_volume": 19748.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-20T12:00:00Z"
        },
        {
          "time": 1774022400,
          "open": 0.96588,
          "high": 0.96777,
          "low": 0.96206,
          "close": 0.96222,
          "tick_volume": 21360.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-20T16:00:00Z"
        },
        {
          "time": 1774036800,
          "open": 0.9622,
          "high": 0.964,
          "low": 0.96091,
          "close": 0.96366,
          "tick_volume": 6488.0,
          "spread": 4.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-20T20:00:00Z"
        },
        {
          "time": 1774209600,
          "open": 0.96089,
          "high": 0.96245,
          "low": 0.96086,
          "close": 0.96177,
          "tick_volume": 2060.0,
          "spread": 8.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-22T20:00:00Z"
        },
        {
          "time": 1774224000,
          "open": 0.96175,
          "high": 0.96221,
          "low": 0.9569,
          "close": 0.95748,
          "tick_volume": 15425.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-23T00:00:00Z"
        },
        {
          "time": 1774238400,
          "open": 0.9575,
          "high": 0.95809,
          "low": 0.95492,
          "close": 0.95518,
          "tick_volume": 12982.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-23T04:00:00Z"
        },
        {
          "time": 1774252800,
          "open": 0.95516,
          "high": 0.95774,
          "low": 0.95041,
          "close": 0.95204,
          "tick_volume": 19129.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-23T08:00:00Z"
        },
        {
          "time": 1774267200,
          "open": 0.95206,
          "high": 0.96572,
          "low": 0.95196,
          "close": 0.96527,
          "tick_volume": 110847.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-23T12:00:00Z"
        },
        {
          "time": 1774281600,
          "open": 0.96527,
          "high": 0.9669,
          "low": 0.95849,
          "close": 0.96381,
          "tick_volume": 49916.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-23T16:00:00Z"
        },
        {
          "time": 1774296000,
          "open": 0.96378,
          "high": 0.96391,
          "low": 0.96111,
          "close": 0.96311,
          "tick_volume": 7813.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-23T20:00:00Z"
        },
        {
          "time": 1774310400,
          "open": 0.963,
          "high": 0.96318,
          "low": 0.95755,
          "close": 0.95825,
          "tick_volume": 15896.0,
          "spread": 4.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-24T00:00:00Z"
        },
        {
          "time": 1774324800,
          "open": 0.95825,
          "high": 0.96078,
          "low": 0.95704,
          "close": 0.96071,
          "tick_volume": 12633.0,
          "spread": 3.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-24T04:00:00Z"
        },
        {
          "time": 1774339200,
          "open": 0.96073,
          "high": 0.96283,
          "low": 0.95611,
          "close": 0.95802,
          "tick_volume": 21649.0,
          "spread": 3.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-24T08:00:00Z"
        },
        {
          "time": 1774353600,
          "open": 0.958,
          "high": 0.95993,
          "low": 0.95491,
          "close": 0.95777,
          "tick_volume": 25971.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-24T12:00:00Z"
        },
        {
          "time": 1774368000,
          "open": 0.95778,
          "high": 0.95999,
          "low": 0.95639,
          "close": 0.95924,
          "tick_volume": 27082.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-24T16:00:00Z"
        },
        {
          "time": 1774382400,
          "open": 0.95924,
          "high": 0.96382,
          "low": 0.95857,
          "close": 0.96318,
          "tick_volume": 12595.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-24T20:00:00Z"
        },
        {
          "time": 1774396800,
          "open": 0.96316,
          "high": 0.96323,
          "low": 0.96012,
          "close": 0.96028,
          "tick_volume": 11358.0,
          "spread": 3.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-25T00:00:00Z"
        },
        {
          "time": 1774411200,
          "open": 0.96028,
          "high": 0.96125,
          "low": 0.95988,
          "close": 0.96055,
          "tick_volume": 6721.0,
          "spread": 4.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-25T04:00:00Z"
        },
        {
          "time": 1774425600,
          "open": 0.96058,
          "high": 0.96327,
          "low": 0.95954,
          "close": 0.96099,
          "tick_volume": 13573.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-25T08:00:00Z"
        },
        {
          "time": 1774440000,
          "open": 0.96099,
          "high": 0.96186,
          "low": 0.95733,
          "close": 0.96097,
          "tick_volume": 19230.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-25T12:00:00Z"
        },
        {
          "time": 1774454400,
          "open": 0.96099,
          "high": 0.96219,
          "low": 0.95898,
          "close": 0.96007,
          "tick_volume": 19823.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-25T16:00:00Z"
        },
        {
          "time": 1774468800,
          "open": 0.96007,
          "high": 0.96031,
          "low": 0.9585,
          "close": 0.95941,
          "tick_volume": 4834.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-25T20:00:00Z"
        },
        {
          "time": 1774483200,
          "open": 0.95944,
          "high": 0.95997,
          "low": 0.95859,
          "close": 0.95903,
          "tick_volume": 8856.0,
          "spread": 6.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-26T00:00:00Z"
        },
        {
          "time": 1774497600,
          "open": 0.959,
          "high": 0.96125,
          "low": 0.959,
          "close": 0.96057,
          "tick_volume": 15625.0,
          "spread": 5.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-26T04:00:00Z"
        },
        {
          "time": 1774512000,
          "open": 0.96057,
          "high": 0.9606,
          "low": 0.95842,
          "close": 0.95891,
          "tick_volume": 12762.0,
          "spread": 5.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-26T08:00:00Z"
        },
        {
          "time": 1774526400,
          "open": 0.95891,
          "high": 0.95927,
          "low": 0.95471,
          "close": 0.95678,
          "tick_volume": 16714.0,
          "spread": 3.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-26T12:00:00Z"
        },
        {
          "time": 1774540800,
          "open": 0.95681,
          "high": 0.95785,
          "low": 0.95375,
          "close": 0.95456,
          "tick_volume": 15214.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-26T16:00:00Z"
        },
        {
          "time": 1774555200,
          "open": 0.95455,
          "high": 0.95727,
          "low": 0.95268,
          "close": 0.95481,
          "tick_volume": 13291.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-26T20:00:00Z"
        },
        {
          "time": 1774569600,
          "open": 0.95474,
          "high": 0.95514,
          "low": 0.95245,
          "close": 0.95485,
          "tick_volume": 9071.0,
          "spread": 3.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-27T00:00:00Z"
        },
        {
          "time": 1774584000,
          "open": 0.95485,
          "high": 0.95733,
          "low": 0.95474,
          "close": 0.95579,
          "tick_volume": 7252.0,
          "spread": 5.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-27T04:00:00Z"
        },
        {
          "time": 1774598400,
          "open": 0.9558,
          "high": 0.95593,
          "low": 0.95335,
          "close": 0.95472,
          "tick_volume": 9521.0,
          "spread": 3.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-27T08:00:00Z"
        },
        {
          "time": 1774612800,
          "open": 0.95476,
          "high": 0.95592,
          "low": 0.95336,
          "close": 0.95519,
          "tick_volume": 15978.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-27T12:00:00Z"
        },
        {
          "time": 1774627200,
          "open": 0.95519,
          "high": 0.95713,
          "low": 0.95328,
          "close": 0.95426,
          "tick_volume": 15907.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-27T16:00:00Z"
        },
        {
          "time": 1774641600,
          "open": 0.95426,
          "high": 0.95592,
          "low": 0.95383,
          "close": 0.95476,
          "tick_volume": 4843.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-27T20:00:00Z"
        },
        {
          "time": 1774814400,
          "open": 0.95341,
          "high": 0.9537,
          "low": 0.95153,
          "close": 0.95344,
          "tick_volume": 766.0,
          "spread": 104.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-29T20:00:00Z"
        },
        {
          "time": 1774828800,
          "open": 0.95386,
          "high": 0.95386,
          "low": 0.95091,
          "close": 0.95177,
          "tick_volume": 14402.0,
          "spread": 4.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-30T00:00:00Z"
        },
        {
          "time": 1774843200,
          "open": 0.95177,
          "high": 0.95469,
          "low": 0.95161,
          "close": 0.95394,
          "tick_volume": 9920.0,
          "spread": 3.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-30T04:00:00Z"
        },
        {
          "time": 1774857600,
          "open": 0.95395,
          "high": 0.95499,
          "low": 0.95239,
          "close": 0.9541,
          "tick_volume": 11305.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-30T08:00:00Z"
        },
        {
          "time": 1774872000,
          "open": 0.9541,
          "high": 0.95591,
          "low": 0.95278,
          "close": 0.95327,
          "tick_volume": 13820.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-30T12:00:00Z"
        },
        {
          "time": 1774886400,
          "open": 0.95327,
          "high": 0.95522,
          "low": 0.95229,
          "close": 0.95428,
          "tick_volume": 18786.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-30T16:00:00Z"
        },
        {
          "time": 1774900800,
          "open": 0.95428,
          "high": 0.9546,
          "low": 0.95292,
          "close": 0.95421,
          "tick_volume": 5881.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-30T20:00:00Z"
        },
        {
          "time": 1774915200,
          "open": 0.95439,
          "high": 0.95674,
          "low": 0.95232,
          "close": 0.95596,
          "tick_volume": 11681.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-31T00:00:00Z"
        },
        {
          "time": 1774929600,
          "open": 0.95596,
          "high": 0.95628,
          "low": 0.95286,
          "close": 0.95418,
          "tick_volume": 12600.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-31T04:00:00Z"
        },
        {
          "time": 1774944000,
          "open": 0.95416,
          "high": 0.95719,
          "low": 0.95382,
          "close": 0.9558,
          "tick_volume": 11877.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-31T08:00:00Z"
        },
        {
          "time": 1774958400,
          "open": 0.9558,
          "high": 0.96013,
          "low": 0.95515,
          "close": 0.95884,
          "tick_volume": 17449.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-31T12:00:00Z"
        },
        {
          "time": 1774972800,
          "open": 0.95883,
          "high": 0.96126,
          "low": 0.95407,
          "close": 0.9593,
          "tick_volume": 33797.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-31T16:00:00Z"
        },
        {
          "time": 1774987200,
          "open": 0.95933,
          "high": 0.96088,
          "low": 0.95908,
          "close": 0.95968,
          "tick_volume": 8571.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-31T20:00:00Z"
        },
        {
          "time": 1775001600,
          "open": 0.9601,
          "high": 0.96296,
          "low": 0.95974,
          "close": 0.96143,
          "tick_volume": 8795.0,
          "spread": 6.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-04-01T00:00:00Z"
        },
        {
          "time": 1775016000,
          "open": 0.96145,
          "high": 0.96192,
          "low": 0.95957,
          "close": 0.96004,
          "tick_volume": 17599.0,
          "spread": 6.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-04-01T04:00:00Z"
        },
        {
          "time": 1775030400,
          "open": 0.96005,
          "high": 0.9654,
          "low": 0.95997,
          "close": 0.96396,
          "tick_volume": 26806.0,
          "spread": 5.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-04-01T08:00:00Z"
        },
        {
          "time": 1775044800,
          "open": 0.96399,
          "high": 0.96668,
          "low": 0.9633,
          "close": 0.96473,
          "tick_volume": 21449.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-04-01T12:00:00Z"
        },
        {
          "time": 1775059200,
          "open": 0.96462,
          "high": 0.96521,
          "low": 0.96237,
          "close": 0.96239,
          "tick_volume": 21206.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-04-01T16:00:00Z"
        },
        {
          "time": 1775073600,
          "open": 0.96237,
          "high": 0.96245,
          "low": 0.96024,
          "close": 0.9615,
          "tick_volume": 11025.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-04-01T20:00:00Z"
        },
        {
          "time": 1775088000,
          "open": 0.96133,
          "high": 0.96258,
          "low": 0.95606,
          "close": 0.95662,
          "tick_volume": 26703.0,
          "spread": 4.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-04-02T00:00:00Z"
        },
        {
          "time": 1775102400,
          "open": 0.95661,
          "high": 0.95789,
          "low": 0.95556,
          "close": 0.95559,
          "tick_volume": 17428.0,
          "spread": 4.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-04-02T04:00:00Z"
        },
        {
          "time": 1775116800,
          "open": 0.95562,
          "high": 0.95772,
          "low": 0.95534,
          "close": 0.95693,
          "tick_volume": 11085.0,
          "spread": 5.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-04-02T08:00:00Z"
        },
        {
          "time": 1775131200,
          "open": 0.95693,
          "high": 0.95968,
          "low": 0.95525,
          "close": 0.95962,
          "tick_volume": 12852.0,
          "spread": 3.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-04-02T12:00:00Z"
        },
        {
          "time": 1775145600,
          "open": 0.95962,
          "high": 0.96275,
          "low": 0.95896,
          "close": 0.96089,
          "tick_volume": 22080.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-04-02T16:00:00Z"
        },
        {
          "time": 1775160000,
          "open": 0.96089,
          "high": 0.96202,
          "low": 0.96033,
          "close": 0.96086,
          "tick_volume": 5272.0,
          "spread": 5.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-04-02T20:00:00Z"
        },
        {
          "time": 1775174400,
          "open": 0.96151,
          "high": 0.96255,
          "low": 0.9615,
          "close": 0.96192,
          "tick_volume": 1620.0,
          "spread": 8.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-04-03T00:00:00Z"
        },
        {
          "time": 1775188800,
          "open": 0.96191,
          "high": 0.96212,
          "low": 0.96136,
          "close": 0.96171,
          "tick_volume": 1301.0,
          "spread": 10.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-04-03T04:00:00Z"
        },
        {
          "time": 1775203200,
          "open": 0.9617,
          "high": 0.96245,
          "low": 0.96114,
          "close": 0.96134,
          "tick_volume": 2079.0,
          "spread": 8.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-04-03T08:00:00Z"
        },
        {
          "time": 1775217600,
          "open": 0.96137,
          "high": 0.96268,
          "low": 0.9608,
          "close": 0.96211,
          "tick_volume": 5091.0,
          "spread": 8.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-04-03T12:00:00Z"
        },
        {
          "time": 1775232000,
          "open": 0.9621,
          "high": 0.96214,
          "low": 0.96042,
          "close": 0.96101,
          "tick_volume": 11800.0,
          "spread": 9.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-04-03T16:00:00Z"
        },
        {
          "time": 1775246400,
          "open": 0.96101,
          "high": 0.96204,
          "low": 0.95972,
          "close": 0.96139,
          "tick_volume": 6747.0,
          "spread": 24.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-04-03T20:00:00Z"
        },
        {
          "time": 1775419200,
          "open": 0.95985,
          "high": 0.95986,
          "low": 0.95935,
          "close": 0.95982,
          "tick_volume": 128.0,
          "spread": 200.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-04-05T20:00:00Z"
        },
        {
          "time": 1775433600,
          "open": 0.96007,
          "high": 0.96204,
          "low": 0.95903,
          "close": 0.96157,
          "tick_volume": 7662.0,
          "spread": 3.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-04-06T00:00:00Z"
        },
        {
          "time": 1775448000,
          "open": 0.9616,
          "high": 0.96386,
          "low": 0.9616,
          "close": 0.96285,
          "tick_volume": 5247.0,
          "spread": 4.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-04-06T04:00:00Z"
        },
        {
          "time": 1775462400,
          "open": 0.96285,
          "high": 0.96551,
          "low": 0.96267,
          "close": 0.96404,
          "tick_volume": 7109.0,
          "spread": 4.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-04-06T08:00:00Z"
        },
        {
          "time": 1775476800,
          "open": 0.96407,
          "high": 0.96502,
          "low": 0.96323,
          "close": 0.96385,
          "tick_volume": 6675.0,
          "spread": 5.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-04-06T12:00:00Z"
        },
        {
          "time": 1775491200,
          "open": 0.96387,
          "high": 0.96463,
          "low": 0.96142,
          "close": 0.96232,
          "tick_volume": 10436.0,
          "spread": 5.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-04-06T16:00:00Z"
        },
        {
          "time": 1775505600,
          "open": 0.96232,
          "high": 0.96334,
          "low": 0.96191,
          "close": 0.96222,
          "tick_volume": 3466.0,
          "spread": 5.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-04-06T20:00:00Z"
        },
        {
          "time": 1775520000,
          "open": 0.96238,
          "high": 0.96325,
          "low": 0.96089,
          "close": 0.96125,
          "tick_volume": 8205.0,
          "spread": 3.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-04-07T00:00:00Z"
        },
        {
          "time": 1775534400,
          "open": 0.96125,
          "high": 0.96294,
          "low": 0.96084,
          "close": 0.96265,
          "tick_volume": 7327.0,
          "spread": 4.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-04-07T04:00:00Z"
        },
        {
          "time": 1775548800,
          "open": 0.96265,
          "high": 0.96681,
          "low": 0.96205,
          "close": 0.96598,
          "tick_volume": 15565.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-04-07T08:00:00Z"
        },
        {
          "time": 1775563200,
          "open": 0.966,
          "high": 0.96644,
          "low": 0.96415,
          "close": 0.96418,
          "tick_volume": 17217.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-04-07T12:00:00Z"
        },
        {
          "time": 1775577600,
          "open": 0.96418,
          "high": 0.96685,
          "low": 0.96387,
          "close": 0.96665,
          "tick_volume": 19293.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-04-07T16:00:00Z"
        },
        {
          "time": 1775592000,
          "open": 0.96666,
          "high": 0.96984,
          "low": 0.96557,
          "close": 0.96902,
          "tick_volume": 15360.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-04-07T20:00:00Z"
        },
        {
          "time": 1775606400,
          "open": 0.97045,
          "high": 0.98018,
          "low": 0.96827,
          "close": 0.97777,
          "tick_volume": 34134.0,
          "spread": 7.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-04-08T00:00:00Z"
        },
        {
          "time": 1775620800,
          "open": 0.97776,
          "high": 0.97918,
          "low": 0.97489,
          "close": 0.97812,
          "tick_volume": 9987.0,
          "spread": 5.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-04-08T04:00:00Z"
        },
        {
          "time": 1775635200,
          "open": 0.9781,
          "high": 0.97984,
          "low": 0.97504,
          "close": 0.97587,
          "tick_volume": 15632.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-04-08T08:00:00Z"
        },
        {
          "time": 1775649600,
          "open": 0.97587,
          "high": 0.97957,
          "low": 0.97559,
          "close": 0.97765,
          "tick_volume": 16717.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-04-08T12:00:00Z"
        },
        {
          "time": 1775664000,
          "open": 0.97763,
          "high": 0.97852,
          "low": 0.97511,
          "close": 0.97626,
          "tick_volume": 22732.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-04-08T16:00:00Z"
        },
        {
          "time": 1775678400,
          "open": 0.9763,
          "high": 0.97701,
          "low": 0.97415,
          "close": 0.97571,
          "tick_volume": 10208.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-04-08T20:00:00Z"
        },
        {
          "time": 1775692800,
          "open": 0.97531,
          "high": 0.97579,
          "low": 0.97342,
          "close": 0.97429,
          "tick_volume": 8211.0,
          "spread": 5.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-04-09T00:00:00Z"
        },
        {
          "time": 1775707200,
          "open": 0.97429,
          "high": 0.97554,
          "low": 0.97385,
          "close": 0.97522,
          "tick_volume": 7099.0,
          "spread": 7.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-04-09T04:00:00Z"
        }
      ]
    },
    "D1": {
      "timeframe": "D1",
      "bars": [
        {
          "time": 1749600000,
          "open": 0.89196,
          "high": 0.89378,
          "low": 0.88796,
          "close": 0.88889,
          "tick_volume": 67584.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-06-11T00:00:00Z"
        },
        {
          "time": 1749686400,
          "open": 0.88855,
          "high": 0.88977,
          "low": 0.88552,
          "close": 0.8889,
          "tick_volume": 70158.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-06-12T00:00:00Z"
        },
        {
          "time": 1749772800,
          "open": 0.8887,
          "high": 0.8887,
          "low": 0.88043,
          "close": 0.88171,
          "tick_volume": 84889.0,
          "spread": 3.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-06-13T00:00:00Z"
        },
        {
          "time": 1749945600,
          "open": 0.88107,
          "high": 0.88255,
          "low": 0.88081,
          "close": 0.88146,
          "tick_volume": 781.0,
          "spread": 47.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-06-15T00:00:00Z"
        },
        {
          "time": 1750032000,
          "open": 0.88082,
          "high": 0.88742,
          "low": 0.87978,
          "close": 0.88582,
          "tick_volume": 76564.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-06-16T00:00:00Z"
        },
        {
          "time": 1750118400,
          "open": 0.88558,
          "high": 0.88826,
          "low": 0.88212,
          "close": 0.8859,
          "tick_volume": 80510.0,
          "spread": 3.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-06-17T00:00:00Z"
        },
        {
          "time": 1750204800,
          "open": 0.88575,
          "high": 0.89281,
          "low": 0.88519,
          "close": 0.89051,
          "tick_volume": 77990.0,
          "spread": 3.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-06-18T00:00:00Z"
        },
        {
          "time": 1750291200,
          "open": 0.891,
          "high": 0.8914,
          "low": 0.88559,
          "close": 0.88734,
          "tick_volume": 58199.0,
          "spread": 4.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-06-19T00:00:00Z"
        },
        {
          "time": 1750377600,
          "open": 0.88777,
          "high": 0.8906,
          "low": 0.88574,
          "close": 0.88599,
          "tick_volume": 65294.0,
          "spread": 4.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-06-20T00:00:00Z"
        },
        {
          "time": 1750550400,
          "open": 0.88433,
          "high": 0.88536,
          "low": 0.88325,
          "close": 0.88372,
          "tick_volume": 399.0,
          "spread": 188.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-06-22T00:00:00Z"
        },
        {
          "time": 1750636800,
          "open": 0.88282,
          "high": 0.88753,
          "low": 0.87906,
          "close": 0.88681,
          "tick_volume": 78445.0,
          "spread": 3.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-06-23T00:00:00Z"
        },
        {
          "time": 1750723200,
          "open": 0.887,
          "high": 0.89338,
          "low": 0.88684,
          "close": 0.89033,
          "tick_volume": 75677.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-06-24T00:00:00Z"
        },
        {
          "time": 1750809600,
          "open": 0.89079,
          "high": 0.89408,
          "low": 0.89047,
          "close": 0.89291,
          "tick_volume": 66603.0,
          "spread": 3.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-06-25T00:00:00Z"
        },
        {
          "time": 1750896000,
          "open": 0.8931,
          "high": 0.89617,
          "low": 0.89242,
          "close": 0.8932,
          "tick_volume": 68024.0,
          "spread": 4.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-06-26T00:00:00Z"
        },
        {
          "time": 1750982400,
          "open": 0.89302,
          "high": 0.89612,
          "low": 0.8906,
          "close": 0.89359,
          "tick_volume": 68832.0,
          "spread": 4.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-06-27T00:00:00Z"
        },
        {
          "time": 1751155200,
          "open": 0.89475,
          "high": 0.89523,
          "low": 0.89444,
          "close": 0.89503,
          "tick_volume": 309.0,
          "spread": 82.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-06-29T00:00:00Z"
        },
        {
          "time": 1751241600,
          "open": 0.89475,
          "high": 0.89674,
          "low": 0.89219,
          "close": 0.89535,
          "tick_volume": 69930.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-06-30T00:00:00Z"
        },
        {
          "time": 1751328000,
          "open": 0.89555,
          "high": 0.89832,
          "low": 0.8925,
          "close": 0.89743,
          "tick_volume": 63787.0,
          "spread": 3.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-07-01T00:00:00Z"
        },
        {
          "time": 1751414400,
          "open": 0.89768,
          "high": 0.89829,
          "low": 0.8932,
          "close": 0.89467,
          "tick_volume": 66037.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-07-02T00:00:00Z"
        },
        {
          "time": 1751500800,
          "open": 0.89464,
          "high": 0.89511,
          "low": 0.89016,
          "close": 0.89288,
          "tick_volume": 48378.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-07-03T00:00:00Z"
        },
        {
          "time": 1751587200,
          "open": 0.89273,
          "high": 0.89312,
          "low": 0.88997,
          "close": 0.89153,
          "tick_volume": 53944.0,
          "spread": 3.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-07-04T00:00:00Z"
        },
        {
          "time": 1751760000,
          "open": 0.89342,
          "high": 0.89342,
          "low": 0.8911,
          "close": 0.89182,
          "tick_volume": 56.0,
          "spread": 200.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-07-06T00:00:00Z"
        },
        {
          "time": 1751846400,
          "open": 0.89152,
          "high": 0.89178,
          "low": 0.88663,
          "close": 0.88808,
          "tick_volume": 51351.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-07-07T00:00:00Z"
        },
        {
          "time": 1751932800,
          "open": 0.88827,
          "high": 0.89447,
          "low": 0.88792,
          "close": 0.89174,
          "tick_volume": 47514.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-07-08T00:00:00Z"
        },
        {
          "time": 1752019200,
          "open": 0.89166,
          "high": 0.89581,
          "low": 0.89101,
          "close": 0.89446,
          "tick_volume": 46210.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-07-09T00:00:00Z"
        },
        {
          "time": 1752105600,
          "open": 0.89449,
          "high": 0.90056,
          "low": 0.89419,
          "close": 0.89943,
          "tick_volume": 38779.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-07-10T00:00:00Z"
        },
        {
          "time": 1752192000,
          "open": 0.89975,
          "high": 0.90225,
          "low": 0.89841,
          "close": 0.90031,
          "tick_volume": 36952.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-07-11T00:00:00Z"
        },
        {
          "time": 1752364800,
          "open": 0.89949,
          "high": 0.8995,
          "low": 0.89877,
          "close": 0.89939,
          "tick_volume": 113.0,
          "spread": 92.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-07-13T00:00:00Z"
        },
        {
          "time": 1752451200,
          "open": 0.89945,
          "high": 0.90118,
          "low": 0.89628,
          "close": 0.89717,
          "tick_volume": 26966.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-07-14T00:00:00Z"
        },
        {
          "time": 1752537600,
          "open": 0.89716,
          "high": 0.89973,
          "low": 0.89323,
          "close": 0.89358,
          "tick_volume": 26960.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-07-15T00:00:00Z"
        },
        {
          "time": 1752624000,
          "open": 0.89356,
          "high": 0.89672,
          "low": 0.89298,
          "close": 0.89341,
          "tick_volume": 31965.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-07-16T00:00:00Z"
        },
        {
          "time": 1752710400,
          "open": 0.89337,
          "high": 0.8934,
          "low": 0.88767,
          "close": 0.89182,
          "tick_volume": 31025.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-07-17T00:00:00Z"
        },
        {
          "time": 1752796800,
          "open": 0.89211,
          "high": 0.89626,
          "low": 0.89211,
          "close": 0.89239,
          "tick_volume": 22906.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-07-18T00:00:00Z"
        },
        {
          "time": 1752969600,
          "open": 0.89363,
          "high": 0.89451,
          "low": 0.89322,
          "close": 0.8938,
          "tick_volume": 176.0,
          "spread": 154.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-07-20T00:00:00Z"
        },
        {
          "time": 1753056000,
          "open": 0.89341,
          "high": 0.89447,
          "low": 0.89221,
          "close": 0.89265,
          "tick_volume": 24366.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-07-21T00:00:00Z"
        },
        {
          "time": 1753142400,
          "open": 0.89249,
          "high": 0.8937,
          "low": 0.89041,
          "close": 0.8915,
          "tick_volume": 27481.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-07-22T00:00:00Z"
        },
        {
          "time": 1753228800,
          "open": 0.89161,
          "high": 0.89798,
          "low": 0.89098,
          "close": 0.89745,
          "tick_volume": 29149.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-07-23T00:00:00Z"
        },
        {
          "time": 1753315200,
          "open": 0.8977,
          "high": 0.90096,
          "low": 0.89746,
          "close": 0.89931,
          "tick_volume": 28525.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-07-24T00:00:00Z"
        },
        {
          "time": 1753401600,
          "open": 0.89898,
          "high": 0.90009,
          "low": 0.89693,
          "close": 0.89964,
          "tick_volume": 27963.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-07-25T00:00:00Z"
        },
        {
          "time": 1753574400,
          "open": 0.90149,
          "high": 0.90149,
          "low": 0.90079,
          "close": 0.90084,
          "tick_volume": 82.0,
          "spread": 113.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-07-27T00:00:00Z"
        },
        {
          "time": 1753660800,
          "open": 0.90089,
          "high": 0.90155,
          "low": 0.89389,
          "close": 0.89606,
          "tick_volume": 29627.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-07-28T00:00:00Z"
        },
        {
          "time": 1753747200,
          "open": 0.89591,
          "high": 0.89762,
          "low": 0.89382,
          "close": 0.89669,
          "tick_volume": 27048.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-07-29T00:00:00Z"
        },
        {
          "time": 1753833600,
          "open": 0.89674,
          "high": 0.89833,
          "low": 0.88812,
          "close": 0.89019,
          "tick_volume": 35031.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-07-30T00:00:00Z"
        },
        {
          "time": 1753920000,
          "open": 0.89013,
          "high": 0.89448,
          "low": 0.8895,
          "close": 0.89001,
          "tick_volume": 36982.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-07-31T00:00:00Z"
        },
        {
          "time": 1754006400,
          "open": 0.89021,
          "high": 0.89547,
          "low": 0.88885,
          "close": 0.89182,
          "tick_volume": 43355.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-08-01T00:00:00Z"
        },
        {
          "time": 1754179200,
          "open": 0.89054,
          "high": 0.89152,
          "low": 0.89054,
          "close": 0.89107,
          "tick_volume": 691.0,
          "spread": 126.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-08-03T00:00:00Z"
        },
        {
          "time": 1754265600,
          "open": 0.89187,
          "high": 0.89355,
          "low": 0.8901,
          "close": 0.89178,
          "tick_volume": 27297.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-08-04T00:00:00Z"
        },
        {
          "time": 1754352000,
          "open": 0.8914,
          "high": 0.89288,
          "low": 0.88999,
          "close": 0.89136,
          "tick_volume": 29866.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-08-05T00:00:00Z"
        },
        {
          "time": 1754438400,
          "open": 0.89132,
          "high": 0.89497,
          "low": 0.89102,
          "close": 0.89327,
          "tick_volume": 27174.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-08-06T00:00:00Z"
        },
        {
          "time": 1754524800,
          "open": 0.89356,
          "high": 0.89762,
          "low": 0.89274,
          "close": 0.89628,
          "tick_volume": 28216.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-08-07T00:00:00Z"
        },
        {
          "time": 1754611200,
          "open": 0.89663,
          "high": 0.89797,
          "low": 0.89519,
          "close": 0.89706,
          "tick_volume": 24628.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-08-08T00:00:00Z"
        },
        {
          "time": 1754784000,
          "open": 0.89724,
          "high": 0.89753,
          "low": 0.89694,
          "close": 0.89715,
          "tick_volume": 179.0,
          "spread": 122.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-08-10T00:00:00Z"
        },
        {
          "time": 1754870400,
          "open": 0.89706,
          "high": 0.89811,
          "low": 0.89598,
          "close": 0.89761,
          "tick_volume": 24275.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-08-11T00:00:00Z"
        },
        {
          "time": 1754956800,
          "open": 0.89758,
          "high": 0.89984,
          "low": 0.89471,
          "close": 0.89919,
          "tick_volume": 30696.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-08-12T00:00:00Z"
        },
        {
          "time": 1755043200,
          "open": 0.89929,
          "high": 0.90251,
          "low": 0.89796,
          "close": 0.90053,
          "tick_volume": 21801.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-08-13T00:00:00Z"
        },
        {
          "time": 1755129600,
          "open": 0.9005,
          "high": 0.90282,
          "low": 0.89538,
          "close": 0.89779,
          "tick_volume": 27155.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-08-14T00:00:00Z"
        },
        {
          "time": 1755216000,
          "open": 0.89749,
          "high": 0.90038,
          "low": 0.89614,
          "close": 0.89946,
          "tick_volume": 20833.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-08-15T00:00:00Z"
        },
        {
          "time": 1755388800,
          "open": 0.89945,
          "high": 0.89945,
          "low": 0.89883,
          "close": 0.8992,
          "tick_volume": 267.0,
          "spread": 78.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-08-17T00:00:00Z"
        },
        {
          "time": 1755475200,
          "open": 0.89951,
          "high": 0.90041,
          "low": 0.89592,
          "close": 0.89616,
          "tick_volume": 20409.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-08-18T00:00:00Z"
        },
        {
          "time": 1755561600,
          "open": 0.89618,
          "high": 0.89749,
          "low": 0.89418,
          "close": 0.89502,
          "tick_volume": 23716.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-08-19T00:00:00Z"
        },
        {
          "time": 1755648000,
          "open": 0.89487,
          "high": 0.89516,
          "low": 0.89086,
          "close": 0.89218,
          "tick_volume": 27646.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-08-20T00:00:00Z"
        },
        {
          "time": 1755734400,
          "open": 0.89227,
          "high": 0.89402,
          "low": 0.89038,
          "close": 0.893,
          "tick_volume": 31619.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-08-21T00:00:00Z"
        },
        {
          "time": 1755820800,
          "open": 0.89306,
          "high": 0.89917,
          "low": 0.89272,
          "close": 0.89752,
          "tick_volume": 27767.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-08-22T00:00:00Z"
        },
        {
          "time": 1755993600,
          "open": 0.89724,
          "high": 0.89804,
          "low": 0.89712,
          "close": 0.8976,
          "tick_volume": 252.0,
          "spread": 134.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-08-24T00:00:00Z"
        },
        {
          "time": 1756080000,
          "open": 0.89773,
          "high": 0.89936,
          "low": 0.89589,
          "close": 0.89826,
          "tick_volume": 20416.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-08-25T00:00:00Z"
        },
        {
          "time": 1756166400,
          "open": 0.89842,
          "high": 0.89931,
          "low": 0.89673,
          "close": 0.89838,
          "tick_volume": 24480.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-08-26T00:00:00Z"
        },
        {
          "time": 1756252800,
          "open": 0.89875,
          "high": 0.89947,
          "low": 0.89523,
          "close": 0.89656,
          "tick_volume": 22198.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-08-27T00:00:00Z"
        },
        {
          "time": 1756339200,
          "open": 0.89696,
          "high": 0.89884,
          "low": 0.89664,
          "close": 0.8979,
          "tick_volume": 25898.0,
          "spread": 3.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-08-28T00:00:00Z"
        },
        {
          "time": 1756425600,
          "open": 0.89802,
          "high": 0.89963,
          "low": 0.8972,
          "close": 0.89885,
          "tick_volume": 21485.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-08-29T00:00:00Z"
        },
        {
          "time": 1756598400,
          "open": 0.89915,
          "high": 0.89937,
          "low": 0.89822,
          "close": 0.89846,
          "tick_volume": 340.0,
          "spread": 90.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-08-31T00:00:00Z"
        },
        {
          "time": 1756684800,
          "open": 0.89871,
          "high": 0.90191,
          "low": 0.89816,
          "close": 0.90097,
          "tick_volume": 14663.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-09-01T00:00:00Z"
        },
        {
          "time": 1756771200,
          "open": 0.90124,
          "high": 0.90164,
          "low": 0.89534,
          "close": 0.89825,
          "tick_volume": 30095.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-09-02T00:00:00Z"
        },
        {
          "time": 1756857600,
          "open": 0.89837,
          "high": 0.90371,
          "low": 0.89769,
          "close": 0.90222,
          "tick_volume": 25858.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-09-03T00:00:00Z"
        },
        {
          "time": 1756944000,
          "open": 0.90252,
          "high": 0.90345,
          "low": 0.89917,
          "close": 0.90034,
          "tick_volume": 27154.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-09-04T00:00:00Z"
        },
        {
          "time": 1757030400,
          "open": 0.9005,
          "high": 0.9096,
          "low": 0.9005,
          "close": 0.90661,
          "tick_volume": 29001.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-09-05T00:00:00Z"
        },
        {
          "time": 1757203200,
          "open": 0.90647,
          "high": 0.90744,
          "low": 0.90644,
          "close": 0.90672,
          "tick_volume": 696.0,
          "spread": 48.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-09-07T00:00:00Z"
        },
        {
          "time": 1757289600,
          "open": 0.90695,
          "high": 0.91086,
          "low": 0.90607,
          "close": 0.90947,
          "tick_volume": 23659.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-09-08T00:00:00Z"
        },
        {
          "time": 1757376000,
          "open": 0.9096,
          "high": 0.9135,
          "low": 0.90951,
          "close": 0.9113,
          "tick_volume": 24853.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-09-09T00:00:00Z"
        },
        {
          "time": 1757462400,
          "open": 0.91141,
          "high": 0.91823,
          "low": 0.91132,
          "close": 0.91644,
          "tick_volume": 24884.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-09-10T00:00:00Z"
        },
        {
          "time": 1757548800,
          "open": 0.91656,
          "high": 0.92214,
          "low": 0.91534,
          "close": 0.92142,
          "tick_volume": 29950.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-09-11T00:00:00Z"
        },
        {
          "time": 1757635200,
          "open": 0.92142,
          "high": 0.92274,
          "low": 0.91871,
          "close": 0.92054,
          "tick_volume": 23794.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-09-12T00:00:00Z"
        },
        {
          "time": 1757808000,
          "open": 0.91874,
          "high": 0.92027,
          "low": 0.91844,
          "close": 0.91944,
          "tick_volume": 504.0,
          "spread": 105.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-09-14T00:00:00Z"
        },
        {
          "time": 1757894400,
          "open": 0.92019,
          "high": 0.92229,
          "low": 0.9181,
          "close": 0.91878,
          "tick_volume": 24383.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-09-15T00:00:00Z"
        },
        {
          "time": 1757980800,
          "open": 0.91901,
          "high": 0.91943,
          "low": 0.91627,
          "close": 0.91833,
          "tick_volume": 25388.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-09-16T00:00:00Z"
        },
        {
          "time": 1758067200,
          "open": 0.91835,
          "high": 0.92067,
          "low": 0.91514,
          "close": 0.91621,
          "tick_volume": 31800.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-09-17T00:00:00Z"
        },
        {
          "time": 1758153600,
          "open": 0.91634,
          "high": 0.91681,
          "low": 0.91165,
          "close": 0.91239,
          "tick_volume": 35821.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-09-18T00:00:00Z"
        },
        {
          "time": 1758240000,
          "open": 0.91234,
          "high": 0.91289,
          "low": 0.90772,
          "close": 0.90841,
          "tick_volume": 25783.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-09-19T00:00:00Z"
        },
        {
          "time": 1758412800,
          "open": 0.90898,
          "high": 0.909,
          "low": 0.90793,
          "close": 0.90827,
          "tick_volume": 406.0,
          "spread": 100.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-09-21T00:00:00Z"
        },
        {
          "time": 1758499200,
          "open": 0.90839,
          "high": 0.91259,
          "low": 0.90763,
          "close": 0.91186,
          "tick_volume": 24717.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-09-22T00:00:00Z"
        },
        {
          "time": 1758585600,
          "open": 0.91217,
          "high": 0.9141,
          "low": 0.91021,
          "close": 0.91275,
          "tick_volume": 24922.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-09-23T00:00:00Z"
        },
        {
          "time": 1758672000,
          "open": 0.91288,
          "high": 0.91771,
          "low": 0.91243,
          "close": 0.91451,
          "tick_volume": 25618.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-09-24T00:00:00Z"
        },
        {
          "time": 1758758400,
          "open": 0.91482,
          "high": 0.91732,
          "low": 0.90985,
          "close": 0.91146,
          "tick_volume": 28533.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-09-25T00:00:00Z"
        },
        {
          "time": 1758844800,
          "open": 0.91154,
          "high": 0.91321,
          "low": 0.90999,
          "close": 0.9129,
          "tick_volume": 31112.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-09-26T00:00:00Z"
        },
        {
          "time": 1759017600,
          "open": 0.91273,
          "high": 0.91314,
          "low": 0.91226,
          "close": 0.91248,
          "tick_volume": 324.0,
          "spread": 90.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-09-28T00:00:00Z"
        },
        {
          "time": 1759104000,
          "open": 0.91288,
          "high": 0.91592,
          "low": 0.91228,
          "close": 0.91524,
          "tick_volume": 24023.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-09-29T00:00:00Z"
        },
        {
          "time": 1759190400,
          "open": 0.91531,
          "high": 0.9222,
          "low": 0.91486,
          "close": 0.92029,
          "tick_volume": 29082.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-09-30T00:00:00Z"
        },
        {
          "time": 1759276800,
          "open": 0.9207,
          "high": 0.9227,
          "low": 0.91788,
          "close": 0.92153,
          "tick_volume": 30775.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-10-01T00:00:00Z"
        },
        {
          "time": 1759363200,
          "open": 0.92154,
          "high": 0.9231,
          "low": 0.91947,
          "close": 0.92077,
          "tick_volume": 26393.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-10-02T00:00:00Z"
        },
        {
          "time": 1759449600,
          "open": 0.92112,
          "high": 0.92265,
          "low": 0.9202,
          "close": 0.92077,
          "tick_volume": 23531.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-10-03T00:00:00Z"
        },
        {
          "time": 1759622400,
          "open": 0.91897,
          "high": 0.9206,
          "low": 0.91895,
          "close": 0.92054,
          "tick_volume": 505.0,
          "spread": 100.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-10-05T00:00:00Z"
        },
        {
          "time": 1759708800,
          "open": 0.92042,
          "high": 0.92423,
          "low": 0.9196,
          "close": 0.92203,
          "tick_volume": 29558.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-10-06T00:00:00Z"
        },
        {
          "time": 1759795200,
          "open": 0.92245,
          "high": 0.92385,
          "low": 0.9178,
          "close": 0.91793,
          "tick_volume": 29603.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-10-07T00:00:00Z"
        },
        {
          "time": 1759881600,
          "open": 0.91808,
          "high": 0.9195,
          "low": 0.91526,
          "close": 0.91857,
          "tick_volume": 25984.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-10-08T00:00:00Z"
        },
        {
          "time": 1759968000,
          "open": 0.91876,
          "high": 0.92166,
          "low": 0.91701,
          "close": 0.91878,
          "tick_volume": 36288.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-10-09T00:00:00Z"
        },
        {
          "time": 1760054400,
          "open": 0.91903,
          "high": 0.92123,
          "low": 0.90604,
          "close": 0.9065,
          "tick_volume": 32937.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-10-10T00:00:00Z"
        },
        {
          "time": 1760227200,
          "open": 0.91029,
          "high": 0.91097,
          "low": 0.90903,
          "close": 0.90913,
          "tick_volume": 1088.0,
          "spread": 87.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-10-12T00:00:00Z"
        },
        {
          "time": 1760313600,
          "open": 0.91017,
          "high": 0.91544,
          "low": 0.90861,
          "close": 0.91458,
          "tick_volume": 28711.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-10-13T00:00:00Z"
        },
        {
          "time": 1760400000,
          "open": 0.91442,
          "high": 0.91525,
          "low": 0.90627,
          "close": 0.91073,
          "tick_volume": 41379.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-10-14T00:00:00Z"
        },
        {
          "time": 1760486400,
          "open": 0.91093,
          "high": 0.91574,
          "low": 0.91087,
          "close": 0.9142,
          "tick_volume": 40288.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-10-15T00:00:00Z"
        },
        {
          "time": 1760572800,
          "open": 0.91437,
          "high": 0.91481,
          "low": 0.90933,
          "close": 0.9114,
          "tick_volume": 55369.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-10-16T00:00:00Z"
        },
        {
          "time": 1760659200,
          "open": 0.91136,
          "high": 0.91211,
          "low": 0.90601,
          "close": 0.91078,
          "tick_volume": 59181.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-10-17T00:00:00Z"
        },
        {
          "time": 1760832000,
          "open": 0.91019,
          "high": 0.91141,
          "low": 0.91006,
          "close": 0.91141,
          "tick_volume": 275.0,
          "spread": 94.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-10-19T00:00:00Z"
        },
        {
          "time": 1760918400,
          "open": 0.91143,
          "high": 0.91484,
          "low": 0.91034,
          "close": 0.91442,
          "tick_volume": 38259.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-10-20T00:00:00Z"
        },
        {
          "time": 1761004800,
          "open": 0.91437,
          "high": 0.91547,
          "low": 0.90857,
          "close": 0.91009,
          "tick_volume": 44814.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-10-21T00:00:00Z"
        },
        {
          "time": 1761091200,
          "open": 0.90997,
          "high": 0.91138,
          "low": 0.90654,
          "close": 0.90814,
          "tick_volume": 49930.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-10-22T00:00:00Z"
        },
        {
          "time": 1761177600,
          "open": 0.90805,
          "high": 0.91195,
          "low": 0.90693,
          "close": 0.91085,
          "tick_volume": 49008.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-10-23T00:00:00Z"
        },
        {
          "time": 1761264000,
          "open": 0.91102,
          "high": 0.91442,
          "low": 0.91016,
          "close": 0.91143,
          "tick_volume": 38857.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-10-24T00:00:00Z"
        },
        {
          "time": 1761436800,
          "open": 0.91598,
          "high": 0.91616,
          "low": 0.91416,
          "close": 0.91419,
          "tick_volume": 2407.0,
          "spread": 7.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-10-26T00:00:00Z"
        },
        {
          "time": 1761523200,
          "open": 0.91432,
          "high": 0.91785,
          "low": 0.91309,
          "close": 0.91726,
          "tick_volume": 41534.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-10-27T00:00:00Z"
        },
        {
          "time": 1761609600,
          "open": 0.91728,
          "high": 0.91889,
          "low": 0.91626,
          "close": 0.91795,
          "tick_volume": 43943.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-10-28T00:00:00Z"
        },
        {
          "time": 1761696000,
          "open": 0.91788,
          "high": 0.92156,
          "low": 0.91485,
          "close": 0.91584,
          "tick_volume": 67630.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-10-29T00:00:00Z"
        },
        {
          "time": 1761782400,
          "open": 0.91601,
          "high": 0.91893,
          "low": 0.91457,
          "close": 0.91631,
          "tick_volume": 70346.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-10-30T00:00:00Z"
        },
        {
          "time": 1761868800,
          "open": 0.91631,
          "high": 0.9182,
          "low": 0.91495,
          "close": 0.91698,
          "tick_volume": 48090.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-10-31T00:00:00Z"
        },
        {
          "time": 1762041600,
          "open": 0.91751,
          "high": 0.91751,
          "low": 0.91629,
          "close": 0.91637,
          "tick_volume": 828.0,
          "spread": 31.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-11-02T00:00:00Z"
        },
        {
          "time": 1762128000,
          "open": 0.91694,
          "high": 0.91988,
          "low": 0.91669,
          "close": 0.91884,
          "tick_volume": 38833.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-11-03T00:00:00Z"
        },
        {
          "time": 1762214400,
          "open": 0.91898,
          "high": 0.91947,
          "low": 0.91347,
          "close": 0.91549,
          "tick_volume": 52280.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-11-04T00:00:00Z"
        },
        {
          "time": 1762300800,
          "open": 0.9155,
          "high": 0.91906,
          "low": 0.91185,
          "close": 0.91762,
          "tick_volume": 47229.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-11-05T00:00:00Z"
        },
        {
          "time": 1762387200,
          "open": 0.91768,
          "high": 0.91897,
          "low": 0.91321,
          "close": 0.91492,
          "tick_volume": 66709.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-11-06T00:00:00Z"
        },
        {
          "time": 1762473600,
          "open": 0.91474,
          "high": 0.9161,
          "low": 0.91047,
          "close": 0.91207,
          "tick_volume": 65713.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-11-07T00:00:00Z"
        },
        {
          "time": 1762646400,
          "open": 0.91295,
          "high": 0.91306,
          "low": 0.91149,
          "close": 0.91179,
          "tick_volume": 379.0,
          "spread": 65.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-11-09T00:00:00Z"
        },
        {
          "time": 1762732800,
          "open": 0.91195,
          "high": 0.91679,
          "low": 0.91177,
          "close": 0.91622,
          "tick_volume": 53496.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-11-10T00:00:00Z"
        },
        {
          "time": 1762819200,
          "open": 0.91641,
          "high": 0.91662,
          "low": 0.9136,
          "close": 0.91493,
          "tick_volume": 39840.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-11-11T00:00:00Z"
        },
        {
          "time": 1762905600,
          "open": 0.91491,
          "high": 0.91671,
          "low": 0.91344,
          "close": 0.91587,
          "tick_volume": 52479.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-11-12T00:00:00Z"
        },
        {
          "time": 1762992000,
          "open": 0.91589,
          "high": 0.92054,
          "low": 0.91445,
          "close": 0.91691,
          "tick_volume": 60797.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-11-13T00:00:00Z"
        },
        {
          "time": 1763078400,
          "open": 0.91668,
          "high": 0.91848,
          "low": 0.91339,
          "close": 0.91646,
          "tick_volume": 58584.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-11-14T00:00:00Z"
        },
        {
          "time": 1763251200,
          "open": 0.91615,
          "high": 0.91672,
          "low": 0.91587,
          "close": 0.91665,
          "tick_volume": 211.0,
          "spread": 122.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-11-16T00:00:00Z"
        },
        {
          "time": 1763337600,
          "open": 0.91613,
          "high": 0.91644,
          "low": 0.91109,
          "close": 0.91291,
          "tick_volume": 57914.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-11-17T00:00:00Z"
        },
        {
          "time": 1763424000,
          "open": 0.91289,
          "high": 0.91316,
          "low": 0.90878,
          "close": 0.91039,
          "tick_volume": 62996.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-11-18T00:00:00Z"
        },
        {
          "time": 1763510400,
          "open": 0.91054,
          "high": 0.91066,
          "low": 0.9067,
          "close": 0.90985,
          "tick_volume": 61488.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-11-19T00:00:00Z"
        },
        {
          "time": 1763596800,
          "open": 0.91006,
          "high": 0.9132,
          "low": 0.90762,
          "close": 0.90899,
          "tick_volume": 66904.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-11-20T00:00:00Z"
        },
        {
          "time": 1763683200,
          "open": 0.90869,
          "high": 0.91084,
          "low": 0.90565,
          "close": 0.9106,
          "tick_volume": 65271.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-11-21T00:00:00Z"
        },
        {
          "time": 1763856000,
          "open": 0.9111,
          "high": 0.91151,
          "low": 0.91029,
          "close": 0.9106,
          "tick_volume": 782.0,
          "spread": 77.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-11-23T00:00:00Z"
        },
        {
          "time": 1763942400,
          "open": 0.91156,
          "high": 0.91234,
          "low": 0.90916,
          "close": 0.91213,
          "tick_volume": 59572.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-11-24T00:00:00Z"
        },
        {
          "time": 1764028800,
          "open": 0.91211,
          "high": 0.91269,
          "low": 0.90849,
          "close": 0.91232,
          "tick_volume": 53460.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-11-25T00:00:00Z"
        },
        {
          "time": 1764115200,
          "open": 0.9123,
          "high": 0.91625,
          "low": 0.91208,
          "close": 0.91481,
          "tick_volume": 51513.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-11-26T00:00:00Z"
        },
        {
          "time": 1764201600,
          "open": 0.91533,
          "high": 0.91733,
          "low": 0.91511,
          "close": 0.91667,
          "tick_volume": 40496.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-11-27T00:00:00Z"
        },
        {
          "time": 1764288000,
          "open": 0.91671,
          "high": 0.91761,
          "low": 0.91321,
          "close": 0.91576,
          "tick_volume": 173707.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-11-28T00:00:00Z"
        },
        {
          "time": 1764460800,
          "open": 0.91426,
          "high": 0.91503,
          "low": 0.91373,
          "close": 0.91429,
          "tick_volume": 593.0,
          "spread": 57.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-11-30T00:00:00Z"
        },
        {
          "time": 1764547200,
          "open": 0.91467,
          "high": 0.91667,
          "low": 0.91396,
          "close": 0.9156,
          "tick_volume": 70933.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-12-01T00:00:00Z"
        },
        {
          "time": 1764633600,
          "open": 0.91577,
          "high": 0.91901,
          "low": 0.91554,
          "close": 0.91733,
          "tick_volume": 52366.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-12-02T00:00:00Z"
        },
        {
          "time": 1764720000,
          "open": 0.91741,
          "high": 0.92114,
          "low": 0.91559,
          "close": 0.92066,
          "tick_volume": 55325.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-12-03T00:00:00Z"
        },
        {
          "time": 1764806400,
          "open": 0.9207,
          "high": 0.92391,
          "low": 0.92049,
          "close": 0.92191,
          "tick_volume": 92856.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-12-04T00:00:00Z"
        },
        {
          "time": 1764892800,
          "open": 0.92246,
          "high": 0.92575,
          "low": 0.91739,
          "close": 0.91746,
          "tick_volume": 55098.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-12-05T00:00:00Z"
        },
        {
          "time": 1765065600,
          "open": 0.91785,
          "high": 0.91816,
          "low": 0.9169,
          "close": 0.91699,
          "tick_volume": 722.0,
          "spread": 81.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-12-07T00:00:00Z"
        },
        {
          "time": 1765152000,
          "open": 0.91746,
          "high": 0.91877,
          "low": 0.91497,
          "close": 0.91745,
          "tick_volume": 62262.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-12-08T00:00:00Z"
        },
        {
          "time": 1765238400,
          "open": 0.91767,
          "high": 0.92049,
          "low": 0.9154,
          "close": 0.91978,
          "tick_volume": 60277.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-12-09T00:00:00Z"
        },
        {
          "time": 1765324800,
          "open": 0.91962,
          "high": 0.92195,
          "low": 0.91805,
          "close": 0.92005,
          "tick_volume": 79930.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-12-10T00:00:00Z"
        },
        {
          "time": 1765411200,
          "open": 0.92029,
          "high": 0.92061,
          "low": 0.91561,
          "close": 0.9178,
          "tick_volume": 88416.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-12-11T00:00:00Z"
        },
        {
          "time": 1765497600,
          "open": 0.91785,
          "high": 0.91893,
          "low": 0.91482,
          "close": 0.91599,
          "tick_volume": 58638.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-12-12T00:00:00Z"
        },
        {
          "time": 1765670400,
          "open": 0.91579,
          "high": 0.91579,
          "low": 0.91379,
          "close": 0.91469,
          "tick_volume": 1202.0,
          "spread": 162.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-12-14T00:00:00Z"
        },
        {
          "time": 1765756800,
          "open": 0.91544,
          "high": 0.91618,
          "low": 0.91375,
          "close": 0.91429,
          "tick_volume": 58673.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-12-15T00:00:00Z"
        },
        {
          "time": 1765843200,
          "open": 0.91432,
          "high": 0.91534,
          "low": 0.91109,
          "close": 0.91238,
          "tick_volume": 56506.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-12-16T00:00:00Z"
        },
        {
          "time": 1765929600,
          "open": 0.91244,
          "high": 0.91314,
          "low": 0.91002,
          "close": 0.91061,
          "tick_volume": 60095.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-12-17T00:00:00Z"
        },
        {
          "time": 1766016000,
          "open": 0.91044,
          "high": 0.91296,
          "low": 0.90879,
          "close": 0.91103,
          "tick_volume": 106879.0,
          "spread": 3.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-12-18T00:00:00Z"
        },
        {
          "time": 1766102400,
          "open": 0.91102,
          "high": 0.91274,
          "low": 0.91031,
          "close": 0.91231,
          "tick_volume": 47021.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-12-19T00:00:00Z"
        },
        {
          "time": 1766275200,
          "open": 0.91269,
          "high": 0.91312,
          "low": 0.91126,
          "close": 0.91155,
          "tick_volume": 445.0,
          "spread": 92.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-12-21T00:00:00Z"
        },
        {
          "time": 1766361600,
          "open": 0.91211,
          "high": 0.91557,
          "low": 0.91149,
          "close": 0.91557,
          "tick_volume": 44354.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-12-22T00:00:00Z"
        },
        {
          "time": 1766448000,
          "open": 0.91567,
          "high": 0.91788,
          "low": 0.91462,
          "close": 0.91722,
          "tick_volume": 71979.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-12-23T00:00:00Z"
        },
        {
          "time": 1766534400,
          "open": 0.91731,
          "high": 0.91872,
          "low": 0.91629,
          "close": 0.91692,
          "tick_volume": 32831.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-12-24T00:00:00Z"
        },
        {
          "time": 1766620800,
          "open": 0.91636,
          "high": 0.91767,
          "low": 0.91636,
          "close": 0.91659,
          "tick_volume": 967.0,
          "spread": 95.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-12-25T00:00:00Z"
        },
        {
          "time": 1766707200,
          "open": 0.91657,
          "high": 0.91845,
          "low": 0.91608,
          "close": 0.91807,
          "tick_volume": 38733.0,
          "spread": 4.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-12-26T00:00:00Z"
        },
        {
          "time": 1766880000,
          "open": 0.91602,
          "high": 0.91754,
          "low": 0.91592,
          "close": 0.91751,
          "tick_volume": 282.0,
          "spread": 129.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-12-28T00:00:00Z"
        },
        {
          "time": 1766966400,
          "open": 0.91755,
          "high": 0.91944,
          "low": 0.91479,
          "close": 0.91621,
          "tick_volume": 52650.0,
          "spread": 3.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-12-29T00:00:00Z"
        },
        {
          "time": 1767052800,
          "open": 0.91638,
          "high": 0.91911,
          "low": 0.91606,
          "close": 0.91684,
          "tick_volume": 31628.0,
          "spread": 6.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-12-30T00:00:00Z"
        },
        {
          "time": 1767139200,
          "open": 0.91689,
          "high": 0.91751,
          "low": 0.91345,
          "close": 0.91579,
          "tick_volume": 31330.0,
          "spread": 12.0,
          "real_volume": 0.0,
          "time_iso_utc": "2025-12-31T00:00:00Z"
        },
        {
          "time": 1767225600,
          "open": 0.91525,
          "high": 0.91611,
          "low": 0.91488,
          "close": 0.91498,
          "tick_volume": 176.0,
          "spread": 134.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-01T00:00:00Z"
        },
        {
          "time": 1767312000,
          "open": 0.91531,
          "high": 0.92005,
          "low": 0.91529,
          "close": 0.9192,
          "tick_volume": 32445.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-02T00:00:00Z"
        },
        {
          "time": 1767484800,
          "open": 0.91864,
          "high": 0.91996,
          "low": 0.91765,
          "close": 0.91867,
          "tick_volume": 872.0,
          "spread": 89.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-04T00:00:00Z"
        },
        {
          "time": 1767571200,
          "open": 0.91875,
          "high": 0.92483,
          "low": 0.91759,
          "close": 0.92475,
          "tick_volume": 43018.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-05T00:00:00Z"
        },
        {
          "time": 1767657600,
          "open": 0.92448,
          "high": 0.931,
          "low": 0.92325,
          "close": 0.93093,
          "tick_volume": 44244.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-06T00:00:00Z"
        },
        {
          "time": 1767744000,
          "open": 0.93105,
          "high": 0.93455,
          "low": 0.92851,
          "close": 0.9315,
          "tick_volume": 49426.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-07T00:00:00Z"
        },
        {
          "time": 1767830400,
          "open": 0.93166,
          "high": 0.93231,
          "low": 0.92664,
          "close": 0.92939,
          "tick_volume": 66374.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-08T00:00:00Z"
        },
        {
          "time": 1767916800,
          "open": 0.92914,
          "high": 0.93085,
          "low": 0.92569,
          "close": 0.93031,
          "tick_volume": 46805.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-09T00:00:00Z"
        },
        {
          "time": 1768089600,
          "open": 0.92918,
          "high": 0.93058,
          "low": 0.92918,
          "close": 0.93045,
          "tick_volume": 253.0,
          "spread": 101.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-11T00:00:00Z"
        },
        {
          "time": 1768176000,
          "open": 0.93048,
          "high": 0.93242,
          "low": 0.92976,
          "close": 0.93122,
          "tick_volume": 35957.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-12T00:00:00Z"
        },
        {
          "time": 1768262400,
          "open": 0.93084,
          "high": 0.93226,
          "low": 0.92707,
          "close": 0.9288,
          "tick_volume": 51954.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-13T00:00:00Z"
        },
        {
          "time": 1768348800,
          "open": 0.92851,
          "high": 0.93037,
          "low": 0.9262,
          "close": 0.92734,
          "tick_volume": 54584.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-14T00:00:00Z"
        },
        {
          "time": 1768435200,
          "open": 0.92742,
          "high": 0.93211,
          "low": 0.92647,
          "close": 0.93085,
          "tick_volume": 64055.0,
          "spread": 3.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-15T00:00:00Z"
        },
        {
          "time": 1768521600,
          "open": 0.93073,
          "high": 0.93204,
          "low": 0.92842,
          "close": 0.92999,
          "tick_volume": 37702.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-16T00:00:00Z"
        },
        {
          "time": 1768694400,
          "open": 0.92812,
          "high": 0.92882,
          "low": 0.928,
          "close": 0.92811,
          "tick_volume": 809.0,
          "spread": 81.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-18T00:00:00Z"
        },
        {
          "time": 1768780800,
          "open": 0.92835,
          "high": 0.93142,
          "low": 0.92817,
          "close": 0.93103,
          "tick_volume": 45838.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-19T00:00:00Z"
        },
        {
          "time": 1768867200,
          "open": 0.93125,
          "high": 0.93376,
          "low": 0.92987,
          "close": 0.93157,
          "tick_volume": 68702.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-20T00:00:00Z"
        },
        {
          "time": 1768953600,
          "open": 0.93175,
          "high": 0.93588,
          "low": 0.93106,
          "close": 0.93482,
          "tick_volume": 72625.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-21T00:00:00Z"
        },
        {
          "time": 1769040000,
          "open": 0.93491,
          "high": 0.94349,
          "low": 0.93465,
          "close": 0.94305,
          "tick_volume": 88111.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-22T00:00:00Z"
        },
        {
          "time": 1769126400,
          "open": 0.94299,
          "high": 0.9454,
          "low": 0.94248,
          "close": 0.94469,
          "tick_volume": 66078.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-23T00:00:00Z"
        },
        {
          "time": 1769299200,
          "open": 0.94837,
          "high": 0.94989,
          "low": 0.94704,
          "close": 0.94989,
          "tick_volume": 1235.0,
          "spread": 96.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-25T00:00:00Z"
        },
        {
          "time": 1769385600,
          "open": 0.94832,
          "high": 0.95101,
          "low": 0.94544,
          "close": 0.94775,
          "tick_volume": 63590.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-26T00:00:00Z"
        },
        {
          "time": 1769472000,
          "open": 0.94747,
          "high": 0.95248,
          "low": 0.9474,
          "close": 0.95123,
          "tick_volume": 69358.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-27T00:00:00Z"
        },
        {
          "time": 1769558400,
          "open": 0.95147,
          "high": 0.95499,
          "low": 0.94658,
          "close": 0.95435,
          "tick_volume": 85473.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-28T00:00:00Z"
        },
        {
          "time": 1769644800,
          "open": 0.95444,
          "high": 0.95908,
          "low": 0.94531,
          "close": 0.95082,
          "tick_volume": 104092.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-29T00:00:00Z"
        },
        {
          "time": 1769731200,
          "open": 0.95079,
          "high": 0.95145,
          "low": 0.94436,
          "close": 0.94833,
          "tick_volume": 96110.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-01-30T00:00:00Z"
        },
        {
          "time": 1769904000,
          "open": 0.94656,
          "high": 0.94701,
          "low": 0.94463,
          "close": 0.94491,
          "tick_volume": 1495.0,
          "spread": 87.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-01T00:00:00Z"
        },
        {
          "time": 1769990400,
          "open": 0.94523,
          "high": 0.95247,
          "low": 0.94461,
          "close": 0.95078,
          "tick_volume": 92298.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-02T00:00:00Z"
        },
        {
          "time": 1770076800,
          "open": 0.95082,
          "high": 0.96254,
          "low": 0.9505,
          "close": 0.95707,
          "tick_volume": 80417.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-03T00:00:00Z"
        },
        {
          "time": 1770163200,
          "open": 0.95718,
          "high": 0.96015,
          "low": 0.95341,
          "close": 0.95623,
          "tick_volume": 68106.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-04T00:00:00Z"
        },
        {
          "time": 1770249600,
          "open": 0.95613,
          "high": 0.95724,
          "low": 0.94926,
          "close": 0.94985,
          "tick_volume": 88653.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-05T00:00:00Z"
        },
        {
          "time": 1770336000,
          "open": 0.94957,
          "high": 0.95951,
          "low": 0.94654,
          "close": 0.95902,
          "tick_volume": 65813.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-06T00:00:00Z"
        },
        {
          "time": 1770508800,
          "open": 0.95949,
          "high": 0.95959,
          "low": 0.95833,
          "close": 0.95887,
          "tick_volume": 581.0,
          "spread": 93.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-08T00:00:00Z"
        },
        {
          "time": 1770595200,
          "open": 0.95932,
          "high": 0.96277,
          "low": 0.95764,
          "close": 0.96152,
          "tick_volume": 50677.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-09T00:00:00Z"
        },
        {
          "time": 1770681600,
          "open": 0.96149,
          "high": 0.96173,
          "low": 0.95671,
          "close": 0.95786,
          "tick_volume": 53081.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-10T00:00:00Z"
        },
        {
          "time": 1770768000,
          "open": 0.95811,
          "high": 0.96827,
          "low": 0.95811,
          "close": 0.96729,
          "tick_volume": 72862.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-11T00:00:00Z"
        },
        {
          "time": 1770854400,
          "open": 0.96756,
          "high": 0.96987,
          "low": 0.96438,
          "close": 0.96452,
          "tick_volume": 74208.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-12T00:00:00Z"
        },
        {
          "time": 1770940800,
          "open": 0.96463,
          "high": 0.96613,
          "low": 0.9599,
          "close": 0.9633,
          "tick_volume": 64297.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-13T00:00:00Z"
        },
        {
          "time": 1771113600,
          "open": 0.96161,
          "high": 0.96235,
          "low": 0.96112,
          "close": 0.96213,
          "tick_volume": 1151.0,
          "spread": 149.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-15T00:00:00Z"
        },
        {
          "time": 1771200000,
          "open": 0.96254,
          "high": 0.96576,
          "low": 0.96226,
          "close": 0.96427,
          "tick_volume": 25568.0,
          "spread": 3.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-16T00:00:00Z"
        },
        {
          "time": 1771286400,
          "open": 0.96429,
          "high": 0.96686,
          "low": 0.96157,
          "close": 0.96623,
          "tick_volume": 57668.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-17T00:00:00Z"
        },
        {
          "time": 1771372800,
          "open": 0.9662,
          "high": 0.96706,
          "low": 0.9636,
          "close": 0.96471,
          "tick_volume": 38382.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-18T00:00:00Z"
        },
        {
          "time": 1771459200,
          "open": 0.96468,
          "high": 0.96845,
          "low": 0.96324,
          "close": 0.96572,
          "tick_volume": 48355.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-19T00:00:00Z"
        },
        {
          "time": 1771545600,
          "open": 0.96559,
          "high": 0.96988,
          "low": 0.96124,
          "close": 0.96901,
          "tick_volume": 80992.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-20T00:00:00Z"
        },
        {
          "time": 1771718400,
          "open": 0.96811,
          "high": 0.96931,
          "low": 0.96787,
          "close": 0.96859,
          "tick_volume": 509.0,
          "spread": 36.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-22T00:00:00Z"
        },
        {
          "time": 1771804800,
          "open": 0.96883,
          "high": 0.97073,
          "low": 0.96531,
          "close": 0.96618,
          "tick_volume": 52001.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-23T00:00:00Z"
        },
        {
          "time": 1771891200,
          "open": 0.96632,
          "high": 0.96907,
          "low": 0.96426,
          "close": 0.96732,
          "tick_volume": 50772.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-24T00:00:00Z"
        },
        {
          "time": 1771977600,
          "open": 0.96721,
          "high": 0.97472,
          "low": 0.96701,
          "close": 0.97387,
          "tick_volume": 53165.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-25T00:00:00Z"
        },
        {
          "time": 1772064000,
          "open": 0.97384,
          "high": 0.97507,
          "low": 0.96892,
          "close": 0.97142,
          "tick_volume": 62743.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-26T00:00:00Z"
        },
        {
          "time": 1772150400,
          "open": 0.97141,
          "high": 0.9745,
          "low": 0.96938,
          "close": 0.97079,
          "tick_volume": 60384.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-02-27T00:00:00Z"
        },
        {
          "time": 1772323200,
          "open": 0.96052,
          "high": 0.96425,
          "low": 0.96052,
          "close": 0.96233,
          "tick_volume": 1196.0,
          "spread": 114.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-01T00:00:00Z"
        },
        {
          "time": 1772409600,
          "open": 0.96395,
          "high": 0.97248,
          "low": 0.96322,
          "close": 0.97111,
          "tick_volume": 94986.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-02T00:00:00Z"
        },
        {
          "time": 1772496000,
          "open": 0.97113,
          "high": 0.97308,
          "low": 0.95455,
          "close": 0.96252,
          "tick_volume": 122100.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-03T00:00:00Z"
        },
        {
          "time": 1772582400,
          "open": 0.96292,
          "high": 0.96691,
          "low": 0.95647,
          "close": 0.96533,
          "tick_volume": 108229.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-04T00:00:00Z"
        },
        {
          "time": 1772668800,
          "open": 0.96523,
          "high": 0.96624,
          "low": 0.95539,
          "close": 0.9583,
          "tick_volume": 152206.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-05T00:00:00Z"
        },
        {
          "time": 1772755200,
          "open": 0.95823,
          "high": 0.96209,
          "low": 0.95285,
          "close": 0.95358,
          "tick_volume": 123781.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-06T00:00:00Z"
        },
        {
          "time": 1772928000,
          "open": 0.94995,
          "high": 0.95006,
          "low": 0.94687,
          "close": 0.94866,
          "tick_volume": 7156.0,
          "spread": 8.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-08T00:00:00Z"
        },
        {
          "time": 1773014400,
          "open": 0.94896,
          "high": 0.96186,
          "low": 0.94628,
          "close": 0.96051,
          "tick_volume": 126153.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-09T00:00:00Z"
        },
        {
          "time": 1773100800,
          "open": 0.96058,
          "high": 0.97277,
          "low": 0.95913,
          "close": 0.96649,
          "tick_volume": 103369.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-10T00:00:00Z"
        },
        {
          "time": 1773187200,
          "open": 0.96651,
          "high": 0.97602,
          "low": 0.96651,
          "close": 0.97024,
          "tick_volume": 79183.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-11T00:00:00Z"
        },
        {
          "time": 1773273600,
          "open": 0.97026,
          "high": 0.97225,
          "low": 0.9637,
          "close": 0.96529,
          "tick_volume": 79524.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-12T00:00:00Z"
        },
        {
          "time": 1773360000,
          "open": 0.96521,
          "high": 0.96705,
          "low": 0.95785,
          "close": 0.9579,
          "tick_volume": 71886.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-13T00:00:00Z"
        },
        {
          "time": 1773532800,
          "open": 0.96027,
          "high": 0.9605,
          "low": 0.95838,
          "close": 0.95933,
          "tick_volume": 2364.0,
          "spread": 9.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-15T00:00:00Z"
        },
        {
          "time": 1773619200,
          "open": 0.95961,
          "high": 0.96847,
          "low": 0.959,
          "close": 0.96703,
          "tick_volume": 56417.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-16T00:00:00Z"
        },
        {
          "time": 1773705600,
          "open": 0.96699,
          "high": 0.97491,
          "low": 0.96481,
          "close": 0.97321,
          "tick_volume": 55208.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-17T00:00:00Z"
        },
        {
          "time": 1773792000,
          "open": 0.9733,
          "high": 0.97617,
          "low": 0.96398,
          "close": 0.96467,
          "tick_volume": 67251.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-18T00:00:00Z"
        },
        {
          "time": 1773878400,
          "open": 0.96444,
          "high": 0.97464,
          "low": 0.96095,
          "close": 0.97292,
          "tick_volume": 119376.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-19T00:00:00Z"
        },
        {
          "time": 1773964800,
          "open": 0.9731,
          "high": 0.97421,
          "low": 0.96091,
          "close": 0.96366,
          "tick_volume": 74817.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-20T00:00:00Z"
        },
        {
          "time": 1774137600,
          "open": 0.96089,
          "high": 0.96245,
          "low": 0.96086,
          "close": 0.96177,
          "tick_volume": 2060.0,
          "spread": 8.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-22T00:00:00Z"
        },
        {
          "time": 1774224000,
          "open": 0.96175,
          "high": 0.9669,
          "low": 0.95041,
          "close": 0.96311,
          "tick_volume": 216112.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-23T00:00:00Z"
        },
        {
          "time": 1774310400,
          "open": 0.963,
          "high": 0.96382,
          "low": 0.95491,
          "close": 0.96318,
          "tick_volume": 115826.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-24T00:00:00Z"
        },
        {
          "time": 1774396800,
          "open": 0.96316,
          "high": 0.96327,
          "low": 0.95733,
          "close": 0.95941,
          "tick_volume": 75539.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-25T00:00:00Z"
        },
        {
          "time": 1774483200,
          "open": 0.95944,
          "high": 0.96125,
          "low": 0.95268,
          "close": 0.95481,
          "tick_volume": 82462.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-26T00:00:00Z"
        },
        {
          "time": 1774569600,
          "open": 0.95474,
          "high": 0.95733,
          "low": 0.95245,
          "close": 0.95476,
          "tick_volume": 62572.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-27T00:00:00Z"
        },
        {
          "time": 1774742400,
          "open": 0.95341,
          "high": 0.9537,
          "low": 0.95153,
          "close": 0.95344,
          "tick_volume": 766.0,
          "spread": 104.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-29T00:00:00Z"
        },
        {
          "time": 1774828800,
          "open": 0.95386,
          "high": 0.95591,
          "low": 0.95091,
          "close": 0.95421,
          "tick_volume": 74114.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-30T00:00:00Z"
        },
        {
          "time": 1774915200,
          "open": 0.95439,
          "high": 0.96126,
          "low": 0.95232,
          "close": 0.95968,
          "tick_volume": 95975.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-03-31T00:00:00Z"
        },
        {
          "time": 1775001600,
          "open": 0.9601,
          "high": 0.96668,
          "low": 0.95957,
          "close": 0.9615,
          "tick_volume": 106880.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-04-01T00:00:00Z"
        },
        {
          "time": 1775088000,
          "open": 0.96133,
          "high": 0.96275,
          "low": 0.95525,
          "close": 0.96086,
          "tick_volume": 95420.0,
          "spread": 2.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-04-02T00:00:00Z"
        },
        {
          "time": 1775174400,
          "open": 0.96151,
          "high": 0.96268,
          "low": 0.95972,
          "close": 0.96139,
          "tick_volume": 28638.0,
          "spread": 8.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-04-03T00:00:00Z"
        },
        {
          "time": 1775347200,
          "open": 0.95985,
          "high": 0.95986,
          "low": 0.95935,
          "close": 0.95982,
          "tick_volume": 128.0,
          "spread": 200.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-04-05T00:00:00Z"
        },
        {
          "time": 1775433600,
          "open": 0.96007,
          "high": 0.96551,
          "low": 0.95903,
          "close": 0.96222,
          "tick_volume": 40595.0,
          "spread": 3.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-04-06T00:00:00Z"
        },
        {
          "time": 1775520000,
          "open": 0.96238,
          "high": 0.96984,
          "low": 0.96084,
          "close": 0.96902,
          "tick_volume": 82967.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-04-07T00:00:00Z"
        },
        {
          "time": 1775606400,
          "open": 0.97045,
          "high": 0.98018,
          "low": 0.96827,
          "close": 0.97571,
          "tick_volume": 109410.0,
          "spread": 1.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-04-08T00:00:00Z"
        },
        {
          "time": 1775692800,
          "open": 0.97531,
          "high": 0.97579,
          "low": 0.97342,
          "close": 0.97522,
          "tick_volume": 15310.0,
          "spread": 5.0,
          "real_volume": 0.0,
          "time_iso_utc": "2026-04-09T00:00:00Z"
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
