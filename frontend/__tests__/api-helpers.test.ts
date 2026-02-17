import { describe, it, expect } from "vitest";
import { getComprehensiveAnalysis, hasComprehensiveAnalysis } from "@/lib/api";
import type { AnalysisResponse, ComprehensiveAnalysis } from "@/types/analysis";

// Minimal mock factory for AnalysisResponse
function createMockResponse(
  overrides: Partial<AnalysisResponse> = {}
): AnalysisResponse {
  const defaultCitation = {
    line_item: "",
    filing_type: "",
    period: "",
    raw_value: null,
    source: "",
  };
  const defaultMetricComponent = { value: null, citation: defaultCitation };

  const defaultComprehensiveAnalysis: ComprehensiveAnalysis = {
    beneish_m_score: {
      composite: null,
      interpretation: null,
      components: {
        dsri: defaultMetricComponent,
        gmi: defaultMetricComponent,
        aqi: defaultMetricComponent,
        sgi: defaultMetricComponent,
        depi: defaultMetricComponent,
        sgai: defaultMetricComponent,
        lvgi: defaultMetricComponent,
        tata: defaultMetricComponent,
      },
      thresholds: { likely_manipulator: -1.78, grey_zone: [-2.22, -1.78] },
    },
    altman_z_score: {
      standard: { score: null, zone: null, components: {} },
      saas_modified: { score: null, zone: null, components: {} },
    },
    profitability: {
      gross_margin: defaultMetricComponent,
      operating_margin: defaultMetricComponent,
      net_margin: defaultMetricComponent,
      roe: defaultMetricComponent,
      roa: defaultMetricComponent,
      roic: defaultMetricComponent,
    },
    leverage: {
      debt_to_equity: defaultMetricComponent,
      interest_coverage: defaultMetricComponent,
      current_ratio: defaultMetricComponent,
      quick_ratio: defaultMetricComponent,
      net_debt_to_ebitda: defaultMetricComponent,
    },
    cash_flow: {
      fcf_yield: defaultMetricComponent,
      ocf_to_net_income: defaultMetricComponent,
      fcf_margin: defaultMetricComponent,
      capex_to_revenue: defaultMetricComponent,
    },
    growth: {
      revenue_growth_yoy: defaultMetricComponent,
      earnings_growth_yoy: defaultMetricComponent,
      fcf_growth_yoy: defaultMetricComponent,
      revenue_cagr_3y: defaultMetricComponent,
    },
    valuation: {
      pe_trailing: defaultMetricComponent,
      pe_forward: defaultMetricComponent,
      ev_to_ebitda: defaultMetricComponent,
      price_to_fcf: defaultMetricComponent,
      price_to_sales: defaultMetricComponent,
      peg_ratio: defaultMetricComponent,
    },
    shareholder_returns: {
      dividend_yield: defaultMetricComponent,
      payout_ratio: defaultMetricComponent,
    },
    sentiment: {
      analyst_rating: defaultMetricComponent,
      analyst_count: null,
      analyst_recommendation: null,
      short_ratio: defaultMetricComponent,
      short_percent_float: defaultMetricComponent,
      institutional_pct: defaultMetricComponent,
      insider_pct: defaultMetricComponent,
    },
    sector_category: "GENERAL",
    sector_specific: null,
  };

  return {
    ticker: "AAPL",
    company_profile: {
      name: "Apple Inc.",
      sector: "Technology",
      industry: "Consumer Electronics",
      market_cap: 3.2e12,
      full_time_employees: 164000,
    },
    forensic_metrics: {
      beneish_m_score: defaultComprehensiveAnalysis.beneish_m_score,
      altman_z_score: defaultComprehensiveAnalysis.altman_z_score,
      rule_of_40: {
        score: null,
        revenue_growth_percent: null,
        fcf_margin_percent: null,
        interpretation: null,
        citations: {},
      },
      magic_number: {
        score: null,
        net_new_arr: null,
        sales_and_marketing_spend: null,
        interpretation: null,
        citations: {},
      },
    },
    comprehensive_analysis: defaultComprehensiveAnalysis,
    report: { markdown: "", generated_at: "", model: "" },
    data_sources: {
      provider: "yfinance",
      periods: [],
      fetched_at: "",
      cache_hit: false,
    },
    ...overrides,
  };
}

describe("getComprehensiveAnalysis", () => {
  it("returns comprehensive_analysis when present", () => {
    const response = createMockResponse();
    const result = getComprehensiveAnalysis(response);
    expect(result).not.toBeNull();
    expect(result?.sector_category).toBe("GENERAL");
  });

  it("returns null when comprehensive_analysis is undefined", () => {
    // Simulate an old API response that does not include comprehensive_analysis
    const response = createMockResponse();
    // Force undefined to simulate backward compat scenario
    (response as unknown as Record<string, unknown>).comprehensive_analysis = undefined;
    const result = getComprehensiveAnalysis(response as AnalysisResponse);
    expect(result).toBeNull();
  });
});

describe("hasComprehensiveAnalysis", () => {
  it("returns true when comprehensive_analysis has profitability data", () => {
    const response = createMockResponse();
    expect(hasComprehensiveAnalysis(response)).toBe(true);
  });

  it("returns false when comprehensive_analysis is null/undefined", () => {
    const response = createMockResponse();
    (response as unknown as Record<string, unknown>).comprehensive_analysis = null;
    expect(hasComprehensiveAnalysis(response as AnalysisResponse)).toBe(false);
  });

  it("returns false when profitability is null", () => {
    const response = createMockResponse();
    (response.comprehensive_analysis as unknown as Record<string, unknown>).profitability = null;
    expect(hasComprehensiveAnalysis(response)).toBe(false);
  });
});
