# MT5 Hard Shutdown Recovery Plan

## Incident captured
Date: 2026-04-11

Observed on the MT5/OpenClaw laptop after a sudden hard shutdown:
- The **intended automation target** stayed the portable MT5 instance (`oanda_paper_oc`, `C:\MT5_OANDA_PAPER_OC`).
- The portable instance was initially **not running** after the reboot.
- The older AppData-backed OANDA terminal auto-restarted and logged back in on its own.
- Broker/account state remained intact (`0 positions`, `28 orders` when checked during recovery).
- Restarting the portable instance via `scripts\reload_mt5_bridge.ps1 -InstanceName oanda_paper_oc` brought MT5 back, but **did not restore the bridge EA automatically**.
- Manual reattach of `GrayPaperBridgeEA` to a chart, with Algo Trading enabled, was required before the bridge became live again.
- After manual recovery there were duplicate MT5 processes (old AppData fallback + two portable processes). Cleanup was needed so only one portable MT5 process remained.

## What this incident teaches
A hard shutdown can leave the system in a **partially recovered but dangerous-looking** state:
- broker login is fine,
- pending orders are still there,
- but the actual file-watching bridge is down because `GrayPaperBridgeEA` is not attached/initialized,
- and duplicate/fallback terminals may create confusion about which MT5 window is the real automation target.

So the recovery objective is not just "MT5 launched". The recovery objective is:
1. the **portable** MT5 instance is the only active automation terminal,
2. the broker is authorized and synchronized,
3. `GrayPaperBridgeEA` is loaded on a chart,
4. expert log shows it initialized and is watching `gray_bridge\inbox`.

## Operator recovery checklist used successfully on 2026-04-11
1. Run portable health check:
   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts\check_mt5_bridge_health.ps1 -InstanceName oanda_paper_oc
   ```
2. If not running, restart the portable terminal:
   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts\reload_mt5_bridge.ps1 -InstanceName oanda_paper_oc
   ```
3. If restart succeeds at the process level but **fails EA load verification**, open the portable MT5 terminal manually.
4. Confirm the terminal is really the portable one:
   - `File -> Open Data Folder`
   - expected root: `C:\MT5_OANDA_PAPER_OC`
5. Open a chart in the portable terminal.
6. Attach `GrayPaperBridgeEA`.
7. Ensure the chart-level EA settings allow algo trading.
8. Ensure the global **Algo Trading** button is ON.
9. Re-run the health check and confirm:
   - `latestLoadLine` is present
   - `latestInitLine` is present
10. List all MT5 processes and close the wrong ones:
   - close AppData fallback if portable bridge is healthy
   - close older duplicate portable processes if multiple portable windows exist
11. Leave one healthy portable MT5 process running.

## Automated recovery plan for next hard shutdown

### Phase 1 - Implement now: scripted detection + cleanup + clear escalation
Create a new orchestrator script, e.g. `scripts\recover_mt5_after_shutdown.ps1`, that performs the following read-only / low-risk checks first:

1. **Resolve intended target**
   - read `config\mt5_instances.json`
   - confirm default target is `oanda_paper_oc`
   - confirm workspace pointer `mql5\MQL5` still resolves to `C:\MT5_OANDA_PAPER_OC\MQL5`

2. **Inventory all MT5 processes**
   - collect process id, executable path, command line, start time, window title
   - classify each process as:
     - portable target
     - AppData fallback
     - unknown/other

3. **Health-check the portable target**
   - reuse `scripts\check_mt5_bridge_health.ps1 -InstanceName oanda_paper_oc`
   - capture:
     - running/not running
     - latest compile result
     - latest EA load line
     - latest init line
     - inbox/outbox counts

4. **If portable target is down, restart it**
   - call `scripts\reload_mt5_bridge.ps1 -InstanceName oanda_paper_oc`
   - wait for process and broker sync

5. **If AppData fallback is running while portable is healthy, close the fallback**
   - only do this when the portable target is confirmed healthy
   - do not close the fallback first if portable is still down

6. **If multiple portable processes exist, keep only one**
   - prefer the newest portable process that still corresponds to the healthy bridge state
   - close older duplicates after health confirmation

7. **Emit a recovery summary**
   - terminal inventory before/after
   - broker sync state
   - EA load/init result
   - whether manual intervention is still required

### Phase 2 - Implement next: automatic failure classification
Teach the recovery script to classify outcomes into explicit buckets:
- `RECOVERED_FULLY`
  - portable MT5 healthy, EA initialized, duplicates removed
- `RECOVERED_PARTIAL_MANUAL_EA_ATTACH_REQUIRED`
  - portable MT5 running and broker synced, but no EA load/init lines
- `FAILED_PORTABLE_START`
  - portable MT5 did not come up
- `FAILED_AUTH_OR_SYNC`
  - portable MT5 started but broker auth/sync did not appear
- `FAILED_AMBIGUOUS_DUPLICATE_STATE`
  - multiple terminals remain and healthy target cannot be identified safely

This makes Discord/agent responses much clearer during incident handling.

### Phase 3 - Best automation target: make EA restoration survive restart
The biggest gap exposed on 2026-04-11 is **EA reattachment**. Restart automation already exists; chart/EA restoration does not.

Best next steps:
1. Verify whether the portable `Default` profile truly persists the chart with `GrayPaperBridgeEA` attached.
2. Save a dedicated portable profile/template specifically for bridge recovery.
3. Test a clean shutdown/restart and a hard-kill/restart to see whether the EA survives both.
4. If MT5 still drops the EA after unclean shutdowns, investigate one of these approaches:
   - a dedicated recovery profile with a single known chart and known template,
   - a startup procedure that opens the correct profile consistently,
   - a supported way to pre-seed chart/profile files so the EA auto-loads after restart.

Important: do **not** claim this phase is automated until the expert log proves:
`GrayPaperBridgeEA initialized. Watching gray_bridge\inbox`

### Phase 4 - Optional health probe after recovery
After `RECOVERED_FULLY`, optionally run a very low-risk post-recovery verification.

Preferred options:
- read-only broker sync + pending-order inventory only, or
- a purpose-built non-trading bridge heartbeat if one is added later.

Avoid placing real test orders automatically after an incident unless the workflow is explicitly approved for that use.

## Proposed implementation tasks
Priority order:
1. Add `scripts\recover_mt5_after_shutdown.ps1` as an orchestrator around the existing health/reload scripts.
2. Add structured JSON output from the recovery script for agent-friendly summaries.
3. Add duplicate-terminal detection and safe cleanup rules.
4. Add explicit manual-escalation text for the "EA attach required" case.
5. Improve portable MT5 profile/template persistence so manual EA reattach is no longer needed after most restarts.

## Safe automation guardrails
- Never close the AppData fallback terminal **before** the portable target is healthy.
- Never assume `terminal64.exe` running means the bridge is live.
- Never assume broker login implies EA attachment.
- Never send live/paper probe orders automatically unless that behavior is explicitly approved.
- Always verify the portable instance by path (`C:\MT5_OANDA_PAPER_OC`) rather than window title alone.

## Success criteria for future recovery automation
A future hard-shutdown recovery is considered complete only when all are true:
- exactly one intended portable MT5 process remains,
- it points to `C:\MT5_OANDA_PAPER_OC`,
- broker authorization and synchronization are present,
- `expert GrayPaperBridgeEA ... loaded successfully` appears in terminal logs,
- `GrayPaperBridgeEA initialized. Watching gray_bridge\inbox` appears in expert logs,
- fallback/duplicate terminals are gone,
- the agent can summarize the final state clearly without manual forensic work.
