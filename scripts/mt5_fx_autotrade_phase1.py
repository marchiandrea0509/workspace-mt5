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

from market_source_lib import make_market_source
from mt5_fx_deep_analysis_lib import analyze_candidate

try:
    import MetaTrader5 as mt5
except Exception:
    mt5 = None

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


def safe_int(v: Any) -> int | None:
    num = safe_float(v)
    if num is None:
        return None
    return int(num)


def floor_step(value: float, step: float) -> float:
    if step <= 0:
        return value
    return math.floor(value / step + 1e-12) * step


def latest_report(reports_dir: Path) -> Path:
    candidates = sorted(reports_dir.glob('pine_screener_*.json'), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        raise SystemExit(f'No screener reports found in {reports_dir}')
    return candidates[0]


def parse_iso_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(timezone.utc)


def validate_phase1_report(report: dict[str, Any], report_path: Path, cfg: dict[str, Any], *, require_fresh: bool) -> None:
    if report.get('ok') is False:
        err = str(report.get('error') or 'screener export failed')
        raise SystemExit(f'Latest screener report is invalid: {err}')

    watchlist = str(report.get('watchlist') or '').strip()
    indicator = str(report.get('indicator') or '').strip()
    timeframe = str(report.get('timeframe') or '').strip()
    expected_watchlist = str(cfg.get('watchlist') or '').strip()
    expected_indicator = str(cfg.get('indicator') or '').strip()
    expected_timeframe = str(cfg.get('timeframe') or '').strip()

    if expected_watchlist and watchlist != expected_watchlist:
        raise SystemExit(f'Latest screener report watchlist mismatch: expected {expected_watchlist}, got {watchlist or "<missing>"}')
    if expected_indicator and indicator != expected_indicator:
        raise SystemExit(f'Latest screener report indicator mismatch: expected {expected_indicator}, got {indicator or "<missing>"}')
    if expected_timeframe and timeframe != expected_timeframe:
        raise SystemExit(f'Latest screener report timeframe mismatch: expected {expected_timeframe}, got {timeframe or "<missing>"}')

    rows = report.get('top10') or report.get('top5') or []
    if not rows:
        raise SystemExit(f'Latest screener report has no top candidates: {report_path.name}')

    generated_at = str(report.get('generatedAt') or '').strip()
    if not generated_at:
        raise SystemExit(f'Latest screener report missing generatedAt: {report_path.name}')

    if require_fresh:
        age_minutes = (now_utc() - parse_iso_utc(generated_at)).total_seconds() / 60.0
        max_age = float(cfg.get('latestReportMaxAgeMinutes') or 0)
        if max_age > 0 and age_minutes > max_age:
            raise SystemExit(f'Latest screener report is stale: age {age_minutes:.1f}m exceeds limit {max_age:.1f}m ({report_path.name})')


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
    if symbol.endswith('.P'):
        symbol = symbol[:-2]
    if symbol.endswith('USDT'):
        symbol = symbol[:-4] + 'USD'
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
        asset_class_guess = str(row.get('AssetClassGuess') or '').strip().upper()
        trade_mode = str(row.get('TradeMode') or '').strip().upper()
        visible = str(row.get('Visible') or '').strip().lower() == 'true'
        selected = str(row.get('Selected') or '').strip().lower() == 'true'
        if not (path_value.startswith('Forex\\') or path_value.startswith('Crypto\\') or calc_mode == 'FOREX' or asset_class_guess == 'FOREX_LIKE'):
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


def reconcile_active_assets(active: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any]:
    assets = dict(active.get('assets', {}))
    if not assets or mt5 is None:
        return {'assets': assets}
    terminal = str((cfg.get('analysisDataSource') or {}).get('terminalExe') or '')
    if not terminal or not mt5.initialize(path=terminal):
        return {'assets': assets}
    try:
        live_symbols = set()
        for o in (mt5.orders_get() or []):
            if int(getattr(o, 'magic', 0)) == 26032601:
                live_symbols.add(str(o.symbol).upper().replace('.PRO', ''))
        for p in (mt5.positions_get() or []):
            if int(getattr(p, 'magic', 0)) == 26032601:
                live_symbols.add(str(p.symbol).upper().replace('.PRO', ''))
        assets = {sym: payload for sym, payload in assets.items() if sym.upper() in live_symbols}
        return {'assets': assets}
    finally:
        mt5.shutdown()


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
    if conviction is not None and conviction < criteria['minConvictionState']:
        reasons.append(f'conviction below threshold {criteria["minConvictionState"]}')

    if direction == 'LONG':
        directional_score = safe_float(row.get('04 Final Long Score'))
        if directional_score is None or directional_score < criteria['minDirectionalScore']:
            reasons.append(f'final long score below threshold {criteria["minDirectionalScore"]}')
    elif direction == 'SHORT':
        directional_score = safe_float(row.get('05 Final Short Score'))
        if directional_score is None or directional_score < criteria['minDirectionalScore']:
            reasons.append(f'final short score below threshold {criteria["minDirectionalScore"]}')
    else:
        reasons.append('unable to determine candidate direction')

    if reasons:
        return False, reasons, None
    return True, reasons, Candidate(symbol=symbol, description=desc, row=row, direction=direction, setup_label=setup_label, side=side)


def select_candidates(report: dict[str, Any], cfg: dict[str, Any], active_assets: dict[str, Any]) -> tuple[list[Candidate], list[dict[str, Any]]]:
    rows = report.get('top10') or report.get('top5') or []
    rows = rows[: int(cfg.get('candidateSearchDepth', 10))]
    audit: list[dict[str, Any]] = []
    candidates: list[Candidate] = []
    for item in rows:
        row = item.get('raw') or item
        ok, reasons, candidate = row_passes(row, cfg, active_assets)
        audit.append({'symbol': row.get('Symbol'), 'passed': ok, 'reasons': reasons})
        if ok and candidate:
            candidates.append(candidate)
    return candidates, audit


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

    execution_symbol = mt5_symbol_map.get(normalize_broker_symbol(candidate.symbol), candidate.symbol)
    proxy_source = str((cfg.get('proxySymbols') or {}).get(candidate.symbol) or '').strip()
    is_proxy_symbol = bool(proxy_source)

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
            'best_setup_code': safe_int(row.get('02 Best Setup Code')),
            'conviction_state': safe_int(row.get('10 Conviction State')),
            'screener_rank_top5': next((idx + 1 for idx, item in enumerate(report.get('top5') or []) if (item.get('symbol') or '').upper() == candidate.symbol), None),
            'tv_root_symbol': candidate.symbol,
            'mt5_execution_symbol': execution_symbol,
            'is_proxy_symbol': is_proxy_symbol,
            'proxy_source': proxy_source or None,
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
            'is_proxy_symbol': is_proxy_symbol,
            'proxy_source': proxy_source or None,
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
        ] + ([f"Proxy symbol: TradingView analysis for {candidate.symbol} is sourced from {proxy_source}, while MT5 execution still targets {execution_symbol}. Phase 1 applies no extra proxy rule yet."] if is_proxy_symbol else [])
    }


