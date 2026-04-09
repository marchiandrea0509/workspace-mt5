# MT5 Trade Journal — Google Sheets Spec

## Purpose
A durable trade journal for the MT5 pipeline that stores:
- trade-group level decisions
- per-leg execution truth
- full screener context at entry time
- LLM rationale and post-trade review
- dashboard metrics for performance monitoring

## Recommended tabs
1. Dashboard
2. Trade_Groups
3. Legs
4. Screener_Snapshot
5. LLM_Review
6. Daily_Equity (optional but recommended)

---

## 1) Dashboard
Human-facing summary page.

### KPI blocks
- Starting balance
- Current balance
- Realized PnL
- Unrealized PnL
- Total trade groups
- Total filled legs
- Win rate
- Profit factor
- Expectancy per trade
- Expectancy in R
- Average win
- Average loss
- Max drawdown
- Recovery factor
- Average planned risk
- Average realized R
- Average hold time
- Average margin used
- Rejection rate
- Cancel rate

### Breakdowns
- By symbol
- By setup family
- By direction
- By screener conviction bucket
- By LLM confidence bucket
- By orderability class

### Charts
- Equity curve
- Drawdown curve
- Cumulative R
- PnL by symbol
- PnL by setup family
- Planned risk vs realized PnL scatter

---

## 2) Trade_Groups
One row per trade idea / cycle.

### Required columns
- trade_group_id
- cycle_id
- opened_at_utc
- closed_at_utc
- status
- symbol
- watchlist
- timeframe
- screener_version
- report_generated_at_utc
- report_path
- candidate_rank
- winner_side
- winner_family
- setup_family_text
- orderability
- execution_style
- plan_source
- llm_confidence
- deterministic_orderability
- llm_orderability
- planned_total_risk_usd
- planned_total_margin_usd
- realized_pnl_usd
- realized_r_multiple
- max_favorable_excursion_usd
- max_adverse_excursion_usd
- filled_legs
- closed_legs
- cancelled_legs
- result_class
- review_status
- note

---

## 3) Legs
One row per actual MT5 order leg.

### Required columns
- trade_group_id
- leg_id
- leg_index
- mt5_order_id
- ticket_id
- symbol
- side
- order_type
- entry_price_planned
- entry_price_filled
- stop_loss_planned
- take_profit_planned
- trailing_enabled
- trailing_trigger
- trailing_mode
- trailing_distance
- trailing_step_price
- lots
- units_estimate
- notional_usd_estimate
- planned_risk_usd
- realized_pnl_usd
- realized_r
- status
- opened_at_utc
- closed_at_utc
- broker_retcode
- broker_message
- parent_group_id

---

## 4) Screener_Snapshot
One row per trade group, storing the exact screener state used for the entry decision.

### Required columns
- trade_group_id
- symbol
- watchlist
- indicator
- report_generated_at_utc
- 01 Signal Dir
- 02 Best Setup Code
- 03 Best Score
- 04 Final Long Score
- 05 Final Short Score
- 06 Long Continuation
- 07 Short Continuation
- 08 Long MeanRev
- 09 Short MeanRev
- 10 Conviction State
- 11 Trend Dir
- 12 Macro Dir 1D
- 13 Position State
- 14 Breakout Dir
- 15 Retest Dir
- 16 ADX
- 17 Rel Volume
- 18 Dist Fast EMA ATR
- 19 Sweep Dir
- 20 Displacement Dir
- 21 PD State
- 22 FVG State
- 23 Tactical Trend Score
- 24 Tactical Breakout Score
- 25 Tactical MeanRev Score
- 26 Fresh Struct Shift
- 27 Verdict State
- 28 Momentum State
- 29 Signed Conviction
- 30 Break Fresh State
- 31 Retest Stage
- 32 Short MR Struct
- 33 Dist To Resistance %
- 34 Zone Count
- 35 EMA Trend State
- 36 VWAP20
- 37 Dist To Support %
- 38 Lifecycle Long Score
- 39 R1 Above
- 40 R2 Above
- 41 S1 Below
- 42 S2 Below
- 43 Cnt Res Above
- 44 Cnt Sup Below
- 45 Cnt Res All
- 46 Cnt Sup All
- 47 Lifecycle Short Score
- 48 Winner Dir
- 49 Winner Family Code
- 50 Winner Margin
- 51 Winner Base Score
- 52 Winner Penalty
- 53 Winner Tactical
- 54 Winner Macro
- 55 Winner Structure
- 56 Winner ADX Fit
- 57 Winner Lifecycle
- 58 Winner Context Boost
- 59 Winner Family Edge

---

## 5) LLM_Review
One row per trade group review.

### Required columns
- trade_group_id
- review_date_utc
- llm_pre_trade_rationale
- why_trade_made_sense
- what_went_well
- what_went_wrong
- mistakes
- lesson_learned
- was_llm_better_than_script
- was_script_better_than_llm
- discrepancy_type
- should_script_be_updated
- update_priority
- confidence_in_lesson
- free_text_review

---

## 6) Daily_Equity
Optional but recommended.

### Required columns
- date
- starting_balance
- ending_balance
- realized_pnl_usd
- open_pnl_usd
- closed_trade_groups
- closed_legs
- win_rate_day
- cumulative_drawdown_usd
- cumulative_drawdown_pct

---

## Suggested formulas for Dashboard
- Win rate = winning_trade_groups / closed_trade_groups
- Profit factor = gross_profit / abs(gross_loss)
- Expectancy = (win_rate * avg_win) - ((1-win_rate) * avg_loss)
- Expectancy R = average(realized_r_multiple)
- Max drawdown = running peak equity - current equity (max)
- Recovery factor = net_profit / max_drawdown

---

## Population logic
- At trade selection / plan creation:
  - write Trade_Groups
  - write Screener_Snapshot
  - write initial LLM_Review rationale
- At leg execution updates:
  - write / update Legs
- At trade close:
  - update Trade_Groups realized metrics
  - update LLM_Review post-trade notes
- Daily:
  - update Daily_Equity and Dashboard aggregates
