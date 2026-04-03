#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import io
import json
import math
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WORKSPACE = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = WORKSPACE / 'config' / 'mt5_fx_autotrade_phase1.json'
EMIT_SCRIPT = WORKSPACE / 'scripts' / 'emit_mt5_bridge_ticket.py'


@dataclass
class Candidate:
    symbol: str
    description: str
    row: dict[str, Any]
    direction: str
    setup_label: str
    side: str


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding='utf-8'))


def save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def now_utc() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def iso_z(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')


def fmt_num(x: Any, nd: int = 2) -> str:
    if isinstance(x, (int, float)):
        return f'{x:,.{nd}f}'
    return 'n/a'


def safe_float(v: Any) -> float | None:
    try:
        if v in (None, '', '—'):
            return None
        return float(v)
    except Exception:
        return None


def floor_step(value: float, step: float) -> float:
    if step <= 0:
        return value
    return math.floor(value / step + 1e-12) * step


def latest_report(reports_dir: Path) -> Path:
    candidates = sorted(reports_dir.glob('pine_screener_*.json'), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        raise SystemExit(f'No screener reports found in {reports_dir}')
    return candidates[0]


def load_csv_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open('r', encoding='utf-8-sig', newline='') as fh:
        return list(csv.DictReader(fh))


def load_delimited_rows_tolerant(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    raw = path.read_bytes()
    text = None
    for enc in ('utf-8-sig', 'cp1252', 'latin-1', 'utf-16'):
        try:
            text = raw.decode(enc)
            break
        except Exception:
            continue
    if text is None:
        text = raw.decode('latin-1', errors='replace')
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=',;\t')
    except Exception:
        class D(csv.excel):
            delimiter = '\t'
        dialect = D
    return list(csv.DictReader(io.StringIO(text), dialect=dialect))


def normalize_broker_symbol(symbol: str) -> str:
    symbol = symbol.strip().upper()
    if symbol.endswith('.PRO'):
        symbol = symbol[:-4]
    return symbol


def load_mt5_symbol_map(path: Path) -> dict[str, str]:
    rows = load_delimited_rows_tolerant(path)
    candidates: dict[str, list[tuple[int, str]]] = {}
    for row in rows:
        raw_symbol = str(row.get('Symbol') or '').strip().upper()
        if not raw_symbol:
            continue
        path_value = str(row.get('Path') or '').strip()
        calc_mode = str(row.get('CalcMode') or '').strip().upper()
        trade_mode = str(row.get('TradeMode') or '').strip().upper()
        visible = str(row.get('Visible') or '').strip().lower() == 'true'
        selected = str(row.get('Selected') or '').strip().lower() == 'true'
        if not (path_value.startswith('Forex\\') or calc_mode == 'FOREX'):
            continue
        root = normalize_broker_symbol(raw_symbol)
        score = 0
        if trade_mode not in {'DISABLED', 'CLOSEONLY', ''}:
            score += 100
        if visible:
            score += 10
        if selected:
            score += 5
        if raw_symbol.endswith('.PRO'):
            score += 3
        score -= len(raw_symbol)
        candidates.setdefault(root, []).append((score, raw_symbol))

    mapping: dict[str, str] = {}
    for root, items in candidates.items():
        items.sort(reverse=True)
        mapping[root] = items[0][1]
    return mapping


def approx_price_from_row(row: dict[str, Any]) -> float | None:
    values = [
        safe_float(row.get('Fast EMA')),
        safe_float(row.get('Medium EMA')),
        safe_float(row.get('Slow EMA')),
    ]
    values = [v for v in values if v is not None and v > 0]
    if not values:
        return None
    return sum(values) / len(values)


def build_fx_graph(rows: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    graph: dict[str, dict[str, float]] = {}
    for row in rows:
        symbol = str(row.get('Symbol') or '').upper()
        if len(symbol) != 6:
            continue
        px = approx_price_from_row(row)
        if px is None or px <= 0:
            continue
        base, quote = symbol[:3], symbol[3:]
        graph.setdefault(base, {})[quote] = px
        graph.setdefault(quote, {})[base] = 1.0 / px
    return graph


def fx_to_usd_rate(currency: str, graph: dict[str, dict[str, float]]) -> float | None:
    currency = currency.upper()
    if currency == 'USD':
        return 1.0
    seen = {currency}
    queue: list[tuple[str, float]] = [(currency, 1.0)]
    while queue:
        node, rate = queue.pop(0)
        if node == 'USD':
            return rate
        for nxt, edge in graph.get(node, {}).items():
            if nxt in seen:
                continue
            seen.add(nxt)
            queue.append((nxt, rate * edge))
    return None


def parse_symbol(symbol: str) -> tuple[str, str]:
    symbol = symbol.upper()
    if len(symbol) != 6:
        raise ValueError(f'Unexpected FX symbol format: {symbol}')
    return symbol[:3], symbol[3:]


def session_key(report: dict[str, Any], report_path: Path) -> str:
    stamp = str(report.get('generatedAt') or report_path.stem)
    watchlist = str(report.get('watchlist') or 'UNKNOWN')
    timeframe = str(report.get('timeframe') or 'UNKNOWN')
    return f'{watchlist}|{timeframe}|{stamp}'


def load_state(state_dir: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    sessions_path = state_dir / 'sessions.json'
    active_path = state_dir / 'active_assets.json'
    sessions = load_json(sessions_path) if sessions_path.exists() else {'sessions': {}}
    active = load_json(active_path) if active_path.exists() else {'assets': {}}
    return sessions, active


def save_state(state_dir: Path, sessions: dict[str, Any], active: dict[str, Any]) -> None:
    save_json(state_dir / 'sessions.json', sessions)
    save_json(state_dir / 'active_assets.json', active)


def candidate_direction(row: dict[str, Any]) -> tuple[str | None, str | None, str | None]:
    setup = safe_float(row.get('02 Best Setup Code'))
    if setup is None:
        return None, None, None
    if int(setup) == 2:
        return 'LONG', 'LONG_CONTINUATION', 'buy'
    if int(setup) == -2:
        return 'SHORT', 'SHORT_CONTINUATION', 'sell'
    if int(setup) == 1:
        return 'LONG', 'LONG_MEANREV', 'buy'
    if int(setup) == -1:
        return 'SHORT', 'SHORT_MEANREV', 'sell'
    return None, None, None


def row_passes(row: dict[str, Any], cfg: dict[str, Any], active_assets: dict[str, Any]) -> tuple[bool, list[str], Candidate | None]:
    reasons: list[str] = []
    symbol = str(row.get('Symbol') or '').upper()
    desc = str(row.get('Description') or symbol)
    criteria = cfg['criteria']

    if symbol in active_assets:
        reasons.append('asset already marked active from a prior autotrade')

    direction, setup_label, side = candidate_direction(row)
    setup_code = safe_float(row.get('02 Best Setup Code'))
    if setup_code is None or int(setup_code) not in set(criteria['allowedSetupCodes']):
        reasons.append('setup code not in allowed continuation set')

    best_score = safe_float(row.get('03 Best Score'))
    if best_score is None or best_score < criteria['minBestScore']:
        reasons.append(f'best score below threshold {criteria["minBestScore"]}')

    conviction = safe_float(row.get('10 Conviction State'))
    if conviction is None or conviction < criteria['minConvictionState']:
        reasons.append(f'conviction below threshold {criteria["minConvictionState"]}')

    adx = safe_float(row.get('16 ADX'))
    if adx is None or adx < criteria['minAdx']:
        reasons.append(f'ADX below threshold {criteria["minAdx"]}')

    dist = safe_float(row.get('18 Dist Fast EMA ATR'))
    if dist is None or abs(dist) > criteria['maxDistFastEmaAtr']:
        reasons.append(f'Dist Fast EMA ATR outside threshold {criteria["maxDistFastEmaAtr"]}')

    if direction == 'LONG':
        directional_score = safe_float(row.get('04 Final Long Score'))
        if directional_score is None or directional_score < criteria['minDirectionalScore']:
            reasons.append(f'final long score below threshold {criteria["minDirectionalScore"]}')
        if criteria.get('requireTrendAlignment') and safe_float(row.get('11 Trend Dir')) != 1:
            reasons.append('trend direction not aligned bullish')
        if criteria.get('requireMacroAlignment') and safe_float(row.get('12 Macro Dir 1D')) != 1:
            reasons.append('1D macro direction not aligned bullish')
    elif direction == 'SHORT':
        directional_score = safe_float(row.get('05 Final Short Score'))
        if directional_score is None or directional_score < criteria['minDirectionalScore']:
            reasons.append(f'final short score below threshold {criteria["minDirectionalScore"]}')
        if criteria.get('requireTrendAlignment') and safe_float(row.get('11 Trend Dir')) != -1:
            reasons.append('trend direction not aligned bearish')
        if criteria.get('requireMacroAlignment') and safe_float(row.get('12 Macro Dir 1D')) != -1:
            reasons.append('1D macro direction not aligned bearish')
    else:
        reasons.append('unable to determine candidate direction')

    if reasons:
        return False, reasons, None
    return True, reasons, Candidate(symbol=symbol, description=desc, row=row, direction=direction, setup_label=setup_label, side=side)


def select_candidate(report: dict[str, Any], cfg: dict[str, Any], active_assets: dict[str, Any]) -> tuple[Candidate | None, list[dict[str, Any]]]:
    rows = report.get('top10') or report.get('top5') or []
    rows = rows[: int(cfg.get('candidateSearchDepth', 10))]
    audit: list[dict[str, Any]] = []
    for item in rows:
        row = item.get('raw') or item
        ok, reasons, candidate = row_passes(row, cfg, active_assets)
        audit.append({'symbol': row.get('Symbol'), 'passed': ok, 'reasons': reasons})
        if ok and candidate:
            return candidate, audit
    return None, audit


def compute_plan(candidate: Candidate, report: dict[str, Any], cfg: dict[str, Any], universe_rows: list[dict[str, Any]], mt5_symbol_map: dict[str, str]) -> dict[str, Any]:
    row = candidate.row
    fast = safe_float(row.get('Fast EMA'))
    medium = safe_float(row.get('Medium EMA'))
    slow = safe_float(row.get('Slow EMA'))
    if None in (fast, medium, slow):
        raise ValueError(f'Missing EMA fields for {candidate.symbol}')

    price_ref = approx_price_from_row(row)
    if price_ref is None:
        raise ValueError(f'Missing price reference for {candidate.symbol}')

    ema_spread = abs(fast - medium) + abs(medium - slow)
    stop_buffer = max(ema_spread * 0.75, price_ref * 0.0012)
    if candidate.direction == 'LONG':
        entry = fast
        sl = min(medium, slow) - stop_buffer
    else:
        entry = fast
        sl = max(medium, slow) + stop_buffer

    risk_per_unit = abs(entry - sl)
    if risk_per_unit <= 0:
        raise ValueError(f'Invalid risk structure for {candidate.symbol}')

    tp1_r = 1.0
    tp2_r = 1.8
    if candidate.direction == 'LONG':
        tp1 = entry + tp1_r * risk_per_unit
        tp2 = entry + tp2_r * risk_per_unit
    else:
        tp1 = entry - tp1_r * risk_per_unit
        tp2 = entry - tp2_r * risk_per_unit

    _base, quote = parse_symbol(candidate.symbol)
    fallback_rows = [item.get('raw') or item for item in (report.get('top10') or [])] + [item.get('raw') or item for item in (report.get('top5') or [])]
    graph = build_fx_graph(universe_rows if universe_rows else fallback_rows)
    quote_to_usd = fx_to_usd_rate(quote, graph)
    if quote_to_usd is None:
        raise ValueError(f'Could not derive {quote}->USD conversion from the screener universe')

    risk_budget = float(cfg['riskBudgetUsdt'])
    max_margin = float(cfg['maxMarginUsdt'])
    leverage = float(cfg['modelLeverage'])
    contract_size = float(cfg['contractSizeFx'])
    min_lot = float(cfg['defaultMinLot'])
    lot_step = float(cfg['defaultLotStep'])

    risk_per_lot_usd = risk_per_unit * contract_size * quote_to_usd
    if risk_per_lot_usd <= 0:
        raise ValueError(f'Invalid risk-per-lot for {candidate.symbol}')
    lots_by_risk = risk_budget / risk_per_lot_usd

    notional_per_lot_usd = entry * contract_size * quote_to_usd
    lots_by_margin = (max_margin * leverage) / notional_per_lot_usd

    lots = floor_step(min(lots_by_risk, lots_by_margin), lot_step)
    lots = round(lots, 2)
    if lots < min_lot:
        raise ValueError(f'Risk/margin capped position for {candidate.symbol} falls below minimum lot size {min_lot:.2f}')

    total_risk_usd = lots * risk_per_lot_usd
    total_notional_usd = lots * notional_per_lot_usd
    total_margin_usd = total_notional_usd / leverage
    rr1 = abs(tp1 - entry) / risk_per_unit
    rr2 = abs(tp2 - entry) / risk_per_unit

    execution_symbol = mt5_symbol_map.get(candidate.symbol, candidate.symbol)

    orderability = {
        'decision': 'placeable_conditional_only',
        'market_order_now': False,
        'ladder_limit_orders': True,
        'stop_entry_orders': False,
        'allowed_order_types': ['LIMIT'],
        'why': 'The setup is executable via one resting limit order near the fast-EMA pullback zone; no market-now order is justified in phase 1.'
    }

    return {
        'report_type': 'MT5_FX_PHASE1_DEEP_ANALYSIS',
        'generated_at_utc': iso_z(now_utc()),
        'symbol': candidate.symbol,
        'description': candidate.description,
        'source_context': {
            'watchlist': report.get('watchlist'),
            'indicator': report.get('indicator'),
            'timeframe': report.get('timeframe'),
            'best_score': safe_float(row.get('03 Best Score')),
            'best_setup_code': int(safe_float(row.get('02 Best Setup Code'))),
            'conviction_state': int(safe_float(row.get('10 Conviction State'))),
            'screener_rank_top5': next((idx + 1 for idx, item in enumerate(report.get('top5') or []) if (item.get('symbol') or '').upper() == candidate.symbol), None),
            'tv_root_symbol': candidate.symbol,
            'mt5_execution_symbol': execution_symbol,
        },
        'bias': {
            'direction': candidate.direction,
            'setup': candidate.setup_label,
            'quality_call': 'good market, conditional-only entry',
            'final_trader_call': 'Ready to place one conditional limit order' if total_risk_usd <= risk_budget and total_margin_usd <= max_margin else 'No order yet',
        },
        'metrics': {
            'fast_ema': fast,
            'medium_ema': medium,
            'slow_ema': slow,
            'trend_dir': safe_float(row.get('11 Trend Dir')),
            'macro_dir_1d': safe_float(row.get('12 Macro Dir 1D')),
            'adx': safe_float(row.get('16 ADX')),
            'rel_volume': safe_float(row.get('17 Rel Volume')),
            'dist_fast_ema_atr': safe_float(row.get('18 Dist Fast EMA ATR')),
            'tactical_trend_score': safe_float(row.get('23 Tactical Trend Score')),
            'tactical_breakout_score': safe_float(row.get('24 Tactical Breakout Score')),
            'tactical_meanrev_score': safe_float(row.get('25 Tactical MeanRev Score')),
        },
        'key_levels': {
            'entry': round(entry, 5),
            'stop_loss': round(sl, 5),
            'tp1': round(tp1, 5),
            'tp2': round(tp2, 5),
            'price_reference': round(price_ref, 5),
            'ema_pullback_zone_from': round(min(fast, medium), 5),
            'ema_pullback_zone_to': round(max(fast, medium), 5),
            'slow_ema_invalidation_anchor': round(slow, 5)
        },
        'orderability_decision': orderability,
        'risk_plan': {
            'risk_budget_usdt': risk_budget,
            'model_leverage': leverage,
            'quote_to_usd': quote_to_usd,
            'contract_size': contract_size,
            'volume_lots': lots,
            'total_risk_usdt': round(total_risk_usd, 2),
            'total_notional_usdt': round(total_notional_usd, 2),
            'total_margin_usdt': round(total_margin_usd, 2),
            'rr_tp1': round(rr1, 2),
            'rr_tp2': round(rr2, 2)
        },
        'trade_ticket_preview': {
            'side': candidate.side,
            'tv_root_symbol': candidate.symbol,
            'mt5_execution_symbol': execution_symbol,
            'order_plan': 'limit_ladder',
            'entry_type': 'limit',
            'entry': round(entry, 5),
            'sl': round(sl, 5),
            'tp_live': round(tp2, 5),
            'planned_tp1': round(tp1, 5),
            'planned_tp2': round(tp2, 5),
            'volume_lots': lots,
            'max_risk_usdt': risk_budget
        },
        'notes': [
            'Phase 1 only permits one single-entry pending order per screening session.',
            'Phase 1 prefers conditional limit entries into the fast-EMA pullback zone rather than market chasing.',
            'Bridge remains paper-only and uses one executable TP in the live ticket; TP2 is used as the live bridge TP while TP1 remains an analysis/management level.'
        ]
    }


def plan_to_ticket(plan: dict[str, Any], session_id: str) -> dict[str, Any]:
    preview = plan['trade_ticket_preview']
    tv_symbol = plan['symbol']
    symbol = preview.get('mt5_execution_symbol') or tv_symbol
    direction = plan['bias']['direction']
    ticket_id = f"mt5-paper-{session_id.replace('|', '-').replace(':', '').replace('.', '-')}-{tv_symbol.lower()}-phase1-001"
    return {
        'bridge_version': 'mt5.paper.v1',
        'ticket_id': ticket_id,
        'created_at': iso_z(now_utc()),
        'mode': 'paper',
        'symbol': symbol,
        'side': preview['side'],
        'order_plan': preview['order_plan'],
        'entries': [
            {
                'client_entry_id': f'{tv_symbol.lower()}-phase1-entry-1',
                'entry_type': preview['entry_type'],
                'price': preview['entry'],
                'volume_lots': preview['volume_lots'],
                'comment': f'{tv_symbol} -> {symbol} phase1 autotrade {direction.lower()} limit entry'
            }
        ],
        'stop_loss': {'price': preview['sl']},
        'take_profit': {'price': preview['tp_live']},
        'max_risk_usdt': preview['max_risk_usdt'],
        'strategy_context': {
            'source': f'Phase1 MT5 FX autotrade deep analysis for {tv_symbol}',
            'watchlist': plan['source_context']['watchlist'],
            'timeframe': plan['source_context']['timeframe'],
            'tv_root_symbol': tv_symbol,
            'mt5_execution_symbol': symbol,
            'orderability_decision': plan['orderability_decision']['decision'],
            'setup': plan['bias']['setup'],
            'planned_tp1': preview['planned_tp1'],
            'planned_tp2': preview['planned_tp2'],
            'planned_rr_tp1': plan['risk_plan']['rr_tp1'],
            'planned_rr_tp2': plan['risk_plan']['rr_tp2'],
            'planned_total_notional_usd': plan['risk_plan']['total_notional_usdt'],
            'modeled_margin_usd': plan['risk_plan']['total_margin_usdt'],
            'bridge_tp_note': 'Bridge v1 supports one live TP only; TP2 is used as executable TP while TP1 remains a management level.'
        },
        'note': f"{tv_symbol} phase1 autotrade via {symbol}. Default risk budget {plan['risk_plan']['risk_budget_usdt']:.0f} USD. Single conditional limit entry from screener-led deep analysis."
    }


def render_markdown(plan: dict[str, Any], ticket: dict[str, Any] | None = None, execution: dict[str, Any] | None = None, audit: list[dict[str, Any]] | None = None, session_id: str | None = None) -> str:
    lines: list[str] = []
    lines.append(f"# MT5 Phase 1 Trade Review — {plan['symbol']}")
    lines.append('')
    if session_id:
        lines.append(f"- Session: `{session_id}`")
    lines.append(f"- Watchlist: `{plan['source_context']['watchlist']}`")
    lines.append(f"- Indicator: `{plan['source_context']['indicator']}`")
    lines.append(f"- Timeframe: `{plan['source_context']['timeframe']}`")
    lines.append(f"- TradingView root symbol: `{plan['source_context']['tv_root_symbol']}`")
    lines.append(f"- MT5 execution symbol: `{plan['source_context']['mt5_execution_symbol']}`")
    lines.append(f"- Generated: `{plan['generated_at_utc']}`")
    lines.append('')
    lines.append('## Candidate gate')
    lines.append('')
    if audit:
        for item in audit[:5]:
            mark = 'PASS' if item['passed'] else 'SKIP'
            reasons = '; '.join(item['reasons']) if item['reasons'] else 'meets criteria'
            lines.append(f"- {mark} `{item['symbol']}` — {reasons}")
    lines.append('')
    lines.append('## Deep analysis')
    lines.append('')
    lines.append(f"- Bias: **{plan['bias']['direction']}**")
    lines.append(f"- Setup: **{plan['bias']['setup']}**")
    lines.append(f"- Quality call: **{plan['bias']['quality_call']}**")
    lines.append(f"- Orderability: **{plan['orderability_decision']['decision']}**")
    lines.append(f"- Why: {plan['orderability_decision']['why']}")
    lines.append(f"- Final trader call: **{plan['bias']['final_trader_call']}**")
    lines.append('')
    lines.append('## Quantitative levels')
    lines.append('')
    lines.append(f"- Price reference: `{plan['key_levels']['price_reference']}`")
    lines.append(f"- Entry zone: `{plan['key_levels']['ema_pullback_zone_from']}` -> `{plan['key_levels']['ema_pullback_zone_to']}`")
    lines.append(f"- Executable entry: `{plan['key_levels']['entry']}`")
    lines.append(f"- 1D-style invalidation anchor: slow EMA `{plan['key_levels']['slow_ema_invalidation_anchor']}`")
    lines.append(f"- Live SL: `{plan['key_levels']['stop_loss']}`")
    lines.append(f"- TP1: `{plan['key_levels']['tp1']}`")
    lines.append(f"- TP2 / live TP: `{plan['key_levels']['tp2']}`")
    lines.append('')
    lines.append('## Proposed trading plan')
    lines.append('')
    lines.append('| Strategy | Order Type | Entry | SL | TP1 | RR1 | TP2 | RR2 | Size Lots | Size Notional USD | Margin USD | Risk USD |')
    lines.append('|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|')
    lines.append(
        f"| {plan['bias']['setup']} | {plan['trade_ticket_preview']['order_plan']} / {plan['trade_ticket_preview']['entry_type']} | {plan['trade_ticket_preview']['entry']:.5f} | {plan['trade_ticket_preview']['sl']:.5f} | {plan['trade_ticket_preview']['planned_tp1']:.5f} | {plan['risk_plan']['rr_tp1']:.2f} | {plan['trade_ticket_preview']['planned_tp2']:.5f} | {plan['risk_plan']['rr_tp2']:.2f} | {plan['trade_ticket_preview']['volume_lots']:.2f} | {plan['risk_plan']['total_notional_usdt']:.2f} | {plan['risk_plan']['total_margin_usdt']:.2f} | {plan['risk_plan']['total_risk_usdt']:.2f} |"
    )
    lines.append('')
    if ticket is not None:
        lines.append('## MT5 bridge ticket')
        lines.append('')
        lines.append('```json')
        lines.append(json.dumps(ticket, indent=2, ensure_ascii=False))
        lines.append('```')
        lines.append('')
    if execution is not None:
        lines.append('## MT5 execution result')
        lines.append('')
        for key in ['status', 'message', 'retcode', 'retcode_text', 'symbol', 'side', 'result_file']:
            if key in execution:
                lines.append(f"- {key}: `{execution[key]}`")
        if execution.get('mt5_order_ids'):
            lines.append(f"- mt5_order_ids: `{execution['mt5_order_ids']}`")
        lines.append('')
    if plan.get('notes'):
        lines.append('## Notes')
        lines.append('')
        for note in plan['notes']:
            lines.append(f'- {note}')
        lines.append('')
    return '\n'.join(lines).strip() + '\n'


def run_emit(ticket_path: Path, cfg: dict[str, Any]) -> dict[str, Any]:
    cmd = [
        sys.executable,
        str(EMIT_SCRIPT),
        '--ticket',
        str(ticket_path),
        '--wait-seconds',
        str(cfg['emit']['waitSeconds']),
        '--poll-seconds',
        str(cfg['emit']['pollSeconds'])
    ]
    proc = subprocess.run(cmd, cwd=str(WORKSPACE), capture_output=True, text=True)
    chunks: list[dict[str, Any]] = []
    text = proc.stdout or ''
    decoder = json.JSONDecoder()
    idx = 0
    while idx < len(text):
        while idx < len(text) and text[idx].isspace():
            idx += 1
        if idx >= len(text):
            break
        obj, end = decoder.raw_decode(text, idx)
        if isinstance(obj, dict):
            chunks.append(obj)
        idx = end
    result = chunks[-1] if chunks else {'status': 'error', 'message': (proc.stderr or proc.stdout or '').strip() or f'emitter exited {proc.returncode}'}
    result['returncode'] = proc.returncode
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description='Phase 1 MT5 FX screen-to-trade pipeline.')
    ap.add_argument('--config', default=str(DEFAULT_CONFIG))
    ap.add_argument('--report-json', default='')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--force', action='store_true')
    args = ap.parse_args()

    cfg = load_json(Path(args.config))
    reports_dir = Path(cfg['screenerReportsDir'])
    report_path = Path(args.report_json) if args.report_json else latest_report(reports_dir)
    report = load_json(report_path)

    csv_path = Path(str(report.get('csvPath') or '')).expanduser() if report.get('csvPath') else None
    universe_rows = load_csv_rows(csv_path) if csv_path else []
    mt5_symbols_csv = Path(str(cfg.get('mt5SymbolsExportCsv') or '')).expanduser() if cfg.get('mt5SymbolsExportCsv') else None
    mt5_symbol_map = load_mt5_symbol_map(mt5_symbols_csv) if mt5_symbols_csv else {}

    state_dir = Path(cfg['stateDir'])
    reports_out = Path(cfg['reportsDir'])
    reports_out.mkdir(parents=True, exist_ok=True)
    sessions, active = load_state(state_dir)

    sess_key = session_key(report, report_path)
    if not args.force and sess_key in sessions['sessions']:
        prior = sessions['sessions'][sess_key]
        payload = {
            'result': 'already_processed',
            'session_key': sess_key,
            'prior': prior,
            'report_path': str(report_path)
        }
        print(json.dumps(payload, indent=2))
        return 0

    candidate, audit = select_candidate(report, cfg, active.get('assets', {}))
    stamp = now_utc().strftime('%Y%m%d_%H%M%S')

    if candidate is None:
        result = {
            'result': 'no_trade',
            'reason': 'no candidate passed the predefined criteria',
            'session_key': sess_key,
            'audit': audit,
            'report_path': str(report_path)
        }
        save_json(reports_out / f'mt5_phase1_session_{stamp}.json', result)
        save_json(reports_out / 'mt5_phase1_latest.json', result)
        sessions['sessions'][sess_key] = {'status': 'no_trade', 'reason': result['reason'], 'processed_at': iso_z(now_utc())}
        save_state(state_dir, sessions, active)
        print(json.dumps(result, indent=2))
        return 0

    plan = compute_plan(candidate, report, cfg, universe_rows=universe_rows, mt5_symbol_map=mt5_symbol_map)
    ticket = None
    execution = None

    if plan['orderability_decision']['decision'] in {'placeable_now', 'placeable_conditional_only'}:
        ticket = plan_to_ticket(plan, sess_key)
        ticket_path = reports_out / f'ticket_{candidate.symbol}_{stamp}.json'
        save_json(ticket_path, ticket)
        if not args.dry_run:
            execution = run_emit(ticket_path, cfg)
            if execution.get('status') == 'accepted':
                active.setdefault('assets', {})[candidate.symbol] = {
                    'session_key': sess_key,
                    'ticket_id': ticket['ticket_id'],
                    'placed_at': iso_z(now_utc()),
                    'status': 'accepted',
                    'result_file': execution.get('result_file')
                }
        else:
            execution = {'status': 'dry_run', 'message': 'Ticket compiled but not emitted.'}
    else:
        execution = {'status': 'skipped', 'message': 'Plan not executable under phase 1 rules.'}

    markdown = render_markdown(plan, ticket=ticket, execution=execution, audit=audit, session_id=sess_key)
    md_path = reports_out / f'mt5_phase1_session_{stamp}.md'
    md_path.write_text(markdown, encoding='utf-8')

    result = {
        'result': 'trade_review',
        'session_key': sess_key,
        'report_path': str(report_path),
        'candidate': candidate.symbol,
        'analysis_path': str(md_path),
        'ticket_path': str(reports_out / f'ticket_{candidate.symbol}_{stamp}.json') if ticket else None,
        'execution': execution,
        'audit': audit,
        'plan': plan
    }
    save_json(reports_out / f'mt5_phase1_session_{stamp}.json', result)
    save_json(reports_out / 'mt5_phase1_latest.json', result)
    sessions['sessions'][sess_key] = {
        'status': execution.get('status'),
        'candidate': candidate.symbol,
        'ticket_id': ticket.get('ticket_id') if ticket else None,
        'processed_at': iso_z(now_utc())
    }
    save_state(state_dir, sessions, active)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