def plan_to_ticket(plan: dict[str, Any], session_id: str) -> dict[str, Any]:
    preview = plan['trade_ticket_preview']
    key = plan.get('key_levels', {})
    tv_symbol = plan['symbol']
    symbol = preview.get('mt5_execution_symbol') or tv_symbol
    direction = plan['bias']['direction']
    template = str(plan.get('orderability_decision', {}).get('execution_template') or '')
    unique_suffix = now_utc().strftime('%m%d%H%M%S')
    ticket_symbol = ''.join(ch for ch in tv_symbol.lower() if ch.isalnum())[:8] or 'asset'
    ticket_id = f"p1-{ticket_symbol}-{unique_suffix}"

    total_lots = float(preview['volume_lots'])
    entries: list[dict[str, Any]] = []

    def split_lots(parts: int) -> list[float]:
        if parts <= 1:
            return [round(total_lots, 2)]
        base = round(total_lots / parts, 2)
        vals = [base for _ in range(parts)]
        used = round(sum(vals), 2)
        vals[-1] = round(max(total_lots - (used - vals[-1]), 0.01), 2)
        return vals

    if template == 'breakout_stop_limit':
        order_plan = 'stop_entry'
        breakout_price = float(key.get('breakout_trigger') or preview['entry'])
        lots = split_lots(1)
        entries.append({
            'client_entry_id': f'{tv_symbol.lower()}-phase1-breakout-1',
            'entry_type': 'stop',
            'price': breakout_price,
            'volume_lots': lots[0],
            'comment': f'{tv_symbol} -> {symbol} phase1 breakout stop entry'
        })
    elif template == 'hybrid_ladder_breakout':
        order_plan = 'hybrid_ladder_breakout'
        ladder = list(key.get('ladder_entries') or [])
        ladder = ladder[:2] if len(ladder) >= 2 else ([float(preview['entry'])] if preview.get('entry') else [])
        breakout_price = float(key.get('breakout_trigger') or (float(preview['entry']) + (abs(float(preview['entry']) - float(preview['sl'])) * (1 if direction == 'LONG' else -1))))
        lots = split_lots(len(ladder) + 1)
        for i, px in enumerate(ladder):
            entries.append({
                'client_entry_id': f'{tv_symbol.lower()}-phase1-ladder-{i+1}',
                'entry_type': 'limit',
                'price': float(px),
                'volume_lots': lots[i],
                'comment': f'{tv_symbol} -> {symbol} phase1 ladder limit entry {i+1}'
            })
        entries.append({
            'client_entry_id': f'{tv_symbol.lower()}-phase1-breakout-1',
            'entry_type': 'stop',
            'price': breakout_price,
            'volume_lots': lots[-1],
            'comment': f'{tv_symbol} -> {symbol} phase1 hybrid breakout stop entry'
        })
    else:
        order_plan = 'limit_ladder'
        ladder = list(key.get('ladder_entries') or [])
        leg_count = 3 if template == 'ladder_limit_3' else 2 if template == 'ladder_limit_2' else 1
        if not ladder:
            ladder = [float(preview['entry'])]
        ladder = ladder[:leg_count]
        lots = split_lots(len(ladder))
        for i, px in enumerate(ladder):
            entries.append({
                'client_entry_id': f'{tv_symbol.lower()}-phase1-ladder-{i+1}',
                'entry_type': 'limit',
                'price': float(px),
                'volume_lots': lots[i],
                'comment': f'{tv_symbol} -> {symbol} phase1 ladder limit entry {i+1}'
            })

    return {
        'bridge_version': 'mt5.paper.v1',
        'ticket_id': ticket_id,
        'created_at': iso_z(now_utc()),
        'mode': 'paper',
        'symbol': symbol,
        'side': preview['side'],
        'order_plan': order_plan,
        'entries': entries,
        'stop_loss': {'price': preview['sl']},
        'take_profit': {'price': preview['tp_live']},
        'max_risk_usdt': preview['max_risk_usdt'],
        'strategy_context': {
            'source': f'Phase1 MT5 FX autotrade deep analysis for {tv_symbol}',
            'watchlist': plan['source_context']['watchlist'],
            'timeframe': plan['source_context']['timeframe'],
            'tv_root_symbol': tv_symbol,
            'mt5_execution_symbol': symbol,
            'is_proxy_symbol': plan['source_context'].get('is_proxy_symbol', False),
            'proxy_source': plan['source_context'].get('proxy_source'),
            'orderability_decision': plan['orderability_decision']['decision'],
            'execution_template': template,
            'setup': plan['bias']['setup'],
            'planned_tp1': preview['planned_tp1'],
            'planned_tp2': preview['planned_tp2'],
            'planned_rr_tp1': plan['risk_plan']['rr_tp1'],
            'planned_rr_tp2': plan['risk_plan']['rr_tp2'],
            'planned_total_notional_usd': plan['risk_plan']['total_notional_usdt'],
            'modeled_margin_usd': plan['risk_plan']['total_margin_usdt'],
            'bridge_tp_note': 'Bridge v1 supports one live TP for the package; TP2 is used as executable TP while TP1 remains a management level.'
        },
        'note': f"{tv_symbol} phase1 autotrade via {symbol}." + (f" Proxy source: {plan['source_context'].get('proxy_source')}." if plan['source_context'].get('is_proxy_symbol') else '') + f" Default risk budget {plan['risk_plan']['risk_budget_usdt']:.0f} USD. Execution template: {template or order_plan}."
    }


