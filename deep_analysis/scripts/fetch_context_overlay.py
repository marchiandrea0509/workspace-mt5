#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus
import xml.etree.ElementTree as ET

from pipeline_lib import REPORT_DIR, build_http_session, load_symbols_config, setup_logger

ROOT = Path(__file__).resolve().parents[1]
CONTEXT_DIR = REPORT_DIR / "context"
ASSET_OVERLAY_DIR = CONTEXT_DIR / "asset_overlays"

POSITIVE_WORDS = {
    "rally",
    "surge",
    "gain",
    "gains",
    "rise",
    "rises",
    "rebound",
    "boost",
    "strong",
    "stronger",
    "approval",
    "approves",
    "inflow",
    "inflows",
    "beat",
    "beats",
    "record",
    "support",
    "supports",
    "ceasefire",
    "stimulus",
    "easing",
    "cut",
    "cuts",
    "cooling",
    "progress",
}

NEGATIVE_WORDS = {
    "selloff",
    "slump",
    "drop",
    "drops",
    "fall",
    "falls",
    "fear",
    "panic",
    "weak",
    "weaker",
    "risk",
    "risks",
    "war",
    "tariff",
    "tariffs",
    "sanction",
    "sanctions",
    "probe",
    "investigation",
    "lawsuit",
    "outflow",
    "outflows",
    "liquidation",
    "tightening",
    "hawkish",
    "inflation",
    "hotter",
    "ban",
    "bans",
}

THEME_KEYWORDS = {
    "hawkish": ["hawkish", "rate hike", "higher for longer", "tightening", "sticky inflation", "hot inflation", "yields rise", "strong dollar"],
    "dovish": ["dovish", "rate cut", "rate cuts", "easing", "soft landing", "cooling inflation", "disinflation", "yields fall", "weaker dollar"],
    "inflation": ["inflation", "cpi", "ppi", "price pressures", "hotter prices"],
    "growth": ["gdp", "growth", "expansion", "industrial output", "strong demand"],
    "slowdown": ["slowdown", "recession", "contraction", "job losses", "weak demand"],
    "risk_on": ["rally", "inflows", "risk-on", "deal", "approval", "boost", "ceasefire"],
    "risk_off": ["selloff", "risk-off", "volatility", "uncertainty", "war", "tariff", "sanctions", "outflows"],
    "geopolitics": ["war", "missile", "conflict", "sanctions", "middle east", "ukraine", "ceasefire"],
    "supply_tightening": ["opec", "supply cut", "output cut", "inventory draw", "disruption", "shutdown"],
    "regulation": ["sec", "regulation", "regulator", "approval", "ban", "lawsuit"],
}

