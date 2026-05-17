/**
 * API Route: /api/stocks
 * 
 * Fetches LIVE market data from NSE India API for Nifty 500 stocks,
 * then merges it with our Shariah screening results.
 * 
 * Data flow:
 *   1. Read halal_stocks.json (Shariah compliance data)
 *   2. Fetch live OHLC data from NSE API (prices, volume, change%)
 *   3. Merge: only return stocks that are in our halal list WITH live prices
 *   4. Fallback: if NSE is down, return screening data only
 */

import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";

const NSE_BASE_URL = "https://www.nseindia.com";
const NSE_INDEX_URL = `${NSE_BASE_URL}/api/equity-stockIndices`;

const NSE_BROWSER_HEADERS = {
  "User-Agent":
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
  Accept:
    "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
  "Accept-Language": "en-US,en;q=0.9",
  "Sec-Fetch-Dest": "document",
  "Sec-Fetch-Mode": "navigate",
  "Sec-Fetch-Site": "none",
  "Sec-Fetch-User": "?1",
  "Upgrade-Insecure-Requests": "1",
};

const NSE_API_HEADERS = {
  "User-Agent":
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
  Accept: "application/json, text/plain, */*",
  "Accept-Language": "en-US,en;q=0.9",
  Referer: `${NSE_BASE_URL}/market-data/live-equity-market`,
  "X-Requested-With": "XMLHttpRequest",
  "Sec-Fetch-Dest": "empty",
  "Sec-Fetch-Mode": "cors",
  "Sec-Fetch-Site": "same-origin",
};

// ── Cache to avoid hammering NSE ──────────────────────────────────────────
let cachedData = null;
let cacheTimestamp = 0;
const CACHE_TTL = 60 * 1000; // 1 minute cache

// Store session cookies across requests
let sessionCookies = "";
let cookieTimestamp = 0;
const COOKIE_TTL = 5 * 60 * 1000; // 5 minute cookie TTL

/**
 * Initialize NSE session with 2-step warmup:
 * 1. Visit homepage (may 403 but sets Akamai cookies)
 * 2. Visit market data page (builds session trust)
 */
async function initNSESession() {
  const now = Date.now();
  if (sessionCookies && now - cookieTimestamp < COOKIE_TTL) {
    return sessionCookies;
  }

  try {
    // Step 1: Visit homepage - may return 403 but sets cookies
    const r1 = await fetch(NSE_BASE_URL, {
      headers: NSE_BROWSER_HEADERS,
      redirect: "follow",
    });
    const cookies1 = r1.headers.getSetCookie?.() || [];
    let allCookies = cookies1.map((c) => c.split(";")[0]);

    // Step 2: Visit market data page with cookies from step 1
    const cookieStr1 = allCookies.join("; ");
    const r2 = await fetch(`${NSE_BASE_URL}/market-data/live-equity-market`, {
      headers: {
        ...NSE_BROWSER_HEADERS,
        Cookie: cookieStr1,
      },
      redirect: "follow",
    });
    const cookies2 = r2.headers.getSetCookie?.() || [];
    allCookies = [
      ...allCookies,
      ...cookies2.map((c) => c.split(";")[0]),
    ];

    sessionCookies = allCookies.join("; ");
    cookieTimestamp = now;

    console.log(`NSE session initialized: ${r1.status} → ${r2.status}`);
    return sessionCookies;
  } catch (err) {
    console.error("Failed to init NSE session:", err.message);
    return null;
  }
}

/**
 * Fetch live Nifty 500 market data from NSE API.
 */
async function fetchNSEData() {
  try {
    // Step 1: Get session cookies
    const cookies = await initNSESession();
    if (!cookies) {
      console.warn("No NSE cookies obtained");
    }

    // Step 2: Fetch index data with API headers
    const url = `${NSE_INDEX_URL}?index=NIFTY%20500`;
    const headers = {
      ...NSE_API_HEADERS,
      ...(cookies ? { Cookie: cookies } : {}),
    };

    const res = await fetch(url, {
      headers,
      next: { revalidate: 60 },
    });

    if (!res.ok) {
      throw new Error(`NSE API returned ${res.status}`);
    }

    const json = await res.json();

    if (!json.data || !Array.isArray(json.data)) {
      throw new Error("Invalid NSE response structure");
    }

    // Parse stock data — filter out the index summary row
    const stocks = json.data
      .filter((item) => item.symbol && item.symbol !== "NIFTY500" && item.symbol !== "NIFTY 500")
      .map((item) => ({
        symbol: item.symbol || "",
        company_name: item.meta?.companyName || "",
        industry: item.meta?.industry || "",
        open: item.open || 0,
        high: item.dayHigh || 0,
        low: item.dayLow || 0,
        prev_close: item.previousClose || 0,
        ltp: item.lastPrice || 0,
        change: item.change || 0,
        change_pct: item.pChange || 0,
        volume: item.totalTradedVolume || 0,
        value_lakhs: item.totalTradedValue || 0,
        year_high: item.yearHigh || 0,
        year_low: item.yearLow || 0,
        last_update: item.lastUpdateTime || "",
      }));

    console.log(`Fetched ${stocks.length} stocks from NSE`);
    return stocks;
  } catch (err) {
    console.error("NSE fetch failed:", err.message);
    return null;
  }
}

