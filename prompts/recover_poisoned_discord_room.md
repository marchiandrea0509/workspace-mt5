Recover the poisoned MT5 Discord room session without losing continuity.

Follow this order:
1. Read `PROJECT_STATE.md`.
2. Read the newest MT5 `memory/*.md` files.
3. Run:
   `python scripts/recover_discord_room_session.py --agent-id mt5-fresh --channel-id 1487602981418303719 --room-label mt5 --perform-reset --restart-gateway`
4. Wait for the next fresh user message in the room to create a new session.
5. Read the newest `state/session_recovery/*/resume_message.md` and use it as the continuity seed.
6. Resume from the last stable task, not from the last failed retry loop.
7. If browser/auth/tab/token failure appears again, stop after one clear failure and explain the blocker.
