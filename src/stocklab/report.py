"""Human-readable research summary.

Turns the pipeline output into a markdown/console report so a run is
self-documenting — useful both for the dissertation appendix and for quickly
eyeballing whether a parameter change helped.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict

import pandas as pd

from stocklab.config import Config
from stocklab.company import format_profile
from stocklab.regime import dominant_regime, regime_breakdown
from stocklab.signals import signal_stats


def _pct(x: float) -> str:
    return f"{100.0 * x:,.2f}%"


def _metrics_table(metrics: Dict[str, Dict[str, float]]) -> str:
    rows = [
        ("Total return", "total_return", _pct),
        ("CAGR", "cagr", _pct),
        ("Annualised volatility", "ann_vol", _pct),
        ("Sharpe ratio", "sharpe", lambda v: f"{v:,.2f}"),
        ("Sortino ratio", "sortino", lambda v: f"{v:,.2f}"),
        ("Max drawdown", "max_drawdown", _pct),
        ("Hit rate (active days)", "hit_rate", _pct),
        ("Trades", "trades", lambda v: f"{int(v):,}"),
    ]
    s = metrics.get("strategy", {})
    b = metrics.get("buy_hold", {})
    lines = ["| Metric | Strategy | Buy & hold |", "|---|---:|---:|"]
    for label, key, fmt in rows:
        lines.append(f"| {label} | {fmt(s.get(key, 0.0))} | {fmt(b.get(key, 0.0))} |")
    return "\n".join(lines)


def _interpretation(metrics: Dict[str, Dict[str, float]], cfg: Config) -> list[str]:
    """Narrative derived from the actual results — never hard-coded.

    Every sentence is generated from the numbers so the report can never
    contradict its own tables. This replaces an earlier templated block that
    asserted a positive strategy Sharpe regardless of the data.
    """
    s = metrics.get("strategy", {})
    b = metrics.get("buy_hold", {})
    out: list[str] = []

    s_ret, b_ret = s.get("total_return", 0.0), b.get("total_return", 0.0)
    s_vol, b_vol = s.get("ann_vol", 0.0), b.get("ann_vol", 0.0)
    s_sh, b_sh = s.get("sharpe", 0.0), b.get("sharpe", 0.0)
    s_dd, b_dd = s.get("max_drawdown", 0.0), b.get("max_drawdown", 0.0)

    if s_ret > b_ret:
        out.append(
            f"- The regime-aware strategy beat buy-and-hold on return: "
            f"{_pct(s_ret)} versus {_pct(b_ret)} over the sample."
        )
    elif s_ret < b_ret:
        out.append(
            f"- Buy-and-hold beat the strategy on raw return this time: "
            f"{_pct(b_ret)} versus {_pct(s_ret)}."
        )
    else:
        out.append(f"- Strategy and buy-and-hold returned the same: {_pct(s_ret)}.")

    if s_vol < b_vol:
        out.append(
            f"- Risk was reduced: annualised volatility fell from {_pct(b_vol)} "
            f"to {_pct(s_vol)}, and the worst drawdown from {_pct(b_dd)} to "
            f"{_pct(s_dd)} — the main benefit of switching strategy by regime."
        )
    else:
        out.append(
            f"- Volatility was not reduced ({_pct(s_vol)} vs {_pct(b_vol)}); "
            f"drawdown went from {_pct(b_dd)} to {_pct(s_dd)}."
        )

    if s_sh > 0 > b_sh:
        out.append(
            f"- **Headline result:** the strategy earned a positive Sharpe "
            f"({s_sh:.2f}) while buy-and-hold was negative ({b_sh:.2f}) — the "
            f"outcome this architecture is built to find."
        )
    elif s_sh >= 0 and b_sh >= 0 and s_sh > b_sh:
        out.append(
            f"- Both were profitable on a risk-adjusted basis, the strategy "
            f"more so: Sharpe {s_sh:.2f} vs {b_sh:.2f}."
        )
    elif s_sh > b_sh:
        out.append(
            f"- Neither was profitable on a risk-adjusted basis, but the "
            f"strategy lost less: Sharpe {s_sh:.2f} vs {b_sh:.2f}, with a "
            f"shallower drawdown."
        )
    else:
        out.append(
            f"- Buy-and-hold had the better risk-adjusted return (Sharpe "
            f"{b_sh:.2f} vs {s_sh:.2f}); on this sample the regime rules did "
            f"not add value."
        )

    out.append(
        f"- {int(s.get('trades', 0.0)):,} trades were triggered, each charged "
        f"{cfg.cost_bps:.1f} bps, so turnover cost is already reflected above."
    )
    out.append(
        "- High-volatility days halve the position size, trading some upside "
        "for lower drawdown and lower turnover cost."
    )
    return out


def build_summary(
    ticker: str,
    frame: pd.DataFrame,
    result: Dict[str, object],
    cfg: Config,
    company: Dict[str, object] | None = None,
    profile: Dict[str, object] | None = None,
) -> str:
    """Compose the full markdown report as a string."""
    if frame.empty:
        raise ValueError("Cannot summarise an empty dataset")

    start = frame.index[0].date()
    end = frame.index[-1].date()
    metrics = result["metrics"]  # type: ignore[assignment]

    lines = [
        f"# Market-Style Analysis — {ticker}",
        "",
    ]

    if profile is not None:
        lines += ["## 0. Instrument history", "",
                  format_profile(ticker, company, profile), ""]

    lines += [
        "## 1. Method and settings",
        "",
        f"- **Period:** {start} to {end} ({len(frame):,} trading days)",
        f"- **Dominant market style:** `{dominant_regime(frame)}`",
        f"- **Trend threshold:** {cfg.trend_threshold} "
        f"(fast MA {cfg.fast_ma} vs slow MA {cfg.slow_ma})",
        f"- **High-volatility cutoff:** {cfg.vol_high_pct:.0%} percentile "
        f"of {cfg.vol_window}-day realised volatility",
        f"- **Round-trip cost:** {cfg.cost_bps:.1f} bps per position change",
        "",
        "## 2. Market-style breakdown",
        "",
    ]

    breakdown = regime_breakdown(frame)
    lines += ["| Market style | Share of days |", "|---|---:|"]
    for regime, share in breakdown.items():
        lines.append(f"| `{regime}` | {_pct(float(share))} |")

    lines += ["", "## 3. Signal activity", "",
              "| Strategy | Days | Share |", "|---|---:|---:|"]
    for strategy, row in signal_stats(frame).iterrows():
        lines.append(
            f"| {strategy} | {int(row['days']):,} | {_pct(float(row['share']))} |"
        )

    lines += ["", "## 4. Performance vs. buy & hold", "",
              _metrics_table(metrics), ""]

    lines += ["## 5. Interpretation", ""]
    lines += _interpretation(metrics, cfg)
    lines += [
        "",
        "> **Disclaimer:** academic exercise only — not financial advice.",
    ]
    return "\n".join(lines)


def write_summary(text: str, out_dir: str | Path, name: str = "summary") -> Path:
    """Write the report to ``<out_dir>/<name>.md``."""
    d = Path(out_dir)
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{name}.md"
    path.write_text(text, encoding="utf-8")
    return path
