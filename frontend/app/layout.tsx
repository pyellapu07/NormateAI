import type { Metadata } from "next";
import { DM_Sans, JetBrains_Mono, Fraunces } from "next/font/google";
import "./globals.css";

const displayFont = Fraunces({
  subsets: ["latin"],
  variable: "--font-display",
  display: "swap",
  weight: ["400", "500", "600", "700", "800"],
});

const bodyFont = DM_Sans({
  subsets: ["latin"],
  variable: "--font-body",
  display: "swap",
  weight: ["400", "500", "600", "700"],
});

const monoFont = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  display: "swap",
  weight: ["400", "500"],
});

export const metadata: Metadata = {
  title: "Normate AI — UX Research Synthesis",
  description:
    "Fuse quantitative and qualitative research data into ranked, actionable recommendations. Powered by AI.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="en"
      className={`${displayFont.variable} ${bodyFont.variable} ${monoFont.variable}`}
    >
      <body className="font-body bg-surface text-ink antialiased">
        {children}
      </body>
    </html>
  );
}
