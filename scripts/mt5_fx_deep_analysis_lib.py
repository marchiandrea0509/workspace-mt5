from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any

from market_source_lib import MarketDataSource, SymbolProfile


def iso_z() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def safe_float(v: Any) -> float | None:
    try:
        if v in (None, '', '—'):
            return None
        return float(v)
    except Exception:
        return None


def ema(values: list[float], period: int) -> list[float]:
    out: list[float] = []
    if not values:
        return out
    alpha = 2.0 / (period + 1.0)
    cur = values[0]
    for v in values:
        cur = alpha * v + (1.0 - alpha) * cur
        out.append(cur)
    return out


def rsi(values: list[float], period: int = 14) -> list[float | None]:
    if len(values) < 2:
        return [None for _ in values]
    gains = [0.0]
    losses = [0.0]
    for i in range(1, len(values)):
        delta = values[i] - values[i - 1]
        gains.append(max(delta, 0.0))
        losses.append(max(-delta, 0.0))
    out: list[float | None] = [None] * len(values)
    avg_gain = sum(gains[1:period + 1]) / period if len(values) > period else 0.0
    avg_loss = sum(losses[1:period + 1]) / period if len(values) > period else 0.0
    for i in range(period, len(values)):
        if i > period:
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        if avg_loss == 0:
            out[i] = 100.0
        else:
            rs = avg_gain / avg_loss
            out[i] = 100.0 - (100.0 / (1.0 + rs))
    return out


def atr(highs: list[float], lows: list[float], closes: list[float], period: int = 14) -> list[float | None]:
    trs: list[float] = []
    for i in range(len(closes)):
        if i == 0:
            tr = highs[i] - lows[i]
        else:
            tr = max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1]))
        trs.append(tr)
    out: list[float | None] = [None] * len(closes)
    if len(closes) <= period:
        return out
    cur = sum(trs[1:period + 1]) / period
    out[period] = cur
    for i in range(period + 1, len(closes)):
        cur = ((cur * (period - 1)) + trs[i]) / period
        out[i] = cur
    return out


def dmi_adx(highs: list[float], lows: list[float], closes: list[float], period: int = 14) -> tuple[list[float | None], list[float | None], list[float | None]]:
    n = len(closes)
    plus_dm = [0.0] * n
    minus_dm = [0.0] * n
    tr = [0.0] * n
    for i in range(1, n):
        up = highs[i] - highs[i - 1]
        down = lows[i - 1] - lows[i]
        plus_dm[i] = up if up > down and up > 0 else 0.0
        minus_dm[i] = down if down > up and down > 0 else 0.0
        tr[i] = max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1]))
    plus_di: list[float | None] = [None] * n
    minus_di: list[float | None] = [None] * n
    adx: list[float | None] = [None] * n
    if n <= period * 2:
        return plus_di, minus_di, adx
    tr14 = sum(tr[1:period + 1])
    plus14 = sum(plus_dm[1:period + 1])
    minus14 = sum(minus_dm[1:period + 1])
    dx_vals: list[float] = []
    for i in range(period, n):
        if i > period:
            tr14 = tr14 - (tr14 / period) + tr[i]
            plus14 = plus14 - (plus14 / period) + plus_dm[i]
            minus14 = minus14 - (minus14 / period) + minus_dm[i]
        pdi = 100.0 * plus14 / tr14 if tr14 else 0.0
        mdi = 100.0 * minus14 / tr14 if tr14 else 0.0
        plus_di[i] = pdi
        minus_di[i] = mdi
        denom = pdi + mdi
        dx = 100.0 * abs(pdi - mdi) / denom if denom else 0.0
        dx_vals.append(dx)
        if i == period * 2 - 1:
            adx[i] = sum(dx_vals[-period:]) / period
        elif i >= period * 2:
            prev = adx[i - 1] if adx[i - 1] is not None else sum(dx_vals[-period:]) / period
            adx[i] = ((prev * (period - 1)) + dx) / period
    return plus_di, minus_di, adx


