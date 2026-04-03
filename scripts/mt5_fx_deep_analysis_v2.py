#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from market_source_lib import make_market_source
from mt5_fx_deep_analysis_lib import analyze_candidate

WORKSPACE = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = WORKSPACE / 'config' / 'mt5_fx_autotrade_phase1.json'


@dataclass
class Candidate:
    symbol: str
    description: str
    row: dict[str, Any]
    direction: str


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding='utf-8'))


def main() -> int:
    ap = argparse.ArgumentParser(description='Run MT5-native FX deep analysis v2 for a selected symbol.')
    ap.add_argument('--config', default=str(DEFAULT_CONFIG))
    ap.add_argument('--report-json', required=True)
    ap.add_argument('--symbol', required=True)
    ap.add_argument('--direction', required=True, choices=['LONG', 'SHORT'])
    args = ap.parse_args()

    cfg = load_json(Path(args.config))
    report = load_json(Path(args.report_json))
    row = None
    for item in (report.get('top10') or report.get('top5') or []):
        raw = item.get('raw') or item
        if str(raw.get('Symbol') or '').upper() == args.symbol.upper():
            row = raw
            break
    if row is None:
        row = {'Symbol': args.symbol.upper(), 'Description': args.symbol.upper()}

    candidate = Candidate(symbol=args.symbol.upper(), description=str(row.get('Description') or args.symbol.upper()), row=row, direction=args.direction.upper())
    source = make_market_source(cfg['analysisDataSource'])
    try:
        plan = analyze_candidate(candidate, report, cfg, source)
    finally:
        shutdown = getattr(source, 'shutdown', None)
        if callable(shutdown):
            shutdown()
    print(json.dumps(plan, indent=2, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
