"""
Full NSE Halal Screening → Excel Export
=========================================
Fetches ALL NSE-listed EQ stocks (≈2,100+), applies the existing
AAOIFI Shariah criteria, and writes a fully-formatted Excel workbook
to your Desktop.

Sheets:
  1. ✅ Halal          — passed all screens (sorted by score)
  2. ❌ Haram          — excluded (haram sector or failed ratios)
  3. ⚠️  Doubtful       — passed ratios but needs manual review
  4. ❓ Errors         — could not fetch data
  5. 📊 All Stocks     — every stock with full data & status
  6. ℹ️  Summary        — counts and screening criteria used

Runtime: ~2-3 hours for all 2,100+ EQ stocks (3 sec delay per stock).
Progress is saved automatically every 50 stocks so you can resume if
interrupted.

Usage:
    cd /Users/rabeehvailassery/Desktop/halal\ stocks/scripts
    python3 screen_all_nse_to_excel.py

    # Resume after interruption:
    python3 screen_all_nse_to_excel.py --resume

    # Quick test with 20 stocks:
    python3 screen_all_nse_to_excel.py --test
"""

import sys
import os
import io
import csv
import json
import time
import logging
import requests
import pandas as pd
from datetime import datetime, date
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# ── Import existing project modules ────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from screener_scraper import ScreenerScraper
from config import (
    DEBT_RATIO_THRESHOLD,
    CASH_RATIO_THRESHOLD,
    RECEIVABLES_RATIO_THRESHOLD,
    INTEREST_INCOME_THRESHOLD,
    SCORE_TIERS,
    HARAM_INDUSTRIES,
    REVIEW_INDUSTRIES,
    SCREENER_REQUEST_DELAY,
)

# ── Configuration ──────────────────────────────────────────────────────────────
OUTPUT_PATH      = os.path.expanduser("~/Desktop/NSE_Halal_Screening.xlsx")
PROGRESS_FILE    = os.path.expanduser("~/Desktop/nse_screen_progress.json")
NSE_EQUITY_URL   = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
SAVE_EVERY       = 50      # Save progress checkpoint every N stocks
REQUEST_DELAY    = SCREENER_REQUEST_DELAY   # seconds between requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.expanduser("~/Desktop/nse_screen.log"), mode="a"),
    ]
)
logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# STEP 1 — Fetch full NSE EQ stock list
# ══════════════════════════════════════════════════════════════════════════════

