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

## Validation result on 2026-04-11
A controlled Saturday validation window was completed.

What was proven:
- a baseline snapshot was captured successfully:
  - `state\mt5_recovery_baselines\oanda_paper_oc\20260411_094722`
- MT5 was restarted through the intended launch path with:
  - `/portable /profile:Default`
- after adding fresh-log validation to the PowerShell helpers, a controlled restart was verified with **new** post-restart evidence for all critical signals:
  - load at `09:54:41`
  - authorization at `09:54:42`
  - synchronization at `09:54:43`
  - EA init at `09:54:43`

What this means:
- the launcher path is correct
- the baseline save path works
- the restart verification path now distinguishes fresh evidence from stale same-day log lines
- the portable MT5 bridge can come back healthy after a controlled restart without manual EA reattach

## What remains unproven
The main remaining proof step is narrower now:
- whether the **restore-from-baseline** path is sufficient to recover automatically from a deliberately simulated bad profile/EA state without manual reattach

So the hardening status is now:
- **baseline save: validated**
- **fresh restart verification: validated**
- **baseline restore as automatic remediation: not yet validated**

## Bottom line
The system is materially more robust than it was before the 2026-04-11 shutdown incident:
- recovery handles terminal restart + duplicate cleanup
- persistence hardening adds baseline save/restore tooling
- strict fresh-log validation now prevents false positives from stale same-day MT5 logs
- a controlled restart has been validated end-to-end for the portable bridge path
- a Windows scheduled task (`MT5 Boot Recovery`) now runs the baseline-aware recovery flow automatically **at user logon**