ASSET_PROFILES = {
    "BTC": {"asset_class": "crypto", "query": "bitcoin OR BTC OR crypto market", "macro_bucket": "risk_assets", "include": ["bitcoin", "btc", "crypto"], "exclude": []},
    "BTC_PERP": {"asset_class": "crypto", "query": "bitcoin OR BTC OR crypto market", "macro_bucket": "risk_assets", "include": ["bitcoin", "btc", "crypto"], "exclude": []},
    "ETH": {"asset_class": "crypto", "query": "ethereum OR ether OR ETH OR crypto market", "macro_bucket": "risk_assets", "include": ["ethereum", "ether", "crypto"], "exclude": []},
    "ETH_PERP": {"asset_class": "crypto", "query": "ethereum OR ether OR ETH OR crypto market", "macro_bucket": "risk_assets", "include": ["ethereum", "ether", "crypto"], "exclude": []},
    "SOL_PERP": {"asset_class": "crypto", "query": "solana OR SOL OR crypto market", "macro_bucket": "risk_assets", "include": ["solana", "crypto"], "exclude": []},
    "PAXG": {"asset_class": "precious_metals", "query": "gold price OR bullion OR PAXG OR XAU", "macro_bucket": "metals", "include": ["gold", "bullion", "xau", "paxg"], "exclude": ["medal", "olympic", "paralympic", "ski", "skier", "curling", "award"]},
    "GOLD": {"asset_class": "precious_metals", "query": "gold price OR bullion OR XAU", "macro_bucket": "metals", "include": ["gold", "bullion", "xau"], "exclude": ["medal", "olympic", "paralympic", "award"]},
    "SILVER": {"asset_class": "precious_metals", "query": "silver price OR bullion OR XAG", "macro_bucket": "metals", "include": ["silver", "bullion", "xag"], "exclude": ["medal", "olympic", "paralympic", "award"]},
    "XPT": {"asset_class": "precious_metals", "query": "platinum price OR XPT OR platinum market", "macro_bucket": "metals", "include": ["platinum", "xpt"], "exclude": ["award"]},
    "COPPER": {"asset_class": "industrial_metal", "query": "copper price OR copper market", "macro_bucket": "growth_assets", "include": ["copper", "metal", "commodity"], "exclude": []},
    "TESLA": {"asset_class": "equity_single_name", "query": "Tesla OR TSLA", "macro_bucket": "risk_assets", "include": ["tesla", "tsla"], "exclude": []},
    "USARX": {"asset_class": "equity_single_name", "query": "USA Rare Earth OR USARX", "macro_bucket": "risk_assets", "include": ["usa rare earth", "usarx"], "exclude": []},
    "NVDAX": {"asset_class": "equity_single_name", "query": "Nvidia OR NVDA OR NVDAX", "macro_bucket": "risk_assets", "include": ["nvidia", "nvda", "nvdax"], "exclude": []},
    "CRCLX": {"asset_class": "equity_single_name", "query": "Circle OR CRCLX OR USDC issuer", "macro_bucket": "risk_assets", "include": ["circle", "crclx", "usdc"], "exclude": []},
    "MSTRX": {"asset_class": "equity_single_name", "query": "MicroStrategy OR Strategy OR MSTR OR MSTRX", "macro_bucket": "risk_assets", "include": ["microstrategy", "strategy", "mstr", "mstrx"], "exclude": []},
    "BMNRX": {"asset_class": "equity_single_name", "query": "BitMine OR BMNRX OR bitcoin miner", "macro_bucket": "risk_assets", "include": ["bitmine", "bmnrx", "bitcoin miner"], "exclude": []},
    "HOODX": {"asset_class": "equity_single_name", "query": "Robinhood OR HOOD OR HOODX", "macro_bucket": "risk_assets", "include": ["robinhood", "hood", "hoodx"], "exclude": []},
    "QQQX": {"asset_class": "equity_index", "query": "Nasdaq 100 OR QQQ OR QQQX OR tech stocks", "macro_bucket": "risk_assets", "include": ["nasdaq", "qqq", "qqqx", "tech stocks"], "exclude": []},
    "INDEX_PROXY": {"asset_class": "equity_index", "query": "S&P 500 OR SPX OR stock market OR Wall Street", "macro_bucket": "risk_assets", "include": ["s&p", "spx", "stock market", "wall street", "equities"], "exclude": []},
    "USOIL": {"asset_class": "energy", "query": "oil OR crude OR WTI OR OPEC", "macro_bucket": "energy", "include": ["oil", "crude", "wti", "opec"], "exclude": []},
    "BRENT_OIL": {"asset_class": "energy", "query": "Brent oil OR crude OR OPEC", "macro_bucket": "energy", "include": ["brent", "oil", "crude", "opec"], "exclude": []},
}


def ensure_dirs() -> None:
    CONTEXT_DIR.mkdir(parents=True, exist_ok=True)
    ASSET_OVERLAY_DIR.mkdir(parents=True, exist_ok=True)


def safe_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except Exception:
        return None


def clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))


