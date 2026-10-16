"""Command-line interface.

Usage examples
--------------
    python main.py --list                                   # show the stock menu
    python main.py --select                                 # interactive pick -> profile + analysis
    python main.py --ticker RELIANCE.NS --profile-only      # history profile only
    python main.py --ticker ZOMATO.NS --out docs/zomato     # full analysis
    python main.py --csv data/raw/RELIANCE.csv --out docs/x # offline CSV
    python main.py --synthetic --out docs/demo_output       # offline demo
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from stocklab import __version__
from stocklab.backtest import run as run_backtest
from stocklab.company import (
    find_company,
    format_profile,
    history_summary,
    load_companies,
)
from stocklab.config import load_config
from stocklab.indicators import add_indicators
from stocklab.loader import load_csv, load_yfinance, save_processed, synthetic_ohlcv
from stocklab.regime import classify
from stocklab.report import build_summary, write_summary
from stocklab.signals import generate


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="market-style-analyser",
        description="Analyse a stock's history, detect its market style and "
                    "generate regime-appropriate trading inputs.",
    )
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    src = p.add_mutually_exclusive_group(required=False)
    src.add_argument("--csv", help="Path to an OHLCV CSV file")
    src.add_argument("--ticker", help="Ticker symbol (NSE: RELIANCE.NS)")
    src.add_argument("--synthetic", action="store_true",
                     help="Use a generated multi-regime series (offline demo)")
    src.add_argument("--select", action="store_true",
                     help="Interactively choose a stock from the reference list")

    p.add_argument("--list", action="store_true",
                   help="List the reference companies and exit")
    p.add_argument("--profile-only", action="store_true",
                   help="Show the instrument's history profile and skip the analysis")
    p.add_argument("--no-profile", action="store_true",
                   help="Skip the history profile section")
    p.add_argument("--config", default=None, help="Optional YAML config file")
    p.add_argument("--start", default=None, help="Start date (YYYY-MM-DD)")
    p.add_argument("--end", default=None, help="End date (YYYY-MM-DD); blank = today")
    p.add_argument("--out", default=None, help="Directory for outputs")
    p.add_argument("--cost-bps", type=float, default=None,
                   help="Transaction cost per position change, in basis points")
    p.add_argument("--quiet", action="store_true",
                   help="Only write the report; do not print it")
    return p


# --------------------------------------------------------------------------- #
# Interactive selection
# --------------------------------------------------------------------------- #
def print_company_list(companies: pd.DataFrame | None = None) -> None:
    df = load_companies() if companies is None else companies
    print(f"\n  {len(df)} companies in the reference list "
          f"(data/reference/nse_companies.csv)\n")
    print(f"  {'#':>3}  {'Symbol':<14} {'Company':<45} {'IPO date':<12}")
    print(f"  {'-'*3}  {'-'*14} {'-'*45} {'-'*12}")
    for i, row in df.reset_index(drop=True).iterrows():
        ipo = row["ipo_date"]
        ipo_txt = ipo.date().isoformat() if pd.notna(ipo) else "-"
        name = str(row["name"])
        if len(name) > 43:
            name = name[:42] + "\u2026"
        print(f"  {i+1:>3}  {str(row['symbol']):<14} {name:<45} {ipo_txt:<12}")
    print()


def prompt_select(companies: pd.DataFrame) -> str | None:
    """Present a numbered menu and return the chosen symbol (or None)."""
    df = companies.reset_index(drop=True)
    print("\n  Select a stock:\n")
    for i, row in df.iterrows():
        print(f"  [{i+1:>2}] {row['name']} ({row['symbol']})")
    print()

    while True:
        try:
            raw = input("  Enter number (or 'q' to quit): ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return None
        if raw.lower() in {"q", "quit", ""}:
            return None
        if raw.isdigit() and 1 <= int(raw) <= len(df):
            return str(df.iloc[int(raw) - 1]["symbol"])
        print("  Invalid selection - try again.")


# --------------------------------------------------------------------------- #
# Data loading
# --------------------------------------------------------------------------- #
def load_source(args: argparse.Namespace, cfg, ticker: str) -> pd.DataFrame:
    if args.csv:
        return load_csv(args.csv)
    if args.synthetic:
        return synthetic_ohlcv()
    return load_yfinance(ticker, cfg.start, cfg.end)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.list:
        print_company_list()
        return 0

    if not any((args.csv, args.ticker, args.synthetic, args.select)):
        print("error: choose a data source: --csv, --ticker, --select or "
              "--synthetic (or use --list)", file=sys.stderr)
        return 2

    cfg = load_config(
        args.config,
        start=args.start,
        end=args.end,
        cost_bps=args.cost_bps,
    )

    # --- Decide which instrument we are analysing --------------------------- #
    company = None
    companies = None
    if args.select:
        companies = load_companies()
        chosen = prompt_select(companies)
        if chosen is None:
            print("  Cancelled.")
            return 0
        ticker = chosen
        company = find_company(chosen, companies)
        # Default the window wide enough to include a recent IPO.
        if args.start is None and company and pd.notna(company.get("listing_date")):
            cfg = cfg.replace(start=pd.Timestamp(company["listing_date"])
                              .date().isoformat())
    elif args.ticker:
        ticker = args.ticker
        company = find_company(ticker)
    elif args.csv:
        ticker = Path(args.csv).stem
        company = find_company(ticker)
    else:
        ticker = "SYNTHETIC"

    try:
        raw = load_source(args, cfg, ticker)
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    # --- History profile ---------------------------------------------------- #
    profile = None
    if not args.no_profile and not args.synthetic:
        try:
            profile = history_summary(raw, company)
        except ValueError as exc:
            print(f"warning: could not build history profile ({exc})",
                  file=sys.stderr)

    if profile is not None and args.profile_only:
        print()
        print(format_profile(ticker, company, profile))
        return 0

    # --- Market-style pipeline --------------------------------------------- #
    enriched = add_indicators(raw, cfg)
    labelled = classify(enriched, cfg)
    signalled = generate(labelled, cfg)
    result = run_backtest(signalled, cfg)

    summary = build_summary(
        ticker, signalled, result, cfg,
        company=company, profile=profile,
    )

    if not args.quiet:
        print(summary)

    if args.out:
        out_dir = Path(args.out)
        save_processed(signalled, out_dir, f"{ticker}_processed")
        equity = result["equity"]
        assert isinstance(equity, pd.DataFrame)
        save_processed(equity, out_dir, f"{ticker}_equity")
        path = write_summary(summary, out_dir)
        print(f"\nWrote outputs to {out_dir}/ (report: {path.name})")

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
