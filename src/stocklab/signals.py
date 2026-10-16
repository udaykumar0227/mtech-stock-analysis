"""Regime-conditioned signal generation.

This is the layer that turns a market style into an actual *input* (a trading
recommendation). The mapping encodes well-known market wisdom:

| Market style            | Strategy family       |
|-------------------------|-----------------------|
| Trending up             | Momentum / breakout   |
| Trending down           | Short momentum        |
| Sideways + low vol      | Mean-reversion        |
| Any + high vol          | De-risk (halve size)  |

Outputs a ``signal`` in {-1, 0, +1} (target position: short / flat / long) and
a continuous ``position`` which applies the high-volatility size scaling.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from stocklab.config import Config
from stocklab.regime import TREND_DOWN, TREND_SIDEWAYS, TREND_UP, VOL_HIGH


def generate(frame: pd.DataFrame, cfg: Config) -> pd.DataFrame:
    """Attach ``signal``, ``position`` and ``strategy`` columns."""
    df = frame.copy()
    for col in ("regime", "trend_state", "rsi", "macd_hist", "bb_pct_b"):
        if col not in df.columns:
            raise KeyError(f"missing {col!r}; run the pipeline stages first")

    signal = pd.Series(0, index=df.index, dtype="int64")
    strategy = pd.Series("flat", index=df.index, dtype="string")

    trend_up = df["trend_state"] == TREND_UP
    trend_down = df["trend_state"] == TREND_DOWN
    sideways = df["trend_state"] == TREND_SIDEWAYS

    # --- Momentum in uptrends: follow the MACD histogram -------------------- #
    long_mom = trend_up & (df["macd_hist"] > 0)
    signal = signal.mask(long_mom, 1)
    strategy = strategy.mask(long_mom, "momentum_long")

    # --- Short momentum in downtrends --------------------------------------- #
    short_mom = trend_down & (df["macd_hist"] < 0)
    signal = signal.mask(short_mom & (signal == 0), -1)
    strategy = strategy.mask(short_mom & (signal == -1), "momentum_short")

    # --- Mean-reversion in quiet ranges ------------------------------------- #
    mr_long = sideways & (df["rsi"] < cfg.rsi_oversold) & (df["bb_pct_b"] < 0.05)
    mr_short = sideways & (df["rsi"] > cfg.rsi_overbought) & (df["bb_pct_b"] > 0.95)
    signal = signal.mask(mr_long & (signal == 0), 1)
    strategy = strategy.mask(mr_long & (signal == 1), "mean_reversion_long")
    signal = signal.mask(mr_short & (signal == 0), -1)
    strategy = strategy.mask(mr_short & (signal == -1), "mean_reversion_short")

    # --- De-risk in high-volatility regimes --------------------------------- #
    scale = np.where(df["vol_state"] == VOL_HIGH, cfg.high_vol_size, 1.0)

    df["signal"] = signal
    df["position"] = signal.astype(float) * scale
    df["strategy"] = strategy
    return df


def signal_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Count of days per strategy label, with share of the sample."""
    if "strategy" not in df.columns:
        raise KeyError("generate() must be run before signal_stats()")
    counts = df["strategy"].value_counts()
    out = pd.DataFrame({"days": counts})
    out["share"] = out["days"] / len(df)
    return out