def fetch_all_nse_eq_stocks() -> list[dict]:
    """Download EQUITY_L.csv from NSE and return EQ-series stocks only."""
    logger.info("Fetching complete NSE equity list...")

    browser_headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }

    session = requests.Session()
    session.headers.update(browser_headers)

    # ── Proper two-step NSE session warmup ────────────────────────────────
    try:
        logger.info("  Warming up NSE session (step 1/2)...")
        r1 = session.get("https://www.nseindia.com", timeout=20, allow_redirects=True)
        logger.info(f"  Homepage: {r1.status_code}, cookies: {list(session.cookies.keys())}")
        time.sleep(3)

        logger.info("  Warming up NSE session (step 2/2)...")
        r2 = session.get(
            "https://www.nseindia.com/market-data/securities-available-for-trading",
            timeout=20, allow_redirects=True
        )
        logger.info(f"  Market page: {r2.status_code}")
        time.sleep(2)
    except Exception as e:
        logger.warning(f"  Session warmup issue: {e}")

    # ── Try downloading EQUITY_L.csv ──────────────────────────────────────
    stocks = []
    for url in [
        "https://archives.nseindia.com/content/equities/EQUITY_L.csv",
        "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv",
    ]:
        try:
            logger.info(f"  Downloading from: {url}")
            r = session.get(url, timeout=30)
            if r.status_code != 200:
                logger.warning(f"  Got {r.status_code}, trying next...")
                continue

            content = r.text.strip()
            if not content or len(content) < 100:
                logger.warning("  Empty response, trying next...")
                continue

            reader = csv.DictReader(io.StringIO(content))
            for row in reader:
                series = (row.get("SERIES") or "").strip()
                symbol = (row.get("SYMBOL") or "").strip()
                name   = (row.get("NAME OF COMPANY") or "").strip()
                if series == "EQ" and symbol:
                    stocks.append({
                        "symbol":       symbol,
                        "company_name": name,
                        "series":       series,
                        "isin":         (row.get("ISIN NUMBER") or "").strip(),
                        "face_value":   (row.get("FACE VALUE") or "").strip(),
                        "date_listed":  (row.get("DATE OF LISTING") or "").strip(),
                    })
            if stocks:
                logger.info(f"  ✅ Got {len(stocks):,} EQ stocks from NSE CSV")
                return stocks
        except Exception as e:
            logger.warning(f"  URL failed: {e}")

    # ── Fallback: Use the local file we already downloaded ────────────────
    local_excel = os.path.expanduser("~/Desktop/NSE_All_Stocks.xlsx")
    if os.path.exists(local_excel):
        logger.info(f"  Using local file: {local_excel}")
        df = pd.read_excel(local_excel)
        df.columns = [c.strip() for c in df.columns]
        for _, row in df.iterrows():
            series = str(row.get("SERIES") or "").strip()
            symbol = str(row.get("SYMBOL") or "").strip()
            name   = str(row.get("NAME OF COMPANY") or "").strip()
            if series == "EQ" and symbol:
                stocks.append({
                    "symbol":       symbol,
                    "company_name": name,
                    "series":       series,
                    "isin":         str(row.get("ISIN NUMBER") or "").strip(),
                    "face_value":   str(row.get("FACE VALUE") or "").strip(),
                    "date_listed":  str(row.get("DATE OF LISTING") or "").strip(),
                })
        if stocks:
            logger.info(f"  ✅ Loaded {len(stocks):,} EQ stocks from local Excel file")
            return stocks

    # ── Final fallback: use the previously downloaded CSV via export script ─
    logger.error("  All sources failed! Run export_all_nse_stocks.py first to create NSE_All_Stocks.xlsx")
    raise RuntimeError("Cannot fetch NSE stock list. Run export_all_nse_stocks.py first.")


# ══════════════════════════════════════════════════════════════════════════════
# STEP 2 — Shariah Screening (same logic as your existing screener)
# ══════════════════════════════════════════════════════════════════════════════

def check_business_activity(industry: str) -> dict:
    if not industry:
        return {"passed": True, "reason": "Industry unknown", "needs_review": True}
    for haram in HARAM_INDUSTRIES:
        if haram.lower() in industry.lower():
            return {"passed": False, "reason": f"Haram sector: {industry}", "needs_review": False}
    for review in REVIEW_INDUSTRIES:
        if review.lower() in industry.lower():
            return {"passed": True, "reason": f"Needs review: {industry}", "needs_review": True}
    return {"passed": True, "reason": "Permissible sector", "needs_review": False}


