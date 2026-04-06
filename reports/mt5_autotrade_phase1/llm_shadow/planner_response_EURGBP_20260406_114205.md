## 1) Screener Read
EURGBP is a **LONG continuation** winner. The dashboard is clearly bullish: Best Setup Code `2`, Best Score `75.83`, Conviction `3`, Trend Dir `1`, Macro Dir `1D = 1`, Verdict `2`, Winner Dir `1`, Winner Family Code `2`, and Winner Margin `44.04`.

The winner is being carried mainly by a strong continuation stack: Winner Base Score `79.83`, Winner Tactical `72.06`, Winner Macro `93`, Winner Structure `70`, Winner ADX Fit `93`, plus a positive Context Boost `3`. Tactical Trend Score is also strong at `83.43`. FVG State `2` and EMA Trend State `1` support the bullish case.

MT5 chart data broadly agrees with the screener winner: D1 and H4 are both bullish and price is still holding above the main higher-timeframe support band. The only caution is location: current price is closer to nearby resistance than to the best pullback support, so the market is good but the immediate entry is not.

## 2) Market State
- 1D trend: **bullish**
- 4H trend: **bullish**
- alignment: **aligned**
- volatility regime: **normal**
- setup type: **continuation / pullback**

## 3) Key Levels
- current price area: `0.8720`
- nearest tactical support levels:
  - `0.87175`
  - `0.87028`
  - `0.86850`
  - `0.86145`
- nearest tactical resistance levels:
  - `0.87367`
  - `0.87427`
  - `0.87479`
- higher-timeframe support if visible:
  - `0.86118`
- higher-timeframe resistance if visible:
  - `0.87895`
  - `0.87970`

## 4) Trade Quality
**GOOD MARKET + BAD ENTRY**

- Trend, macro, and winner attribution all support the long side.
- Price is still in a valid bullish structure, but it is trading too close to the local resistance shelf around `0.8737` / `0.8743` / `0.8748`.
- Dashboard support distance is larger than resistance distance, which matches the chart read: upside remains, but reward is compressed if chased here.
- The better trade is to buy a pullback into support rather than force a market entry below resistance.

## 5) Primary Trade Plan
- Bias: **LONG**
- Entry method: **ladder limits**
- Execution style: **DIP_LADDER**
- Entry zone or trigger: buy pullback into `0.87030` then `0.86860`
- Stop loss / invalidation: `0.86695`
- TP: `0.87470`
- trailing stop logic: base executable package keeps trailing **disabled**; if there is a later H4 close above `0.87480`, a manual follow-up can convert to ATR trailing instead of fixed TP
- brief R:R comment: blended package R:R is about `2.1R`, with the deeper second leg carrying the better asymmetry

## 6) Orderability Decision
**PLACEABLE_CONDITIONAL_ONLY**

- Market order now: **NO**
- Ladder limit orders allowed now: **YES**
- Stop-entry orders allowed now: **NO**

Exact entry zone allowed now:
- buy limit 1: `0.87030`
- buy limit 2: `0.86860`

No market chase. No breakout stop-entry yet.

## 7) Backup Plan
If EURGBP prints a clean H4 close above `0.87430` and then holds above `0.87360` on the retest, the backup is a **LONG BREAKOUT** continuation using a stop-entry above `0.87485` with invalidation back under `0.87320`.

## 8) Risk Sizing
Using the fixed total trade risk budget of **100 USD** and keeping total margin under **1500 USD**:
- proposed executable size: `0.24` lots total
- split: `0.12 + 0.12`
- estimated total risk at shared stop: about **79.5 USD**
- estimated total margin: about **1385.4 USD**

This stays inside both the risk budget and the margin cap.

## 9) Trade Plan Ticket
| order level | order type | entry price | notional size in $ | quantity / units estimate | lots | stop loss | effective loss at stop $ | TP with estimated profit $ and R:R | trailing stop logic | trigger | trailing distance |
|---|---|---:|---:|---:|---:|---:|---:|---|---|---|---|
| 1 | buy limit | 0.87030 | 13854.06 | 12000 | 0.12 | 0.86695 | 53.2 | TP `0.87470` ~ `69.9 USD` / `1.31R` | disabled in base package | rest at support band | n/a |
| 2 | buy limit | 0.86860 | 13854.06 | 12000 | 0.12 | 0.86695 | 26.2 | TP `0.87470` ~ `96.9 USD` / `3.70R` | disabled in base package | deeper pullback fill | n/a |

Also state:
- effective risk budget used: **79.5 USD**
- total planned risk: **79.5 USD**
- total margin implication: **1385.4 USD**
- short note if margin is too tight: margin is usable but not loose; avoid oversizing beyond `0.24` total lots

## 10) Final Verdict
Final verdict:
- Bias: LONG
- Best setup: Pullback continuation into `0.87030 / 0.86860`
- Orderability: PLACEABLE_CONDITIONAL_ONLY
- Confidence: 74
- What would invalidate the idea: loss of bullish structure and acceptance below `0.86695`, or repeated H4 rejection that turns `0.8737-0.8748` into a durable ceiling
- What I should do now: place only the dip ladder if you want exposure; do not buy market here

