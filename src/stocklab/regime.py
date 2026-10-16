"""Market-style (regime) classification.

The project's premise is that a stock spends its life in a handful of
recurring "styles". We label each day with two orthogonal axes:

* **Trend**  - up / down / sideways, from the normalised fast-vs-slow MA
  spread, confirmed by the MACD histogram.
* **Volatility** - high / low, from the percentile rank of realised vol.

Combining them yields an interpretable label such as ``up_trend_low_vol`` or
``sideways_high_vol``. Volatility is a *percentile*, so the definition of
"high" adapts to each stock's own history.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from stocklab.config import Config

TREND_UP = "up"
TREND_DOWN = "down"
TREND_SIDEWAYS = "sideways"

VOL_HIGH = "high_vol"
VOL_LOW = "low_vol"


def classify(frame: pd.DataFrame, cfg: Config) -> pd.DataFrame:
    """Attach ``trend_state``, ``vol_state`` and ``regime`` columns.

    ``regime`` is the composite market style used downstream by the signal
    layer.
    """
    df = frame.copy()
    required = {"trend_strength", "macd_hist", "vol_pct"}
    missing = required - set(df.columns)
    if missing:
        raise KeyError(f"run add_indicators() first; missing {sorted(missing)}")

    ts = df["trend_strength"]
    hist = df["macd_hist"]
    threshold = cfg.trend_threshold

    up = (ts > threshold) & (hist > 0)
    down = (ts < -threshold) & (hist < 0)

    trend_state = np.where(up, TREND_UP, np.where(down, TREND_DOWN, TREND_SIDEWAYS))
    vol_state = np.where(df["vol_pct"] >= cfg.vol_high_pct, VOL_HIGH, VOL_LOW)

    df["trend_state"] = pd.Series(trend_state, index=df.index).astype("string")
    df["vol_state"] = pd.Series(vol_state, index=df.index).astype("string")
    df["regime"] = df["trend_state"] + "_" + df["vol_state"]
    return df


def regime_breakdown(df: pd.DataFrame) -> pd.Series:
    """Share of observations in each market style, sorted descending."""
    if "regime" not in df.columns:
        raise KeyError("classify() must be run before regime_breakdown()")
    share = df["regime"].value_counts(normalize=True, dropna=True)
    return share.sort_values(ascending=False)


def dominant_regime(df: pd.DataFrame) -> str:
    """The single most common market style in the sample."""
    counts = df["regime"].value_counts()
    return str(counts.index[0]) if len(counts) else "unknown"
