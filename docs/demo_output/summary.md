# Market-Style Analysis — SYNTHETIC

- **Period:** 2019-01-01 to 2024-09-30 (1,500 trading days)
- **Dominant market style:** `sideways_low_vol`
- **Trend threshold:** 0.005 (fast MA 20 vs slow MA 50)
- **High-volatility cutoff:** 70% percentile of 20-day realised volatility
- **Round-trip cost:** 5.0 bps per position change

## 1. Market-style breakdown

| Market style | Share of days |
|---|---:|
| `sideways_low_vol` | 40.40% |
| `sideways_high_vol` | 21.27% |
| `up_low_vol` | 15.27% |
| `down_low_vol` | 11.93% |
| `down_high_vol` | 5.80% |
| `up_high_vol` | 5.33% |

## 2. Signal activity

| Strategy | Days | Share |
|---|---:|---:|
| flat | 917 | 61.13% |
| momentum_long | 309 | 20.60% |
| momentum_short | 266 | 17.73% |
| mean_reversion_long | 4 | 0.27% |
| mean_reversion_short | 4 | 0.27% |

## 3. Performance vs. buy & hold

| Metric | Strategy | Buy & hold |
|---|---:|---:|
| Total return | 14.51% | 27.62% |
| CAGR | 2.30% | 4.18% |
| Annualised volatility | 10.05% | 18.50% |
| Sharpe ratio | 0.28 | 0.31 |
| Sortino ratio | 0.27 | 0.53 |
| Max drawdown | -23.41% | -46.30% |
| Hit rate (active days) | 45.31% | 48.70% |
| Trades | 171 | 1,499 |

## 4. Interpretation

- Buy-and-hold beat the strategy on raw return this time: 27.62% versus 14.51%.
- Risk was reduced: annualised volatility fell from 18.50% to 10.05%, and the worst drawdown from -46.30% to -23.41% — the main benefit of switching strategy by regime.
- Buy-and-hold had the better risk-adjusted return (Sharpe 0.31 vs 0.28); on this sample the regime rules did not add value.
- 171 trades were triggered, each charged 5.0 bps, so turnover cost is already reflected above.
- High-volatility days halve the position size, trading some upside for lower drawdown and lower turnover cost.

> **Disclaimer:** academic exercise only — not financial advice.