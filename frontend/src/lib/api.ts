const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface CommodityDetail {
  name: string;
  risk_weight: number;
  matched_keywords: string[];
}

export interface RegionDetail {
  name: string;
  iso_code: string;
  risk_tier: string;
  base_risk: number;
  linked_commodities: string[];
}

export interface CommodityRegionBreakdown {
  commodity: string;
  region: string;
  region_iso: string;
  commodity_weight: number;
  region_risk: number;
  combined_score: number;
}

export interface SourceResult {
  source_name: string;
  status: string;
  commodities_found: string[];
  regions_found: string[];
  raw_data?: Record<string, unknown>;
  error?: string;
}

export interface DisclosureFlags {
  no_csr_page_found: boolean;
  no_trase_data: boolean;
  no_forest500_data: boolean;
  no_gfw_data: boolean;
  low_confidence: boolean;
  no_commodities_detected: boolean;
  no_regions_detected: boolean;
}

export interface RiskResponse {
  company: string;
  risk_score: number;
  risk_level: string;
  confidence_score: number;
  confidence_level: string;
  commodities: CommodityDetail[];
  regions: RegionDetail[];
  breakdown: CommodityRegionBreakdown[];
  sources: SourceResult[];
  flags: DisclosureFlags;
  summary: string;
}

export async function analyzeRisk(company: string): Promise<RiskResponse> {
  const res = await fetch(`${API_BASE}/api/risk`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ company }),
  });

  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }

  return res.json();
}

export async function healthCheck(): Promise<Record<string, unknown>> {
  const res = await fetch(`${API_BASE}/health`);
  return res.json();
}
