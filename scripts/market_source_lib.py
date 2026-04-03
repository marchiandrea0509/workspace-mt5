from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


@dataclass
class SymbolProfile:
    root_symbol: str
    analysis_symbol: str
    execution_symbol: str
    path: str
    trade_mode: str
    trade_mode_code: int
    visible: bool
    selected: bool
    digits: int
    point: float
    volume_min: float
    volume_step: float
    volume_max: float
    contract_size: float
    currency_base: str
    currency_profit: str
    currency_margin: str


class MarketDataSource(Protocol):
    kind: str

    def describe(self) -> dict[str, Any]: ...
    def resolve_symbol(self, root_symbol: str) -> SymbolProfile: ...
    def get_rates(self, symbol: str, timeframe: str, count: int) -> list[dict[str, Any]]: ...
    def fx_to_usd_rate(self, currency: str) -> float | None: ...


class CSVFixtureSource:
    kind = 'csv_fixture'

    def __init__(self, config: dict[str, Any]):
        import json

        fixture_path = Path(str(config.get('fixturePath') or '')).expanduser()
        payload = json.loads(fixture_path.read_text(encoding='utf-8'))
        self._profiles = payload['profiles']
        self._rates = payload['rates']
        self._fx_to_usd = payload.get('fx_to_usd', {})

    def describe(self) -> dict[str, Any]:
        return {'kind': self.kind}

    def resolve_symbol(self, root_symbol: str) -> SymbolProfile:
        row = self._profiles[root_symbol.upper()]
        return SymbolProfile(**row)

    def get_rates(self, symbol: str, timeframe: str, count: int) -> list[dict[str, Any]]:
        rows = self._rates[symbol][timeframe]
        return rows[-count:]

    def fx_to_usd_rate(self, currency: str) -> float | None:
        return self._fx_to_usd.get(currency.upper())


