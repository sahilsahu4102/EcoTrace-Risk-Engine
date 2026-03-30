"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { Search, TreePine, AlertTriangle, Globe, Clock } from "lucide-react";

const SUGGESTIONS = [
  { label: "Unilever", icon: "🧴" },
  { label: "Cargill", icon: "🌾" },
  { label: "JBS", icon: "🥩" },
  { label: "Wilmar", icon: "🌴" },
  { label: "Nestlé", icon: "☕" },
  { label: "Palm Oil", icon: "🌴" },
  { label: "Cocoa", icon: "🍫" },
  { label: "Soy", icon: "🌾" },
];

export default function HomePage() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [recentSearches, setRecentSearches] = useState<string[]>([]);
  const router = useRouter();

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
      const updated = [term, ...recentSearches.filter(s => s.toLowerCase() !== term.toLowerCase())].slice(0, 5);
      localStorage.setItem("ecotrace_recent", JSON.stringify(updated));
      setRecentSearches(updated);
    } catch (e) {
      console.error("Failed to save history", e);
    }

    setLoading(true);
    router.push(`/results/${encodeURIComponent(term)}`);
  };

  return (
    <main
      style={{
        minHeight: "100vh",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "40px 20px",
        position: "relative",
      }}
    >
      {/* Top right history button */}
      <motion.div 
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.1 }}
        style={{ position: 'absolute', top: 24, right: 24 }}
      >
        <button
           onClick={() => router.push('/history')}
           style={{
              background: 'rgba(255,255,255,0.05)',
              border: '1px solid rgba(255,255,255,0.1)',
              borderRadius: 20,
              padding: '8px 16px',
              color: 'var(--text-secondary)',
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              fontSize: '0.875rem',
              cursor: 'pointer',
           }}
        >
          <Clock size={16} />
          Global History
        </button>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, ease: "easeOut" }}
        style={{ textAlign: "center", maxWidth: 720, width: "100%" }}
      >
        {/* Logo */}
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ delay: 0.2, type: "spring", stiffness: 200 }}
          style={{
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            width: 72,
            height: 72,
            borderRadius: 20,
            background: "rgba(16, 185, 129, 0.1)",
            border: "1px solid rgba(16, 185, 129, 0.2)",
            marginBottom: 32,
          }}
        >
          <TreePine size={36} color="#10b981" />
        </motion.div>

        {/* Title */}
        <h1
          style={{
            fontSize: "clamp(2rem, 5vw, 3.5rem)",
            fontWeight: 800,
            lineHeight: 1.1,
            marginBottom: 16,
            background: "linear-gradient(135deg, #f1f5f9 0%, #94a3b8 100%)",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
          }}
        >
          EcoTrace-Risk-Engine
        </h1>

        <div style={{ fontSize: "1.5rem", fontWeight: 600, color: "var(--text-secondary)", marginBottom: 12 }}>
          How risky is your supply chain?
        </div>

        {/* Subtitle */}
        <p
          style={{
            color: "var(--text-secondary)",
            fontSize: "1.125rem",
            marginBottom: 40,
            lineHeight: 1.6,
          }}
        >
          Analyze deforestation risk using real data from{" "}
          <span style={{ color: "var(--accent-emerald)" }}>Trase</span>,{" "}
          <span style={{ color: "var(--accent-blue)" }}>Forest 500</span>, and{" "}
          <span style={{ color: "var(--accent-amber)" }}>
            Global Forest Watch
          </span>
        </p>

        {/* Search Bar - Flexbox fix for the generic transform clipping issue */}
        <motion.form
          onSubmit={(e) => {
            e.preventDefault();
            handleSearch(query);
          }}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          style={{
            display: "flex",
            alignItems: "center",
            background: "var(--card-bg)",
            border: "1px solid var(--border-color)",
            borderRadius: 16,
            padding: "8px 8px 8px 24px",
            boxShadow: "0 8px 32px rgba(0, 0, 0, 0.2)",
            width: "100%",
            maxWidth: 500,
            margin: "0 auto 24px auto",
          }}
        >
          <Search size={20} style={{ color: "var(--text-muted)", flexShrink: 0 }} />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Enter company name or product category (e.g., Palm Oil)..."
            style={{ 
              flex: 1,
              border: "none",
              outline: "none",
              background: "transparent",
              padding: "12px 16px",
              fontSize: "1rem",
              color: "var(--text-primary)",
              minWidth: 0, // allows input to shrink in flex containers
            }}
            disabled={loading}
            autoFocus
          />
          {query.trim() && (
            <motion.button
              type="submit"
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              disabled={loading}
              style={{
                background: "var(--accent-emerald)",
                color: "#fff",
                border: "none",
                borderRadius: 12,
                padding: "12px 24px",
                fontWeight: 600,
                cursor: "pointer",
                fontSize: "0.875rem",
                flexShrink: 0,
              }}
            >
              {loading ? "Analyzing..." : "Analyze"}
            </motion.button>
          )}
        </motion.form>

        {/* Memory/History Chips Context */}
        <motion.div
           initial={{ opacity: 0 }}
           animate={{ opacity: 1 }}
           transition={{ delay: 0.5 }}
           style={{
             display: "flex",
             flexDirection: "column",
             gap: 16,
             alignItems: "center",
           }}
        >
          {recentSearches.length > 0 && (
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8, justifyContent: "center" }}>
              <span style={{ color: "var(--text-muted)", fontSize: "0.8125rem", alignSelf: "center", marginRight: 4, display: "flex", alignItems: "center", gap: 4 }}>
                <Clock size={14} /> Recent:
              </span>
              {recentSearches.map((s) => (
                <button
                  key={`recent-${s}`}
                  className="chip"
                  onClick={() => handleSearch(s)}
                  disabled={loading}
                  style={{ background: "rgba(255, 255, 255, 0.05)" }}
                >
                  {s}
                </button>
              ))}
            </div>
          )}

          {/* Suggestion Chips */}
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8, justifyContent: "center" }}>
            <span style={{ color: "var(--text-muted)", fontSize: "0.8125rem", alignSelf: "center", marginRight: 4 }}>
              Try:
            </span>
            {SUGGESTIONS.map((s) => (
              <button
                key={s.label}
                className="chip"
                onClick={() => handleSearch(s.label)}
                disabled={loading}
              >
                <span>{s.icon}</span>
                {s.label}
              </button>
            ))}
          </div>
        </motion.div>

        {/* Stats Bar */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.8 }}
          style={{
            marginTop: 64,
            display: "flex",
            justifyContent: "center",
            gap: 48,
            flexWrap: "wrap",
          }}
        >
          {[
            { icon: <Globe size={16} />, label: "40+ Countries" },
            { icon: <AlertTriangle size={16} />, label: "15 Commodities" },
            { icon: <TreePine size={16} />, label: "4 Data Sources" },
          ].map((stat) => (
            <div
              key={stat.label}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                color: "var(--text-muted)",
                fontSize: "0.8125rem",
              }}
            >
              {stat.icon}
              {stat.label}
            </div>
          ))}
        </motion.div>
      </motion.div>
    </main>
  );
}
