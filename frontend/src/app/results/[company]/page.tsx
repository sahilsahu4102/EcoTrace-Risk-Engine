"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { motion } from "framer-motion";
import {
  ArrowLeft,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  TreePine,
  Globe,
  Shield,
  BarChart3,
  Info,
} from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Cell,
} from "recharts";
import { analyzeRisk, RiskResponse } from "@/lib/api";

const RISK_COLORS: Record<string, string> = {
  critical: "#ef4444",
  high: "#f97316",
  moderate: "#f59e0b",
  low: "#22c55e",
  minimal: "#3b82f6",
};

const TIER_COLORS: Record<string, string> = {
  critical: "#ef4444",
  high: "#f97316",
  moderate: "#fbbf24",
  lower: "#4ade80",
};

function ScoreGauge({ score, level }: { score: number; level: string }) {
  const color = RISK_COLORS[level] || "#94a3b8";
  const circumference = 2 * Math.PI * 54;
  const offset = circumference - (score / 100) * circumference;

  return (
    <div style={{ position: "relative", width: 140, height: 140 }}>
      <svg width="140" height="140" viewBox="0 0 140 140">
        <circle
          cx="70" cy="70" r="54"
          fill="none"
          stroke="rgba(255,255,255,0.06)"
          strokeWidth="12"
        />
        <motion.circle
          cx="70" cy="70" r="54"
          fill="none"
          stroke={color}
          strokeWidth="12"
          strokeLinecap="round"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: offset }}
          transition={{ duration: 1.5, ease: "easeOut" }}
          transform="rotate(-90 70 70)"
          style={{ filter: `drop-shadow(0 0 8px ${color}40)` }}
        />
      </svg>
      <div
        style={{
          position: "absolute",
          inset: 0,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <motion.span
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
          style={{ fontSize: "2rem", fontWeight: 800, color }}
        >
          {score}
        </motion.span>
        <span style={{ fontSize: "0.7rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.1em" }}>
          / 100
        </span>
      </div>
    </div>
  );
}

function SourceBadge({ status }: { status: string }) {
  if (status === "success") return <CheckCircle2 size={14} color="#22c55e" />;
  if (status === "not_found" || status === "not_available") return <XCircle size={14} color="#64748b" />;
  return <AlertTriangle size={14} color="#f59e0b" />;
}

