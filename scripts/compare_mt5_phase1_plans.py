#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding='utf-8-sig'))


def as_float(value: Any) -> float | None:
    try:
        if value in (None, '', '—'):
            return None
        return float(value)
    except Exception:
        return None


def first_or_none(values: list[Any]) -> Any:
    return values[0] if values else None


def normalize_enum(value: Any) -> Any:
    if isinstance(value, str):
        return value.strip().upper()
    return value


def extract_script(plan: dict[str, Any]) -> dict[str, Any]:
    key_levels = plan.get('key_levels') or {}
    risk = plan.get('risk_plan') or {}
    orderability = plan.get('orderability_decision') or {}
    preview = plan.get('trade_ticket_preview') or {}
    ladder = key_levels.get('ladder_entries') or []
    return {
        'symbol': plan.get('symbol'),
        'bias': normalize_enum((plan.get('bias') or {}).get('direction')),
        'setup': normalize_enum((plan.get('bias') or {}).get('setup')),
        'orderability': normalize_enum(orderability.get('decision')),
        'execution_template': orderability.get('execution_template'),
        'entry_method': preview.get('entry_type'),
        'entry_reference': preview.get('entry'),
        'entry_zone_low': min(ladder) if ladder else preview.get('entry'),
        'entry_zone_high': max(ladder) if ladder else preview.get('entry'),
        'stop_loss': preview.get('sl'),
        'take_profit': preview.get('tp_live'),
        'trailing_enabled': False,
        'legs_count': len(ladder),
        'risk_usd': risk.get('total_risk_usdt'),
        'margin_usd': risk.get('total_margin_usdt'),
    }


def extract_llm(plan: dict[str, Any]) -> dict[str, Any]:
    primary = plan.get('primary_plan') or {}
    orderability = plan.get('orderability') or {}
    risk = plan.get('risk_sizing') or {}
    ticket = plan.get('trade_plan_ticket') or {}
    legs = ticket.get('legs') or []
    entry_prices = [as_float((leg or {}).get('entry_price')) for leg in legs]
    entry_prices = [x for x in entry_prices if x is not None]
    trailing = ticket.get('trailing') or {}
    return {
        'symbol': first_or_none([
            (plan.get('final_verdict') or {}).get('symbol'),
            primary.get('symbol'),
            (plan.get('validator_hints') or {}).get('symbol'),
        ]),
        'bias': normalize_enum(primary.get('bias')),
        'setup': normalize_enum(primary.get('execution_style')),
        'orderability': normalize_enum(orderability.get('classification')),
        'execution_template': primary.get('entry_method'),
        'entry_method': primary.get('entry_method'),
        'entry_reference': first_or_none([
            primary.get('entry_trigger'),
            primary.get('entry_zone'),
            primary.get('entry_price'),
        ]),
        'entry_zone_low': min(entry_prices) if entry_prices else as_float(primary.get('entry_zone_low')),
        'entry_zone_high': max(entry_prices) if entry_prices else as_float(primary.get('entry_zone_high')),
        'stop_loss': first_or_none([
            ticket.get('shared_stop_loss_price'),
            primary.get('stop_loss_price'),
            primary.get('stop_loss'),
        ]),
        'take_profit': first_or_none([
            ticket.get('shared_take_profit_price'),
            primary.get('take_profit_price'),
            primary.get('tp_price'),
            primary.get('tp1'),
        ]),
        'trailing_enabled': bool(trailing.get('enabled')),
        'legs_count': len(legs),
        'risk_usd': first_or_none([
            risk.get('total_risk_usd'),
            ticket.get('total_planned_risk_usd'),
        ]),
        'margin_usd': first_or_none([
            risk.get('total_margin_usd_estimate'),
            ticket.get('total_margin_usd_estimate'),
        ]),
    }


def delta(a: Any, b: Any) -> float | None:
    af = as_float(a)
    bf = as_float(b)
    if af is None or bf is None:
        return None
    return round(bf - af, 10)


def main() -> int:
    ap = argparse.ArgumentParser(description='Compare deterministic MT5 Phase1 plan vs LLM planner output.')
    ap.add_argument('--script-plan', required=True)
    ap.add_argument('--llm-plan', required=True)
    ap.add_argument('--out', default='')
    args = ap.parse_args()

    script_plan = load_json(Path(args.script_plan))
    llm_plan = load_json(Path(args.llm_plan))
    script_view = extract_script(script_plan)
    llm_view = extract_llm(llm_plan)

    comparison = {
        'script': script_view,
        'llm': llm_view,
        'differences': {
            'bias_changed': script_view['bias'] != llm_view['bias'],
            'orderability_changed': script_view['orderability'] != llm_view['orderability'],
            'entry_method_changed': script_view['entry_method'] != llm_view['entry_method'],
            'legs_count_delta': (llm_view['legs_count'] or 0) - (script_view['legs_count'] or 0),
            'entry_zone_low_delta': delta(script_view['entry_zone_low'], llm_view['entry_zone_low']),
            'entry_zone_high_delta': delta(script_view['entry_zone_high'], llm_view['entry_zone_high']),
            'stop_loss_delta': delta(script_view['stop_loss'], llm_view['stop_loss']),
            'take_profit_delta': delta(script_view['take_profit'], llm_view['take_profit']),
            'risk_usd_delta': delta(script_view['risk_usd'], llm_view['risk_usd']),
            'margin_usd_delta': delta(script_view['margin_usd'], llm_view['margin_usd']),
            'trailing_enabled_script': script_view['trailing_enabled'],
            'trailing_enabled_llm': llm_view['trailing_enabled'],
        },
    }

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(comparison, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps(comparison, indent=2, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
