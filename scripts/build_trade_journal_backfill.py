#!/usr/bin/env python3
from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

WORKSPACE = Path(__file__).resolve().parents[1]
REPORTS = WORKSPACE / 'reports' / 'mt5_autotrade_phase1'
SHADOW = REPORTS / 'llm_shadow'
OUT = REPORTS / 'trade_journal_backfill.json'
CONFIG = WORKSPACE / 'config' / 'mt5_fx_autotrade_phase1.json'

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

MT5_ORDER_STATE_PLACED = 1
MT5_ORDER_STATE_CANCELED = 2
MT5_ORDER_STATE_PARTIAL = 3
MT5_ORDER_STATE_FILLED = 4
MT5_ORDER_STATE_REJECTED = 5
MT5_ORDER_STATE_EXPIRED = 6
MT5_ORDER_STATE_REQUEST_CANCEL = 9

MT5_DEAL_ENTRY_IN = 0
MT5_DEAL_ENTRY_OUT = 1
MT5_DEAL_ENTRY_INOUT = 2
MT5_DEAL_ENTRY_OUT_BY = 3


@dataclass
class MT5OrderSnapshot:
    order_id: int
    open_order: dict[str, Any] | None
    hist_order: dict[str, Any] | None
    open_position: dict[str, Any] | None
    entry_deals: list[dict[str, Any]]
    exit_deals: list[dict[str, Any]]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding='utf-8-sig'))


def safe(v: Any) -> Any:
    if v is None:
        return ''
    return v


def safe_float(v: Any) -> float | None:
    try:
        if v in (None, '', '—'):
            return None
        return float(v)
    except Exception:
        return None


def load_config() -> dict[str, Any]:
    if not CONFIG.exists():
        return {}
    try:
        return load_json(CONFIG)
    except Exception:
        return {}


def iso_utc_naive(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(tzinfo=None, microsecond=0).isoformat()


def parse_dt(value: Any) -> datetime | None:
    if value in (None, ''):
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value), tz=timezone.utc)
    text = str(value).strip()
    if not text:
        return None
    try:
        if text.endswith('Z'):
            return datetime.fromisoformat(text.replace('Z', '+00:00')).astimezone(timezone.utc)
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def unix_to_iso_utc(value: Any) -> str:
    dt = parse_dt(value)
    return iso_utc_naive(dt) if dt else ''


def first_dt(values: list[Any]) -> str:
    dts = [parse_dt(v) for v in values if parse_dt(v)]
    if not dts:
        return ''
    return iso_utc_naive(min(dts))


def last_dt(values: list[Any]) -> str:
    dts = [parse_dt(v) for v in values if parse_dt(v)]
    if not dts:
        return ''
    return iso_utc_naive(max(dts))


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
            out = {
                'candidate_rank': idx,
                'symbol': raw.get('Symbol') or candidate,
                'watchlist': d.get('watchlist'),
                'indicator': d.get('indicator'),
                'report_generated_at_utc': d.get('generatedAt'),
            }
            out.update(raw)
            return out
    return {
        'symbol': candidate or '',
        'watchlist': d.get('watchlist'),
        'indicator': d.get('indicator'),
        'report_generated_at_utc': d.get('generatedAt'),
    }


def planner_text_without_json(path: Path) -> str:
    if not path.exists():
        return ''
    text = path.read_text(encoding='utf-8-sig')
    start = text.find('```json')
    if start != -1:
        text = text[:start].rstrip()
    return text


def normalize_order_type(side: str | None, entry_type: str | None, fallback: str | None = None) -> str:
    if fallback:
        return str(fallback)
    side_v = str(side or '').strip().upper()
    entry_v = str(entry_type or '').strip().upper()
    if not side_v and not entry_v:
        return ''
    if entry_v == 'LIMIT':
        return f'{side_v}_LIMIT' if side_v else 'LIMIT'
    if entry_v == 'STOP':
        return f'{side_v}_STOP' if side_v else 'STOP'
    if entry_v == 'MARKET':
        return f'{side_v}_MARKET' if side_v else 'MARKET'
    if side_v and entry_v:
        return f'{side_v}_{entry_v}'
    return side_v or entry_v


