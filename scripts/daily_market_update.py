#!/usr/bin/env python3
"""
Daily Market Data Update Pipeline
==================================
Runs every day at 3:36 PM IST (after NSE market close at 3:30 PM).

FLOW:
  Monthly (1st of month) → shariah_screener.py → screens 500 stocks → saves HALAL list
  Daily   (3:36 PM IST)  → THIS SCRIPT → fetches prices for HALAL stocks ONLY

This is VERY LIGHTWEIGHT:
  - Reads halal symbols from halal_stocks.json (e.g. 54 stocks)
  - Fetches prices ONLY for those 54 halal stocks from Yahoo Finance
  - Updates LTP, change%, volume in halal_stocks.json
  - NO full 500-stock scan — that is the monthly screener's job

Schedule: 6 10 * * 1-5 (3:36 PM IST = 10:06 AM UTC, Monday–Friday)
Duration: ~5 seconds
"""

import json
import os
import sys
import logging
from datetime import datetime, timezone, timedelta

# Add scripts directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── Configuration ───────────────────────────────────────────────────────────────

IST = timezone(timedelta(hours=5, minutes=30))
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
HALAL_STOCKS_FILE = os.path.join(DATA_DIR, "halal_stocks.json")
SCREENING_RESULTS_FILE = os.path.join(DATA_DIR, "screening_results.json")
MARKET_SNAPSHOT_FILE = os.path.join(DATA_DIR, "market_snapshot.json")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


def load_json(filepath: str) -> dict | None:
    """Load a JSON file safely."""
    try:
        if os.path.exists(filepath):
            with open(filepath, "r") as f:
                return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Failed to read {filepath}: {e}")
    return None


