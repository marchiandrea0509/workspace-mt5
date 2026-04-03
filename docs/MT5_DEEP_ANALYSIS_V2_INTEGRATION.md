# MT5 Deep Analysis v2 Integration

## Goal
Move deep analysis from screener-derived proxy levels to broker-native MT5 data while keeping source integration plug-and-play.

## What was added

### 1) Source adapter layer
- `scripts/market_source_lib.py`

Provides a swappable market-data source interface:
- `MT5PythonSource` (`kind: mt5_python`)
- `CSVFixtureSource` (`kind: csv_fixture`) for offline/future adapters

Core adapter contract:
- resolve symbol profile (`root -> analysis/execution symbol`)
- fetch rates by timeframe
- provide FX conversion into USD

### 2) MT5-native deep analysis engine
- `scripts/mt5_fx_deep_analysis_lib.py`

Uses MT5 bars for H4/D1 calculations:
- EMA 21/50/200
- RSI, ATR, DMI/ADX, MACD
- pivot-based support/resistance zones
- breakout/retest lifecycle
- trend/macro alignment
- stretch/fake-breakout checks
- execution-template classification:
  - `breakout_stop_limit`
  - `ladder_limit_2`
  - `ladder_limit_3`
  - `hybrid_ladder_breakout`
  - `no_order`

Outputs `MT5_FX_DEEP_ANALYSIS_V2` plan payload compatible with current phase1 reporting/ticket flow.

### 3) CLI runner for direct testing
- `scripts/mt5_fx_deep_analysis_v2.py`

Example:
```powershell
python scripts\mt5_fx_deep_analysis_v2.py \
  --report-json C:\Users\anmar\.openclaw\workspace\tradingview\reports\pine_screener\pine_screener_2026-04-03T07-05-25-254Z.json \
  --symbol EURGBP \
  --direction LONG
```

### 4) Phase1 integration switch
- `scripts/mt5_fx_autotrade_phase1.py`

Now uses:
- candidate selection from screener (unchanged)
- deep-analysis plan generation from MT5 source adapter (`analyze_candidate`)
- same bridge ticket emission path

### 5) Config extensions
- `config/mt5_fx_autotrade_phase1.json`

Added `analysisDataSource` block:
```json
"analysisDataSource": {
  "kind": "mt5_python",
  "terminalExe": "C:\\MT5_OANDA_PAPER_OC\\terminal64.exe",
  "preferredSuffixes": [".pro", ""],
  "historyBars": {
    "H4": 350,
    "D1": 260
  }
}
```

## Plug-and-play source swapping
To change market data source later, only update `analysisDataSource.kind` and adapter config fields.

Current supported kinds:
- `mt5_python` (live terminal)
- `csv_fixture` (offline fixture)

To add new brokers/sources later:
1. implement adapter in `market_source_lib.py`
2. wire it in `make_market_source()`
3. keep deep-analysis logic unchanged

## Test status
Validated on live terminal:
- MT5 Python initialize: success
- direct symbol resolution: success (`EURGBP.pro`, `CHFPLN.pro`)
- H4/D1 rates fetch: success
- deep-analysis v2 CLI for EURGBP: success
- deep-analysis v2 CLI for CHFPLN proxy symbol: success
- phase1 dry-run using MT5 v2 analysis: success

## Notes / current constraints
- Bridge now executes multi-entry pending packages for ladder and hybrid templates.
- Hybrid package cancel-on-fill is managed by an EA-side package state file under `gray_bridge\\trailing`.
- Current remaining constraint: package legs still share one live TP/SL set; branch-specific TP/SL management is not implemented yet.
- Proxy symbol metadata remains preserved (`CHFPLN -> Forexcom`) while analysis levels are MT5-native.