def compute_units(lots: Any, contract_size: Any) -> int | str:
    lots_v = safe_float(lots)
    contract_v = safe_float(contract_size)
    if lots_v is None or contract_v is None:
        return ''
    return int(round(lots_v * contract_v))


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
        'opened_at_utc': execution.get('legs', [{}])[0].get('execution', {}).get('timestamp') or execution.get('legs', [{}])[0].get('execution', {}).get('received_at') or execution.get('timestamp') or '',
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
        'result_class': 'open' if execution.get('status') in {'accepted', 'partial'} else execution.get('status'),
        'review_status': 'pending',
        'note': execution.get('message'),
    })

    leg_rows: list[dict[str, Any]] = []
    planner_legs = list((planner.get('trade_plan_ticket') or {}).get('legs') or [])
    for idx, leg in enumerate(execution.get('legs') or [], start=1):
        ex = leg.get('execution') or {}
        plan_leg = planner_legs[idx - 1] if idx - 1 < len(planner_legs) else {}
        trailing = leg.get('trailing') or plan_leg.get('trailing') or {}
        leg_rows.append({
            'trade_group_id': trade_group_id,
            'leg_id': leg.get('ticket_id'),
            'leg_index': leg.get('leg_index') or idx,
            'mt5_order_id': ','.join(str(x) for x in (ex.get('mt5_order_ids') or [])),
            'ticket_id': leg.get('ticket_id'),
            'symbol': result.get('candidate'),
            'side': primary.get('bias'),
            'order_type': leg.get('order_type') or plan_leg.get('order_type') or '',
            'entry_price_planned': leg.get('entry_price') if leg.get('entry_price') not in (None, '') else plan_leg.get('entry_price'),
            'entry_price_filled': '',
            'stop_loss_planned': leg.get('stop_loss_price') if leg.get('stop_loss_price') not in (None, '') else plan_leg.get('stop_loss_price'),
            'take_profit_planned': leg.get('take_profit_price') if leg.get('take_profit_price') not in (None, '') else plan_leg.get('take_profit_price'),
            'trailing_enabled': trailing.get('enabled') if isinstance(trailing, dict) else '',
            'trailing_trigger': trailing.get('trigger_price') if isinstance(trailing, dict) else '',
            'trailing_mode': trailing.get('distance_mode') if isinstance(trailing, dict) else '',
            'trailing_distance': trailing.get('distance_value') if isinstance(trailing, dict) else '',
            'trailing_step_price': trailing.get('step_price') if isinstance(trailing, dict) else '',
            'lots': leg.get('lots') if leg.get('lots') not in (None, '') else plan_leg.get('lots'),
            'units_estimate': leg.get('units_estimate') if leg.get('units_estimate') not in (None, '') else plan_leg.get('units_estimate'),
            'notional_usd_estimate': leg.get('notional_usd_estimate') if leg.get('notional_usd_estimate') not in (None, '') else plan_leg.get('notional_usd_estimate'),
            'planned_risk_usd': plan_leg.get('effective_loss_at_stop_usd') or plan_leg.get('estimated_loss_at_stop_usd') or '',
            'realized_pnl_usd': '',
            'realized_r': '',
            'status': ex.get('status'),
            'opened_at_utc': ex.get('timestamp') or '',
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


def build_script_leg_rows(result: dict[str, Any], trade_group_id: str) -> list[dict[str, Any]]:
    execution = result.get('execution') or {}
    plan = result.get('plan') or {}
    risk = plan.get('risk_plan') or {}
    ticket_path = Path(result.get('ticket_path')) if result.get('ticket_path') else None
    ticket = load_json(ticket_path) if ticket_path and ticket_path.exists() else {}
    entries = list(ticket.get('entries') or [])
    mt5_order_ids = list(execution.get('mt5_order_ids') or [])
    contract_size = safe_float(risk.get('contract_size')) or 100000.0
    quote_to_usd = safe_float(risk.get('quote_to_usd')) or 1.0
    stop_loss = safe_float((ticket.get('stop_loss') or {}).get('price'))
    take_profit = safe_float((ticket.get('take_profit') or {}).get('price'))
    side = str(execution.get('side') or (plan.get('trade_ticket_preview') or {}).get('side') or '').upper()
    trailing = ticket.get('trailing') or {}

    leg_rows: list[dict[str, Any]] = []
    for idx, entry in enumerate(entries, start=1):
        lots = safe_float(entry.get('volume_lots'))
        entry_price = safe_float(entry.get('price'))
        units = compute_units(lots, contract_size)
        notional = ''
        planned_risk = ''
        if isinstance(units, int) and entry_price is not None:
            notional = round(units * entry_price * quote_to_usd, 2)
            if stop_loss is not None:
                planned_risk = round(units * abs(entry_price - stop_loss) * quote_to_usd, 2)
        leg_id = str(entry.get('client_entry_id') or f'{trade_group_id}-leg{idx}')
        leg_rows.append({
            'trade_group_id': trade_group_id,
            'leg_id': leg_id,
            'leg_index': idx,
            'mt5_order_id': str(mt5_order_ids[idx - 1]) if idx - 1 < len(mt5_order_ids) else '',
            'ticket_id': leg_id,
            'symbol': result.get('candidate'),
            'side': side,
            'order_type': normalize_order_type(side, entry.get('entry_type'), None),
            'entry_price_planned': entry_price if entry_price is not None else '',
            'entry_price_filled': '',
            'stop_loss_planned': stop_loss if stop_loss is not None else '',
            'take_profit_planned': take_profit if take_profit is not None else '',
            'trailing_enabled': trailing.get('enabled') if isinstance(trailing, dict) else '',
            'trailing_trigger': trailing.get('trigger_price') if isinstance(trailing, dict) else '',
            'trailing_mode': trailing.get('distance_mode') if isinstance(trailing, dict) else '',
            'trailing_distance': trailing.get('distance_value') if isinstance(trailing, dict) else '',
            'trailing_step_price': trailing.get('step_price') if isinstance(trailing, dict) else '',
            'lots': lots if lots is not None else '',
            'units_estimate': units,
            'notional_usd_estimate': notional,
            'planned_risk_usd': planned_risk,
            'realized_pnl_usd': '',
            'realized_r': '',
            'status': execution.get('status'),
            'opened_at_utc': execution.get('timestamp') or ticket.get('created_at') or '',
            'closed_at_utc': '',
            'broker_retcode': execution.get('retcode'),
            'broker_message': execution.get('message'),
            'parent_group_id': trade_group_id,
        })
    return leg_rows


def build_script_group_row(result: dict[str, Any], path: Path) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    execution = result.get('execution') or {}
    plan = result.get('plan') or {}
    bias = plan.get('bias') or {}
    risk = plan.get('risk_plan') or {}
    ordy = plan.get('orderability_decision') or {}
    snap = parse_report_candidate(result.get('report_path'), result.get('candidate'))
    trade_group_id = path.stem
    leg_rows = build_script_leg_rows(result, trade_group_id)
    row = {h: '' for h in TRADE_GROUP_HEADERS}
    row.update({
        'trade_group_id': trade_group_id,
        'cycle_id': result.get('session_key') or path.stem,
        'opened_at_utc': execution.get('timestamp') or '',
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
        'filled_legs': len(leg_rows),
        'closed_legs': 0,
        'cancelled_legs': 0,
        'result_class': 'open' if execution.get('status') == 'accepted' else execution.get('status'),
        'review_status': 'pending',
        'note': execution.get('message'),
    })
    review = {h: '' for h in REVIEW_HEADERS}
    review['trade_group_id'] = trade_group_id
    review['review_date_utc'] = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    return row, leg_rows, snap, review


def choose_mt5_terminal() -> str:
    cfg = load_config()
    analysis = cfg.get('analysisDataSource') or {}
    terminal = str(analysis.get('terminalExe') or '').strip()
    return terminal


def unique_deals(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[int] = set()
    out: list[dict[str, Any]] = []
    for row in rows:
        try:
            ticket = int(row.get('ticket'))
        except Exception:
            ticket = -1
        if ticket in seen:
            continue
        seen.add(ticket)
        out.append(row)
    out.sort(key=lambda d: (int(d.get('time_msc') or 0), int(d.get('ticket') or 0)))
    return out


def load_mt5_snapshots(order_ids: list[int], since_hints: list[str]) -> dict[int, MT5OrderSnapshot]:
    if not order_ids:
        return {}
    terminal = choose_mt5_terminal()
    if not terminal or not Path(terminal).exists():
        return {}
    try:
        import MetaTrader5 as mt5
    except Exception:
        return {}

    parsed_hints = [parse_dt(v) for v in since_hints if parse_dt(v)]
    start = min(parsed_hints) - timedelta(days=45) if parsed_hints else datetime.now(timezone.utc) - timedelta(days=60)
    end = datetime.now(timezone.utc) + timedelta(days=1)

    if not mt5.initialize(path=terminal):
        return {}
    try:
        open_orders = {int(o.ticket): o._asdict() for o in (mt5.orders_get() or [])}
        open_positions = {int(p.ticket): p._asdict() for p in (mt5.positions_get() or [])}
        hist_orders_rows = [o._asdict() for o in (mt5.history_orders_get(start, end) or [])]
        hist_deals_rows = [d._asdict() for d in (mt5.history_deals_get(start, end) or [])]
    finally:
        try:
            mt5.shutdown()
        except Exception:
            pass

    hist_orders = {int(row.get('ticket')): row for row in hist_orders_rows if row.get('ticket') is not None}
    deals_by_order: dict[int, list[dict[str, Any]]] = defaultdict(list)
    deals_by_position: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in hist_deals_rows:
        order = int(row.get('order') or 0)
        position_id = int(row.get('position_id') or 0)
        if order:
            deals_by_order[order].append(row)
        if position_id:
            deals_by_position[position_id].append(row)

    out: dict[int, MT5OrderSnapshot] = {}
    for order_id in sorted(set(order_ids)):
        open_order = open_orders.get(order_id)
        hist_order = hist_orders.get(order_id)
        position_id = 0
        for src in (open_order, hist_order):
            if src:
                position_id = int(src.get('position_id') or 0)
                if position_id:
                    break
        open_position = open_positions.get(position_id or order_id)
        deals = list(deals_by_order.get(order_id) or [])
        if position_id:
            deals.extend(deals_by_position.get(position_id) or [])
        deals = unique_deals(deals)
        entry_deals = [d for d in deals if int(d.get('entry') or -1) in {MT5_DEAL_ENTRY_IN, MT5_DEAL_ENTRY_INOUT}]
        exit_deals = [d for d in deals if int(d.get('entry') or -1) in {MT5_DEAL_ENTRY_OUT, MT5_DEAL_ENTRY_OUT_BY}]
        out[order_id] = MT5OrderSnapshot(
            order_id=order_id,
            open_order=open_order,
            hist_order=hist_order,
            open_position=open_position,
            entry_deals=entry_deals,
            exit_deals=exit_deals,
        )
    return out


def snapshot_terminal_state(snapshot: MT5OrderSnapshot) -> str:
    hist_state = int((snapshot.hist_order or {}).get('state') or -1)
    if snapshot.open_order:
        return 'accepted'
    if snapshot.open_position:
        return 'partial' if snapshot.exit_deals else 'filled'
    if snapshot.entry_deals and snapshot.exit_deals:
        return 'closed'
    if hist_state == MT5_ORDER_STATE_FILLED and snapshot.entry_deals:
        return 'closed' if snapshot.exit_deals else 'filled'
    if hist_state in {MT5_ORDER_STATE_CANCELED, MT5_ORDER_STATE_REQUEST_CANCEL}:
        return 'cancelled'
    if hist_state == MT5_ORDER_STATE_REJECTED:
        return 'rejected'
    if hist_state == MT5_ORDER_STATE_EXPIRED:
        return 'expired'
    if snapshot.entry_deals:
        return 'filled'
    return 'accepted'


def snapshot_opened_at(snapshot: MT5OrderSnapshot) -> str:
    if snapshot.entry_deals:
        return unix_to_iso_utc(snapshot.entry_deals[0].get('time'))
    if snapshot.open_order:
        return unix_to_iso_utc(snapshot.open_order.get('time_setup'))
    if snapshot.hist_order:
        return unix_to_iso_utc(snapshot.hist_order.get('time_setup'))
    return ''


def snapshot_closed_at(snapshot: MT5OrderSnapshot, status: str) -> str:
    if status == 'closed' and snapshot.exit_deals:
        return unix_to_iso_utc(snapshot.exit_deals[-1].get('time'))
    if status in {'cancelled', 'rejected', 'expired'} and snapshot.hist_order:
        return unix_to_iso_utc(snapshot.hist_order.get('time_done'))
    return ''


def snapshot_entry_price(snapshot: MT5OrderSnapshot) -> float | str:
    if not snapshot.entry_deals:
        return ''
    total_volume = sum(float(d.get('volume') or 0) for d in snapshot.entry_deals)
    if total_volume <= 0:
        return ''
    weighted = sum(float(d.get('price') or 0) * float(d.get('volume') or 0) for d in snapshot.entry_deals) / total_volume
    return round(weighted, 8)


def snapshot_realized_pnl(snapshot: MT5OrderSnapshot) -> float | str:
    if not snapshot.exit_deals:
        return ''
    total = 0.0
    for deal in snapshot.exit_deals:
        total += float(deal.get('profit') or 0)
        total += float(deal.get('commission') or 0)
        total += float(deal.get('swap') or 0)
        total += float(deal.get('fee') or 0)
    return round(total, 2)


def reconcile_leg_row(row: dict[str, Any], snapshots: dict[int, MT5OrderSnapshot]) -> dict[str, Any]:
    order_ids = []
    for part in str(row.get('mt5_order_id') or '').split(','):
        part = part.strip()
        if not part:
            continue
        try:
            order_ids.append(int(part))
        except Exception:
            continue
    if not order_ids:
        row['_is_filled'] = False
        return row

    relevant = [snapshots[oid] for oid in order_ids if oid in snapshots]
    if not relevant:
        row['_is_filled'] = False
        return row

    statuses = [snapshot_terminal_state(s) for s in relevant]
    has_accepted = any(s == 'accepted' for s in statuses)
    has_filled = any(s == 'filled' for s in statuses)
    has_partial = any(s == 'partial' for s in statuses)
    has_closed = any(s == 'closed' for s in statuses)
    has_cancelled = any(s in {'cancelled', 'rejected', 'expired'} for s in statuses)
    terminal_only = all(s in {'closed', 'cancelled', 'rejected', 'expired'} for s in statuses)

    if has_accepted:
        final_status = 'accepted'
    elif has_partial:
        final_status = 'partial'
    elif has_filled:
        final_status = 'filled'
    elif terminal_only and has_closed:
        final_status = 'closed'
    elif terminal_only and has_cancelled:
        if all(s == 'cancelled' for s in statuses):
            final_status = 'cancelled'
        elif all(s == 'rejected' for s in statuses):
            final_status = 'rejected'
        elif all(s == 'expired' for s in statuses):
            final_status = 'expired'
        else:
            final_status = 'cancelled'
    else:
        final_status = row.get('status') or 'accepted'

    entry_prices = [snapshot_entry_price(s) for s in relevant if snapshot_entry_price(s) != '']
    if entry_prices:
        if len(entry_prices) == 1:
            row['entry_price_filled'] = entry_prices[0]
        else:
            row['entry_price_filled'] = round(sum(float(x) for x in entry_prices) / len(entry_prices), 8)

    opened_candidates = [row.get('opened_at_utc')]
    opened_candidates.extend(snapshot_opened_at(s) for s in relevant)
    row['opened_at_utc'] = first_dt(opened_candidates) or row.get('opened_at_utc') or ''

    if final_status in {'closed', 'cancelled', 'rejected', 'expired'}:
        row['closed_at_utc'] = last_dt([snapshot_closed_at(s, snapshot_terminal_state(s)) for s in relevant])

    realized_values = [snapshot_realized_pnl(s) for s in relevant if snapshot_realized_pnl(s) != '']
    if realized_values:
        realized_total = round(sum(float(v) for v in realized_values), 2)
        row['realized_pnl_usd'] = realized_total
        planned_risk = safe_float(row.get('planned_risk_usd'))
        if planned_risk and planned_risk != 0:
            row['realized_r'] = round(realized_total / planned_risk, 4)

    row['status'] = final_status
    row['_is_filled'] = any(snapshot.entry_deals or snapshot.open_position or snapshot.exit_deals for snapshot in relevant)
    return row


def reconcile_trade_groups(trade_groups: list[dict[str, Any]], legs: list[dict[str, Any]]) -> None:
    if not legs:
        return
    order_ids: list[int] = []
    since_hints: list[str] = []
    for leg in legs:
        since_hints.append(str(leg.get('opened_at_utc') or ''))
        for part in str(leg.get('mt5_order_id') or '').split(','):
            part = part.strip()
            if not part:
                continue
            try:
                order_ids.append(int(part))
            except Exception:
                continue
    snapshots = load_mt5_snapshots(order_ids, since_hints)
    if snapshots:
        for leg in legs:
            reconcile_leg_row(leg, snapshots)

    legs_by_group: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for leg in legs:
        legs_by_group[str(leg.get('trade_group_id') or '')].append(leg)

    for row in trade_groups:
        group_legs = legs_by_group.get(str(row.get('trade_group_id') or ''), [])
        if not group_legs:
            continue
        statuses = [str(leg.get('status') or '') for leg in group_legs]
        filled_legs = sum(1 for leg in group_legs if bool(leg.get('_is_filled')))
        closed_legs = sum(1 for s in statuses if s == 'closed')
        cancelled_legs = sum(1 for s in statuses if s in {'cancelled', 'rejected', 'expired'})
        realized_total = round(sum(float(leg.get('realized_pnl_usd') or 0) for leg in group_legs), 2)
        opened_at = first_dt([row.get('opened_at_utc')] + [leg.get('opened_at_utc') for leg in group_legs])
        terminal_only = all(s in {'closed', 'cancelled', 'rejected', 'expired'} for s in statuses)

        row['opened_at_utc'] = opened_at or row.get('opened_at_utc') or ''
        row['filled_legs'] = filled_legs
        row['closed_legs'] = closed_legs
        row['cancelled_legs'] = cancelled_legs
        row['realized_pnl_usd'] = realized_total if (realized_total or closed_legs) else ''

        planned_total_risk = safe_float(row.get('planned_total_risk_usd'))
        if row.get('realized_pnl_usd') not in ('', None) and planned_total_risk and planned_total_risk != 0:
            row['realized_r_multiple'] = round(float(row['realized_pnl_usd']) / planned_total_risk, 4)

        if terminal_only:
            row['closed_at_utc'] = last_dt([leg.get('closed_at_utc') for leg in group_legs])
            if filled_legs > 0:
                row['status'] = 'closed'
                if realized_total > 0:
                    row['result_class'] = 'win'
                elif realized_total < 0:
                    row['result_class'] = 'loss'
                else:
                    row['result_class'] = 'flat'
            elif cancelled_legs == len(group_legs):
                row['status'] = 'cancelled'
                row['result_class'] = 'cancelled'
        else:
            if any(s == 'partial' for s in statuses):
                row['status'] = 'partial'
            elif any(s == 'filled' for s in statuses):
                row['status'] = 'filled'
            elif any(s == 'accepted' for s in statuses):
                row['status'] = 'accepted'
            row['result_class'] = 'open'

    for leg in legs:
        leg.pop('_is_filled', None)


def build_daily_equity(trade_groups: list[dict[str, Any]]) -> list[list[Any]]:
    daily_map: dict[str, dict[str, Any]] = defaultdict(lambda: {
        'realized_pnl_usd': 0.0,
        'closed_trade_groups': 0,
        'closed_legs': 0,
        'wins': 0,
    })
    for row in trade_groups:
        closed_at = row.get('closed_at_utc')
        if not closed_at:
            continue
        day = str(closed_at)[:10]
        daily_map[day]['closed_trade_groups'] += 1
        daily_map[day]['closed_legs'] += int(safe_float(row.get('closed_legs')) or 0)
        daily_map[day]['realized_pnl_usd'] += float(safe_float(row.get('realized_pnl_usd')) or 0)
        if str(row.get('result_class') or '') == 'win':
            daily_map[day]['wins'] += 1

    daily_equity = [DAILY_HEADERS]
    for day in sorted(daily_map):
        item = daily_map[day]
        closed_trade_groups = int(item['closed_trade_groups'])
        win_rate = round(item['wins'] / closed_trade_groups, 4) if closed_trade_groups else ''
        daily_equity.append([
            day,
            '',
            '',
            round(item['realized_pnl_usd'], 2),
            '',
            closed_trade_groups,
            int(item['closed_legs']),
            win_rate,
            '',
            '',
        ])
    return daily_equity


def main() -> int:
    trade_group_rows: list[dict[str, Any]] = []
    leg_rows: list[dict[str, Any]] = []
    review_rows: list[dict[str, Any]] = []
    screener_rows: list[dict[str, Any]] = []

    for path in sorted(REPORTS.glob('mt5_phase1_llm_live_*.json')):
        if path.name.endswith('latest.json'):
            continue
        try:
            d = load_json(path)
        except Exception:
            continue
        row, legs, snap, review = build_llm_group_rows(d, path)
        trade_group_rows.append(row)
        leg_rows.extend(legs)
        if snap:
            screener_rows.append({'trade_group_id': row['trade_group_id'], **snap})
        review_rows.append(review)

    existing_cycles = {str(r.get('cycle_id') or '') for r in trade_group_rows}
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
        row, legs, snap, review = build_script_group_row(d, path)
        trade_group_rows.append(row)
        leg_rows.extend(legs)
        if snap:
            screener_rows.append({'trade_group_id': row['trade_group_id'], **snap})
        review_rows.append(review)

    reconcile_trade_groups(trade_group_rows, leg_rows)

    trade_groups: list[list[Any]] = [TRADE_GROUP_HEADERS]
    for row in trade_group_rows:
        trade_groups.append([safe(row.get(h)) for h in TRADE_GROUP_HEADERS])

    legs: list[list[Any]] = [LEGS_HEADERS]
    for row in leg_rows:
        legs.append([safe(row.get(h)) for h in LEGS_HEADERS])

    reviews: list[list[Any]] = [REVIEW_HEADERS]
    for row in review_rows:
        reviews.append([safe(row.get(h)) for h in REVIEW_HEADERS])

    screener_headers = ['trade_group_id','symbol','watchlist','indicator','report_generated_at_utc',
                        '01 Signal Dir','02 Best Setup Code','03 Best Score','04 Final Long Score','05 Final Short Score','06 Long Continuation','07 Short Continuation','08 Long MeanRev','09 Short MeanRev','10 Conviction State','11 Trend Dir','12 Macro Dir 1D','13 Position State','14 Breakout Dir','15 Retest Dir','16 ADX','17 Rel Volume','18 Dist Fast EMA ATR','19 Sweep Dir','20 Displacement Dir','21 PD State','22 FVG State','23 Tactical Trend Score','24 Tactical Breakout Score','25 Tactical MeanRev Score','26 Fresh Struct Shift','27 Verdict State','28 Momentum State','29 Signed Conviction','30 Break Fresh State','31 Retest Stage','32 Short MR Struct','33 Dist To Resistance %','34 Zone Count','35 EMA Trend State','36 VWAP20','37 Dist To Support %','38 Lifecycle Long Score','39 R1 Above','40 R2 Above','41 S1 Below','42 S2 Below','43 Cnt Res Above','44 Cnt Sup Below','45 Cnt Res All','46 Cnt Sup All','47 Lifecycle Short Score','48 Winner Dir','49 Winner Family Code','50 Winner Margin','51 Winner Base Score','52 Winner Penalty','53 Winner Tactical','54 Winner Macro','55 Winner Structure','56 Winner ADX Fit','57 Winner Lifecycle','58 Winner Context Boost','59 Winner Family Edge']
    screener_data = [screener_headers]
    for row in screener_rows:
        screener_data.append([safe(row.get(h)) for h in screener_headers])

    daily_equity = build_daily_equity(trade_group_rows)

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
