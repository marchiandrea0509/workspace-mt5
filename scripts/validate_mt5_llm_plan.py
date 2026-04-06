#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REQUIRED_TOP_LEVEL = [
    'screener_read',
    'market_state',
    'key_levels',
    'trade_quality',
    'primary_plan',
    'orderability',
    'backup_plan',
    'risk_sizing',
    'trade_plan_ticket',
    'final_verdict',
    'validator_hints',
]

VALID_BIAS = {'LONG', 'SHORT', 'WAIT'}
VALID_ENTRY_METHOD = {'market', 'ladder_limits', 'stop_entry'}
VALID_EXECUTION_STYLE = {'AUTO', 'DIP_LADDER', 'BREAKOUT', 'SELL_RALLY', 'BREAKDOWN'}
VALID_ORDERABILITY = {'PLACEABLE_NOW', 'PLACEABLE_CONDITIONAL_ONLY', 'NOT_PLACEABLE_YET'}
VALID_TRAILING_MODES = {'price', 'percent', 'atr'}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding='utf-8-sig'))


def as_float(value: Any) -> float | None:
    try:
        if value in (None, '', '—'):
            return None
        return float(value)
    except Exception:
        return None


def main() -> int:
    ap = argparse.ArgumentParser(description='Validate MT5 Phase1 LLM planner JSON before comparison/execution.')
    ap.add_argument('--plan', required=True)
    ap.add_argument('--pack', default='')
    ap.add_argument('--out', default='')
    args = ap.parse_args()

    plan = load_json(Path(args.plan))
    pack = load_json(Path(args.pack)) if args.pack else {}
    constraints = pack.get('execution_constraints') or {}
    account_limits = pack.get('account_limits') or {}

    errors: list[str] = []
    warnings: list[str] = []

    for key in REQUIRED_TOP_LEVEL:
        if key not in plan:
            errors.append(f'missing top-level key: {key}')

    primary = plan.get('primary_plan') or {}
    orderability = plan.get('orderability') or {}
    risk = plan.get('risk_sizing') or {}
    ticket = plan.get('trade_plan_ticket') or {}
    trailing = ticket.get('trailing') or {}
    legs = ticket.get('legs') or []

    if str(primary.get('bias') or '').upper() not in VALID_BIAS:
        errors.append('primary_plan.bias invalid or missing')
    if primary.get('entry_method') not in VALID_ENTRY_METHOD:
        errors.append('primary_plan.entry_method invalid or missing')
    if primary.get('execution_style') not in VALID_EXECUTION_STYLE:
        errors.append('primary_plan.execution_style invalid or missing')
    if str(orderability.get('classification') or '').upper() not in VALID_ORDERABILITY:
        errors.append('orderability.classification invalid or missing')

    max_legs = int(constraints.get('max_legs') or 8)
    if not isinstance(legs, list):
        errors.append('trade_plan_ticket.legs must be an array')
        legs = []
    if len(legs) > max_legs:
        errors.append(f'trade_plan_ticket.legs exceeds max_legs={max_legs}')

    for idx, leg in enumerate(legs, start=1):
        if not isinstance(leg, dict):
            errors.append(f'leg {idx} must be an object')
            continue
        for field in ['level', 'order_type', 'entry_price', 'lots', 'units_estimate', 'notional_usd_estimate']:
            if field not in leg:
                errors.append(f'leg {idx} missing {field}')
        if as_float(leg.get('lots')) is None or as_float(leg.get('lots')) <= 0:
            errors.append(f'leg {idx} lots must be > 0')

    if legs:
        if as_float(ticket.get('shared_stop_loss_price')) is None:
            errors.append('trade_plan_ticket.shared_stop_loss_price required when legs exist')
        if as_float(ticket.get('shared_take_profit_price')) is None:
            errors.append('trade_plan_ticket.shared_take_profit_price required when legs exist')
        if not isinstance(trailing, dict):
            errors.append('trade_plan_ticket.trailing must be an object')
        else:
            if trailing.get('enabled'):
                if trailing.get('distance_mode') not in VALID_TRAILING_MODES:
                    errors.append('trailing.distance_mode must be price, percent, or atr when trailing is enabled')
                if as_float(trailing.get('distance_value')) is None or as_float(trailing.get('distance_value')) <= 0:
                    errors.append('trailing.distance_value must be > 0 when trailing is enabled')
                if as_float(trailing.get('trigger_price')) is None or as_float(trailing.get('trigger_price')) <= 0:
                    errors.append('trailing.trigger_price must be > 0 when trailing is enabled')

    total_risk = as_float(risk.get('total_risk_usd'))
    total_margin = as_float(risk.get('total_margin_usd_estimate'))
    if total_risk is None:
        errors.append('risk_sizing.total_risk_usd required')
    if total_margin is None:
        errors.append('risk_sizing.total_margin_usd_estimate required')

    budget = as_float(account_limits.get('risk_budget_usd_total_trade'))
    margin_cap = as_float(account_limits.get('max_margin_usd_total_trade'))
    if budget is not None and total_risk is not None and total_risk - budget > 1e-9:
        warnings.append(f'total_risk_usd exceeds budget ({total_risk} > {budget})')
    if margin_cap is not None and total_margin is not None and total_margin - margin_cap > 1e-9:
        warnings.append(f'total_margin_usd_estimate exceeds margin cap ({total_margin} > {margin_cap})')

    result = {
        'valid': not errors,
        'errors': errors,
        'warnings': warnings,
        'summary': {
            'legs_count': len(legs),
            'bias': primary.get('bias'),
            'entry_method': primary.get('entry_method'),
            'orderability': orderability.get('classification'),
            'total_risk_usd': total_risk,
            'total_margin_usd_estimate': total_margin,
        },
    }

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == '__main__':
    raise SystemExit(main())
