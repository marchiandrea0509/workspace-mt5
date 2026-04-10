# MT5 Discord Room Session Recovery

Use this when the MT5 Discord room starts **typing and then stopping**, keeps replaying the same bad state, or is clearly stuck on a poisoned old session.

## What this workflow solves

Typical symptoms:
- Discord room message is received, Gray starts typing, then stops after ~2 minutes.
- Same room keeps binding to one old `sessionId`.
- Transcript shows repeated `tab not found`, `openclaw:prompt-error`, `aborted`, usage-limit noise, or browser/auth retry loops.
- Generic Discord-side error text hides the real failure.

This workflow does **three** things:
1. quarantines the poisoned room session
2. restarts OpenClaw so the next room message binds to a fresh session
3. builds a recovery packet from MT5 memory + the old room transcript so continuity is not lost

## Canonical command

For the current MT5 room (`#mt5`, channel `1487602981418303719`):

```powershell
python scripts/recover_discord_room_session.py `
  --agent-id mt5-fresh `
  --channel-id 1487602981418303719 `
  --room-label mt5 `
  --perform-reset `
  --restart-gateway
```

## What the script produces

Under `state/session_recovery/<room>_<channel>_<timestamp>/` it writes:
- `recovery_bundle.md` — the full continuity packet
- `resume_message.md` — short seed message for the fresh session
- `recovery_meta.json` — machine-readable metadata

If `--perform-reset` is used, it also creates an archive under:
- `.openclaw/agents/<agent>/session-archive/discord_room_recovery_<room>_<channel>_<timestamp>/`

That archive contains:
- `sessions.json.backup`
- `removed-session-entry.json`
- quarantined transcript / lock files

## Recommended operator workflow

### A. Detect a poisoned session

Check for a combination of:
- stuck typing
- repeated old errors
- bloated transcript
- fresh `.lock` file on the same old session

### B. Run the recovery script

Use the canonical command above.

### C. Send one fresh message in the Discord room

After gateway restart, the **next** room message should create a fresh session.

Do **not** expect older pre-restart messages to be answered.

### D. Rehydrate the new session

Use `resume_message.md` as the seed context for the fresh room session.

Recovery priority order:
1. `PROJECT_STATE.md`
2. recent `memory/*.md`
3. `resume_message.md`
4. `recovery_bundle.md` if deeper continuity is needed

## Agent behavior after recovery

When resuming after a poisoned reset, the agent should:
- read `PROJECT_STATE.md`
- read recent MT5 memory files
- use transcript highlights only for continuity, **not** as orders to replay every failed retry
- stop quickly on browser/auth/tab/token failures instead of looping
- prefer the **last stable task** over the **last failed attempt**

## Already-quarantined session: rebuild bundle only

If the room was already quarantined and you only want the continuity bundle:

```powershell
python scripts/recover_discord_room_session.py `
  --agent-id mt5-fresh `
  --room-label mt5 `
  --channel-id 1487602981418303719 `
  --archive-dir C:\Users\anmar\.openclaw\agents\mt5-fresh\session-archive\discord_room_recovery_mt5_1487602981418303719_<timestamp>
```

## Case note: 2026-04-10

This runbook was created after the MT5 room got poisoned twice.

Observed pattern in the bad session:
- invalid model config created the first misleading “API rate limit” symptom
- after that was fixed, the room still stayed wedged on a large old transcript
- transcript contained repeated browser / Apps Script style retries (`tab not found`) and aborted runs
- the clean fix was to quarantine the room session, restart the gateway, and let the next Discord message create a fresh room session