class MT5PythonSource:
    kind = 'mt5_python'

    _TRADE_MODES = {
        0: 'DISABLED',
        1: 'LONGONLY',
        2: 'SHORTONLY',
        3: 'CLOSEONLY',
        4: 'FULL',
    }

    def __init__(self, config: dict[str, Any]):
        import MetaTrader5 as mt5

        self.mt5 = mt5
        self.config = config
        self.terminal_path = str(config.get('terminalExe') or '')
        self.preferred_suffixes = [str(x).lower() for x in config.get('preferredSuffixes') or ['.pro', '']]
        if not self.mt5.initialize(path=self.terminal_path):
            raise RuntimeError(f'MT5 initialize failed: {self.mt5.last_error()}')
        self._symbols = list(self.mt5.symbols_get() or [])
        self._symbol_map: dict[str, list[Any]] = {}
        for sym in self._symbols:
            root = self._normalize(sym.name)
            self._symbol_map.setdefault(root, []).append(sym)

    def shutdown(self) -> None:
        try:
            self.mt5.shutdown()
        except Exception:
            pass

    def describe(self) -> dict[str, Any]:
        return {
            'kind': self.kind,
            'terminal_path': self.terminal_path,
            'symbols_loaded': len(self._symbols),
        }

    def resolve_symbol(self, root_symbol: str) -> SymbolProfile:
        root = self._normalize(root_symbol)
        candidates = list(self._symbol_map.get(root, []))
        if not candidates:
            raise KeyError(f'No MT5 symbols found for root {root_symbol}')
        candidates.sort(key=self._sort_key, reverse=True)
        best = candidates[0]
        return self._profile_from_symbol(best)

    def get_rates(self, symbol: str, timeframe: str, count: int) -> list[dict[str, Any]]:
        tf = self._timeframe_code(timeframe)
        self.mt5.symbol_select(symbol, True)
        rows = self.mt5.copy_rates_from_pos(symbol, tf, 0, count)
        if rows is None:
            raise RuntimeError(f'copy_rates_from_pos failed for {symbol} {timeframe}: {self.mt5.last_error()}')
        out: list[dict[str, Any]] = []
        for row in rows:
            out.append({
                'time': int(row['time']),
                'open': float(row['open']),
                'high': float(row['high']),
                'low': float(row['low']),
                'close': float(row['close']),
                'tick_volume': float(row['tick_volume']),
                'spread': float(row['spread']),
                'real_volume': float(row['real_volume']),
            })
        return out

    def fx_to_usd_rate(self, currency: str) -> float | None:
        currency = currency.upper()
        if currency == 'USD':
            return 1.0
        direct = self._find_best_symbol(currency + 'USD')
        if direct:
            return self._latest_mid(direct.name)
        inverse = self._find_best_symbol('USD' + currency)
        if inverse:
            mid = self._latest_mid(inverse.name)
            return None if not mid else 1.0 / mid
        return None

    def _latest_mid(self, symbol: str) -> float | None:
        self.mt5.symbol_select(symbol, True)
        tick = self.mt5.symbol_info_tick(symbol)
        if tick and tick.bid and tick.ask:
            return (float(tick.bid) + float(tick.ask)) / 2.0
        rates = self.get_rates(symbol, 'H4', 1)
        return rates[-1]['close'] if rates else None

    def _find_best_symbol(self, root_symbol: str):
        candidates = list(self._symbol_map.get(self._normalize(root_symbol), []))
        if not candidates:
            return None
        candidates.sort(key=self._sort_key, reverse=True)
        return candidates[0]

    def _sort_key(self, sym: Any) -> tuple[float, float, float, float]:
        suffix = Path(sym.name).suffix.lower() if '.' in sym.name else ''
        suffix_rank = 0
        if suffix in self.preferred_suffixes:
            suffix_rank = len(self.preferred_suffixes) - self.preferred_suffixes.index(suffix)
        trade_score = 3 if sym.trade_mode == 4 else 2 if sym.trade_mode in (1, 2) else 1 if sym.trade_mode == 3 else 0
        path_bonus = 1 if 'PRO\\FX' in (sym.path or '').upper() else 0
        return trade_score, int(bool(sym.visible)) + int(bool(sym.select)), suffix_rank, path_bonus

    def _profile_from_symbol(self, sym: Any) -> SymbolProfile:
        return SymbolProfile(
            root_symbol=self._normalize(sym.name),
            analysis_symbol=sym.name,
            execution_symbol=sym.name,
            path=sym.path or '',
            trade_mode=self._TRADE_MODES.get(int(sym.trade_mode), str(sym.trade_mode)),
            trade_mode_code=int(sym.trade_mode),
            visible=bool(sym.visible),
            selected=bool(sym.select),
            digits=int(sym.digits),
            point=float(sym.point),
            volume_min=float(sym.volume_min),
            volume_step=float(sym.volume_step),
            volume_max=float(sym.volume_max),
            contract_size=float(sym.trade_contract_size),
            currency_base=(sym.currency_base or '').upper(),
            currency_profit=(sym.currency_profit or '').upper(),
            currency_margin=(sym.currency_margin or '').upper(),
        )

    @staticmethod
    def _normalize(symbol: str) -> str:
        sym = symbol.strip().upper()
        if sym.endswith('.PRO'):
            sym = sym[:-4]
        return sym

    def _timeframe_code(self, timeframe: str) -> int:
        tf = timeframe.strip().upper()
        mapping = {
            'H4': self.mt5.TIMEFRAME_H4,
            'D1': self.mt5.TIMEFRAME_D1,
            'H1': self.mt5.TIMEFRAME_H1,
            'M30': self.mt5.TIMEFRAME_M30,
        }
        if tf not in mapping:
            raise KeyError(f'Unsupported timeframe: {timeframe}')
        return mapping[tf]


def make_market_source(config: dict[str, Any]) -> MarketDataSource:
    kind = str(config.get('kind') or '').strip().lower()
    if kind == 'mt5_python':
        return MT5PythonSource(config)
    if kind == 'csv_fixture':
        return CSVFixtureSource(config)
    raise ValueError(f'Unsupported market data source kind: {kind}')