def strip_html(raw: str) -> str:
    text = re.sub(r"<script.*?</script>|<style.*?</style>", " ", raw or "", flags=re.S | re.I)
    text = re.sub(r"</(p|div|li|tr|td|th|h1|h2|h3|h4|h5|h6|br|section)>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = unescape(text)
    text = text.replace("\r", "")
    text = re.sub(r"\u00a0", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip()).lower()


def score_text(text: str) -> int:
    lower = normalize_text(text)
    score = 0
    for word in POSITIVE_WORDS:
        if word in lower:
            score += 1
    for word in NEGATIVE_WORDS:
        if word in lower:
            score -= 1
    return score


def count_themes(texts: list[str]) -> dict[str, int]:
    joined = " \n ".join(texts)
    lower = normalize_text(joined)
    out: dict[str, int] = {}
    for theme, phrases in THEME_KEYWORDS.items():
        out[theme] = sum(1 for phrase in phrases if phrase in lower)
    return out


def label_pressure(avg_score: float, volume: int) -> str:
    if volume == 0:
        return "NEUTRAL"
    if avg_score >= 0.35:
        return "POSITIVE"
    if avg_score <= -0.35:
        return "NEGATIVE"
    return "MIXED"


def parse_rfc822(value: str | None) -> str | None:
    if not value:
        return None
    try:
        dt = parsedate_to_datetime(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    except Exception:
        return None


def fetch_text(session, url: str, timeout: int = 20) -> str:
    response = session.get(url, timeout=timeout)
    response.raise_for_status()
    return response.text


def fetch_json(session, url: str, timeout: int = 20) -> Any:
    response = session.get(url, timeout=timeout)
    response.raise_for_status()
    return response.json()


def fetch_rss_items(session, url: str, limit: int = 10) -> list[dict[str, Any]]:
    xml_text = fetch_text(session, url)
    if "<" in xml_text:
        xml_text = xml_text[xml_text.find("<"):]
    xml_text = xml_text.lstrip("\ufeff\n\r\t ")
    root = ET.fromstring(xml_text)
    items: list[dict[str, Any]] = []
    for item in root.findall(".//item")[:limit]:
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub = parse_rfc822(item.findtext("pubDate"))
        desc = (item.findtext("description") or "").strip()
        items.append({"title": title, "link": link, "published_at_utc": pub, "description": desc})
    return items


def fetch_google_news_rss(session, query: str, days: int = 2, limit: int = 8) -> list[dict[str, Any]]:
    query_text = f"({query}) when:{days}d"
    url = f"https://news.google.com/rss/search?q={quote_plus(query_text)}&hl=en-US&gl=US&ceid=US:en"
    return fetch_rss_items(session, url, limit=limit)


def parse_bea_schedule(text: str, limit: int = 8) -> list[dict[str, Any]]:
    cleaned = text.replace("N ews", "News").replace("D ata", "Data").replace("V isual Data", "Visual Data")
    cleaned = cleaned.replace("A rticle", "Article")
    if "Year 2026" in cleaned:
        cleaned = cleaned.split("Year 2026", 1)[1]
    pattern = re.compile(
        r"([A-Z][a-z]+ \d{1,2})\s+(\d{1,2}:\d{2} [AP]M)\s+(News|Data|Visual Data|Article)\s+(.+?)(?=\s+[A-Z][a-z]+ \d{1,2}\s+\d{1,2}:\d{2} [AP]M\s+(?:News|Data|Visual Data|Article)\s+|$)",
        flags=re.S,
    )
    now = datetime.now(timezone.utc)
    rows: list[dict[str, Any]] = []
    for date_text, time_text, kind, title in pattern.findall(cleaned):
        title_clean = re.sub(r"\s+", " ", title).strip(" -\n\t")
        try:
            dt = datetime.strptime(f"{date_text} {now.year} {time_text}", "%B %d %Y %I:%M %p").replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        rows.append(
            {
                "source": "BEA",
                "kind": kind.upper().replace(" ", "_"),
                "title": title_clean,
                "scheduled_at_utc": dt.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            }
        )
        if len(rows) >= limit:
            break
    return rows


def event_risk_label(upcoming: list[dict[str, Any]], horizon_hours: int) -> str:
    now = datetime.now(timezone.utc)
    end = now + timedelta(hours=horizon_hours)
    count = 0
    major = 0
    major_terms = ("GDP", "Personal Income", "Trade", "Inflation", "CPI", "Payroll", "Employment")
    for item in upcoming:
        stamp = item.get("scheduled_at_utc")
        if not stamp:
            continue
        try:
            dt = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
        except Exception:
            continue
        if now <= dt <= end:
            count += 1
            if any(term.lower() in item.get("title", "").lower() for term in major_terms):
                major += 1
    if major >= 1 or count >= 2:
        return "HIGH"
    if count == 1:
        return "MEDIUM"
    return "LOW"


def classify_macro_bias(theme_counts: dict[str, int]) -> str:
    hawkish = theme_counts.get("hawkish", 0)
    dovish = theme_counts.get("dovish", 0)
    if hawkish - dovish >= 2:
        return "HAWKISH"
    if dovish - hawkish >= 2:
        return "DOVISH"
    if hawkish or dovish:
        return "MIXED"
    return "NEUTRAL"


def classify_fear_greed(value: int | None, label: str | None) -> str:
    if value is None:
        return (label or "UNKNOWN").upper().replace(" ", "_")
    if value <= 24:
        return "EXTREME_FEAR"
    if value <= 44:
        return "FEAR"
    if value < 56:
        return "NEUTRAL"
    if value < 75:
        return "GREED"
    return "EXTREME_GREED"


def profile_for_symbol(symbol: str) -> dict[str, Any]:
    return ASSET_PROFILES.get(
        symbol.upper(),
        {"asset_class": "other", "query": symbol, "macro_bucket": "other", "include": [], "exclude": []},
    )


def headline_relevant(item: dict[str, Any], include_terms: list[str], exclude_terms: list[str]) -> bool:
    text = normalize_text(f"{item.get('title', '')} {item.get('description', '')}")
    if exclude_terms and any(term.lower() in text for term in exclude_terms):
        return False
    if include_terms:
        return any(term.lower() in text for term in include_terms)
    return True


def macro_alignment_score(asset_class: str, macro_bias: str, macro_themes: dict[str, int]) -> int:
    score = 0
    risk_on = macro_themes.get("risk_on", 0)
    risk_off = macro_themes.get("risk_off", 0)
    geopolitics = macro_themes.get("geopolitics", 0)
    supply_tightening = macro_themes.get("supply_tightening", 0)
    growth = macro_themes.get("growth", 0)
    slowdown = macro_themes.get("slowdown", 0)
    inflation = macro_themes.get("inflation", 0)

    if asset_class in {"crypto", "equity_index", "equity_single_name"}:
        if macro_bias == "DOVISH":
            score += 1
        elif macro_bias == "HAWKISH":
            score -= 1
        if risk_on > risk_off:
            score += 1
        elif risk_off > risk_on:
            score -= 1
    elif asset_class == "precious_metals":
        if macro_bias == "DOVISH":
            score += 1
        elif macro_bias == "HAWKISH":
            score -= 1
        if geopolitics > 0 or inflation > 0:
            score += 1
    elif asset_class == "industrial_metal":
        if growth > slowdown:
            score += 1
        elif slowdown > growth:
            score -= 1
        if macro_bias == "HAWKISH":
            score -= 1
    elif asset_class == "energy":
        if supply_tightening > 0 or geopolitics > 0:
            score += 1
        if slowdown > growth:
            score -= 1
    return clamp(score, -2, 2)


def macro_alignment_label(score: int) -> str:
    if score >= 1:
        return "FAVORABLE"
    if score <= -1:
        return "UNFAVORABLE"
    return "MIXED"


def sentiment_state_for_symbol(asset_class: str, fear_greed_label: str) -> str:
    if asset_class == "crypto":
        return fear_greed_label
    return "NEUTRAL"


def base_conviction_adjustment(macro_alignment: str, headline_pressure: str, event_risk: str, asset_class: str, sentiment_state: str) -> int:
    adj = 0
    if macro_alignment == "FAVORABLE":
        adj += 1
    elif macro_alignment == "UNFAVORABLE":
        adj -= 1
    if headline_pressure == "POSITIVE":
        adj += 1
    elif headline_pressure == "NEGATIVE":
        adj -= 1
    if event_risk == "HIGH":
        adj -= 1
    if asset_class == "crypto" and sentiment_state == "EXTREME_FEAR":
        adj -= 1
    return clamp(adj, -2, 2)


def decision_posture(adjustment: int, event_risk: str) -> str:
    if event_risk == "HIGH" and adjustment <= 0:
        return "WAIT_OR_REDUCE_SIZE"
    if adjustment >= 2:
        return "PRESS_IF_PRICE_CONFIRMS"
    if adjustment == 1:
        return "LEAN_WITH_SETUP"
    if adjustment == 0:
        return "KEEP_SELECTIVE"
    if adjustment == -1:
        return "REDUCE_TRUST"
    return "AVOID_AGGRESSION"


def build_asset_news_summary(items: list[dict[str, Any]], include_terms: list[str], exclude_terms: list[str]) -> dict[str, Any]:
    filtered = [item for item in items if headline_relevant(item, include_terms, exclude_terms)]
    titles = [item.get("title", "") for item in filtered if item.get("title")]
    scores = [score_text(title) for title in titles]
    avg = (sum(scores) / len(scores)) if scores else 0.0
    return {
        "raw_news_volume": len(items),
        "news_volume": len(titles),
        "news_sentiment_score": avg,
        "headline_pressure": label_pressure(avg, len(titles)),
        "theme_counts": count_themes(titles),
        "top_headlines": filtered[:5],
    }


def build_macro_context(session, logger) -> dict[str, Any]:
    fed_items = fetch_rss_items(session, "https://www.federalreserve.gov/feeds/press_all.xml", limit=8)
    ecb_items = fetch_rss_items(session, "https://www.ecb.europa.eu/rss/press.xml", limit=8)
    macro_news = fetch_google_news_rss(session, "Federal Reserve OR ECB OR inflation OR CPI OR GDP OR payrolls OR unemployment", days=2, limit=10)
    bea_text = strip_html(fetch_text(session, "https://www.bea.gov/news/schedule"))
    bea_schedule = parse_bea_schedule(bea_text, limit=10)

    official_titles = [item["title"] for item in fed_items + ecb_items + macro_news if item.get("title")]
    themes = count_themes(official_titles)
    macro_bias = classify_macro_bias(themes)

    context = {
        "official_macro_bias": macro_bias,
        "theme_counts": themes,
        "event_risk_next_24h": event_risk_label(bea_schedule, 24),
        "event_risk_next_72h": event_risk_label(bea_schedule, 72),
        "official_items": {
            "fed_press": fed_items[:5],
            "ecb_press": ecb_items[:5],
            "macro_news": macro_news[:5],
        },
        "bea_schedule": bea_schedule,
    }
    logger.info("Fetched macro context fed=%s ecb=%s macro_news=%s bea=%s", len(fed_items), len(ecb_items), len(macro_news), len(bea_schedule))
    return context


def build_sentiment_context(session) -> dict[str, Any]:
    raw = fetch_json(session, "https://api.alternative.me/fng/")
    item = (raw.get("data") or [{}])[0]
    value = None
    try:
        value = int(item.get("value"))
    except Exception:
        value = None
    label = item.get("value_classification")
    return {
        "crypto_fear_greed": {
            "value": value,
            "classification": label,
            "state_label": classify_fear_greed(value, label),
            "timestamp": item.get("timestamp"),
            "time_until_update": item.get("time_until_update"),
        }
    }


def build_news_context(session, symbols: list[str], logger) -> dict[str, Any]:
    asset_news: dict[str, Any] = {}
    for symbol in symbols:
        profile = profile_for_symbol(symbol)
        items = fetch_google_news_rss(session, profile["query"], days=2, limit=8)
        asset_news[symbol] = {
            "asset_class": profile["asset_class"],
            "query": profile["query"],
            "include_terms": profile.get("include", []),
            "exclude_terms": profile.get("exclude", []),
            **build_asset_news_summary(items, profile.get("include", []), profile.get("exclude", [])),
        }
    logger.info("Fetched asset news overlays for %s symbols", len(symbols))
    return {"asset_news": asset_news}


def build_asset_overlay(symbol: str, macro_context: dict[str, Any], sentiment_context: dict[str, Any], news_context: dict[str, Any]) -> dict[str, Any]:
    profile = profile_for_symbol(symbol)
    asset_class = profile["asset_class"]
    asset_news = news_context["asset_news"].get(symbol, {})
    macro_alignment_raw = macro_alignment_score(asset_class, macro_context["official_macro_bias"], macro_context.get("theme_counts", {}))
    macro_alignment = macro_alignment_label(macro_alignment_raw)
    event_risk = macro_context.get("event_risk_next_24h", "LOW")
    sentiment_state = sentiment_state_for_symbol(asset_class, sentiment_context["crypto_fear_greed"].get("state_label", "UNKNOWN"))
    adjustment = base_conviction_adjustment(macro_alignment, asset_news.get("headline_pressure", "NEUTRAL"), event_risk, asset_class, sentiment_state)
    posture = decision_posture(adjustment, event_risk)

    note_parts = [f"Macro alignment is {macro_alignment.lower()}"]
    pressure = asset_news.get("headline_pressure", "NEUTRAL")
    note_parts.append(f"headline pressure is {pressure.lower()}")
    note_parts.append(f"event risk in the next 24h is {event_risk.lower()}")
    if asset_class == "crypto":
        note_parts.append(f"crypto sentiment is {sentiment_state.lower().replace('_', ' ')}")

    return {
        "internal_symbol": symbol,
        "asset_class": asset_class,
        "macro_bucket": profile["macro_bucket"],
        "macro_alignment": macro_alignment,
        "macro_alignment_score": macro_alignment_raw,
        "headline_pressure": pressure,
        "news_volume": asset_news.get("news_volume", 0),
        "news_sentiment_score": asset_news.get("news_sentiment_score", 0.0),
        "event_risk_next_24h": event_risk,
        "event_risk_next_72h": macro_context.get("event_risk_next_72h", "LOW"),
        "sentiment_state": sentiment_state,
        "conviction_adjustment_hint": adjustment,
        "decision_posture": posture,
        "decision_note": "; ".join(note_parts) + ".",
        "top_headlines": asset_news.get("top_headlines", []),
    }


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_outputs(bundle: dict[str, Any], symbol_filter: str | None = None) -> dict[str, Any]:
    ensure_dirs()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    suffix = f"_{symbol_filter.upper()}" if symbol_filter else ""

    paths = {
        "macro": {
            "latest": CONTEXT_DIR / f"macro_context{suffix}_latest.json",
            "stamped": CONTEXT_DIR / f"macro_context{suffix}_{stamp}.json",
        },
        "news": {
            "latest": CONTEXT_DIR / f"news_context{suffix}_latest.json",
            "stamped": CONTEXT_DIR / f"news_context{suffix}_{stamp}.json",
        },
        "sentiment": {
            "latest": CONTEXT_DIR / f"sentiment_context{suffix}_latest.json",
            "stamped": CONTEXT_DIR / f"sentiment_context{suffix}_{stamp}.json",
        },
        "bundle": {
            "latest": CONTEXT_DIR / f"context_bundle{suffix}_latest.json",
            "stamped": CONTEXT_DIR / f"context_bundle{suffix}_{stamp}.json",
        },
    }

    write_json(paths["macro"]["latest"], bundle["macro_context"])
    write_json(paths["macro"]["stamped"], bundle["macro_context"])
    write_json(paths["news"]["latest"], bundle["news_context"])
    write_json(paths["news"]["stamped"], bundle["news_context"])
    write_json(paths["sentiment"]["latest"], bundle["sentiment_context"])
    write_json(paths["sentiment"]["stamped"], bundle["sentiment_context"])
    write_json(paths["bundle"]["latest"], bundle)
    write_json(paths["bundle"]["stamped"], bundle)

    for symbol, payload in bundle["asset_overlays"].items():
        latest = ASSET_OVERLAY_DIR / f"{symbol}_latest.json"
        stamped = ASSET_OVERLAY_DIR / f"{symbol}_{stamp}.json"
        write_json(latest, payload)
        write_json(stamped, payload)

    return {
        "macro_latest": str(paths["macro"]["latest"]),
        "news_latest": str(paths["news"]["latest"]),
        "sentiment_latest": str(paths["sentiment"]["latest"]),
        "bundle_latest": str(paths["bundle"]["latest"]),
        "asset_overlay_dir": str(ASSET_OVERLAY_DIR),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch free macro/news/sentiment context and write asset overlay files.")
    parser.add_argument("--symbol", help="Optional internal symbol filter, e.g. PAXG")
    args = parser.parse_args()

    logger = setup_logger("fetch_context_overlay")
    session = build_http_session(total_retries=2, backoff_factor=0.5)
    symbols_cfg = load_symbols_config()
    symbols = sorted({entry["internal_symbol"] for entry in symbols_cfg if entry.get("status") and str(entry.get("status")).lower() != "disabled"})
    if args.symbol:
        symbols = [symbol for symbol in symbols if symbol.upper() == args.symbol.upper()]
    if not symbols:
        raise SystemExit("No symbols available for context overlay generation.")

    macro_context = build_macro_context(session, logger)
    sentiment_context = build_sentiment_context(session)
    news_context = build_news_context(session, symbols, logger)
    asset_overlays = {symbol: build_asset_overlay(symbol, macro_context, sentiment_context, news_context) for symbol in symbols}

    bundle = {
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "symbols": symbols,
        "macro_context": macro_context,
        "news_context": news_context,
        "sentiment_context": sentiment_context,
        "asset_overlays": asset_overlays,
    }
    paths = write_outputs(bundle, symbol_filter=args.symbol)
    logger.info("Built context overlay bundle for %s symbols -> %s", len(symbols), paths["bundle_latest"])
    print(json.dumps({"paths": paths, "context": bundle}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
