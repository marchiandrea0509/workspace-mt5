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

## Recommended cutover order
1. Create the portable instance.
2. Log in and attach the EA there.
3. Run `check_mt5_bridge_health.ps1 -InstanceName oanda_paper_oc`.
4. Run a smoke paper ticket against the portable pointer file.
5. Verify result JSON lands in `C:\MT5_OANDA_PAPER_OC\MQL5\Files\gray_bridge\outbox`.
6. Once proven, treat `oanda_paper_oc` as the automation default.
7. Only after that, decide whether to repoint `mql5/MQL5` from AppData to the portable instance.

## Important caution
Do not flip the default workspace pointer (`mql5/MQL5`) until the portable instance has passed at least one full end-to-end paper smoke test.
