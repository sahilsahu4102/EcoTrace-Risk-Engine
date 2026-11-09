"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Search } from "lucide-react";
import { API_BASE } from "@/lib/api";
import { Footer, Masthead, Stamp } from "@/components/form";

interface HistoryItem {
  query: string;
  risk_score: number;
  risk_level: string;
  confidence_score: number;
  confidence_level: string;
  created_at: string;
}

type Load = "loading" | "ready" | "error";

export default function HistoryPage() {
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [load, setLoad] = useState<Load>("loading");
  const [slow, setSlow] = useState(false);
  const [search, setSearch] = useState("");

  const fetchHistory = useCallback(() => {
    setLoad("loading");
    setSlow(false);
    const slowTimer = setTimeout(() => setSlow(true), 4000);
    fetch(`${API_BASE}/api/history`)
      .then((res) => {
        if (!res.ok) throw new Error(`API error: ${res.status}`);
        return res.json();
      })
      .then((data) => {
        setHistory(data.history || []);
        setLoad("ready");
      })
      .catch((err) => {
        console.error("Failed to load history", err);
        setLoad("error");
      })
      .finally(() => clearTimeout(slowTimer));
  }, []);

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  const filteredHistory = history.filter((item) => item.query.toLowerCase().includes(search.toLowerCase()));

  return (
    <div className="page">
      <Masthead />
      <main>
        <h1 className="display" style={{ fontSize: "clamp(2.25rem, 5vw, 3.75rem)" }}>
          Search history
        </h1>
        <p className="lede">Lookups this server has run recently, newest first. Open one to see its result again.</p>

        <div style={{ margin: "24px 0 16px" }}>
          <label className="history-filter">
            <Search size={18} aria-hidden="true" />
            <span className="visually-hidden">Filter recent searches</span>
            <input type="text" placeholder="Filter by company or commodity" value={search} onChange={(e) => setSearch(e.target.value)} />
          </label>
        </div>

        <div className="sheet" style={{ display: "block" }}>
          <div className="box" style={{ borderBottom: 0, borderRight: 0 }}>
            {load === "loading" && (
              <div role="status" aria-live="polite">
                <p className="prose-sm">Loading history…</p>
                {slow && (
                  <p className="wait-note">
                    Still loading. The server runs on a free host that sleeps when idle, so the first request can take about a minute.
                  </p>
                )}
              </div>
            )}

            {load === "error" && (
              <div role="alert">
                <p className="prose">The history could not be loaded. The server may still be waking up.</p>
                <button className="btn btn-line" style={{ marginTop: 14 }} onClick={fetchHistory}>
                  Try again
                </button>
              </div>
            )}

            {load === "ready" && filteredHistory.length === 0 && <p className="prose-sm">No recent searches found.</p>}

            {load === "ready" && filteredHistory.length > 0 && (
              <div className="table-wrap">
                <table className="ledger stack">
                  <thead>
                    <tr>
                      <th scope="col">Query</th>
                      <th scope="col" className="num">Score</th>
                      <th scope="col">Level</th>
                      <th scope="col">Confidence</th>
                      <th scope="col">When</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredHistory.map((item, idx) => {
                      // SQLite stores UTC as "YYYY-MM-DD HH:MM:SS" with no zone, which browsers read as local
                      // time: in India every entry looked 5.5 hours old.
                      const date = new Date(item.created_at.replace(" ", "T") + "Z");
                      const timeAgo = Math.floor((Date.now() - date.getTime()) / 60000);
                      const timeString =
                        timeAgo < 60 ? `${timeAgo}m ago` : timeAgo < 1440 ? `${Math.floor(timeAgo / 60)}h ago` : `${Math.floor(timeAgo / 1440)}d ago`;
                      const isCategory = item.query.startsWith("CATEGORY:");
                      const name = isCategory ? item.query.replace("CATEGORY: ", "") : item.query;

                      return (
                        <tr key={`${item.query}-${idx}`}>
                          <td className="strong head" data-label="Query">
                            <Link className="row-link" href={`/results/${encodeURIComponent(item.query)}`}>
                              {name}
                              {isCategory && <span className="fine" style={{ marginLeft: 8, fontWeight: 400 }}>commodity</span>}
                            </Link>
                          </td>
                          <td className="num strong" data-label="Score">{item.risk_score}</td>
                          <td data-label="Level">
                            <Stamp level={item.risk_level} />
                          </td>
                          <td data-label="Confidence" style={{ textTransform: "capitalize" }}>
                            {item.confidence_level.replace(/_/g, " ")}
                          </td>
                          <td data-label="When">{timeString}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </main>
      <Footer />
    </div>
  );
}
