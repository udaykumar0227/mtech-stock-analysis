"""Company reference data and instrument-history profiling.

Two responsibilities:

1. **Reference lookup** - map a user's selection (symbol like ``RELIANCE`` or
   ``RELIANCE.NS``, or a company name) to a canonical entry in
   ``data/reference/nse_companies.csv``.
2. **History profile** - summarise a price history: first/last data date,
   all-time and 52-week extremes, listing age and long-run growth.

IMPORTANT - data provenance
---------------------------
Free market APIs (yfinance and friends) **do not provide IPO or listing
dates**. The earliest row they return is simply where the exchange feed
begins, which is usually *after* the real listing. The reference CSV is
therefore a hand-maintained file, and its dates are **indicative, not
authoritative**. Blank dates mean "not established in this file". Always
verify against the company's prospectus / NSE / BSE / SEBI filings before
citing an IPO date in the dissertation.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
COMPANIES_CSV = PROJECT_ROOT / "data" / "reference" / "nse_companies.csv"

REFERENCE_COLUMNS = [
    "symbol", "name", "sector", "exchange",
    "ipo_date", "listing_date", "issue_price", "notes",
]


# --------------------------------------------------------------------------- #
# Reference data
# --------------------------------------------------------------------------- #
def load_companies(path: str | Path | None = None) -> pd.DataFrame:
    """Load the hand-maintained company reference table."""
    p = Path(path) if path is not None else COMPANIES_CSV
    if not p.exists():
        raise FileNotFoundError(f"Reference file not found: {p}")

    df = pd.read_csv(p, dtype=str).fillna("")
    df.columns = [c.strip().lower() for c in df.columns]
    for col in REFERENCE_COLUMNS:
        if col not in df.columns:
            df[col] = ""

    df["ipo_date"] = pd.to_datetime(df["ipo_date"], errors="coerce")
    df["listing_date"] = pd.to_datetime(df["listing_date"], errors="coerce")
    df["issue_price"] = pd.to_numeric(df["issue_price"], errors="coerce")
    return df[REFERENCE_COLUMNS]


def _normalise_symbol(value: str) -> str:
    """Strip exchange suffixes so RELIANCE, RELIANCE.NS and RELIANCE.BO match."""
    return str(value).strip().upper().replace(".NS", "").replace(".BO", "")


def find_company(
    query: str, companies: Optional[pd.DataFrame] = None
) -> Optional[Dict[str, object]]:
    """Resolve a symbol or company name to a reference record.

    Returns ``None`` when there is no match, so callers can still analyse an
    unknown ticker - the profile section is simply omitted.
    """
    df = load_companies() if companies is None else companies
    if df.empty or not str(query).strip():
        return None

    wanted = _normalise_symbol(query)
    if wanted in set(df["symbol"].map(_normalise_symbol)):
        hit = df[df["symbol"].map(_normalise_symbol) == wanted]
    else:
        needle = str(query).strip().upper()
        names = df["name"].str.upper()
        mask = names.str.contains(needle, regex=False, na=False)
        # Fall back to a space-insensitive match so legacy spellings such as
        # "TATAMOTORS" still find "Tata Motors Passenger Vehicles ...".
        if not mask.any() and wanted:
            squashed = names.str.replace(" ", "", regex=False)
            mask = squashed.str.contains(
                wanted.replace(" ", ""), regex=False, na=False
            )
        hit = df[mask]

    if hit.empty:
        return None
    return dict(hit.iloc[0].to_dict())


def resolve_symbol(query: str, companies: Optional[pd.DataFrame] = None) -> Optional[str]:
    """Return the canonical symbol for a free-text query (or ``None``)."""
    record = find_company(query, companies)
    return str(record["symbol"]) if record else None


# --------------------------------------------------------------------------- #
# History profiling
# --------------------------------------------------------------------------- #
def _as_date(value: object) -> Optional[pd.Timestamp]:
    """Return a Timestamp for a real date, or None for blanks/NaT."""
    if value is None:
        return None
    if isinstance(value, str) and not value.strip():
        return None
    try:
        if pd.isna(value):  # type: ignore[arg-type]
            return None
    except (TypeError, ValueError):
        return None
    ts = pd.Timestamp(value)
    return None if pd.isna(ts) else ts


def history_summary(
    frame: pd.DataFrame,
    company: Optional[Dict[str, object]] = None,
    trading_days: int = 252,
) -> Dict[str, object]:
    """Summarise a price history into a profile dictionary.

    Degrades gracefully: a stock with only a few months of data (a recent
    IPO) still produces a profile, with the long-run fields left as ``None``.
    """
    if frame is None or frame.empty:
        raise ValueError("Cannot profile an empty price history")
    close = frame["close"].dropna()
    if len(close) < 2:
        raise ValueError("Need at least two prices to build a history profile")

    first_d, last_d = close.index[0], close.index[-1]
    last_price, first_price = float(close.iloc[-1]), float(close.iloc[0])

    out: Dict[str, object] = {
        "first_data_date": first_d,
        "last_data_date": last_d,
        "trading_days": int(len(close)),
        "first_close": first_price,
        "last_close": last_price,
        "all_time_high": float(close.max()),
        "all_time_high_date": close.idxmax(),
        "all_time_low": float(close.min()),
        "all_time_low_date": close.idxmin(),
    }

    window = close.tail(int(trading_days))
    out["high_52w"] = float(window.max())
    out["high_52w_date"] = window.idxmax()
    out["low_52w"] = float(window.min())
    out["low_52w_date"] = window.idxmin()

    years_of_data = max((last_d - first_d).days / 365.25, 0.0)
    out["years_of_data"] = years_of_data
    out["return_since_data"] = last_price / first_price - 1.0
    out["cagr_since_data"] = (
        (last_price / first_price) ** (1.0 / years_of_data) - 1.0
        if years_of_data >= 1.0 else None
    )

    company = company or {}
    ipo = _as_date(company.get("ipo_date"))
    listing = _as_date(company.get("listing_date"))
    issue = company.get("issue_price")
    issue = None if issue is None or pd.isna(issue) else float(issue)  # type: ignore[arg-type]

    out["ipo_date"] = ipo
    out["listing_date"] = listing
    out["issue_price"] = issue
    out["years_since_listing"] = (
        (last_d - listing).days / 365.25 if listing is not None else None
    )
    out["months_since_listing"] = (
        (last_d - listing).days / 30.44 if listing is not None else None
    )
    # Indicative only: ignores splits, bonus issues and dividends.
    out["growth_from_issue_price"] = (
        last_price / issue - 1.0 if issue not in (None, 0.0) else None
    )
    return out


def _money(value: object) -> str:
    try:
        return f"\u20b9{float(value):,.2f}"  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return "n/a"


def _pct(value: object) -> str:
    try:
        return f"{100.0 * float(value):+,.2f}%"  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return "n/a"


def _date(value: object) -> str:
    ts = _as_date(value)
    return ts.date().isoformat() if ts is not None else "not established"


def format_profile(
    ticker: str,
    company: Optional[Dict[str, object]],
    profile: Dict[str, object],
) -> str:
    """Render the history profile as markdown (used by CLI and report)."""
    company = company or {}
    name = str(company.get("name") or ticker)
    sector = str(company.get("sector") or "unknown")
    exchange = str(company.get("exchange") or "-")

    lines: List[str] = [
        f"### {name} ({ticker})",
        "",
        f"- **Sector / exchange:** {sector} / {exchange}",
        f"- **IPO date:** {_date(profile.get('ipo_date'))}",
        f"- **Listing date:** {_date(profile.get('listing_date'))}",
        f"- **Issue price:** {_money(profile['issue_price'])}"
        if profile.get("issue_price") else "- **Issue price:** not established",
    ]

    years_listed = profile.get("years_since_listing")
    if years_listed is not None:
        lines.append(
            f"- **Listed for:** {float(years_listed):.1f} years "
            f"({float(profile.get('months_since_listing') or 0.0):.0f} months)"
        )

    lines += [
        f"- **Data available:** {_date(profile['first_data_date'])} \u2192 "
        f"{_date(profile['last_data_date'])} "
        f"({int(profile['trading_days']):,} trading days, "
        f"{float(profile['years_of_data']):.1f} years)",
        f"- **Current close:** {_money(profile['last_close'])}",
        f"- **All-time high:** {_money(profile['all_time_high'])} "
        f"on {_date(profile['all_time_high_date'])}",
        f"- **All-time low:** {_money(profile['all_time_low'])} "
        f"on {_date(profile['all_time_low_date'])}",
        f"- **52-week range:** {_money(profile['low_52w'])} \u2013 "
        f"{_money(profile['high_52w'])}",
        f"- **Return over available data:** {_pct(profile['return_since_data'])}",
    ]

    if profile.get("cagr_since_data") is not None:
        lines.append(
            f"- **CAGR over available data:** {_pct(profile['cagr_since_data'])}"
        )
    if profile.get("growth_from_issue_price") is not None:
        lines.append(
            f"- **Growth from issue price:** {_pct(profile['growth_from_issue_price'])}"
            " *(indicative \u2014 ignores splits, bonus issues and dividends)*"
        )

    note = str(company.get("notes") or "").strip()
    if note:
        lines += ["", f"> _{note}_"]

    lines += [
        "",
        "> **Data caveat:** IPO/listing dates come from the hand-maintained "
        "`data/reference/nse_companies.csv`, not from the market API. Treat "
        "them as indicative and verify against NSE/BSE/SEBI filings.",
    ]
    return "\n".join(lines)
