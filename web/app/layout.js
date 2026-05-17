import { Plus_Jakarta_Sans, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import Navbar from "./components/Navbar";

const plusJakarta = Plus_Jakarta_Sans({
  variable: "--font-plus-jakarta",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700", "800"],
});

const jetbrainsMono = JetBrains_Mono({
  variable: "--font-jetbrains",
  subsets: ["latin"],
  weight: ["400", "500", "600"],
});

export const metadata = {
  title: "HalalVest | Shariah-Compliant Indian Stock Screener",
  description:
    "Discover 250+ Shariah-compliant Indian stocks screened daily from Nifty 500 using AAOIFI standards. Ethical investing made accessible.",
  keywords:
    "halal stocks, shariah compliant, indian stocks, nifty 500, AAOIFI, islamic finance, ethical investing",
  openGraph: {
    title: "HalalVest — Invest With Faith",
    description:
      "Shariah-compliant Indian stock screener. 250+ halal stocks from Nifty 500.",
    type: "website",
  },
};

export default function RootLayout({ children }) {
  return (
    <html lang="en" className="dark">
      <body
        className={`${plusJakarta.variable} ${jetbrainsMono.variable} min-h-screen antialiased`}
        style={{ fontFamily: "var(--font-plus-jakarta), sans-serif" }}
      >
        <Navbar />
        <main className="flex-1">{children}</main>
      </body>
    </html>
  );
}
