"""Streamlit web UI for the market-style analyser.

Run with:
    pip install -r requirements-ui.txt
    streamlit run app.py

The UI lets the user pick an NSE stock from the reference list, shows its
history profile (IPO/listing dates, extremes, long-run growth), and renders
the market-style analysis and equity curve.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from stocklab.backtest import run as run_backtest  # noqa: E402
from stocklab.company import (  # noqa: E402
    find_company,
    format_profile,
    history_summary,
    load_companies,
)
from stocklab.config import Config  # noqa: E402
from stocklab.indicators import add_indicators  # noqa: E402
from stocklab.loader import load_yfinance  # noqa: E402
from stocklab.regime import classify, regime_breakdown  # noqa: E402
from stocklab.signals import generate, signal_stats  # noqa: E402

st.set_page_config(page_title="Market-Style Analyser", page_icon="\U0001F4C8",
                   layout="wide")


@st.cache_data(show_spinner=False)
def fetch(symbol: str, start: str, end: str | None) -> pd.DataFrame:
    """Download price history (cached so re-runs are instant)."""
    return load_yfinance(symbol, start, end or "")


def render_profile(ticker: str, company, profile) -> None:
    st.subheader("Instrument history")
    st.markdown(format_profile(ticker, company, profile))


def main() -> None:
    st.title("\U0001F4C8 Market-Style Aware Stock Analyser")
    st.caption("M.Tech Data Science project \u2014 academic use only, not "
               "financial advice.")

    companies = load_companies()
    options = [f"{r['name']} ({r['symbol']})" for _, r in companies.iterrows()]

    with st.sidebar:
        st.header("Selection")
        choice = st.selectbox("Stock", options, index=options and 0)
        symbol = str(companies.iloc[options.index(choice)]["symbol"])
        start = st.text_input("History from", "2015-01-01")
        end = st.text_input("History to (blank = today)", "")
        cost = st.number_input("Cost per position change (bps)", 0.0, 100.0, 5.0)
        run = st.button("Analyse", type="primary")

    custom = st.sidebar.text_input("Or type any ticker", "")
    if custom.strip():
        symbol = custom.strip()
        st.sidebar.caption(f"Using custom ticker: {symbol}")

    if not run:
        st.info("Pick a stock in the sidebar and press **Analyse**.")
        return

    try:
        with st.spinner(f"Fetching {symbol} ..."):
            raw = fetch(symbol, start, end or None)
    except Exception as exc:  # noqa: BLE001 - surfaced to the user
        st.error(f"Could not fetch {symbol}: {exc}")
        return

    company = find_company(symbol, companies)
    profile = history_summary(raw, company)

    cfg = Config(start=start, end=end, cost_bps=float(cost))
    frame = generate(classify(add_indicators(raw, cfg), cfg), cfg)
    result = run_backtest(frame, cfg)
    metrics = result["metrics"]

    # --- Headline profile --------------------------------------------------- #
    render_profile(symbol, company, profile)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Current close", f"\u20b9{profile['last_close']:,.2f}",
              f"{100 * (profile['last_close'] / profile['first_close'] - 1):+.1f}% "
              "over available data")
    c2.metric("All-time high", f"\u20b9{profile['all_time_high']:,.2f}",
              str(pd.Timestamp(profile['all_time_high_date']).date()))
    c3.metric("52-week low", f"\u20b9{profile['low_52w']:,.2f}")
    years = profile.get("years_since_listing")
    c4.metric("Listed for", f"{years:.1f} years" if years else "n/a")
    st.divider()

    # --- Charts ------------------------------------------------------------- #
    left, right = st.columns([3, 2])

    with left:
        st.subheader("Price history")
        show = pd.DataFrame({"close": raw["close"]})
        st.line_chart(show, height=340)

        st.subheader("Equity curve")
        equity = result["equity"]
        st.line_chart(equity, height=300)

    with right:
        st.subheader("Market-style mix")
        mix = regime_breakdown(frame).rename("share").to_frame()
        st.bar_chart(mix, height=300)

        st.subheader("Signal activity")
        st.dataframe(signal_stats(frame), use_container_width=True)

        st.subheader("Performance")
        table = pd.DataFrame(metrics).T
        st.dataframe(table, use_container_width=True)

    st.divider()
    st.subheader("Latest readings")
    cols = ["close", "trend_state", "vol_state", "regime", "rsi",
            "macd_hist", "signal", "strategy"]
    st.dataframe(frame[cols].tail(15).iloc[::-1], use_container_width=True)

    with st.expander("Show processed data"):
        st.dataframe(frame.tail(200), use_container_width=True)


if __name__ == "__main__":
    main()
