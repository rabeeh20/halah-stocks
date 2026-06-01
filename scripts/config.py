"""
Configuration for Halal Stock Screening Engine
Defines Shariah compliance thresholds and haram sector classifications.
"""

# ─── AAOIFI Shariah Compliance Thresholds ───────────────────────────────────────
# All ratios use Market Cap as the denominator (AAOIFI standard)

DEBT_RATIO_THRESHOLD = 5.0       # Interest-bearing Debt / Market Cap < 30%
CASH_RATIO_THRESHOLD = 30.0       # Cash + Interest-bearing Securities / Market Cap < 30%
RECEIVABLES_RATIO_THRESHOLD = 49.0  # Accounts Receivable / Market Cap < 49%
INTEREST_INCOME_THRESHOLD = 1.0   # Interest Income / Total Revenue < 5%

# ─── Compliance Score Tiers ─────────────────────────────────────────────────────
# Based on the maximum ratio value across all 4 financial screens

SCORE_TIERS = {
    5: 15.0,   # ⭐⭐⭐⭐⭐ Excellent — all ratios < 15%
    4: 20.0,   # ⭐⭐⭐⭐   Very Good — all ratios < 20%
    3: 25.0,   # ⭐⭐⭐     Good      — all ratios < 25%
    2: 30.0,   # ⭐⭐       Acceptable — all ratios < 30% (borderline)
}

# ─── Haram Sectors / Industries ─────────────────────────────────────────────────
# Stocks in these sectors are automatically excluded regardless of financials.
# Based on Screener.in's industry classification system.

HARAM_INDUSTRIES = [
    # Conventional Financial Services (Riba-based)
    "Banks",
    "Private Banks",
    "Public Banks",
    "Finance",
    "Financial Institution",
    "Financial Services",
    "Insurance",
    "General Insurance",
    "Life Insurance",
    "Housing Finance",
    "Non-Banking Financial Company (NBFC)",
    "Stock/Commodity Brokers",
    "Asset Management",
    "Holding Companies",
    
    # Alcohol
    "Breweries & Distilleries",
    "Alcoholic Beverages",
    "Breweries",
    
    # Tobacco
    "Tobacco Products",
    "Tobacco",
    "Cigarettes",
    
    # Entertainment (potentially haram)
    "Casinos & Gaming",
    "Gambling",
    
    # Weapons & Defense (controversial — being conservative)
    "Defense",
    "Aerospace & Defense",
    
    # Meat Processing (non-halal)
    "Meat & Poultry",
    "Pork Products",
]

# ─── Industries Requiring Manual Review ─────────────────────────────────────────
# These may have mixed revenue streams; flag for additional scrutiny

REVIEW_INDUSTRIES = [
    "Hotels & Restaurants",    # May serve alcohol
    "Media & Entertainment",   # May include adult content
    "Diversified",             # May have financial subsidiaries
    "Conglomerate",            # Mixed businesses
]

# ─── NSE API Configuration ──────────────────────────────────────────────────────

NSE_BASE_URL = "https://www.nseindia.com"
NSE_INDEX_URL = f"{NSE_BASE_URL}/api/equity-stockIndices"
NSE_NIFTY500_INDEX = "NIFTY 500"

NSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": f"{NSE_BASE_URL}/",
    "Connection": "keep-alive",
}

# ─── Screener.in Configuration ──────────────────────────────────────────────────

SCREENER_BASE_URL = "https://www.screener.in/company"
SCREENER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# Delay between requests to avoid being blocked (in seconds)
SCREENER_REQUEST_DELAY = 3

# ─── Screener.in Table Indices ──────────────────────────────────────────────────
# These are the indices of HTML tables on a Screener.in company page.
# Note: These may shift if Screener.in changes their layout.
# We use header matching as a fallback.

SCREENER_TABLE_NAMES = {
    "quarterly": 0,
    "profit_loss": 1,
    "balance_sheet": 2,
    "cash_flow": 3,
    "ratios": 4,
}

# ─── Balance Sheet Row Labels (Screener.in) ─────────────────────────────────────
# These are the row labels we look for in the Balance Sheet table.

BS_ROW_BORROWINGS = "Borrowings"
BS_ROW_CASH = "Cash Equivalents"
BS_ROW_RECEIVABLES = "Trade Receivables"
BS_ROW_TOTAL_ASSETS = "Total Assets"

# ─── P&L Row Labels (Screener.in) ───────────────────────────────────────────────

PL_ROW_SALES = "Sales"
PL_ROW_OTHER_INCOME = "Other Income"
PL_ROW_INTEREST = "Interest"
PL_ROW_NET_PROFIT = "Net Profit"