def check_financial_ratios(data: dict) -> dict:
    market_cap  = data.get("market_cap_cr", 0) or 0
    borrowings  = data.get("borrowings_cr", 0) or 0
    cash        = data.get("cash_cr", 0) or 0
    receivables = data.get("receivables_cr", 0) or 0
    sales       = data.get("sales_cr", 0) or 0
    other_income= data.get("other_income_cr", 0) or 0

    if market_cap <= 0:
        return {
            "passed": False,
            "reason": "Market cap unavailable",
            "debt_ratio": None, "cash_ratio": None,
            "receivables_ratio": None, "interest_income_ratio": None,
        }

    debt_ratio  = (borrowings   / market_cap) * 100
    cash_ratio  = (cash         / market_cap) * 100
    recv_ratio  = (receivables  / market_cap) * 100
    int_ratio   = (other_income / sales) * 100 if sales > 0 else 0.0

    failures = []
    if debt_ratio  >= DEBT_RATIO_THRESHOLD:         failures.append(f"Debt {debt_ratio:.1f}%>={DEBT_RATIO_THRESHOLD}%")
    if cash_ratio  >= CASH_RATIO_THRESHOLD:         failures.append(f"Cash {cash_ratio:.1f}%>={CASH_RATIO_THRESHOLD}%")
    if recv_ratio  >= RECEIVABLES_RATIO_THRESHOLD:  failures.append(f"Recv {recv_ratio:.1f}%>={RECEIVABLES_RATIO_THRESHOLD}%")
    if int_ratio   >= INTEREST_INCOME_THRESHOLD:    failures.append(f"Interest {int_ratio:.1f}%>={INTEREST_INCOME_THRESHOLD}%")

    return {
        "passed": len(failures) == 0,
        "reason": "; ".join(failures) if failures else "All ratios within limits",
        "debt_ratio":            round(debt_ratio, 2),
        "cash_ratio":            round(cash_ratio, 2),
        "receivables_ratio":     round(recv_ratio, 2),
        "interest_income_ratio": round(int_ratio, 2),
    }


def calculate_score(ratios: dict) -> int:
    values = [
        ratios.get("debt_ratio") or 0,
        ratios.get("cash_ratio") or 0,
        ratios.get("receivables_ratio") or 0,
        ratios.get("interest_income_ratio") or 0,
    ]
    max_ratio = max(values)
    for score, threshold in sorted(SCORE_TIERS.items(), reverse=True):
        if max_ratio < threshold:
            return score
    return 1


def screen_stock(financial_data: dict) -> dict:
    symbol   = financial_data.get("symbol", "")
    industry = financial_data.get("industry", "") or ""

    biz = check_business_activity(industry)
    if not biz["passed"]:
        return {
            "symbol": symbol, "company_name": financial_data.get("company_name"),
            "industry": industry, "status": "HARAM", "compliance_score": 0,
            "reason": biz["reason"], "needs_review": False,
            "debt_ratio": None, "cash_ratio": None,
            "receivables_ratio": None, "interest_income_ratio": None,
            "purification_pct": 0, "screening_date": date.today().isoformat(),
            "market_cap_cr": financial_data.get("market_cap_cr"),
            "borrowings_cr": financial_data.get("borrowings_cr"),
            "cash_cr": financial_data.get("cash_cr"),
            "receivables_cr": financial_data.get("receivables_cr"),
            "sales_cr": financial_data.get("sales_cr"),
            "other_income_cr": financial_data.get("other_income_cr"),
            "data_year": financial_data.get("data_year"),
        }

    ratios = check_financial_ratios(financial_data)
    sales        = financial_data.get("sales_cr", 0) or 0
    other_income = financial_data.get("other_income_cr", 0) or 0
    purification = round((other_income / sales) * 100, 2) if sales > 0 else 0

    if not ratios["passed"]:
        status, score = "HARAM", 0
    elif biz.get("needs_review"):
        status, score = "DOUBTFUL", calculate_score(ratios)
    else:
        status, score = "HALAL", calculate_score(ratios)

    return {
        "symbol": symbol, "company_name": financial_data.get("company_name"),
        "industry": industry, "status": status, "compliance_score": score,
        "reason": ratios["reason"] if status != "HALAL" else "Shariah compliant",
        "needs_review": biz.get("needs_review", False),
        "debt_ratio":             ratios.get("debt_ratio"),
        "cash_ratio":             ratios.get("cash_ratio"),
        "receivables_ratio":      ratios.get("receivables_ratio"),
        "interest_income_ratio":  ratios.get("interest_income_ratio"),
        "purification_pct": purification,
        "screening_date": date.today().isoformat(),
        "market_cap_cr": financial_data.get("market_cap_cr"),
        "borrowings_cr": financial_data.get("borrowings_cr"),
        "cash_cr": financial_data.get("cash_cr"),
        "receivables_cr": financial_data.get("receivables_cr"),
        "sales_cr": financial_data.get("sales_cr"),
        "other_income_cr": financial_data.get("other_income_cr"),
        "data_year": financial_data.get("data_year"),
    }


