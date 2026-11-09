"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import dynamic from "next/dynamic";
import { Download, ExternalLink, Globe } from "lucide-react";
import { analyzeRisk, RiskResponse } from "@/lib/api";
import { Box, Footer, Mark, Masthead, ScoreScale, Stamp, shortDate, type MarkKind } from "@/components/form";

const SupplyChainGraph = dynamic(() => import("@/components/SupplyChainGraph"), {
  ssr: false,
});

const SOURCING: Record<string, { mark: MarkKind; label: string }> = {
  confirmed: { mark: "solid", label: "Confirmed" },
  estimated: { mark: "hollow", label: "Estimated" },
  inferred: { mark: "dashed", label: "Inferred" },
  operational_only: { mark: "hollow", label: "Operations only" },
};

// Dataset kinds are fixed facts about the pipeline: Trase and Forest 500 are static files,
// Global Forest Watch is queried live, the company page is read at lookup time.
const SOURCE_INFO: Record<string, { name: string; kind: string }> = {
  csr: { name: "Company page", kind: "Read per lookup" },
  trase: { name: "Trase", kind: "Static dataset" },
  forest500: { name: "Forest 500", kind: "Static dataset" },
  gfw: { name: "Global Forest Watch", kind: "Live API" },
};

const TRADE = "Trase trade records";

function Evidence({ evidence }: { evidence?: string | null }) {
  if (evidence === TRADE) {
    return (
      <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
        <Mark kind="solid" /> Trade records
      </span>
    );
  }
  if (evidence) {
    return (
      <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
        <Mark kind="hollow" /> Producer country
      </span>
    );
  }
  return <span>None</span>;
}

function sourceMarkKind(status: string): MarkKind {
  if (status === "success") return "solid";
  if (status === "not_found" || status === "not_available") return "hollow";
  return "dashed";
}

