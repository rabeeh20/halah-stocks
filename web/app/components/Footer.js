import Link from "next/link";

export default function Footer() {
  return (
    <footer className="w-full py-16 bg-surface-container-lowest border-t border-outline-variant/20">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 px-5 md:px-16 max-w-[1280px] mx-auto w-full">
        <div>
          <div className="flex items-center gap-3 mb-6">
            <span className="text-2xl font-bold text-primary">HalalVest</span>
          </div>
          <p className="text-sm text-on-surface-variant max-w-sm leading-relaxed">
            © 2026 HalalVest. Shariah-compliant investing for the modern world.
            Data sourced from NSE India &amp; Screener.in.
          </p>
        </div>
        <div className="flex flex-col md:items-end justify-between">
          <div className="flex flex-wrap gap-8 mb-8 md:mb-0">
            <Link
              href="/methodology"
              className="text-xs font-semibold tracking-[0.05em] text-on-surface-variant hover:text-primary transition-colors"
            >
              Methodology
            </Link>
            <Link
              href="#"
              className="text-xs font-semibold tracking-[0.05em] text-on-surface-variant hover:text-primary transition-colors"
            >
              Privacy Policy
            </Link>
            <Link
              href="#"
              className="text-xs font-semibold tracking-[0.05em] text-on-surface-variant hover:text-primary transition-colors"
            >
              Terms of Service
            </Link>
          </div>
          <p className="text-xs text-on-surface-variant/60 mt-4 md:mt-0">
            Data sourced from NSE India. Screening based on AAOIFI standards.
            Not financial advice.
          </p>
        </div>
      </div>
    </footer>
  );
}