# ══════════════════════════════════════════════════════════════════════════════
# STEP 3 — Run the screening loop with progress saving
# ══════════════════════════════════════════════════════════════════════════════

def load_progress() -> dict:
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {"completed": [], "results": []}


def save_progress(completed_symbols: list, results: list):
    with open(PROGRESS_FILE, "w") as f:
        json.dump({"completed": completed_symbols, "results": results}, f)


def run_screening(stocks: list[dict], resume: bool = False) -> list[dict]:
    scraper = ScreenerScraper()
    progress = load_progress() if resume else {"completed": [], "results": []}
    completed   = set(progress["completed"])
    all_results = progress["results"]

    # Filter out already-done stocks
    pending = [s for s in stocks if s["symbol"] not in completed]
    total   = len(stocks)
    done    = len(completed)

    logger.info(f"Total stocks: {total} | Already done: {done} | Remaining: {len(pending)}")

    for i, stock in enumerate(pending, start=done + 1):
        symbol = stock["symbol"]
        logger.info(f"[{i}/{total}] Screening {symbol}...")

        try:
            fin_data = scraper.fetch_company_data(symbol)
            if fin_data:
                # Merge NSE info (ISIN, listing date etc.) into result
                result = screen_stock(fin_data)
                result["isin"]        = stock.get("isin", "")
                result["date_listed"] = stock.get("date_listed", "")
            else:
                result = {
                    "symbol": symbol,
                    "company_name": stock.get("company_name", ""),
                    "industry": "",
                    "status": "ERROR",
                    "compliance_score": 0,
                    "reason": "Could not fetch data from Screener.in",
                    "needs_review": False,
                    "isin": stock.get("isin", ""),
                    "date_listed": stock.get("date_listed", ""),
                    "screening_date": date.today().isoformat(),
                    "debt_ratio": None, "cash_ratio": None,
                    "receivables_ratio": None, "interest_income_ratio": None,
                    "purification_pct": 0,
                    "market_cap_cr": None, "borrowings_cr": None,
                    "cash_cr": None, "receivables_cr": None,
                    "sales_cr": None, "other_income_cr": None, "data_year": None,
                }

            all_results.append(result)
            completed.add(symbol)

            stars = "⭐" * result["compliance_score"] if result["compliance_score"] > 0 else ""
            logger.info(f"  → {result['status']} {stars} | {result.get('reason', '')}")

        except Exception as e:
            logger.error(f"  → ERROR for {symbol}: {e}")
            all_results.append({
                "symbol": symbol,
                "company_name": stock.get("company_name", ""),
                "industry": "", "status": "ERROR", "compliance_score": 0,
                "reason": str(e), "needs_review": False,
                "isin": stock.get("isin", ""), "date_listed": stock.get("date_listed", ""),
                "screening_date": date.today().isoformat(),
                "debt_ratio": None, "cash_ratio": None,
                "receivables_ratio": None, "interest_income_ratio": None,
                "purification_pct": 0,
                "market_cap_cr": None, "borrowings_cr": None,
                "cash_cr": None, "receivables_cr": None,
                "sales_cr": None, "other_income_cr": None, "data_year": None,
            })
            completed.add(symbol)

        # Save progress every SAVE_EVERY stocks
        if i % SAVE_EVERY == 0:
            save_progress(list(completed), all_results)
            logger.info(f"  💾 Progress saved ({i}/{total} done)")

        if i < total:
            time.sleep(REQUEST_DELAY)

    # Final save
    save_progress(list(completed), all_results)
    return all_results


