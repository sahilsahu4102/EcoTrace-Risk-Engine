import sys

filepath = "frontend/src/app/results/[company]/page.tsx"
with open(filepath, "r", encoding="utf-8") as f:
    code = f.read()

# 1. Imports
code = code.replace(
    'import { analyzeRisk, RiskResponse } from "@/lib/api";',
    '''import { analyzeRisk, RiskResponse } from "@/lib/api";
import dynamic from 'next/dynamic';
import html2pdf from 'html2pdf.js';
import { Download } from 'lucide-react';
const SupplyChainGraph = dynamic(() => import('@/components/SupplyChainGraph'), { ssr: false });'''
)

# 2. State & PDF handler
code = code.replace(
    '  const [error, setError] = useState("");',
    '''  const [error, setError] = useState("");
  const [isExporting, setIsExporting] = useState(false);

  const handleExportPDF = () => {
    setIsExporting(true);
    const element = document.getElementById("pdf-report-container");
    if (!element) return;
    
    const opt = {
      margin:       10,
      filename:     `${company.replace(/[^a-z0-9]/gi, '_').toLowerCase()}_risk_report.pdf`,
      image:        { type: 'jpeg', quality: 0.98 },
      html2canvas:  { scale: 2, useCORS: true, backgroundColor: '#0f172a' },
      jsPDF:        { unit: 'mm', format: 'a4', orientation: 'portrait' }
    };

    html2pdf().set(opt).from(element).save().then(() => setIsExporting(false));
  };'''
)

# 3. Export Button
code = code.replace(
    '''        <span className={`badge badge-${data.risk_level}`} style={{ marginLeft: "auto" }}>
          {data.risk_level}
        </span>
      </motion.div>''',
    '''        <span className={`badge badge-${data.risk_level}`} style={{ marginLeft: "auto" }}>
          {data.risk_level}
        </span>
        <button
          onClick={handleExportPDF}
          disabled={isExporting}
          data-html2canvas-ignore="true"
          style={{
            background: "var(--accent-emerald)",
            color: "#fff",
            border: "none",
            borderRadius: 8,
            padding: "8px 16px",
            fontSize: "0.875rem",
            fontWeight: 600,
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: 8,
            opacity: isExporting ? 0.7 : 1,
            boxShadow: "0 0 10px rgba(16, 185, 129, 0.2)",
            marginLeft: 16,
          }}
        >
          <Download size={16} />
          {isExporting ? "Exporting..." : "Export PDF"}
        </button>
      </motion.div>
      <div id="pdf-report-container" style={{ padding: "0 4px" }}>'''
)

# 4. SupplyChainGraph & close container
code = code.replace(
    '    </main>',
    '''
        {/* --- Phase 7 Feature: Supply Chain Graph --- */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6 }}
          className="glass-card"
          style={{ marginBottom: 24, padding: 24, marginTop: 24 }}
        >
          <h2 className="section-title" style={{ fontSize: "1rem", fontWeight: 600, marginBottom: 16, display: "flex", alignItems: "center", gap: 8 }}>
            <Globe size={18} color="var(--accent-emerald)" /> Supply Chain Mapping
          </h2>
          <p style={{ color: "var(--text-muted)", fontSize: "0.8125rem", marginBottom: 16 }}>
            Verified trade flows and geographical sourcing linked to {data.company}.
          </p>
          <div style={{ height: 400, width: "100%", position: "relative", borderRadius: 16, overflow: "hidden", border: "1px solid var(--border-color)", background: "var(--background)" }}>
            <SupplyChainGraph company={data.company} breakdown={data.breakdown} />
          </div>
        </motion.div>
      </div> {/* END pdf-report-container */}
    </main>'''
)

# 5. Add ignore tag to Top Left Back Button
code = code.replace(
    '          onClick={() => router.push("/")}',
    '''          onClick={() => router.push("/")}
          data-html2canvas-ignore="true"'''
)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(code)

print("Modification complete.")
