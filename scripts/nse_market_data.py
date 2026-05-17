"""
NSE Market Data Fetcher
Fetches live/EOD market data for Nifty 500 stocks from NSE India API.
Handles session cookies and anti-bot measures.
"""

import requests
import time
import logging
from typing import Optional
from config import NSE_BASE_URL, NSE_INDEX_URL, NSE_NIFTY500_INDEX

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# More realistic browser headers that NSE accepts
_BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
    "Cache-Control": "max-age=0",
}

_API_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": f"{NSE_BASE_URL}/market-data/live-equity-market",
    "X-Requested-With": "XMLHttpRequest",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
}


class NSEClient:
    """Client for fetching market data from NSE India's internal API."""

    def __init__(self):
        self.session = requests.Session()
        self._cookies_initialized = False

    def _init_cookies(self, retries: int = 3) -> bool:
        """
        Visit the NSE website to obtain session cookies.
        NSE requires a 2-step warmup:
          1. Visit homepage (may 403 but still sets Akamai cookies)
          2. Visit market data page (builds session trust)
        Only then will the JSON API respond correctly.
        """
        for attempt in range(retries):
            try:
                logger.info(f"Initializing NSE session (attempt {attempt + 1}/{retries})...")
                
                # Step 1: Visit homepage — may return 403 but sets Akamai cookies
                r1 = self.session.get(
                    NSE_BASE_URL,
                    headers=_BROWSER_HEADERS,
                    timeout=15,
                    allow_redirects=True,
                )
                logger.info(f"Homepage: status={r1.status_code}, cookies={list(self.session.cookies.keys())}")
                time.sleep(2)
                
                # Step 2: Visit market data page — this builds session trust
                r2 = self.session.get(
                    f"{NSE_BASE_URL}/market-data/live-equity-market",
                    headers=_BROWSER_HEADERS,
                    timeout=15,
                    allow_redirects=True,
                )
                logger.info(f"Market page: status={r2.status_code}")
                
                if r2.status_code == 200:
                    self._cookies_initialized = True
                    logger.info("NSE session fully initialized")
                    time.sleep(1)
                    return True
                else:
                    logger.warning(f"Market page returned {r2.status_code}")
                    if attempt < retries - 1:
                        wait = 2 ** (attempt + 1)
                        logger.info(f"Retrying in {wait}s...")
                        time.sleep(wait)
            except requests.exceptions.RequestException as e:
                logger.error(f"Failed to initialize NSE session: {e}")
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)
        
        return False

    def fetch_index_data(self, index_name: str = NSE_NIFTY500_INDEX) -> Optional[dict]:
        """
        Fetch all constituent stocks data for a given NSE index.
        
        Args:
            index_name: Name of the index (e.g., "NIFTY 500")
        
        Returns:
            Dictionary with index metadata and constituent stock data,
            or None if the request fails.
        """
        # Ensure cookies are set
        if not self._cookies_initialized:
            if not self._init_cookies():
                logger.error("Cannot fetch data without valid cookies")
                return None
            time.sleep(1)  # Brief pause after cookie init

        try:
            url = f"{NSE_INDEX_URL}?index={index_name}"
            logger.info(f"Fetching index data: {index_name}")

            response = self.session.get(url, headers=_API_HEADERS, timeout=15)

            if response.status_code == 401 or response.status_code == 403:
                # Cookies expired, retry
                logger.warning("Cookies expired, re-initializing...")
                self._cookies_initialized = False
                if self._init_cookies():
                    time.sleep(1)
                    response = self.session.get(url, headers=_API_HEADERS, timeout=15)
                else:
                    return None

            response.raise_for_status()
            data = response.json()

            if "data" in data:
                logger.info(f"Received data for {len(data['data'])} stocks")
            return data

        except requests.exceptions.JSONDecodeError:
            logger.error("Response was not valid JSON (possible HTML error page)")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch index data: {e}")
            return None

    def get_nifty500_stocks(self) -> list[dict]:
        """
        Get market data for all Nifty 500 constituent stocks.
        
        Returns:
            List of dictionaries, each containing market data for one stock.
            Fields include: symbol, open, dayHigh, dayLow, previousClose,
            lastPrice, pChange, totalTradedVolume, totalTradedValue,
            yearHigh, yearLow, industry, etc.
        """
        data = self.fetch_index_data(NSE_NIFTY500_INDEX)
        if not data or "data" not in data:
            return []

        stocks = []
        for item in data["data"]:
            # Skip the index summary row (first item is usually the index itself)
            sym = item.get("symbol", "")
            if sym in (NSE_NIFTY500_INDEX, NSE_NIFTY500_INDEX.replace(" ", ""), ""):
                continue

            stock = {
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
            stocks.append(stock)

        logger.info(f"Parsed {len(stocks)} stocks from Nifty 500")
        return stocks

    def get_nifty500_symbols(self) -> list[str]:
        """Get just the list of Nifty 500 stock symbols."""
        stocks = self.get_nifty500_stocks()
        return [s["symbol"] for s in stocks if s["symbol"]]


# ─── Quick Test ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    client = NSEClient()
    stocks = client.get_nifty500_stocks()

    if stocks:
        print(f"\nTotal stocks: {len(stocks)}")
        print(f"\n{'SYMBOL':<15} {'LTP':>10} {'%CHNG':>8} {'VOLUME':>15} {'INDUSTRY'}")
        print("-" * 80)
        for stock in stocks[:20]:  # Show first 20
            print(
                f"{stock['symbol']:<15} "
                f"₹{stock['ltp']:>8.2f} "
                f"{stock['change_pct']:>7.2f}% "
                f"{stock['volume']:>14,} "
                f"{stock['industry']}"
            )
    else:
        print("Failed to fetch data. NSE may be blocking the request.")
        print("Try running during market hours or check your network.")