# ══════════════════════════════════════════════════════════════════════════════
# STEP 4 — Write Excel workbook
# ══════════════════════════════════════════════════════════════════════════════

COLUMNS = [
    ("Symbol",              "symbol"),
    ("Company Name",        "company_name"),
    ("Industry",            "industry"),
    ("Status",              "status"),
    ("Score (★)",           "compliance_score"),
    ("Reason",              "reason"),
    ("Debt Ratio %",        "debt_ratio"),
    ("Cash Ratio %",        "cash_ratio"),
    ("Receivables Ratio %", "receivables_ratio"),
    ("Interest Income %",   "interest_income_ratio"),
    ("Purification %",      "purification_pct"),
    ("Market Cap (₹Cr)",    "market_cap_cr"),
    ("Borrowings (₹Cr)",    "borrowings_cr"),
    ("Sales (₹Cr)",         "sales_cr"),
    ("Other Income (₹Cr)",  "other_income_cr"),
    ("Data Year",           "data_year"),
    ("ISIN",                "isin"),
    ("Date Listed",         "date_listed"),
    ("Needs Review",        "needs_review"),
    ("Screened On",         "screening_date"),
]

STATUS_COLORS = {
    "HALAL":    "E8F5E9",   # light green
    "HARAM":    "FFEBEE",   # light red
    "DOUBTFUL": "FFF8E1",   # light amber
    "ERROR":    "F5F5F5",   # light grey
}

HEADER_COLORS = {
    "HALAL":    "2E7D32",   # dark green
    "HARAM":    "C62828",   # dark red
    "DOUBTFUL": "F57F17",   # dark amber
    "ERROR":    "546E7A",   # dark grey
    "ALL":      "1F4E79",   # navy
    "SUMMARY":  "4A148C",   # purple
}


def _style_header_row(ws, header_color: str):
    thin = Side(style="thin", color="CCCCCC")
    for cell in ws[1]:
        cell.font      = Font(bold=True, color="FFFFFF", size=10)
        cell.fill      = PatternFill(start_color=header_color, end_color=header_color, fill_type="solid")
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border    = Border(bottom=Side(style="medium", color="FFFFFF"))
    ws.row_dimensions[1].height = 28


def _auto_width(ws, df: pd.DataFrame):
    for i, col in enumerate(df.columns, start=1):
        max_len = max(len(str(col)), df[col].astype(str).str.len().max() if not df[col].empty else 0)
        ws.column_dimensions[get_column_letter(i)].width = min(max_len + 3, 40)


def _color_status_rows(ws, df: pd.DataFrame):
    """Color entire rows based on status column."""
    if "Status" not in df.columns:
        return
    status_col_idx = list(df.columns).index("Status") + 1  # 1-indexed
    for row_idx, status_val in enumerate(df["Status"], start=2):  # data starts row 2
        row_color = STATUS_COLORS.get(str(status_val), "FFFFFF")
        fill = PatternFill(start_color=row_color, end_color=row_color, fill_type="solid")
        for col_idx in range(1, len(df.columns) + 1):
            ws.cell(row=row_idx, column=col_idx).fill = fill


def _score_stars(score):
    if isinstance(score, int) and score > 0:
        return "★" * score + "☆" * (5 - score)
    return ""


def results_to_df(results: list[dict]) -> pd.DataFrame:
    headers = [h for h, _ in COLUMNS]
    keys    = [k for _, k in COLUMNS]
    rows = []
    for r in results:
        row = []
        for h, k in COLUMNS:
            val = r.get(k)
            if k == "compliance_score":
                row.append(_score_stars(val) if val else "")
            elif k == "needs_review":
                row.append("Yes" if val else "No")
            elif isinstance(val, float):
                row.append(round(val, 2))
            elif val is None:
                row.append("")
            else:
                row.append(val)
        rows.append(row)
    return pd.DataFrame(rows, columns=headers)