def preflight_mt5_ticket(ticket: dict[str, Any], cfg: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    if mt5 is None:
        return ticket, {'mode': 'skipped', 'reason': 'MetaTrader5 module unavailable'}

    source_cfg = cfg.get('analysisDataSource') or {}
    terminal = str(source_cfg.get('terminalExe') or '')
    if not terminal:
        return ticket, {'mode': 'skipped', 'reason': 'No terminal configured'}
    if not mt5.initialize(path=terminal):
        return ticket, {'mode': 'failed', 'reason': f'MT5 initialize failed: {mt5.last_error()}'}

    try:
        symbol = ticket['symbol']
        info = mt5.symbol_info(symbol)
        tick = mt5.symbol_info_tick(symbol)
        if info is None or tick is None:
            return ticket, {'mode': 'failed', 'reason': f'Missing symbol info/tick for {symbol}'}
        mt5.symbol_select(symbol, True)
        point = float(info.point or 0.0)
        stops_level = float(getattr(info, 'trade_stops_level', 0) or 0)
        min_dist = max(stops_level * point, 5 * point if point > 0 else 0.0)
        sl = float(ticket['stop_loss']['price'])
        tp = float(ticket['take_profit']['price'])
        side = ticket['side']
        valid = []
        rejected = []
        order_type_names = {
            mt5.ORDER_TYPE_BUY_LIMIT: 'BUY_LIMIT',
            mt5.ORDER_TYPE_SELL_LIMIT: 'SELL_LIMIT',
            mt5.ORDER_TYPE_BUY_STOP: 'BUY_STOP',
            mt5.ORDER_TYPE_SELL_STOP: 'SELL_STOP',
        }
        for entry in ticket['entries']:
            et = entry['entry_type']
            adjusted_entry = dict(entry)
            price = float(entry['price']) if entry.get('price') is not None else 0.0
            adjusted = False
            local_reasons = []
            if et == 'limit' and side == 'buy' and price >= tick.ask - min_dist:
                new_price = tick.ask - min_dist
                if point > 0:
                    new_price = round(new_price / point) * point
                adjusted_entry['price'] = new_price
                price = float(new_price)
                adjusted = True
            if et == 'limit' and side == 'sell' and price <= tick.bid + min_dist:
                new_price = tick.bid + min_dist
                if point > 0:
                    new_price = round(new_price / point) * point
                adjusted_entry['price'] = new_price
                price = float(new_price)
                adjusted = True
            if et == 'stop' and side == 'buy' and price <= tick.ask + min_dist:
                new_price = tick.ask + min_dist
                if point > 0:
                    new_price = round(new_price / point) * point
                adjusted_entry['price'] = new_price
                price = float(new_price)
                adjusted = True
            if et == 'stop' and side == 'sell' and price >= tick.bid - min_dist:
                new_price = tick.bid - min_dist
                if point > 0:
                    new_price = round(new_price / point) * point
                adjusted_entry['price'] = new_price
                price = float(new_price)
                adjusted = True
            if et == 'limit' and side == 'buy' and not (price < tick.ask):
                local_reasons.append('buy limit no longer below current ask')
            if et == 'limit' and side == 'sell' and not (price > tick.bid):
                local_reasons.append('sell limit no longer above current bid')
            if et == 'stop' and side == 'buy' and not (price > tick.ask):
                local_reasons.append('buy stop no longer above current ask')
            if et == 'stop' and side == 'sell' and not (price < tick.bid):
                local_reasons.append('sell stop no longer below current bid')
            if point > 0 and stops_level > 0:
                market_dist_pts = abs((tick.ask if side == 'buy' else tick.bid) - price) / point
                sl_dist_pts = abs(price - sl) / point
                tp_dist_pts = abs(tp - price) / point
                if market_dist_pts < stops_level:
                    local_reasons.append(f'entry too close to market (<{int(stops_level)} pts)')
                if sl_dist_pts < stops_level:
                    local_reasons.append(f'SL too close (<{int(stops_level)} pts)')
                if tp_dist_pts < stops_level:
                    local_reasons.append(f'TP too close (<{int(stops_level)} pts)')
            type_map = {
                ('buy', 'limit'): mt5.ORDER_TYPE_BUY_LIMIT,
                ('sell', 'limit'): mt5.ORDER_TYPE_SELL_LIMIT,
                ('buy', 'stop'): mt5.ORDER_TYPE_BUY_STOP,
                ('sell', 'stop'): mt5.ORDER_TYPE_SELL_STOP,
            }
            preflight_comment = str(entry.get('client_entry_id') or ticket['ticket_id'])[:31]
            req = {
                'action': mt5.TRADE_ACTION_PENDING,
                'symbol': symbol,
                'magic': 26032601,
                'volume': float(adjusted_entry['volume_lots']),
                'price': price,
                'sl': sl,
                'tp': tp,
                'deviation': 20,
                'type_time': mt5.ORDER_TIME_GTC,
                'type_filling': mt5.ORDER_FILLING_RETURN,
                'comment': preflight_comment,
                'type': type_map[(side, et)],
            }
            chk = mt5.order_check(req)
            if chk is None:
                local_reasons.append(f'order_check returned None (last_error={mt5.last_error()})')
            else:
                retcode = getattr(chk, 'retcode', None)
                comment = getattr(chk, 'comment', None)
                if retcode not in (0, 10009, 10008):
                    local_reasons.append(f'order_check retcode {retcode} ({comment})')
            if local_reasons:
                rejected.append({'client_entry_id': entry.get('client_entry_id'), 'entry_type': et, 'price': price, 'original_price': entry.get('price'), 'adjusted': adjusted, 'reasons': local_reasons, 'order_type': order_type_names.get(req['type'], str(req['type']))})
            else:
                valid.append(adjusted_entry)

        adjusted = dict(ticket)
        adjusted['entries'] = valid
        if valid:
            has_limit = any(e['entry_type'] == 'limit' for e in valid)
            has_stop = any(e['entry_type'] == 'stop' for e in valid)
            if has_limit and has_stop:
                adjusted['order_plan'] = 'hybrid_ladder_breakout'
            elif has_limit:
                adjusted['order_plan'] = 'limit_ladder'
            elif has_stop:
                adjusted['order_plan'] = 'stop_entry'
        return adjusted, {
            'mode': 'applied',
            'symbol': symbol,
            'valid_entries': len(valid),
            'rejected_entries': rejected,
            'original_entries': len(ticket['entries']),
            'adjusted_order_plan': adjusted.get('order_plan'),
        }
    finally:
        mt5.shutdown()


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
    if plan['source_context'].get('is_proxy_symbol'):
        lines.append(f"- Proxy symbol source: `{plan['source_context'].get('proxy_source')}`")
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
    if plan['key_levels'].get('analysis_ladder_entries'):
        lines.append(f"- Analysis ladder levels: `{plan['key_levels']['analysis_ladder_entries']}`")
    if plan['key_levels'].get('ladder_entries'):
        lines.append(f"- Executable ladder levels: `{plan['key_levels']['ladder_entries']}`")
    if plan['key_levels'].get('selected_zone_quality_score') is not None:
        lines.append(f"- Selected zone quality / touches / age: `{plan['key_levels']['selected_zone_quality_score']}` / `{plan['key_levels'].get('selected_zone_touches')}` / `{plan['key_levels'].get('selected_zone_age_bars')}`")
    for note in (plan['key_levels'].get('level_selection_notes') or [])[:4]:
        lines.append(f"- Level selection note: {note}")
    lines.append(f"- 1D-style invalidation anchor: slow EMA `{plan['key_levels']['slow_ema_invalidation_anchor']}`")
    lines.append(f"- Live SL: `{plan['key_levels']['stop_loss']}`")
    lines.append(f"- TP1: `{plan['key_levels']['tp1']}`")
    lines.append(f"- TP2 / live TP: `{plan['key_levels']['tp2']}`")
    lines.append('')
    lines.append('## Proposed trading plan')
    lines.append('')
    lines.append('| Strategy | Template | Entry Ref | SL | TP1 | RR1 | TP2 | RR2 | Size Lots | Size Notional USD | Margin USD | Risk USD | Binding Constraint |')
    lines.append('|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|')
    lines.append(
        f"| {plan['bias']['setup']} | {plan['orderability_decision']['execution_template']} | {plan['trade_ticket_preview']['entry']:.5f} | {plan['trade_ticket_preview']['sl']:.5f} | {plan['trade_ticket_preview']['planned_tp1']:.5f} | {plan['risk_plan']['rr_tp1']:.2f} | {plan['trade_ticket_preview']['planned_tp2']:.5f} | {plan['risk_plan']['rr_tp2']:.2f} | {plan['trade_ticket_preview']['volume_lots']:.2f} | {plan['risk_plan']['total_notional_usdt']:.2f} | {plan['risk_plan']['total_margin_usdt']:.2f} | {plan['risk_plan']['total_risk_usdt']:.2f} | {plan['risk_plan'].get('binding_constraint','n/a')} |"
    )
    lines.append('')
    if ticket is not None:
        lines.append('## Emitted MT5 package')
        lines.append('')
        lines.append('| # | Entry ID | Type | Price | Lots |')
        lines.append('|---|---|---|---:|---:|')
        for idx, entry in enumerate(ticket.get('entries', []), start=1):
            lines.append(f"| {idx} | {entry.get('client_entry_id')} | {entry.get('entry_type')} | {entry.get('price')} | {entry.get('volume_lots')} |")
        lines.append('')
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
        preflight = execution.get('preflight') if isinstance(execution, dict) else None
        if preflight:
            lines.append(f"- preflight: valid_entries={preflight.get('valid_entries')} / original_entries={preflight.get('original_entries')} / adjusted_order_plan={preflight.get('adjusted_order_plan')}")
            for item in (preflight.get('rejected_entries') or [])[:5]:
                lines.append(f"  - rejected {item.get('client_entry_id')}: {'; '.join(item.get('reasons') or [])}")
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
    report_resolution = 'explicit' if args.report_json else 'latest'
    if args.report_json and not report_path.exists():
        raise SystemExit(f'Explicit screener report not found: {report_path}')
    report = load_json(report_path)
    validate_phase1_report(report, report_path, cfg, require_fresh=not bool(args.report_json))

    state_dir = Path(cfg['stateDir'])
    reports_out = Path(cfg['reportsDir'])
    reports_out.mkdir(parents=True, exist_ok=True)
    sessions, active = load_state(state_dir)
    active = reconcile_active_assets(active, cfg)

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

    candidates, audit = select_candidates(report, cfg, active.get('assets', {}))
    stamp = now_utc().strftime('%Y%m%d_%H%M%S')

    if not candidates:
        result = {
            'result': 'no_trade',
            'reason': 'no candidate passed the predefined criteria',
            'session_key': sess_key,
            'audit': audit,
            'report_path': str(report_path),
            'report_resolution': report_resolution
        }
        save_json(reports_out / f'mt5_phase1_session_{stamp}.json', result)
        save_json(reports_out / 'mt5_phase1_latest.json', result)
        sessions['sessions'][sess_key] = {'status': 'no_trade', 'reason': result['reason'], 'processed_at': iso_z(now_utc())}
        save_state(state_dir, sessions, active)
        print(json.dumps(result, indent=2))
        return 0

    candidate = None
    plan = None
    source = make_market_source(cfg['analysisDataSource'])
    try:
        for maybe_candidate in candidates:
            try:
                plan = analyze_candidate(maybe_candidate, report, cfg, source)
                candidate = maybe_candidate
                break
            except KeyError as exc:
                for item in audit:
                    if str(item.get('symbol') or '').upper() == maybe_candidate.symbol.upper():
                        item['passed'] = False
                        item.setdefault('reasons', []).append(f'mt5 symbol resolution failed: {exc}')
                        break
        if candidate is None or plan is None:
            result = {
                'result': 'no_trade',
                'reason': 'no candidate passed the predefined criteria or MT5 symbol resolution',
                'session_key': sess_key,
                'audit': audit,
                'report_path': str(report_path),
                'report_resolution': report_resolution
            }
            save_json(reports_out / f'mt5_phase1_session_{stamp}.json', result)
            save_json(reports_out / 'mt5_phase1_latest.json', result)
            sessions['sessions'][sess_key] = {'status': 'no_trade', 'reason': result['reason'], 'processed_at': iso_z(now_utc())}
            save_state(state_dir, sessions, active)
            print(json.dumps(result, indent=2))
            return 0
    finally:
        shutdown = getattr(source, 'shutdown', None)
        if callable(shutdown):
            shutdown()

    ticket = None
    execution = None

    if plan['orderability_decision']['decision'] in {'placeable_now', 'placeable_conditional_only'}:
        ticket = plan_to_ticket(plan, sess_key)
        ticket, preflight = preflight_mt5_ticket(ticket, cfg)
        if preflight.get('mode') == 'applied' and preflight.get('valid_entries', 0) <= 0:
            execution = {
                'status': 'skipped',
                'message': 'All candidate entries became invalid at MT5 preflight time.',
                'preflight': preflight,
            }
        else:
            ticket_path = reports_out / f'ticket_{candidate.symbol}_{stamp}.json'
            save_json(ticket_path, ticket)
            if not args.dry_run:
                execution = run_emit(ticket_path, cfg)
                execution['preflight'] = preflight
                if execution.get('status') == 'accepted':
                    active.setdefault('assets', {})[candidate.symbol] = {
                        'session_key': sess_key,
                        'ticket_id': ticket['ticket_id'],
                        'placed_at': iso_z(now_utc()),
                        'status': 'accepted',
                        'result_file': execution.get('result_file')
                    }
            else:
                execution = {'status': 'dry_run', 'message': 'Ticket compiled but not emitted.', 'preflight': preflight}
    else:
        execution = {'status': 'skipped', 'message': 'Plan not executable under phase 1 rules.'}

    markdown = render_markdown(plan, ticket=ticket, execution=execution, audit=audit, session_id=sess_key)
    md_path = reports_out / f'mt5_phase1_session_{stamp}.md'
    md_path.write_text(markdown, encoding='utf-8')

    result = {
        'result': 'trade_review',
        'session_key': sess_key,
        'report_path': str(report_path),
        'report_resolution': report_resolution,
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
