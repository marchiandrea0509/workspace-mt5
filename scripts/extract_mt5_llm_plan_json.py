#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


JSON_BLOCK_RE = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL | re.IGNORECASE)


def load_text(path: Path) -> str:
    return path.read_text(encoding='utf-8-sig')


def extract_json_block(text: str) -> dict[str, Any]:
    match = JSON_BLOCK_RE.search(text)
    if not match:
        raise ValueError('No fenced ```json ... ``` block found in planner output')
    return json.loads(match.group(1))


def main() -> int:
    ap = argparse.ArgumentParser(description='Extract the fenced JSON plan block from an LLM planner markdown/text output.')
    ap.add_argument('--input', required=True)
    ap.add_argument('--out', required=True)
    args = ap.parse_args()

    payload = extract_json_block(load_text(Path(args.input)))
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps({'ok': True, 'out': str(out_path), 'top_level_keys': list(payload.keys())}, indent=2, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
