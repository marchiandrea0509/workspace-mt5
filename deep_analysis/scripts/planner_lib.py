#!/usr/bin/env python3
from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from pipeline_lib import PROCESSED_DIR, REPORT_DIR, normalize_timeframe, read_existing_dataframe

ROOT = Path(__file__).resolve().parents[1]
SCREENER_DIR = ROOT / "screeners"
SCREENER_REPORT_DIR = REPORT_DIR / "screeners"
FEATURE_REPORT_DIR = REPORT_DIR / "features"
CONTEXT_DIR = REPORT_DIR / "context"
ASSET_OVERLAY_DIR = CONTEXT_DIR / "asset_overlays"
PLAN_DIR = REPORT_DIR / "plans"


def ensure_dirs() -> None:
    PLAN_DIR.mkdir(parents=True, exist_ok=True)


def safe_float(value: Any) -> float | None:
    try:
        if value is None or pd.isna(value):
            return None
        return float(value)
    except Exception:
        return None


def safe_int(value: Any) -> int | None:
    try:
        if value is None or pd.isna(value):
            return None
        return int(value)
    except Exception:
        return None


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def clamp_int(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))


def round_price(value: float | None, digits: int = 4) -> float | None:
    if value is None:
        return None
    return round(float(value), digits)


def fmt_num(value: Any, digits: int = 2) -> str:
    if value is None or pd.isna(value):
        return "n/a"
    return f"{float(value):.{digits}f}"


def fmt_pct(value: Any, digits: int = 2, scale: float = 100.0) -> str:
    if value is None or pd.isna(value):
        return "n/a"
    return f"{float(value) * scale:.{digits}f}%"


