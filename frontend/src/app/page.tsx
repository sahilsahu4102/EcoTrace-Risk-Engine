"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowUpRight } from "lucide-react";
import { healthCheck } from "@/lib/api";
import { Box, Footer, Mark, Masthead } from "@/components/form";

const COMPANIES = ["Unilever", "Cargill", "JBS", "Wilmar", "Nestlé"];
const COMMODITIES = ["Palm Oil", "Cocoa", "Soy"];

// Descriptions follow the methodology note the API returns with every result.
const SOURCES: { name: string; desc: string; kind: string }[] = [
  {
    name: "Company sustainability page",
    desc: "Read when you search: fetched directly, or through Jina Reader when the site blocks that. An AI model then extracts commodities and countries.",
    kind: "Read per lookup",
  },
  {
    name: "Trase trade records",
    desc: "Which commodity leaves which country, per company.",
    kind: "Static dataset",
  },
  {
    name: "Forest 500",
    desc: "Company forest-policy scores, which adjust the total.",
    kind: "Static dataset",
  },
  {
    name: "Global Forest Watch",
    desc: "Tree-cover-loss trend and deforestation alerts by country.",
    kind: "Live API",
  },
];

type Server = "checking" | "waking" | "ready" | "down";

export default function HomePage() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [recentSearches, setRecentSearches] = useState<string[]>([]);
  const [server, setServer] = useState<Server>("checking");
  const router = useRouter();

  // Wake the backend while the visitor reads the page: the free host sleeps after
  // 15 idle minutes and takes up to a minute to start. The status line reports what
  // actually happened to this request, nothing more.
  const checkServer = useCallback(() => {
    setServer("checking");
    const slow = setTimeout(() => setServer((s) => (s === "checking" ? "waking" : s)), 4000);
    healthCheck()
      .then(() => setServer("ready"))
      .catch(() => setServer("down"))
      .finally(() => clearTimeout(slow));
  }, []);

  useEffect(() => {
    checkServer();
  }, [checkServer]);

  // Load recent searches from localStorage on mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem("ecotrace_recent");
      if (stored) {
        setRecentSearches(JSON.parse(stored).slice(0, 5));
      }
    } catch (e) {
      console.error("Failed to load history", e);
    }
  }, []);

  const handleSearch = (company: string) => {
    const term = company.trim();
    if (!term) return;

    // Save to localStorage
    try {
      const updated = [term, ...recentSearches.filter((s) => s.toLowerCase() !== term.toLowerCase())].slice(0, 5);
      localStorage.setItem("ecotrace_recent", JSON.stringify(updated));
      setRecentSearches(updated);
    } catch (e) {
      console.error("Failed to save history", e);
    }

    setLoading(true);
    router.push(`/results/${encodeURIComponent(term)}`);
  };

  return (
    <div className="page">
      <Masthead />
      <main className="sheet">
        <div className="col">
          <div className="box">
            <h1 className="display h1-home">
              A <span className="nowrap">deforestation-risk</span> score you can trace to its sources.
            </h1>
            <p className="lede">
              Enter a company or a commodity. EcoTrace scores it from 0 to 100 and shows the evidence behind every part of the score, with the date of the data
              and what is missing.
            </p>
          </div>

          <Box n={1} label="Company or commodity">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSearch(query);
              }}
            >
              <div className="entry">
                <input
                  id="q"
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Cargill, or Palm Oil"
                  aria-label="Company or commodity"
                  autoComplete="off"
                  disabled={loading}
                  autoFocus
                />
                <button type="submit" className="btn" disabled={loading || !query.trim()}>
                  {loading ? "Opening…" : "Run assessment"}
                </button>
              </div>
            </form>
          </Box>

          <Box n={2} label="Or pick an example">
            <div className="chips-two">
              <div>
                <p className="fine" id="ex-co">Companies</p>
                <ul className="pick-list" aria-labelledby="ex-co">
                  {COMPANIES.map((c) => (
                    <li key={c}>
                      <button className="pick" onClick={() => handleSearch(c)} disabled={loading}>
                        {c}
                        <ArrowUpRight size={16} aria-hidden="true" />
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
              <div>
                <p className="fine" id="ex-cm">Commodities</p>
                <ul className="pick-list" aria-labelledby="ex-cm">
                  {COMMODITIES.map((c) => (
                    <li key={c}>
                      <button className="pick" onClick={() => handleSearch(c)} disabled={loading}>
                        {c}
                        <ArrowUpRight size={16} aria-hidden="true" />
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </Box>

          {recentSearches.length > 0 && (
            <Box label="Your recent searches">
              <ul className="pick-list">
                {recentSearches.map((s) => (
                  <li key={`recent-${s}`}>
                    <button className="pick" onClick={() => handleSearch(s)} disabled={loading}>
                      {s}
                      <ArrowUpRight size={16} aria-hidden="true" />
                    </button>
                  </li>
                ))}
              </ul>
            </Box>
          )}
        </div>

        <div className="col col-right">
          <Box label="How the score is built">
            <ul className="sources">
              {SOURCES.map((s) => (
                <li key={s.name}>
                  <strong>{s.name}</strong>
                  <span className="tag">{s.kind}</span>
                  <span className="desc">{s.desc}</span>
                </li>
              ))}
            </ul>
            <p className="prose-sm" style={{ marginTop: 16 }}>
              The score averages commodity weight × country risk over the commodity-country pairs that the evidence supports. Every result prints its methodology
              and limits.
            </p>
          </Box>

          <Box label="Analysis server">
            <div className="status" role="status" aria-live="polite">
              <Mark kind={server === "ready" ? "solid" : server === "checking" ? "dashed" : "hollow"} />
              <div>
                {server === "checking" && <p>Checking the analysis server.</p>}
                {server === "ready" && <p>Ready.</p>}
                {server === "waking" && (
                  <p>
                    Waking up. The server runs on a free host that sleeps when idle, so the first request can take about a minute. You can search now; the lookup
                    waits for it.
                  </p>
                )}
                {server === "down" && (
                  <>
                    <p>The server did not answer. Give it a minute, then check again.</p>
                    <button className="btn btn-line" style={{ marginTop: 10, minHeight: 40 }} onClick={checkServer}>
                      Check again
                    </button>
                  </>
                )}
              </div>
            </div>
          </Box>
        </div>
      </main>
      <Footer />
    </div>
  );
}
