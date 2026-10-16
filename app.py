"""Streamlit web UI for the market-style analyser.

Run with:
    pip install -r requirements-ui.txt
    streamlit run app.py

Layout
------
Sidebar   colourful header, quick picks, stock selector, date window, costs
Hero      gradient banner: company, symbol, price, current market-style badge
Cards     all-time high, 52-week range, CAGR, Sharpe (colour-coded)
Tabs      Overview | Market regimes | Performance | Data
"""
from __future__ import annotations

import sys
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from stocklab.backtest import run as run_backtest  # noqa: E402
from stocklab.company import (  # noqa: E402
    find_company,
    history_summary,
    load_companies,
)
from stocklab.config import Config  # noqa: E402
from stocklab.indicators import add_indicators  # noqa: E402
from stocklab.loader import load_yfinance  # noqa: E402
from stocklab.regime import classify, regime_breakdown  # noqa: E402
from stocklab.signals import generate, signal_stats  # noqa: E402

st.set_page_config(
    page_title="Market-Style Analyser",
    page_icon="\U0001F4C8",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --------------------------------------------------------------------------- #
# Palette
# --------------------------------------------------------------------------- #
VIOLET = "#6C5CE7"
BLUE = "#0984E3"
TEAL = "#00B894"
AMBER = "#F39C12"
CORAL = "#E17055"
RED = "#E74C3C"
GREY = "#6B7280"

REGIME_COLORS = {
    "up_low_vol": "#00B894",
    "up_high_vol": "#3F9142",
    "down_low_vol": "#E74C3C",
    "down_high_vol": "#8C1D18",
    "sideways_low_vol": "#0984E3",
    "sideways_high_vol": "#F39C12",
}

QUICK_PICKS = [
    ("Reliance", "RELIANCE.NS"),
    ("TCS", "TCS.NS"),
    ("Infosys", "INFY.NS"),
    ("HDFC Bank", "HDFCBANK.NS"),
    ("Eternal", "ETERNAL.NS"),
    ("IRCTC", "IRCTC.NS"),
]

METRIC_ROWS = [
    ("Total return", "total_return", "{:+.2%}"),
    ("CAGR", "cagr", "{:+.2%}"),
    ("Annualised volatility", "ann_vol", "{:.2%}"),
    ("Sharpe ratio", "sharpe", "{:,.2f}"),
    ("Sortino ratio", "sortino", "{:,.2f}"),
    ("Max drawdown", "max_drawdown", "{:.2%}"),
    ("Hit rate (active days)", "hit_rate", "{:.2%}"),
    ("Trades", "trades", "{:,.0f}"),
]

# --------------------------------------------------------------------------- #
# Styling
# --------------------------------------------------------------------------- #
CSS = """
<style>
.block-container {padding-top: 1.4rem; padding-bottom: 2rem; max-width: 1450px;}

/* ---------- hero ---------- */
.hero {
  position: relative; overflow: hidden;
  padding: 1.35rem 1.6rem; border-radius: 18px; margin-bottom: 1.15rem;
  background: linear-gradient(120deg,#5B3FD9 0%,#6C5CE7 35%,#0984E3 70%,#00B894 100%);
  box-shadow: 0 10px 30px rgba(108,92,231,.28); color: #fff;
}
.hero:before {
  content:""; position:absolute; right:-60px; top:-70px; width:260px; height:260px;
  background: radial-gradient(circle, rgba(255,255,255,.28) 0%, rgba(255,255,255,0) 70%);
}
.hero h1 {margin:0; font-size:1.62rem; font-weight:800; color:#fff; letter-spacing:.2px;}
.hero .sub {margin:.35rem 0 0 0; opacity:.94; font-size:.94rem;}
.hero .price {font-size:2.05rem; font-weight:800; margin:.5rem 0 0 0;}
.hero .chg {font-size:.94rem; opacity:.96; font-weight:600;}
.hero .up {color:#C8FFE8;} .hero .down {color:#FFD3CC;}

.badge {
  display:inline-block; padding:.2rem .68rem; border-radius:999px;
  background:rgba(255,255,255,.22); border:1px solid rgba(255,255,255,.38);
  font-size:.79rem; font-weight:600; margin:.55rem .4rem 0 0;
}

/* ---------- stat cards ---------- */
.card {
  border-radius:14px; padding:.9rem 1.05rem; height:100%;
  background:#fff; border:1px solid rgba(108,92,231,.16);
  box-shadow:0 3px 12px rgba(17,24,39,.06);
}
.card .k {font-size:.74rem; text-transform:uppercase; letter-spacing:.7px;
          color:#6B7280; font-weight:700;}
.card .v {font-size:1.45rem; font-weight:800; margin-top:.2rem; color:#1F2937;}
.card .d {font-size:.78rem; color:#6B7280; margin-top:.15rem;}
.card.pos {border-top:4px solid #00B894;}
.card.neg {border-top:4px solid #E74C3C;}
.card.neu {border-top:4px solid #6C5CE7;}
.card.pos .v {color:#0E8F6E;} .card.neg .v {color:#C0392B;}

/* ---------- tables / chips ---------- */
.kv {width:100%; border-collapse:collapse; font-size:.92rem;}
.kv td {padding:.42rem .2rem; border-bottom:1px solid rgba(17,24,39,.07);}
.kv td:first-child {color:#6B7280;}
.kv td:last-child {text-align:right; font-weight:600; font-variant-numeric:tabular-nums;}

.chip {
  display:inline-block; padding:.22rem .68rem; border-radius:8px;
  font-family:ui-monospace,Menlo,monospace; font-size:.83rem; font-weight:700;
}

.landing {padding:2.2rem 1rem 1rem 1rem; text-align:center;}
.landing h2 {margin-bottom:.4rem; color:#5B3FD9;}
.landing p {color:#6B7280; max-width:640px; margin:0 auto;}

.tile {
  border-radius:14px; padding:1rem 1.1rem; height:100%;
  background:linear-gradient(160deg,#F5F3FF 0%,#FFFFFF 100%);
  border:1px solid rgba(108,92,231,.18);
}
.tile .t {font-weight:800; color:#5B3FD9; margin-bottom:.25rem;}
.tile .d {font-size:.86rem; color:#6B7280; line-height:1.45;}
.foot {font-size:.8rem; color:#9CA3AF; text-align:center; padding-top:1rem;}
</style>
"""


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


# --------------------------------------------------------------------------- #
# Formatting helpers
# --------------------------------------------------------------------------- #
def inr(value: float) -> str:
    return f"\u20b9{value:,.2f}"


def _date(value) -> str:
    ts = pd.to_datetime(value, errors="coerce")
    return "\u2014" if pd.isna(ts) else ts.date().isoformat()


def regime_color(regime: str) -> str:
    return REGIME_COLORS.get(str(regime), GREY)


def chip(regime: str) -> str:
    c = regime_color(regime)
    return (f'<span class="chip" style="background:{c}20;color:{c};'
            f'border:1px solid {c}55">{regime}</span>')


def hero(title: str, subtitle: str, badges: list[str],
         price: float | None = None, change: float | None = None) -> None:
    chips = "".join(f'<span class="badge">{b}</span>' for b in badges)
    body = ""
    if price is not None:
        cls = "up" if (change or 0) >= 0 else "down"
        arrow = "\u25b2" if (change or 0) >= 0 else "\u25bc"
        chg = (f'<div class="chg {cls}">{arrow} {change:+.1f}% over available '
               f"data</div>") if change is not None else ""
        body = f'<div class="price">{inr(price)}</div>{chg}'
    st.markdown(
        f'<div class="hero"><h1>{title}</h1><div class="sub">{subtitle}</div>'
        f"{chips}{body}</div>",
        unsafe_allow_html=True,
    )


def stat_cards(items: list[tuple[str, str, str, str]]) -> None:
    """items: (label, value, detail, tone) where tone in pos/neg/neu."""
    cols = st.columns(len(items))
    for col, (label, value, detail, tone) in zip(cols, items):
        with col:
            st.markdown(
                f'<div class="card {tone}"><div class="k">{label}</div>'
                f'<div class="v">{value}</div><div class="d">{detail}</div></div>',
                unsafe_allow_html=True,
            )


def tone_of(value: float) -> str:
    return "pos" if value > 0 else ("neg" if value < 0 else "neu")


def kv_table(rows: list[tuple[str, str]]) -> str:
    body = "".join(
        f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in rows
    )
    return f'<table class="kv">{body}</table>'


# --------------------------------------------------------------------------- #
# Data
# --------------------------------------------------------------------------- #
@st.cache_data(show_spinner=False)
def fetch(symbol: str, start: str, end: str | None) -> pd.DataFrame:
    return load_yfinance(symbol, start, end or "")


@st.cache_data(show_spinner=False)
def company_list() -> pd.DataFrame:
    return load_companies()


def run_pipeline(raw: pd.DataFrame, cfg: Config):
    frame = generate(classify(add_indicators(raw, cfg), cfg), cfg)
    return frame, run_backtest(frame, cfg)


# --------------------------------------------------------------------------- #
# Charts
# --------------------------------------------------------------------------- #
def price_chart(raw: pd.DataFrame, frame: pd.DataFrame):
    data = pd.DataFrame({
        "date": raw.index,
        "Close": raw["close"].to_numpy(),
        "50-day MA": frame["sma_slow"].to_numpy(),
    }).melt("date", var_name="series", value_name="price")

    return (
        alt.Chart(data)
        .mark_line(strokeWidth=1.8)
        .encode(
            x=alt.X("date:T", title=None),
            y=alt.Y("price:Q", title="Price (\u20b9)", scale=alt.Scale(zero=False)),
            color=alt.Color(
                "series:N",
                scale=alt.Scale(domain=["Close", "50-day MA"],
                                range=[BLUE, AMBER]),
                legend=alt.Legend(title=None, orient="top"),
            ),
            tooltip=["date:T", "series:N", alt.Tooltip("price:Q", format=",.2f")],
        )
        .properties(height=290)
    )


def regime_timeline(frame: pd.DataFrame):
    data = pd.DataFrame({
        "date": frame.index,
        "regime": frame["regime"].to_numpy(),
        "row": 1,
    })
    return (
        alt.Chart(data)
        .mark_rect()
        .encode(
            x=alt.X("date:T", title=None),
            y=alt.Y("row:O", axis=None),
            color=alt.Color(
                "regime:N",
                scale=alt.Scale(domain=list(REGIME_COLORS),
                                range=list(REGIME_COLORS.values())),
                legend=alt.Legend(title="Market style", orient="bottom",
                                  columns=3, symbolLimit=10),
            ),
            tooltip=["date:T", "regime:N"],
        )
        .properties(height=78)
    )


def regime_bar(frame: pd.DataFrame):
    mix = regime_breakdown(frame).rename("share").reset_index()
    mix.columns = ["regime", "share"]
    return (
        alt.Chart(mix)
        .mark_bar(cornerRadiusTopRight=5, cornerRadiusBottomRight=5)
        .encode(
            y=alt.Y("regime:N", sort="-x", title=None),
            x=alt.X("share:Q", title="Share of days",
                    axis=alt.Axis(format="%")),
            color=alt.Color(
                "regime:N",
                scale=alt.Scale(domain=list(REGIME_COLORS),
                                range=list(REGIME_COLORS.values())),
                legend=None,
            ),
            tooltip=["regime:N", alt.Tooltip("share:Q", format=".1%")],
        )
        .properties(height=225)
    )


def equity_chart(result) -> None:
    eq = result["equity"].copy()
    eq.columns = ["Regime strategy", "Buy & hold"]
    st.line_chart(eq, height=300, color=[VIOLET, CORAL], width="stretch")


def drawdown_chart(result) -> None:
    eq = result["equity"]
    dd = pd.DataFrame({
        "Regime strategy": eq["strategy"] / eq["strategy"].cummax() - 1.0,
        "Buy & hold": eq["buy_hold"] / eq["buy_hold"].cummax() - 1.0,
    })
    st.line_chart(dd, height=230, color=[RED, GREY], width="stretch")


def metrics_dataframe(metrics: dict) -> pd.DataFrame:
    s, b = metrics.get("strategy", {}), metrics.get("buy_hold", {})
    rows = []
    for label, key, fmt in METRIC_ROWS:
        rows.append({
            "Metric": label,
            "Strategy": fmt.format(s.get(key, 0.0)),
            "Buy & hold": fmt.format(b.get(key, 0.0)),
        })
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- #
# Sidebar
# --------------------------------------------------------------------------- #
def sidebar(companies: pd.DataFrame):
    labels = [f"{r['name']} ({r['symbol']})" for _, r in companies.iterrows()]
    symbols = [str(r["symbol"]) for _, r in companies.iterrows()]

    with st.sidebar:
        st.markdown(
            f'<div style="background:linear-gradient(120deg,{VIOLET},{BLUE});'
            'padding:.85rem 1rem;border-radius:14px;color:#fff;margin-bottom:.9rem">'
            '<div style="font-size:1.05rem;font-weight:800">\U0001F4C8 Market-Style '
            'Analyser</div>'
            '<div style="font-size:.78rem;opacity:.9">M.Tech Data Science '
            "\u00b7 NSE equities</div></div>",
            unsafe_allow_html=True,
        )

        st.markdown("**Quick picks**")
        qcols = st.columns(3)
        for i, (label, sym) in enumerate(QUICK_PICKS):
            if qcols[i % 3].button(label, key=f"qp_{sym}", width="stretch"):
                st.session_state["_pending"] = sym
                st.rerun()

        if st.session_state.get("_pending") in symbols:
            st.session_state["stock_select"] = labels[
                symbols.index(st.session_state.pop("_pending"))
            ]

        choice = st.selectbox("Select a stock", labels, key="stock_select")
        symbol = symbols[labels.index(choice)]

        custom = st.text_input("\u2026or type any ticker", "",
                               placeholder="e.g. INFY.NS")
        if custom.strip():
            symbol = custom.strip()

        with st.expander("Advanced settings", expanded=False):
            start = st.text_input("History from", "2015-01-01")
            end = st.text_input("To (blank = today)", "")
            cost = st.number_input("Cost per position change (bps)",
                                   0.0, 100.0, 5.0, step=1.0)

        run = st.button("\u25b6  Analyse", type="primary", width="stretch")
        st.caption("Long-only signals (long / hold / exit) \u2014 SEBI does not "
                   "permit retail short-selling for delivery. Not financial advice.")
    return symbol, start, end, float(cost), run


# --------------------------------------------------------------------------- #
# Tabs
# --------------------------------------------------------------------------- #
def overview_tab(raw, frame, result, profile) -> None:
    left, right = st.columns([3, 2], gap="large")

    with left:
        st.markdown("##### Price history")
        st.altair_chart(price_chart(raw, frame), width="stretch")
        st.markdown("##### Market style over time")
        st.altair_chart(regime_timeline(frame), width="stretch")
        st.markdown("##### Equity curve \u2014 strategy vs buy & hold")
        equity_chart(result)

    with right:
        st.markdown("##### Instrument history")
        rows = [
            ("IPO date", _date(profile.get("ipo_date"))),
            ("Listing date", _date(profile.get("listing_date"))),
            ("Issue price", inr(profile["issue_price"])
             if profile.get("issue_price") else "\u2014"),
            ("Data available", f"{_date(profile['first_data_date'])} \u2192 "
                               f"{_date(profile['last_data_date'])}"),
            ("Trading days", f"{int(profile['trading_days']):,} "
                             f"({float(profile['years_of_data']):.1f} yrs)"),
            ("All-time high", f"{inr(profile['all_time_high'])} "
                              f"{_date(profile['all_time_high_date'])}"),
            ("All-time low", f"{inr(profile['all_time_low'])} "
                             f"{_date(profile['all_time_low_date'])}"),
            ("52-week range", f"{inr(profile['low_52w'])} \u2013 "
                              f"{inr(profile['high_52w'])}"),
            ("Return over data", f"{profile['return_since_data']:+.1%}"),
        ]
        if profile.get("cagr_since_data") is not None:
            rows.append(("CAGR over data",
                         f"{profile['cagr_since_data']:+.2%}"))
        if profile.get("growth_from_issue_price") is not None:
            rows.append(("Growth from issue price",
                         f"{profile['growth_from_issue_price']:+.1%}"))
        if profile.get("years_since_listing"):
            rows.append(("Listed for",
                         f"{profile['years_since_listing']:.1f} years"))
        st.markdown(kv_table(rows), unsafe_allow_html=True)

        st.markdown("##### Market-style mix")
        st.altair_chart(regime_bar(frame), width="stretch")


def regimes_tab(frame) -> None:
    st.markdown("##### Market-style breakdown")
    st.caption("Trend \u00d7 volatility. Volatility is a percentile of the "
               "stock's own realised volatility, so 'high' is stock-relative.")
    mix = regime_breakdown(frame).rename("share").reset_index()
    mix.columns = ["regime", "share"]
    rows = [(chip(r), f"{s:.1%}") for r, s in
            zip(mix["regime"], mix["share"])]
    st.markdown(kv_table(rows), unsafe_allow_html=True)

    st.markdown("##### Signal activity")
    stats = signal_stats(frame)
    stats.index.name = "Strategy"
    st.dataframe(
        stats.style.format({"days": "{:,.0f}", "share": "{:.2%}"}),
        width="stretch",
    )

    st.markdown("##### Latest readings")
    cols = ["close", "trend_state", "vol_state", "regime", "rsi",
            "macd_hist", "signal", "strategy"]
    latest = frame[cols].tail(15).iloc[::-1].copy()
    latest["close"] = latest["close"].map(inr)
    st.dataframe(latest, width="stretch")


def performance_tab(result) -> None:
    st.markdown("##### Performance vs. buy & hold")
    st.caption("One-bar-lagged positions; costs charged on every position "
               "change. The verdict below is generated from these numbers.")
    st.dataframe(metrics_dataframe(result["metrics"]), hide_index=True,
                 width="stretch")

    s, b = result["metrics"]["strategy"], result["metrics"]["buy_hold"]
    exposure = float((result["daily"]["position_applied"] != 0).mean())
    better = ("The regime strategy" if s["sharpe"] > b["sharpe"]
              else "Buy & hold")
    st.info(
        f"**{better}** delivered the better risk-adjusted return on this "
        f"sample (Sharpe {s['sharpe']:.2f} vs {b['sharpe']:.2f}). "
        f"The strategy was invested on {exposure:.0%} of days, traded "
        f"{s['trades']:,.0f} times, and ran at {s['ann_vol']:.1%} volatility "
        f"against {b['ann_vol']:.1%} for buy & hold."
    )

    st.markdown("##### Return, risk and reward-for-risk")
    stat_cards([
        ("Total return", f"{s['total_return']:+.2%}",
         f"buy & hold {b['total_return']:+.2%}",
         tone_of(s["total_return"] - b["total_return"])),
        ("Volatility", f"{s['ann_vol']:.2%}",
         f"buy & hold {b['ann_vol']:.2%}",
         tone_of(b["ann_vol"] - s["ann_vol"])),
        ("Sharpe", f"{s['sharpe']:,.2f}",
         f"buy & hold {b['sharpe']:,.2f}",
         tone_of(s["sharpe"] - b["sharpe"])),
        ("Max drawdown", f"{s['max_drawdown']:.2%}",
         f"buy & hold {b['max_drawdown']:.2%}",
         tone_of(s["max_drawdown"] - b["max_drawdown"])),
    ])

    st.markdown("##### Drawdown")
    drawdown_chart(result)


def data_tab(frame) -> None:
    st.markdown("##### Processed data")
    st.caption(f"{len(frame):,} rows \u00d7 {len(frame.columns)} columns \u2014 "
               "indicators, regimes, signals and strategy labels per day.")
    st.dataframe(frame.tail(300), width="stretch")
    st.download_button("\u2b07 Download full processed CSV",
                       frame.to_csv().encode("utf-8"),
                       file_name="processed.csv", mime="text/csv",
                       type="primary")


def landing(companies: pd.DataFrame) -> None:
    st.markdown(
        '<div class="landing"><h2>Pick a stock to begin</h2>'
        f"<p>{len(companies)} NSE companies are loaded. Choose one in the "
        "sidebar \u2014 or use a quick pick \u2014 then press "
        "<b>Analyse</b>.</p></div>",
        unsafe_allow_html=True,
    )
    tiles = [
        ("\U0001F4C5 History profile",
         "IPO and listing dates, issue price, all-time high and low, 52-week "
         "range and long-run CAGR for the instrument."),
        ("\U0001F9ED Market style",
         "Every day labelled trending up/down/sideways crossed with high or "
         "low volatility, relative to the stock's own history."),
        ("\U0001F3AF Strategy performance",
         "The regime-aware strategy against buy-and-hold: volatility, Sharpe, "
         "drawdown and trade count, with costs included."),
    ]
    for col, (title, body) in zip(st.columns(3), tiles):
        with col:
            st.markdown(f'<div class="tile"><div class="t">{title}</div>'
                        f'<div class="d">{body}</div></div>',
                        unsafe_allow_html=True)


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main() -> None:
    inject_css()
    companies = company_list()
    symbol, start, end, cost, run = sidebar(companies)

    if not run:
        hero("Market-Style Aware Stock Analyser",
             "Detect a stock's market style and generate regime-aware signals",
             ["Rule-based", "NSE equities", "Long-only", "M.Tech project"])
        landing(companies)
        st.markdown('<div class="foot">Academic exercise only \u2014 not '
                    "financial advice.</div>", unsafe_allow_html=True)
        return

    try:
        with st.spinner(f"Fetching {symbol} \u2026"):
            raw = fetch(symbol, start, end or None)
    except Exception as exc:  # noqa: BLE001 - surfaced to the user
        st.error(f"Could not fetch **{symbol}**: {exc}")
        st.info("Check the ticker, or try `RELIANCE.NS`. A blank end date "
                "means 'up to today'.")
        return

    company = find_company(symbol, companies)
    cfg = Config(start=start, end=end, cost_bps=cost)

    try:
        frame, result = run_pipeline(raw, cfg)
        profile = history_summary(raw, company)
    except ValueError as exc:
        st.error(f"Could not analyse {symbol}: {exc}")
        return

    name = str(company.get("name")) if company else symbol
    sector = str(company.get("sector")) if company else "unlisted in reference"
    latest = frame["regime"].iloc[-1]
    change = profile["last_close"] / profile["first_close"] - 1.0

    hero(
        name,
        f"{symbol} \u00b7 {sector} \u00b7 {len(frame):,} trading days "
        f"({frame.index[0].date()} \u2192 {frame.index[-1].date()})",
        [f"Current market style: {latest}"],
        price=profile["last_close"],
        change=100.0 * change,
    )

    m = result["metrics"]
    stat_cards([
        ("All-time high", inr(profile["all_time_high"]),
         _date(profile["all_time_high_date"]), "neu"),
        ("52-week range", f"{inr(profile['low_52w'])} \u2013 "
                          f"{inr(profile['high_52w'])}", "trailing 252 days",
         "neu"),
        ("CAGR over data",
         f"{profile['cagr_since_data']:+.2%}"
         if profile.get("cagr_since_data") is not None else "\u2014",
         f"{float(profile['years_of_data']):.1f} years",
         tone_of(profile.get("cagr_since_data") or 0.0)),
        ("Strategy Sharpe", f"{m['strategy']['sharpe']:,.2f}",
         f"buy & hold {m['buy_hold']['sharpe']:,.2f}",
         tone_of(m["strategy"]["sharpe"])),
    ])

    st.write("")
    tabs = st.tabs(["\U0001F4C9  Overview", "\U0001F9ED  Market regimes",
                    "\U0001F3AF  Strategy & performance", "\U0001F5C3  Data"])
    with tabs[0]:
        overview_tab(raw, frame, result, profile)
    with tabs[1]:
        regimes_tab(frame)
    with tabs[2]:
        performance_tab(result)
    with tabs[3]:
        data_tab(frame)


if __name__ == "__main__":
    main()
