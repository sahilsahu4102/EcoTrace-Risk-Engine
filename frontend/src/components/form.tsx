"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

/** Top rule of every page: wordmark left, navigation right. */
export function Masthead({ actions }: { actions?: ReactNode }) {
  const path = usePathname();
  return (
    <header className="masthead" data-html2canvas-ignore="true">
      <Link href="/" className="wordmark" aria-label="EcoTrace, home">
        EcoTrace
      </Link>
      <nav className="nav" aria-label="Main">
        <Link href="/" aria-current={path === "/" ? "page" : undefined}>
          Search
        </Link>
        <Link href="/history" aria-current={path === "/history" ? "page" : undefined}>
          History
        </Link>
        {actions}
      </nav>
    </header>
  );
}

/** One numbered box on the form. The number is only printed where other text points at it. */
export function Box({
  n,
  label,
  children,
  className = "",
}: {
  n?: number;
  /** Omit when the box opens with its own heading: a label above a heading is an eyebrow. */
  label?: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`box ${className}`}>
      {label && (
        <h2 className="label">
          {n !== undefined && <span className="n">{n}</span>}
          {label}
        </h2>
      )}
      {children}
    </section>
  );
}

/** Closing line of every page: the one outbound link recruiters need. */
export function Footer() {
  return (
    <footer className="footer" data-html2canvas-ignore="true">
      <span>EcoTrace is open source.</span>
      <a href="https://github.com/sahilsahu4102/EcoTrace-Risk-Engine" target="_blank" rel="noreferrer">
        Source code on GitHub
      </a>
    </footer>
  );
}

export type MarkKind = "solid" | "hollow" | "dashed";

/** Drawn state mark. Always printed beside a word, so colour never carries meaning alone. */
export function Mark({ kind }: { kind: MarkKind }) {
  return (
    <svg className="mark" viewBox="0 0 12 12" aria-hidden="true" focusable="false">
      {kind === "solid" && <rect x="0.75" y="0.75" width="10.5" height="10.5" fill="currentColor" stroke="currentColor" strokeWidth="1.5" />}
      {kind === "hollow" && <rect x="0.75" y="0.75" width="10.5" height="10.5" fill="none" stroke="currentColor" strokeWidth="1.5" />}
      {kind === "dashed" && <rect x="0.75" y="0.75" width="10.5" height="10.5" fill="none" stroke="currentColor" strokeWidth="1.5" strokeDasharray="2.5 2" />}
    </svg>
  );
}

const LEVELS = ["critical", "high", "moderate", "low", "minimal"] as const;

/** Risk level stamp: the border style (filled, double, single, dashed, dotted) plus the word. */
export function Stamp({ level, large = false, press = false }: { level: string; large?: boolean; press?: boolean }) {
  const known = (LEVELS as readonly string[]).includes(level) ? level : "moderate";
  return (
    <span className={`stamp stamp-${known}${large ? " stamp-lg" : ""}${press ? " stamp-press" : ""}`}>
      {level.replace(/_/g, " ")}
    </span>
  );
}

/** Risk-score ruler. Level cutoffs are the backend's: 20, 40, 60, 80. */
export function ScoreScale({ score }: { score: number }) {
  const pct = Math.max(0, Math.min(100, score));
  return (
    <div className="scale" role="img" aria-label={`Score ${score} on a scale of 0 to 100. Levels change at 20, 40, 60 and 80.`}>
      <div className="scale-track">
        <div className="scale-fill" style={{ width: `${pct}%` }} />
        {[20, 40, 60, 80].map((t) => (
          <i key={t} className="tick" style={{ left: `${t}%` }} />
        ))}
        <span className="scale-pin" style={{ left: `${pct}%` }} />
      </div>
      <div className="scale-words" aria-hidden="true">
        <span>minimal</span>
        <span>low</span>
        <span>moderate</span>
        <span>high</span>
        <span>critical</span>
      </div>
      <div className="scale-nums" aria-hidden="true">
        <span>0</span>
        <span>20</span>
        <span>40</span>
        <span>60</span>
        <span>80</span>
      </div>
    </div>
  );
}

/** "9 Nov 2026" in the visitor's locale. */
export function shortDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
}
