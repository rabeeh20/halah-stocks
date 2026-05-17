"use client";

import { useState, useMemo, useEffect } from "react";
import Footer from "../components/Footer";

function Stars({ count }) {
  if (count == null) return <span className="text-outline text-sm">—</span>;
  return (
    <span className="text-primary text-sm tracking-tight whitespace-nowrap">
      {"★".repeat(count)}
      {"☆".repeat(5 - count)}
    </span>
  );
}

function formatVolume(vol) {
  if (!vol) return "—";
  if (vol >= 1e7) return `${(vol / 1e7).toFixed(2)}Cr`;
  if (vol >= 1e5) return `${(vol / 1e5).toFixed(2)}L`;
  if (vol >= 1e3) return `${(vol / 1e3).toFixed(1)}K`;
  return vol.toLocaleString("en-IN");
}

function formatPrice(price) {
  if (!price) return "—";
  return price.toLocaleString("en-IN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function formatMarketCap(cr) {
  if (!cr) return "—";
  if (cr >= 100000) return `${(cr / 100000).toFixed(2)}L Cr`;
  if (cr >= 1000) return `${Math.round(cr).toLocaleString("en-IN")} Cr`;
  return `${cr.toFixed(0)} Cr`;
}

export default function ScreenerPage() {
  const [stocks, setStocks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [dataSource, setDataSource] = useState("");
  const [lastUpdated, setLastUpdated] = useState("");
  const [warning, setWarning] = useState("");
  const [totalHalal, setTotalHalal] = useState(0);

  const [search, setSearch] = useState("");
  const [sortKey, setSortKey] = useState("symbol");
  const [sortDir, setSortDir] = useState("asc");
  const [page, setPage] = useState(1);
  const [viewMode, setViewMode] = useState("halal"); // "halal" or "all"
  const perPage = 20;

  // Fetch real data from API
  useEffect(() => {
    async function fetchData() {
      try {
        setLoading(true);
        const res = await fetch("/api/stocks");
        if (!res.ok) throw new Error(`API returned ${res.status}`);
        const data = await res.json();

        setDataSource(data.source || "UNKNOWN");
        setLastUpdated(data.last_updated || "");
        setWarning(data.warning || "");
        setTotalHalal(data.total_halal || 0);

        // Use halal_stocks or all_stocks based on view
        const allStocks = data.all_stocks || data.halal_stocks || [];
        setStocks(allStocks);
      } catch (err) {
        console.error("Fetch error:", err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }

    fetchData();

    // Auto-refresh every 60 seconds during market hours
    const interval = setInterval(fetchData, 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  // Filter and sort
  const filtered = useMemo(() => {
    let data = [...stocks];

    // View mode filter
    if (viewMode === "halal") {
      data = data.filter((s) => s.status === "HALAL");
    }

    // Search filter
    if (search) {
      const q = search.toLowerCase();
      data = data.filter(
        (s) =>
          s.symbol?.toLowerCase().includes(q) ||
          s.company_name?.toLowerCase().includes(q) ||
          s.industry?.toLowerCase().includes(q)
      );
    }

    // Sort
    data.sort((a, b) => {
      const valA = a[sortKey] ?? "";
      const valB = b[sortKey] ?? "";
      if (typeof valA === "string") {
        return sortDir === "asc"
          ? valA.localeCompare(valB)
          : valB.localeCompare(valA);
      }
      return sortDir === "asc" ? valA - valB : valB - valA;
    });

    return data;
  }, [stocks, search, sortKey, sortDir, viewMode]);

  const totalPages = Math.ceil(filtered.length / perPage);
  const paginated = filtered.slice((page - 1) * perPage, page * perPage);

  function handleSort(key) {
    if (sortKey === key) {
      setSortDir(sortDir === "asc" ? "desc" : "asc");
    } else {
      setSortKey(key);
      setSortDir("asc");
    }
    setPage(1);
  }

  function SortIcon({ column }) {
    if (sortKey !== column)
      return <span className="text-outline-variant ml-1 text-[10px]">⇅</span>;
    return (
      <span className="text-primary ml-1 text-[10px]">
        {sortDir === "asc" ? "▲" : "▼"}
      </span>
    );
  }

  const isLive = dataSource === "LIVE_NSE";

  // Format last updated time
  const formattedTime = lastUpdated
    ? new Date(lastUpdated).toLocaleString("en-IN", {
        day: "numeric",
        month: "short",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        timeZone: "Asia/Kolkata",
      })
    : "—";

  return (
    <>
      <section className="pt-28 pb-8">
        <div className="max-w-[1280px] mx-auto px-5 md:px-16">
          {/* Warning banner */}
          {warning && (
            <div className="mb-6 px-4 py-3 rounded-lg bg-primary/5 border border-primary/20 text-sm text-primary">
              ⚠ {warning}
            </div>
          )}

          {/* Page Header */}
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-8">
            <div>
              <h1 className="text-[32px] font-semibold tracking-tight text-on-background mb-1">
                Shariah Stock Screener
              </h1>
              <p className="text-sm text-on-surface-variant">
                {filtered.length} stocks
                {viewMode === "halal"
                  ? " passing AAOIFI compliance"
                  : " in Nifty 500"}{" "}
                •{" "}
                <span className="text-primary">
                  {isLive ? (
                    <>
                      <span className="inline-flex items-center gap-1">
                        <span className="h-1.5 w-1.5 rounded-full bg-gain animate-pulse" />
                        Live — {formattedTime}
                      </span>
                    </>
                  ) : (
                    `Last screened: ${formattedTime}`
                  )}
                </span>
              </p>
            </div>
            <div className="flex items-center gap-4">
              {/* View Toggle */}
              <div className="flex bg-surface-container-low p-1 rounded-lg">
                <button
                  onClick={() => {
                    setViewMode("halal");
                    setPage(1);
                  }}
                  className={`px-4 py-2 text-xs font-semibold tracking-[0.05em] rounded-md transition-colors ${
                    viewMode === "halal"
                      ? "bg-primary text-on-primary"
                      : "text-on-surface-variant hover:text-primary"
                  }`}
                >
                  Halal Only
                </button>
                <button
                  onClick={() => {
                    setViewMode("all");
                    setPage(1);
                  }}
                  className={`px-4 py-2 text-xs font-semibold tracking-[0.05em] rounded-md transition-colors ${
                    viewMode === "all"
                      ? "bg-primary text-on-primary"
                      : "text-on-surface-variant hover:text-primary"
                  }`}
                >
                  All Nifty 500
                </button>
              </div>

              {/* Search */}
              <div className="relative">
                <svg
                  className="absolute left-3 top-1/2 -translate-y-1/2 text-outline"
                  width="16"
                  height="16"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                >
                  <circle cx="11" cy="11" r="8" />
                  <line x1="21" y1="21" x2="16.65" y2="16.65" />
                </svg>
                <input
                  type="text"
                  placeholder="Search stocks..."
                  value={search}
                  onChange={(e) => {
                    setSearch(e.target.value);
                    setPage(1);
                  }}
                  className="bg-background border border-outline-variant/30 rounded-lg pl-10 pr-4 py-3 text-sm text-on-surface placeholder:text-outline focus:outline-none focus:border-primary transition-colors w-56"
                />
              </div>
            </div>
          </div>

          {/* Loading State */}
          {loading && (
            <div className="text-center py-20">
              <div className="inline-block w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin mb-4" />
              <p className="text-on-surface-variant">
                Fetching live NSE data...
              </p>
            </div>
          )}

          {/* Error State */}
          {error && !loading && (
            <div className="text-center py-20">
              <p className="text-loss text-lg mb-2">Failed to load data</p>
              <p className="text-sm text-on-surface-variant">{error}</p>
            </div>
          )}

          {/* ── Desktop Table ─────────────────────────────── */}
          {!loading && !error && (
            <>
              <div className="hidden md:block overflow-hidden rounded-2xl border border-outline-variant/20 shadow-2xl">
                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse">
                    <thead>
                      <tr className="bg-surface-container-high/50 border-b border-outline-variant/20">
                        {[
                          { key: "symbol", label: "Symbol", align: "" },
                          { key: "open", label: "Open", align: "text-right" },
                          { key: "high", label: "High", align: "text-right" },
                          { key: "low", label: "Low", align: "text-right" },
                          {
                            key: "prev_close",
                            label: "Prev. Close",
                            align: "text-right",
                          },
                          { key: "ltp", label: "LTP", align: "text-right" },
                          {
                            key: "change_pct",
                            label: "%Chng",
                            align: "text-right",
                          },
                          {
                            key: "volume",
                            label: "Volume",
                            align: "text-right",
                          },
                          {
                            key: "market_cap_cr",
                            label: "Mkt Cap (₹ Cr)",
                            align: "text-right",
                          },
                          {
                            key: "compliance_score",
                            label: "Compliance",
                            align: "text-center",
                          },
                        ].map((col) => (
                          <th
                            key={col.key}
                            onClick={() => handleSort(col.key)}
                            className={`px-4 py-4 text-xs font-semibold tracking-[0.05em] text-primary uppercase cursor-pointer hover:text-primary-container select-none whitespace-nowrap ${col.align}`}
                          >
                            {col.label}
                            <SortIcon column={col.key} />
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-outline-variant/10">
                      {paginated.map((stock, i) => (
                        <tr
                          key={stock.symbol}
                          className={`${
                            i % 2 === 0 ? "bg-row-even" : "bg-row-odd"
                          } hover:bg-row-hover transition-colors cursor-pointer`}
                        >
                          <td className="px-4 py-4 text-sm font-bold text-primary">
                            {stock.symbol}
                          </td>
                          <td className="px-4 py-4 text-sm text-on-surface-variant text-right font-mono">
                            {formatPrice(stock.open)}
                          </td>
                          <td className="px-4 py-4 text-sm text-on-surface-variant text-right font-mono">
                            {formatPrice(stock.high)}
                          </td>
                          <td className="px-4 py-4 text-sm text-on-surface-variant text-right font-mono">
                            {formatPrice(stock.low)}
                          </td>
                          <td className="px-4 py-4 text-sm text-on-surface-variant text-right font-mono">
                            {formatPrice(stock.prev_close)}
                          </td>
                          <td className="px-4 py-4 text-sm font-bold text-on-background text-right font-mono">
                            {formatPrice(stock.ltp)}
                          </td>
                          <td
                            className={`px-4 py-4 text-sm font-bold text-right font-mono ${
                              (stock.change_pct || 0) >= 0
                                ? "text-gain"
                                : "text-loss"
                            }`}
                          >
                            {stock.change_pct != null
                              ? `${stock.change_pct >= 0 ? "+" : ""}${stock.change_pct.toFixed(2)}%`
                              : "—"}
                          </td>
                          <td className="px-4 py-4 text-sm text-on-surface-variant text-right font-mono">
                            {formatVolume(stock.volume)}
                          </td>
                          <td className="px-4 py-4 text-sm text-on-surface-variant text-right font-mono">
                            {formatMarketCap(stock.market_cap_cr)}
                          </td>
                          <td className="px-4 py-4 text-center">
                            {stock.status === "HALAL" ? (
                              <Stars count={stock.compliance_score} />
                            ) : stock.status === "HARAM" ? (
                              <span className="text-loss text-xs font-semibold">
                                HARAM
                              </span>
                            ) : (
                              <span className="text-outline text-xs">—</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* Pagination */}
                <div className="flex items-center justify-between px-6 py-4 bg-surface-container-lowest border-t border-outline-variant/20">
                  <span className="text-sm text-on-surface-variant">
                    Showing {(page - 1) * perPage + 1}–
                    {Math.min(page * perPage, filtered.length)} of{" "}
                    {filtered.length} items
                  </span>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setPage(Math.max(1, page - 1))}
                      disabled={page === 1}
                      className="px-4 py-2 text-sm border border-outline-variant/30 rounded-lg text-on-surface-variant hover:text-primary hover:border-primary disabled:opacity-30 transition-colors"
                    >
                      Previous
                    </button>
                    {Array.from(
                      { length: Math.min(totalPages, 5) },
                      (_, i) => {
                        let pageNum;
                        if (totalPages <= 5) {
                          pageNum = i + 1;
                        } else if (page <= 3) {
                          pageNum = i + 1;
                        } else if (page >= totalPages - 2) {
                          pageNum = totalPages - 4 + i;
                        } else {
                          pageNum = page - 2 + i;
                        }
                        return (
                          <button
                            key={pageNum}
                            onClick={() => setPage(pageNum)}
                            className={`w-10 h-10 text-sm rounded-lg transition-colors ${
                              page === pageNum
                                ? "bg-primary text-on-primary font-bold"
                                : "border border-outline-variant/30 text-on-surface-variant hover:text-primary"
                            }`}
                          >
                            {pageNum}
                          </button>
                        );
                      }
                    )}
                    <button
                      onClick={() =>
                        setPage(Math.min(totalPages, page + 1))
                      }
                      disabled={page === totalPages}
                      className="px-4 py-2 text-sm border border-outline-variant/30 rounded-lg text-on-surface-variant hover:text-primary hover:border-primary disabled:opacity-30 transition-colors"
                    >
                      Next
                    </button>
                  </div>
                </div>
              </div>

              {/* ── Mobile Cards ──────────────────────────────── */}
              <div className="md:hidden space-y-3">
                {paginated.map((stock) => (
                  <div
                    key={stock.symbol}
                    className="bg-row-even border border-outline-variant/20 rounded-xl p-5 hover:border-primary/30 transition-colors"
                  >
                    <div className="flex items-start justify-between mb-2">
                      <div>
                        <span className="text-base font-bold text-on-background">
                          {stock.symbol}
                        </span>
                        <p className="text-xs text-on-surface-variant mt-0.5">
                          {stock.company_name}
                        </p>
                        <div className="mt-1">
                          {stock.status === "HALAL" ? (
                            <Stars count={stock.compliance_score} />
                          ) : stock.status === "HARAM" ? (
                            <span className="text-loss text-xs font-semibold">
                              HARAM
                            </span>
                          ) : (
                            <span className="text-outline text-xs">
                              Not Screened
                            </span>
                          )}
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-xl font-bold text-on-background font-mono">
                          ₹{formatPrice(stock.ltp)}
                        </div>
                        <span
                          className={`inline-block mt-1 px-2 py-0.5 rounded text-xs font-bold ${
                            (stock.change_pct || 0) >= 0
                              ? "bg-gain/10 text-gain"
                              : "bg-loss/10 text-loss"
                          }`}
                        >
                          {stock.change_pct != null
                            ? `${stock.change_pct >= 0 ? "+" : ""}${stock.change_pct.toFixed(2)}%`
                            : "—"}
                        </span>
                      </div>
                    </div>
                    <div className="flex justify-between mt-4 text-xs text-on-surface-variant">
                      <div>
                        <span className="uppercase tracking-wider font-semibold">
                          Vol
                        </span>
                        <br />
                        <span className="font-mono">
                          {formatVolume(stock.volume)}
                        </span>
                      </div>
                      <div className="text-right">
                        <span className="uppercase tracking-wider font-semibold">
                          Mkt Cap
                        </span>
                        <br />
                        <span className="font-mono">
                          ₹{formatMarketCap(stock.market_cap_cr)}
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              {/* No results */}
              {filtered.length === 0 && (
                <div className="text-center py-20 text-on-surface-variant">
                  <p className="text-lg mb-2">No stocks found</p>
                  <p className="text-sm">
                    Try adjusting your search or filters.
                  </p>
                </div>
              )}
            </>
          )}

          {/* Disclaimer */}
          <p className="text-center text-xs text-on-surface-variant/60 italic mt-8">
            Data sourced from NSE India. Screening based on AAOIFI standards.
            Not financial advice.
          </p>
        </div>
      </section>

      <Footer />
    </>
  );
}