def save_json(filepath: str, data: dict):
    """Save data to a JSON file with pretty formatting."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved: {filepath}")


def get_halal_symbols() -> list[str]:
    """
    Read the list of HALAL stock symbols from halal_stocks.json.
    These are the stocks screened monthly by shariah_screener.py.
    We only fetch daily data for THESE stocks — not all 500.
    """
    halal_data = load_json(HALAL_STOCKS_FILE)
    if not halal_data:
        logger.error("halal_stocks.json not found — run monthly screening first!")
        return []

    symbols = [s["symbol"] for s in halal_data.get("stocks", []) if s.get("symbol")]
    logger.info(f"Found {len(symbols)} halal stocks to update: {', '.join(symbols[:5])}...")
    return symbols


def fetch_halal_stocks_data(symbols: list[str]) -> list[dict]:
    """
    Fetch EOD market data for ONLY the halal stocks.
    Uses Yahoo Finance (yfinance) — fast, reliable for Indian stocks.
    """
    if not symbols:
        logger.error("No halal symbols to fetch")
        return []

    try:
        import yfinance as yf
    except ImportError:
        logger.error("yfinance not installed. Run: pip3 install yfinance")
        return []

    logger.info(f"Fetching prices for {len(symbols)} halal stocks via Yahoo Finance...")

    # Convert to Yahoo Finance format: RELIANCE → RELIANCE.NS
    yahoo_symbols = [f"{s}.NS" for s in symbols]

    try:
        # Download all halal stocks in ONE batch (only 54 stocks — very fast)
        data = yf.download(
            " ".join(yahoo_symbols),
            period="1d",
            interval="1d",
            progress=False,
            group_by="ticker",
            auto_adjust=True,
            threads=True,
        )

        stocks = []
        for yahoo_sym in yahoo_symbols:
            symbol = yahoo_sym.replace(".NS", "")
            try:
                if len(yahoo_symbols) == 1:
                    row = data.iloc[-1] if not data.empty else None
                else:
                    ticker_data = data[yahoo_sym] if yahoo_sym in data.columns.get_level_values(0) else None
                    row = ticker_data.iloc[-1] if ticker_data is not None and not ticker_data.empty else None

                if row is not None:
                    close  = float(row.get("Close", 0) or 0)
                    open_  = float(row.get("Open",  0) or 0)
                    high   = float(row.get("High",  0) or 0)
                    low    = float(row.get("Low",   0) or 0)
                    vol    = int(row.get("Volume",  0) or 0)
                    prev_close = open_  # best approximation from daily data
                    change = round(close - open_, 2)
                    change_pct = round(((close - open_) / open_) * 100, 2) if open_ else 0

                    stocks.append({
                        "symbol":          symbol,
                        "open":            open_,
                        "high":            high,
                        "low":             low,
                        "prev_close":      prev_close,
                        "ltp":             close,
                        "change":          change,
                        "change_pct":      change_pct,
                        "volume":          vol,
                        "value_lakhs":     0,
                        "year_high":       0,
                        "year_low":        0,
                        "last_update_time": "",
                    })
                    logger.info(f"  {symbol:<15} LTP=₹{close:.2f}  Change={change_pct:+.2f}%  Vol={vol:,}")
                else:
                    logger.warning(f"  {symbol}: No data returned")

            except Exception as e:
                logger.warning(f"  {symbol}: Error — {e}")

        logger.info(f"✅ Fetched {len(stocks)}/{len(symbols)} halal stocks successfully")
        return stocks

    except Exception as e:
        logger.error(f"Yahoo Finance batch download failed: {e}")
        return []


def update_halal_stocks(nse_data: list[dict]) -> dict:
    """
    Update halal_stocks.json with fresh market data from NSE.
    Preserves all Shariah screening fields (status, scores, ratios).
    Only updates: ltp, open, high, low, prev_close, change, change_pct,
                  volume, value_lakhs, market_cap_cr (recalculated).
    """
    halal_data = load_json(HALAL_STOCKS_FILE)
    if not halal_data:
        logger.warning("No existing halal_stocks.json found — skipping halal update")
        return {}

    # Build NSE lookup: symbol → market data
    nse_map = {s["symbol"]: s for s in nse_data}

    updated_count = 0
    missing_count = 0
    now = datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST")

    for stock in halal_data.get("stocks", []):
        symbol = stock.get("symbol")
        nse = nse_map.get(symbol)

        if nse:
            # Update market data fields (preserve screening fields)
            stock["ltp"] = nse["ltp"]
            stock["open"] = nse["open"]
            stock["high"] = nse["high"]
            stock["low"] = nse["low"]
            stock["prev_close"] = nse["prev_close"]
            stock["change"] = nse["change"]
            stock["change_pct"] = nse["change_pct"]
            stock["volume"] = nse["volume"]
            stock["value_lakhs"] = nse["value_lakhs"]
            stock["year_high"] = nse["year_high"]
            stock["year_low"] = nse["year_low"]
            stock["last_update_time"] = nse.get("last_update_time", "")

            # Recalculate market cap from screening data
            # If the stock already has market_cap_cr from screening, keep it
            # (Screener.in market cap is more accurate as it's from financials)
            # But we could update it here if needed from NSE data
            updated_count += 1
        else:
            missing_count += 1
            logger.debug(f"[{symbol}] Not found in NSE Nifty 500 data")

    # Update metadata
    halal_data["last_market_update"] = now
    halal_data["market_data_source"] = "NSE_EOD"

    logger.info(
        f"Updated market data for {updated_count}/{len(halal_data.get('stocks', []))} halal stocks "
        f"({missing_count} not in current Nifty 500)"
    )

    return halal_data


def update_screening_results(nse_data: list[dict]) -> dict:
    """
    Update screening_results.json with fresh market data.
    This file has ALL screened stocks across halal/haram/doubtful categories.
    """
    results_data = load_json(SCREENING_RESULTS_FILE)
    if not results_data:
        logger.warning("No screening_results.json found — skipping")
        return {}

    nse_map = {s["symbol"]: s for s in nse_data}
    now = datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST")
    updated = 0

    # Update stocks in all categories
    for category in ["halal", "haram", "doubtful"]:
        stocks = results_data.get(category, [])
        for result in stocks:
            symbol = result.get("symbol")
            nse = nse_map.get(symbol)
            if nse:
                result["ltp"] = nse["ltp"]
                result["change_pct"] = nse["change_pct"]
                result["volume"] = nse["volume"]
                updated += 1

    results_data["last_market_update"] = now

    logger.info(f"Updated market data for {updated} screening results")
    return results_data


def create_market_snapshot(nse_data: list[dict]) -> dict:
    """
    Create a full market snapshot of all Nifty 500 stocks.
    This is a standalone EOD file used by the frontend for the "All Nifty 500" view.
    """
    now = datetime.now(IST)

    snapshot = {
        "snapshot_date": now.strftime("%Y-%m-%d"),
        "snapshot_time": now.strftime("%H:%M:%S IST"),
        "snapshot_timestamp": now.isoformat(),
        "total_stocks": len(nse_data),
        "market_status": "CLOSED" if now.hour >= 16 or now.hour < 9 else "OPEN",
        "stocks": nse_data,
    }

    # Calculate summary stats
    if nse_data:
        gainers = sum(1 for s in nse_data if (s.get("change_pct") or 0) > 0)
        losers = sum(1 for s in nse_data if (s.get("change_pct") or 0) < 0)
        unchanged = len(nse_data) - gainers - losers

        top_gainer = max(nse_data, key=lambda s: s.get("change_pct") or 0)
        top_loser = min(nse_data, key=lambda s: s.get("change_pct") or 0)

        snapshot["summary"] = {
            "advances": gainers,
            "declines": losers,
            "unchanged": unchanged,
            "top_gainer": {
                "symbol": top_gainer["symbol"],
                "change_pct": top_gainer.get("change_pct", 0),
                "ltp": top_gainer.get("ltp", 0),
            },
            "top_loser": {
                "symbol": top_loser["symbol"],
                "change_pct": top_loser.get("change_pct", 0),
                "ltp": top_loser.get("ltp", 0),
            },
        }

    return snapshot


def run_daily_update():
    """
    Main entry point for the daily market data update.
    ONLY updates prices for HALAL stocks — not all 500.
    """
    now = datetime.now(IST)
    logger.info("=" * 60)
    logger.info(f"  DAILY MARKET UPDATE — {now.strftime('%d %b %Y, %I:%M %p IST')}")
    logger.info("=" * 60)

    # Check if it's a weekday (market is closed on weekends)
    force = "--force" in sys.argv
    if now.weekday() >= 5 and not force:  # 5=Saturday, 6=Sunday
        logger.info("Weekend — skipping (use --force to override)")
        return

    # ── Step 1: Read halal symbols from monthly screening ───────────────────
    logger.info("\n📋 Step 1: Reading halal stock list from last monthly screening...")
    halal_symbols = get_halal_symbols()

    if not halal_symbols:
        logger.error("❌ No halal stocks found — run monthly screening first!")
        sys.exit(1)

    # ── Step 2: Fetch prices for ONLY those halal stocks ────────────────────
    logger.info(f"\n📊 Step 2: Fetching prices for {len(halal_symbols)} halal stocks...")
    market_data = fetch_halal_stocks_data(halal_symbols)

    if not market_data:
        logger.error("❌ Market data fetch failed — aborting")
        sys.exit(1)

    # ── Step 3: Merge into halal_stocks.json (preserve screening data) ──────
    logger.info("\n🕌 Step 3: Merging market data into halal_stocks.json...")
    halal_data = update_halal_stocks(market_data)
    if halal_data:
        save_json(HALAL_STOCKS_FILE, halal_data)

    # ── Summary ─────────────────────────────────────────────────────────────
    logger.info("\n" + "=" * 60)
    logger.info("  ✅ DAILY UPDATE COMPLETE")
    logger.info(f"  Halal stocks updated: {len(market_data)}/{len(halal_symbols)}")
    if market_data:
        gainers = [s for s in market_data if (s.get('change_pct') or 0) > 0]
        losers  = [s for s in market_data if (s.get('change_pct') or 0) < 0]
        if gainers:
            top = max(gainers, key=lambda s: s.get('change_pct', 0))
            logger.info(f"  Top Gainer: {top['symbol']} (+{top['change_pct']:.2f}%)")
        if losers:
            bot = min(losers, key=lambda s: s.get('change_pct', 0))
            logger.info(f"  Top Loser:  {bot['symbol']} ({bot['change_pct']:.2f}%)")
    logger.info("=" * 60)


if __name__ == "__main__":
    run_daily_update()
