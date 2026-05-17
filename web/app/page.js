"use client";

import Link from "next/link";
import { useState, useEffect, useMemo } from "react";
import Footer from "./components/Footer";

function Stars({ count }) {
  if (count == null) return <span className="text-outline text-sm">—</span>;
  return (
    <span className="text-primary text-sm tracking-tight">
      {"★".repeat(count)}
      {"☆".repeat(5 - count)}
    </span>
  );
}

function formatVolume(vol) {
  if (!vol) return "—";
  if (vol >= 1e7) return `${(vol / 1e7).toFixed(1)}Cr`;
  if (vol >= 1e5) return `${(vol / 1e5).toFixed(1)}L`;
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
  if (cr >= 100000) return `₹${(cr / 100000).toFixed(2)}L Cr`;
  if (cr >= 1000) return `₹${(cr / 1000).toFixed(0)}K Cr`;
  return `₹${cr.toLocaleString("en-IN")} Cr`;
}

// Define tab configurations
const TABS = [
  {
    key: "gainers",
    label: "Top Gainers",
    sortKey: "change_pct",
    sortDir: "desc",
  },
  {
    key: "losers",
    label: "Top Losers",
    sortKey: "change_pct",
    sortDir: "asc",
  },
  {
    key: "volume",
    label: "Volume",
    sortKey: "volume",
    sortDir: "desc",
  },
  {
    key: "marketcap",
    label: "Market Cap",
    sortKey: "market_cap_cr",
    sortDir: "desc",
  },
];