def write_sheet(writer, sheet_name: str, df: pd.DataFrame, header_color: str, color_rows: bool = False):
    df.to_excel(writer, sheet_name=sheet_name, index=False)
    ws = writer.sheets[sheet_name]
    _style_header_row(ws, header_color)
    _auto_width(ws, df)
    ws.freeze_panes = "A2"
    if color_rows:
        _color_status_rows(ws, df)


def write_summary_sheet(writer, results: list[dict], run_time: str):
    halal    = [r for r in results if r["status"] == "HALAL"]
    haram    = [r for r in results if r["status"] == "HARAM"]
    doubtful = [r for r in results if r["status"] == "DOUBTFUL"]
    errors   = [r for r in results if r["status"] == "ERROR"]

    rows = [
        ["NSE COMPLETE HALAL SCREENING REPORT", ""],
        ["", ""],
        ["Screening Date",          date.today().strftime("%d %B %Y")],
        ["Run Time",                run_time],
        ["", ""],
        ["RESULTS SUMMARY",         ""],
        ["Total Stocks Screened",   len(results)],
        ["✅  Halal",                len(halal)],
        ["❌  Haram",                len(haram)],
        ["⚠️   Doubtful",            len(doubtful)],
        ["❓  Errors / No Data",     len(errors)],
        ["", ""],
        ["SHARIAH CRITERIA USED (AAOIFI Standard)", ""],
        ["Debt Ratio Threshold",         f"< {DEBT_RATIO_THRESHOLD}% of Market Cap"],
        ["Cash Ratio Threshold",         f"< {CASH_RATIO_THRESHOLD}% of Market Cap"],
        ["Receivables Ratio Threshold",  f"< {RECEIVABLES_RATIO_THRESHOLD}% of Market Cap"],
        ["Interest Income Threshold",    f"< {INTEREST_INCOME_THRESHOLD}% of Total Revenue"],
        ["", ""],
        ["SCORE TIERS",               ""],
        ["★★★★★  (5 stars)",           "All ratios < 15%"],
        ["★★★★☆  (4 stars)",           "All ratios < 20%"],
        ["★★★☆☆  (3 stars)",           "All ratios < 25%"],
        ["★★☆☆☆  (2 stars)",           "All ratios < 30% (borderline)"],
        ["★☆☆☆☆  (1 star)",            "Passed but close to limits"],
        ["", ""],
        ["HARAM SECTORS EXCLUDED",    ""],
    ]
    for sector in HARAM_INDUSTRIES:
        rows.append(["", sector])

    df = pd.DataFrame(rows, columns=["Field", "Value"])
    df.to_excel(writer, sheet_name="ℹ️ Summary", index=False)
    ws = writer.sheets["ℹ️ Summary"]
    _style_header_row(ws, HEADER_COLORS["SUMMARY"])

    # Style section headers bold
    for row in ws.iter_rows(min_row=2):
        val = str(row[0].value or "")
        if val.isupper() or val.startswith("NSE "):
            for cell in row:
                cell.font = Font(bold=True, size=11)

    ws.column_dimensions["A"].width = 35
    ws.column_dimensions["B"].width = 50
    ws.freeze_panes = "A2"