def macd(values: list[float]) -> tuple[list[float], list[float], list[float]]:
    fast = ema(values, 12)
    slow = ema(values, 26)
    macd_line = [f - s for f, s in zip(fast, slow)]
    signal = ema(macd_line, 9)
    hist = [m - s for m, s in zip(macd_line, signal)]
    return macd_line, signal, hist


def pivot_highs(highs: list[float], left: int, right: int) -> list[tuple[int, float]]:
    out = []
    for i in range(left, len(highs) - right):
        window = highs[i - left:i + right + 1]
        if highs[i] == max(window):
            out.append((i, highs[i]))
    return out


def pivot_lows(lows: list[float], left: int, right: int) -> list[tuple[int, float]]:
    out = []
    for i in range(left, len(lows) - right):
        window = lows[i - left:i + right + 1]
        if lows[i] == min(window):
            out.append((i, lows[i]))
    return out


def merge_zones(pivots: list[tuple[int, float]], atr_value: float, is_support: bool, merge_mult: float = 1.2, max_zones: int = 6) -> list[dict[str, Any]]:
    if not pivots:
        return []
    thresh = atr_value * merge_mult
    zones: list[dict[str, Any]] = []
    for idx, price in pivots:
        matched = None
        for zone in zones:
            if abs(zone['level'] - price) <= thresh:
                matched = zone
                break
        if matched is None:
            zones.append({'level': price, 'touches': 1, 'first_idx': idx, 'last_idx': idx, 'is_support': is_support})
        else:
            t = matched['touches']
            matched['level'] = (matched['level'] * t + price) / (t + 1)
            matched['touches'] += 1
            matched['last_idx'] = idx
    zones.sort(key=lambda z: z['last_idx'], reverse=True)
    zones = zones[:max_zones]
    for zone in zones:
        zone['upper'] = zone['level'] + atr_value * 0.25
        zone['lower'] = zone['level'] - atr_value * 0.25
    return zones


def nearest_zone(zones: list[dict[str, Any]], close: float, want_support: bool) -> dict[str, Any] | None:
    best = None
    for zone in zones:
        if want_support and zone['level'] <= close:
            if best is None or zone['level'] > best['level']:
                best = zone
        if not want_support and zone['level'] >= close:
            if best is None or zone['level'] < best['level']:
                best = zone
    return best


def pick_recent_breakout(closes: list[float], highs: list[float], lows: list[float], resistance: dict[str, Any] | None, support: dict[str, Any] | None, atr_value: float) -> tuple[int, int | None]:
    margin = atr_value * 0.15
    breakout_dir = 0
    breakout_idx = None
    if resistance:
        for i in range(max(1, len(closes) - 8), len(closes)):
            if closes[i] > resistance['upper'] + margin and closes[i - 1] <= resistance['upper'] + margin:
                breakout_dir = 1
                breakout_idx = i
    if support:
        for i in range(max(1, len(closes) - 8), len(closes)):
            if closes[i] < support['lower'] - margin and closes[i - 1] >= support['lower'] - margin:
                breakout_dir = -1
                breakout_idx = i
    return breakout_dir, breakout_idx


def recent_retest_state(direction: int, breakout_idx: int | None, closes: list[float], highs: list[float], lows: list[float], zone: dict[str, Any] | None, window: int = 16) -> tuple[int, str]:
    if direction == 0 or breakout_idx is None or zone is None:
        return 0, 'none'
    start = breakout_idx + 1
    end = min(len(closes), breakout_idx + 1 + window)
    if start >= len(closes):
        return 0, 'none'
    touched = False
    for i in range(start, end):
        if direction == 1:
            if lows[i] <= zone['upper'] and highs[i] >= zone['lower']:
                touched = True
                if closes[i] > zone['level']:
                    return 3, 'retest_confirmed'
                if closes[i] < zone['lower']:
                    return 4, 'failed_retest'
        else:
            if highs[i] >= zone['lower'] and lows[i] <= zone['upper']:
                touched = True
                if closes[i] < zone['level']:
                    return -3, 'retest_confirmed'
                if closes[i] > zone['upper']:
                    return -4, 'failed_retest'
    if touched:
        return (2 if direction == 1 else -2), 'retest_touched'
    return (1 if direction == 1 else -1), 'waiting_retest'


