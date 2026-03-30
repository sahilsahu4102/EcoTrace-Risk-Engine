"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { Search, ArrowLeft, Clock, Activity, ShieldAlert, CheckCircle2 } from "lucide-react";

interface HistoryItem {
  query: string;
  risk_score: number;
  risk_level: string;
  confidence_score: number;
  confidence_level: string;
  created_at: string;
}

export default function HistoryPage() {
  const router = useRouter();
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  useEffect(() => {
    fetch("http://localhost:8000/api/history")
      .then((res) => res.json())
      .then((data) => {
        setHistory(data.history || []);
        setLoading(false);
      })
      .catch((err) => {
        console.error("Failed to load history", err);
        setLoading(false);
      });
  }, []);

  const getRiskColor = (level: string) => {
    switch (level) {
      case "critical": return "#ef4444";
      case "high": return "#f97316";
      case "moderate": return "#f59e0b";
      case "low": return "#22c55e";
      default: return "#3b82f6";
    }
  };

  const filteredHistory = history.filter(item => 
    item.query.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <main style={{ minHeight: "100vh", padding: "40px 20px", maxWidth: 1000, margin: "0 auto" }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 32 }}>
        <button
          onClick={() => router.push("/")}
          style={{
            background: "rgba(255,255,255,0.05)",
            border: "1px solid rgba(255,255,255,0.1)",
            borderRadius: 12,
            padding: "10px 12px",
            cursor: "pointer",
            color: "var(--text-secondary)",
            display: "flex",
          }}
        >
          <ArrowLeft size={18} />
        </button>
        <div>
          <h1 style={{ fontSize: "1.75rem", fontWeight: 700, display: "flex", alignItems: "center", gap: 12 }}>
            <Clock size={24} color="var(--accent-emerald)" />
            Search History
          </h1>
          <p style={{ color: "var(--text-muted)", fontSize: "0.875rem", marginTop: 4 }}>
            Recently analyzed supply chains and commodity baseline profiles.
          </p>
        </div>
      </div>

      {/* Control Bar */}
      <div className="glass-card" style={{ padding: "16px", marginBottom: 24, display: "flex", alignItems: "center" }}>
        <div style={{ display: "flex", alignItems: "center", background: "rgba(0,0,0,0.2)", borderRadius: 8, padding: "8px 12px", flex: 1, border: "1px solid rgba(255,255,255,0.05)" }}>
          <Search size={18} color="var(--text-muted)" style={{ marginRight: 8 }} />
          <input 
            type="text" 
            placeholder="Filter recent searches..." 
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{ border: "none", background: "transparent", color: "#fff", outline: "none", width: "100%", fontSize: "0.9rem" }}
          />
        </div>
      </div>

      {/* List */}
      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {loading ? (
           <div style={{ textAlign: "center", padding: 60, color: "var(--text-muted)" }}>Loading history...</div>
        ) : filteredHistory.length === 0 ? (
           <div style={{ textAlign: "center", padding: 60, color: "var(--text-muted)", background: "rgba(255,255,255,0.02)", borderRadius: 16 }}>
              No recent searches found.
           </div>
        ) : (
          filteredHistory.map((item, idx) => {
            const date = new Date(item.created_at);
            const timeAgo = Math.floor((Date.now() - date.getTime()) / 60000);
            const timeString = timeAgo < 60 ? `${timeAgo}m ago` : timeAgo < 1440 ? `${Math.floor(timeAgo/60)}h ago` : `${Math.floor(timeAgo/1440)}d ago`;

            return (
              <motion.div 
                key={`${item.query}-${idx}`}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: idx * 0.05 }}
                className="glass-card"
                onClick={() => router.push(`/results/${encodeURIComponent(item.query)}`)}
                style={{
                  padding: "20px 24px",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  cursor: "pointer",
                  border: "1px solid rgba(255,255,255,0.05)",
                  transition: "all 0.2s"
                }}
                onMouseOver={(e) => e.currentTarget.style.borderColor = "var(--accent-emerald)"}
                onMouseOut={(e) => e.currentTarget.style.borderColor = "rgba(255,255,255,0.05)"}
              >
                <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                  <div style={{ fontSize: "1.1rem", fontWeight: 600, color: "var(--text-primary)" }}>
                    {item.query.startsWith("CATEGORY:") ? item.query.replace("CATEGORY: ", "📦 Commodity: ") : item.query}
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: 16, fontSize: "0.8rem", color: "var(--text-muted)" }}>
                    <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
                      <Activity size={14} /> Score: {item.risk_score}/100
                    </span>
                    <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
                      <ShieldAlert size={14} /> Conf: {item.confidence_level}
                    </span>
                    <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
                       <Clock size={14} /> {timeString}
                    </span>
                  </div>
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
                  <span 
                    className={`badge badge-${item.risk_level}`} 
                    style={{ fontSize: "0.75rem", background: getRiskColor(item.risk_level) + "20", color: getRiskColor(item.risk_level), border: `1px solid ${getRiskColor(item.risk_level)}40` }}
                  >
                    {item.risk_level.toUpperCase()}
                  </span>
                </div>
              </motion.div>
            );
          })
        )}
      </div>
    </main>
  );
}
