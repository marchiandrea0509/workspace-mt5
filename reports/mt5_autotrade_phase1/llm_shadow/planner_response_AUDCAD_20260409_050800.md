## 1) Screener Read
- Winner: **LONG continuation** on AUDCAD (Best Score 74.89, Conviction 3, Winner Family 2).
- Dashboard read: strong trend/tactical continuation profile (tactical trend high, macro positive, ADX fit strong), but not a fresh breakout state.
- Main contributors: Long Continuation score, macro alignment (1D up), trend-state support, positive family edge.
- MT5 chart agreement: mostly yes. D1 trend remains bullish; H4 is bullish but currently in post-impulse consolidation/pullback above prior support.

## 2) Market State
- 1D trend: **bullish**
- 4H trend: **bullish**
- alignment: **aligned**
- volatility regime: **high** (recent impulse expansion vs prior range)
- setup type: **pullback / continuation**

## 3) Key Levels
- current price area: **0.9752**
- nearest tactical support levels: **0.9749-0.9734**, **0.9628**, **0.9590**
- nearest tactical resistance levels: **0.9766-0.9802**, **0.9835**
- higher-timeframe support if visible: **0.9600-0.9620**, then **0.9559**
- higher-timeframe resistance if visible: **0.9802-0.9810**, then **~0.9850**

## 4) Trade Quality
**GOOD MARKET + BAD ENTRY**

Trend and macro are still constructive, but price is extended after a sharp upside displacement and currently chopping under recent highs. Entering market now gives weak location versus the preferred pullback zone and raises stop-distance or whipsaw risk. A laddered dip plan into support is cleaner and keeps risk sizing practical under the 100 USD cap. Continuation remains valid, but entry quality is conditional.

## 5) Primary Trade Plan
- Bias: **LONG**
- Entry method: **ladder limits**
- Execution style: **DIP_LADDER**
- Entry zone or trigger: stage buys into **0.9628 / 0.9590** (deep pullback continuation)
- Stop loss / invalidation: **0.9580** shared SL (clean break below support shelf)
- TP: **0.9661** shared live TP (single package TP constraint)
- trailing stop logic: activate trailing after +0.8R; trail by **0.0019** (~19 pips), step 0.0005
- brief R:R comment: first leg has modest R:R, second leg improves package R:R materially; blended package acceptable for continuation recovery leg.

## 6) Orderability Decision
**PLACEABLE_CONDITIONAL_ONLY**

- Market order now: **NO**
- Ladder limit orders allowed now: **YES**
- Stop-entry orders allowed now: **YES**

Allowed logic now:
- Ladder limits at **0.96275** and **0.95903** with shared SL/TP/trailing.
- Optional breakout trigger above **0.98024** is structurally valid, but less efficient for this package under shared TP constraints.

## 7) Backup Plan
Backup (one only): **WAIT-for-breakout retest**
- If price closes H4 above 0.9802 and retests 0.9785-0.9800 holding, allow a stop-entry continuation package with same shared risk framework.

## 8) Risk Sizing
- Total risk budget: **100 USD** (hard cap)
- Proposed total lots: **0.48** split across 2 legs (0.24 + 0.24)
- Shared stop basis and per-leg stop distance used for sizing
- Estimated total risk: **~99.5 USD**
- Estimated total margin: **~1110 USD**
- Margin cap check (1500 USD): **pass**

## 9) Trade Plan Ticket
| order level | order type | entry price | notional size in $ | quantity / units estimate | lots | stop loss | effective loss at stop $ (sum across package) | TP with estimated profit $ and R:R | trailing stop logic | trigger | trailing distance |
|---|---|---:|---:|---:|---:|---:|---:|---|---|---|---:|
| L1 | BUY_LIMIT | 0.96275 | 16652 | 24000 | 0.24 | 0.95802 | 82.2 | TP 0.96606, ~57.4 USD, ~0.70R | shared trailing | resting | 0.00190 |
| L2 | BUY_LIMIT | 0.95903 | 16652 | 24000 | 0.24 | 0.95802 | 17.3 | TP 0.96606, ~121.8 USD, ~7.04R | shared trailing | resting | 0.00190 |

- effective risk budget used: **100% (~99.5 USD)**
- total planned risk: **~99.5 USD**
- total margin implication: **~1110 USD**
- margin too tight? **No (within cap, moderate headroom)**

