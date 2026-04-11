# MT5 Profile Persistence Hardening

## Why this exists
The 2026-04-11 hard-shutdown incident showed a specific weak point in the portable MT5 setup:
- the portable terminal could be restarted,
- broker authorization and synchronization could return,
- but `GrayPaperBridgeEA` still might **not** come back on a chart after an unclean shutdown.

That means the bridge can be down even while MT5 itself looks healthy.

## Key findings from inspection on 2026-04-11

### 1) `MQL5\Profiles` appears to be the authoritative profile store
MetaTrader documentation says profiles/templates are stored under `\MQL5\Profiles`, and the portable instance inspection matches that better than the stale top-level `Profiles\...` tree.

Observed locally:
- `C:\MT5_OANDA_PAPER_OC\MQL5\Profiles\Charts\Default\chart03.chr`
  - symbol text decodes as `EURGBP.pro`
  - modified on `2026-04-06`
- `C:\MT5_OANDA_PAPER_OC\Profiles\Charts\Default\chart03.chr`
  - still looked like the old cloned `GBPUSD` default chart
  - timestamp remained at the original `2026-03-01` clone time

Operational conclusion:
- treat **`MQL5\Profiles` as the profile/template recovery source of truth**
- do **not** rely on the top-level portable `Profiles\...` tree as the main recovery input

### 2) Live EA attach did not obviously flush profile files during the incident window
After the manual EA reattach that restored the bridge, the files that visibly changed were mainly:
- `Config\terminal.ini`
- `Config\settings.ini`

The obvious chart profile files did **not** show fresh timestamps from the reattach moment.

Operational conclusion:
- a live healthy bridge does **not** automatically prove the on-disk profile state is now safely crash-persistent
- the safest way to capture a durable recovery baseline is after a **controlled clean MT5 exit**

## Hardening model
Use two layers:

### Layer A - Known-good recovery baseline
Capture a workspace-stored snapshot of the portable terminal's recovery-critical state:
- `Config\terminal.ini`
- `Config\settings.ini`
- `Config\common.ini`
- `MQL5\Profiles\**`

This gives a durable recovery package that can be restored even if MT5's crash persistence is unreliable.

### Layer B - Baseline-aware recovery
If a future shutdown leaves MT5 in the familiar bad state:
- terminal running
- broker synced
- no `GrayPaperBridgeEA` load/init lines

then the recovery flow can restore the known-good baseline and restart MT5, instead of immediately falling back to manual reattach.

## New scripts

### Save a known-good baseline
```powershell
powershell -ExecutionPolicy Bypass -File scripts\save_mt5_recovery_baseline.ps1 -InstanceName oanda_paper_oc
```

What it does:
- verifies the bridge is currently healthy
- attempts a **graceful** MT5 window close so profile state can flush to disk
- snapshots the selected config files and `MQL5\Profiles`
- writes the snapshot under:
  - `state\mt5_recovery_baselines\oanda_paper_oc\<timestamp>`
- updates:
  - `state\mt5_recovery_baselines\oanda_paper_oc\LATEST.json`
- restarts MT5 and re-verifies health

Important:
- by default it refuses to save from an unhealthy bridge state
- by default it also refuses to fall back to a forced close unless you explicitly pass `-ForceCloseOnTimeout`

### Restore the latest known-good baseline
```powershell
powershell -ExecutionPolicy Bypass -File scripts\restore_mt5_recovery_baseline.ps1 -InstanceName oanda_paper_oc -RestartAfterRestore
```

What it does:
- resolves the latest saved baseline from `LATEST.json`
- makes a safety backup of the current selected config files and `MQL5\Profiles`
- restores the baseline into the portable MT5 data root
- optionally restarts MT5 and health-checks it

Safety note:
- restore operates only on the selected config files and `MQL5\Profiles`
- it intentionally does **not** roll back account databases like `accounts.dat` or `servers.dat`

### Baseline-aware recovery
```powershell
powershell -ExecutionPolicy Bypass -File scripts\recover_mt5_after_shutdown.ps1 -InstanceName oanda_paper_oc -TryRestoreBaselineOnMissingEa
```

What it adds:
- detects whether a recovery baseline exists
- if MT5 comes back but the EA/profile state is incomplete, it can attempt a restore of the latest baseline before escalating to manual reattach

## Recommended operating procedure

### Right now
1. Keep the current portable MT5 healthy and unchanged.
2. At a convenient moment when a brief controlled restart is acceptable, run:
   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts\save_mt5_recovery_baseline.ps1 -InstanceName oanda_paper_oc
   ```
3. Confirm a baseline was created and MT5 returned healthy.

### On the next hard shutdown
1. Run the baseline-aware recovery path first:
   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts\recover_mt5_after_shutdown.ps1 -InstanceName oanda_paper_oc -TryRestoreBaselineOnMissingEa
   ```
2. If outcome is still partial, inspect MT5 manually and reattach `GrayPaperBridgeEA` only as the fallback step.
3. After manual recovery, capture a fresh known-good baseline again.

## What remains unproven
As of 2026-04-11, the following still needs a controlled live test:
- whether the current portable `Default` profile now survives a clean close/reopen with the bridge EA intact
- whether the saved baseline restore is sufficient to auto-recover the EA without manual reattach after a simulated bad state

So the tooling is in place, but the final proof step is still:
- **capture baseline**
- **test restore path**

## Bottom line
The system is now better prepared for the exact shutdown failure we saw:
- recovery already handled terminal restart + duplicate cleanup
- persistence hardening now adds baseline save/restore tooling
- the next high-value move is to capture a known-good baseline during a controlled restart window