def load_json_if_exists(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def load_screener_frame() -> pd.DataFrame:
    csv_path = SCREENER_DIR / "mtf_screener.csv"
    if not csv_path.exists():
        raise SystemExit(f"Missing screener table: {csv_path}. Run build_screener.py first.")
    frame = pd.read_csv(csv_path)
    if frame.empty:
        raise SystemExit("Screener table is empty.")
    return frame


def load_screener_summary() -> dict[str, Any]:
    summary_path = SCREENER_REPORT_DIR / "mtf_screener_summary.json"
    if not summary_path.exists():
        return {}
    return json.loads(summary_path.read_text(encoding="utf-8"))


WINNER_MAP = {
    "top_best": ("best_score_rank", "best_score"),
    "best": ("best_score_rank", "best_score"),
    "winner": ("best_score_rank", "best_score"),
    "top_long": ("overall_long_score_rank", "overall_long_score"),
    "long": ("overall_long_score_rank", "overall_long_score"),
    "top_short": ("overall_short_score_rank", "overall_short_score"),
    "short": ("overall_short_score_rank", "overall_short_score"),
}


def resolve_symbol(frame: pd.DataFrame, symbol: str | None = None, winner: str | None = None) -> str:
    if symbol:
        symbol_upper = symbol.upper()
        subset = frame[frame["internal_symbol"].astype(str).str.upper() == symbol_upper]
        if subset.empty:
            raise SystemExit(f"Symbol not present in screener: {symbol_upper}")
        return symbol_upper

    winner_key = str(winner or "top_best").strip().lower()
    rank_column, score_column = WINNER_MAP.get(winner_key, WINNER_MAP["top_best"])
    ordered = frame.sort_values([rank_column, score_column], ascending=[True, False]).reset_index(drop=True)
    if ordered.empty:
        raise SystemExit("No screener rows available to resolve winner.")
    return str(ordered.iloc[0]["internal_symbol"]).upper()


def screener_row(frame: pd.DataFrame, symbol: str) -> pd.Series:
    subset = frame[frame["internal_symbol"].astype(str).str.upper() == symbol.upper()]
    if subset.empty:
        raise SystemExit(f"Missing screener row for {symbol}")
    return subset.iloc[0]


def load_feature_summary(symbol: str, timeframe: str) -> dict[str, Any]:
    path = FEATURE_REPORT_DIR / symbol.upper() / f"{normalize_timeframe(timeframe)}_summary.json"
    payload = load_json_if_exists(path)
    if not payload:
        raise SystemExit(f"Missing feature summary: {path}")
    latest = payload.get("latest") or {}
    latest["row_count"] = payload.get("row_count")
    latest["first_candle_utc"] = payload.get("first_candle_utc")
    latest["last_candle_utc"] = payload.get("last_candle_utc")
    latest["internal_symbol"] = payload.get("internal_symbol", symbol.upper())
    latest["timeframe"] = payload.get("timeframe", normalize_timeframe(timeframe))
    return latest


def processed_input_path(symbol: str, timeframe: str) -> Path:
    base_dir = PROCESSED_DIR / symbol.upper()
    parquet_path = base_dir / f"{normalize_timeframe(timeframe)}.parquet"
    csv_path = base_dir / f"{normalize_timeframe(timeframe)}.csv"
    if parquet_path.exists():
        return parquet_path
    return csv_path


def load_price_frame(symbol: str, timeframe: str) -> pd.DataFrame:
    path = processed_input_path(symbol, timeframe)
    if not path.exists():
        return pd.DataFrame()
    frame = read_existing_dataframe(path)
    if frame.empty:
        return frame
    frame = frame.sort_values("timestamp_ms").drop_duplicates(subset=["timestamp_ms"], keep="last").reset_index(drop=True)
    for col in ["open", "high", "low", "close", "volume", "turnover"]:
        frame[col] = pd.to_numeric(frame[col], errors="coerce")
    return frame


def recent_structure_levels(frame: pd.DataFrame, lookback: int = 7) -> dict[str, float | None]:
    if frame.empty:
        return {"recent_low": None, "recent_high": None, "recent_close": None, "range": None}
    sample = frame.tail(max(3, lookback)).copy()
    recent_low = safe_float(sample["low"].min())
    recent_high = safe_float(sample["high"].max())
    range_value = None
    if recent_low is not None and recent_high is not None:
        range_value = recent_high - recent_low
    return {
        "recent_low": recent_low,
        "recent_high": recent_high,
        "recent_close": safe_float(sample.iloc[-1]["close"]),
        "range": range_value,
    }


def load_context_doc(base_name: str, symbol: str | None = None) -> dict[str, Any] | None:
    candidates: list[Path] = []
    if symbol:
        candidates.append(CONTEXT_DIR / f"{base_name}_{symbol.upper()}_latest.json")
    candidates.append(CONTEXT_DIR / f"{base_name}_latest.json")
    for path in candidates:
        payload = load_json_if_exists(path)
        if payload is not None:
            return payload
    return None


def load_macro_context(symbol: str | None = None) -> dict[str, Any] | None:
    return load_context_doc("macro_context", symbol=symbol)


def load_news_context(symbol: str | None = None) -> dict[str, Any] | None:
    return load_context_doc("news_context", symbol=symbol)


def load_sentiment_context(symbol: str | None = None) -> dict[str, Any] | None:
    return load_context_doc("sentiment_context", symbol=symbol)


def load_asset_overlay(symbol: str) -> dict[str, Any] | None:
    return load_json_if_exists(ASSET_OVERLAY_DIR / f"{symbol.upper()}_latest.json")


SETUP_STYLE_MAP = {
    "LONG_MEANREV": "DIP_LADDER",
    "LONG_CONTINUATION": "BREAKOUT",
    "SHORT_MEANREV": "SELL_RALLY",
    "SHORT_CONTINUATION": "BREAKDOWN",
}


def infer_direction(best_setup: str, direction_bias: str) -> str:
    forced = str(direction_bias or "AUTO").upper()
    if forced in {"LONG", "SHORT"}:
        return forced
    return "LONG" if str(best_setup).upper().startswith("LONG") else "SHORT"


def infer_trade_style(best_setup: str, preferred_style: str) -> tuple[str, str | None]:
    preferred = str(preferred_style or "AUTO").upper()
    default_style = SETUP_STYLE_MAP.get(str(best_setup).upper(), "DIP_LADDER")
    if preferred == "AUTO":
        return default_style, None
    note = None
    if preferred != default_style:
        note = f"Preferred execution style overrides screener-implied style ({default_style} -> {preferred})."
    return preferred, note


def backup_trade_style(primary: str, direction: str) -> str:
    primary = str(primary).upper()
    direction = str(direction).upper()
    if direction == "LONG":
        return "BREAKOUT" if primary == "DIP_LADDER" else "DIP_LADDER"
    return "BREAKDOWN" if primary == "SELL_RALLY" else "SELL_RALLY"


def resolve_risk_budget(equity_usdt: float | None, risk_budget_usdt: float | None, brb_percent: float | None) -> tuple[float, dict[str, Any]]:
    candidates: list[tuple[str, float]] = []
    if risk_budget_usdt is not None:
        candidates.append(("RISK_BUDGET_USDT", float(risk_budget_usdt)))
    if equity_usdt is not None and brb_percent is not None:
        candidates.append(("BRB_PERCENT", float(equity_usdt) * float(brb_percent) / 100.0))
    if not candidates:
        candidates.append(("DEFAULT_RISK_BUDGET_USDT", 150.0))
    source, value = min(candidates, key=lambda item: item[1])
    return float(value), {
        "source": source,
        "provided_risk_budget_usdt": risk_budget_usdt,
        "provided_brb_percent": brb_percent,
    }


def invalidation_buffer_pct(close: float | None, atr_14: float | None) -> float:
    atr_buffer = 0.0
    if close and atr_14:
        atr_buffer = 0.15 * float(atr_14) / float(close)
    return float(max(0.0025, min(0.01, atr_buffer)))


def infer_invalidation(direction: str, d1: dict[str, Any], row: pd.Series, d1_frame: pd.DataFrame | None = None) -> dict[str, Any]:
    direction = str(direction).upper()
    close = safe_float(d1.get("close")) or safe_float(row.get("d1_close")) or safe_float(row.get("h4_close"))
    atr = safe_float(d1.get("atr_14"))
    buffer_pct = invalidation_buffer_pct(close, atr)
    structure = recent_structure_levels(d1_frame if d1_frame is not None else pd.DataFrame(), lookback=7)

    if direction == "LONG":
        candidates = [
            ("D1_RECENT_7BAR_LOW", structure.get("recent_low"), "HIGH"),
            ("D1_PIVOT_SUPPORT", safe_float(d1.get("pivot_support")) or safe_float(row.get("d1_pivot_support")), "MEDIUM"),
            ("D1_ATR_FALLBACK", (close - 2.0 * atr) if close is not None and atr is not None else None, "LOW"),
        ]
        selected = next(((basis, level, confidence) for basis, level, confidence in candidates if level is not None and close is not None and level < close), None)
        if selected is None:
            raise SystemExit("Unable to infer long invalidation level.")
        basis, base_level, confidence = selected
        buffered = base_level * (1.0 - buffer_pct)
    else:
        candidates = [
            ("D1_RECENT_7BAR_HIGH", structure.get("recent_high"), "HIGH"),
            ("D1_PIVOT_RESISTANCE", safe_float(d1.get("pivot_resistance")) or safe_float(row.get("d1_pivot_resistance")), "MEDIUM"),
            ("D1_ATR_FALLBACK", (close + 2.0 * atr) if close is not None and atr is not None else None, "LOW"),
        ]
        selected = next(((basis, level, confidence) for basis, level, confidence in candidates if level is not None and close is not None and level > close), None)
        if selected is None:
            raise SystemExit("Unable to infer short invalidation level.")
        basis, base_level, confidence = selected
        buffered = base_level * (1.0 + buffer_pct)

    return {
        "direction": direction,
        "level": round_price(base_level, 4),
        "buffer_pct": buffer_pct,
        "buffered_level": round_price(buffered, 4),
        "basis": basis,
        "confidence": confidence,
    }


def build_key_levels(direction: str, h4: dict[str, Any], d1: dict[str, Any], invalidation: dict[str, Any]) -> list[dict[str, Any]]:
    current = safe_float(h4.get("close")) or safe_float(d1.get("close"))
    h4_atr = safe_float(h4.get("atr_14")) or 0.0
    h4_support = safe_float(h4.get("pivot_support"))
    h4_resistance = safe_float(h4.get("pivot_resistance"))
    d1_support = safe_float(d1.get("pivot_support"))
    d1_resistance = safe_float(d1.get("pivot_resistance"))
    disaster = safe_float(invalidation.get("buffered_level"))

    supports: list[tuple[str, float, str]] = []
    resistances: list[tuple[str, float, str]] = []

    def add(bucket: list[tuple[str, float, str]], label: str, level: float | None, note: str) -> None:
        if level is not None and math.isfinite(level):
            bucket.append((label, float(level), note))

    add(supports, "S1", h4_support, "4h pivot support")
    add(supports, "S2", d1_support, "1d pivot support")
    add(resistances, "R1", h4_resistance, "4h pivot resistance")
    add(resistances, "R2", d1_resistance, "1d pivot resistance")
    if direction == "LONG":
        add(supports, "S3", disaster, "buffered disaster SL")
    else:
        add(resistances, "R4", disaster, "buffered disaster SL")
    if current is not None and h4_atr:
        add(resistances, "R3", current + 1.5 * h4_atr, "ATR stretch objective")
        add(supports, "S4", current - 1.5 * h4_atr, "ATR pullback objective")

    supports = sorted({(a, round_price(b, 4), c) for a, b, c in supports if b is not None}, key=lambda item: item[1], reverse=True)
    resistances = sorted({(a, round_price(b, 4), c) for a, b, c in resistances if b is not None}, key=lambda item: item[1])

    rows: list[dict[str, Any]] = []
    for label, price, note in supports[:3]:
        rows.append({"type": "SUPPORT", "label": label, "price": price, "note": note})
    for label, price, note in resistances[:3]:
        rows.append({"type": "RESISTANCE", "label": label, "price": price, "note": note})
    return rows


def peak_risk(best_setup: str, direction: str, row: pd.Series, h4: dict[str, Any], d1: dict[str, Any], overlay: dict[str, Any] | None) -> dict[str, Any]:
    score = 0
    bullets: list[str] = []

    event_risk = str((overlay or {}).get("event_risk_next_24h") or "LOW").upper()
    if event_risk == "HIGH":
        score += 2
        bullets.append("Macro event risk is HIGH, so leverage and deployment should be capped.")

    daily_quality = str(row.get("daily_quality_label") or "UNKNOWN").upper()
    if daily_quality in {"WEAK", "INSUFFICIENT"}:
        score += 1
        bullets.append(f"Daily data quality is {daily_quality}, so conviction should be discounted.")

    h4_rsi = safe_float(h4.get("rsi_14"))
    if direction == "LONG" and h4_rsi is not None and h4_rsi >= 68:
        score += 2
        bullets.append(f"4h RSI is stretched ({h4_rsi:.1f}), which raises pullback risk for fresh longs.")
    if direction == "SHORT" and h4_rsi is not None and h4_rsi <= 32:
        score += 2
        bullets.append(f"4h RSI is compressed ({h4_rsi:.1f}), which raises squeeze risk for fresh shorts.")
    if direction == "SHORT" and h4_rsi is not None and h4_rsi >= 68:
        bullets.append(f"4h RSI is elevated ({h4_rsi:.1f}), which supports a tactical fade thesis.")
    if direction == "LONG" and h4_rsi is not None and h4_rsi <= 32:
        bullets.append(f"4h RSI is depressed ({h4_rsi:.1f}), which supports a tactical rebound thesis.")

    h4_side = str(h4.get("dominant_side") or row.get("h4_dominant_side") or "UNKNOWN").upper()
    d1_side = str(d1.get("dominant_side") or row.get("d1_dominant_side") or "UNKNOWN").upper()
    h4_adx_label = str(h4.get("adx_regime_label") or row.get("h4_adx_regime_label") or "UNKNOWN").upper()

    if direction == "SHORT" and h4_side == "LONG" and d1_side == "LONG":
        score += 2
        bullets.append("Both 4h and 1d still lean LONG, so any short is countertrend.")
    if direction == "LONG" and h4_side == "SHORT" and d1_side == "SHORT":
        score += 2
        bullets.append("Both 4h and 1d still lean SHORT, so any long is countertrend.")
    if h4_adx_label == "TRENDING" and ((direction == "SHORT" and h4_side == "LONG") or (direction == "LONG" and h4_side == "SHORT")):
        score += 1
        bullets.append("4h ADX is TRENDING against the planned direction, which increases failure risk.")

    if str(best_setup).upper().endswith("MEANREV"):
        score += 1
        bullets.append("Mean-reversion setups decay faster than continuation setups and need cleaner execution.")

    directional_barrier = safe_float(row.get("h4_dist_to_resistance_pct")) if direction == "LONG" else safe_float(row.get("h4_dist_to_support_pct"))
    if directional_barrier is not None and directional_barrier <= 0.015:
        score += 1
        bullets.append("Price is very close to the nearest opposing 4h barrier, so room may be constrained.")

    if score >= 5:
        label = "HIGH"
        action = "Cap leverage at x3, keep more dry powder, and prefer confirmation over aggression."
    elif score >= 3:
        label = "MED"
        action = "Use standard caution, smaller initial size, and only add if price confirms."
    else:
        label = "LOW"
        action = "Normal sizing is acceptable if the structure remains intact."

    bullets = bullets[:6]
    if not bullets:
        bullets.append("No major stress flags fired; use normal structure discipline.")

    return {"label": label, "score": score, "action": action, "bullets": bullets}


def risk_fraction(peak_risk_label: str, event_risk_24h: str) -> float:
    label = str(peak_risk_label).upper()
    event = str(event_risk_24h).upper()
    if label == "HIGH" or event == "HIGH":
        return 0.50
    if label == "MED":
        return 0.75
    return 1.00


def recommended_deploy_fraction(peak_risk_label: str, event_risk_24h: str) -> float:
    label = str(peak_risk_label).upper()
    event = str(event_risk_24h).upper()
    if label == "HIGH" or event == "HIGH":
        return 0.45
    if label == "MED":
        return 0.60
    return 0.70


def effective_leverage_cap(peak_risk_label: str, event_risk_24h: str) -> int:
    label = str(peak_risk_label).upper()
    event = str(event_risk_24h).upper()
    if label == "HIGH" or event == "HIGH":
        return 3
    if label == "MED":
        return 4
    return 5


def scenario_probabilities(best_setup: str) -> tuple[int, int]:
    setup = str(best_setup).upper()
    if setup.startswith("LONG_CONTINUATION") or setup.startswith("SHORT_CONTINUATION"):
        return 60, 40
    return 55, 45


def quality_note(row: pd.Series, direction: str) -> dict[str, Any]:
    direction = str(direction).upper()
    score_field = "overall_long_score" if direction == "LONG" else "overall_short_score"
    rank_field = f"{score_field}_rank"
    return {
        "score": safe_float(row.get(score_field)),
        "rank": safe_int(row.get(rank_field)),
        "best_score_rank": safe_int(row.get("best_score_rank")),
        "conviction_label": str(row.get("conviction_label") or "UNKNOWN").upper(),
        "daily_quality_label": str(row.get("daily_quality_label") or "UNKNOWN").upper(),
        "daily_quality_factor": safe_float(row.get("daily_quality_factor")),
    }


def candidate_entries(direction: str, trade_style: str, h4: dict[str, Any], invalidation: dict[str, Any], max_levels: int) -> list[tuple[str, str, float]]:
    direction = str(direction).upper()
    trade_style = str(trade_style).upper()
    close = safe_float(h4.get("close"))
    atr = safe_float(h4.get("atr_14")) or (close * 0.02 if close else 0.0)
    support = safe_float(h4.get("pivot_support"))
    resistance = safe_float(h4.get("pivot_resistance"))
    sl = safe_float(invalidation.get("buffered_level"))
    if close is None or sl is None:
        raise SystemExit("Missing close or invalidation for entry generation.")

    levels: list[tuple[str, str, float]] = []

    if direction == "LONG" and trade_style == "DIP_LADDER":
        anchor = support if support is not None else close - 0.8 * atr
        l1 = min(close, max(anchor * 1.03, close - 0.30 * atr))
        l2 = max(anchor * 1.01, close - 0.70 * atr)
        l3 = max(sl * 1.03, anchor * 1.002, close - 1.05 * atr)
        for idx, price in enumerate([l1, l2, l3][:max_levels], start=1):
            if price > sl:
                levels.append((f"L{idx}", "LIMIT", round_price(price, 4)))

    elif direction == "SHORT" and trade_style == "SELL_RALLY":
        anchor = resistance if resistance is not None else close + 0.8 * atr
        l1 = max(close, min(anchor * 0.97, close + 0.30 * atr))
        l2 = min(anchor * 0.995, close + 0.70 * atr)
        l3 = min(sl * 0.97, anchor * 0.999, close + 1.05 * atr)
        for idx, price in enumerate([l1, l2, l3][:max_levels], start=1):
            if price < sl:
                levels.append((f"L{idx}", "LIMIT", round_price(price, 4)))

    elif direction == "LONG" and trade_style == "BREAKOUT":
        trigger = max(close + 0.20 * atr, (resistance or close) + 0.12 * atr)
        levels.append(("L1", "STOP-LIMIT", round_price(trigger, 4)))

    else:  # SHORT BREAKDOWN
        trigger = min(close - 0.20 * atr, (support or close) - 0.12 * atr)
        levels.append(("L1", "STOP-LIMIT", round_price(trigger, 4)))

    deduped: list[tuple[str, str, float]] = []
    seen: set[float] = set()
    for level, order_type, price in levels:
        if price not in seen:
            seen.add(price)
            deduped.append((level, order_type, price))
    return deduped


def target_levels(
    direction: str,
    trade_style: str,
    h4: dict[str, Any],
    d1: dict[str, Any],
    reference_entry: float,
    h4_frame: pd.DataFrame | None = None,
    d1_frame: pd.DataFrame | None = None,
) -> tuple[float | None, float | None]:
    direction = str(direction).upper()
    trade_style = str(trade_style).upper()
    atr = safe_float(h4.get("atr_14")) or (reference_entry * 0.02)
    h4_support = safe_float(h4.get("pivot_support"))
    h4_resistance = safe_float(h4.get("pivot_resistance"))
    d1_support = safe_float(d1.get("pivot_support"))
    d1_resistance = safe_float(d1.get("pivot_resistance"))
    h4_recent = recent_structure_levels(h4_frame if h4_frame is not None else pd.DataFrame(), lookback=20)
    d1_recent = recent_structure_levels(d1_frame if d1_frame is not None else pd.DataFrame(), lookback=20)
    h4_range = safe_float(h4_recent.get("range")) or (2.0 * atr)
    d1_range = safe_float(d1_recent.get("range")) or (3.0 * atr)

    if direction == "LONG" and trade_style == "BREAKOUT":
        recent_high = safe_float(h4_recent.get("recent_high")) or h4_resistance or reference_entry
        tp1 = max(reference_entry + 0.80 * atr, recent_high + 0.20 * atr, reference_entry + 0.35 * h4_range)
        higher_d1 = safe_float(d1_recent.get("recent_high"))
        tp2 = max(tp1 + 0.90 * atr, reference_entry + 0.65 * h4_range, (higher_d1 + 0.35 * atr) if higher_d1 is not None else tp1 + 1.4 * atr, reference_entry + 0.35 * d1_range)
    elif direction == "SHORT" and trade_style == "BREAKDOWN":
        recent_low = safe_float(h4_recent.get("recent_low")) or h4_support or reference_entry
        tp1 = min(reference_entry - 0.80 * atr, recent_low - 0.20 * atr, reference_entry - 0.35 * h4_range)
        lower_d1 = safe_float(d1_recent.get("recent_low"))
        tp2 = min(tp1 - 0.90 * atr, reference_entry - 0.65 * h4_range, (lower_d1 - 0.35 * atr) if lower_d1 is not None else tp1 - 1.4 * atr, reference_entry - 0.35 * d1_range)
    elif direction == "LONG":
        candidates_tp1 = [value for value in [h4_resistance, safe_float(h4_recent.get("recent_high")), reference_entry + 0.9 * atr] if value is not None and value > reference_entry]
        tp1 = min(candidates_tp1) if candidates_tp1 else reference_entry + 0.9 * atr
        candidates_tp2 = [value for value in [d1_resistance, safe_float(d1_recent.get("recent_high")), tp1 + 1.1 * atr, reference_entry + 0.50 * d1_range] if value is not None and value > tp1]
        tp2 = min(candidates_tp2) if candidates_tp2 else tp1 + 1.4 * atr
    else:
        candidates_tp1 = [value for value in [h4_support, safe_float(h4_recent.get("recent_low")), reference_entry - 0.9 * atr] if value is not None and value < reference_entry]
        tp1 = max(candidates_tp1) if candidates_tp1 else reference_entry - 0.9 * atr
        candidates_tp2 = [value for value in [d1_support, safe_float(d1_recent.get("recent_low")), tp1 - 1.1 * atr, reference_entry - 0.50 * d1_range] if value is not None and value < tp1]
        tp2 = max(candidates_tp2) if candidates_tp2 else tp1 - 1.4 * atr

    return round_price(tp1, 4), round_price(tp2, 4)


def stop_dist_pct(direction: str, entry: float, sl: float) -> float:
    direction = str(direction).upper()
    if direction == "LONG":
        return max(0.0, (entry - sl) / entry)
    return max(0.0, (sl - entry) / entry)


def compute_rr(direction: str, entry: float, sl: float, tp: float | None) -> float | None:
    if tp is None:
        return None
    risk = abs(entry - sl)
    if risk <= 0:
        return None
    reward = abs(tp - entry)
    return reward / risk


def weighted_average_entry(orders: list[dict[str, Any]]) -> float | None:
    total_notional = sum(float(item.get("notional_usdt") or 0.0) for item in orders)
    if total_notional <= 0:
        return None
    return sum(float(item.get("entry") or 0.0) * float(item.get("notional_usdt") or 0.0) for item in orders) / total_notional


def build_orders(
    direction: str,
    trade_style: str,
    h4: dict[str, Any],
    d1: dict[str, Any],
    h4_frame: pd.DataFrame,
    d1_frame: pd.DataFrame,
    invalidation: dict[str, Any],
    free_margin_usdt: float,
    risk_budget_usdt: float,
    peak_risk_label: str,
    event_risk_24h: str,
    max_ladder_levels: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    direction = str(direction).upper()
    sl = safe_float(invalidation.get("buffered_level"))
    if sl is None:
        raise SystemExit("Cannot build plan without an invalidation level.")

    entries = candidate_entries(direction, trade_style, h4, invalidation, max_levels=max_ladder_levels)
    if not entries:
        raise SystemExit("No valid entries could be generated.")

    alloc_map = {
        1: [1.0],
        2: [0.55, 0.45],
        3: [0.40, 0.35, 0.25],
    }
    risk_fraction_used = risk_fraction(peak_risk_label, event_risk_24h)
    effective_risk_budget = risk_budget_usdt * risk_fraction_used
    risk_allocations = alloc_map[len(entries)]

    initial_rows: list[dict[str, Any]] = []
    for idx, (level, order_type, entry) in enumerate(entries):
        dist_pct = stop_dist_pct(direction, entry, sl)
        if dist_pct <= 0:
            continue
        order_risk_budget = effective_risk_budget * risk_allocations[idx]
        notional = order_risk_budget / dist_pct
        initial_rows.append(
            {
                "level": level,
                "order_type": order_type,
                "entry": entry,
                "stop_dist_pct": dist_pct,
                "risk_budget_usdt": order_risk_budget,
                "notional_usdt": notional,
            }
        )

    if not initial_rows:
        raise SystemExit("Entries failed structural stop validation.")

    target_deploy_fraction = recommended_deploy_fraction(peak_risk_label, event_risk_24h)
    target_margin_cap = free_margin_usdt * target_deploy_fraction
    hard_margin_cap = free_margin_usdt * 0.80
    max_margin_cap = min(target_margin_cap, hard_margin_cap)
    total_notional = sum(item["notional_usdt"] for item in initial_rows)

    leverage_cap = effective_leverage_cap(peak_risk_label, event_risk_24h)
    required_leverage = max(1, math.ceil(total_notional / max(max_margin_cap, 1.0)))
    leverage = clamp_int(required_leverage, 1, leverage_cap)

    total_margin = total_notional / leverage
    if total_margin > hard_margin_cap:
        scale = (hard_margin_cap * leverage) / total_notional
        for item in initial_rows:
            item["notional_usdt"] *= scale
            item["risk_budget_usdt"] *= scale
        total_notional = sum(item["notional_usdt"] for item in initial_rows)
        total_margin = total_notional / leverage

    orders: list[dict[str, Any]] = []
    for item in initial_rows:
        margin_usdt = item["notional_usdt"] / leverage
        tp1, tp2 = target_levels(direction, trade_style, h4, d1, reference_entry=float(item["entry"]), h4_frame=h4_frame, d1_frame=d1_frame)
        risk_usdt = item["notional_usdt"] * item["stop_dist_pct"]
        trail_distance = max((safe_float(h4.get("atr_14")) or (float(item["entry"]) * 0.02)) * 0.5, float(item["entry"]) * 0.003)
        orders.append(
            {
                "level": item["level"],
                "order_type": item["order_type"],
                "entry": round_price(item["entry"], 4),
                "size_pct_of_deployable_margin": None,
                "margin_usdt": round_price(margin_usdt, 2),
                "leverage": float(leverage),
                "notional_usdt": round_price(item["notional_usdt"], 2),
                "sl": round_price(sl, 4),
                "tp1": tp1,
                "rr_tp1": round_price(compute_rr(direction, float(item["entry"]), sl, tp1), 2),
                "tp2": tp2,
                "rr_tp2": round_price(compute_rr(direction, float(item["entry"]), sl, tp2), 2),
                "trail_trigger": tp1,
                "trail_distance": round_price(trail_distance, 4),
                "risk_usdt": round_price(risk_usdt, 2),
                "stop_dist_pct": item["stop_dist_pct"],
            }
        )

    deployable_margin = sum(float(item.get("margin_usdt") or 0.0) for item in orders)
    for item in orders:
        if deployable_margin > 0:
            item["size_pct_of_deployable_margin"] = round_price(float(item["margin_usdt"]) / deployable_margin * 100.0, 2)

    avg_entry = weighted_average_entry(orders)
    total_risk = sum(float(item.get("risk_usdt") or 0.0) for item in orders)
    summary = {
        "estimated_average_entry": round_price(avg_entry, 4),
        "total_margin_usdt": round_price(deployable_margin, 2),
        "deployable_margin_used_pct_of_free_margin": round_price(deployable_margin / free_margin_usdt * 100.0 if free_margin_usdt else 0.0, 2),
        "estimated_total_risk_usdt": round_price(total_risk, 2),
        "pass_vs_risk_budget": "YES" if total_risk <= risk_budget_usdt + 1e-9 else "NO",
        "size_fraction_of_risk_budget": round_price(risk_fraction_used, 2),
        "recommended_deploy_fraction": round_price(target_deploy_fraction, 2),
        "leverage_cap": leverage_cap,
        "effective_risk_budget_usdt": round_price(effective_risk_budget, 2),
    }
    return orders, summary


def market_state(direction: str, row: pd.Series, h4: dict[str, Any], d1: dict[str, Any]) -> dict[str, Any]:
    return {
        "h4_trend": str(h4.get("trend_regime") or row.get("h4_trend_regime") or "UNKNOWN").upper(),
        "d1_trend": str(d1.get("trend_regime") or row.get("d1_trend_regime") or "UNKNOWN").upper(),
        "h4_side": str(h4.get("dominant_side") or row.get("h4_dominant_side") or "UNKNOWN").upper(),
        "d1_side": str(d1.get("dominant_side") or row.get("d1_dominant_side") or "UNKNOWN").upper(),
        "volatility_regime": str(h4.get("vol_regime_label") or "UNKNOWN").upper(),
        "adx_regime": str(h4.get("adx_regime_label") or row.get("h4_adx_regime_label") or "UNKNOWN").upper(),
        "direction": direction,
    }


def build_outlook(direction: str, best_setup: str, row: pd.Series, h4: dict[str, Any], d1: dict[str, Any], orders: list[dict[str, Any]]) -> list[dict[str, Any]]:
    current = safe_float(h4.get("close")) or safe_float(row.get("h4_close")) or 0.0
    first_entry = safe_float((orders[0] if orders else {}).get("entry")) or current
    tp2 = safe_float((orders[0] if orders else {}).get("tp2"))
    support = safe_float(h4.get("pivot_support")) or safe_float(row.get("h4_pivot_support"))
    resistance = safe_float(h4.get("pivot_resistance")) or safe_float(row.get("h4_pivot_resistance"))
    cont_prob, pullback_prob = scenario_probabilities(best_setup)

    higher_target = tp2 if tp2 is not None else (resistance or current * 1.05)
    lower_target = support if support is not None else current * 0.95

    upside_pct = ((higher_target - current) / current * 100.0) if current else None
    downside_pct = ((lower_target - current) / current * 100.0) if current else None

    if direction == "SHORT":
        primary_title = "Bearish follow-through / lower reset"
        primary_trigger = f"Lose {fmt_num(first_entry, 4)} and fail to reclaim the 4h reaction zone."
        secondary_title = "Squeeze / continuation higher"
        secondary_trigger = f"Accept back above {fmt_num(resistance, 4)} or invalidate the fade structure."
    else:
        primary_title = "Bullish continuation higher"
        primary_trigger = f"Hold above {fmt_num(first_entry, 4)} and reclaim/extend through the next 4h resistance."
        secondary_title = "Pullback / retrace first"
        secondary_trigger = f"Reject near {fmt_num(resistance, 4)} or lose the first ladder support before rebasing."

    return [
        {
            "scenario": primary_title,
            "probability_pct": cont_prob if direction == ("LONG" if str(best_setup).upper().startswith("LONG") else "SHORT") else pullback_prob,
            "expected_move_pct": round_price(abs(upside_pct) if upside_pct is not None else 0.0, 2),
            "trigger": primary_trigger,
        },
        {
            "scenario": secondary_title,
            "probability_pct": 100 - (cont_prob if direction == ("LONG" if str(best_setup).upper().startswith("LONG") else "SHORT") else pullback_prob),
            "expected_move_pct": round_price(abs(downside_pct) if downside_pct is not None else 0.0, 2),
            "trigger": secondary_trigger,
        },
    ]


def macro_news_block(symbol: str, overlay: dict[str, Any] | None, macro_context: dict[str, Any] | None, news_context: dict[str, Any] | None, sentiment_context: dict[str, Any] | None) -> dict[str, Any]:
    asset_news = (((news_context or {}).get("asset_news") or {}).get(symbol.upper()) or {})
    macro_events = (macro_context or {}).get("upcoming_events") or (macro_context or {}).get("bea_schedule") or []
    crypto_fg = ((sentiment_context or {}).get("crypto_fear_greed") or {})
    top_headlines = (overlay or {}).get("top_headlines") or asset_news.get("top_headlines") or []
    event_rows = []
    for item in macro_events[:5]:
        event_rows.append(
            {
                "title": item.get("title") or item.get("name") or "Event",
                "scheduled_at_utc": item.get("scheduled_at_utc") or item.get("published_at_utc"),
                "importance": item.get("importance") or item.get("kind") or "scheduled",
            }
        )

    fundamental_availability = "PROXY_ONLY"
    asset_class = str((overlay or {}).get("asset_class") or "other")
    if asset_class in {"equity_single_name", "equity_index"}:
        fundamental_note = "Company/index context is news-driven in v1; no earnings/valuation feed is wired yet."
    elif asset_class in {"precious_metals", "industrial_metal", "energy", "crypto"}:
        fundamental_note = "Macro/flows/news context is available; classic corporate fundamentals are not applicable or not wired."
    else:
        fundamental_note = "Only macro/news proxy context is available in v1."

    return {
        "macro_alignment": (overlay or {}).get("macro_alignment"),
        "headline_pressure": (overlay or {}).get("headline_pressure"),
        "event_risk_next_24h": (overlay or {}).get("event_risk_next_24h") or (macro_context or {}).get("event_risk_next_24h"),
        "event_risk_next_72h": (overlay or {}).get("event_risk_next_72h") or (macro_context or {}).get("event_risk_next_72h"),
        "official_macro_bias": (macro_context or {}).get("official_macro_bias"),
        "sentiment_state": (overlay or {}).get("sentiment_state") or (crypto_fg.get("state_label") if crypto_fg else None),
        "decision_posture": (overlay or {}).get("decision_posture"),
        "decision_note": (overlay or {}).get("decision_note"),
        "top_headlines": top_headlines[:5],
        "scheduled_events": event_rows,
        "fundamental_availability": fundamental_availability,
        "fundamental_note": fundamental_note,
        "news_volume": asset_news.get("news_volume"),
    }


def should_reject(row: pd.Series, direction: str, best_setup: str, orders: list[dict[str, Any]], summary: dict[str, Any]) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    daily_quality = str(row.get("daily_quality_label") or "UNKNOWN").upper()
    if daily_quality == "INSUFFICIENT":
        reasons.append("Daily quality is INSUFFICIENT.")

    if not orders:
        reasons.append("No valid orders were generated.")

    if summary.get("pass_vs_risk_budget") != "YES":
        reasons.append("Plan fails the risk budget check.")

    setup = str(best_setup).upper()
    rr_tp1_values = [safe_float(item.get("rr_tp1")) for item in orders if safe_float(item.get("rr_tp1")) is not None]
    rr_tp2_values = [safe_float(item.get("rr_tp2")) for item in orders if safe_float(item.get("rr_tp2")) is not None]
    best_rr_tp1 = max(rr_tp1_values) if rr_tp1_values else None
    best_rr_tp2 = max(rr_tp2_values) if rr_tp2_values else None

    if "CONTINUATION" in setup:
        if (best_rr_tp2 is None or best_rr_tp2 < 1.0) and (best_rr_tp1 is None or best_rr_tp1 < 0.7):
            reasons.append("Continuation setup has insufficient projected reward-to-risk.")
    else:
        if (best_rr_tp2 is None or best_rr_tp2 < 1.1) and (best_rr_tp1 is None or best_rr_tp1 < 0.9):
            reasons.append("Mean-reversion setup has insufficient projected reward-to-risk.")

    stop_dists = [safe_float(item.get("stop_dist_pct")) for item in orders if safe_float(item.get("stop_dist_pct")) is not None]
    if stop_dists and min(stop_dists) > 0.25:
        reasons.append("Required stop distance is too wide for a practical swing plan.")

    setup = str(best_setup).upper()
    if direction == "LONG" and setup.startswith("SHORT_CONTINUATION"):
        reasons.append("Forced long conflicts with a short continuation board read.")
    if direction == "SHORT" and setup.startswith("LONG_CONTINUATION"):
        reasons.append("Forced short conflicts with a long continuation board read.")

    return bool(reasons), reasons


def classify_orderability(reject: bool, reject_reasons: list[str], orders: list[dict[str, Any]]) -> dict[str, Any]:
    order_types = sorted({str(item.get("order_type") or "").upper() for item in orders if item.get("order_type")})
    has_market = any(item == "MARKET" for item in order_types)
    has_limit = any(item == "LIMIT" for item in order_types)
    has_stop_entry = any("STOP" in item for item in order_types)

    if reject or not orders:
        why = reject_reasons[0] if reject_reasons else "No valid executable order structure was generated yet."
        return {
            "decision": "not_placeable_yet",
            "market_order_now": False,
            "ladder_limit_orders": False,
            "stop_entry_orders": False,
            "allowed_order_types": order_types,
            "why": why,
        }

    if has_market:
        why = "A market-style executable order exists now; immediate execution is permissible if the live structure still matches the plan."
        if has_limit or has_stop_entry:
            why += " Conditional orders are also available as alternatives."
        return {
            "decision": "placeable_now",
            "market_order_now": True,
            "ladder_limit_orders": has_limit,
            "stop_entry_orders": has_stop_entry,
            "allowed_order_types": order_types,
            "why": why,
        }

    if has_limit and has_stop_entry:
        why = "The setup is executable only via resting conditional orders; ladder limits and stop-entry logic are both valid, but no market-now order is justified."
    elif has_limit:
        why = "The setup is executable only via resting limit orders into the planned zone; no market-now order is justified."
    elif has_stop_entry:
        why = "The setup is executable only via stop-entry / breakout-breakdown confirmation; no market-now order is justified."
    else:
        why = "Orders exist, but they do not yet map cleanly to an immediate market order; treat the setup as conditional-only."

    return {
        "decision": "placeable_conditional_only",
        "market_order_now": False,
        "ladder_limit_orders": has_limit,
        "stop_entry_orders": has_stop_entry,
        "allowed_order_types": order_types,
        "why": why,
    }


def build_do_now_checklist(report: dict[str, Any]) -> list[str]:
    decision = report["decision"]
    orders = report.get("orders") or []
    first = orders[0] if orders else {}
    orderability = report.get("orderability_decision") or {}
    checklist = [
        f"Confirm {report['symbol']} still matches the {decision['trade_type']} read before placing anything.",
        f"Use the disaster SL at {fmt_num(decision['invalidation'], 4)} and do not tighten it just to fit size.",
        f"Keep total risk at or below {fmt_num(report['risk_summary']['risk_budget_usdt'], 2)} USDT.",
        f"Start with the primary method ({decision['primary_entry_method']}); backup is {decision['backup_entry_method']}.",
        f"If event risk stays {decision['event_risk_24h']}, keep leverage <= x{decision['leverage_cap']} and avoid chasing.",
    ]
    if (orderability.get("decision") or "").lower() == "not_placeable_yet":
        checklist[0] = f"No resting order yet for {report['symbol']}; wait until the structure improves enough to become executable."
        checklist[3] = f"Current orderability: {orderability.get('decision')} — {orderability.get('why') or 'execution is not clean yet.'}"
        return checklist
    if first:
        checklist[0] = f"Check whether price is near the first planned order at {fmt_num(first.get('entry'), 4)} before placing the setup."
    if (orderability.get("decision") or "").lower() == "placeable_conditional_only":
        checklist[3] = f"Conditional-only setup: market-now={str(bool(orderability.get('market_order_now'))).upper()}, ladder-limits={str(bool(orderability.get('ladder_limit_orders'))).upper()}, stop-entry={str(bool(orderability.get('stop_entry_orders'))).upper()}."
    return checklist


def build_plan(
    symbol: str,
    frame: pd.DataFrame,
    free_margin_usdt: float,
    equity_usdt: float | None = None,
    risk_budget_usdt: float | None = None,
    brb_percent: float | None = None,
    direction_bias: str = "AUTO",
    preferred_style: str = "AUTO",
    horizon_days: int = 10,
    max_ladder_levels: int = 3,
) -> dict[str, Any]:
    row = screener_row(frame, symbol)
    best_setup = str(row.get("best_setup") or "UNKNOWN").upper()
    direction = infer_direction(best_setup, direction_bias)
    trade_style, style_note = infer_trade_style(best_setup, preferred_style)
    backup_style = backup_trade_style(trade_style, direction)

    h4 = load_feature_summary(symbol, "4h")
    d1 = load_feature_summary(symbol, "1d")
    h4_frame = load_price_frame(symbol, "4h")
    d1_frame = load_price_frame(symbol, "1d")
    overlay = load_asset_overlay(symbol)
    macro_context = load_macro_context(symbol)
    news_context = load_news_context(symbol)
    sentiment_context = load_sentiment_context(symbol)

    risk_budget_resolved, risk_meta = resolve_risk_budget(equity_usdt, risk_budget_usdt, brb_percent)
    invalidation = infer_invalidation(direction, d1, row, d1_frame=d1_frame)
    key_levels = build_key_levels(direction, h4, d1, invalidation)
    quality = quality_note(row, direction)
    peak = peak_risk(best_setup, direction, row, h4, d1, overlay)
    event_risk_24h = str((overlay or {}).get("event_risk_next_24h") or (macro_context or {}).get("event_risk_next_24h") or "LOW").upper()

    orders, order_summary = build_orders(
        direction=direction,
        trade_style=trade_style,
        h4=h4,
        d1=d1,
        h4_frame=h4_frame,
        d1_frame=d1_frame,
        invalidation=invalidation,
        free_margin_usdt=float(free_margin_usdt),
        risk_budget_usdt=float(risk_budget_resolved),
        peak_risk_label=peak["label"],
        event_risk_24h=event_risk_24h,
        max_ladder_levels=clamp_int(int(max_ladder_levels), 1, 3),
    )

    reject, reject_reasons = should_reject(row, direction, best_setup, orders, order_summary)
    orderability = classify_orderability(reject, reject_reasons, orders)
    macro_news = macro_news_block(symbol, overlay, macro_context, news_context, sentiment_context)
    outlook = build_outlook(direction, best_setup, row, h4, d1, orders)
    state = market_state(direction, row, h4, d1)

    total_risk = safe_float(order_summary.get("estimated_total_risk_usdt")) or 0.0
    estimated_loss_pct_equity = (total_risk / equity_usdt * 100.0) if equity_usdt else None
    average_entry = safe_float(order_summary.get("estimated_average_entry"))
    lead_order = orders[0] if orders else {}
    risk_bucket = "LOW"
    if peak["label"] == "HIGH" or event_risk_24h == "HIGH":
        risk_bucket = "HIGH"
    elif peak["label"] == "MED":
        risk_bucket = "MID"

    generated_at_utc = datetime.now(timezone.utc).replace(microsecond=0)
    generated_at_local = generated_at_utc.astimezone().replace(microsecond=0)

    notes: list[str] = []
    if style_note:
        notes.append(style_note)
    if reject_reasons:
        notes.extend(reject_reasons)
    decision_note = macro_news.get("decision_note")
    if decision_note:
        notes.append(str(decision_note))

    report = {
        "report_type": "TRADE_PLAN_DEEP_DIVE",
        "generated_at_utc": generated_at_utc.isoformat().replace("+00:00", "Z"),
        "generated_at_local": generated_at_local.isoformat(),
        "symbol": symbol.upper(),
        "mode": "deep",
        "inputs": {
            "free_margin_usdt": float(free_margin_usdt),
            "equity_usdt": equity_usdt,
            "risk_budget_usdt": round_price(risk_budget_resolved, 2),
            "risk_budget_meta": risk_meta,
            "direction_bias": str(direction_bias or "AUTO").upper(),
            "preferred_execution_style": str(preferred_style or "AUTO").upper(),
            "horizon_days": int(horizon_days),
            "max_ladder_levels": clamp_int(int(max_ladder_levels), 1, 3),
        },
        "source_context": {
            "best_setup": best_setup,
            "best_score": safe_float(row.get("best_score")),
            "best_score_rank": safe_int(row.get("best_score_rank")),
            "conviction_label": str(row.get("conviction_label") or "UNKNOWN").upper(),
            "decision_posture": macro_news.get("decision_posture") or "NO_CONTEXT",
            "screening_quality": quality,
        },
        "market_state": state,
        "macro_news_fundamental": macro_news,
        "key_levels": key_levels,
        "scenarios": outlook,
        "peak_risk": peak,
        "decision": {
            "trade_candidate": "NO" if reject else "YES",
            "direction": direction,
            "trade_type": best_setup,
            "primary_entry_method": trade_style,
            "backup_entry_method": backup_style,
            "entry_basis": "4H_EXECUTION_STRUCTURE",
            "sl_basis": invalidation.get("basis"),
            "invalidation": invalidation.get("buffered_level"),
            "event_risk_24h": event_risk_24h,
            "risk_bucket": risk_bucket,
            "quality_label": quality.get("conviction_label"),
            "quality_rank": quality.get("rank"),
            "leverage_cap": order_summary.get("leverage_cap"),
            "size_fraction_of_risk_budget": order_summary.get("size_fraction_of_risk_budget"),
            "size_note": (
                "Reduced because event/peak risk is elevated"
                if (order_summary.get("size_fraction_of_risk_budget") or 1.0) < 1.0
                else "Normal risk budget allowed"
            ),
        },
        "orderability_decision": orderability,
        "orders": orders,
        "risk_summary": {
            "risk_budget_usdt": round_price(risk_budget_resolved, 2),
            "estimated_total_loss_usdt": round_price(total_risk, 2),
            "estimated_total_loss_pct_equity": round_price(estimated_loss_pct_equity, 2),
            "pass_vs_risk_budget": "YES" if total_risk <= risk_budget_resolved + 1e-9 else "NO",
            "estimated_average_entry": average_entry,
            "deployable_margin_used_pct_of_free_margin": order_summary.get("deployable_margin_used_pct_of_free_margin"),
            "total_margin_usdt": order_summary.get("total_margin_usdt"),
        },
        "final_trade_setup": {
            "symbol": symbol.upper(),
            "direction": direction,
            "trade_type": best_setup,
            "screening_score": safe_float(row.get("best_score")),
            "screening_rank": safe_int(row.get("best_score_rank")),
            "quality": quality.get("conviction_label"),
            "risk": risk_bucket,
            "orderability_decision": orderability.get("decision"),
            "entry_zone": {
                "from": round_price(min(float(item.get("entry") or 0.0) for item in orders), 4) if orders else None,
                "to": round_price(max(float(item.get("entry") or 0.0) for item in orders), 4) if orders else None,
            },
            "estimated_average_entry": average_entry,
            "disaster_sl": invalidation.get("buffered_level"),
            "tp1": lead_order.get("tp1"),
            "tp2": lead_order.get("tp2"),
            "total_margin_usdt": order_summary.get("total_margin_usdt"),
            "estimated_total_loss_usdt": round_price(total_risk, 2),
            "estimated_total_loss_pct_equity": round_price(estimated_loss_pct_equity, 2),
            "size_fraction_of_risk_budget": order_summary.get("size_fraction_of_risk_budget"),
            "pass_vs_risk_budget": "YES" if total_risk <= risk_budget_resolved + 1e-9 else "NO",
            "decision_posture": macro_news.get("decision_posture"),
        },
        "notes": notes,
    }
    report["do_this_now"] = build_do_now_checklist(report)
    return report


def markdown_table(headers: list[str], rows: list[list[str]]) -> list[str]:
    if not rows:
        return ["- None"]
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return lines


def to_markdown(report: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append(f"# Trade Plan Deep Dive — {report['symbol']}")
    lines.append("")
    lines.append(f"Generated: {report['generated_at_local']} | UTC: {report['generated_at_utc']}")
    lines.append("")
    lines.append("## Snapshot")
    lines.append("")
    lines.append(f"- Direction: **{report['decision']['direction']}**")
    lines.append(f"- Trade type: **{report['decision']['trade_type']}**")
    lines.append(f"- Quality: **{report['decision']['quality_label']}** (rank #{report['decision']['quality_rank'] or 'n/a'})")
    lines.append(f"- Screening score: **{fmt_num(report['source_context']['best_score'])}** (best rank #{report['source_context']['best_score_rank'] or 'n/a'})")
    lines.append(f"- Risk bucket: **{report['decision']['risk_bucket']}**")
    lines.append(f"- Trade candidate: **{report['decision']['trade_candidate']}**")
    lines.append(f"- Orderability: **{(report.get('orderability_decision') or {}).get('decision', 'UNKNOWN')}**")
    lines.append("")
    lines.append("## Orderability decision")
    lines.append("")
    orderability = report.get('orderability_decision') or {}
    lines.append(f"- Market order now: **{str(bool(orderability.get('market_order_now'))).upper()}**")
    lines.append(f"- Ladder limit orders: **{str(bool(orderability.get('ladder_limit_orders'))).upper()}**")
    lines.append(f"- Stop-entry orders: **{str(bool(orderability.get('stop_entry_orders'))).upper()}**")
    if orderability.get('allowed_order_types'):
        lines.append(f"- Allowed order types: **{', '.join(orderability.get('allowed_order_types') or [])}**")
    if orderability.get('why'):
        lines.append(f"- Why: {orderability.get('why')}")
    lines.append("")
    lines.append("## A) Table 1 — Key Levels")
    lines.append("")
    key_rows = [[item['type'], item['label'], fmt_num(item['price'], 4), item['note']] for item in report.get('key_levels', [])]
    lines.extend(markdown_table(["Type", "Level", "Price", "Notes"], key_rows))
    lines.append("")
    lines.append("## B) Table 2 — Scenarios")
    lines.append("")
    scenario_rows = [[item['scenario'], f"{item['probability_pct']}%", f"{fmt_num(item['expected_move_pct'])}%", item['trigger']] for item in report.get('scenarios', [])]
    lines.extend(markdown_table(["Scenario", "Probability", "Expected move", "Triggers"], scenario_rows))
    lines.append("")
    lines.append("## Market state")
    lines.append("")
    state = report.get('market_state') or {}
    lines.append(f"- 4h trend/side: **{state.get('h4_trend', 'UNKNOWN')} / {state.get('h4_side', 'UNKNOWN')}**")
    lines.append(f"- 1d trend/side: **{state.get('d1_trend', 'UNKNOWN')} / {state.get('d1_side', 'UNKNOWN')}**")
    lines.append(f"- Volatility regime: **{state.get('volatility_regime', 'UNKNOWN')}**")
    lines.append(f"- ADX regime: **{state.get('adx_regime', 'UNKNOWN')}**")
    lines.append("")
    lines.append("## Macro / news / fundamental context")
    lines.append("")
    macro = report.get('macro_news_fundamental') or {}
    lines.append(f"- Official macro bias: **{macro.get('official_macro_bias') or 'UNKNOWN'}**")
    lines.append(f"- Macro alignment: **{macro.get('macro_alignment') or 'UNKNOWN'}**")
    lines.append(f"- Headline pressure: **{macro.get('headline_pressure') or 'UNKNOWN'}**")
    lines.append(f"- Event risk 24h / 72h: **{macro.get('event_risk_next_24h') or 'UNKNOWN'} / {macro.get('event_risk_next_72h') or 'UNKNOWN'}**")
    lines.append(f"- Sentiment state: **{macro.get('sentiment_state') or 'UNKNOWN'}**")
    lines.append(f"- Fundamental availability: **{macro.get('fundamental_availability') or 'UNKNOWN'}**")
    if macro.get('fundamental_note'):
        lines.append(f"- Fundamental note: {macro.get('fundamental_note')}")
    if macro.get('decision_note'):
        lines.append(f"- Context note: {macro.get('decision_note')}")
    if macro.get('top_headlines'):
        lines.append("")
        lines.append("Top headlines:")
        for item in macro.get('top_headlines', [])[:5]:
            title = item.get('title') or '(untitled)'
            lines.append(f"- {title}")
    if macro.get('scheduled_events'):
        lines.append("")
        lines.append("Scheduled macro events:")
        for item in macro.get('scheduled_events', [])[:5]:
            lines.append(f"- {item.get('scheduled_at_utc') or 'n/a'} — {item.get('title')} ({item.get('importance')})")
    lines.append("")
    lines.append("## C) Table 3 — Orders")
    lines.append("")
    order_rows = []
    for item in report.get('orders', []):
        order_rows.append([
            item.get('level') or 'n/a',
            item.get('order_type') or 'n/a',
            fmt_num(item.get('entry'), 4),
            fmt_num(item.get('size_pct_of_deployable_margin')), 
            fmt_num(item.get('margin_usdt')),
            fmt_num(item.get('leverage')),
            fmt_num(item.get('sl'), 4),
            f"{fmt_num(item.get('tp1'), 4)} / {fmt_num(item.get('tp2'), 4)}",
            f"{fmt_num(item.get('trail_trigger'), 4)} / {fmt_num(item.get('trail_distance'), 4)}",
        ])
    lines.extend(markdown_table(["Level", "Type", "Price", "Size %", "Margin USDT", "Lev", "SL", "TP1 / TP2", "Trail trigger / dist"], order_rows))
    lines.append("")
    lines.append("## D) Peak Risk Score")
    lines.append("")
    peak = report.get('peak_risk') or {}
    lines.append(f"- **{peak.get('label', 'UNKNOWN')}** — {peak.get('action', '')}")
    for bullet in peak.get('bullets', [])[:6]:
        lines.append(f"- {bullet}")
    lines.append("")
    lines.append("## E) Risk Summary")
    lines.append("")
    risk = report.get('risk_summary') or {}
    lines.append(f"- RiskBudgetUSDT: **{fmt_num(risk.get('risk_budget_usdt'))}**")
    lines.append(f"- EstimatedLossUSDT: **{fmt_num(risk.get('estimated_total_loss_usdt'))}**")
    lines.append(f"- EstimatedLoss%Equity: **{fmt_num(risk.get('estimated_total_loss_pct_equity'))}%**")
    lines.append(f"- Pass/Fail vs risk budget: **{risk.get('pass_vs_risk_budget') or 'UNKNOWN'}**")
    lines.append(f"- Estimated average entry: **{fmt_num(risk.get('estimated_average_entry'), 4)}**")
    lines.append(f"- Margin used % of free margin: **{fmt_num(risk.get('deployable_margin_used_pct_of_free_margin'))}%**")
    lines.append("")
    lines.append("## F) 5-line Do this now")
    lines.append("")
    for item in report.get('do_this_now', [])[:5]:
        lines.append(f"- {item}")
    lines.append("")
    visual = report.get('visual_confirmation') or {}
    if visual.get('requested'):
        lines.append("## Visual confirmation (opt-in)")
        lines.append("")
        lines.append("- Structured exchange data remains primary; screenshots are supplementary only.")
        if visual.get('error'):
            lines.append(f"- Status: **FAILED** — {visual.get('error')}")
        else:
            lines.append("- Status: **READY**")
            lines.append(f"- TradingView symbol: **{visual.get('tv_symbol') or 'UNKNOWN'}**")
            lines.append(f"- Prompt packet: `{visual.get('prompt') or 'n/a'}`")
            lines.append(f"- Structure 1H: `{visual.get('structure_1h') or 'n/a'}`")
            lines.append(f"- Structure 1D: `{visual.get('structure_1d') or 'n/a'}`")
            if visual.get('flow_1h'):
                lines.append(f"- Flow 1H: `{visual.get('flow_1h')}`")
            if visual.get('flow_1d'):
                lines.append(f"- Flow 1D: `{visual.get('flow_1d')}`")
            if visual.get('flow_1h_panels'):
                lines.append(f"- Flow 1H panels: `{visual.get('flow_1h_panels')}`")
            if visual.get('flow_1d_panels'):
                lines.append(f"- Flow 1D panels: `{visual.get('flow_1d_panels')}`")
            if visual.get('log'):
                lines.append(f"- Capture log: `{visual.get('log')}`")
        for note in visual.get('notes', [])[:4]:
            lines.append(f"- {note}")
        lines.append("")
    lines.append("## Final trade setup table")
    lines.append("")
    final_setup = report.get('final_trade_setup') or {}
    final_rows = [[
        final_setup.get('symbol') or 'n/a',
        final_setup.get('direction') or 'n/a',
        final_setup.get('trade_type') or 'n/a',
        fmt_num(final_setup.get('screening_score')),
        str(final_setup.get('screening_rank') or 'n/a'),
        final_setup.get('quality') or 'n/a',
        final_setup.get('risk') or 'n/a',
        final_setup.get('orderability_decision') or 'n/a',
        f"{fmt_num((final_setup.get('entry_zone') or {}).get('from'), 4)} → {fmt_num((final_setup.get('entry_zone') or {}).get('to'), 4)}",
        fmt_num(final_setup.get('estimated_average_entry'), 4),
        fmt_num(final_setup.get('disaster_sl'), 4),
        fmt_num(final_setup.get('tp1'), 4),
        fmt_num(final_setup.get('tp2'), 4),
        fmt_num(final_setup.get('total_margin_usdt')),
        fmt_num(final_setup.get('estimated_total_loss_usdt')),
        fmt_num(final_setup.get('estimated_total_loss_pct_equity')) + '%',
        fmt_num(final_setup.get('size_fraction_of_risk_budget')),
        final_setup.get('pass_vs_risk_budget') or 'n/a',
    ]]
    lines.extend(markdown_table(["Symbol", "Dir", "Trade type", "Score", "Rank", "Quality", "Risk", "Orderability", "Entry zone", "Avg entry", "SL", "TP1", "TP2", "Margin", "Risk USDT", "Risk %Eq", "RiskFrac", "Pass"], final_rows))
    lines.append("")
    if report.get('notes'):
        lines.append("## Notes")
        lines.append("")
        for item in report.get('notes', [])[:10]:
            lines.append(f"- {item}")
        lines.append("")
    return "\n".join(lines)


def write_outputs(report: dict[str, Any], markdown: str, symbol: str) -> dict[str, str]:
    ensure_dirs()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    prefix = f"trade_plan_{symbol.upper()}"
    stamped_json = PLAN_DIR / f"{prefix}_{stamp}.json"
    stamped_md = PLAN_DIR / f"{prefix}_{stamp}.md"
    latest_json = PLAN_DIR / f"{prefix}_latest.json"
    latest_md = PLAN_DIR / f"{prefix}_latest.md"

    payload = json.dumps(report, indent=2)
    for path in [stamped_json, latest_json]:
        path.write_text(payload, encoding="utf-8")
    for path in [stamped_md, latest_md]:
        path.write_text(markdown, encoding="utf-8")

    return {
        "json": str(stamped_json),
        "markdown": str(stamped_md),
        "latest_json": str(latest_json),
        "latest_markdown": str(latest_md),
    }
