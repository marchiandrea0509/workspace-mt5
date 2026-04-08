## 1) Screener Read
EURGBP is a **LONG continuation** winner. The dashboard is cleanly bullish: Best Setup Code `2`, Best Score `74.01`, Conviction `3`, Trend Dir `1`, Macro Dir `1`, Verdict `2`, Winner Dir `1`, Winner Family Code `2`, and Winner Margin `41.56`.

The long winner is being driven by a strong continuation profile: Winner Base Score `78.01`, Tactical Trend Score `83.57`, Winner Tactical `72.12`, Winner Macro `93`, Winner Structure `70`, Winner ADX Fit `93`, and a positive Context Boost `1`. FVG State `1`, EMA Trend State `1`, and Signed Conviction `3` all support the same side.

MT5 chart data broadly agrees with the screener. D1 remains constructive and H4 still supports a bullish continuation bias, but current price is stretched above the main actionable pullback support area. So the market is good, but the immediate entry is not ideal.

## 2) Market State
- 1D trend: **bullish**
- 4H trend: **bullish to neutral-positive**
- alignment: **aligned**
- volatility regime: **normal**
- setup type: **continuation / pullback**

## 3) Key Levels
- current price area: `0.8700`
- nearest tactical support levels:
  - `0.86850`
  - `0.86145`
  - `0.86139`
  - `0.86108`
- nearest tactical resistance levels:
  - `0.87414`
  - `0.87444`
  - `0.87475`
- higher-timeframe support if visible:
  - `0.86118`
- higher-timeframe resistance if visible:
  - `0.87890`

Order them from nearest to farthest: supports `0.86850 -> 0.86145 -> 0.86139 -> 0.86108`, resistances `0.87414 -> 0.87444 -> 0.87475 -> 0.87890`.

## 4) Trade Quality
**GOOD MARKET + BAD ENTRY**

- Trend, macro and winner attribution all support the long side.
- The issue is location: current price is sitting between support and a nearby resistance shelf, so chasing here compresses reward.
- The better trade is to buy weakness into support, not force a market buy under resistance.
- The deterministic script levels are too deep relative to current live structure; a discretionary plan should use the nearer tactical support before the much deeper zone.

## 5) Primary Trade Plan
- Bias: **LONG**
- Entry method: **ladder limits**
- Execution style: **DIP_LADDER**
- Entry zone or trigger: staged buy limits at `0.86850` and `0.86145`
- Stop loss / invalidation: `0.86080`
- TP: `0.87470`
- trailing stop logic: keep the base executable package with **no live trailing**; if H4 later closes cleanly above `0.87480`, a manual follow-up can switch the open runner logic to ATR-style trailing instead of a fixed target
- brief R:R comment: blended package is materially better than a market chase and keeps the trade aligned with the bullish continuation read

## 6) Orderability Decision
**PLACEABLE_CONDITIONAL_ONLY**

- Market order now: **NO**
- Ladder limit orders allowed now: **YES**
- Stop-entry orders allowed now: **NO**

If YES, specify the exact entry zone or trigger logic:
- buy limit 1 at `0.86850`
- buy limit 2 at `0.86145`
- shared SL `0.86080`
- shared TP `0.87470`

## 7) Backup Plan
Only if valid.

Backup setup:
- If EURGBP prints a clean H4 close above `0.87475` and then holds above `0.87410` on retest, the backup becomes a **LONG BREAKOUT** continuation with stop-entry above `0.87490` and invalidation below `0.87320`.

## 8) Risk Sizing
Using the provided total trade risk budget of **100 USD**:
- executable package size: `0.24` lots total
- split: `0.12 + 0.12`
- estimated total planned risk: about **93.6 USD**
- estimated total margin implication: about **1458 USD**

This stays below the `1500 USD` margin cap while using the risk budget much more effectively than the current deterministic plan.

## 9) Trade Plan Ticket
| order level | order type | entry price | notional size in $ | quantity in asset units | lots | stop loss | effective loss at stop $ | TPs with estimated profit $ and R:R | trailing stop logic | trigger | trailing distance |
|---|---|---:|---:|---:|---:|---:|---:|---|---|---|---|
| 1 | buy limit | 0.86850 | 13989 | 12000 | 0.12 | 0.86080 | 77.4 | TP `0.87470` ~ `72.1 USD` / `0.93R` | disabled in base package | first tactical pullback support | n/a |
| 2 | buy limit | 0.86145 | 13875 | 12000 | 0.12 | 0.86080 | 16.2 | TP `0.87470` ~ `154.6 USD` / `9.54R` | disabled in base package | deeper structural support | n/a |

Also state:
- effective risk budget used: **93.6 USD**
- total planned risk: **93.6 USD**
- total margin implication if leverage is relevant: **1458 USD**
- short note if margin is too tight: margin is usable but tight enough that oversizing beyond `0.24` total lots is not advisable

## 10) Final Verdict
Final verdict:
- Bias: LONG
- Best setup: buy pullback into `0.86850 / 0.86145`
- Orderability: PLACEABLE_CONDITIONAL_ONLY
- Confidence: 72
- What would invalidate the idea: sustained acceptance below `0.86080` or repeated H4 rejection that hardens `0.8741-0.8748` as a ceiling
- What I should do now: do not buy market; place only the dip ladder if you want exposure

