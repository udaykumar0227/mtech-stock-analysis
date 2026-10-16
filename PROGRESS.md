# Progress Report

**Project:** Market-Style Aware Stock Analyser
**Degree:** M.Tech — Data Science
**Last updated:** 2026-10-17
**Location:** `/home/uday/Documents/mtech-stock-analysis/`
**Repository:** https://github.com/udaykumar0227/mtech-stock-analysis

---

## 1. Objective

Build a data-science pipeline that analyses an Indian stock's price history,
identifies the prevailing **market style / regime** (trending up, trending
down, sideways; high or low volatility), and emits rule-based **trading inputs**
matched to that regime — with an interactive web app to select a stock and
inspect its history.

## 2. Work completed

| # | Area | File | Status |
|---|------|------|--------|
| 1 | Project overview, layout, usage | `README.md` | Done |
| 2 | Dependencies | `requirements.txt`, `requirements-ui.txt` | Done |
| 3 | Tunable parameters | `config.yaml` | Done |
| 4 | VCS hygiene | `.gitignore` | Done |
| 5 | Entry point | `main.py` | Done |
| 6 | Config dataclass + YAML loader | `src/stocklab/config.py` | Done |
| 7 | Data ingestion (CSV / yfinance / synthetic) | `src/stocklab/loader.py` | Done |
| 8 | Indicator library + data-quality guard | `src/stocklab/indicators.py` | Done |
| 9 | Market-style classification | `src/stocklab/regime.py` | Done |
| 10 | Regime-conditioned signals (long-only) | `src/stocklab/signals.py` | Done |
| 11 | Reference data + history profiling | `src/stocklab/company.py` | Done |
| 12 | Back-test engine + metrics | `src/stocklab/backtest.py` | Done |
| 13 | Auto research summary | `src/stocklab/report.py` | Done |
| 14 | CLI (`--list`, `--select`, `--profile-only`) | `src/stocklab/cli.py` | Done |
| 15 | Streamlit web UI (colour-coded redesign) | `app.py` | Done, serves HTTP 200 |
| 16 | App theme (violet accent, light, headless) | `.streamlit/config.toml` | Done |
| 17 | NSE reference dataset (28 companies) | `data/reference/nse_companies.csv` | Done |
| 18 | Unit tests | `tests/` | Done — **29/29 pass** |
| 19 | M.Tech report / title page | `docs/report.md` | Done |
| 20 | GitHub repository + push | remote `origin` | Done |

### 2.1 Web app — presentation layer

The Streamlit page was rebuilt so the analysis reads at a glance rather than
as a wall of plain tables:

- **Hero banner** — violet→blue→teal gradient carrying the company, sector,
  date span, live price with a green/red direction arrow, and the current
  market-style badge.
- **Colour-coded stat cards** — value and top border turn green/red by sign
  (all-time high, 52-week range, CAGR, strategy Sharpe).
- **Market-style timeline** — an Altair band chart painting the *entire*
  history in the six regime colours, with legend and hover tooltips.
- **Regime mix** — horizontal bars keyed to each regime's own colour, plus
  coloured chips in the breakdown table.
- **Charts** — regime-coloured price chart, strategy (violet) vs buy-and-hold
  (coral) equity curve, and a two-line drawdown comparison.
- **Sidebar** — gradient header, six one-click quick picks, advanced settings
  (dates, cost) tucked into an expander.
- **Onboarding** — emoji-labelled tabs, explainer tiles on the landing page,
  a spinner while fetching, actionable error text, and the SEBI long-only note
  stated up front.

## 3. How the pipeline works

1. **Ingest** — normalise OHLCV data to a clean, sorted, duplicate-free
   `DatetimeIndex` frame.
2. **Clean** — mask daily returns above `max_abs_return` as likely
   corporate-action artifacts, recording the count for disclosure.
3. **Feature engineering** — returns, SMA/EMA, MACD, RSI, ATR, Bollinger
   bands, realised volatility and its rolling percentile rank.
4. **Classify market style** — combine the normalised fast/slow MA spread
   (trend axis) with the volatility percentile (volatility axis) into labels
   such as `up_trend_low_vol` or `sideways_high_vol`.
5. **Generate signals** — momentum in uptrends, mean-reversion in quiet
   ranges, and position de-risking (halved size) in high-volatility regimes.
   Long-only by default.
6. **Back-test** — one-bar-lagged positions, basis-point transaction costs,
   then CAGR, annualised volatility, Sharpe, Sortino, max drawdown and hit rate
   versus buy-and-hold.
7. **Report** — a markdown summary whose interpretation is generated from the
   actual numbers, never templated.

