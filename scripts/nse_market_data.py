"""
NSE Market Data Fetcher
=======================
Fetches EOD market data for Nifty 500 stocks from NSE India.

NSE's API changes frequently. This module uses a multi-source strategy:
  1. Try the NSE CSV download (most reliable, gives full 500 stocks)
  2. Try the new NSE JSON API with correct session warmup
  3. Fallback: Use Yahoo Finance batch quotes for halal stocks only
"""

import requests
import time
import logging
import csv
import io
from typing import Optional
from config import NSE_BASE_URL, NSE_NIFTY500_INDEX

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

_BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

_API_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": f"{NSE_BASE_URL}/market-data/live-equity-market",
}


class NSEClient:
    """Client for fetching market data from NSE India."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(_BROWSER_HEADERS)
        self._session_ready = False

    def _warmup_session(self, retries: int = 3) -> bool:
        """
        Two-step session warmup so NSE accepts our API requests.
        """
        for attempt in range(retries):
            try:
                logger.info(f"Initializing NSE session (attempt {attempt + 1}/{retries})...")

                r1 = self.session.get(NSE_BASE_URL, timeout=15, allow_redirects=True)
                logger.info(f"Homepage: status={r1.status_code}, cookies={list(self.session.cookies.keys())}")
                time.sleep(2)

                r2 = self.session.get(
                    f"{NSE_BASE_URL}/market-data/live-equity-market",
                    timeout=15,
                    allow_redirects=True,
                )
                logger.info(f"Market page: status={r2.status_code}")

                if r2.status_code == 200:
                    self._session_ready = True
                    logger.info("NSE session fully initialized")
                    time.sleep(1)
                    return True

                if attempt < retries - 1:
                    time.sleep(2 ** attempt)

            except requests.exceptions.RequestException as e:
                logger.error(f"Session warmup failed: {e}")
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)

        return False

    # ── Source 1: NSE CSV Download ───────────────────────────────────────────

    def _fetch_via_csv(self) -> list[dict]:
        """
        Download the official NSE Nifty 500 CSV.
        URL: https://nsearchives.nseindia.com/content/indices/ind_nifty500list.csv
        This gives the CONSTITUENT LIST (symbols, company names, industry).
        For prices we still need the API, but this is the most reliable symbol source.
        """
        try:
            csv_url = "https://nsearchives.nseindia.com/content/indices/ind_nifty500list.csv"
            r = self.session.get(csv_url, timeout=15)
            if r.status_code != 200:
                logger.warning(f"NSE CSV returned {r.status_code}")
                return []

            reader = csv.DictReader(io.StringIO(r.text))
            symbols = []
            for row in reader:
                symbol = (row.get("Symbol") or row.get("symbol", "")).strip()
                if symbol:
                    symbols.append(symbol)

            logger.info(f"Got {len(symbols)} symbols from NSE CSV")
            return symbols

        except Exception as e:
            logger.warning(f"CSV fetch failed: {e}")
            return []

    # ── Source 2: NSE JSON API (new endpoint) ────────────────────────────────

    def _fetch_via_new_api(self) -> list[dict]:
        """
        Try NSE's current JSON API endpoints for Nifty 500 market data.
        NSE changes endpoints frequently — we try multiple patterns.
        """
        if not self._session_ready:
            if not self._warmup_session():
                return []

        endpoints = [
            f"{NSE_BASE_URL}/api/equity-stockIndices?index=NIFTY%20500",
            f"{NSE_BASE_URL}/api/equity-stockIndices?index=NIFTY500",
            f"{NSE_BASE_URL}/api/equity-stockIndices?index=NIFTY+500",
        ]

        for url in endpoints:
            try:
                logger.info(f"Trying endpoint: {url}")
                r = self.session.get(url, headers=_API_HEADERS, timeout=15)
                if r.status_code != 200:
                    logger.warning(f"  → {r.status_code}")
                    time.sleep(1)
                    continue

                data = r.json()
                items = data.get("data", [])
                if not items:
                    continue

                stocks = []
                for item in items:
                    sym = item.get("symbol", "")
                    if not sym or sym in ("NIFTY 500", "NIFTY500"):
                        continue
                    stocks.append(self._parse_nse_item(item))

                if stocks:
                    logger.info(f"Got {len(stocks)} stocks from NSE JSON API")
                    return stocks

            except Exception as e:
                logger.warning(f"Endpoint {url} failed: {e}")
                time.sleep(1)

        return []

    # ── Source 3: Yahoo Finance (reliable fallback) ──────────────────────────

    def _fetch_via_yahoo(self, symbols: list[str]) -> list[dict]:
        """
        Fetch prices from Yahoo Finance for a list of symbols.
        Yahoo uses {SYMBOL}.NS format for NSE stocks.
        Batches 50 symbols per request.
        """
        if not symbols:
            return []

        logger.info(f"Fetching {len(symbols)} stocks via Yahoo Finance...")
        stocks = []
        batch_size = 50

        for i in range(0, len(symbols), batch_size):
            batch = symbols[i:i + batch_size]
            yahoo_symbols = " ".join(f"{s}.NS" for s in batch)

            try:
                url = "https://query1.finance.yahoo.com/v7/finance/quote"
                params = {
                    "symbols": yahoo_symbols,
                    "fields": "symbol,regularMarketPrice,regularMarketOpen,regularMarketDayHigh,regularMarketDayLow,regularMarketPreviousClose,regularMarketChange,regularMarketChangePercent,regularMarketVolume,fiftyTwoWeekHigh,fiftyTwoWeekLow,regularMarketTime",
                }
                headers = {
                    "User-Agent": "Mozilla/5.0",
                    "Accept": "application/json",
                }
                r = requests.get(url, params=params, headers=headers, timeout=15)

                if r.status_code != 200:
                    logger.warning(f"Yahoo batch {i // batch_size + 1}: HTTP {r.status_code}")
                    continue

                data = r.json()
                results = data.get("quoteResponse", {}).get("result", [])

                for item in results:
                    symbol = item.get("symbol", "").replace(".NS", "")
                    stocks.append({
                        "symbol": symbol,
                        "company_name": item.get("longName") or item.get("shortName", ""),
                        "industry": item.get("industry", ""),
                        "open": item.get("regularMarketOpen", 0),
                        "high": item.get("regularMarketDayHigh", 0),
                        "low": item.get("regularMarketDayLow", 0),
                        "prev_close": item.get("regularMarketPreviousClose", 0),
                        "ltp": item.get("regularMarketPrice", 0),
                        "change": item.get("regularMarketChange", 0),
                        "change_pct": item.get("regularMarketChangePercent", 0),
                        "volume": item.get("regularMarketVolume", 0),
                        "value_lakhs": 0,
                        "year_high": item.get("fiftyTwoWeekHigh", 0),
                        "year_low": item.get("fiftyTwoWeekLow", 0),
                        "last_update_time": "",
                    })

                logger.info(f"  Batch {i // batch_size + 1}: got {len(results)} quotes")
                time.sleep(0.5)

            except Exception as e:
                logger.warning(f"Yahoo batch failed: {e}")
                time.sleep(1)

        logger.info(f"Yahoo Finance: total {len(stocks)} stocks fetched")
        return stocks

    # ── Parse NSE API response item ──────────────────────────────────────────

    def _parse_nse_item(self, item: dict) -> dict:
        return {
            "symbol": item.get("symbol", ""),
            "company_name": item.get("meta", {}).get("companyName", ""),
            "industry": item.get("meta", {}).get("industry", ""),
            "series": item.get("series", ""),
            "open": item.get("open", 0),
            "high": item.get("dayHigh", 0),
            "low": item.get("dayLow", 0),
            "prev_close": item.get("previousClose", 0),
            "ltp": item.get("lastPrice", 0),
            "change": item.get("change", 0),
            "change_pct": item.get("pChange", 0),
            "volume": item.get("totalTradedVolume", 0),
            "value_lakhs": item.get("totalTradedValue", 0),
            "year_high": item.get("yearHigh", 0),
            "year_low": item.get("yearLow", 0),
            "last_update_time": item.get("lastUpdateTime", ""),
        }

    # ── Public API ────────────────────────────────────────────────────────────

    def get_nifty500_stocks(self) -> list[dict]:
        """
        Get market data for all Nifty 500 stocks.
        Tries multiple sources in order of reliability.
        """
        # Try NSE JSON API first (most complete data)
        stocks = self._fetch_via_new_api()
        if stocks and len(stocks) > 100:
            return stocks

        logger.warning("NSE JSON API failed or returned too few stocks — falling back to Yahoo Finance")

        # Get symbol list from NSE CSV
        symbols = self._fetch_via_csv()

        # If CSV also failed, we can't do anything
        if not symbols:
            logger.error("All NSE data sources failed")
            return []

        # Fetch prices from Yahoo Finance
        stocks = self._fetch_via_yahoo(symbols)
        return stocks

    def get_nifty500_symbols(self) -> list[str]:
        """Get just the list of Nifty 500 stock symbols."""
        # Try CSV first (fast, just symbols)
        symbols = self._fetch_via_csv()
        if symbols:
            return symbols

        # Fallback: get from full stocks
        stocks = self.get_nifty500_stocks()
        return [s["symbol"] for s in stocks if s.get("symbol")]


# ── Quick Test ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    client = NSEClient()
    stocks = client.get_nifty500_stocks()

    if stocks:
        print(f"\nTotal stocks: {len(stocks)}")
        print(f"\n{'SYMBOL':<15} {'LTP':>10} {'%CHNG':>8} {'VOLUME':>15}")
        print("-" * 60)
        for stock in stocks[:20]:
            print(
                f"{stock['symbol']:<15} "
                f"₹{stock['ltp']:>8.2f} "
                f"{stock['change_pct']:>7.2f}% "
                f"{stock['volume']:>14,}"
            )
    else:
        print("Failed to fetch data from all sources.")
