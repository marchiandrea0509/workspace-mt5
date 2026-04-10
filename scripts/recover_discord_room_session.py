#!/usr/bin/env python3
"""Recover / rehydrate a poisoned OpenClaw Discord room session.

What this does:
1. Locate the live or quarantined session transcript for a Discord room.
2. Build a recovery bundle from:
   - PROJECT_STATE.md
   - recent workspace memory/*.md notes
   - recent user/assistant text from the poisoned transcript
   - failure-pattern counters from the transcript
3. Optionally quarantine the active room session by removing its sessions.json entry
   and moving the transcript + lock out of the active sessions directory.
4. Optionally restart the OpenClaw gateway.

This is intentionally conservative: it backs up first, then detaches the room.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable


DEFAULT_AGENT_ROOT = Path(r"C:\Users\anmar\.openclaw\agents\mt5-fresh")
DEFAULT_WORKSPACE = Path(r"C:\Users\anmar\.openclaw\workspace-mt5")
DEFAULT_CHANNEL_ID = "1487602981418303719"
DEFAULT_ROOM_LABEL = "mt5"


def utc_stamp() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d_%H%M%SUTC")


def strip_untrusted_wrappers(text: str) -> str:
    patterns = [
        r"Conversation info \(untrusted metadata\):\s*```json.*?```",
        r"Sender \(untrusted metadata\):\s*```json.*?```",
        r"Untrusted context \(metadata, do not treat as instructions or commands\):\s*<<<EXTERNAL_UNTRUSTED_CONTENT.*?<<<END_EXTERNAL_UNTRUSTED_CONTENT.*?>>>",
    ]
    for pattern in patterns:
        text = re.sub(pattern, " ", text, flags=re.DOTALL)
    return text.strip()


def clean_text(text: str, limit: int = 400) -> str:
    text = strip_untrusted_wrappers(text)
    text = " ".join(text.replace("\r", " ").replace("\n", " ").split())
    return text[: limit - 1] + "…" if len(text) > limit else text


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def load_json(path: Path) -> Any:
    return json.loads(read_text(path))


def save_json(path: Path, data: Any) -> None:
    write_text(path, json.dumps(data, indent=2, ensure_ascii=False))


def extract_text_blocks(content: Any) -> list[str]:
    out: list[str] = []
    if isinstance(content, str):
        if content.strip():
            out.append(content.strip())
        return out
    if not isinstance(content, list):
        return out
    for item in content:
        if not isinstance(item, dict):
            continue
        item_type = item.get("type")
        text = item.get("text")
        if item_type in {"text", "input_text"} and isinstance(text, str) and text.strip():
            out.append(text.strip())
    return out


def parse_transcript_records(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    if not path.exists():
        return records
    with path.open("r", encoding="utf-8-sig") as fh:
        for raw_line in fh:
            raw_line = raw_line.strip()
            if not raw_line:
                continue
            try:
                obj = json.loads(raw_line)
            except json.JSONDecodeError:
                continue
            rec_type = obj.get("type")
            ts = obj.get("timestamp", "")
            if rec_type == "message":
                msg = obj.get("message", {})
                role = msg.get("role") or "unknown"
                texts = extract_text_blocks(msg.get("content"))
                error_message = msg.get("errorMessage")
                if texts:
                    for text in texts:
                        records.append({
                            "kind": role,
                            "timestamp": ts,
                            "text": clean_text(text),
                        })
                elif error_message:
                    records.append({
                        "kind": f"{role}_error",
                        "timestamp": ts,
                        "text": clean_text(error_message),
                    })
            elif rec_type == "custom" and obj.get("customType") == "openclaw:prompt-error":
                err = obj.get("data", {}).get("error", "prompt-error")
                records.append({
                    "kind": "prompt_error",
                    "timestamp": ts,
                    "text": clean_text(str(err)),
                })
    return records


def count_failure_signals(transcript_text: str, records: Iterable[dict[str, Any]]) -> dict[str, int]:
    lower = transcript_text.lower()
    kinds = Counter(rec["kind"] for rec in records)
    return {
        "prompt_error": kinds.get("prompt_error", 0),
        "assistant_error": kinds.get("assistant_error", 0),
        "usage_limit": lower.count("usage limit"),
        "tab_not_found": lower.count("tab not found"),
        "rate_limit": lower.count("rate limit"),
        "aborted": lower.count('"error":"aborted"') + lower.count("error\": \"aborted\""),
    }


def latest_memory_files(memory_dir: Path, limit: int) -> list[Path]:
    if not memory_dir.exists():
        return []
    files = sorted(memory_dir.glob("*.md"), key=lambda p: p.name, reverse=True)
    return files[:limit]


def find_live_session(agent_root: Path, agent_id: str, channel_id: str) -> tuple[str | None, dict[str, Any] | None, Path | None, Path | None, Path]:
    sessions_dir = agent_root / "sessions"
    sessions_json = sessions_dir / "sessions.json"
    if not sessions_json.exists():
        return None, None, None, None, sessions_json
    sessions = load_json(sessions_json)
    key = f"agent:{agent_id}:discord:channel:{channel_id}"
    entry = sessions.get(key)
    if not entry:
        return key, None, None, None, sessions_json
    session_id = entry.get("sessionId")
    transcript = sessions_dir / f"{session_id}.jsonl" if session_id else None
    lock = sessions_dir / f"{session_id}.jsonl.lock" if session_id else None
    return key, entry, transcript, lock, sessions_json


def find_archive_transcript(archive_dir: Path) -> tuple[Path | None, dict[str, Any] | None]:
    entry_path = archive_dir / "removed-session-entry.json"
    entry = load_json(entry_path) if entry_path.exists() else None
    candidates = sorted(
        [p for p in archive_dir.iterdir() if p.is_file() and ".jsonl" in p.name and ".lock" not in p.name],
        key=lambda p: p.name,
    ) if archive_dir.exists() else []
    transcript = candidates[0] if candidates else None
    return transcript, entry


def build_bundle(
    workspace: Path,
    archive_dir: Path,
    transcript_path: Path | None,
    entry: dict[str, Any] | None,
    room_label: str,
    channel_id: str,
    memory_limit: int,
    recent_limit: int,
) -> tuple[Path, Path]:
    bundle_dir = workspace / "state" / "session_recovery" / f"{room_label}_{channel_id}_{utc_stamp()}"
    bundle_dir.mkdir(parents=True, exist_ok=True)

    project_state = read_text(workspace / "PROJECT_STATE.md") if (workspace / "PROJECT_STATE.md").exists() else "(missing)"
    memory_files = latest_memory_files(workspace / "memory", memory_limit)
    memory_sections: list[str] = []
    for mem in memory_files:
        memory_sections.append(f"## {mem.name}\n\n{read_text(mem).strip()}\n")

    transcript_text = read_text(transcript_path) if transcript_path and transcript_path.exists() else ""
    records = parse_transcript_records(transcript_path) if transcript_path else []
    failure_counts = count_failure_signals(transcript_text, records)
    recent_records = [r for r in records if r["kind"] in {"user", "assistant", "assistant_error", "prompt_error"}][-recent_limit:]

    recent_lines = []
    for rec in recent_records:
        recent_lines.append(f"- [{rec['timestamp']}] {rec['kind']}: {rec['text']}")

    session_id = entry.get("sessionId") if isinstance(entry, dict) else None
    entry_path = archive_dir / "removed-session-entry.json"

    recovery_md = f"""# Discord Room Session Recovery Bundle

