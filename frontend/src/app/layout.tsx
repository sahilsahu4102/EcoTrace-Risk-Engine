import type { Metadata, Viewport } from "next";
import { Barlow, Barlow_Condensed } from "next/font/google";
import "./globals.css";

const barlow = Barlow({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-barlow",
  display: "swap",
});
const barlowCondensed = Barlow_Condensed({
  subsets: ["latin"],
  weight: ["500", "600", "700"],
  variable: "--font-barlow-cond",
  display: "swap",
});

const SITE = "https://eco-trace-risk-engine.vercel.app";
const TITLE = "EcoTrace: deforestation risk for a company's supply chain";
const DESCRIPTION =
  "Look up a company or commodity and get a 0-100 deforestation-risk score with the evidence behind it, drawn from Trase trade records, Forest 500, Global Forest Watch and the company's own sustainability page.";

export const metadata: Metadata = {
  metadataBase: new URL(SITE),
  title: { default: TITLE, template: "%s · EcoTrace" },
  description: DESCRIPTION,
  applicationName: "EcoTrace",
  authors: [{ name: "Sahil Kumar Sahu", url: "https://github.com/sahilsahu4102" }],
  alternates: { canonical: "/" },
  openGraph: {
    type: "website",
    siteName: "EcoTrace",
    title: TITLE,
    description: DESCRIPTION,
    url: SITE,
  },
  twitter: { card: "summary_large_image", title: TITLE, description: DESCRIPTION },
};

export const viewport: Viewport = {
  themeColor: "#f2f2ee",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${barlow.variable} ${barlowCondensed.variable}`}>
      <body>{children}</body>
    </html>
  );
}
