"""Unit tests for the indicator and pipeline logic.

Run with the standard library so no extra test dependency is required:

    python -m unittest discover -s tests
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from stocklab.backtest import run as run_backtest  # noqa: E402
from stocklab.config import Config  # noqa: E402
from stocklab.indicators import add_indicators, rsi, sma  # noqa: E402
from stocklab.loader import _normalise, synthetic_ohlcv  # noqa: E402
from stocklab.regime import classify  # noqa: E402
from stocklab.signals import generate  # noqa: E402


class TestIndicators(unittest.TestCase):
    def test_sma_matches_manual_mean(self):
        s = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        out = sma(s, 3)
        self.assertTrue(np.isnan(out.iloc[1]))  # not enough history yet
        self.assertAlmostEqual(out.iloc[2], 2.0)
        self.assertAlmostEqual(out.iloc[4], 4.0)

    def test_rsi_bounds_and_direction(self):
        rising = pd.Series(np.linspace(10, 40, 60))
        falling = pd.Series(np.linspace(40, 10, 60))
        r_up = rsi(rising, 14).dropna()
        r_down = rsi(falling, 14).dropna()
        self.assertTrue(((r_up >= 0) & (r_up <= 100)).all())
        self.assertTrue(((r_down >= 0) & (r_down <= 100)).all())
        self.assertGreater(r_up.iloc[-1], 70)
        self.assertLess(r_down.iloc[-1], 30)


class TestLoader(unittest.TestCase):
    def test_normalise_requires_ohlcv(self):
        good = pd.DataFrame(
            {
                "date": pd.bdate_range("2020-01-01", periods=5),
                "open": 1.0, "high": 2.0, "low": 0.5, "close": 1.5, "volume": 100,
            }
        )
        frame = _normalise(good)
        self.assertEqual(list(frame.columns),
                         ["open", "high", "low", "close", "volume"])
        self.assertIsInstance(frame.index, pd.DatetimeIndex)

    def test_normalise_rejects_incomplete(self):
        bad = pd.DataFrame({"date": pd.bdate_range("2020-01-01", periods=3),
                            "close": [1, 2, 3]})
        with self.assertRaises(ValueError):
            _normalise(bad)

    def test_synthetic_has_expected_shape(self):
        frame = synthetic_ohlcv(days=300, seed=1)
        self.assertEqual(len(frame), 300)
        self.assertTrue((frame["high"] >= frame["close"]).all())
        self.assertTrue((frame["low"] <= frame["close"]).all())


class TestPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = Config()
        raw = synthetic_ohlcv(days=800, seed=42)
        cls.frame = generate(classify(add_indicators(raw, cls.cfg), cls.cfg), cls.cfg)

    def test_columns_present(self):
        for col in ("regime", "signal", "position", "strategy"):
            self.assertIn(col, self.frame.columns)

    def test_signals_are_valid(self):
        self.assertTrue(set(self.frame["signal"].unique()) <= {-1, 0, 1})

    def test_multiple_regimes_exist(self):
        self.assertGreater(self.frame["regime"].nunique(), 1)

    def test_position_scaled_in_high_vol(self):
        hi = self.frame[self.frame["vol_state"] == "high_vol"]["position"].abs()
        self.assertTrue((hi <= 0.5 + 1e-9).all())

    def test_backtest_shapes_and_finiteness(self):
        result = run_backtest(self.frame, self.cfg)
        equity = result["equity"]
        metrics = result["metrics"]["strategy"]
        self.assertEqual(len(equity), len(self.frame))
        self.assertTrue(np.isfinite(metrics["sharpe"]))
        self.assertLessEqual(metrics["max_drawdown"], 0.0)


class TestReturnOutlierGuard(unittest.TestCase):
    """The corporate-action artifact guard (Reliance 2005 demerger case)."""

    def _frame_with_jump(self, factor: float = 5.0) -> pd.DataFrame:
        frame = synthetic_ohlcv(days=300, seed=3)
        i = 150
        frame.iloc[i, frame.columns.get_loc("close")] *= factor
        return frame

    def test_outlier_is_flagged_and_masked(self):
        cfg = Config()
        out = add_indicators(self._frame_with_jump(), cfg)
        self.assertGreaterEqual(out.attrs.get("n_return_outliers", 0), 1)
        # No return above the threshold survives.
        self.assertLessEqual(float(out["returns"].abs().max()), cfg.max_abs_return)

    def test_outlier_inflates_vol_when_guard_disabled(self):
        frame = self._frame_with_jump()
        guarded = add_indicators(frame, Config(max_abs_return=0.50))
        unguarded = add_indicators(frame, Config(max_abs_return=0.0))
        self.assertEqual(unguarded.attrs["n_return_outliers"], 0)
        self.assertGreater(
            float(unguarded["vol"].max()), float(guarded["vol"].max())
        )

    def test_guard_is_disabled_by_zero(self):
        out = add_indicators(self._frame_with_jump(), Config(max_abs_return=0.0))
        self.assertEqual(out.attrs["n_return_outliers"], 0)


if __name__ == "__main__":
    unittest.main()
