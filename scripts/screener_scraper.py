"""
Screener.in Data Scraper v2
Fetches financial data using BeautifulSoup with section-ID-based table identification.
Proven to work with Screener.in's actual HTML structure.
"""

import requests
import pandas as pd
from bs4 import BeautifulSoup
import re
import time
import logging
from typing import Optional

from config import (
    SCREENER_BASE_URL,
    SCREENER_HEADERS,
    SCREENER_REQUEST_DELAY,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


class ScreenerScraper:
    """Scrapes financial data from Screener.in for a given stock symbol."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(SCREENER_HEADERS)

    def _fetch_page(self, symbol: str) -> Optional[str]:
        """Fetch the HTML content of a company page."""
        url = f"{SCREENER_BASE_URL}/{symbol}/consolidated/"
        try:
            response = self.session.get(url, timeout=15)
            if response.status_code == 404:
                url = f"{SCREENER_BASE_URL}/{symbol}/"
                response = self.session.get(url, timeout=15)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            logger.warning(f"[{symbol}] Request failed: {e}")
            return None

    def _extract_table_from_section(self, soup: BeautifulSoup, section_id: str) -> Optional[pd.DataFrame]:
        """
        Extract a financial table from a specific section of the page.
        Screener.in uses section IDs: 'profit-loss', 'balance-sheet', 'quarters', etc.
        """
        section = soup.find('section', id=section_id)
        if not section:
            logger.debug(f"Section '{section_id}' not found")
            return None

        table = section.find('table')
        if not table:
            logger.debug(f"No table in section '{section_id}'")
            return None

        # Parse rows
        rows = []
        for tr in table.find_all('tr'):
            cells = []
            for td in tr.find_all(['td', 'th']):
                text = td.get_text(strip=True)
                # Clean up: remove + suffix, non-breaking spaces
                text = text.replace('\xa0', ' ').replace('+', '').strip()
                cells.append(text)
            if cells:
                rows.append(cells)

        if not rows:
            return None

        # First row is headers (years), rest are data
        df = pd.DataFrame(rows[1:], columns=rows[0] if rows[0] else None)
        return df

    def _get_value(self, df: Optional[pd.DataFrame], row_label: str, col_index: int = 1) -> float:
        """
        Extract a numeric value from a DataFrame by row label.
        Searches the first column for a partial match.
        """
        if df is None or df.empty:
            return 0.0

        try:
            first_col = df.columns[0] if len(df.columns) > 0 else 0

            for idx, row in df.iterrows():
                cell_text = str(row.iloc[0]).strip().lower()
                if row_label.lower() in cell_text:
                    # Found the row — get the value from the latest year column
                    if col_index < len(row):
                        val = str(row.iloc[col_index]).replace(',', '').replace('+', '').strip()
                        if val in ('', '-', '—', 'nan'):
                            return 0.0
                        return float(val)
            return 0.0
        except (ValueError, IndexError) as e:
            logger.debug(f"Could not extract '{row_label}': {e}")
            return 0.0

    def _parse_market_cap(self, soup: BeautifulSoup) -> Optional[float]:
        """Extract Market Cap from the company info section."""
        try:
            # Look for the "Market Cap" label in the top section
            for li in soup.find_all('li'):
                name = li.find('span', class_='name')
                if name and 'Market Cap' in name.text:
                    value_span = li.find('span', class_='number')
                    if value_span:
                        val = value_span.text.replace(',', '').replace('₹', '').strip()
                        return float(val)

            # Fallback: regex on raw text
            text = soup.get_text()
            match = re.search(r'Market\s+Cap[^₹]*₹\s*([\d,]+(?:\.\d+)?)', text)
            if match:
                return float(match.group(1).replace(',', ''))
        except (ValueError, AttributeError):
            pass
        return None

    def _parse_industry(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract industry from peer comparison links."""
        try:
            # Screener shows industry breadcrumb in peer section
            peer_section = soup.find('section', id='peers')
            if peer_section:
                links = peer_section.find_all('a')
                for link in links:
                    href = link.get('href', '')
                    if '/market/' in href:
                        return link.text.strip()
        except AttributeError:
            pass
        return None

    def _parse_company_name(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract company name from the page heading."""
        try:
            h1 = soup.find('h1')
            if h1:
                return h1.text.strip()
        except AttributeError:
            pass
        return None

    def fetch_company_data(self, symbol: str) -> Optional[dict]:
        """
        Fetch and parse all financial data for a company.

        Returns dict with: symbol, company_name, industry, market_cap_cr,
        borrowings_cr, cash_cr, receivables_cr, sales_cr, other_income_cr, etc.
        """
        logger.info(f"Fetching data for {symbol}...")
        html = self._fetch_page(symbol)
        if not html:
            return None

        soup = BeautifulSoup(html, 'lxml')

        # Parse metadata
        company_name = self._parse_company_name(soup)
        market_cap = self._parse_market_cap(soup)
        industry = self._parse_industry(soup)

        # Parse financial tables using section IDs
        balance_sheet = self._extract_table_from_section(soup, 'balance-sheet')
        profit_loss = self._extract_table_from_section(soup, 'profit-loss')

        # Get latest year data (column index 1 = most recent year after row labels)
        # Find the latest year column index
        latest_col = 1  # Default
        if balance_sheet is not None and len(balance_sheet.columns) > 1:
            # Columns are like: ['', 'Mar 2015', 'Mar 2016', ..., 'Mar 2025']
            # Last data column = latest year
            latest_col = len(balance_sheet.columns) - 1
            data_year = str(balance_sheet.columns[latest_col])
        else:
            data_year = None

        # Extract Balance Sheet values (in Crores)
        borrowings = self._get_value(balance_sheet, "borrowings", latest_col)
        total_assets = self._get_value(balance_sheet, "total assets", latest_col)

        # For cash and receivables, look in "Other Assets" expanded or use 0 as safe default
        # Screener.in groups these under "Other Assets +"
        # We'll get what we can from the main table
        other_assets = self._get_value(balance_sheet, "other assets", latest_col)

        # Extract P&L values (in Crores) — latest year
        pl_latest_col = 1
        if profit_loss is not None and len(profit_loss.columns) > 1:
            pl_latest_col = len(profit_loss.columns) - 1

        sales = self._get_value(profit_loss, "sales", pl_latest_col)
        other_income = self._get_value(profit_loss, "other income", pl_latest_col)
        interest = self._get_value(profit_loss, "interest", pl_latest_col)
        net_profit = self._get_value(profit_loss, "net profit", pl_latest_col)

        result = {
            "symbol": symbol,
            "company_name": company_name,
            "industry": industry,
            "market_cap_cr": market_cap,
            "data_year": data_year,
            # Balance Sheet
            "borrowings_cr": borrowings,
            "total_assets_cr": total_assets,
            "other_assets_cr": other_assets,
            # P&L
            "sales_cr": sales,
            "other_income_cr": other_income,
            "interest_expense_cr": interest,
            "net_profit_cr": net_profit,
        }

        logger.info(
            f"[{symbol}] Mkt Cap: ₹{market_cap} Cr | "
            f"Borrowings: ₹{borrowings} Cr | "
            f"Sales: ₹{sales} Cr | "
            f"Other Income: ₹{other_income} Cr | "
            f"Industry: {industry} | Year: {data_year}"
        )

        return result

    def fetch_multiple(self, symbols: list[str]) -> list[dict]:
        """Fetch financial data for multiple stocks with rate limiting."""
        results = []
        total = len(symbols)

        for i, symbol in enumerate(symbols, 1):
            logger.info(f"[{i}/{total}] Processing {symbol}...")
            data = self.fetch_company_data(symbol)
            if data:
                results.append(data)
            else:
                logger.warning(f"[{i}/{total}] Skipped {symbol}")

            if i < total:
                time.sleep(SCREENER_REQUEST_DELAY)

        logger.info(f"Completed: {len(results)}/{total} stocks fetched")
        return results


# ─── Quick Test ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    scraper = ScreenerScraper()

    test_symbols = ["RELIANCE", "TCS", "INFY"]
    for symbol in test_symbols:
        data = scraper.fetch_company_data(symbol)
        if data:
            print(f"\n{'='*60}")
            print(f"  {data['company_name']} ({data['symbol']})")
            print(f"  Industry:      {data['industry']}")
            print(f"  Market Cap:    ₹{data['market_cap_cr']:,.0f} Cr" if data['market_cap_cr'] else "  Market Cap: N/A")
            print(f"  Data Year:     {data['data_year']}")
            print(f"  Borrowings:    ₹{data['borrowings_cr']:,.0f} Cr")
            print(f"  Sales:         ₹{data['sales_cr']:,.0f} Cr")
            print(f"  Other Income:  ₹{data['other_income_cr']:,.0f} Cr")
            print(f"  Interest:      ₹{data['interest_expense_cr']:,.0f} Cr")
            print(f"{'='*60}")
        time.sleep(SCREENER_REQUEST_DELAY)
