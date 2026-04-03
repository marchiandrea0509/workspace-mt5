# Deep Analysis Transfer Pack

_Last prepared: 2026-03-29_

## What this layer is

This is the **single-asset deep-analysis / trade-planning layer** that sits after screening and before execution.

Its job is to take one selected asset — usually the screener winner — and turn it into a practical trade plan with:
- structure read
- support / resistance levels
- invalidation
- targets
- risk summary
- executable order styles
- explicit orderability classification

It was created because the screener alone was useful for ranking, but not enough for deciding whether a trade could actually be placed.

## Core principle

**PRICE_FIRST_CONTEXT_SECOND**
- price structure and levels decide the trade skeleton
- context adjusts conviction and urgency
- context does not replace execution structure

## What was transferred

### Core files
- `deep_analysis/config/trade_deep_analysis_v1.yaml`
- `deep_analysis/prompts/trade_deep_analysis_v1.md`
- `deep_analysis/prompts/single_market_deep_dive_prompt.md`
- `deep_analysis/scripts/planner_lib.py`
- `deep_analysis/scripts/generate_trade_plan.py`
- `deep_analysis/scripts/fetch_context_overlay.py`
- `deep_analysis/scripts/visual_confirmation_lib.py`
- `deep_analysis/scripts/run_daily_hybrid_workflow.py`

### Example outputs
- `deep_analysis/reports/plans/trade_plan_CRCLX_latest.{json,md}`
- `deep_analysis/reports/plans/trade_plan_ETH_PERP_latest.{json,md}`
- `deep_analysis/reports/plans/trade_plan_HOODX_20260326_170722.{json,md}`

## Functional design

### Inputs
The planner can consume:
- screener winner or explicit symbol
- 4H feature summary
- 1D feature summary
- processed candles
- macro / news / sentiment overlay
- optional TradingView visual confirmation
- account inputs: free margin, equity, risk budget, BRB%

### Outputs
The planner produces:
- market state
- key levels
- scenario block
- peak risk score
- primary and backup execution plans
- order table
- risk summary
- final trade setup table
- explicit orderability decision

## Mandatory orderability classification

Each deep analysis should end with exactly one of:
- `placeable_now`
- `placeable_conditional_only`
- `not_placeable_yet`

And must answer explicitly:
- market order now?
- ladder limits valid?
- stop entry valid?
- why?

This is the critical handoff field for eventual MT5 automation.

## Important operating rules

### Quantitative spine required
A deep analysis must not end in vague commentary.
It must include:
- bias
- setup
- conviction
- numeric levels
- invalidation
- targets
- risk/reward comment
- orderability
- final trader call

### Good market vs good entry
The system was deliberately hardened to distinguish:
- good market / bad entry
- from good trade now

This matters because a screen winner can still be unattractive for execution.

### Rejection behavior exists
The planner can mark a setup as not executable even if it is mechanically constructible.
Typical reasons include:
- poor projected reward-to-risk
- weak daily quality
- failing risk-budget checks
- structurally impractical stop distance

## Known limitations

- The planner is strong enough for v1 decision support, but it is not yet a native MT5 ticket compiler.
- Some logic originated in a screenshot-first design, but the practical implementation evolved toward structured-data-first with screenshots as optional visual confirmation.
- It can already drive the decision layer for automation, but still needs a clean translation layer into MT5 bridge ticket JSON.

## Why this belongs in the MT5 workspace

This layer is the natural middle step for the MT5 automation chain:
1. screen OANDA-compatible assets
2. choose winner
3. run deep analysis
4. classify orderability
5. translate approved plan into MT5 bridge ticket(s)
6. execute on MT5 paper via GrayPaperBridgeEA

## Best immediate use inside MT5

Treat this as the **decision layer** between screening and execution.

The strongest next integration is:
- planner output -> MT5 ticket compiler
- only when `orderability_decision` permits execution
- and only on paper until the full bridge remains stable under repeated use

## Short verdict

The deep-analysis tool is not just a prompt. It is already a reusable planning subsystem with logic, prompts, examples, outputs, and execution-readiness classification. It is ready to be adapted into the MT5 project as the pre-execution decision engine.