export default function ResultsPage() {
  const params = useParams();
  const router = useRouter();
  const company = decodeURIComponent(params.company as string);
  const [data, setData] = useState<RiskResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    analyzeRisk(company)
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [company]);

  if (loading) return <LoadingSkeleton company={company} />;
  if (error) return <ErrorScreen error={error} onBack={() => router.push("/")} />;
  if (!data) return null;

  const breakdownChartData = data.breakdown.slice(0, 8).map((b) => ({
    name: `${b.commodity.split("/")[0].trim().slice(0, 8)} × ${b.region.slice(0, 8)}`,
    score: b.combined_score,
    color: b.combined_score >= 80 ? "#ef4444" : b.combined_score >= 60 ? "#f97316" : b.combined_score >= 40 ? "#f59e0b" : "#22c55e",
  }));

  const regionRadarData = data.regions.slice(0, 6).map((r) => ({
    region: r.name.length > 12 ? r.name.slice(0, 12) + "…" : r.name,
    risk: Math.round(r.base_risk * 100),
  }));

  return (
    <main style={{ minHeight: "100vh", padding: "24px 20px", maxWidth: 1200, margin: "0 auto" }}>
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 32 }}
      >
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
          <h1 style={{ fontSize: "1.5rem", fontWeight: 700 }}>{data.company}</h1>
          <p style={{ color: "var(--text-muted)", fontSize: "0.8125rem" }}>
            Deforestation Risk Assessment
          </p>
        </div>
        <span className={`badge badge-${data.risk_level}`} style={{ marginLeft: "auto" }}>
          {data.risk_level}
        </span>
      </motion.div>

      {/* Metric Cards Row */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 16, marginBottom: 24 }}>
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="glass-card metric-card" style={{ alignItems: "center" }}>
          <span className="metric-label">Risk Score</span>
          <ScoreGauge score={data.risk_score} level={data.risk_level} />
        </motion.div>

        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }} className="glass-card metric-card">
          <span className="metric-label">Confidence</span>
          <span className="metric-value" style={{ color: data.confidence_score >= 60 ? "#22c55e" : data.confidence_score >= 30 ? "#f59e0b" : "#ef4444" }}>
            {data.confidence_score}%
          </span>
          <span className={`badge badge-${data.confidence_score >= 60 ? "low" : data.confidence_score >= 30 ? "moderate" : "critical"}`}>
            {data.confidence_level}
          </span>
        </motion.div>

        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }} className="glass-card metric-card">
          <span className="metric-label">Commodities</span>
          <span className="metric-value">{data.commodities.length}</span>
          <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
            {data.commodities.slice(0, 3).map((c) => (
              <span key={c.name} style={{ fontSize: "0.75rem", color: "var(--text-secondary)", background: "rgba(255,255,255,0.05)", padding: "2px 8px", borderRadius: 6 }}>
                {c.name}
              </span>
            ))}
          </div>
        </motion.div>

        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }} className="glass-card metric-card">
          <span className="metric-label">Regions</span>
          <span className="metric-value">{data.regions.length}</span>
          <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
            {data.regions.slice(0, 3).map((r) => (
              <span key={r.name} style={{ fontSize: "0.75rem", color: TIER_COLORS[r.risk_tier] || "#94a3b8", background: "rgba(255,255,255,0.05)", padding: "2px 8px", borderRadius: 6 }}>
                {r.name}
              </span>
            ))}
          </div>
        </motion.div>
      </div>

      {/* Summary */}
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.5 }} className="glass-card" style={{ padding: 24, marginBottom: 24, display: "flex", gap: 12 }}>
        <Info size={18} color="var(--accent-blue)" style={{ flexShrink: 0, marginTop: 2 }} />
        <p style={{ color: "var(--text-secondary)", fontSize: "0.9375rem", lineHeight: 1.7 }}>
          {data.summary}
        </p>
      </motion.div>

      {/* Charts Row */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(350px, 1fr))", gap: 16, marginBottom: 24 }}>
        {/* Breakdown Chart */}
        {breakdownChartData.length > 0 && (
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.6 }} className="glass-card" style={{ padding: 24 }}>
            <h3 style={{ fontSize: "0.875rem", fontWeight: 600, marginBottom: 20, display: "flex", alignItems: "center", gap: 8 }}>
              <BarChart3 size={16} color="var(--accent-emerald)" />
              Commodity × Region Risk
            </h3>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={breakdownChartData} layout="vertical" margin={{ left: 0, right: 16 }}>
                <XAxis type="number" domain={[0, 100]} tick={{ fill: "#64748b", fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis type="category" dataKey="name" tick={{ fill: "#94a3b8", fontSize: 11 }} width={120} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={{ background: "#1e293b", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8, color: "#f1f5f9" }} />
                <Bar dataKey="score" radius={[0, 6, 6, 0]} barSize={20}>
                  {breakdownChartData.map((entry, i) => (
                    <Cell key={i} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </motion.div>
        )}

        {/* Region Radar */}
        {regionRadarData.length >= 3 && (
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.7 }} className="glass-card" style={{ padding: 24 }}>
            <h3 style={{ fontSize: "0.875rem", fontWeight: 600, marginBottom: 20, display: "flex", alignItems: "center", gap: 8 }}>
              <Globe size={16} color="var(--accent-blue)" />
              Regional Risk Profile
            </h3>
            <ResponsiveContainer width="100%" height={250}>
              <RadarChart data={regionRadarData}>
                <PolarGrid stroke="rgba(255,255,255,0.08)" />
                <PolarAngleAxis dataKey="region" tick={{ fill: "#94a3b8", fontSize: 11 }} />
                <PolarRadiusAxis domain={[0, 100]} tick={false} axisLine={false} />
                <Radar dataKey="risk" stroke="#10b981" fill="#10b981" fillOpacity={0.2} strokeWidth={2} />
              </RadarChart>
            </ResponsiveContainer>
          </motion.div>
        )}
      </div>

      {/* Breakdown Table */}
      {data.breakdown.length > 0 && (
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.8 }} className="glass-card" style={{ padding: 24, marginBottom: 24, overflowX: "auto" }}>
          <h3 style={{ fontSize: "0.875rem", fontWeight: 600, marginBottom: 16, display: "flex", alignItems: "center", gap: 8 }}>
            <Shield size={16} color="var(--accent-amber)" />
            Risk Breakdown
          </h3>
          <table className="data-table">
            <thead>
              <tr>
                <th>Commodity</th>
                <th>Region</th>
                <th>Weight</th>
                <th>Region Risk</th>
                <th>Combined</th>
                <th style={{ width: 120 }}>Score</th>
              </tr>
            </thead>
            <tbody>
              {data.breakdown.map((b, i) => (
                <tr key={i}>
                  <td style={{ fontWeight: 500, color: "var(--text-primary)" }}>{b.commodity}</td>
                  <td>
                    <span style={{ color: TIER_COLORS[data.regions.find((r) => r.name === b.region)?.risk_tier || "lower"] }}>
                      {b.region}
                    </span>
                  </td>
                  <td>{b.commodity_weight.toFixed(2)}</td>
                  <td>{b.region_risk.toFixed(2)}</td>
                  <td style={{ fontWeight: 600, color: b.combined_score >= 80 ? "#ef4444" : b.combined_score >= 60 ? "#f97316" : b.combined_score >= 40 ? "#f59e0b" : "#22c55e" }}>
                    {b.combined_score}
                  </td>
                  <td>
                    <div className="score-bar-bg">
                      <div
                        className="score-bar-fill"
                        style={{
                          width: `${b.combined_score}%`,
                          background: b.combined_score >= 80 ? "#ef4444" : b.combined_score >= 60 ? "#f97316" : b.combined_score >= 40 ? "#f59e0b" : "#22c55e",
                        }}
                      />
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </motion.div>
      )}

      {/* Disclosure Flags */}
      {Object.values(data.flags).some(Boolean) && (
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.9 }} className="glass-card" style={{ padding: 24, marginBottom: 24 }}>
          <h3 style={{ fontSize: "0.875rem", fontWeight: 600, marginBottom: 12, display: "flex", alignItems: "center", gap: 8 }}>
            <AlertTriangle size={16} color="var(--accent-amber)" />
            Disclosure Flags
          </h3>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {data.flags.no_csr_page_found && <FlagItem label="No CSR/sustainability page found" />}
            {data.flags.no_trase_data && <FlagItem label="Company not found in Trase datasets" />}
            {data.flags.no_forest500_data && <FlagItem label="Company not in Forest 500 rankings" />}
            {data.flags.no_gfw_data && <FlagItem label="GFW tree cover loss data unavailable" />}
            {data.flags.low_confidence && <FlagItem label="Low confidence — limited data available" warn />}
            {data.flags.no_commodities_detected && <FlagItem label="No deforestation-linked commodities detected" warn />}
            {data.flags.no_regions_detected && <FlagItem label="No high-risk sourcing regions detected" warn />}
          </div>
        </motion.div>
      )}

      {/* Data Sources */}
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 1.0 }} className="glass-card" style={{ padding: 24 }}>
        <h3 style={{ fontSize: "0.875rem", fontWeight: 600, marginBottom: 16, display: "flex", alignItems: "center", gap: 8 }}>
          <TreePine size={16} color="var(--accent-emerald)" />
          Data Sources
        </h3>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 12 }}>
          {data.sources.map((s) => (
            <div
              key={s.source_name}
              style={{
                padding: 16,
                borderRadius: 12,
                background: "rgba(255,255,255,0.02)",
                border: "1px solid rgba(255,255,255,0.05)",
                display: "flex",
                alignItems: "center",
                gap: 10,
              }}
            >
              <SourceBadge status={s.status} />
              <div>
                <div style={{ fontSize: "0.8125rem", fontWeight: 600, color: "var(--text-primary)", textTransform: "uppercase" }}>
                  {s.source_name}
                </div>
                <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                  {s.status === "success"
                    ? `${s.commodities_found.length + s.regions_found.length} entities found`
                    : s.error
                    ? s.error.slice(0, 50)
                    : s.status.replace("_", " ")}
                </div>
              </div>
            </div>
          ))}
        </div>
      </motion.div>
    </main>
  );
}

