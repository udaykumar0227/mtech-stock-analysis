"""Regime-conditioned signal generation.

This is the layer that turns a market style into an actual *input* (a trading
recommendation). The mapping encodes well-known market wisdom:

| Market style            | Strategy family       |
|-------------------------|-----------------------|
| Trending up             | Momentum / breakout   |
| Trending down           | Short momentum *      |
| Sideways + low vol      | Mean-reversion (long) |
| Sideways + high vol     | Mean-reversion (short) * |
| Any + high vol          | De-risk (halve size)  |

\* only when ``cfg.allow_short`` is true. The **default is long-only**
(``allow_short=False``), producing signals in ``{0, +1}`` — long, hold or exit.
That is deliberate: SEBI does not permit Indian retail investors to short-sell
for delivery, so a long/short daily strategy would not be executable.

Outputs a ``signal`` in {0, +1} (or {-1, 0, +1} with shorting enabled) and a
continuous ``position`` which applies the high-volatility size scaling.
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

    allow_short = bool(getattr(cfg, "allow_short", False))

    signal = pd.Series(0, index=df.index, dtype="int64")
    strategy = pd.Series("flat", index=df.index, dtype="string")

    trend_up = df["trend_state"] == TREND_UP
    trend_down = df["trend_state"] == TREND_DOWN
    sideways = df["trend_state"] == TREND_SIDEWAYS

    # --- Momentum in uptrends: follow the MACD histogram -------------------- #
    long_mom = trend_up & (df["macd_hist"] > 0)
    signal = signal.mask(long_mom, 1)
    strategy = strategy.mask(long_mom, "momentum_long")

    # --- Short momentum in downtrends (only if shorting is enabled) --------- #
    if allow_short:
        short_mom = trend_down & (df["macd_hist"] < 0)
        signal = signal.mask(short_mom & (signal == 0), -1)
        strategy = strategy.mask(short_mom & (signal == -1), "momentum_short")

    # --- Mean-reversion in quiet ranges (long leg) -------------------------- #
    mr_long = sideways & (df["rsi"] < cfg.rsi_oversold) & (df["bb_pct_b"] < 0.05)
    signal = signal.mask(mr_long & (signal == 0), 1)
    strategy = strategy.mask(mr_long & (signal == 1), "mean_reversion_long")

    # --- Mean-reversion short leg (only if shorting is enabled) ------------- #
    if allow_short:
        mr_short = (
            sideways & (df["rsi"] > cfg.rsi_overbought) & (df["bb_pct_b"] > 0.95)
        )
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