## 4. Key decisions

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | **Rule-based, no ML** | Regime labelling by economic definition (trend × volatility) is deliberate and interpretable; success is judged by back-test performance, not prediction accuracy |
| 2 | **Indian equities (NSE/BSE)** | NSE symbols via `.NS` suffix; curated NSE reference list |
| 3 | **Long-only** (`allow_short: false`) | SEBI does not permit retail short-selling for delivery, so a long/short strategy would not be executable |
| 4 | **Stock-relative volatility** | Percentile rank means one threshold works across instruments |
| 5 | **Disclose, don't hide** | Excluded anomalous returns are reported in the method section |

## 5. Environment and verification

**Verified on 2026-10-17.** Dependencies installed into a project-local
virtual environment (`.venv`) — no system changes, no `sudo` required.

| Item | Result |
|---|---|
| pip bootstrap | `python3 -m ensurepip` → pip 26.0.1 (no sudo needed) |
| Virtualenv | `.venv/` created with Python 3.14.3 |
| Packages | pandas 3.0.6, numpy 2.5.4, PyYAML 6.0.3, yfinance 1.7.0, streamlit 1.66.0 |
| Pipeline (synthetic) | ✅ runs end-to-end |
| Pipeline (live NSE) | ✅ 26.8 years of RELIANCE.NS |
| Interactive web app | ✅ serves at http://localhost:8501 (root 200, `/_stcore/health` = `ok`) |
| Web app (headless) | ✅ `streamlit.testing.AppTest` on the real app — 0 exceptions, 4 tabs, 4 dataframes, 5 charts |
| Unit tests | ✅ **29 / 29 pass** |
| Reference list validation | ✅ 28 symbols checked; 2 dead tickers found and fixed |
| Reproducibility | ✅ re-run of RELIANCE.NS reproduced the same figures to the basis point |

> `sudo dnf install python3-pip` was not usable (no terminal for the password
> prompt). The `ensurepip` + `venv` route achieves the same result without root.

## 6. Latest result (RELIANCE.NS, 2000–2026, 6,680 trading days)

| Metric | Strategy | Buy & hold |
|---|---:|---:|
| Total return | +104.27% | +9,057.14% |
| CAGR | 2.73% | 18.58% |
| Annualised volatility | **12.22%** | 32.49% |
| Sharpe | 0.28 | **0.69** |
| Max drawdown | **−48.46%** | −68.18% |
| Trades | 416 | — |

**Finding:** the long-only regime strategy roughly halves volatility and cuts
drawdown, but does **not** beat buy-and-hold on return, because it sits flat
~76% of the time in a strong uptrend. This is an honest, data-derived result,
not a defect — and it makes the parameter sweep the key next experiment.

## 7. Bugs found and fixed

1. **Hard-coded report narrative.** The Interpretation section asserted a
   positive strategy Sharpe regardless of the data. Now generated
   conditionally from the actual metrics (`report._interpretation`).
2. **Dead tickers after corporate renames.** `ZOMATO.NS` → `ETERNAL.NS`
   (Apr 2025) and `TATAMOTORS.NS` → `TMPV.NS` (Oct 2025) returned no data.
   Fixed in the reference file, with space-insensitive legacy-name fallback.
3. **Corporate-action artifacts.** Two unadjusted rows in Reliance's 2005
   history (+337.48%, −76.99%) inflated annual volatility from a true **32%**
   to **74%**, and made the strategy appear profitable when it was not
   (+58.87% became −40.24% once corrected). Guard added via `max_abs_return`,
   with the excluded count disclosed in the report.
4. **Broken performance-tab verdict.** The UI verdict string was assembled
   with a leftover `walrus :=` / `.replace("100%", "")` expression that printed
   a nonsense percentage. It now derives the real invested-day exposure from
   the back-test's `position_applied` column. Also dropped a dead fourth field
   from the metric-row table.

## 8. Known limitations

- `docs/report.md` is a template — the dissertation chapters are not written.
- The parameter defaults are untuned; no hyper-parameter sweep yet.
- The reference list covers 28 large-caps only, and its IPO dates are
  indicative, not authoritative.
- Analysis notebooks are planned but not yet written.
- The Streamlit app requires the terminal to stay open while running.

## 9. Suggested next steps

1. Hyper-parameter sweep over `trend_threshold`, `vol_high_pct`, `fast_ma`,
   `slow_ma` — the honest result shows the defaults are not optimal.
2. Portfolio extension: apply across many stocks rather than one at a time.
3. Write the analysis notebooks (exploration, regime charts, sensitivity heat-map).
4. Fill in the dissertation chapters using `docs/report.md`.
5. Consider walk-forward validation to guard against overfitting in the sweep.

## 10. Working agreement

Per instruction, the assistant **asks the user for one confirmation before any
execution** — running commands or writing/editing files in this project.