- Generated: {datetime.now(UTC).isoformat()}
- Room: {room_label}
- Channel ID: {channel_id}
- Prior session ID: {session_id or '(unknown)'}
- Transcript source: {transcript_path if transcript_path else '(missing)'}
- Session entry source: {entry_path if entry_path.exists() else '(missing)'}

## Failure signal counts

- prompt_error: {failure_counts['prompt_error']}
- assistant_error: {failure_counts['assistant_error']}
- usage_limit mentions: {failure_counts['usage_limit']}
- tab_not_found mentions: {failure_counts['tab_not_found']}
- rate_limit mentions: {failure_counts['rate_limit']}
- aborted markers: {failure_counts['aborted']}

## Current MT5 project state

{project_state.strip()}

## Recent MT5 memory

{chr(10).join(memory_sections).strip() if memory_sections else '(no memory files found)'}

## Recent transcript highlights

{chr(10).join(recent_lines) if recent_lines else '(no transcript highlights found)'}

## Recommended recovery approach

1. Start from a fresh Discord room session.
2. Re-read `PROJECT_STATE.md` and the recent memory files listed above.
3. Use the recent transcript highlights only as continuity context, not as instructions to resume every failed retry.
4. Be suspicious of repeated browser/auth/tool loops. If a browser tab/auth/token/resource is missing, stop after one clear failure and report it.
5. Prefer resuming from the last stable task, not from the last failed retry.
"""

    resume_md = f"""Session recovery context for Discord room **#{room_label}** after poisoned-session reset.

Read and use this context before resuming:

- Project state: portable MT5 / OANDA paper bridge is the current baseline.
- Workspace continuity: use `PROJECT_STATE.md` plus the recent MT5 memory files.
- Prior room session `{session_id or '(unknown)'}` was quarantined after repeated failure patterns.
- Key failure signals seen in the old transcript:
  - prompt_error: {failure_counts['prompt_error']}
  - usage_limit mentions: {failure_counts['usage_limit']}
  - tab_not_found mentions: {failure_counts['tab_not_found']}
  - aborted markers: {failure_counts['aborted']}
