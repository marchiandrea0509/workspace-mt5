#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WORKSPACE = Path(__file__).resolve().parents[1]
REPORTS = WORKSPACE / 'reports' / 'mt5_autotrade_phase1'
SHADOW = REPORTS / 'llm_shadow'
OUT = REPORTS / 'trade_journal_backfill.json'

TRADE_GROUP_HEADERS = [
    'trade_group_id','cycle_id','opened_at_utc','closed_at_utc','status','symbol','watchlist','timeframe','screener_version','report_generated_at_utc','report_path','candidate_rank','winner_side','winner_family','setup_family_text','orderability','execution_style','plan_source','llm_confidence','deterministic_orderability','llm_orderability','planned_total_risk_usd','planned_total_margin_usd','realized_pnl_usd','realized_r_multiple','max_favorable_excursion_usd','max_adverse_excursion_usd','filled_legs','closed_legs','cancelled_legs','result_class','review_status','note'
]
LEGS_HEADERS = [
    'trade_group_id','leg_id','leg_index','mt5_order_id','ticket_id','symbol','side','order_type','entry_price_planned','entry_price_filled','stop_loss_planned','take_profit_planned','trailing_enabled','trailing_trigger','trailing_mode','trailing_distance','trailing_step_price','lots','units_estimate','notional_usd_estimate','planned_risk_usd','realized_pnl_usd','realized_r','status','opened_at_utc','closed_at_utc','broker_retcode','broker_message','parent_group_id'
]
REVIEW_HEADERS = [
    'trade_group_id','review_date_utc','llm_pre_trade_rationale','why_trade_made_sense','what_went_well','what_went_wrong','mistakes','lesson_learned','was_llm_better_than_script','was_script_better_than_llm','discrepancy_type','should_script_be_updated','update_priority','confidence_in_lesson','free_text_review'
]
DAILY_HEADERS = [
    'date','starting_balance','ending_balance','realized_pnl_usd','open_pnl_usd','closed_trade_groups','closed_legs','win_rate_day','cumulative_drawdown_usd','cumulative_drawdown_pct'
]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding='utf-8-sig'))


def safe(v: Any) -> Any:
    if v is None:
        return ''
    return v


def list_json(pattern: str) -> list[Path]:
    return sorted(REPORTS.glob(pattern), key=lambda p: p.stat().st_mtime)


def parse_report_candidate(report_path: str | None, candidate: str | None) -> dict[str, Any]:
    if not report_path or not candidate:
        return {}
    p = Path(report_path)
    if not p.exists():
        return {}
    try:
        d = load_json(p)
    except Exception:
        return {}
    rows = d.get('top10') or d.get('top5') or []
    for idx, item in enumerate(rows, start=1):
        raw = item.get('raw') or item
        if str(raw.get('Symbol') or '').upper() == str(candidate).upper():
            out = {'candidate_rank': idx, 'watchlist': d.get('watchlist'), 'indicator': d.get('indicator'), 'report_generated_at_utc': d.get('generatedAt')}
            out.update(raw)
            return out
    return {'watchlist': d.get('watchlist'), 'indicator': d.get('indicator'), 'report_generated_at_utc': d.get('generatedAt')}


def planner_text_without_json(path: Path) -> str:
    if not path.exists():
        return ''
    text = path.read_text(encoding='utf-8-sig')
    start = text.find('```json')
    if start != -1:
        text = text[:start].rstrip()
    return text


