# Market-Style Aware Stock Analyser

An M.Tech (Data Science) project that analyses a stock's price history,
detects the prevailing **market style / regime** (trending up, trending down,
sideways, high-volatility), and generates rule-based **trading inputs**
(signals) appropriate to that regime.

The central idea: no single strategy works in every market. A trend-following
rule wins in trending markets but bleeds in choppy ones, and vice versa. This
project first *classifies the regime*, then *selects the strategy* that suits
it, and finally *back-tests* the result so the quality of the inputs can be
measured objectively.

## Why this is an M.Tech-scale project

| Component | What it demonstrates |
|-----------|----------------------|
| Data pipeline | Ingestion, cleaning, alignment of OHLCV time series |
| Feature engineering | Returns, moving averages, RSI, MACD, ATR, Bollinger bands |
| Unsupervised labelling | Regime detection from trend + volatility features |
| Decision logic | Regime-conditioned signal generation |
| Evaluation | Vectorised back-test, risk-adjusted metrics, drawdown |
| Reporting | Auto-generated markdown/console research summary |

## Project layout

```
mtech-stock-analysis/
├── config.yaml              # tunable parameters
├── requirements.txt         # Python dependencies
├── main.py                  # entry point -> src/stocklab/cli.py
├── data/
│   ├── raw/                 # input CSVs (ticker_OHLCV.csv)
│   └── processed/           # cached indicator output
├── docs/
│   └── report.md            # M.Tech report / title page template
├── notebooks/
│   └── README.md
├── src/stocklab/
│   ├── config.py            # Config dataclass + YAML loader
│   ├── loader.py            # CSV / yfinance data ingestion
│   ├── indicators.py        # technical indicator library
│   ├── regime.py            # market-style classification
│   ├── signals.py           # regime-conditioned signal generation
│   ├── backtest.py          # vectorised back-test + metrics
│   ├── report.py            # human-readable summary output
│   └── cli.py               # command-line interface
└── tests/
    └── test_indicators.py
```

## Setup

```bash
cd mtech-stock-analysis
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

Analyse a CSV of daily OHLCV data (columns: `date,open,high,low,close,volume`):

```bash
python main.py --csv data/raw/RELIANCE.csv --out docs/RELIANCE_output
```

Or pull data directly with `yfinance` (requires internet):

```bash
python main.py --ticker AAPL --start 2018-01-01 --end 2024-12-31
```

Generate a synthetic series so the pipeline can be demonstrated offline:

```bash
python main.py --synthetic --out docs/demo_output
```

Run the tests:

```bash
python -m unittest discover -s tests
```

## Output

The command prints, and optionally writes to `<out>/summary.md`:

1. **Regime breakdown** – share of days spent in each market style.
2. **Signal statistics** – how often each strategy fired.
3. **Performance** – CAGR, annualised volatility, Sharpe, max drawdown,
   hit rate, and total trades for strategy vs. buy-and-hold.

## Methodology in one paragraph

Daily returns are computed from closing prices. Trend is measured as the
normalised spread between a fast and a slow moving average, confirmed by
MACD. Volatility is measured as the rolling std-dev of returns and converted
to a percentile rank within a trailing look-back window, so "high volatility"
is relative to that stock's own history rather than an absolute number. The
two axes are combined into a discrete market style. Each style maps to a
strategy family: momentum/breakout in trends, mean-reversion in quiet ranges,
and de-risking in high-volatility regimes. Positions are shifted by one bar to
avoid look-ahead bias, and transaction costs are charged on every change in
position.

## Disclaimer

This project is an academic exercise. It is **not financial advice** and must
not be used to trade real money.
