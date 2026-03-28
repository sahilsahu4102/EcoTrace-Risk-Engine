"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { Search, TreePine, AlertTriangle, Globe } from "lucide-react";

const SUGGESTIONS = [
  { label: "Unilever", icon: "🧴" },
  { label: "Cargill", icon: "🌾" },
  { label: "JBS", icon: "🥩" },
  { label: "Wilmar", icon: "🌴" },
  { label: "Nestlé", icon: "☕" },
  { label: "Mondelez", icon: "🍫" },
];

export default function HomePage() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleSearch = (company: string) => {
    if (!company.trim()) return;
    setLoading(true);
    router.push(`/results/${encodeURIComponent(company.trim())}`);
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
      }}
    >
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
          How risky is your
          <br />
          supply chain?
        </h1>

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

        {/* Search Bar */}
        <motion.form
          onSubmit={(e) => {
            e.preventDefault();
            handleSearch(query);
          }}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          style={{ position: "relative", marginBottom: 24 }}
        >
          <Search
            size={20}
            style={{
              position: "absolute",
              left: 20,
              top: "50%",
              transform: "translateY(-50%)",
              color: "var(--text-muted)",
              pointerEvents: "none",
            }}
          />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Enter a company name..."
            className="search-input"
            style={{ paddingLeft: 52 }}
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
                position: "absolute",
                right: 8,
                top: "50%",
                transform: "translateY(-50%)",
                background: "var(--accent-emerald)",
                color: "#fff",
                border: "none",
                borderRadius: 12,
                padding: "12px 24px",
                fontWeight: 600,
                cursor: "pointer",
                fontSize: "0.875rem",
              }}
            >
              {loading ? "Analyzing..." : "Analyze"}
            </motion.button>
          )}
        </motion.form>

        {/* Suggestion Chips */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.6 }}
          style={{
            display: "flex",
            flexWrap: "wrap",
            gap: 8,
            justifyContent: "center",
          }}
        >
          <span
            style={{
              color: "var(--text-muted)",
              fontSize: "0.8125rem",
              alignSelf: "center",
              marginRight: 4,
            }}
          >
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
