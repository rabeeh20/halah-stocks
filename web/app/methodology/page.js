import Footer from "../components/Footer";

export const metadata = {
  title: "How We Screen | HalalVest",
  description:
    "Transparent, independent Shariah compliance analysis based on AAOIFI standards for Indian stocks.",
};

export default function MethodologyPage() {
  return (
    <>
      {/* ── Hero ────────────────────────────────────────────── */}
      <section className="pt-32 pb-16 bg-surface-container-lowest border-b border-outline-variant/20">
        <div className="max-w-[1280px] mx-auto px-5 md:px-16 text-center">
          <h1 className="text-4xl md:text-[48px] font-bold tracking-tight text-primary mb-4">
            How We Screen
          </h1>
          <p className="text-lg text-on-surface-variant max-w-2xl mx-auto leading-relaxed">
            Transparent, independent Shariah compliance analysis based on AAOIFI
            standards. Ensuring your wealth grows ethically and purely.
          </p>
        </div>
      </section>

      {/* ── 3-Step Process ──────────────────────────────────── */}
      <section className="py-20">
        <div className="max-w-[1280px] mx-auto px-5 md:px-16">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 relative">
            {/* Connecting line (desktop) */}
            <div className="hidden md:block absolute top-12 left-[20%] right-[20%] h-0.5 border-t-2 border-dashed border-outline-variant/30" />

            <StepCard
              icon="📊"
              title="Source"
              description="We start with all 500 stocks from NSE's Nifty 500 index"
              step="01"
            />
            <StepCard
              icon="⚡"
              title="Screen"
              description="Apply AAOIFI financial ratio tests + business activity screening"
              step="02"
            />
            <StepCard
              icon="✅"
              title="Verify"
              description="Quarterly re-screening with latest financial data from Screener.in"
              step="03"
            />
          </div>
        </div>
      </section>

      {/* ── Screening Rules ─────────────────────────────────── */}
      <section className="py-20 bg-surface-container-lowest/50">
        <div className="max-w-[1280px] mx-auto px-5 md:px-16">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            {/* Business Activity Screen */}
            <div className="bg-row-even border border-outline-variant/20 rounded-xl p-8">
              <div className="flex items-center gap-3 mb-6">
                <span className="text-2xl">🚫</span>
                <h3 className="text-2xl font-semibold text-on-background">
                  Business Activity Screen
                </h3>
              </div>
              <ul className="space-y-4">
                {[
                  "Banks & Financial Services",
                  "Alcohol & Tobacco",
                  "Gambling & Entertainment",
                  "Weapons & Defense",
                ].map((item) => (
                  <li key={item} className="flex items-center gap-3 text-on-surface-variant">
                    <span className="text-loss text-lg">✕</span>
                    <span className="text-base">{item}</span>
                  </li>
                ))}
              </ul>
              <p className="mt-6 text-sm text-loss italic">
                Stocks in these sectors are automatically excluded
              </p>
            </div>

            {/* Financial Ratio Screen */}
            <div className="bg-row-even border border-outline-variant/20 rounded-xl p-8 border-l-4 border-l-primary">
              <div className="flex items-center gap-3 mb-6">
                <span className="text-2xl">📐</span>
                <h3 className="text-2xl font-semibold text-on-background">
                  Financial Ratio Screen
                </h3>
              </div>
              <table className="w-full">
                <thead>
                  <tr className="border-b border-outline-variant/20">
                    <th className="text-left text-xs font-semibold tracking-[0.05em] text-primary uppercase py-3">
                      Rule
                    </th>
                    <th className="text-left text-xs font-semibold tracking-[0.05em] text-primary uppercase py-3">
                      Formula
                    </th>
                    <th className="text-right text-xs font-semibold tracking-[0.05em] text-primary uppercase py-3">
                      Threshold
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-outline-variant/10">
                  {[
                    { rule: "Debt Ratio", formula: "Debt ÷ Market Cap", threshold: "< 30%" },
                    { rule: "Cash Ratio", formula: "Cash ÷ Market Cap", threshold: "< 30%" },
                    { rule: "Receivables", formula: "Receiv. ÷ Market Cap", threshold: "< 49%" },
                    { rule: "Interest Income", formula: "Interest ÷ Total Revenue", threshold: "< 5%" },
                  ].map((row) => (
                    <tr key={row.rule}>
                      <td className="py-4 text-base font-medium text-on-background">
                        {row.rule}
                      </td>
                      <td className="py-4 text-sm text-on-surface-variant">
                        {row.formula}
                      </td>
                      <td className="py-4 text-base font-bold text-primary text-right">
                        {row.threshold}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </section>

      {/* ── Compliance Score ─────────────────────────────────── */}
      <section className="py-20">
        <div className="max-w-[800px] mx-auto px-5 md:px-16">
          <div className="bg-row-even border border-outline-variant/20 rounded-xl p-8">
            <h3 className="text-2xl font-semibold text-on-background text-center mb-8">
              Shariah Compliance Score
            </h3>
            <div className="space-y-4">
              {[
                { stars: 5, label: "Excellent", threshold: "All ratios < 15%", highlight: true },
                { stars: 4, label: "Very Good", threshold: "< 20%", highlight: false },
                { stars: 3, label: "Good", threshold: "< 25%", highlight: false },
                { stars: 2, label: "Acceptable", threshold: "< 30%", highlight: false },
              ].map((tier) => (
                <div
                  key={tier.stars}
                  className={`flex items-center justify-between px-6 py-4 rounded-lg border ${
                    tier.highlight
                      ? "border-primary/40 bg-primary/5"
                      : "border-outline-variant/20"
                  }`}
                >
                  <div className="flex items-center gap-4">
                    <span className="text-primary text-lg tracking-tight">
                      {"★".repeat(tier.stars)}{"☆".repeat(5 - tier.stars)}
                    </span>
                    <span className="text-base font-semibold text-on-background">
                      {tier.label}
                    </span>
                  </div>
                  <span className="text-sm text-on-surface-variant">
                    {tier.threshold}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ── Data Sources ────────────────────────────────────── */}
      <section className="py-16 bg-surface-container-lowest/50 border-t border-outline-variant/20">
        <div className="max-w-[1280px] mx-auto px-5 md:px-16 text-center">
          <p className="text-xs font-semibold tracking-[0.05em] text-on-surface-variant uppercase mb-8">
            Powered by Verified Data
          </p>
          <div className="flex items-center justify-center gap-12">
            <div className="flex items-center gap-3 text-on-surface-variant">
              <span className="text-2xl">📈</span>
              <span className="text-lg font-semibold">NSE India</span>
            </div>
            <div className="h-8 w-px bg-outline-variant/30" />
            <div className="flex items-center gap-3 text-on-surface-variant">
              <span className="text-2xl">📄</span>
              <span className="text-lg font-semibold">Screener.in</span>
            </div>
          </div>
        </div>
      </section>

      <Footer />
    </>
  );
}

/* ── Step Card Component ──────────────────────────────────── */
function StepCard({ icon, title, description, step }) {
  return (
    <div className="relative text-center">
      <div className="w-20 h-20 mx-auto mb-6 rounded-full bg-surface-container-high border border-outline-variant/30 flex items-center justify-center text-3xl relative z-10">
        {icon}
      </div>
      <h3 className="text-xl font-semibold text-on-background mb-3">
        {title}
      </h3>
      <p className="text-sm text-on-surface-variant leading-relaxed max-w-xs mx-auto">
        {description}
      </p>
    </div>
  );
}
