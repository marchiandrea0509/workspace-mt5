#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

WORKSPACE = Path(__file__).resolve().parents[1]
LATEST_PHASE1 = WORKSPACE / 'reports' / 'mt5_autotrade_phase1' / 'mt5_phase1_latest.json'

JSON_BLOCK_RE = re.compile(r'```json\s*\{.*?\}\s*```', re.DOTALL | re.IGNORECASE)
MAX_CHARS = 1800


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding='utf-8-sig'))


def load_text(path: Path) -> str:
    return path.read_text(encoding='utf-8-sig')


def fmt(x: Any) -> str:
    if x is None:
        return 'n/a'
    if isinstance(x, float):
        return f'{x:.2f}'
    return str(x)


def build_phase1_summary(o: dict[str, Any]) -> str:
    e = o.get('execution', {}) or {}
    p = o.get('plan', {}) or {}
    bias = p.get('bias', {}) or {}
    risk = p.get('risk_plan', {}) or {}
    ordy = p.get('orderability_decision', {}) or {}
    pre = e.get('preflight', {}) or {}
    lines = []
    lines.append('MT5 Phase1 execution summary')
    lines.append(f"Session: {o.get('session_key')}")
    lines.append(f"Candidate: {o.get('candidate')}")
    lines.append(f"Setup: {bias.get('setup')}")
    lines.append(f"Orderability: {ordy.get('decision')}")
    lines.append(f"Execution template: {ordy.get('execution_template')}")
    lines.append(f"Risk modeled: {fmt(risk.get('total_risk_usdt'))} USD / target {fmt(risk.get('risk_budget_usdt'))} USD")
    lines.append(f"Margin: {fmt(risk.get('total_margin_usdt'))} USD")
    lines.append(f"Execution: {fmt(e.get('status'))} | {fmt(e.get('retcode'))} ({fmt(e.get('retcode_text'))})")
    lines.append(f"Message: {fmt(e.get('message'))}")
    if pre:
        lines.append(f"Preflight: valid {fmt(pre.get('valid_entries'))}/{fmt(pre.get('original_entries'))} | adjusted plan {fmt(pre.get('adjusted_order_plan'))}")
    return '\n'.join(lines)


def strip_json_block(md: str) -> str:
    return JSON_BLOCK_RE.sub('', md).strip()


def build_comparison_summary(comp: dict[str, Any], validation: dict[str, Any]) -> str:
    d = comp.get('differences') or {}
    s = comp.get('script') or {}
    l = comp.get('llm') or {}
    lines = []
    lines.append('Phase1_LLM vs Phase1 script comparison')
    lines.append(f"Validation: {'PASS' if validation.get('valid') else 'FAIL'}")
    if validation.get('warnings'):
        lines.append('Warnings: ' + '; '.join(validation.get('warnings')[:4]))
    lines.append(f"Bias: script {fmt(s.get('bias'))} | LLM {fmt(l.get('bias'))}")
    lines.append(f"Orderability: script {fmt(s.get('orderability'))} | LLM {fmt(l.get('orderability'))}")
    lines.append(f"Entry zone: script {fmt(s.get('entry_zone_low'))}->{fmt(s.get('entry_zone_high'))} | LLM {fmt(l.get('entry_zone_low'))}->{fmt(l.get('entry_zone_high'))}")
    lines.append(f"SL / TP: script {fmt(s.get('stop_loss'))} / {fmt(s.get('take_profit'))} | LLM {fmt(l.get('stop_loss'))} / {fmt(l.get('take_profit'))}")
    lines.append(f"Risk USD: script {fmt(s.get('risk_usd'))} | LLM {fmt(l.get('risk_usd'))} | delta {fmt(d.get('risk_usd_delta'))}")
    lines.append(f"Margin USD: script {fmt(s.get('margin_usd'))} | LLM {fmt(l.get('margin_usd'))} | delta {fmt(d.get('margin_usd_delta'))}")
    lines.append(f"Legs: script {fmt(s.get('legs_count'))} | LLM {fmt(l.get('legs_count'))}")
    lines.append(f"Trailing: script {fmt(d.get('trailing_enabled_script'))} | LLM {fmt(d.get('trailing_enabled_llm'))}")
    return '\n'.join(lines)


def chunk_text(text: str, max_chars: int = MAX_CHARS) -> list[str]:
    blocks = text.split('\n\n')
    out: list[str] = []
    current = ''
    for block in blocks:
        candidate = block if not current else current + '\n\n' + block
        if len(candidate) <= max_chars:
            current = candidate
            continue
        if current:
            out.append(current)
            current = ''
        while len(block) > max_chars:
            split_at = block.rfind('\n', 0, max_chars)
            if split_at <= 0:
                split_at = max_chars
            out.append(block[:split_at])
            block = block[split_at:].lstrip('\n')
        current = block
    if current:
        out.append(current)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description='Build Discord-safe MT5 trades thread messages from phase1 + LLM shadow artifacts.')
    ap.add_argument('--phase1-json', default=str(LATEST_PHASE1))
    ap.add_argument('--planner-md', required=True)
    ap.add_argument('--comparison-json', required=True)
    ap.add_argument('--validation-json', required=True)
    ap.add_argument('--out', required=True)
    args = ap.parse_args()

    phase1 = load_json(Path(args.phase1_json))
    planner_md = strip_json_block(load_text(Path(args.planner_md)))
    comparison = load_json(Path(args.comparison_json))
    validation = load_json(Path(args.validation_json))

    messages: list[str] = []
    messages.append(build_phase1_summary(phase1))
    messages.extend(chunk_text(planner_md))
    messages.append(build_comparison_summary(comparison, validation))

    payload = {'messages': messages}
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps({'ok': True, 'out': str(out_path), 'message_count': len(messages)}, indent=2, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
