import json
from pathlib import Path

src = Path(r'C:\Users\anmar\.openclaw\workspace-mt5\reports\mt5_autotrade_phase1\mt5_phase1_latest.json')
out = Path(r'C:\Users\anmar\.openclaw\workspace-mt5\tmp\latest_phase1_discord_message.txt')
o = json.loads(src.read_text(encoding='utf-8'))
e = o.get('execution', {}) or {}
p = o.get('plan', {}) or {}
bias = p.get('bias', {}) or {}
ord = p.get('orderability_decision', {}) or {}
risk = p.get('risk_plan', {}) or {}
preview = p.get('trade_ticket_preview', {}) or {}
pre = e.get('preflight', {}) or {}
parts = []
parts.append('MT5 Phase1 trade report')
parts.append('')
parts.append(f"Candidate: {o.get('candidate')}")
parts.append(f"Setup: {bias.get('setup')}")
parts.append(f"Orderability: {ord.get('decision')}")
parts.append(f"Execution template: {ord.get('execution_template')}")
parts.append('')
parts.append('Trade package:')
parts.append(f"- symbol: {preview.get('mt5_execution_symbol')}")
parts.append(f"- side: {preview.get('side')}")
parts.append(f"- order_plan: {preview.get('order_plan')}")
parts.append(f"- entry: {preview.get('entry')}")
parts.append(f"- SL: {preview.get('sl')}")
parts.append(f"- TP: {preview.get('tp_live')}")
parts.append(f"- lots: {preview.get('volume_lots')}")
parts.append(f"- modeled risk: {risk.get('total_risk_usdt')} USD")
parts.append(f"- modeled margin: {risk.get('total_margin_usdt')} USD")
parts.append('')
parts.append('Execution:')
parts.append(f"- status: {e.get('status')}")
parts.append(f"- retcode: {e.get('retcode')} ({e.get('retcode_text')})")
parts.append(f"- message: {e.get('message')}")
if e.get('mt5_order_ids'):
    parts.append(f"- mt5_order_ids: {e.get('mt5_order_ids')}")
if pre:
    parts.append('')
    parts.append(f"Preflight: valid_entries={pre.get('valid_entries')} / original_entries={pre.get('original_entries')} / adjusted_order_plan={pre.get('adjusted_order_plan')}")
    for item in (pre.get('rejected_entries') or [])[:5]:
        parts.append(f"- rejected {item.get('client_entry_id')}: {'; '.join(item.get('reasons') or [])}")
out.write_text('\n'.join(parts) + '\n', encoding='utf-8')
