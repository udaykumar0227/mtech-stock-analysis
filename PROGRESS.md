# Progress Report

**Project:** Market-Style Aware Stock Analyser
**Degree:** M.Tech — Data Science
**Report date:** 2026-10-17
**Location:** `/home/uday/Documents/mtech-stock-analysis/`

---

## 1. Objective

Build a data-science pipeline that analyses a stock's price history, identifies
the prevailing **market style (regime)** — trending up, trending down, sideways,
and high/low volatility — and emits rule-based **trading inputs** matched to
that regime, with an objective back-test to measure their quality.

## 2. Work completed

The full project scaffold and implementation are in place.

| # | Area | File | Status |
|---|------|------|--------|
| 1 | Project overview, layout, usage | `README.md` | Done |
| 2 | Dependencies | `requirements.txt` | Done |
| 3 | Tunable parameters | `config.yaml` | Done |
| 4 | VCS hygiene | `.gitignore` | Done |
| 5 | Entry point | `main.py` | Done |
| 6 | Config dataclass + YAML loader | `src/stocklab/config.py` | Done |
| 7 | Data ingestion (CSV / yfinance / synthetic) | `src/stocklab/loader.py` | Done |
| 8 | Indicator library | `src/stocklab/indicators.py` | Done |
| 9 | Market-style classification | `src/stocklab/regime.py` | Done |
| 10 | Regime-conditioned signals | `src/stocklab/signals.py` | Done |
| 11 | Back-test engine + metrics | `src/stocklab/backtest.py` | Done |
| 12 | Auto research summary | `src/stocklab/report.py` | Done |
| 13 | Command-line interface | `src/stocklab/cli.py` | Done |
| 14 | Unit tests | `tests/test_indicators.py` | Done — 10/10 pass |
| 15 | M.Tech report / title page | `docs/report.md` | Done |
| 16 | Notebook workspace notes | `notebooks/README.md` | Done |

## 3. How the pipeline works

1. **Ingest** — normalise OHLCV data to a clean, sorted, duplicate-free
   `DatetimeIndex` frame.
2. **Feature engineering** — returns, SMA/EMA, MACD, RSI, ATR, Bollinger bands,
   realised volatility and its rolling percentile rank.
3. **Classify market style** — combine the normalised fast/slow MA spread
   (trend axis) with the volatility percentile (volatility axis) into labels
   such as `up_trend_low_vol` or `sideways_high_vol`.
4. **Generate signals** — momentum in trends, mean-reversion in quiet ranges,
   and position de-risking (halved size) in high-volatility regimes.
5. **Back-test** — one-bar-lagged positions, basis-point transaction costs,
   then CAGR, annualised volatility, Sharpe, Sortino, max drawdown and hit rate
   versus buy-and-hold.
6. **Report** — a markdown summary of the regime mix, signal activity and
   relative performance.

## 4. Key design decisions

- **Stock-relative volatility.** "High volatility" is a *percentile rank*
  within a trailing window, so one threshold works across instruments rather
  than an absolute number tuned to a single price scale.
- **No look-ahead bias.** The position decided at close *t* is applied to
  *t+1*'s return.
- **Costs modelled.** Every position change is charged basis points, so
  churn-heavy strategies are penalised.
- **Offline demo path.** A synthetic multi-regime generator lets the whole
  pipeline run and be demonstrated with no network access.
- **Separation of concerns.** Pure indicator functions and a thin CLI make the
  logic importable from notebooks and unit-testable.

## 5. Environment and verification

**Verified on 2026-10-17.** Dependencies were installed into a project-local
virtual environment (`.venv`) — no system changes, no `sudo` required.

| Item | Result |
|---|---|
| `pip` bootstrap | `python3 -m ensurepip` → pip 26.0.1 (no sudo needed) |
| Virtualenv | `.venv/` created with Python 3.14.3 |
| Packages | pandas 3.0.6, numpy 2.5.4, PyYAML 6.0.3, yfinance 1.7.0 |
| Pipeline (synthetic, 1,500 days) | ✅ runs end-to-end, writes `docs/demo_output/` |
| Unit tests | ✅ **10 / 10 pass** (0.04 s) |

> Note: `sudo dnf install python3-pip` was **not** usable here (no terminal for
> the password prompt). The `ensurepip` + `venv` route achieves the same result
> without root.

### Latest run (synthetic, seed 14, 1,500 days)

| Metric | Strategy | Buy & hold |
|---|---:|---:|
| Total return | 14.51% | 27.62% |
| Annualised volatility | 10.05% | 18.50% |
| Sharpe | 0.28 | 0.31 |
| Max drawdown | −23.41% | −46.30% |
| Trades | 171 | 1,499 |

**Finding:** on this series the strategy roughly halved volatility and cut
drawdown (−46% → −23%), but buy-and-hold still won on raw return, because
long/short rules give up upside in a rising market. This is an honest,
data-derived result — not a defect.

### Issue found and fixed during verification

The report's Interpretation section was originally **hard-coded** to claim a
positive strategy Sharpe, which the real numbers contradicted. It is now
generated conditionally from the actual metrics in
`report._interpretation()`, so the narrative can never contradict the tables.

### Remaining limitation

- `--ticker` mode (yfinance) has not been exercised; it needs internet and a
  valid symbol. `--csv` and `--synthetic` are fully working.

## 6. Suggested next steps

1. ✅ ~~Install dependencies and run a smoke-test~~ — done (see Section 5).
2. ✅ ~~Run the unit tests~~ — done, 10/10 pass.
3. Load a real ticker (via `--csv` or `--ticker`) and record baseline metrics.
4. Add a hyper-parameter sweep over `fast_ma`, `slow_ma`, `trend_threshold`
   and `vol_high_pct` — the demo shows results are sensitive to these, so a
   sweep is the logical next experiment.
5. Write the analysis notebook in `notebooks/` (exploration + charts).
6. Fill in the dissertation chapters using `docs/report.md` as the template.

## 7. Working agreement

Per instruction, the assistant **asks the user for one confirmation before any
execution** — running commands or writing/editing files in this project.