```json
{
  "screener_read": {
    "winner_side": "LONG",
    "winner_family": "CONTINUATION",
    "dashboard_summary": "Bullish continuation winner supported by strong trend, macro, ADX fit, and strong signed conviction.",
    "main_scoring_components": {
      "best_score": 74.00910899626291,
      "conviction_state": 3,
      "trend_dir": 1,
      "macro_dir_1d": 1,
      "tactical_trend_score": 83.56994050623462,
      "winner_margin": 41.55807333007019,
      "winner_base_score": 78.00910899626291,
      "winner_penalty": 4.0,
      "winner_tactical": 72.12160411404449,
      "winner_macro": 93.0,
      "winner_structure": 70.0,
      "winner_adx_fit": 93.0,
      "winner_lifecycle": 50.0,
      "winner_context_boost": 1.0,
      "winner_family_edge": 15.26014466245563
    },
    "chart_agreement": "mostly_agrees",
    "chart_agreement_note": "MT5 D1/H4 structure supports the bullish winner, but current location favors a pullback entry rather than a market chase."
  },
  "market_state": {
    "trend_1d": "bullish",
    "trend_4h": "bullish",
    "alignment": "aligned",
    "volatility_regime": "normal",
    "setup_type": "continuation",
    "location_comment": "Bullish structure intact, but price sits closer to resistance than to the best immediate pullback support."
  },
  "key_levels": {
    "current_price_area": 0.86999,
    "tactical_support_levels": [0.8685, 0.86145, 0.86139, 0.86108],
    "tactical_resistance_levels": [0.87414, 0.87444, 0.87475],
    "higher_timeframe_support_levels": [0.86118],
    "higher_timeframe_resistance_levels": [0.8789]
  },
  "trade_quality": {
    "classification": "GOOD MARKET + BAD ENTRY",
    "why": [
      "Trend and macro remain bullish.",
      "Winner attribution strongly favors long continuation.",
      "Immediate location is not ideal because resistance is nearby.",
      "A pullback ladder offers much better asymmetry than buying market here."
    ]
  },
  "primary_plan": {
    "symbol": "EURGBP",
    "bias": "LONG",
    "entry_method": "ladder_limits",
    "execution_style": "DIP_LADDER",
    "entry_zone": "0.86850 then 0.86145",
    "entry_zone_low": 0.86145,
    "entry_zone_high": 0.8685,
    "stop_loss_price": 0.8608,
    "take_profit_price": 0.8747,
    "rr_comment": "Blended package improves asymmetry materially versus a market chase.",
    "trailing_plan_note": "Base executable package keeps trailing disabled; reconsider trailing only after confirmed H4 breakout above 0.87480."
  },
  "orderability": {
    "classification": "PLACEABLE_CONDITIONAL_ONLY",
    "market_order_now": "NO",
    "ladder_limit_orders_allowed_now": "YES",
    "stop_entry_orders_allowed_now": "NO",
    "allowed_entry_logic": "Rest buy limits at 0.86850 and 0.86145 with shared SL 0.86080 and shared TP 0.87470.",
    "no_resting_order_yet": false
  },
  "backup_plan": {
    "valid": true,
    "bias": "LONG",
    "execution_style": "BREAKOUT",
    "trigger_logic": "Only if H4 closes above 0.87475 and retest holds above 0.87410; stop-entry above 0.87490.",
    "stop_loss_price": 0.8732,
    "note": "Secondary only; not preferred while price is still under the resistance shelf."
  },
  "risk_sizing": {
    "risk_budget_usd": 100.0,
    "effective_risk_budget_used_usd": 93.6,
    "total_risk_usd": 93.6,
    "total_margin_usd_estimate": 1458.0,
    "within_budget": true,
    "within_margin_cap": true,
    "sizing_note": "Uses the risk budget more effectively than the deterministic script while staying inside the margin cap."
  },
  "trade_plan_ticket": {
    "legs": [
      {
        "level": 1,
        "order_type": "BUY_LIMIT",
        "entry_price": 0.8685,
        "lots": 0.12,
        "units_estimate": 12000,
        "notional_usd_estimate": 13989.0,
        "estimated_loss_at_stop_usd": 77.4,
        "estimated_profit_at_tp_usd": 72.1,
        "estimated_rr": 0.93,
        "trigger": "resting order at first tactical pullback support"
      },
      {
        "level": 2,
        "order_type": "BUY_LIMIT",
        "entry_price": 0.86145,
        "lots": 0.12,
        "units_estimate": 12000,
        "notional_usd_estimate": 13875.0,
        "estimated_loss_at_stop_usd": 16.2,
        "estimated_profit_at_tp_usd": 154.6,
        "estimated_rr": 9.54,
        "trigger": "resting order at deeper structural support"
      }
    ],
    "shared_stop_loss_price": 0.8608,
    "shared_take_profit_price": 0.8747,
    "total_planned_risk_usd": 93.6,
    "total_margin_usd_estimate": 1458.0,
    "trailing": {
      "enabled": false,
      "trigger_price": null,
      "distance_mode": null,
      "distance_value": null,
      "step_price": null,
      "note": "Base executable package keeps trailing disabled."
    }
  },
  "final_verdict": {
    "symbol": "EURGBP",
    "bias": "LONG",
    "best_setup": "Pullback continuation buy ladder into 0.86850 / 0.86145",
    "orderability": "PLACEABLE_CONDITIONAL_ONLY",
    "confidence": 72,
    "what_would_invalidate_the_idea": "Acceptance below 0.86080 or repeated H4 failure that hardens 0.8741-0.8748 as a ceiling.",
    "what_i_should_do_now": "Do not buy market; only place the dip ladder if you want exposure."
  },
  "validator_hints": {
    "symbol": "EURGBP",
    "shared_package_constraints_respected": true,
    "uses_shared_live_sl_tp_trailing_rules": true,
    "planner_safe_for_manual_review": true,
    "notes": [
      "Two-leg package uses one shared SL and one shared TP.",
      "This plan intentionally uses a nearer tactical leg plus a deeper structural leg.",
      "Per-leg TP is not modeled here because current bridge constraints still require a shared live TP across the package."
    ]
  }
}
```