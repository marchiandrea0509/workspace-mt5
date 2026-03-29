Project: MT5 / OANDA paper bridge
Goal: Own continuity and development for MT5 trading automation, especially the Gray -> MT5 paper execution bridge and related MT5 tooling
Agent role: Main continuity agent for MT5 trading automation, EA work, bridge health, ticket execution logic, and future MT5 integration from higher-level Gray workflows
Current phase: Portable-instance cutover completed; portable MT5 is now the default automation target
Last successful step: Created the dedicated portable OANDA paper MT5 instance, updated the bridge scripts to be instance-aware, repointed the default workspace MQL5 pointer to the portable instance, and proved an accepted ETHUSD smoke test on that new terminal
Current architecture: Host emits validated `mt5.paper.v1` ticket JSON -> default workspace pointer `mql5\\MQL5` -> `C:\MT5_OANDA_PAPER_OC\MQL5\Files\gray_bridge\\inbox` -> `GrayPaperBridgeEA` inside the dedicated portable MT5 instance -> broker paper order request -> result JSON in `outbox`, ticket moved to `archive` or `errors`, optional trailing config persisted
Verified scope: End-to-end paper v1 bridge is proven on the dedicated portable instance for the current single-ticket flow; BTCUSD and ETHUSD paper orders have been accepted; trailing config persistence is proven
Next step: Use the now-isolated portable instance as the baseline for the next MT5-owned deliverable, with the best current candidate still being proof of post-fill trailing SL movement end-to-end
Blockers: No core architecture blocker; remaining proof gap is live post-fill trailing behavior after fill and trigger; live trading remains out of scope
Key live MT5 path: `C:\MT5_OANDA_PAPER_OC\MQL5`
Notes: `workspace-mt5` is now the continuity workspace. The tracked EA mirror lives in `mt5_bridge\GrayPaperBridgeEA.mq5`. The default automation target is now the portable instance via `mql5\MQL5`, while the prior AppData-backed terminal is preserved as fallback via `mql5\MQL5_OANDA_APPDATA` and `config\mt5_instances.json`.
