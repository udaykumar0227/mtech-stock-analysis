# Notebooks

This folder is for exploratory analysis and figures used in the dissertation.

Suggested notebooks:

1. `01_exploration.ipynb` — load a ticker, plot price/volume, inspect returns
   distribution, volatility and missing-data patterns.
2. `02_features.ipynb` — visualise each indicator and sanity-check values.
3. `03_regimes.ipynb` — colour the price series by detected market style and
   inspect regime durations and transitions.
4. `04_backtest.ipynb` — equity curves, drawdown curve, and a sensitivity
   sweep over `trend_threshold` and `vol_high_pct`.

## Getting started

Make the package importable from a notebook with:

```python
import sys, pathlib
sys.path.insert(0, str(pathlib.Path.cwd().parent / "src"))

from stocklab.config import Config
from stocklab.loader import synthetic_ohlcv, load_csv
from stocklab.indicators import add_indicators
from stocklab.regime import classify, regime_breakdown
from stocklab.signals import generate
from stocklab.backtest import run
```

## Housekeeping

- Keep notebooks **output-free** before committing (clear outputs) to keep the
  repository small.
- Anything reusable should move into `src/stocklab/` — notebooks are for
  exploration and reporting, not production logic.
