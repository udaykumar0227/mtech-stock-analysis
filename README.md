# Market-Style Aware Stock Analyser

An M.Tech (Data Science) project that analyses an Indian stock's price history,
detects the prevailing **market style / regime** (trending up, trending down,
sideways, high-volatility), and generates rule-based **trading inputs**
(signals) appropriate to that regime — with an interactive web app to pick a
stock and inspect its history.

The central idea: no single strategy works in every market. A trend-following
rule wins in trending markets but bleeds in choppy ones, and vice versa. This
project first *classifies the regime*, then *selects the strategy* that suits
it, and finally *back-tests* the result so the quality of the inputs can be
measured objectively.

> **Academic exercise only — not financial advice.**

## Features

**Analysis**
- Regime detection on two axes: **trend** (up/down/sideways) × **volatility**
  (high/low, as a *percentile* of the stock's own history)
- Regime-conditioned signals: momentum in trends, mean-reversion in quiet
  ranges, position de-risking in high-volatility regimes
- Vectorised back-test vs. buy-and-hold with one-bar lag and transaction costs
- Auto-generated markdown research summary with risk-adjusted metrics

**Stock selection and history**
- A curated NSE reference list of 28 companies with IPO/listing dates
- `--list` to browse, `--select` for an interactive numbered menu
- History profile: IPO/listing date, issue price, first/last data date,
  all-time high/low (with dates), 52-week range, CAGR, growth from issue price

**Interactive web app** (`app.py`, Streamlit)
- Dropdown of all 28 stocks (or type any ticker)
- Profile card, price chart, equity curve, market-style mix, signal activity,
  performance table, latest per-day readings, CSV download

## Why this is M.Tech-scale

| Component | What it demonstrates |
|-----------|---------------------|
| Data pipeline | Ingestion, cleaning, alignment of OHLCV time series |
| Data quality | Corporate-action artifact detection and disclosure |
| Feature engineering | Returns, moving averages, RSI, MACD, ATR, Bollinger bands |
| Unsupervised labelling | Regime detection from trend + volatility features |
| Decision logic | Regime-conditioned signal generation |
| Evaluation | Vectorised back-test, risk-adjusted metrics, drawdown |
| Delivery | CLI + interactive web UI |

## Project layout

```
mtech-stock-analysis/
├── app.py                   # Streamlit web UI
├── main.py                  # CLI entry point
├── config.yaml              # tunable parameters
├── requirements.txt         # core dependencies
├── requirements-ui.txt      # Streamlit (optional)
├── data/
│   ├── reference/
│   │   └── nse_companies.csv   # curated NSE list with IPO dates
│   ├── raw/                 # input CSVs
│   └── processed/           # cached indicator output
├── docs/
│   └── report.md            # M.Tech report / title page template
├── notebooks/README.md
├── src/stocklab/
│   ├── config.py            # Config dataclass + YAML loader
│   ├── loader.py            # CSV / yfinance / synthetic ingestion
│   ├── indicators.py        # technical indicators + data-quality guard
│   ├── regime.py            # market-style classification
│   ├── signals.py           # regime-conditioned signal generation
│   ├── company.py           # reference data + history profiling
│   ├── backtest.py          # vectorised back-test + metrics
│   ├── report.py            # markdown research summary
│   └── cli.py               # command-line interface
└── tests/                   # 29 unit tests
```

## Setup

```bash
cd mtech-stock-analysis
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Optional (web UI):

```bash
pip install -r requirements-ui.txt
```

## Usage

### Interactive web app

```bash
streamlit run app.py
```
Opens at `http://localhost:8501`. Pick a stock from the dropdown and press
**Analyse**.

### Command line

```bash
# Browse the reference list
python main.py --list

# Interactive stock picker -> profile + full analysis
python main.py --select

# History profile only
python main.py --ticker RELIANCE.NS --profile-only

# Full analysis, writing outputs
python main.py --ticker RELIANCE.NS --out docs/reliance_output

# Offline CSV (columns: date,open,high,low,close,volume)
python main.py --csv data/raw/RELIANCE.csv --out docs/reliance_output

# Offline demo on synthetic multi-regime data
python main.py --synthetic --out docs/demo_output
```

### Tests

```bash
python -m unittest discover -s tests
```

## Reference data — read this before citing IPO dates

Free market APIs **do not provide IPO or listing dates**. yfinance's earliest
row is simply where the exchange feed begins, which is usually *after* the real
listing. IPO/listing dates therefore come from the hand-maintained
`data/reference/nse_companies.csv`, and are **indicative, not authoritative**.
Blank dates mean "not established in this file". Verify against the prospectus,
NSE/BSE or SEBI filings before citing.

Corporate actions also break tickers. Two renames are already handled:

| Old symbol | New symbol | Change |
|---|---|---|
| `ZOMATO.NS` | `ETERNAL.NS` | Zomato Ltd renamed Eternal Ltd, 9 Apr 2025 |
| `TATAMOTORS.NS` | `TMPV.NS` | Renamed Tata Motors Passenger Vehicles, 24 Oct 2025 (demerger; CV arm `TMLCV`) |

Legacy names (e.g. `zomato`, `TATAMOTORS.NS`) still resolve to the new symbols.

## Methodology in one paragraph

Daily returns are computed from closing prices. Trend is measured as the
normalised spread between a fast and a slow moving average, confirmed by MACD.
Volatility is measured as the rolling std-dev of returns and converted to a
percentile rank within a trailing look-back window, so "high volatility" is
relative to that stock's own history rather than an absolute number. The two
axes combine into a discrete market style. Each style maps to a strategy
family: momentum in trends, mean-reversion in quiet ranges, and de-risking in
high-volatility regimes. Positions are lagged one bar to avoid look-ahead bias,
and transaction costs are charged on every change in position.

## Key design decisions

- **Stock-relative volatility.** "High volatility" is a *percentile rank*, so
  one threshold works across instruments rather than an absolute number tuned
  to a single price scale.
- **Long-only by default** (`allow_short: false`). SEBI does not permit Indian
  retail investors to short-sell for delivery, so a long/short daily strategy
  would not be executable. Signals are `{0, +1}` — long, hold or exit. Set
  `allow_short: true` to re-enable the short legs.
- **No look-ahead bias.** The position decided at close *t* is applied to
  *t+1*'s return.
- **Costs modelled.** Every position change is charged basis points, so
  churn-heavy strategies are penalised.
- **Corporate-action guard.** `max_abs_return` (default 0.50) masks daily
  returns above the threshold as likely demerger/split adjustment artifacts,
  and the count is disclosed in the report. See below.
- **Rule-based, not ML.** Regime detection is deliberate, unsupervised
  labelling by economic definition (trend × volatility), chosen for
  interpretability and reproducibility. Success is measured by back-test
  performance, not prediction accuracy.

## An honest result

On 26.8 years of Reliance (RELIANCE.NS) with default parameters, the
long-only strategy **does not beat buy-and-hold**:

| Metric | Strategy | Buy & hold |
|---|---:|---:|
| Total return | +104.27% | +9,057.14% |
| CAGR | 2.73% | 18.58% |
| Annualised volatility | **12.22%** | 32.49% |
| Sharpe | 0.28 | **0.69** |
| Max drawdown | **−48.46%** | −68.18% |

It roughly **halves volatility and cuts drawdown**, but gives up return by
sitting flat ~76% of the time in a strong uptrend. Whether that trade-off is
worth it is precisely what the parameter sweep is for. The auto-generated
report says this from the data itself — it is not templated.

## Bugs found and fixed during development

1. **Hard-coded report narrative** — the Interpretation section asserted a
   positive strategy Sharpe regardless of the data. Now generated
   conditionally from the actual metrics.
2. **Dead tickers** — `ZOMATO.NS` and `TATAMOTORS.NS` stopped resolving after
   corporate renames. Both fixed, with legacy-name fallback matching.
3. **Corporate-action artifacts** — two unadjusted rows in Reliance's 2005
   history (+337% then −77%) inflated annual volatility from a true **32%** to
   **74%**, and made the strategy look profitable when it was not. Guard added.