def trend_structure(highs: list[float], lows: list[float]) -> tuple[int, int]:
    ph = pivot_highs(highs, 16, 5)
    pl = pivot_lows(lows, 16, 5)
    trend_dir = 0
    struct_shift = 0
    if len(ph) >= 2 and len(pl) >= 2:
        higher_high = ph[-1][1] > ph[-2][1]
        higher_low = pl[-1][1] > pl[-2][1]
        lower_high = ph[-1][1] < ph[-2][1]
        lower_low = pl[-1][1] < pl[-2][1]
        if higher_high and higher_low:
            trend_dir = 1
        elif lower_high and lower_low:
            trend_dir = -1
    if ph:
        closes_ref = highs[-1]
        last_high = ph[-1][1]
        if closes_ref > last_high:
            struct_shift = 2 if trend_dir <= 0 else 1
    if pl and lows[-1] < pl[-1][1]:
        struct_shift = -2 if trend_dir >= 0 else -1
    return trend_dir, struct_shift


def clip(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def choose_direction(candidate_direction: str, h4: dict[str, Any], d1: dict[str, Any]) -> tuple[str, list[str]]:
    notes = []
    direction = candidate_direction
    if candidate_direction == 'LONG':
        if h4['trend_dir'] < 0 and d1['macro_dir'] < 0:
            notes.append('MT5 H4 and D1 context both oppose LONG bias.')
    else:
        if h4['trend_dir'] > 0 and d1['macro_dir'] > 0:
            notes.append('MT5 H4 and D1 context both oppose SHORT bias.')
    return direction, notes


def build_risk_plan(profile: SymbolProfile, quote_to_usd: float | None, entry: float, sl: float, cfg: dict[str, Any]) -> dict[str, Any]:
    leverage = float(cfg['modelLeverage'])
    risk_budget = float(cfg['riskBudgetUsdt'])
    max_margin = float(cfg['maxMarginUsdt'])
    quote_to_usd = quote_to_usd or 1.0
    contract_size = profile.contract_size or float(cfg.get('contractSizeFx') or 100000.0)
    risk_per_lot = abs(entry - sl) * contract_size * quote_to_usd
    notional_per_lot = entry * contract_size * quote_to_usd
    lots_by_risk = risk_budget / risk_per_lot if risk_per_lot > 0 else 0.0
    lots_by_margin = (max_margin * leverage) / notional_per_lot if notional_per_lot > 0 else 0.0
    step = profile.volume_step or float(cfg['defaultLotStep'])
    min_lot = profile.volume_min or float(cfg['defaultMinLot'])
    lots = math.floor(min(lots_by_risk, lots_by_margin) / step + 1e-12) * step if step > 0 else min(lots_by_risk, lots_by_margin)
    lots = round(max(lots, 0.0), 2)
    if lots < min_lot:
        lots = round(min_lot, 2)
    total_risk = lots * risk_per_lot
    total_notional = lots * notional_per_lot
    total_margin = total_notional / leverage if leverage else total_notional
    return {
        'risk_budget_usdt': risk_budget,
        'model_leverage': leverage,
        'quote_to_usd': quote_to_usd,
        'contract_size': contract_size,
        'volume_lots': lots,
        'total_risk_usdt': round(total_risk, 2),
        'total_notional_usdt': round(total_notional, 2),
        'total_margin_usdt': round(total_margin, 2),
    }


def analyze_candidate(candidate: Any, report: dict[str, Any], cfg: dict[str, Any], source: MarketDataSource) -> dict[str, Any]:
    root_symbol = candidate.symbol
    row = candidate.row
    profile = source.resolve_symbol(root_symbol)
    h4_bars = source.get_rates(profile.analysis_symbol, 'H4', int(cfg['analysisDataSource']['historyBars']['H4']))
    d1_bars = source.get_rates(profile.analysis_symbol, 'D1', int(cfg['analysisDataSource']['historyBars']['D1']))

    closes = [b['close'] for b in h4_bars]
    highs = [b['high'] for b in h4_bars]
    lows = [b['low'] for b in h4_bars]
    tick_vol = [b['tick_volume'] for b in h4_bars]
    d_closes = [b['close'] for b in d1_bars]
    d_highs = [b['high'] for b in d1_bars]
    d_lows = [b['low'] for b in d1_bars]

    ema_fast = ema(closes, 21)
    ema_med = ema(closes, 50)
    ema_slow = ema(closes, 200)
    atr_h4 = atr(highs, lows, closes, 14)
    rsi_h4 = rsi(closes, 14)
    plus_di_h4, minus_di_h4, adx_h4 = dmi_adx(highs, lows, closes, 14)
    macd_line, macd_signal, macd_hist = macd(closes)

    d_ema50 = ema(d_closes, 50)
    d_ema200 = ema(d_closes, 200)
    d_rsi = rsi(d_closes, 14)
    d_plus, d_minus, d_adx = dmi_adx(d_highs, d_lows, d_closes, 14)

    close = closes[-1]
    fast = ema_fast[-1]
    med = ema_med[-1]
    slow = ema_slow[-1]
    atr_now = atr_h4[-1] or max(close * 0.0015, 1e-6)
    adx_now = adx_h4[-1] or 0.0
    plus_now = plus_di_h4[-1] or 0.0
    minus_now = minus_di_h4[-1] or 0.0
    rsi_now = rsi_h4[-1] or 50.0
    rel_vol = tick_vol[-1] / (sum(tick_vol[-20:]) / min(20, len(tick_vol))) if tick_vol else 1.0

    support_zones = merge_zones(pivot_lows(lows, 10, 10), atr_now, True)
    resistance_zones = merge_zones(pivot_highs(highs, 10, 10), atr_now, False)
    support_zone = nearest_zone(support_zones, close, True)
    resistance_zone = nearest_zone(resistance_zones, close, False)
    breakout_dir, breakout_idx = pick_recent_breakout(closes, highs, lows, resistance_zone, support_zone, atr_now)
    retest_state, retest_label = recent_retest_state(breakout_dir, breakout_idx, closes, highs, lows, support_zone if breakout_dir == 1 else resistance_zone)
    trend_dir, struct_shift = trend_structure(highs, lows)

    d_close = d_closes[-1]
    macro_dir = 1 if d_close > d_ema50[-1] > d_ema200[-1] else -1 if d_close < d_ema50[-1] < d_ema200[-1] else 0
    d_adx_now = d_adx[-1] or 0.0
    d_plus_now = d_plus[-1] or 0.0
    d_minus_now = d_minus[-1] or 0.0

    dist_fast_ema_atr = abs(close - fast) / atr_now if atr_now else 0.0
    ema_spread_atr = abs(fast - slow) / atr_now if atr_now else 0.0
    overextended = dist_fast_ema_atr > 2.0 or ema_spread_atr > 4.0
    fake_breakout_risk = (breakout_dir == 1 and rsi_now > 70) or (breakout_dir == -1 and rsi_now < 30)
    breakout_fresh = breakout_idx is not None and (len(closes) - 1 - breakout_idx) <= 3

    direction, bias_notes = choose_direction(candidate.direction, {'trend_dir': trend_dir}, {'macro_dir': macro_dir})
    aligned = (direction == 'LONG' and (trend_dir >= 0 and macro_dir >= 0)) or (direction == 'SHORT' and (trend_dir <= 0 and macro_dir <= 0))

    family = 'NONE'
    execution_template = 'no_order'
    decision = 'not_placeable_yet'

    if direction == 'LONG':
        continuation_ok = (fast > med > slow) and (macro_dir >= 0) and not fake_breakout_risk
        meanrev_ok = support_zone is not None and rsi_now < 45 and trend_dir >= 0
        breakout_ok = breakout_dir == 1 and breakout_fresh and adx_now >= 20 and not overextended and plus_now > minus_now
        hybrid_ok = continuation_ok and breakout_dir == 1 and not overextended and adx_now >= 20
        if breakout_ok:
            family = 'BREAKOUT'
            execution_template = 'breakout_stop_limit'
            decision = 'placeable_now'
        elif hybrid_ok:
            family = 'CONTINUATION'
            execution_template = 'hybrid_ladder_breakout'
            decision = 'placeable_conditional_only'
        elif continuation_ok:
            family = 'CONTINUATION'
            execution_template = 'ladder_limit_3' if support_zone and (fast - support_zone['level']) > 0.5 * atr_now else 'ladder_limit_2'
            decision = 'placeable_conditional_only'
        elif meanrev_ok:
            family = 'MEAN_REVERSION'
            execution_template = 'ladder_limit_2'
            decision = 'placeable_conditional_only'
    else:
        continuation_ok = (fast < med < slow) and (macro_dir <= 0) and not fake_breakout_risk
        meanrev_ok = resistance_zone is not None and rsi_now > 55 and trend_dir <= 0
        breakout_ok = breakout_dir == -1 and breakout_fresh and adx_now >= 20 and not overextended and minus_now > plus_now
        hybrid_ok = continuation_ok and breakout_dir == -1 and not overextended and adx_now >= 20
        if breakout_ok:
            family = 'BREAKOUT'
            execution_template = 'breakout_stop_limit'
            decision = 'placeable_now'
        elif hybrid_ok:
            family = 'CONTINUATION'
            execution_template = 'hybrid_ladder_breakout'
            decision = 'placeable_conditional_only'
        elif continuation_ok:
            family = 'CONTINUATION'
            execution_template = 'ladder_limit_3' if resistance_zone and (resistance_zone['level'] - fast) > 0.5 * atr_now else 'ladder_limit_2'
            decision = 'placeable_conditional_only'
        elif meanrev_ok:
            family = 'MEAN_REVERSION'
            execution_template = 'ladder_limit_2'
            decision = 'placeable_conditional_only'

    if not aligned:
        decision = 'not_placeable_yet'
        execution_template = 'no_order'

    proxy_source = str((cfg.get('proxySymbols') or {}).get(root_symbol) or '').strip()
    is_proxy_symbol = bool(proxy_source)

    if direction == 'LONG':
        support_anchor = support_zone['level'] if support_zone else min(med, slow)
        ladder = sorted({round(min(fast, close), profile.digits), round(support_anchor, profile.digits), round(min(slow, support_anchor - 0.25 * atr_now), profile.digits)})
        ladder = [x for x in ladder if x < close + 5 * profile.point]
        breakout_trigger = round(max(highs[-5:]) + 0.15 * atr_now, profile.digits)
        breakout_limit = round(breakout_trigger + 0.10 * atr_now, profile.digits)
        structural_sl = round(min((support_zone['lower'] if support_zone else slow), min(lows[-20:])) - 0.15 * atr_now, profile.digits)
    else:
        resistance_anchor = resistance_zone['level'] if resistance_zone else max(med, slow)
        ladder = sorted({round(max(fast, close), profile.digits), round(resistance_anchor, profile.digits), round(max(slow, resistance_anchor + 0.25 * atr_now), profile.digits)}, reverse=True)
        ladder = [x for x in ladder if x > close - 5 * profile.point]
        breakout_trigger = round(min(lows[-5:]) - 0.15 * atr_now, profile.digits)
        breakout_limit = round(breakout_trigger - 0.10 * atr_now, profile.digits)
        structural_sl = round(max((resistance_zone['upper'] if resistance_zone else slow), max(highs[-20:])) + 0.15 * atr_now, profile.digits)

    if execution_template == 'breakout_stop_limit':
        entry = breakout_trigger
        entry_type = 'stop'
        order_plan = 'stop_entry'
    else:
        usable_ladder = ladder[:3] if '3' in execution_template else ladder[:2]
        if not usable_ladder:
            usable_ladder = [round(fast, profile.digits)]
        entry = round(sum(usable_ladder) / len(usable_ladder), profile.digits)
        entry_type = 'limit'
        order_plan = 'limit_ladder'

    risk_r = abs(entry - structural_sl)
    tp1 = round(entry + (risk_r if direction == 'LONG' else -risk_r), profile.digits)
    tp2 = round(entry + (1.8 * risk_r if direction == 'LONG' else -1.8 * risk_r), profile.digits)
    quote_to_usd = source.fx_to_usd_rate(profile.currency_profit)
    risk_plan = build_risk_plan(profile, quote_to_usd, entry, structural_sl, cfg)
    rr1 = abs(tp1 - entry) / risk_r if risk_r else 0.0
    rr2 = abs(tp2 - entry) / risk_r if risk_r else 0.0
    risk_plan['rr_tp1'] = round(rr1, 2)
    risk_plan['rr_tp2'] = round(rr2, 2)

    notes = [
        'Deep analysis v2 is MT5-native for H4/D1 market structure, indicators, and level geometry.',
        'TradingView screener still ranks/selects candidates, but execution-grade analysis now uses broker-feed MT5 candles.',
        'Bridge now supports multi-entry pending packages for ladder execution; hybrid cancel-on-fill is managed by package state in the EA timer loop.'
    ]
    notes.extend(bias_notes)
    if is_proxy_symbol:
        notes.append(f'Proxy symbol: screener selection for {root_symbol} came from {proxy_source}, but deep analysis now uses MT5 symbol {profile.analysis_symbol}.')
    if execution_template == 'hybrid_ladder_breakout':
        notes.append('Hybrid template detected: recommended package is ladder + breakout stop, with EA-managed cancel-on-fill for the opposite branch.')

    best_score_val = safe_float(row.get('03 Best Score'))
    best_setup_val = safe_float(row.get('02 Best Setup Code'))
    conviction_val = safe_float(row.get('10 Conviction State'))

    return {
        'report_type': 'MT5_FX_DEEP_ANALYSIS_V2',
        'generated_at_utc': iso_z(),
        'symbol': root_symbol,
        'description': candidate.description,
        'source_context': {
            'watchlist': report.get('watchlist'),
            'indicator': report.get('indicator'),
            'timeframe': report.get('timeframe'),
            'best_score': best_score_val,
            'best_setup_code': int(best_setup_val) if best_setup_val is not None else None,
            'conviction_state': int(conviction_val) if conviction_val is not None else None,
            'screener_rank_top5': next((idx + 1 for idx, item in enumerate(report.get('top5') or []) if (item.get('symbol') or '').upper() == root_symbol), None),
            'tv_root_symbol': root_symbol,
            'analysis_source_kind': source.kind,
            'analysis_symbol': profile.analysis_symbol,
            'mt5_execution_symbol': profile.execution_symbol,
            'is_proxy_symbol': is_proxy_symbol,
            'proxy_source': proxy_source or None,
        },
        'bias': {
            'direction': direction,
            'setup': f'{direction}_{family}' if family != 'NONE' else 'UNQUALIFIED',
            'quality_call': 'broker-feed MT5 structure validated' if decision != 'not_placeable_yet' else 'screener candidate failed MT5 execution-grade validation',
            'final_trader_call': 'Ready for bridge fallback execution' if decision in {'placeable_now', 'placeable_conditional_only'} else 'No trade from MT5 deep analysis',
        },
        'market_source': {
            'kind': source.kind,
            'analysis_symbol': profile.analysis_symbol,
            'execution_symbol': profile.execution_symbol,
            'trade_mode': profile.trade_mode,
            'path': profile.path,
            'digits': profile.digits,
            'volume_min': profile.volume_min,
            'volume_step': profile.volume_step,
        },
        'metrics': {
            'close_h4': close,
            'fast_ema_h4': fast,
            'medium_ema_h4': med,
            'slow_ema_h4': slow,
            'atr_h4': atr_now,
            'rsi_h4': rsi_now,
            'adx_h4': adx_now,
            'plus_di_h4': plus_now,
            'minus_di_h4': minus_now,
            'macd_hist_h4': macd_hist[-1],
            'rel_volume_h4': rel_vol,
            'dist_fast_ema_atr': dist_fast_ema_atr,
            'ema_spread_atr': ema_spread_atr,
            'd1_close': d_close,
            'd1_ema50': d_ema50[-1],
            'd1_ema200': d_ema200[-1],
            'd1_rsi': d_rsi[-1],
            'd1_adx': d_adx_now,
            'd1_plus_di': d_plus_now,
            'd1_minus_di': d_minus_now,
        },
        'lifecycle': {
            'trend_dir_h4': trend_dir,
            'macro_dir_d1': macro_dir,
            'fresh_structure_shift': struct_shift,
            'breakout_dir': breakout_dir,
            'breakout_fresh': breakout_fresh,
            'retest_state': retest_state,
            'retest_label': retest_label,
            'fake_breakout_risk': fake_breakout_risk,
            'overextended': overextended,
        },
        'key_levels': {
            'analysis_price_reference': round(close, profile.digits),
            'price_reference': round(close, profile.digits),
            'support_zone_level': round(support_zone['level'], profile.digits) if support_zone else None,
            'support_zone_lower': round(support_zone['lower'], profile.digits) if support_zone else None,
            'support_zone_upper': round(support_zone['upper'], profile.digits) if support_zone else None,
            'resistance_zone_level': round(resistance_zone['level'], profile.digits) if resistance_zone else None,
            'resistance_zone_lower': round(resistance_zone['lower'], profile.digits) if resistance_zone else None,
            'resistance_zone_upper': round(resistance_zone['upper'], profile.digits) if resistance_zone else None,
            'ladder_entries': ladder[:3],
            'ema_pullback_zone_from': round(min(ladder[:2]) if ladder else entry, profile.digits),
            'ema_pullback_zone_to': round(max(ladder[:2]) if ladder else entry, profile.digits),
            'slow_ema_invalidation_anchor': round(slow, profile.digits),
            'breakout_trigger': breakout_trigger,
            'breakout_limit': breakout_limit,
            'entry': entry,
            'stop_loss': structural_sl,
            'tp1': tp1,
            'tp2': tp2,
        },
        'orderability_decision': {
            'decision': decision,
            'execution_template': execution_template,
            'bridge_supported_now': execution_template in {'breakout_stop_limit', 'ladder_limit_2', 'ladder_limit_3'},
            'market_order_now': decision == 'placeable_now' and execution_template == 'breakout_stop_limit',
            'ladder_limit_orders': execution_template.startswith('ladder') or execution_template == 'hybrid_ladder_breakout',
            'stop_entry_orders': execution_template in {'breakout_stop_limit', 'hybrid_ladder_breakout'},
            'allowed_order_types': ['LIMIT', 'STOP-LIMIT'] if execution_template == 'hybrid_ladder_breakout' else ['STOP'] if execution_template == 'breakout_stop_limit' else ['LIMIT'],
            'why': {
                'breakout_stop_limit': 'Fresh breakout on MT5 broker candles with trend/macro alignment and acceptable stretch.',
                'ladder_limit_2': 'Continuation quality is good but current location is better handled as a pullback ladder.',
                'ladder_limit_3': 'Continuation quality is good and structure supports a deeper 3-level pullback ladder.',
                'hybrid_ladder_breakout': 'Both pullback and breakout continuation paths are valid on MT5 structure; ideal package is ladder + breakout, but bridge still needs linked-leg support.',
                'no_order': 'MT5 structure, lifecycle, or alignment does not justify an executable order package yet.'
            }[execution_template],
        },
        'risk_plan': risk_plan,
        'trade_ticket_preview': {
            'side': 'buy' if direction == 'LONG' else 'sell',
            'tv_root_symbol': root_symbol,
            'analysis_symbol': profile.analysis_symbol,
            'mt5_execution_symbol': profile.execution_symbol,
            'is_proxy_symbol': is_proxy_symbol,
            'proxy_source': proxy_source or None,
            'order_plan': order_plan,
            'entry_type': entry_type,
            'entry': entry,
            'sl': structural_sl,
            'tp_live': tp2,
            'planned_tp1': tp1,
            'planned_tp2': tp2,
            'volume_lots': risk_plan['volume_lots'],
            'max_risk_usdt': risk_plan['risk_budget_usdt'],
            'bridge_fallback_reason': 'Hybrid execution still uses one live TP across all legs; branch-level TP/SL separation is not yet implemented.' if execution_template == 'hybrid_ladder_breakout' else None,
        },
        'notes': notes,
    }
