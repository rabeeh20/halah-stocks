"""
Shariah Screening Engine
Takes financial data from Screener.in and applies AAOIFI-standard
Shariah compliance rules to determine if a stock is Halal.
"""

import json
import logging
import os
import time
from datetime import date
from typing import Optional

from screener_scraper import ScreenerScraper
from nse_market_data import NSEClient
from config import (
    DEBT_RATIO_THRESHOLD,
    CASH_RATIO_THRESHOLD,
    RECEIVABLES_RATIO_THRESHOLD,
    INTEREST_INCOME_THRESHOLD,
    SCORE_TIERS,
    HARAM_INDUSTRIES,
    REVIEW_INDUSTRIES,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


class ShariahScreener:
    """Applies AAOIFI Shariah compliance rules to stock financial data."""

    def __init__(self):
        self.scraper = ScreenerScraper()
        self.nse_client = NSEClient()

    def _check_business_activity(self, industry: str) -> dict:
        """
        Step 1: Business Activity Screen.
        Checks if the company's industry is in a prohibited sector.
        """
        if not industry:
            return {
                "passed": True,
                "reason": "Industry not identified — defaults to permissible",
                "needs_review": True,
            }

        industry_clean = industry.strip()

        # Check against haram industries
        for haram in HARAM_INDUSTRIES:
            if haram.lower() in industry_clean.lower():
                return {
                    "passed": False,
                    "reason": f"Excluded sector: {industry_clean}",
                    "needs_review": False,
                }

        # Check if manual review needed
        for review in REVIEW_INDUSTRIES:
            if review.lower() in industry_clean.lower():
                return {
                    "passed": True,
                    "reason": f"Needs manual review: {industry_clean}",
                    "needs_review": True,
                }

        return {
            "passed": True,
            "reason": "Permissible sector",
            "needs_review": False,
        }

    def _check_financial_ratios(self, data: dict) -> dict:
        """
        Step 2: Financial Ratio Screen.
        Applies AAOIFI thresholds using Market Cap as denominator.
        """
        market_cap = data.get("market_cap_cr", 0) or 0
        borrowings = data.get("borrowings_cr", 0) or 0
        cash = data.get("cash_cr", 0) or 0
        receivables = data.get("receivables_cr", 0) or 0
        sales = data.get("sales_cr", 0) or 0
        other_income = data.get("other_income_cr", 0) or 0

        # Cannot compute ratios without market cap
        if market_cap <= 0:
            return {
                "passed": False,
                "reason": "Market cap unavailable — cannot compute ratios",
                "debt_ratio": None,
                "cash_ratio": None,
                "receivables_ratio": None,
                "interest_income_ratio": None,
            }

        # Calculate ratios
        debt_ratio = (borrowings / market_cap) * 100
        cash_ratio = (cash / market_cap) * 100
        recv_ratio = (receivables / market_cap) * 100

        # Interest income ratio uses Sales as denominator
        interest_ratio = 0.0
        if sales > 0:
            interest_ratio = (other_income / sales) * 100

        # Check thresholds
        debt_pass = debt_ratio < DEBT_RATIO_THRESHOLD
        cash_pass = cash_ratio < CASH_RATIO_THRESHOLD
        recv_pass = recv_ratio < RECEIVABLES_RATIO_THRESHOLD
        interest_pass = interest_ratio < INTEREST_INCOME_THRESHOLD

        all_pass = debt_pass and cash_pass and recv_pass and interest_pass

        failures = []
        if not debt_pass:
            failures.append(f"Debt ratio {debt_ratio:.1f}% >= {DEBT_RATIO_THRESHOLD}%")
        if not cash_pass:
            failures.append(f"Cash ratio {cash_ratio:.1f}% >= {CASH_RATIO_THRESHOLD}%")
        if not recv_pass:
            failures.append(f"Receivables ratio {recv_ratio:.1f}% >= {RECEIVABLES_RATIO_THRESHOLD}%")
        if not interest_pass:
            failures.append(f"Interest income ratio {interest_ratio:.1f}% >= {INTEREST_INCOME_THRESHOLD}%")

        return {
            "passed": all_pass,
            "reason": "All ratios within limits" if all_pass else "; ".join(failures),
            "debt_ratio": round(debt_ratio, 2),
            "cash_ratio": round(cash_ratio, 2),
            "receivables_ratio": round(recv_ratio, 2),
            "interest_income_ratio": round(interest_ratio, 2),
        }

    def _calculate_score(self, ratios: dict) -> int:
        """
        Step 3: Calculate compliance score (1-5 stars).
        Based on the maximum ratio value across all screens.
        """
        values = [
            ratios.get("debt_ratio", 0) or 0,
            ratios.get("cash_ratio", 0) or 0,
            ratios.get("receivables_ratio", 0) or 0,
            ratios.get("interest_income_ratio", 0) or 0,
        ]
        max_ratio = max(values)

        for score, threshold in sorted(SCORE_TIERS.items(), reverse=True):
            if max_ratio < threshold:
                return score

        return 1  # Minimum score if borderline

    def screen_stock(self, financial_data: dict) -> dict:
        """
        Run full Shariah screening on a single stock.
        
        Args:
            financial_data: Dictionary from ScreenerScraper.fetch_company_data()
        
        Returns:
            Complete screening result dictionary.
        """
        symbol = financial_data.get("symbol", "UNKNOWN")

        # Step 1: Business Activity Screen
        industry = financial_data.get("industry", "")
        business_result = self._check_business_activity(industry)

        if not business_result["passed"]:
            return {
                "symbol": symbol,
                "company_name": financial_data.get("company_name"),
                "industry": industry,
                "status": "HARAM",
                "compliance_score": 0,
                "reason": business_result["reason"],
                "needs_review": False,
                "debt_ratio": None,
                "cash_ratio": None,
                "receivables_ratio": None,
                "interest_income_ratio": None,
                "purification_pct": 0,
                "screening_date": date.today().isoformat(),
                **{k: financial_data.get(k) for k in [
                    "market_cap_cr", "borrowings_cr", "cash_cr",
                    "receivables_cr", "sales_cr", "other_income_cr", "data_year"
                ]},
            }

        # Step 2: Financial Ratio Screen
        ratio_result = self._check_financial_ratios(financial_data)

        if not ratio_result["passed"]:
            status = "HARAM"
            score = 0
        elif business_result.get("needs_review"):
            status = "DOUBTFUL"
            score = self._calculate_score(ratio_result)
        else:
            status = "HALAL"
            score = self._calculate_score(ratio_result)

        # Calculate purification percentage
        # (Other Income / Sales) — the % of dividends that should be donated
        sales = financial_data.get("sales_cr", 0) or 0
        other_income = financial_data.get("other_income_cr", 0) or 0
        purification_pct = round((other_income / sales) * 100, 2) if sales > 0 else 0

        return {
            "symbol": symbol,
            "company_name": financial_data.get("company_name"),
            "industry": industry,
            "status": status,
            "compliance_score": score,
            "reason": ratio_result["reason"] if status != "HALAL" else "Shariah compliant",
            "needs_review": business_result.get("needs_review", False),
            "debt_ratio": ratio_result.get("debt_ratio"),
            "cash_ratio": ratio_result.get("cash_ratio"),
            "receivables_ratio": ratio_result.get("receivables_ratio"),
            "interest_income_ratio": ratio_result.get("interest_income_ratio"),
            "purification_pct": purification_pct,
            "screening_date": date.today().isoformat(),
            **{k: financial_data.get(k) for k in [
                "market_cap_cr", "borrowings_cr", "cash_cr",
                "receivables_cr", "sales_cr", "other_income_cr", "data_year"
            ]},
        }

    def run_full_screening(self, symbols: Optional[list[str]] = None) -> dict:
        """
        Run full Shariah screening on all Nifty 500 stocks (or a given list).
        
        Args:
            symbols: Optional list of symbols. If None, fetches Nifty 500 from NSE.
        
        Returns:
            Dictionary with 'halal', 'haram', 'doubtful' lists and summary stats.
        """
        # Step 0: Get stock universe
        if symbols is None:
            logger.info("Fetching Nifty 500 stock list from NSE...")
            symbols = self.nse_client.get_nifty500_symbols()
            if not symbols:
                logger.error("Failed to fetch Nifty 500 symbols from NSE")
                return {"error": "Failed to fetch stock universe"}
            logger.info(f"Got {len(symbols)} stocks from Nifty 500")

        # Step 1: Fetch financial data from Screener.in
        logger.info(f"Fetching financial data for {len(symbols)} stocks from Screener.in...")
        financial_data_list = self.scraper.fetch_multiple(symbols)

        # Step 2: Screen each stock
        logger.info("Running Shariah screening...")
        halal = []
        haram = []
        doubtful = []
        errors = []

        for data in financial_data_list:
            result = self.screen_stock(data)
            status = result["status"]

            if status == "HALAL":
                halal.append(result)
            elif status == "HARAM":
                haram.append(result)
            else:
                doubtful.append(result)

            # Log status
            score_display = "⭐" * result["compliance_score"] if result["compliance_score"] > 0 else "❌"
            logger.info(f"  [{result['symbol']}] {status} {score_display}")

        # Summary
        total = len(financial_data_list)
        summary = {
            "screening_date": date.today().isoformat(),
            "total_screened": total,
            "halal_count": len(halal),
            "haram_count": len(haram),
            "doubtful_count": len(doubtful),
            "error_count": len(symbols) - total,
            "halal": sorted(halal, key=lambda x: x.get("compliance_score", 0), reverse=True),
            "haram": haram,
            "doubtful": doubtful,
        }

        logger.info(f"\n{'='*60}")
        logger.info(f"  SCREENING COMPLETE")
        logger.info(f"  Total Screened: {total}")
        logger.info(f"  ✅ Halal:    {len(halal)}")
        logger.info(f"  ❌ Haram:    {len(haram)}")
        logger.info(f"  ⚠️  Doubtful: {len(doubtful)}")
        logger.info(f"  ❓ Errors:   {len(symbols) - total}")
        logger.info(f"{'='*60}")

        return summary


def save_results(results: dict, output_dir: str = "../data"):
    """Save screening results to JSON files."""
    os.makedirs(output_dir, exist_ok=True)

    # Save full results
    output_path = os.path.join(output_dir, "screening_results.json")
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    logger.info(f"Full results saved to {output_path}")

    # Save halal-only list (for frontend consumption)
    halal_path = os.path.join(output_dir, "halal_stocks.json")
    halal_data = {
        "screening_date": results.get("screening_date"),
        "total_halal": results.get("halal_count"),
        "stocks": results.get("halal", []),
    }
    with open(halal_path, "w") as f:
        json.dump(halal_data, f, indent=2, default=str)
    logger.info(f"Halal stocks saved to {halal_path}")


# ─── Main Entry Point ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    screener = ShariahScreener()

    # Check for command-line arguments
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        # Test mode: screen only a few stocks
        test_symbols = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ITC", "COALINDIA"]
        print(f"\n🧪 TEST MODE: Screening {len(test_symbols)} stocks\n")
        results = screener.run_full_screening(test_symbols)
    else:
        # Full mode: screen all Nifty 500
        print(f"\n🕌 FULL SCREENING: Nifty 500 stocks\n")
        results = screener.run_full_screening()

    # Save results
    save_results(results, output_dir=os.path.join(os.path.dirname(__file__), "..", "data"))

    # Print halal stocks summary
    if results.get("halal"):
        print(f"\n✅ HALAL STOCKS ({len(results['halal'])})")
        print(f"{'SYMBOL':<15} {'SCORE':<8} {'DEBT%':>8} {'CASH%':>8} {'RECV%':>8} {'INT%':>8}")
        print("-" * 65)
        for stock in results["halal"][:30]:  # Show top 30
            score = "⭐" * stock["compliance_score"]
            print(
                f"{stock['symbol']:<15} {score:<8} "
                f"{stock['debt_ratio'] or 0:>7.1f}% "
                f"{stock['cash_ratio'] or 0:>7.1f}% "
                f"{stock['receivables_ratio'] or 0:>7.1f}% "
                f"{stock['interest_income_ratio'] or 0:>7.1f}%"
            )