```json
{
  "screener_read": {
    "winner_side": "LONG",
    "winner_family": "CONTINUATION",
    "dashboard_summary": "Strong bullish continuation winner driven by high tactical trend score, strong macro alignment, strong ADX fit, positive FVG/context, and very strong conviction.",
    "main_scoring_components": {
      "best_score": 75.82907699439424,
      "conviction_state": 3,
      "trend_dir": 1,
      "macro_dir_1d": 1,
      "tactical_trend_score": 83.4251462268375,
      "winner_margin": 44.04186812839956,
      "winner_base_score": 79.82907699439424,
      "winner_penalty": 4.0,
      "winner_tactical": 72.06131988334191,
      "winner_macro": 93.0,
      "winner_structure": 70.0,
      "winner_adx_fit": 93.0,
      "winner_lifecycle": 50.0,
      "winner_context_boost": 3.0,
      "winner_family_edge": 14.416285860388925
    },
    "chart_agreement": "mostly_agrees",
    "chart_agreement_note": "MT5 D1/H4 structure supports the bullish continuation winner, but current price location is too close to local resistance for a clean market entry."
  },
  "market_state": {
    "trend_1d": "bullish",
    "trend_4h": "bullish",
    "alignment": "aligned",
    "volatility_regime": "normal",
    "setup_type": "continuation",
    "location_comment": "Bullish trend intact, but current price is closer to nearby resistance than to the best pullback support."
  },
  "key_levels": {
    "current_price_area": 0.87201,
    "tactical_support_levels": [0.87175, 0.87028, 0.8685, 0.86145],
    "tactical_resistance_levels": [0.87367, 0.87427, 0.87479],
    "higher_timeframe_support_levels": [0.86118],
    "higher_timeframe_resistance_levels": [0.87895, 0.8797]
  },
  "trade_quality": {
    "classification": "GOOD MARKET + BAD ENTRY",
    "why": [
      "Bullish trend and macro alignment are strong.",
      "Winner attribution confirms continuation dominance.",
      "Current price is sitting too close to nearby resistance for a clean market chase.",
      "A pullback entry offers materially better asymmetry than an immediate entry."
    ]
  },
  "primary_plan": {
    "symbol": "EURGBP",
    "bias": "LONG",
    "entry_method": "ladder_limits",
    "execution_style": "DIP_LADDER",
    "entry_zone": "0.87030 then 0.86860",
    "entry_zone_low": 0.8686,
    "entry_zone_high": 0.8703,
    "stop_loss_price": 0.86695,
    "take_profit_price": 0.8747,
    "rr_comment": "Blended package is about 2.1R with better asymmetry on the deeper leg.",
    "trailing_plan_note": "Disabled in the base executable package; reconsider ATR trailing only after a clean H4 breakout above 0.87480."
  },
  "orderability": {
    "classification": "PLACEABLE_CONDITIONAL_ONLY",
    "market_order_now": "NO",
    "ladder_limit_orders_allowed_now": "YES",
    "stop_entry_orders_allowed_now": "NO",
    "allowed_entry_logic": "Rest buy limits at 0.87030 and 0.86860 with shared SL 0.86695 and shared TP 0.87470.",
    "no_resting_order_yet": false
  },
  "backup_plan": {
    "valid": true,
    "bias": "LONG",
    "execution_style": "BREAKOUT",
    "trigger_logic": "Only if H4 closes above 0.87430 and then retest holds above 0.87360; breakout stop-entry above 0.87485.",
    "stop_loss_price": 0.8732,
    "note": "This is secondary and not preferred while the market remains under the current resistance shelf."
  },
  "risk_sizing": {
    "risk_budget_usd": 100.0,
    "effective_risk_budget_used_usd": 79.5,
    "total_risk_usd": 79.5,
    "total_margin_usd_estimate": 1385.4,
    "within_budget": true,
    "within_margin_cap": true,
    "sizing_note": "Kept below the margin cap; did not use full risk budget because margin is the tighter practical constraint for this package."
  },
  "trade_plan_ticket": {
    "legs": [
      {
        "level": 1,
        "order_type": "BUY_LIMIT",
        "entry_price": 0.8703,
        "lots": 0.12,
        "units_estimate": 12000,
        "notional_usd_estimate": 13854.06,
        "estimated_loss_at_stop_usd": 53.2,
        "estimated_profit_at_tp_usd": 69.9,
        "estimated_rr": 1.31,
        "trigger": "resting order at first tactical support"
      },
      {
        "level": 2,
        "order_type": "BUY_LIMIT",
        "entry_price": 0.8686,
        "lots": 0.12,
        "units_estimate": 12000,
        "notional_usd_estimate": 13854.06,
        "estimated_loss_at_stop_usd": 26.2,
        "estimated_profit_at_tp_usd": 96.9,
        "estimated_rr": 3.7,
        "trigger": "resting order at deeper pullback support"
      }
    ],
    "shared_stop_loss_price": 0.86695,
    "shared_take_profit_price": 0.8747,
    "total_planned_risk_usd": 79.5,
    "total_margin_usd_estimate": 1385.4,
    "trailing": {
      "enabled": false,
      "trigger_price": null,
      "distance_mode": null,
      "distance_value": null,
      "step_price": null,
      "note": "Base executable package keeps trailing disabled; optional later manual conversion only after confirmed breakout."
    }
  },
  "final_verdict": {
    "symbol": "EURGBP",
    "bias": "LONG",
    "best_setup": "Pullback continuation buy ladder into 0.87030 / 0.86860",
    "orderability": "PLACEABLE_CONDITIONAL_ONLY",
    "confidence": 74,
    "what_would_invalidate_the_idea": "Acceptance below 0.86695 or repeated H4 failure that hardens 0.8737-0.8748 as a lasting ceiling.",
    "what_i_should_do_now": "Do not buy market here; only place the dip ladder if you want exposure."
  },
  "validator_hints": {
    "symbol": "EURGBP",
    "shared_package_constraints_respected": true,
    "uses_shared_live_sl_tp_trailing_rules": true,
    "planner_safe_for_manual_review": true,
    "notes": [
      "Two-leg package uses one shared SL and one shared TP.",
      "Trailing is intentionally disabled in the base executable package.",
      "Total planned risk and margin remain inside pack limits."
    ]
  }
}
```