"""Technical indicators.

Pure functions: each takes a price series (or OHLC frame) and returns a new
series or frame. No global state, so everything is trivially unit-testable and
safe to compose.

Conventions
-----------
* ``close`` is used whenever a single price series is required.
* Wilder's smoothing is used for RSI and ATR (the standard for those studies).
* Annualisation uses ``cfg.trading_days`` (252 by default).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from stocklab.config import Config


# --------------------------------------------------------------------------- #
# Trend
# --------------------------------------------------------------------------- #
def sma(series: pd.Series, window: int) -> pd.Series:
    """Simple moving average."""
    return series.rolling(window=window, min_periods=window).mean()


def ema(series: pd.Series, span: int) -> pd.Series:
    """Exponential moving average."""
    return series.ewm(span=span, adjust=False, min_periods=span).mean()


def macd(
    series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9
) -> pd.DataFrame:
    """MACD line, signal line and histogram."""
    macd_line = ema(series, fast) - ema(series, slow)
    signal_line = ema(macd_line, signal)
    return pd.DataFrame(
        {
            "macd": macd_line,
            "macd_signal": signal_line,
            "macd_hist": macd_line - signal_line,
        }
    )


# --------------------------------------------------------------------------- #
# Momentum
# --------------------------------------------------------------------------- #
def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Relative Strength Index using Wilder's smoothing.

    Returns 0..100; undefined early values are filled with the neutral 50.
    """
    delta = series.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)

    avg_gain = gain.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()

    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    out = 100.0 - (100.0 / (1.0 + rs))
    # avg_loss == 0 means an unbroken rally -> RSI 100; flat start -> 50.
    out = out.where(~((avg_loss == 0) & (avg_gain > 0)), 100.0)
    return out.fillna(50.0)


# --------------------------------------------------------------------------- #
# Volatility
# --------------------------------------------------------------------------- #
def true_range(frame: pd.DataFrame) -> pd.Series:
    """True Range: max(high-low, |high-prev_close|, |low-prev_close|)."""
    prev_close = frame["close"].shift(1)
    ranges = pd.concat(
        [
            frame["high"] - frame["low"],
            (frame["high"] - prev_close).abs(),
            (frame["low"] - prev_close).abs(),
        ],
        axis=1,
    )
    return ranges.max(axis=1)


def atr(frame: pd.DataFrame, period: int = 14) -> pd.Series:
    """Average True Range (Wilder smoothing)."""
    tr = true_range(frame)
    return tr.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()


def bollinger(
    series: pd.Series, window: int = 20, num_std: float = 2.0
) -> pd.DataFrame:
    """Bollinger bands and the normalised %B position."""
    mid = sma(series, window)
    std = series.rolling(window=window, min_periods=window).std(ddof=0)
    upper = mid + num_std * std
    lower = mid - num_std * std
    width = (upper - lower) / mid.replace(0.0, np.nan)
    pct_b = (series - lower) / (upper - lower).replace(0.0, np.nan)
    return pd.DataFrame(
        {"bb_mid": mid, "bb_upper": upper, "bb_lower": lower,
         "bb_width": width, "bb_pct_b": pct_b}
    )


def realized_vol(
    returns: pd.Series, window: int = 20, trading_days: int = 252
) -> pd.Series:
    """Annualised rolling standard deviation of returns."""
    return returns.rolling(window=window, min_periods=window).std(ddof=0) * np.sqrt(
        trading_days
    )


def rolling_percentile(series: pd.Series, window: int) -> pd.Series:
    """Percentile rank (0..1) of each value within its trailing window.

    This is what makes "high volatility" *stock-relative* rather than an
    absolute threshold that would only suit one instrument.
    """
    return series.rolling(window=window, min_periods=window).rank(pct=True)


# --------------------------------------------------------------------------- #
# Composition
# --------------------------------------------------------------------------- #
def add_indicators(frame: pd.DataFrame, cfg: Config) -> pd.DataFrame:
    """Return a copy of ``frame`` with the full indicator set attached."""
    df = frame.copy()
    close = df["close"]

    df["returns"] = close.pct_change()
    df["log_returns"] = np.log(close).diff()

    df["sma_fast"] = sma(close, cfg.fast_ma)
    df["sma_slow"] = sma(close, cfg.slow_ma)
    df["ema_fast"] = ema(close, cfg.fast_ma)
    df["ema_slow"] = ema(close, cfg.slow_ma)
    df = df.join(macd(close, cfg.macd_fast, cfg.macd_slow, cfg.macd_signal))

    df["rsi"] = rsi(close, cfg.rsi_period)
    df = df.join(bollinger(close, cfg.bb_window, cfg.bb_std))

    df["atr"] = atr(df, cfg.atr_period)
    df["atr_pct"] = df["atr"] / close
    df["vol"] = realized_vol(df["returns"], cfg.vol_window, cfg.trading_days)
    df["vol_pct"] = rolling_percentile(df["vol"], cfg.vol_window * 5)

    # Normalised fast/slow separation: dimensionless, so one threshold works
    # across different price levels.
    df["trend_strength"] = (df["sma_fast"] - df["sma_slow"]) / df["sma_slow"]

    return df