def export_to_excel(results: list[dict], start_time: datetime):
    run_time = str(datetime.now() - start_time).split(".")[0]
    halal    = sorted([r for r in results if r["status"] == "HALAL"],    key=lambda x: -(x.get("compliance_score") or 0))
    haram    = [r for r in results if r["status"] == "HARAM"]
    doubtful = [r for r in results if r["status"] == "DOUBTFUL"]
    errors   = [r for r in results if r["status"] == "ERROR"]

    logger.info(f"\nWriting Excel: {OUTPUT_PATH}")
    logger.info(f"  Halal: {len(halal)} | Haram: {len(haram)} | Doubtful: {len(doubtful)} | Errors: {len(errors)}")

    with pd.ExcelWriter(OUTPUT_PATH, engine="openpyxl") as writer:
        # Sheet 1: Halal
        write_sheet(writer, "✅ Halal", results_to_df(halal), HEADER_COLORS["HALAL"])
        # Sheet 2: Haram
        write_sheet(writer, "❌ Haram", results_to_df(haram), HEADER_COLORS["HARAM"])
        # Sheet 3: Doubtful
        write_sheet(writer, "⚠️ Doubtful", results_to_df(doubtful), HEADER_COLORS["DOUBTFUL"])
        # Sheet 4: Errors
        write_sheet(writer, "❓ Errors", results_to_df(errors), HEADER_COLORS["ERROR"])
        # Sheet 5: All Stocks
        write_sheet(writer, "📊 All Stocks", results_to_df(results), HEADER_COLORS["ALL"], color_rows=True)
        # Sheet 6: Summary
        write_summary_sheet(writer, results, run_time)

    logger.info(f"✅ Excel saved: {OUTPUT_PATH}")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main():
    args    = sys.argv[1:]
    resume  = "--resume" in args
    test    = "--test" in args

    start_time = datetime.now()

    print("\n" + "=" * 65)
    print("  🕌  NSE COMPLETE HALAL STOCK SCREENING")
    print(f"  📅  {start_time.strftime('%d %B %Y, %I:%M %p')}")
    print("=" * 65)

    if test:
        print("\n  ⚡ TEST MODE — screening 20 stocks only\n")
    elif resume:
        print("\n  🔄 RESUME MODE — continuing from last checkpoint\n")
    else:
        print("\n  ⏱️  Full run ≈ 2–3 hours for ~2,100 stocks")
        print("  💾 Progress auto-saves every 50 stocks")
        print("  🔄 If interrupted, run with --resume to continue\n")

    # ── Fetch NSE list ────────────────────────────────────────────────────
    stocks = fetch_all_nse_eq_stocks()

    if test:
        stocks = stocks[:20]

    print(f"  📈 Stocks to screen: {len(stocks):,}\n")
    print("  Criteria:")
    print(f"    Debt Ratio        < {DEBT_RATIO_THRESHOLD}% of Mkt Cap")
    print(f"    Cash Ratio        < {CASH_RATIO_THRESHOLD}% of Mkt Cap")
    print(f"    Receivables Ratio < {RECEIVABLES_RATIO_THRESHOLD}% of Mkt Cap")
    print(f"    Interest Income   < {INTEREST_INCOME_THRESHOLD}% of Revenue")
    print(f"    Haram sectors     : {len(HARAM_INDUSTRIES)} excluded\n")
    print("=" * 65 + "\n")

    # ── Run screening ─────────────────────────────────────────────────────
    results = run_screening(stocks, resume=resume)

    # ── Export to Excel ───────────────────────────────────────────────────
    export_to_excel(results, start_time)

    # ── Final summary ─────────────────────────────────────────────────────
    halal    = sum(1 for r in results if r["status"] == "HALAL")
    haram    = sum(1 for r in results if r["status"] == "HARAM")
    doubtful = sum(1 for r in results if r["status"] == "DOUBTFUL")
    errors   = sum(1 for r in results if r["status"] == "ERROR")

    print("\n" + "=" * 65)
    print("  ✅  SCREENING COMPLETE")
    print(f"  Total screened : {len(results):,}")
    print(f"  ✅  Halal        : {halal:,}")
    print(f"  ❌  Haram        : {haram:,}")
    print(f"  ⚠️   Doubtful     : {doubtful:,}")
    print(f"  ❓  Errors       : {errors:,}")
    print(f"\n  📁  Excel saved  : {OUTPUT_PATH}")
    print("=" * 65 + "\n")

    # Clean up progress file after successful completion
    if not test and os.path.exists(PROGRESS_FILE):
        os.remove(PROGRESS_FILE)
        logger.info("Progress file cleaned up.")


if __name__ == "__main__":
    main()
