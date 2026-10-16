"""Data ingestion for the analyser.

Two sources are supported:

* ``load_csv``        - a local OHLCV CSV (works fully offline).
* ``load_yfinance``   - live/historical data via the optional yfinance package.
* ``synthetic_ohlcv`` - a reproducible random-walk series for demos and tests.

Every loader returns a tidy DataFrame indexed by a tz-naive ``DatetimeIndex``
with columns ``open, high, low, close, volume`` (lower-case), sorted ascending
and free of duplicate index entries. Normalising here means the rest of the
pipeline never has to worry about data hygiene.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional, Sequence

import numpy as np
import pandas as pd

OHLCV = ["open", "high", "low", "close", "volume"]


def _normalise(df: pd.DataFrame, date_col: Optional[str] = None) -> pd.DataFrame:
    """Coerce an arbitrary OHLCV frame into the canonical shape."""
    if df.empty:
        raise ValueError("Input data is empty")

    out = df.copy()
    out.columns = [str(c).strip().lower() for c in out.columns]

    # Promote a date-like column to the index when needed.
    if date_col is not None:
        col = date_col.strip().lower()
        if col in out.columns:
            out = out.set_index(col)
    elif not isinstance(out.index, pd.DatetimeIndex):
        for candidate in ("date", "datetime", "timestamp", "time"):
            if candidate in out.columns:
                out = out.set_index(candidate)
                break

    missing = [c for c in OHLCV if c not in out.columns]
    if missing:
        raise ValueError(f"Missing required OHLCV columns: {missing}")

    out.index = pd.to_datetime(out.index, errors="coerce", utc=False)
    if getattr(out.index, "tz", None) is not None:
        out.index = out.index.tz_localize(None)

    out = out.loc[out.index.notna()].copy()
    out = out[OHLCV].apply(pd.to_numeric, errors="coerce")
    out = out[~out.index.duplicated(keep="last")]
    out = out.sort_index().dropna(subset=["close"])

    if len(out) < 2:
        raise ValueError("Need at least two valid rows after cleaning")
    return out


def load_csv(path: str | Path, date_col: Optional[str] = None) -> pd.DataFrame:
    """Load OHLCV data from a CSV file."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"CSV not found: {p}")
    return _normalise(pd.read_csv(p), date_col=date_col)


def load_yfinance(
    ticker: str, start: str, end: str = "", interval: str = "1d"
) -> pd.DataFrame:  # pragma: no cover - requires network
    """Download OHLCV data through yfinance (optional dependency).

    An empty ``end`` means "up to today".
    """
    try:
        import yfinance as yf  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "yfinance is required for --ticker mode: pip install yfinance"
        ) from exc

    raw = yf.download(
        ticker, start=start or None, end=end or None, interval=interval,
        auto_adjust=True, progress=False,
    )
    if raw is None or raw.empty:
        raise ValueError(f"No data returned for {ticker!r}")
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)
    return _normalise(raw)


def synthetic_ohlcv(
    days: int = 1500,
    seed: int = 14,
    start: str = "2019-01-01",
    regimes: Sequence[float] = (0.0015, -0.0010, 0.0002, 0.0008),
) -> pd.DataFrame:
    """Generate a reproducible series that cycles through several regimes.

    The point is to have a dataset on which *every* market style appears, so
    the classifier and the strategy switch can be demonstrated without a
    network connection.
    """
    rng = np.random.default_rng(seed)
    n = int(days)
    block = max(n // (len(regimes) * 3), 20)

    drifts, vols = [], []
    idx = 0
    k = 0
    while idx < n:
        r = regimes[k % len(regimes)]
        # Trending regimes are noisier; the sideways regime is quieter.
        # The regime drifts now net mildly positive, so the demo shows a
        # rising buy-and-hold baseline for the strategy to be judged against.
        vol = 0.006 if abs(r) < 1e-9 else 0.012
        drifts.append(np.full(block, r))
        vols.append(np.full(block, vol))
        idx += block
        k += 1

    drift = np.concatenate(drifts)[:n]
    vol = np.concatenate(vols)[:n]
    shocks = rng.normal(0.0, 1.0, size=n)
    returns = drift + vol * shocks
    close = 100.0 * np.exp(np.cumsum(returns))

    high = close * (1.0 + np.abs(rng.normal(0.0, 0.004, size=n)))
    low = close * (1.0 - np.abs(rng.normal(0.0, 0.004, size=n)))
    open_ = np.concatenate([[close[0]], close[:-1]])
    volume = rng.integers(1_000_000, 5_000_000, size=n).astype(float)

    index = pd.bdate_range(start=start, periods=n, name="date")
    frame = pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": volume},
        index=index,
    )
    frame["high"] = frame[["open", "close", "high"]].max(axis=1)
    frame["low"] = frame[["open", "close", "low"]].min(axis=1)
    return frame


def save_processed(df: pd.DataFrame, out_dir: str | Path, name: str) -> Path:
    """Persist a processed frame, creating parent directories as needed."""
    d = Path(out_dir)
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{name}.csv"
    df.to_csv(path)
    return path