export default function ResultsPage() {
  const params = useParams();
  const router = useRouter();
  const company = decodeURIComponent(params.company as string);
  const [data, setData] = useState<RiskResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [isExporting, setIsExporting] = useState(false);

  const handleExportPDF = async () => {
    setIsExporting(true);
    const element = document.getElementById("pdf-report-container");
    if (!element) {
      setIsExporting(false);
      return;
    }

    try {
      // Dynamically import to avoid SSR 'self is not defined' error
      const html2pdf = (await import("html2pdf.js")).default;

      const opt = {
        margin: 10,
        filename: `${company.replace(/[^a-z0-9]/gi, "_").toLowerCase()}_risk_report.pdf`,
        image: { type: "jpeg" as const, quality: 0.98 },
        html2canvas: { scale: 2, useCORS: true, backgroundColor: "#f2f2ee" },
        jsPDF: { unit: "mm" as const, format: "a4", orientation: "portrait" as const },
      };

      await html2pdf().set(opt).from(element).save();
    } catch (err) {
      console.error("PDF Export failed:", err);
    } finally {
      setIsExporting(false);
    }
  };

  useEffect(() => {
    analyzeRisk(company)
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [company]);

  if (loading) return <LoadingForm company={company} />;
  if (error) return <ErrorForm error={error} onBack={() => router.push("/")} onRetry={() => window.location.reload()} />;
  if (!data) return null;

  const csrSource = data.sources.find((s) => s.source_name === "csr");
  const csrCommodities = csrSource?.commodities_found || [];
  const anyFlag = Object.values(data.flags).some(Boolean);
  const flagItems: { text: string; warn?: boolean; on: boolean }[] = [
    { on: data.flags.no_csr_page_found, text: "No CSR or sustainability page found" },
    { on: data.flags.no_trase_data, text: "Company not found in the Trase datasets" },
    { on: data.flags.no_forest500_data, text: "Company not in the Forest 500 rankings" },
    { on: data.flags.no_gfw_data, text: "Global Forest Watch tree-cover-loss data unavailable" },
    { on: data.flags.low_confidence, warn: true, text: "Low confidence: limited data available" },
    { on: data.flags.no_commodities_detected, warn: true, text: "No deforestation-linked commodities detected" },
    { on: data.flags.no_regions_detected, warn: true, text: "No high-risk sourcing regions detected" },
  ];

  const exportButton = (
    <button onClick={handleExportPDF} disabled={isExporting}>
      <Download size={16} aria-hidden="true" />
      {isExporting ? "Exporting…" : "Export PDF"}
    </button>
  );

  return (
    <div className="page" id="pdf-report-container">
      <Masthead actions={exportButton} />
      <main className="sheet">
        <Box className="span-7">
          <h1 className="display subject">{data.company}</h1>
          <p className="lede" style={{ marginTop: 12 }}>
            Deforestation risk assessment
            {data.computed_at && <> · data as of {shortDate(data.computed_at)}</>}
          </p>
        </Box>

        <Box n={1} label="Risk score" className="span-5 edge row-2">
          <div className="score">
            {data.risk_score}
            <small>/ 100</small>
          </div>
          <div style={{ marginTop: 16 }}>
            <Stamp level={data.risk_level} large press />
          </div>
          <ScoreScale score={data.risk_score} />
          <p className="fine" style={{ marginTop: 14 }}>
            Built from the pairs in Box 6. Method and limits are in Box 8.
          </p>
        </Box>

        <Box n={2} label="Confidence" className="span-3">
          <div className="big-num">{data.confidence_score}%</div>
          <p className="fine" style={{ marginTop: 8, textTransform: "capitalize" }}>
            {data.confidence_level.replace(/_/g, " ")}
          </p>
        </Box>

        <Box n={3} label={`Commodities (${data.commodities.length})`} className="span-4">
          <ul className="chips">
            {data.commodities.map((c) => (
              <li key={c.name} className="chip">
                {c.name}
                {csrCommodities.includes(c.name) && (
                  <Globe size={13} aria-label="Named on the company's own website" role="img" />
                )}
              </li>
            ))}
          </ul>
          {csrCommodities.length > 0 && (
            <p className="legend">
              <span>
                <Globe size={13} aria-hidden="true" /> Named on the company&apos;s own website
              </span>
            </p>
          )}
        </Box>

        <Box n={4} label="Summary" className="span-7">
          <p className="prose">{data.summary}</p>
        </Box>

        <Box n={5} label="Gaps in the evidence" className="span-5 edge">
          {anyFlag ? (
            <ul className="gaps">
              {flagItems
                .filter((f) => f.on)
                .map((f) => (
                  <li key={f.text}>
                    <span className="w">{f.warn ? "Warning" : "Gap"}</span>
                    <span>{f.text}</span>
                  </li>
                ))}
            </ul>
          ) : (
            <p className="prose-sm">No gaps flagged for this lookup.</p>
          )}

          {data.operational_regions && data.operational_regions.length > 0 && (
            <div style={{ marginTop: 20 }}>
              <p className="label" style={{ marginBottom: 6 }}>Operational presence, not scored</p>
              <p className="prose-sm" style={{ marginBottom: 10 }}>
                Detected as markets, manufacturing or office locations, not raw-material sourcing origins. They are excluded from the score.
              </p>
              <ul className="chips">
                {data.operational_regions.map((r) => (
                  <li key={r.name} className="chip dashed-chip" title={r.evidence_source}>
                    {r.name}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </Box>


        {data.breakdown.length > 0 && (
          <Box n={6} label="Basis: commodity-country pairs the evidence supports" className="span-12">
            <div className="table-wrap">
              <table className="ledger stack">
                <thead>
                  <tr>
                    <th scope="col">Commodity</th>
                    <th scope="col">Country</th>
                    <th scope="col">Evidence</th>
                    <th scope="col" className="num">Weight</th>
                    <th scope="col" className="num">Country risk</th>
                    <th scope="col">Combined</th>
                  </tr>
                </thead>
                <tbody>
                  {data.breakdown.map((b, i) => (
                    <tr key={i}>
                      <td className="strong head" data-label="Commodity">
                        <span style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
                          {b.commodity}
                          {csrCommodities.includes(b.commodity) && (
                            <Globe size={13} aria-label="Named on the company's own website" role="img" />
                          )}
                        </span>
                      </td>
                      <td data-label="Country">{b.region}</td>
                      <td data-label="Evidence">
                        <Evidence evidence={b.evidence} />
                      </td>
                      <td className="num" data-label="Weight">{b.commodity_weight.toFixed(2)}</td>
                      <td className="num" data-label="Country risk">{b.region_risk.toFixed(2)}</td>
                      <td data-label="Combined">
                        <div className="combined">
                          <b>{b.combined_score}</b>
                          <span className="bar" aria-hidden="true">
                            <i style={{ width: `${Math.min(100, b.combined_score)}%` }} />
                          </span>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="legend">
              <span><Mark kind="solid" /> Trade records: a Trase record of that commodity leaving that country</span>
              <span><Mark kind="hollow" /> Producer country: the country is a known producer of it</span>
            </p>
          </Box>
        )}

        <Box n={7} label={`Sourcing regions (${data.regions.length})`} className="span-7">
          {data.regions.length > 0 ? (
            <div className="table-wrap">
              <table className="ledger stack">
                <thead>
                  <tr>
                    <th scope="col">Country</th>
                    <th scope="col">Tier</th>
                    <th scope="col" className="num">Base risk</th>
                    <th scope="col">Sourcing</th>
                  </tr>
                </thead>
                <tbody>
                  {data.regions.map((r) => {
                    const conf = SOURCING[r.sourcing_confidence] || SOURCING.inferred;
                    return (
                      <tr key={r.name}>
                        <td className="strong head" data-label="Country">{r.name}</td>
                        <td data-label="Tier" style={{ textTransform: "capitalize" }}>{r.risk_tier}</td>
                        <td className="num" data-label="Base risk">{r.base_risk.toFixed(2)}</td>
                        <td data-label="Sourcing">
                          <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }} title={r.evidence_source}>
                            <Mark kind={conf.mark} /> {conf.label}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="prose-sm">No sourcing regions were identified.</p>
          )}
          <p className="legend">
            <span><Mark kind="solid" /> Confirmed</span>
            <span><Mark kind="hollow" /> Estimated</span>
            <span><Mark kind="dashed" /> Inferred</span>
          </p>
        </Box>

        {data.methodology_note && (
          <Box n={8} label="Methodology" className="span-5 edge">
            <p className="prose-sm">{data.methodology_note}</p>
            <p className="prose-sm" style={{ marginTop: 10 }}>
              Trase and Forest 500 are static datasets. Only Global Forest Watch is queried live.
            </p>
          </Box>
        )}

        <Box n={9} label="Data sources" className="span-12">
          <div className="src-grid">
            {data.sources.map((s) => {
              const info = SOURCE_INFO[s.source_name] || { name: s.source_name.toUpperCase(), kind: "" };
              const csrEmpty = s.status === "success" && s.source_name === "csr" && s.commodities_found.length + s.regions_found.length === 0;
              const live = s.source_name === "gfw" && s.raw_data?.live ? (s.raw_data.live as Record<string, { latest_alert?: string | null }>) : null;
              const liveCount = live ? Object.keys(live).length : 0;
              const latest = live
                ? Object.values(live)
                    .map((v) => v.latest_alert)
                    .filter(Boolean)
                    .sort()
                : [];
              return (
                <div key={s.source_name} className="src">
                  <h3>
                    <Mark kind={sourceMarkKind(s.status)} />
                    {info.name}
                  </h3>
                  <p className="kind">{info.kind}</p>
                  <p>
                    {csrEmpty
                      ? "Page read; it names no commodities or countries"
                      : s.status === "success"
                      ? `${s.commodities_found.length + s.regions_found.length} entities found`
                      : s.error
                      ? s.error.slice(0, 50)
                      : s.status.replace(/_/g, " ")}
                  </p>
                  {s.status === "success" && s.source_name === "csr" && s.commodities_found.length > 0 && (
                    <ul className="chips" style={{ marginTop: 8 }}>
                      {s.commodities_found.map((c) => (
                        <li key={c} className="chip">{c}</li>
                      ))}
                    </ul>
                  )}
                  {liveCount > 0 && (
                    <p>
                      Live for {liveCount} countries{latest.length ? ` · latest alert ${latest[latest.length - 1]}` : ""}
                    </p>
                  )}
                  {s.status === "success" && s.source_name === "csr" && typeof s.raw_data?.url === "string" && (
                    <p>
                      <a href={s.raw_data.url} target="_blank" rel="noreferrer">
                        View scraped webpage <ExternalLink size={13} aria-hidden="true" style={{ verticalAlign: "-1px" }} />
                      </a>
                    </p>
                  )}
                </div>
              );
            })}
          </div>
          <p className="legend">
            <span><Mark kind="solid" /> Used</span>
            <span><Mark kind="hollow" /> Not found or unavailable</span>
            <span><Mark kind="dashed" /> Other status</span>
          </p>
        </Box>

        <Box n={10} label="Supply chain mapping" className="span-12">
          <p className="prose-sm" style={{ marginBottom: 14 }}>
            Country, commodity and company, as the evidence in Box 6 links them for {data.company}.
          </p>
          <div className="graph-scroll">
            <div className="graph-inner">
              <SupplyChainGraph company={data.company} breakdown={data.breakdown} />
            </div>
          </div>
          <p className="legend">
            <span>
              <svg width="26" height="8" aria-hidden="true"><line x1="0" y1="4" x2="26" y2="4" stroke="currentColor" strokeWidth="1.5" /></svg>
              <Mark kind="solid" /> Trade record
            </span>
            <span>
              <svg width="26" height="8" aria-hidden="true"><line x1="0" y1="4" x2="26" y2="4" stroke="currentColor" strokeWidth="1.5" strokeDasharray="4 3" /></svg>
              <Mark kind="hollow" /> Producer country
            </span>
          </p>
        </Box>
      </main>
      <Footer />
    </div>
  );
}

function LoadingForm({ company }: { company: string }) {
  const [seconds, setSeconds] = useState(0);
  useEffect(() => {
    const timer = setInterval(() => setSeconds((s) => s + 1), 1000);
    return () => clearInterval(timer);
  }, []);
  return (
    <div className="page">
      <Masthead />
      <main className="sheet" aria-busy="true">
        <Box className="span-7">
          <h1 className="display subject">{company}</h1>
          <p className="lede" style={{ marginTop: 12 }}>Assessment in progress</p>
        </Box>
        <Box label="Elapsed" className="span-5 edge">
          <div className="timer">{seconds} s</div>
        </Box>

        <Box label="What a lookup does" className="span-12">
          <p className="prose">
            A new lookup reads the company&apos;s sustainability page, matches Trase trade records and Forest 500 scores, and queries Global Forest Watch. It then
            scores the commodity-country pairs the evidence supports.
          </p>
          <p className="prose-sm" style={{ marginTop: 8 }}>
            Cached results answer in under a second. A new company usually takes 8 to 31 seconds.
          </p>
          <div role="status" aria-live="polite">
            {seconds >= 25 && (
              <p className="wait-note">
                Still working. The server runs on a free host that sleeps when idle, so a first request can take up to a minute longer. Results are cached
                afterwards.
              </p>
            )}
          </div>
        </Box>

        <Box label="Risk score" className="span-4" >
          <div className="blank" aria-hidden="true" />
        </Box>
        <Box label="Confidence" className="span-4">
          <div className="blank" aria-hidden="true" />
        </Box>
        <Box label="Commodities" className="span-4 edge">
          <div className="blank" aria-hidden="true" />
        </Box>
      </main>
      <Footer />
    </div>
  );
}

function ErrorForm({ error, onBack, onRetry }: { error: string; onBack: () => void; onRetry: () => void }) {
  return (
    <div className="page">
      <Masthead />
      <main className="sheet">
        <Box className="span-12">
          <h1 className="display subject" style={{ fontSize: "clamp(2rem, 5vw, 3.5rem)" }}>The assessment did not finish.</h1>
          <p className="lede" role="alert">
            {error === "Failed to fetch"
              ? "The analysis server did not answer. It runs on a free host that sleeps when idle; trying again usually works."
              : error}
          </p>
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginTop: 20 }}>
            <button className="btn" onClick={onRetry}>
              Try again
            </button>
            <button className="btn btn-line" onClick={onBack}>
              Back to search
            </button>
          </div>
        </Box>
      </main>
      <Footer />
    </div>
  );
}