export default function Home() {
  const [allStocks, setAllStocks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dataSource, setDataSource] = useState("OFFLINE");
  const [totalHalal, setTotalHalal] = useState(0);
  const [screeningDate, setScreeningDate] = useState("—");
  const [totalMarketCap, setTotalMarketCap] = useState(0);
  const [warning, setWarning] = useState("");
  const [activeTab, setActiveTab] = useState("gainers");

  // Fetch data client-side
  useEffect(() => {
    async function fetchData() {
      try {
        const res = await fetch("/api/stocks");
        if (!res.ok) throw new Error(`API returned ${res.status}`);
        const data = await res.json();

        setDataSource(data.source || "UNKNOWN");
        setTotalHalal(data.total_halal || 0);
        setScreeningDate(data.screening_date || "—");
        setWarning(data.warning || "");

        const stocks = data.halal_stocks || [];
        setAllStocks(stocks);

        // Calculate total market cap
        const mcap = stocks.reduce(
          (sum, s) => sum + (s.market_cap_cr || 0),
          0
        );
        setTotalMarketCap(mcap);
      } catch (err) {
        console.error("Failed to fetch stock data:", err);
      } finally {
        setLoading(false);
      }
    }

    fetchData();
  }, []);

  // Sort stocks based on active tab
  const displayStocks = useMemo(() => {
    const tab = TABS.find((t) => t.key === activeTab);
    if (!tab || allStocks.length === 0) return [];

    const sorted = [...allStocks].sort((a, b) => {
      const valA = a[tab.sortKey] ?? 0;
      const valB = b[tab.sortKey] ?? 0;
      return tab.sortDir === "desc" ? valB - valA : valA - valB;
    });

    return sorted.slice(0, 10);
  }, [allStocks, activeTab]);

  // Find top gainer for stat card
  const topGainer = useMemo(() => {
    const withChange = allStocks.filter((s) => s.change_pct != null);
    if (withChange.length === 0) return null;
    return withChange.reduce((max, s) =>
      (s.change_pct || 0) > (max.change_pct || 0) ? s : max
    );
  }, [allStocks]);

  const isLive = dataSource === "LIVE_NSE";

  // Format market cap stat
  const marketCapDisplay =
    totalMarketCap > 0
      ? `₹${(totalMarketCap / 100000).toFixed(0)}L Cr`
      : "—";

  // Dynamic table columns based on active tab
  const getColumns = () => {
    const base = [
      { key: "symbol", label: "Symbol" },
      { key: "company_name", label: "Company" },
      { key: "ltp", label: "LTP (₹)", align: "right", format: "price" },
      {
        key: "change_pct",
        label: "Change (%)",
        align: "right",
        format: "change",
      },
    ];

    if (activeTab === "volume") {
      base.push({
        key: "volume",
        label: "Volume",
        align: "right",
        format: "volume",
      });
    } else if (activeTab === "marketcap") {
      base.push({
        key: "market_cap_cr",
        label: "Mkt Cap (₹ Cr)",
        align: "right",
        format: "marketcap",
      });
    } else {
      base.push({
        key: "volume",
        label: "Volume",
        align: "right",
        format: "volume",
        hideOnMobile: true,
      });
    }

    base.push({ key: "compliance_score", label: "Compliance", align: "center" });
    return base;
  };

  const columns = getColumns();

  // Format cell value based on format type
  function formatCell(stock, col) {
    const val = stock[col.key];
    switch (col.format) {
      case "price":
        return formatPrice(val);
      case "change":
        if (val == null) return "—";
        return `${val >= 0 ? "+" : ""}${val.toFixed(2)}%`;
      case "volume":
        return formatVolume(val);
      case "marketcap":
        return formatMarketCap(val);
      default:
        return val || "—";
    }
  }

  return (
    <>
      {/* ── Hero Section ────────────────────────────────────── */}
      <section className="relative pt-40 pb-24 overflow-hidden islamic-pattern min-h-[80vh] flex flex-col justify-center">
        <div className="max-w-[1280px] mx-auto px-5 md:px-16 text-center">
          {/* Badge */}
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-primary/20 bg-primary/5 mb-8 animate-fade-in-up">
            <span
              className={`flex h-2 w-2 rounded-full ${
                isLive ? "bg-gain animate-pulse" : "bg-primary animate-pulse"
              }`}
            />
            <span className="text-xs font-semibold tracking-[0.05em] text-primary">
              {isLive ? "Live NSE Data" : "NSE Screening Active"}
            </span>
          </div>

          {/* Heading */}
          <h1 className="text-4xl md:text-[48px] font-bold tracking-tight text-on-background mb-6 max-w-3xl mx-auto leading-tight animate-fade-in-up-delay-1">
            Invest With <span className="text-primary">Faith</span>
          </h1>

          {/* Subtitle */}
          <p className="text-lg text-on-surface-variant mb-12 max-w-2xl mx-auto leading-relaxed animate-fade-in-up-delay-2">
            {totalHalal > 0 ? totalHalal : "250+"} Shariah-compliant Indian
            stocks, screened daily from Nifty 500 using AAOIFI standards.
            Ethical investing made accessible.
          </p>

          {/* CTAs */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-6 animate-fade-in-up-delay-3">
            <Link
              href="/screener"
              className="bg-primary text-on-primary text-base px-10 py-4 rounded-lg hover:opacity-90 transition-opacity active:scale-95 duration-200 font-bold w-full sm:w-auto text-center"
            >
              Explore Stocks
            </Link>
            <Link
              href="/methodology"
              className="border border-primary text-primary text-base px-10 py-4 rounded-lg hover:bg-primary/10 transition-colors active:scale-95 duration-200 font-bold w-full sm:w-auto text-center"
            >
              Our Methodology
            </Link>
          </div>
        </div>
      </section>

      {/* ── Stats Bar ───────────────────────────────────────── */}
      <section className="relative -mt-16 z-10">
        <div className="max-w-[1280px] mx-auto px-5 md:px-16">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            <StatCard
              icon="✓"
              value={totalHalal > 0 ? String(totalHalal) : "—"}
              label="Halal Stocks"
            />
            <StatCard icon="₹" value={marketCapDisplay} label="Market Cap" />
            <StatCard
              icon="↗"
              value={
                topGainer
                  ? `+${topGainer.change_pct?.toFixed(2)}%`
                  : "—"
              }
              label={topGainer?.symbol || "Top Gainer"}
              valueColor="text-gain"
            />
            <StatCard icon="⟳" value={screeningDate} label="Last Screened" />
          </div>
        </div>
      </section>

      {/* ── Preview Table ───────────────────────────────────── */}
      <section className="py-24">
        <div className="max-w-[1280px] mx-auto px-5 md:px-16">
          {/* Warning */}
          {warning && (
            <div className="mb-6 px-4 py-3 rounded-lg bg-primary/5 border border-primary/20 text-sm text-primary">
              ⚠ {warning}
            </div>
          )}

          {/* Header + Tabs */}
          <div className="flex flex-col md:flex-row md:items-end justify-between mb-12 gap-6">
            <div>
              <h2 className="text-[32px] font-semibold tracking-tight text-on-background mb-2">
                Top Performing Halal Stocks
              </h2>
              <p className="text-base text-on-surface-variant">
                {isLive ? "Real-time" : "Cached"} performance of AAOIFI
                compliant entities.
                {isLive && (
                  <span className="ml-2 inline-flex items-center gap-1 text-gain text-xs font-semibold">
                    <span className="h-1.5 w-1.5 rounded-full bg-gain animate-pulse" />
                    LIVE
                  </span>
                )}
              </p>
            </div>

            {/* ── WORKING FILTER TABS ── */}
            <div className="flex gap-2 bg-surface-container-low p-1 rounded-xl">
              {TABS.map((tab) => (
                <button
                  key={tab.key}
                  onClick={() => setActiveTab(tab.key)}
                  className={`px-6 py-2.5 rounded-lg text-xs font-semibold tracking-[0.05em] transition-colors ${
                    activeTab === tab.key
                      ? "bg-primary text-on-primary"
                      : "text-on-surface-variant hover:text-primary"
                  } ${
                    tab.key === "volume" || tab.key === "marketcap"
                      ? "hidden sm:block"
                      : ""
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>
          </div>

          {/* Loading */}
          {loading && (
            <div className="text-center py-20">
              <div className="inline-block w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin mb-4" />
              <p className="text-on-surface-variant">
                Fetching live NSE data...
              </p>
            </div>
          )}

          {/* Table */}
          {!loading && displayStocks.length > 0 && (
            <div className="overflow-hidden rounded-2xl border border-outline-variant/20 shadow-2xl">
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="bg-surface-container-high/50 border-b border-outline-variant/20">
                      {columns.map((col) => (
                        <th
                          key={col.key}
                          className={`px-6 py-5 text-xs font-semibold tracking-[0.05em] text-primary uppercase whitespace-nowrap ${
                            col.align === "right"
                              ? "text-right"
                              : col.align === "center"
                                ? "text-center"
                                : ""
                          } ${col.hideOnMobile ? "hidden md:table-cell" : ""}`}
                        >
                          {col.label}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-outline-variant/10">
                    {displayStocks.map((stock, i) => (
                      <tr
                        key={stock.symbol}
                        className={`${
                          i % 2 === 0 ? "bg-row-even" : "bg-row-odd"
                        } hover:bg-row-hover transition-colors cursor-pointer group`}
                      >
                        {columns.map((col) => {
                          // Symbol column
                          if (col.key === "symbol") {
                            return (
                              <td
                                key={col.key}
                                className="px-6 py-5 text-base font-bold text-on-background"
                              >
                                {stock.symbol}
                              </td>
                            );
                          }
                          // Company column
                          if (col.key === "company_name") {
                            return (
                              <td
                                key={col.key}
                                className="px-6 py-5 text-base text-on-surface-variant"
                              >
                                {stock.company_name}
                              </td>
                            );
                          }
                          // Compliance column
                          if (col.key === "compliance_score") {
                            return (
                              <td key={col.key} className="px-6 py-5 text-center">
                                <Stars count={stock.compliance_score} />
                              </td>
                            );
                          }
                          // Change% column (colored)
                          if (col.key === "change_pct") {
                            return (
                              <td
                                key={col.key}
                                className={`px-6 py-5 text-base text-right font-bold font-mono ${
                                  (stock.change_pct || 0) >= 0
                                    ? "text-gain"
                                    : "text-loss"
                                }`}
                              >
                                {formatCell(stock, col)}
                              </td>
                            );
                          }
                          // All other data columns
                          return (
                            <td
                              key={col.key}
                              className={`px-6 py-5 text-base font-mono ${
                                col.align === "right"
                                  ? "text-right"
                                  : col.align === "center"
                                    ? "text-center"
                                    : ""
                              } ${
                                col.key === "ltp"
                                  ? "text-on-background"
                                  : "text-on-surface-variant"
                              } ${col.hideOnMobile ? "hidden md:table-cell" : ""}`}
                            >
                              {formatCell(stock, col)}
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Empty state */}
          {!loading && displayStocks.length === 0 && (
            <div className="text-center py-20 text-on-surface-variant">
              <p className="text-lg mb-2">No stock data available</p>
              <p className="text-sm">
                Run the screening pipeline or check NSE connectivity.
              </p>
            </div>
          )}

          {/* View All Link */}
          <div className="mt-8 text-center">
            <Link
              href="/screener"
              className="inline-flex items-center gap-2 text-xs font-semibold tracking-[0.05em] text-primary hover:gap-4 transition-all duration-300"
            >
              View All {totalHalal} Stocks
              <svg
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <line x1="5" y1="12" x2="19" y2="12" />
                <polyline points="12 5 19 12 12 19" />
              </svg>
            </Link>
          </div>
        </div>
      </section>

      <Footer />
    </>
  );
}

/* ── Stat Card Component ──────────────────────────────────── */
function StatCard({ icon, value, label, valueColor = "text-on-background" }) {
  return (
    <div className="glass-card p-8 rounded-xl border-primary/20 hover:border-primary/40 transition-colors">
      <div className="flex items-center justify-between mb-4">
        <span className="text-primary text-2xl">{icon}</span>
      </div>
      <div
        className={`text-[32px] font-semibold tracking-tight ${valueColor}`}
      >
        {value}
      </div>
      <div className="text-xs font-semibold tracking-[0.05em] text-on-surface-variant uppercase mt-1">
        {label}
      </div>
    </div>
  );
}
