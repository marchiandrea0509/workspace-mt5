#!/usr/bin/env bash
set -euo pipefail

TERM_ID="47AEB69EDDAD4D73097816C71FB25856"
TESTER_DIR="/mnt/c/Users/anmar/AppData/Roaming/MetaQuotes/Terminal/${TERM_ID}/Tester/logs"
OUT_DIR="$HOME/openclaw/workspace/memory"

mkdir -p "$OUT_DIR" "$HOME/openclaw/workspace/tools"

# pick newest tester log
LOG="$(ls -1t "$TESTER_DIR"/*.log 2>/dev/null | head -n 1 || true)"
if [[ -z "${LOG}" ]]; then
  echo "No tester .log found in: $TESTER_DIR" >&2
  exit 1
fi

STAMP="$(basename "$LOG" .log)"
OUT="$OUT_DIR/LOGS_MT5_2026-02-15_0008_TESTER.md"

echo "# MT5 Tester Digest — ${STAMP}" > "$OUT"
echo "" >> "$OUT"
echo "- Source: \`${LOG}\`" >> "$OUT"
echo "- Created: $(date -Iseconds)" >> "$OUT"
echo "" >> "$OUT"

echo "## Tester header (first matches)" >> "$OUT"
# capture key header lines (EA name, symbol, period, started, deposit/leverage)
grep -nEi "testing of Experts\\\\|expert file added:\\|initial deposit\\|leverage\\|symbol synchronized\\|history synchronized\\|MetaTester 5 started\\|initialization finished\\|authorized\\|connected" "$LOG" \
  | head -n 120 >> "$OUT" || true
echo "" >> "$OUT"

echo "## Errors / Warnings (high signal)" >> "$OUT"
# capture common error phrases + some context
PAT='invalid stops|ret=10016|lastErr=4756|cannot open file|failed modify|OrderSend|error|failed|[[]556[]]'
grep -nEi "$PAT" "$LOG" | head -n 200 >> "$OUT" || echo "(no matches)" >> "$OUT"
echo "" >> "$OUT"

echo "## Context blocks (±6 lines around key failures)" >> "$OUT"
# For each key line, print surrounding context once (limited)
python3 - <<PY >> "$OUT"
import re, pathlib
log = pathlib.Path(r"""$LOG""").read_text(errors="ignore").splitlines()
pat = re.compile(r"(invalid stops|ret=10016|lastErr=4756|cannot open file|failed modify|CTrade::OrderSend|OrderSend)", re.I)

hits = [i for i,l in enumerate(log) if pat.search(l)]
seen = set()
max_blocks = 25
ctx = 6

print(f"Log lines: {len(log)}")
print(f"Hit lines: {len(hits)}")
print("")

blocks = 0
for i in hits:
    # dedupe by nearby region
    key = i // 20
    if key in seen:
        continue
    seen.add(key)

    a = max(0, i-ctx)
    b = min(len(log), i+ctx+1)
    print(f"### Block around line {i+1}")
    for j in range(a,b):
        print(f"{j+1:6d}: {log[j]}")
    print("")
    blocks += 1
    if blocks >= max_blocks:
        break
PY

echo "" >> "$OUT"
echo "Done. Wrote: $OUT"
