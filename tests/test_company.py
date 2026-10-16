"""Tests for the company reference data and history profiling."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from stocklab.company import (  # noqa: E402
    find_company,
    format_profile,
    history_summary,
    load_companies,
    resolve_symbol,
)
from stocklab.loader import synthetic_ohlcv  # noqa: E402


class TestReferenceData(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.df = load_companies()

    def test_reference_loads(self):
        self.assertGreater(len(self.df), 10)
        for col in ("symbol", "name", "sector"):
            self.assertIn(col, self.df.columns)

    def test_symbols_are_unique(self):
        self.assertEqual(len(self.df), self.df["symbol"].nunique())

    def test_date_columns_are_datetime(self):
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(self.df["ipo_date"]))
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(self.df["listing_date"]))

    def test_find_company_accepts_bare_and_suffixed(self):
        for query in ("RELIANCE", "RELIANCE.NS", "reliance.ns"):
            rec = find_company(query, self.df)
            self.assertIsNotNone(rec, query)
            self.assertEqual(rec["symbol"], "RELIANCE.NS")

    def test_find_company_rejects_unknown(self):
        self.assertIsNone(find_company("NOTAREALTICKER", self.df))

    def test_resolve_symbol(self):
        # "zomato" is a legacy name; it should still resolve to the new symbol.
        self.assertEqual(resolve_symbol("zomato", self.df), "ETERNAL.NS")
        self.assertEqual(resolve_symbol("ETERNAL", self.df), "ETERNAL.NS")
        self.assertEqual(resolve_symbol("TMPV", self.df), "TMPV.NS")

    def test_renamed_symbols_are_present(self):
        symbols = set(self.df["symbol"])
        self.assertIn("ETERNAL.NS", symbols)   # was ZOMATO.NS
        self.assertIn("TMPV.NS", symbols)      # was TATAMOTORS.NS
        self.assertNotIn("ZOMATO.NS", symbols)
        self.assertNotIn("TATAMOTORS.NS", symbols)

    def test_recent_ipos_have_dates(self):
        # The whole point of the feature: recent listings must carry dates.
        for sym in ("ETERNAL.NS", "PAYTM.NS", "LICI.NS"):
            rec = find_company(sym, self.df)
            self.assertIsNotNone(rec, sym)
            self.assertIsNotNone(rec["ipo_date"], f"{sym} has no IPO date")
            self.assertIsNotNone(rec["listing_date"], f"{sym} has no listing date")


class TestHistorySummary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.frame = synthetic_ohlcv(days=800, seed=14)

    def test_summary_keys(self):
        prof = history_summary(self.frame)
        for key in ("first_data_date", "last_data_date", "trading_days",
                    "all_time_high", "high_52w", "return_since_data",
                    "years_of_data"):
            self.assertIn(key, prof)
        self.assertEqual(prof["trading_days"], 800)

    def test_extremes_bracket_price(self):
        prof = history_summary(self.frame)
        self.assertGreaterEqual(prof["all_time_high"], prof["last_close"])
        self.assertLessEqual(prof["all_time_low"], prof["last_close"])

    def test_profile_with_company_dates(self):
        company = find_company("ETERNAL.NS")
        prof = history_summary(self.frame, company)
        self.assertIsNotNone(prof["ipo_date"])
        self.assertIsNotNone(prof["years_since_listing"])
        self.assertIsNotNone(prof["growth_from_issue_price"])

    def test_short_history_does_not_raise(self):
        short = self.frame.tail(5)
        prof = history_summary(short)
        self.assertEqual(prof["trading_days"], 5)
        self.assertIsNone(prof["cagr_since_data"])  # under a year of data

    def test_empty_history_raises(self):
        with self.assertRaises(ValueError):
            history_summary(self.frame.iloc[0:0])

    def test_format_profile_renders_text(self):
        company = find_company("RELIANCE.NS")
        text = format_profile("RELIANCE.NS", company, history_summary(self.frame, company))
        self.assertIn("RELIANCE.NS", text)
        self.assertIn("All-time high", text)


if __name__ == "__main__":
    unittest.main()