def build_llm_group_rows(result: dict[str, Any], path: Path) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    execution = result.get('execution') or {}
    planner = result.get('planner_plan') or {}
    primary = planner.get('primary_plan') or {}
    risk = planner.get('risk_sizing') or {}
    finalv = planner.get('final_verdict') or {}
    pack = load_json(Path(result['pack_path'])) if result.get('pack_path') and Path(result['pack_path']).exists() else {}
    snap = parse_report_candidate(result.get('report_path'), result.get('candidate'))
    comparison = load_json(Path(result['comparison_path'])) if result.get('comparison_path') and Path(result['comparison_path']).exists() else {}
    analysis_path = Path(result['analysis_path']) if result.get('analysis_path') else None

    trade_group_id = result.get('ticket_group_id') or path.stem
    row = {h: '' for h in TRADE_GROUP_HEADERS}
    row.update({
        'trade_group_id': trade_group_id,
        'cycle_id': result.get('session_key') or path.stem,
        'opened_at_utc': execution.get('legs', [{}])[0].get('execution', {}).get('received_at') or '',
        'closed_at_utc': '',
        'status': execution.get('status'),
        'symbol': result.get('candidate'),
        'watchlist': snap.get('watchlist') or ((pack.get('report_source') or {}).get('watchlist')),
        'timeframe': ((pack.get('report_source') or {}).get('timeframe')) or '',
        'screener_version': snap.get('indicator') or ((pack.get('report_source') or {}).get('indicator')),
        'report_generated_at_utc': snap.get('report_generated_at_utc') or ((pack.get('report_source') or {}).get('generated_at')),
        'report_path': result.get('report_path'),
        'candidate_rank': snap.get('candidate_rank'),
        'winner_side': (planner.get('screener_read') or {}).get('winner_side'),
        'winner_family': (planner.get('screener_read') or {}).get('winner_family'),
        'setup_family_text': primary.get('execution_style'),
        'orderability': (planner.get('orderability') or {}).get('classification'),
        'execution_style': primary.get('execution_style'),
        'plan_source': 'LLM',
        'llm_confidence': finalv.get('confidence'),
        'deterministic_orderability': (comparison.get('script') or {}).get('orderability'),
        'llm_orderability': (comparison.get('llm') or {}).get('orderability'),
        'planned_total_risk_usd': risk.get('total_risk_usd'),
        'planned_total_margin_usd': risk.get('total_margin_usd_estimate'),
        'realized_pnl_usd': '',
        'realized_r_multiple': '',
        'max_favorable_excursion_usd': '',
        'max_adverse_excursion_usd': '',
        'filled_legs': len(execution.get('legs') or []),
        'closed_legs': 0,
        'cancelled_legs': 0,
        'result_class': 'open' if execution.get('status') in {'accepted','partial'} else execution.get('status'),
        'review_status': 'pending',
        'note': execution.get('message'),
    })

    leg_rows: list[dict[str, Any]] = []
    for leg in execution.get('legs') or []:
        ex = leg.get('execution') or {}
        leg_rows.append({
            'trade_group_id': trade_group_id,
            'leg_id': leg.get('ticket_id'),
            'leg_index': leg.get('leg_index'),
            'mt5_order_id': ','.join(str(x) for x in (ex.get('mt5_order_ids') or [])),
            'ticket_id': leg.get('ticket_id'),
            'symbol': result.get('candidate'),
            'side': primary.get('bias'),
            'order_type': leg.get('order_type') or '',
            'entry_price_planned': leg.get('entry_price'),
            'entry_price_filled': '',
            'stop_loss_planned': leg.get('stop_loss_price'),
            'take_profit_planned': leg.get('take_profit_price'),
            'trailing_enabled': '',
            'trailing_trigger': '',
            'trailing_mode': '',
            'trailing_distance': '',
            'trailing_step_price': '',
            'lots': leg.get('lots'),
            'units_estimate': '',
            'notional_usd_estimate': '',
            'planned_risk_usd': '',
            'realized_pnl_usd': '',
            'realized_r': '',
            'status': ex.get('status'),
            'opened_at_utc': '',
            'closed_at_utc': '',
            'broker_retcode': ex.get('retcode'),
            'broker_message': ex.get('message'),
            'parent_group_id': trade_group_id,
        })

    review = {h: '' for h in REVIEW_HEADERS}
    review.update({
        'trade_group_id': trade_group_id,
        'review_date_utc': datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),
        'llm_pre_trade_rationale': planner_text_without_json(analysis_path) if analysis_path else '',
        'why_trade_made_sense': (planner.get('screener_read') or {}).get('dashboard_summary'),
        'what_went_well': 'Trade was selected and emitted successfully.' if execution.get('status') in {'accepted','partial'} else '',
        'what_went_wrong': '',
        'mistakes': '',
        'lesson_learned': '',
        'was_llm_better_than_script': '',
        'was_script_better_than_llm': '',
        'discrepancy_type': '',
        'should_script_be_updated': '',
        'update_priority': '',
        'confidence_in_lesson': '',
        'free_text_review': '',
    })
    return row, leg_rows, snap, review


def build_script_group_row(result: dict[str, Any], path: Path) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    execution = result.get('execution') or {}
    plan = result.get('plan') or {}
    bias = plan.get('bias') or {}
    risk = plan.get('risk_plan') or {}
    ordy = plan.get('orderability_decision') or {}
    snap = parse_report_candidate(result.get('report_path'), result.get('candidate'))
    trade_group_id = path.stem
    row = {h: '' for h in TRADE_GROUP_HEADERS}
    row.update({
        'trade_group_id': trade_group_id,
        'cycle_id': result.get('session_key') or path.stem,
        'opened_at_utc': '',
        'closed_at_utc': '',
        'status': execution.get('status'),
        'symbol': result.get('candidate'),
        'watchlist': snap.get('watchlist'),
        'timeframe': plan.get('source_context',{}).get('timeframe',''),
        'screener_version': snap.get('indicator'),
        'report_generated_at_utc': snap.get('report_generated_at_utc'),
        'report_path': result.get('report_path'),
        'candidate_rank': snap.get('candidate_rank'),
        'winner_side': bias.get('direction'),
        'winner_family': bias.get('setup'),
        'setup_family_text': bias.get('setup'),
        'orderability': ordy.get('decision'),
        'execution_style': ordy.get('execution_template'),
        'plan_source': 'SCRIPT',
        'deterministic_orderability': ordy.get('decision'),
        'planned_total_risk_usd': risk.get('total_risk_usdt'),
        'planned_total_margin_usd': risk.get('total_margin_usdt'),
        'filled_legs': len((plan.get('trade_ticket_preview') or {}).get('entries') or []),
        'result_class': 'open' if execution.get('status') == 'accepted' else execution.get('status'),
        'review_status': 'pending',
        'note': execution.get('message'),
    })
    review = {h: '' for h in REVIEW_HEADERS}
    review['trade_group_id'] = trade_group_id
    review['review_date_utc'] = datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
    return row, [], snap, review


