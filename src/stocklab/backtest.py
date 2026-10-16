"""Vectorised back-test and performance metrics.

Design choices that keep the evaluation honest:

* **One-bar lag.** The position decided at the close of day *t* is applied to
  day *t+1*'s return, so no look-ahead bias creeps in.
* **Transaction costs.** Charged in basis points on every change in position,
  which penalises strategies that churn.
* **Risk-adjusted metrics.** Sharpe and max drawdown matter more than raw
  return for this kind of study.
"""
from __future__ import annotations

from typing import Dict

import numpy as np
import pandas as pd

from stocklab.config import Config

TRADING_DAYS_DEFAULT = 252


def run(frame: pd.DataFrame, cfg: Config) -> Dict[str, object]:
    """Back-test the ``position`` column.

    Returns a dict with the ``equity`` and ``daily`` frames plus a flat
    ``metrics`` mapping for both the strategy and buy-and-hold.
    """
    if "position" not in frame.columns or "returns" not in frame.columns:
        raise KeyError("generate() and add_indicators() must run first")

    df = frame.copy()
    cost = cfg.cost_bps / 10_000.0

    # Trade on information available at the previous close.
    df["position_applied"] = df["position"].shift(1).fillna(0.0)
    df["turnover"] = df["position_applied"].diff().abs().fillna(
        df["position_applied"].abs()
    )
    df["cost"] = df["turnover"] * cost

    df["strategy_return"] = df["position_applied"] * df["returns"] - df["cost"]
    df["strategy_return"] = df["strategy_return"].fillna(0.0)

    equity = pd.DataFrame(index=df.index)
    equity["strategy"] = cfg.init_cash * (1.0 + df["strategy_return"]).cumprod()
    bh_returns = df["returns"].fillna(0.0)
    equity["buy_hold"] = cfg.init_cash * (1.0 + bh_returns).cumprod()

    trades = int((df["turnover"] > 0).sum())
    metrics = {
        "strategy": _metrics(df["strategy_return"], equity["strategy"], cfg, trades),
        "buy_hold": _metrics(bh_returns, equity["buy_hold"], cfg,
                             int((bh_returns != 0).sum())),
    }

    return {"daily": df, "equity": equity, "metrics": metrics}


def _metrics(
    returns: pd.Series, equity: pd.Series, cfg: Config, trades: int
) -> Dict[str, float]:
    """Compute the standard performance block for one return stream."""
    td = cfg.trading_days or TRADING_DAYS_DEFAULT
    n = max(len(returns), 1)
    clean = returns.replace([np.inf, -np.inf], np.nan).fillna(0.0)

    total_return = float(equity.iloc[-1] / cfg.init_cash - 1.0) if len(equity) else 0.0
    years = n / td
    cagr = float((1.0 + total_return) ** (1.0 / years) - 1.0) if years > 0 else 0.0

    mean = float(clean.mean())
    std = float(clean.std(ddof=0))
    ann_return = mean * td
    ann_vol = std * np.sqrt(td)
    sharpe = float(ann_return / ann_vol) if ann_vol > 0 else 0.0

    downside = clean[clean < 0]
    dstd = float(downside.std(ddof=0)) if len(downside) > 1 else 0.0
    sortino = float(ann_return / (dstd * np.sqrt(td))) if dstd > 0 else 0.0

    running_max = equity.cummax()
    drawdown = equity / running_max - 1.0
    max_dd = float(drawdown.min()) if len(drawdown) else 0.0

    active = clean[clean != 0.0]
    hit_rate = float((active > 0).mean()) if len(active) else 0.0

    return {
        "total_return": total_return,
        "cagr": cagr,
        "ann_return": float(ann_return),
        "ann_vol": float(ann_vol),
        "sharpe": sharpe,
        "sortino": sortino,
        "max_drawdown": max_dd,
        "hit_rate": hit_rate,
        "trades": float(trades),
        "days": float(n),
    }
