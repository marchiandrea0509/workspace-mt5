import json
from pathlib import Path
phase = json.loads(Path(r'C:\Users\anmar\.openclaw\workspace-mt5\reports\mt5_autotrade_phase1\mt5_phase1_latest.json').read_text(encoding='utf-8'))
report = json.loads(Path(r'C:\Users\anmar\.openclaw\workspace\tradingview\reports\pine_screener\pine_screener_2026-04-03T15-24-49-309Z.json').read_text(encoding='utf-8'))
out = {
  'candidate': phase.get('candidate'),
  'audit': phase.get('audit'),
  'execution': phase.get('execution'),
  'bias': phase.get('plan',{}).get('bias'),
  'orderability': phase.get('plan',{}).get('orderability_decision'),
  'risk_plan': phase.get('plan',{}).get('risk_plan'),
  'key_levels': phase.get('plan',{}).get('key_levels'),
  'ticket_preview': phase.get('plan',{}).get('trade_ticket_preview'),
  'ticket_path': phase.get('ticket_path'),
  'top5': report.get('top5')
}
Path(r'C:\Users\anmar\.openclaw\workspace-mt5\tmp\latest_qs_dump.json').write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding='utf-8')
