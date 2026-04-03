import json
import subprocess
import sys
from pathlib import Path

workspace = Path(r"C:\Users\anmar\.openclaw\workspace-mt5")
emit_script = workspace / "scripts" / "emit_mt5_bridge_ticket.py"
tickets = [
    ("L1", workspace / "examples" / "mt5_bridge_ticket.paper.limit.single.nzdsgd.autotrade.l1.20260329.json"),
    ("L2", workspace / "examples" / "mt5_bridge_ticket.paper.limit.single.nzdsgd.autotrade.l2.20260329.json"),
    ("L3", workspace / "examples" / "mt5_bridge_ticket.paper.limit.single.nzdsgd.autotrade.l3.20260329.json"),
]


def parse_json_stream(text: str):
    decoder = json.JSONDecoder()
    idx = 0
    items = []
    while idx < len(text):
        while idx < len(text) and text[idx].isspace():
            idx += 1
        if idx >= len(text):
            break
        obj, end = decoder.raw_decode(text, idx)
        items.append(obj)
        idx = end
    return items


def clean_message(text: str) -> str:
    return " ".join((text or "").strip().split())


results = []
for leg, ticket_path in tickets:
    ticket = json.loads(ticket_path.read_text(encoding="utf-8"))
    entry = ticket["entries"][0].get("price")
    ticket_id = ticket.get("ticket_id")
    cmd = [
        sys.executable,
        str(emit_script),
        "--ticket",
        str(ticket_path),
        "--wait-seconds",
        "90",
        "--poll-seconds",
        "2",
    ]
    proc = subprocess.run(cmd, cwd=str(workspace), capture_output=True, text=True)

    parsed_stdout = []
    try:
        parsed_stdout = parse_json_stream(proc.stdout)
    except Exception:
        parsed_stdout = []

    result_obj = None
    timeout_obj = None
    for obj in parsed_stdout:
        if isinstance(obj, dict):
            if "status" in obj or "retcode" in obj or "retcode_text" in obj or "mt5_order_ids" in obj:
                result_obj = obj
            if obj.get("result") == "timeout":
                timeout_obj = obj

    stderr_text = clean_message(proc.stderr)
    if result_obj is not None:
        status = str(result_obj.get("status") or ("timeout" if proc.returncode == 2 else "unknown"))
        message = clean_message(result_obj.get("message") or result_obj.get("retcode_text") or stderr_text or "")
        order_ids = result_obj.get("mt5_order_ids") or []
    elif timeout_obj is not None or proc.returncode == 2:
        status = "timeout"
        message = clean_message((timeout_obj or {}).get("hint") or stderr_text or "No result file appeared within 90 seconds.")
        order_ids = []
    else:
        status = "error"
        message = stderr_text or clean_message(proc.stdout) or f"Emitter exited with code {proc.returncode}."
        order_ids = []

    haystack = " ".join([
        status,
        message,
        stderr_text,
        json.dumps(result_obj or {}, ensure_ascii=False),
    ]).lower()
    symbol_issue = any(token in haystack for token in ["symbolselect", "symbol select", "symbol availability", "market watch", "symbol not found", "unknown symbol"])

    results.append({
        "leg": leg,
        "ticket_id": ticket_id,
        "entry": entry,
        "status": status,
        "message": message,
        "order_ids": order_ids,
        "symbol_issue": symbol_issue,
        "returncode": proc.returncode,
    })

accepted = sum(1 for r in results if r["status"] == "accepted")
failed = sum(1 for r in results if r["status"] not in {"accepted", "timeout"})
timed_out = sum(1 for r in results if r["status"] == "timeout")
symbol_issues = sum(1 for r in results if r["symbol_issue"])

for r in results:
    order_id = r["order_ids"][0] if r["order_ids"] else "n/a"
    suffix = " SYMBOL AVAILABILITY ISSUE." if r["symbol_issue"] else ""
    print(f"- {r['leg']}: ticket id {r['ticket_id']}, entry {r['entry']}, status {r['status']}, message {r['message'] or 'n/a'}, order id {order_id}.{suffix}")

summary = f"Summary: accepted {accepted}/3, failed {failed}/3, timed out {timed_out}/3"
if symbol_issues:
    summary += f"; symbol-availability issues on {symbol_issues} leg(s)"
summary += "."
print(summary)
