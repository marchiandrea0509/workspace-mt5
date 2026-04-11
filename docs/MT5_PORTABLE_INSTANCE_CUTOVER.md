# MT5 Portable Instance Cutover

## Goal
Create a dedicated MT5 terminal for OpenClaw + OANDA paper automation so manual trading and automation no longer share the same terminal state.

## Chosen target
- Instance name: `oanda_paper_oc`
- Install/data root: `C:\MT5_OANDA_PAPER_OC`
- Launch mode: portable
- Launch command:
  - `"C:\MT5_OANDA_PAPER_OC\terminal64.exe" /portable /profile:Default`

## What was added in the workspace
- `config/mt5_instances.json`
  - named MT5 instances (`oanda_appdata`, `oanda_paper_oc`)
- `scripts/Resolve-Mt5Instance.ps1`
  - shared config resolver for MT5 instance-aware scripts
- `scripts/create_mt5_portable_instance.ps1`
  - clones the current OANDA MT5 install into a dedicated portable folder and seeds bridge directories
- `scripts/check_mt5_bridge_health.ps1`
  - now supports `-InstanceName`
- `scripts/reload_mt5_bridge.ps1`
  - now supports `-InstanceName` and portable launch args
- `mql5/MQL5_OANDA_PAPER_OC`
  - pointer file for the portable instance MQL5 root
- `scripts/emit_mt5_bridge_ticket.py`
  - schema default corrected to `config/mt5_bridge_ticket.schema.json`

## One-time setup command
```powershell
powershell -ExecutionPolicy Bypass -File scripts\create_mt5_portable_instance.ps1
```

## Manual steps after the folder exists
1. Launch the portable instance from the desktop shortcut or run:
   ```powershell
   "C:\MT5_OANDA_PAPER_OC\terminal64.exe" /portable /profile:Default
   ```
2. Log in to the OANDA paper account inside that portable terminal.
3. Open one chart.
4. Attach `GrayPaperBridgeEA` to the chart.
5. Enable Algo Trading.
6. Confirm the EA logs an initialization line for `gray_bridge\inbox`.

## Health check against the portable instance
```powershell
powershell -ExecutionPolicy Bypass -File scripts\check_mt5_bridge_health.ps1 -InstanceName oanda_paper_oc
```

## Reload bridge against the portable instance
```powershell
powershell -ExecutionPolicy Bypass -File scripts\reload_mt5_bridge.ps1 -InstanceName oanda_paper_oc
```

## Emit tickets to the portable instance
Use the new pointer file:
```powershell
python scripts\emit_mt5_bridge_ticket.py --ticket <ticket.json> --pointer mql5\MQL5_OANDA_PAPER_OC
```

## Cutover result
The cutover is now complete.

Completed outcomes:
1. Portable instance created at `C:\MT5_OANDA_PAPER_OC`.
2. `GrayPaperBridgeEA` attached and initialized there.
3. Health check proved the terminal and bridge paths are live.
4. A portable-instance ETHUSD smoke ticket first failed with `TRADE_RETCODE_CLIENT_DISABLES_AT`, confirming the path was wired but AutoTrading was still disabled.
5. After enabling AutoTrading, a retry ETHUSD smoke ticket was accepted with `TRADE_RETCODE_DONE`.
6. The default workspace pointer `mql5/MQL5` has now been repointed to `C:\MT5_OANDA_PAPER_OC\MQL5`.
7. The prior AppData-backed terminal remains preserved as fallback through `mql5/MQL5_OANDA_APPDATA` and `config/mt5_instances.json`.

## Important caution
Keep using the portable instance as the default automation target unless there is a deliberate rollback. Preserve the AppData-backed terminal as fallback/manual history rather than silently mixing the two again.

## Hard-shutdown recovery note
A 2026-04-11 hard-shutdown incident showed that the portable MT5 terminal can be restarted successfully while still failing to auto-restore `GrayPaperBridgeEA` on a chart. In that failure mode, broker login may look healthy even though the bridge watcher is still down, and duplicate/fallback MT5 terminals may also be running. See `docs/MT5_HARD_SHUTDOWN_RECOVERY_PLAN.md` for the tested operator recovery flow and the staged automation plan.

Current first-pass recovery command:
```powershell
powershell -ExecutionPolicy Bypass -File scripts\recover_mt5_after_shutdown.ps1 -InstanceName oanda_paper_oc
```
