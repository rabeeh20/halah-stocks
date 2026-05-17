#!/usr/bin/env python3
"""
Daily Market Data Update Pipeline
==================================
Runs every day at 3:45 PM IST (after NSE market close at 3:30 PM).

This script:
  1. Fetches end-of-day (EOD) data for all Nifty 500 stocks from NSE
  2. Merges live market data into existing halal_stocks.json (preserving screening results)
  3. Saves a full market snapshot (market_snapshot.json) for all 500 stocks
  4. Updates the screening_results.json with latest market data

This is LIGHTWEIGHT — no Screener.in calls, no financial scraping.
Only NSE API for prices, volume, and market cap.

Schedule: 45 15 * * 1-5 (3:45 PM IST, Monday–Friday)
Duration: ~10 seconds
"""

import json
import os
import sys
import logging
from datetime import datetime, timezone, timedelta

# Add scripts directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nse_market_data import NSEClient

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


def fetch_nse_eod_data() -> list[dict]:
    """
    Fetch end-of-day market data for all Nifty 500 stocks.
    Returns list of stock dicts with OHLCV + market data.
    """
    client = NSEClient()
    stocks = client.get_nifty500_stocks()

    if not stocks:
        logger.error("Failed to fetch Nifty 500 data from NSE")
        return []

    logger.info(f"Fetched EOD data for {len(stocks)} stocks from NSE")
    return stocks


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
    """
    now = datetime.now(IST)
    logger.info("=" * 60)
    logger.info(f"  DAILY MARKET UPDATE — {now.strftime('%d %b %Y, %I:%M %p IST')}")
    logger.info("=" * 60)

    # Check if it's a weekday (market is closed on weekends)
    force = "--force" in sys.argv
    if now.weekday() >= 5 and not force:  # 5=Saturday, 6=Sunday
        logger.info("Weekend detected — skipping market update (use --force to override)")
        return

    # ── Step 1: Fetch NSE EOD data ──────────────────────────────────────────
    logger.info("\n📊 Step 1: Fetching NSE end-of-day data...")
    nse_data = fetch_nse_eod_data()

    if not nse_data:
        logger.error("❌ NSE data fetch failed — aborting daily update")
        sys.exit(1)

    # ── Step 2: Update halal_stocks.json ────────────────────────────────────
    logger.info("\n🕌 Step 2: Updating halal stocks with fresh market data...")
    halal_data = update_halal_stocks(nse_data)
    if halal_data:
        save_json(HALAL_STOCKS_FILE, halal_data)

    # ── Step 3: Update screening_results.json ───────────────────────────────
    logger.info("\n📋 Step 3: Updating screening results...")
    results_data = update_screening_results(nse_data)
    if results_data:
        save_json(SCREENING_RESULTS_FILE, results_data)

    # ── Step 4: Save full market snapshot ───────────────────────────────────
    logger.info("\n📸 Step 4: Creating market snapshot...")
    snapshot = create_market_snapshot(nse_data)
    save_json(MARKET_SNAPSHOT_FILE, snapshot)

    # ── Summary ─────────────────────────────────────────────────────────────
    logger.info("\n" + "=" * 60)
    logger.info("  ✅ DAILY UPDATE COMPLETE")
    logger.info(f"  Nifty 500 stocks: {len(nse_data)}")
    if halal_data:
        logger.info(f"  Halal stocks updated: {len(halal_data.get('stocks', []))}")
    if snapshot.get("summary"):
        s = snapshot["summary"]
        logger.info(f"  Market: {s['advances']} ↑  {s['declines']} ↓  {s['unchanged']} =")
        logger.info(f"  Top Gainer: {s['top_gainer']['symbol']} (+{s['top_gainer']['change_pct']:.2f}%)")
        logger.info(f"  Top Loser:  {s['top_loser']['symbol']} ({s['top_loser']['change_pct']:.2f}%)")
    logger.info("=" * 60)


if __name__ == "__main__":
    run_daily_update()