def main() -> int:
    trade_groups: list[list[Any]] = [TRADE_GROUP_HEADERS]
    legs: list[list[Any]] = [LEGS_HEADERS]
    reviews: list[list[Any]] = [REVIEW_HEADERS]
    screener_rows: list[dict[str, Any]] = []

    # LLM live results first
    for path in sorted(REPORTS.glob('mt5_phase1_llm_live_*.json')):
        if path.name.endswith('latest.json'):
            continue
        try:
            d = load_json(path)
        except Exception:
            continue
        row, leg_rows, snap, review = build_llm_group_rows(d, path)
        trade_groups.append([safe(row.get(h)) for h in TRADE_GROUP_HEADERS])
        for lr in leg_rows:
            legs.append([safe(lr.get(h)) for h in LEGS_HEADERS])
        if snap:
            screener_rows.append({'trade_group_id': row['trade_group_id'], **snap})
        reviews.append([safe(review.get(h)) for h in REVIEW_HEADERS])

    # Historical deterministic accepted results not already represented
    existing_cycles = {r[1] for r in trade_groups[1:] if len(r) > 1}
    for path in sorted(REPORTS.glob('mt5_phase1_session_*.json')):
        try:
            d = load_json(path)
        except Exception:
            continue
        execution = d.get('execution') or {}
        if execution.get('status') != 'accepted':
            continue
        if (d.get('session_key') or path.stem) in existing_cycles:
            continue
        row, leg_rows, snap, review = build_script_group_row(d, path)
        trade_groups.append([safe(row.get(h)) for h in TRADE_GROUP_HEADERS])
        for lr in leg_rows:
            legs.append([safe(lr.get(h)) for h in LEGS_HEADERS])
        if snap:
            screener_rows.append({'trade_group_id': row['trade_group_id'], **snap})
        reviews.append([safe(review.get(h)) for h in REVIEW_HEADERS])

    # Screener snapshot headers
    screener_headers = ['trade_group_id','symbol','watchlist','indicator','report_generated_at_utc',
                        '01 Signal Dir','02 Best Setup Code','03 Best Score','04 Final Long Score','05 Final Short Score','06 Long Continuation','07 Short Continuation','08 Long MeanRev','09 Short MeanRev','10 Conviction State','11 Trend Dir','12 Macro Dir 1D','13 Position State','14 Breakout Dir','15 Retest Dir','16 ADX','17 Rel Volume','18 Dist Fast EMA ATR','19 Sweep Dir','20 Displacement Dir','21 PD State','22 FVG State','23 Tactical Trend Score','24 Tactical Breakout Score','25 Tactical MeanRev Score','26 Fresh Struct Shift','27 Verdict State','28 Momentum State','29 Signed Conviction','30 Break Fresh State','31 Retest Stage','32 Short MR Struct','33 Dist To Resistance %','34 Zone Count','35 EMA Trend State','36 VWAP20','37 Dist To Support %','38 Lifecycle Long Score','39 R1 Above','40 R2 Above','41 S1 Below','42 S2 Below','43 Cnt Res Above','44 Cnt Sup Below','45 Cnt Res All','46 Cnt Sup All','47 Lifecycle Short Score','48 Winner Dir','49 Winner Family Code','50 Winner Margin','51 Winner Base Score','52 Winner Penalty','53 Winner Tactical','54 Winner Macro','55 Winner Structure','56 Winner ADX Fit','57 Winner Lifecycle','58 Winner Context Boost','59 Winner Family Edge']
    screener_data = [screener_headers]
    for row in screener_rows:
        screener_data.append([safe(row.get(h)) for h in screener_headers])

    # Daily equity placeholder from trade groups dates
    daily_map: dict[str, dict[str, Any]] = defaultdict(lambda: {'closed_trade_groups':0,'closed_legs':0})
    for row in trade_groups[1:]:
        opened = row[2]
        if not opened:
            continue
        day = str(opened)[:10]
        daily_map[day]['closed_trade_groups'] += 1
    daily_equity = [DAILY_HEADERS]
    for day in sorted(daily_map):
        daily_equity.append([day,'','','','',daily_map[day]['closed_trade_groups'],daily_map[day]['closed_legs'],'','',''])

    payload = {
        'Trade_Groups': trade_groups,
        'Legs': legs,
        'Screener_Snapshot': screener_data,
        'LLM_Review': reviews,
        'Daily_Equity': daily_equity,
    }
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps({k: len(v)-1 for k,v in payload.items()}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
