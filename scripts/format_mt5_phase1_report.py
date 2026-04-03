#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[1]
LATEST = WORKSPACE / 'reports' / 'mt5_autotrade_phase1' / 'mt5_phase1_latest.json'


def load_json(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))


def fmt(x):
    if x is None:
        return 'n/a'
    if isinstance(x, float):
        return f'{x:.2f}'
    return str(x)


def main():
    o = load_json(LATEST)
    e = o.get('execution', {}) or {}
    p = o.get('plan', {}) or {}
    bias = p.get('bias', {}) or {}
    risk = p.get('risk_plan', {}) or {}
    ordy = p.get('orderability_decision', {}) or {}
    pre = e.get('preflight', {}) or {}
    ticket = {}
    tpath = o.get('ticket_path')
    if tpath and Path(tpath).exists():
        ticket = load_json(Path(tpath))

    lines = []
    lines.append('MT5 Phase1 trade report')
    lines.append('')
    lines.append(f"Session: {o.get('session_key')}")
    lines.append(f"Report source: {o.get('report_resolution')} -> {o.get('report_path')}")
    lines.append(f"Candidate: {o.get('candidate')}")
    lines.append(f"Setup: {bias.get('setup')}")
    lines.append(f"Orderability: {ordy.get('decision')}")
    lines.append(f"Execution template: {ordy.get('execution_template')}")
    lines.append('')
    lines.append('Candidate audit:')
    for item in (o.get('audit') or [])[:5]:
        status = 'PASS' if item.get('passed') else 'SKIP'
        reasons = '; '.join(item.get('reasons') or []) or 'meets criteria'
        lines.append(f"- {item.get('symbol')}: {status} | {reasons}")
    lines.append('')
    lines.append('Risk model:')
    lines.append(f"- target risk: {fmt(risk.get('risk_budget_usdt'))} USD")
    lines.append(f"- max risk: {fmt(risk.get('risk_budget_max_usdt'))} USD")
    lines.append(f"- actual modeled risk: {fmt(risk.get('total_risk_usdt'))} USD")
    lines.append(f"- margin: {fmt(risk.get('total_margin_usdt'))} USD")
    lines.append(f"- leverage: x{fmt(risk.get('model_leverage'))}")
    lines.append(f"- binding constraint: {fmt(risk.get('binding_constraint'))}")
    lines.append('')
    if ticket:
        lines.append('Emitted MT5 package:')
        for idx, entry in enumerate(ticket.get('entries', []), start=1):
            lines.append(f"- leg {idx}: {entry.get('client_entry_id')} | {entry.get('entry_type')} | {entry.get('price')} | {entry.get('volume_lots')} lots")
        lines.append(f"- SL: {ticket.get('stop_loss',{}).get('price')}")
        lines.append(f"- TP: {ticket.get('take_profit',{}).get('price')}")
        lines.append('')
    if pre:
        lines.append('MT5 preflight:')
        lines.append(f"- valid entries: {fmt(pre.get('valid_entries'))} / {fmt(pre.get('original_entries'))}")
        lines.append(f"- adjusted order plan: {fmt(pre.get('adjusted_order_plan'))}")
        for item in (pre.get('rejected_entries') or [])[:8]:
            reasons = '; '.join(item.get('reasons') or [])
            lines.append(f"- rejected {item.get('client_entry_id')}: {reasons}")
        lines.append('')
    lines.append('Execution:')
    lines.append(f"- status: {fmt(e.get('status'))}")
    lines.append(f"- retcode: {fmt(e.get('retcode'))} ({fmt(e.get('retcode_text'))})")
    lines.append(f"- message: {fmt(e.get('message'))}")
    if e.get('mt5_order_ids'):
        lines.append(f"- mt5_order_ids: {e.get('mt5_order_ids')}")

    print('\n'.join(lines))


if __name__ == '__main__':
    main()