## 10) Final Verdict
Final verdict:
- Bias: LONG
- Best setup: Dip-ladder continuation into 0.9628/0.9590 with shared risk controls
- Orderability: PLACEABLE_CONDITIONAL_ONLY
- Confidence: 72
- What would invalidate the idea: sustained H4 acceptance below 0.9580 or strong bearish structure break on D1
- What I should do now: place conditional ladder limits only; avoid market chase

```json
{
  "screener_read": {
    "winner_side": "LONG",
    "winner_family": "CONTINUATION",
    "dashboard_summary": "Strong continuation profile with positive macro/trend context and high ADX fit; not a fresh breakout state.",
    "main_scoring_drivers": [
      "best_score 74.89",
      "long_continuation 78.89",
      "conviction_state 3",
      "winner_macro 85",
      "winner_adx_fit 93"
    ],
    "mt5_agreement": "mostly_agrees"
  },
  "market_state": {
    "trend_1d": "bullish",
    "trend_4h": "bullish",
    "alignment": "aligned",
    "volatility_regime": "high",
    "setup_type": "pullback"
  },
  "key_levels": {
    "current_price_area": 0.97522,
    "tactical_support_near_to_far": [0.97491, 0.97342, 0.96275, 0.95903],
    "tactical_resistance_near_to_far": [0.97659, 0.98024, 0.9835],
    "htf_support": [0.96203, 0.96005, 0.95588],
    "htf_resistance": [0.98024, 0.985]
  },
  "trade_quality": {
    "classification": "GOOD MARKET + BAD ENTRY",
    "why": "Trend quality is good, but current location is extended and less attractive for market entry; conditional pullback execution offers better risk efficiency."
  },
  "primary_plan": {
    "bias": "LONG",
    "entry_method": "ladder_limits",
    "execution_style": "DIP_LADDER",
    "entry_zone_or_trigger": "buy limits at 0.96275 and 0.95903",
    "stop_loss_invalidation": 0.95802,
    "take_profit": 0.96606,
    "trailing_logic": "activate after +0.8R, trail by 0.00190 with 0.00050 step",
    "rr_comment": "Blended package acceptable; deeper leg materially improves expected R:R."
  },
  "orderability": {
    "classification": "PLACEABLE_CONDITIONAL_ONLY",
    "market_order_now": "NO",
    "ladder_limit_orders_allowed_now": "YES",
    "stop_entry_orders_allowed_now": "YES",
    "entry_or_trigger_logic": "resting buy limits at 0.96275 and 0.95903; optional breakout stop-entry above 0.98024"
  },
  "backup_plan": {
    "bias": "LONG",
    "condition": "H4 close above 0.98024 then successful retest",
    "entry_method": "stop_entry",
    "execution_style": "BREAKOUT"
  },
  "risk_sizing": {
    "risk_budget_usd": 100.0,
    "total_risk_usd": 99.48,
    "total_margin_usd_estimate": 1110.17,
    "sizing_basis": "stop_distance",
    "within_margin_cap": true
  },
  "trade_plan_ticket": {
    "legs": [
      {
        "level": "L1",
        "order_type": "BUY_LIMIT",
        "entry_price": 0.96275,
        "lots": 0.24,
        "units_estimate": 24000,
        "notional_usd_estimate": 16652
      },
      {
        "level": "L2",
        "order_type": "BUY_LIMIT",
        "entry_price": 0.95903,
        "lots": 0.24,
        "units_estimate": 24000,
        "notional_usd_estimate": 16652
      }
    ],
    "shared_stop_loss_price": 0.95802,
    "shared_take_profit_price": 0.96606,
    "trailing": {
      "enabled": true,
      "distance_mode": "price",
      "distance_value": 0.0019,
      "trigger_price": 0.9632,
      "step": 0.0005,
      "activation_rule": "after +0.8R"
    },
    "effective_risk_budget_used_usd": 99.48,
    "total_margin_usd_estimate": 1110.17
  },
  "final_verdict": {
    "bias": "LONG",
    "best_setup": "DIP_LADDER pullback continuation",
    "orderability": "PLACEABLE_CONDITIONAL_ONLY",
    "confidence": 72,
    "invalidates_if": "H4 acceptance below 0.95802 or bearish structure shift on D1",
    "action_now": "Place conditional ladder limits only; no market chase"
  },
  "validator_hints": {
    "shared_package_constraints_respected": true,
    "notes": "All legs share one live SL/TP and one trailing rule set; leg count within max_legs; risk and margin within caps."
  }
}
```