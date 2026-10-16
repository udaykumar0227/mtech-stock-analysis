"""Configuration for the analyser.

A single ``Config`` dataclass holds every tunable knob. Values can be
overridden by a YAML file and/or by command-line flags, which makes the
research workflow reproducible: a run is fully described by its config.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class Config:
    """All parameters controlling data, features, regimes and back-testing."""

    # Data selection
    ticker: str = "RELIANCE.NS"
    start: str = "2000-01-01"
    end: str = ""

    # Trend features
    fast_ma: int = 20
    slow_ma: int = 50
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9

    # Momentum / mean-reversion features
    rsi_period: int = 14
    bb_window: int = 20
    bb_std: float = 2.0

    # Volatility features
    atr_period: int = 14
    vol_window: int = 20

    # Regime decision thresholds
    trend_threshold: float = 0.005
    vol_high_pct: float = 0.70

    # Signal operating points
    rsi_oversold: float = 30.0
    rsi_overbought: float = 70.0
    high_vol_size: float = 0.5

    # Back-test assumptions
    cost_bps: float = 5.0
    init_cash: float = 100_000.0
    trading_days: int = 252

    def replace(self, **overrides: Any) -> "Config":
        """Return a copy with the given non-None overrides applied."""
        data: Dict[str, Any] = asdict(self)
        for key, value in overrides.items():
            if value is not None:
                if key not in data:
                    raise KeyError(f"Unknown config field: {key!r}")
                data[key] = value
        return Config(**data)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def load_config(path: Optional[str | Path] = None, **overrides: Any) -> Config:
    """Build a ``Config`` from an optional YAML file plus keyword overrides.

    Missing PyYAML is tolerated: the defaults simply survive.
    """
    data: Dict[str, Any] = {}
    if path is not None:
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Config file not found: {p}")
        try:
            import yaml  # type: ignore
        except ImportError as exc:  # pragma: no cover - env dependent
            raise RuntimeError(
                "PyYAML is required to read a config file: pip install PyYAML"
            ) from exc
        loaded = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        if not isinstance(loaded, dict):
            raise ValueError(f"Config file must contain a mapping: {p}")
        data = loaded

    valid = {f.name for f in fields(Config)}
    unknown = set(data) - valid
    if unknown:
        raise KeyError(f"Unknown config keys in file: {sorted(unknown)}")

    cfg = Config(**data)
    return cfg.replace(**overrides)
