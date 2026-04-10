Session recovery context for Discord room **#mt5** after poisoned-session reset.

Read and use this context before resuming:

- Project state: portable MT5 / OANDA paper bridge is the current baseline.
- Workspace continuity: use `PROJECT_STATE.md` plus the recent MT5 memory files.
- Prior room session `04b605be-326b-4e48-8fee-0adda0e0e647` was quarantined after repeated failure patterns.
- Key failure signals seen in the old transcript:
  - prompt_error: 5
  - usage_limit mentions: 2
  - tab_not_found mentions: 110
  - aborted markers: 5
- Do **not** blindly resume repeated browser/auth retries from the poisoned session.
- If a browser/auth/token/tab dependency fails again, stop quickly, explain the blocker, and propose the single best next action.

Recent continuity highlights:
- [2026-04-09T19:54:24.651Z] prompt_error: aborted
- [2026-04-09T19:54:24.660Z] assistant: I’ve got the local secret persisted. Now I’m pushing the Apps Script code into the newly opened script project directly from the editor session.
- [2026-04-09T20:03:49.756Z] user: Conversation info (untrusted metadata): ```json { "message_id": "1491891399476514976", "sender_id": "1322306175865323552", "conversation_label": "Guild #mt5 channel id:1487602981418303719", "sender": "anmarc", "timestamp": "Thu 2026-04-09 22:03 GMT+2", "group_subject": "#mt5", "group_channel": "#mt5", "group_space": "1487584401872261323", "is_group_chat": true } ``` Sender (untrusted metadata): `…
- [2026-04-09T20:04:02.886Z] assistant_error: You have hit your ChatGPT usage limit (plus plan). Try again in ~107 min.
- [2026-04-09T20:06:25.683Z] user: Conversation info (untrusted metadata): ```json { "message_id": "1491892054207238224", "sender_id": "1322306175865323552", "conversation_label": "Guild #mt5 channel id:1487602981418303719", "sender": "anmarc", "timestamp": "Thu 2026-04-09 22:06 GMT+2", "group_subject": "#mt5", "group_channel": "#mt5", "group_space": "1487584401872261323", "is_group_chat": true } ``` Sender (untrusted metadata): `…
- [2026-04-09T20:06:39.394Z] assistant_error: You have hit your ChatGPT usage limit (plus plan). Try again in ~104 min.
- [2026-04-10T03:36:49.995Z] prompt_error: aborted
- [2026-04-10T03:58:11.874Z] prompt_error: aborted
