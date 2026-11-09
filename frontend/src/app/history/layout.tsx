import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Search history",
  description: "Recent EcoTrace lookups and their risk levels.",
  robots: { index: false },
};

export default function HistoryLayout({ children }: { children: React.ReactNode }) {
  return children;
}
