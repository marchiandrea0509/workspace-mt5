# MT5_FRX Phase 1 Autotrade

## Scope (Phase 1)
- Input: latest `MT5_FRX` Pine Screener report (`4h`, best-score sorted).
- Selection: first symbol that passes predefined criteria.
- Analysis: MT5-native FX deep-analysis summary with orderability decision.
- Execution cap: **max 1 trade package per screening session**.
- Asset cap: one active asset lock in local state.
- MT5 mode: **paper only** (`mt5.paper.v1`).

## Files
- Config: `config/mt5_fx_autotrade_phase1.json`
- Orchestrator: `scripts/mt5_fx_autotrade_phase1.py`
- Cron prompt: `prompts/cron_mt5_fx_phase1.md`
- Compact MT5 open report: `scripts/mt5_open_compact_report.py`
- Discord thread message builder: `scripts/build_mt5_thread_messages.py`
- Runtime reports: `reports/mt5_autotrade_phase1/`
- Runtime state: `state/mt5_autotrade_phase1/`
- Excel journal builder: `scripts/build_trade_journal_excel.py`
- Excel upload staging helper: `scripts/stage_trade_journal_for_browser_upload.py`
- Excel journal workflow: `docs/MT5_TRADE_JOURNAL_EXCEL_WORKFLOW.md`
- Best-effort Drive upload prompt: `prompts/upload_mt5_excel_to_gdrive_best_effort.md`

## Predefined criteria
- Best Score >= 70
- Conviction State >= 3
- ADX >= 20
- Dist Fast EMA ATR <= 1.35
- Directional score >= 70 (long/short side-specific)
- Setup code in `{2, -2}`
- Trend + Macro (1D) alignment required

## Risk + sizing defaults
- Risk budget: 100 USD
- Margin cap: 1000 USD
- Modeled leverage: 10x
- FX contract size model: 100,000
- Default min lot: 0.01, step: 0.01

## Symbol mapping
- TradingView and screener logic use normalized FX roots like `EURGBP`.
- MT5 execution now resolves those roots through the OANDA export file:
  - `C:\MT5_OANDA_PAPER_OC\MQL5\Files\OANDA_All_Symbols.csv`
- The planner prefers trade-enabled broker symbols, e.g.:
  - `EURGBP` -> `EURGBP.PRO`
  - `CHFPLN` -> `CHFPLN.PRO`
- This avoids sending plain-root symbols to MT5 when the tradable broker instrument is the suffixed symbol.
- Proxy-symbol tagging is supported too. Right now:
  - `CHFPLN` is marked as a TradingView proxy symbol sourced from `Forexcom`
- In phase 1 this is metadata only; it does **not** change trade rules yet.
- The proxy marker is surfaced in:
  - deep-analysis source context
  - ticket preview metadata
  - MT5 bridge `strategy_context`
  - analysis notes / ticket note text

The planner computes lot size from both:
1) risk budget, and
2) margin cap,
then takes the tighter value.

## Session dedupe
Session key:
`<watchlist>|<timeframe>|<generatedAt>`

- If a session key is already in `state/mt5_autotrade_phase1/sessions.json`, re-run is skipped unless `--force`.

## Current cron wiring
- Screener cron (existing):
  - `MT5_FRX Pine Screener 4H`
  - `5 7,9,15,17 * * 1-5` (Europe/Berlin)
- Phase 1 autotrade cron (new):
  - `MT5_FRX Phase1 Autotrade`
  - `7 7,9,15,17 * * 1-5` (Europe/Berlin)
  - model: `openai/gpt-5.4-nano`
  - thread output now prepends a fresh compact MT5 open report generated during the cron cycle
  - that report can cancel stale strategy-managed pending orders before posting, using the configured cleanup thresholds in `compactReportCleanup`
  - live LLM execution now applies a per-symbol guard before emitting new legs:
    - if the symbol already has active strategy-managed **open positions**, block the new ladder
    - if the symbol has only older **pending** strategy-managed orders, cancel those pending orders first and then allow the new ladder (`liveSymbolGuard.mode = replace_pending_only`)

## Manual run
Dry run:
`python scripts/mt5_fx_autotrade_phase1.py --dry-run --force`

Live paper run:
`python scripts/mt5_fx_autotrade_phase1.py --force`

## Current execution capability
- Ladder packages are now live through the bridge.
- Hybrid ladder + breakout packages are now live through the bridge.
- Hybrid package state is persisted in `gray_bridge\\trailing\\*__package.json` so the EA timer can cancel the opposite branch after a fill.
- Current limitation: package legs still share one live TP/SL set; per-leg TP/SL differentiation is not implemented yet.