function FlagItem({ label, warn = false }: { label: string; warn?: boolean }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: "0.8125rem", color: warn ? "#f59e0b" : "var(--text-muted)" }}>
      {warn ? <AlertTriangle size={14} /> : <Info size={14} />}
      {label}
    </div>
  );
}

function LoadingSkeleton({ company }: { company: string }) {
  return (
    <main style={{ minHeight: "100vh", padding: "24px 20px", maxWidth: 1200, margin: "0 auto" }}>
      <div style={{ marginBottom: 32 }}>
        <h1 style={{ fontSize: "1.5rem", fontWeight: 700 }}>{company}</h1>
        <p style={{ color: "var(--text-muted)", fontSize: "0.875rem" }}>Analyzing deforestation risk...</p>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 16 }}>
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="glass-card" style={{ padding: 24 }}>
            <div className="skeleton" style={{ height: 16, width: "60%", marginBottom: 12 }} />
            <div className="skeleton" style={{ height: 40, width: "40%", marginBottom: 8 }} />
            <div className="skeleton" style={{ height: 12, width: "80%" }} />
          </div>
        ))}
      </div>
      <div className="glass-card" style={{ padding: 24, marginTop: 16 }}>
        <div className="skeleton" style={{ height: 16, width: "40%", marginBottom: 16 }} />
        <div className="skeleton" style={{ height: 200, width: "100%" }} />
      </div>
    </main>
  );
}

function ErrorScreen({ error, onBack }: { error: string; onBack: () => void }) {
  return (
    <main style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", padding: 20 }}>
      <div className="glass-card" style={{ padding: 40, textAlign: "center", maxWidth: 440 }}>
        <AlertTriangle size={40} color="#ef4444" style={{ marginBottom: 16 }} />
        <h2 style={{ fontSize: "1.25rem", fontWeight: 700, marginBottom: 8 }}>Analysis Failed</h2>
        <p style={{ color: "var(--text-muted)", fontSize: "0.875rem", marginBottom: 24 }}>{error}</p>
        <button
          onClick={onBack}
          style={{
            background: "var(--accent-emerald)",
            color: "#fff",
            border: "none",
            borderRadius: 12,
            padding: "12px 32px",
            fontWeight: 600,
            cursor: "pointer",
          }}
        >
          Back to Search
        </button>
      </div>
    </main>
  );
}