/**
 * Read the Shariah screening results from local JSON file.
 */
function readScreeningData() {
  try {
    // Try project root data directory
    const dataPath = path.join(process.cwd(), "..", "data", "halal_stocks.json");
    
    if (fs.existsSync(dataPath)) {
      const raw = fs.readFileSync(dataPath, "utf-8");
      return JSON.parse(raw);
    }

    // Fallback: check public directory
    const publicPath = path.join(process.cwd(), "public", "data", "halal_stocks.json");
    if (fs.existsSync(publicPath)) {
      const raw = fs.readFileSync(publicPath, "utf-8");
      return JSON.parse(raw);
    }

    console.warn("No halal_stocks.json found");
    return null;
  } catch (err) {
    console.error("Failed to read screening data:", err.message);
    return null;
  }
}

export async function GET() {
  try {
    // ── Check cache ───────────────────────────────────────────────
    const now = Date.now();
    if (cachedData && now - cacheTimestamp < CACHE_TTL) {
      return NextResponse.json(cachedData);
    }

    // ── Load screening data ───────────────────────────────────────
    const screeningData = readScreeningData();
    const halalStocks = screeningData?.stocks || [];

    // Build lookup map: symbol → screening info
    const screeningMap = {};
    for (const stock of halalStocks) {
      screeningMap[stock.symbol] = {
        status: stock.status,
        compliance_score: stock.compliance_score,
        reason: stock.reason,
        debt_ratio: stock.debt_ratio,
        cash_ratio: stock.cash_ratio,
        receivables_ratio: stock.receivables_ratio,
        interest_income_ratio: stock.interest_income_ratio,
        purification_pct: stock.purification_pct,
        market_cap_cr: stock.market_cap_cr,
        industry: stock.industry,
        data_year: stock.data_year,
      };
    }

    // ── Fetch live NSE data ───────────────────────────────────────
    const nseStocks = await fetchNSEData();

    let result;

    if (nseStocks && nseStocks.length > 0) {
      // ── LIVE MODE: Merge NSE data with screening data ──────────
      // Filter NSE data to only show Halal stocks
      const halalSymbols = new Set(halalStocks.map((s) => s.symbol));

      const mergedStocks = nseStocks
        .filter((nse) => halalSymbols.has(nse.symbol))
        .map((nse) => ({
          // Live market data from NSE
          symbol: nse.symbol,
          company_name: nse.company_name,
          industry: nse.industry,
          open: nse.open,
          high: nse.high,
          low: nse.low,
          prev_close: nse.prev_close,
          ltp: nse.ltp,
          change: nse.change,
          change_pct: nse.change_pct,
          volume: nse.volume,
          value_lakhs: nse.value_lakhs,
          year_high: nse.year_high,
          year_low: nse.year_low,
          last_update: nse.last_update,
          // Screening compliance data
          ...(screeningMap[nse.symbol] || {}),
        }));

      // Also include all Nifty 500 stocks with screening data merged
      const allStocksWithStatus = nseStocks.map((nse) => {
        const screening = screeningMap[nse.symbol];
        return {
          ...nse,
          // Merge all screening data if available
          status: screening?.status || "NOT_SCREENED",
          compliance_score: screening?.compliance_score ?? null,
          reason: screening?.reason ?? null,
          debt_ratio: screening?.debt_ratio ?? null,
          cash_ratio: screening?.cash_ratio ?? null,
          receivables_ratio: screening?.receivables_ratio ?? null,
          interest_income_ratio: screening?.interest_income_ratio ?? null,
          purification_pct: screening?.purification_pct ?? null,
          market_cap_cr: screening?.market_cap_cr ?? null,
          data_year: screening?.data_year ?? null,
        };
      });

      result = {
        source: "LIVE_NSE",
        last_updated: new Date().toISOString(),
        total_nifty500: nseStocks.length,
        total_halal: mergedStocks.length,
        screening_date: screeningData?.screening_date || null,
        halal_stocks: mergedStocks,
        all_stocks: allStocksWithStatus,
      };
    } else {
      // ── FALLBACK MODE: Return screening data without live prices ─
      result = {
        source: "CACHED_SCREENING",
        last_updated: screeningData?.screening_date || null,
        total_nifty500: 500,
        total_halal: halalStocks.length,
        screening_date: screeningData?.screening_date || null,
        halal_stocks: halalStocks,
        all_stocks: halalStocks,
        warning: "Live NSE data unavailable. Showing cached screening data without real-time prices.",
      };
    }

    // Update cache
    cachedData = result;
    cacheTimestamp = now;

    return NextResponse.json(result);
  } catch (err) {
    console.error("API error:", err);
    return NextResponse.json(
      { error: "Failed to fetch stock data", details: err.message },
      { status: 500 }
    );
  }
}