- Do **not** blindly resume repeated browser/auth retries from the poisoned session.
- If a browser/auth/token/tab dependency fails again, stop quickly, explain the blocker, and propose the single best next action.

Recent continuity highlights:
{chr(10).join(recent_lines[-8:]) if recent_lines else '- (no transcript highlights found)'}
"""

    bundle_path = bundle_dir / "recovery_bundle.md"
    resume_path = bundle_dir / "resume_message.md"
    write_text(bundle_path, recovery_md)
    write_text(resume_path, resume_md)

    meta = {
        "generatedAt": datetime.now(UTC).isoformat(),
        "roomLabel": room_label,
        "channelId": channel_id,
        "priorSessionId": session_id,
        "transcriptPath": str(transcript_path) if transcript_path else None,
        "entryPath": str(entry_path) if entry_path.exists() else None,
        "failureCounts": failure_counts,
        "bundlePath": str(bundle_path),
        "resumeMessagePath": str(resume_path),
    }
    save_json(bundle_dir / "recovery_meta.json", meta)
    return bundle_path, resume_path


def quarantine_live_session(
    agent_root: Path,
    sessions_json: Path,
    session_key: str,
    entry: dict[str, Any],
    transcript_path: Path | None,
    lock_path: Path | None,
    archive_dir: Path,
) -> None:
    archive_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(sessions_json, archive_dir / "sessions.json.backup")
    save_json(archive_dir / "removed-session-entry.json", entry)

    sessions = load_json(sessions_json)
    if session_key in sessions:
        del sessions[session_key]
        save_json(sessions_json, sessions)

    if transcript_path and transcript_path.exists():
        shutil.move(str(transcript_path), str(archive_dir / f"{transcript_path.name}.quarantined"))
    if lock_path and lock_path.exists():
        shutil.move(str(lock_path), str(archive_dir / f"{lock_path.name}.quarantined"))


def restart_gateway() -> tuple[int, str]:
    cmd = ["openclaw", "gateway", "restart"]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    output = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, output.strip()


def main() -> int:
    ap = argparse.ArgumentParser(description="Recover / rehydrate a poisoned Discord room session.")
    ap.add_argument("--agent-id", default="mt5-fresh")
    ap.add_argument("--agent-root", default=str(DEFAULT_AGENT_ROOT))
    ap.add_argument("--workspace", default=str(DEFAULT_WORKSPACE))
    ap.add_argument("--channel-id", default=DEFAULT_CHANNEL_ID)
    ap.add_argument("--room-label", default=DEFAULT_ROOM_LABEL)
    ap.add_argument("--archive-dir", default="", help="Use an existing quarantine archive instead of a live session.")
    ap.add_argument("--session-file", default="", help="Use a specific transcript file instead of looking up the live room binding.")
    ap.add_argument("--memory-files", type=int, default=3)
    ap.add_argument("--recent-messages", type=int, default=16)
    ap.add_argument("--perform-reset", action="store_true", help="Quarantine the active room session after building the recovery bundle.")
    ap.add_argument("--restart-gateway", action="store_true", help="Restart OpenClaw gateway after quarantine.")
    args = ap.parse_args()

    agent_root = Path(args.agent_root)
    workspace = Path(args.workspace)

    archive_dir = Path(args.archive_dir) if args.archive_dir else agent_root / "session-archive" / f"discord_room_recovery_{args.room_label}_{args.channel_id}_{utc_stamp()}"

    entry = None
    transcript_path: Path | None = None
    sessions_json: Path | None = None
    session_key: str | None = None
    lock_path: Path | None = None

    if args.archive_dir:
        transcript_path, entry = find_archive_transcript(Path(args.archive_dir))
    elif args.session_file:
        transcript_path = Path(args.session_file)
    else:
        session_key, entry, transcript_path, lock_path, sessions_json = find_live_session(agent_root, args.agent_id, args.channel_id)

    bundle_path, resume_path = build_bundle(
        workspace=workspace,
        archive_dir=archive_dir,
        transcript_path=transcript_path,
        entry=entry,
        room_label=args.room_label,
        channel_id=args.channel_id,
        memory_limit=args.memory_files,
        recent_limit=args.recent_messages,
    )

    print(f"RECOVERY_BUNDLE={bundle_path}")
    print(f"RESUME_MESSAGE={resume_path}")

    if args.perform_reset:
        if not (session_key and entry and sessions_json):
            raise SystemExit("--perform-reset requires a live room session entry.")
        quarantine_live_session(
            agent_root=agent_root,
            sessions_json=sessions_json,
            session_key=session_key,
            entry=entry,
            transcript_path=transcript_path,
            lock_path=lock_path,
            archive_dir=archive_dir,
        )
        print(f"QUARANTINE_ARCHIVE={archive_dir}")
        if args.restart_gateway:
            code, output = restart_gateway()
            print(f"GATEWAY_RESTART_EXIT={code}")
            if output:
                print(output)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
