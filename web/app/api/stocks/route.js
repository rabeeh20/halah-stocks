/**
 * API Route: /api/stocks
 *
 * Serves stock data from LOCAL JSON files only.
 * NO live NSE API calls — all data is pre-fetched by cron jobs:
 *   - Daily 3:36 PM IST → daily_market_update.py → updates market data
 *   - Monthly 1st 12 AM → shariah_screener.py → updates compliance data
 *
 * Files read:
 *   - data/halal_stocks.json     → Halal stocks with market data
 *   - data/market_snapshot.json  → All Nifty 500 stocks (for screener page)
 */

import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";

// ── File paths ──────────────────────────────────────────────────────────────

function getDataPath(filename) {
  // Try project root data directory (EC2: /home/ubuntu/halal-stocks/data/)
  const rootPath = path.join(process.cwd(), "..", "data", filename);
  if (fs.existsSync(rootPath)) return rootPath;

  // Fallback: public directory (for local dev)
  const publicPath = path.join(process.cwd(), "public", "data", filename);
  if (fs.existsSync(publicPath)) return publicPath;

  return null;
}

function readJSON(filename) {
  const filepath = getDataPath(filename);
  if (!filepath) {
    console.warn(`File not found: ${filename}`);
    return null;
  }
  try {
    const raw = fs.readFileSync(filepath, "utf-8");
    return JSON.parse(raw);
  } catch (err) {
    console.error(`Failed to read ${filename}:`, err.message);
    return null;
  }
}

// ── In-memory cache (avoid reading files on every request) ──────────────────

let cache = {
  data: null,
  fileModified: 0, // Track file modification time
};

function getFileModTime(filename) {
  const filepath = getDataPath(filename);
  if (!filepath) return 0;
  try {
    return fs.statSync(filepath).mtimeMs;
  } catch {
    return 0;
  }
}

// Force this route to be dynamic — never statically cached by Next.js
export const dynamic = "force-dynamic";
export const revalidate = 0;

// ── API Handler ─────────────────────────────────────────────────────────────

export async function GET() {
  try {
    // Check if the data file has been updated since last cache
    const halalModTime = getFileModTime("halal_stocks.json");

    // Serve from in-memory cache if file hasn't changed (avoids disk reads)
    if (cache.data && cache.fileModified === halalModTime) {
      return NextResponse.json(cache.data, {
        headers: {
          "Cache-Control": "no-store, no-cache, must-revalidate",
          "Pragma": "no-cache",
        },
      });
    }

    // ── Read halal stocks (screening + daily market data merged) ────────
    const halalData = readJSON("halal_stocks.json");
    const halalStocks = halalData?.stocks || [];

    // ── Read market snapshot (all Nifty 500 for screener page) ──────────
    const snapshotData = readJSON("market_snapshot.json");
    const allNSEStocks = snapshotData?.stocks || [];

    // ── Build screening lookup for the "All Stocks" view ───────────────
    const screeningMap = {};
    for (const stock of halalStocks) {
      screeningMap[stock.symbol] = {
        status: stock.status || "HALAL",
        compliance_score: stock.compliance_score,
        reason: stock.reason,
        debt_ratio: stock.debt_ratio,
        cash_ratio: stock.cash_ratio,
        receivables_ratio: stock.receivables_ratio,
        interest_income_ratio: stock.interest_income_ratio,
        purification_pct: stock.purification_pct,
        market_cap_cr: stock.market_cap_cr,
        data_year: stock.data_year,
      };
    }

    // ── Build "All Nifty 500" list with screening data merged ──────────
    const allStocksWithStatus = allNSEStocks.map((nse) => {
      const screening = screeningMap[nse.symbol];
      return {
        ...nse,
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

    // ── Build response ─────────────────────────────────────────────────
    const result = {
      source: "DATA_FILES",
      last_market_update: halalData?.last_market_update || null,
      screening_date: halalData?.screening_date || null,
      total_nifty500: allNSEStocks.length || 500,
      total_halal: halalStocks.length,
      halal_stocks: halalStocks,
      all_stocks: allStocksWithStatus.length > 0
        ? allStocksWithStatus
        : halalStocks,
      snapshot_date: snapshotData?.snapshot_date || null,
      snapshot_summary: snapshotData?.summary || null,
    };

    // Update in-memory cache keyed by file mod time
    cache = { data: result, fileModified: halalModTime };

    return NextResponse.json(result, {
      headers: {
        "Cache-Control": "no-store, no-cache, must-revalidate",
        "Pragma": "no-cache",
      },
    });
  } catch (err) {
    console.error("API error:", err);
    return NextResponse.json(
      { error: "Failed to read stock data", details: err.message },
      { status: 500 }
    );
  }
}
