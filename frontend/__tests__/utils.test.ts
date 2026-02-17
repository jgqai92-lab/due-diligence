import { describe, it, expect } from "vitest";
import {
  // Existing functions (verify they still work)
  formatScore,
  formatLargeNumber,
  formatPercent,
  classifyMScore,
  classifyZScore,
  timeAgo,
  getZoneColor,
  getZoneBorder,
  // New classification helpers
  classifyLeverage,
  classifyProfitability,
  classifyCashFlow,
  classifyGrowth,
  classifyValuation,
  classifySentiment,
  // New formatting helpers
  formatRatio,
  formatMultiple,
  formatPercentFromDecimal,
  // Composite helpers
  getHealthScore,
  getForensicRisk,
  // Zone-to-color helpers
  getLeverageZoneColor,
  getProfitabilityZoneColor,
  getCashFlowZoneColor,
  getGrowthZoneColor,
  getValuationZoneColor,
  getSentimentZoneColor,
  getHealthScoreColor,
  getForensicRiskColor,
  getHealthScoreBorder,
  getForensicRiskBorder,
} from "@/lib/utils";

// ─── Existing Function Regression Tests ─────────────────────────────

describe("formatScore (existing)", () => {
  it("returns N/A for null", () => {
    expect(formatScore(null)).toBe("N/A");
  });
  it("formats number to 2 decimal places", () => {
    expect(formatScore(-2.45)).toBe("-2.45");
    expect(formatScore(3.0)).toBe("3.00");
  });
});

describe("formatLargeNumber (existing)", () => {
  it("returns N/A for null", () => {
    expect(formatLargeNumber(null)).toBe("N/A");
  });
  it("formats trillions", () => {
    expect(formatLargeNumber(3.2e12)).toBe("$3.20T");
  });
  it("formats billions", () => {
    expect(formatLargeNumber(1.5e9)).toBe("$1.50B");
  });
  it("formats millions", () => {
    expect(formatLargeNumber(250e6)).toBe("$250.00M");
  });
  it("formats small numbers", () => {
    expect(formatLargeNumber(1234.56)).toBe("$1234.56");
  });
});

describe("classifyMScore (existing)", () => {
  it("returns null for null input", () => {
    expect(classifyMScore(null)).toBeNull();
  });
  it("classifies safe scores (< -2.22)", () => {
    expect(classifyMScore(-3.0)).toBe("safe");
  });
  it("classifies warning scores (-2.22 to -1.78)", () => {
    expect(classifyMScore(-2.0)).toBe("warning");
  });
  it("classifies danger scores (> -1.78)", () => {
    expect(classifyMScore(-1.0)).toBe("danger");
  });
});

describe("classifyZScore (existing)", () => {
  it("returns null for null input", () => {
    expect(classifyZScore(null)).toBeNull();
  });
  it("classifies safe scores (> 2.99)", () => {
    expect(classifyZScore(5.0)).toBe("safe");
  });
  it("classifies warning scores (1.81-2.99)", () => {
    expect(classifyZScore(2.5)).toBe("warning");
  });
  it("classifies danger scores (< 1.81)", () => {
    expect(classifyZScore(1.0)).toBe("danger");
  });
});

// ─── New Classification Helpers ─────────────────────────────────────

describe("classifyLeverage", () => {
  it("returns 'safe' for null (graceful default)", () => {
    expect(classifyLeverage(null)).toBe("safe");
  });
  it("classifies safe leverage (D/E < 1.0)", () => {
    expect(classifyLeverage(0.5)).toBe("safe");
    expect(classifyLeverage(0.0)).toBe("safe");
    expect(classifyLeverage(0.99)).toBe("safe");
  });
  it("classifies warning leverage (1.0 <= D/E < 2.0)", () => {
    expect(classifyLeverage(1.0)).toBe("warning");
    expect(classifyLeverage(1.5)).toBe("warning");
    expect(classifyLeverage(1.99)).toBe("warning");
  });
  it("classifies danger leverage (D/E >= 2.0)", () => {
    expect(classifyLeverage(2.0)).toBe("danger");
    expect(classifyLeverage(5.0)).toBe("danger");
    expect(classifyLeverage(100)).toBe("danger");
  });
});

describe("classifyProfitability", () => {
  it("returns 'moderate' for null (graceful default)", () => {
    expect(classifyProfitability(null)).toBe("moderate");
  });
  it("classifies strong profitability (> 15%)", () => {
    expect(classifyProfitability(0.20)).toBe("strong");
    expect(classifyProfitability(0.50)).toBe("strong");
  });
  it("classifies moderate profitability (5% < margin <= 15%)", () => {
    expect(classifyProfitability(0.10)).toBe("moderate");
    expect(classifyProfitability(0.15)).toBe("moderate"); // exactly 0.15 is NOT > 0.15
    expect(classifyProfitability(0.06)).toBe("moderate");
  });
  it("classifies weak profitability (<= 5%)", () => {
    expect(classifyProfitability(0.05)).toBe("weak");
    expect(classifyProfitability(0.01)).toBe("weak");
    expect(classifyProfitability(0.0)).toBe("weak");
    expect(classifyProfitability(-0.10)).toBe("weak");
  });
});

describe("classifyCashFlow", () => {
  it("returns 'moderate' for null (graceful default)", () => {
    expect(classifyCashFlow(null)).toBe("moderate");
  });
  it("classifies strong cash flow (> 1.0)", () => {
    expect(classifyCashFlow(1.5)).toBe("strong");
    expect(classifyCashFlow(2.0)).toBe("strong");
  });
  it("classifies moderate cash flow (0.5 < ratio <= 1.0)", () => {
    expect(classifyCashFlow(1.0)).toBe("moderate"); // exactly 1.0 is NOT > 1.0
    expect(classifyCashFlow(0.8)).toBe("moderate");
    expect(classifyCashFlow(0.51)).toBe("moderate");
  });
  it("classifies weak cash flow (<= 0.5)", () => {
    expect(classifyCashFlow(0.5)).toBe("weak");
    expect(classifyCashFlow(0.3)).toBe("weak");
    expect(classifyCashFlow(0.0)).toBe("weak");
    expect(classifyCashFlow(-1.0)).toBe("weak");
  });
});

describe("classifyGrowth", () => {
  it("returns 'low' for null (graceful default)", () => {
    expect(classifyGrowth(null)).toBe("low");
  });
  it("classifies high growth (> 20%)", () => {
    expect(classifyGrowth(0.25)).toBe("high");
    expect(classifyGrowth(1.0)).toBe("high");
  });
  it("classifies moderate growth (5% < growth <= 20%)", () => {
    expect(classifyGrowth(0.20)).toBe("moderate"); // exactly 0.20 is NOT > 0.20
    expect(classifyGrowth(0.10)).toBe("moderate");
    expect(classifyGrowth(0.06)).toBe("moderate");
  });
  it("classifies low growth (0% <= growth <= 5%)", () => {
    expect(classifyGrowth(0.05)).toBe("low");
    expect(classifyGrowth(0.02)).toBe("low");
    expect(classifyGrowth(0.0)).toBe("low");
  });
  it("classifies negative growth (< 0%)", () => {
    expect(classifyGrowth(-0.01)).toBe("negative");
    expect(classifyGrowth(-0.30)).toBe("negative");
  });
});

describe("classifyValuation", () => {
  it("returns 'fair' for null (graceful default)", () => {
    expect(classifyValuation(null)).toBe("fair");
  });
  it("classifies cheap valuation (P/E < 15)", () => {
    expect(classifyValuation(10)).toBe("cheap");
    expect(classifyValuation(14.99)).toBe("cheap");
  });
  it("classifies fair valuation (15 <= P/E < 30)", () => {
    expect(classifyValuation(15)).toBe("fair");
    expect(classifyValuation(25)).toBe("fair");
    expect(classifyValuation(29.99)).toBe("fair");
  });
  it("classifies expensive valuation (P/E >= 30)", () => {
    expect(classifyValuation(30)).toBe("expensive");
    expect(classifyValuation(50)).toBe("expensive");
    expect(classifyValuation(100)).toBe("expensive");
  });
});

describe("classifySentiment", () => {
  it("returns 'neutral' for null (graceful default)", () => {
    expect(classifySentiment(null)).toBe("neutral");
  });
  it("classifies bullish sentiment (rating < 2.0)", () => {
    expect(classifySentiment(1.0)).toBe("bullish");
    expect(classifySentiment(1.5)).toBe("bullish");
    expect(classifySentiment(1.99)).toBe("bullish");
  });
  it("classifies neutral sentiment (2.0 <= rating < 3.5)", () => {
    expect(classifySentiment(2.0)).toBe("neutral");
    expect(classifySentiment(3.0)).toBe("neutral");
    expect(classifySentiment(3.49)).toBe("neutral");
  });
  it("classifies bearish sentiment (rating >= 3.5)", () => {
    expect(classifySentiment(3.5)).toBe("bearish");
    expect(classifySentiment(4.0)).toBe("bearish");
    expect(classifySentiment(5.0)).toBe("bearish");
  });
});

// ─── New Formatting Helpers ─────────────────────────────────────────

describe("formatRatio", () => {
  it("returns 'N/A' for null", () => {
    expect(formatRatio(null)).toBe("N/A");
  });
  it("formats ratio with x suffix and 1 decimal", () => {
    expect(formatRatio(2.4)).toBe("2.4x");
    expect(formatRatio(0.5)).toBe("0.5x");
    expect(formatRatio(10.0)).toBe("10.0x");
  });
  it("handles negative ratios", () => {
    expect(formatRatio(-1.5)).toBe("-1.5x");
  });
});

describe("formatMultiple", () => {
  it("returns 'N/A' for null", () => {
    expect(formatMultiple(null)).toBe("N/A");
  });
  it("formats multiple with x suffix and 1 decimal", () => {
    expect(formatMultiple(12.5)).toBe("12.5x");
    expect(formatMultiple(25.0)).toBe("25.0x");
  });
});

describe("formatPercentFromDecimal", () => {
  it("returns 'N/A' for null", () => {
    expect(formatPercentFromDecimal(null)).toBe("N/A");
  });
  it("formats positive decimal as percentage with + sign", () => {
    expect(formatPercentFromDecimal(0.152)).toBe("+15.2%");
    expect(formatPercentFromDecimal(0.05)).toBe("+5.0%");
  });
  it("formats negative decimal as percentage with - sign", () => {
    expect(formatPercentFromDecimal(-0.08)).toBe("-8.0%");
  });
  it("formats zero as +0.0%", () => {
    expect(formatPercentFromDecimal(0)).toBe("+0.0%");
  });
});

// ─── Composite Score Helpers ────────────────────────────────────────

describe("getHealthScore", () => {
  it("returns STRONG when all metrics are excellent", () => {
    // strong profitability (> 0.15) = 2, safe leverage (< 1.0) = 2, strong CF (> 1.0) = 2 -> 6 >= 5
    expect(getHealthScore(0.25, 0.5, 1.5)).toBe("STRONG");
  });

  it("returns MODERATE for mixed metrics", () => {
    // moderate profitability (0.10) = 1, warning leverage (1.5) = 1, strong CF (1.5) = 2 -> 4 >= 3
    expect(getHealthScore(0.10, 1.5, 1.5)).toBe("MODERATE");
  });

  it("returns WEAK when most metrics are poor", () => {
    // weak profitability (0.02) = 0, danger leverage (3.0) = 0, weak CF (0.3) = 0 -> 0 < 3
    expect(getHealthScore(0.02, 3.0, 0.3)).toBe("WEAK");
  });

  it("handles all null values gracefully", () => {
    // null profitability -> moderate = 1, null leverage -> safe = 2, null CF -> moderate = 1 -> 4 >= 3
    expect(getHealthScore(null, null, null)).toBe("MODERATE");
  });

  it("returns STRONG at exact boundary (total = 5)", () => {
    // strong profitability (0.20) = 2, safe leverage (0.5) = 2, moderate CF (0.8) = 1 -> 5 >= 5
    expect(getHealthScore(0.20, 0.5, 0.8)).toBe("STRONG");
  });

  it("returns MODERATE at exact boundary (total = 3)", () => {
    // moderate profitability (0.10) = 1, warning leverage (1.5) = 1, moderate CF (0.8) = 1 -> 3 >= 3
    expect(getHealthScore(0.10, 1.5, 0.8)).toBe("MODERATE");
  });

  it("returns WEAK below boundary (total = 2)", () => {
    // weak profitability (0.03) = 0, warning leverage (1.5) = 1, moderate CF (0.8) = 1 -> 2 < 3
    expect(getHealthScore(0.03, 1.5, 0.8)).toBe("WEAK");
  });
});

describe("getForensicRisk", () => {
  it("returns LOW when both scores are safe", () => {
    // M-Score safe (< -2.22) = 0, Z-Score safe (> 2.99) = 0 -> 0
    expect(getForensicRisk(-3.0, 5.0)).toBe("LOW");
  });

  it("returns MEDIUM for one warning signal", () => {
    // M-Score safe = 0, Z-Score warning = 1 -> 1 <= 2
    expect(getForensicRisk(-3.0, 2.5)).toBe("MEDIUM");
  });

  it("returns MEDIUM for two warning signals", () => {
    // M-Score warning = 1, Z-Score warning = 1 -> 2 <= 2
    expect(getForensicRisk(-2.0, 2.0)).toBe("MEDIUM");
  });

  it("returns HIGH for danger + warning", () => {
    // M-Score danger = 2, Z-Score warning = 1 -> 3 > 2
    expect(getForensicRisk(-1.0, 2.5)).toBe("HIGH");
  });

  it("returns HIGH for two danger signals", () => {
    // M-Score danger = 2, Z-Score danger = 2 -> 4 > 2
    expect(getForensicRisk(0.0, 1.0)).toBe("HIGH");
  });

  it("handles null values gracefully (defaults to LOW)", () => {
    // null M-Score -> safe = 0, null Z-Score -> safe = 0 -> 0
    expect(getForensicRisk(null, null)).toBe("LOW");
  });

  it("handles one null value", () => {
    // null M-Score -> safe = 0, Z-Score danger = 2 -> 2 <= 2
    expect(getForensicRisk(null, 1.0)).toBe("MEDIUM");
  });
});

// ─── Zone-to-Color Mapping Tests ────────────────────────────────────

describe("getLeverageZoneColor", () => {
  it("maps safe to text-bull", () => {
    expect(getLeverageZoneColor("safe")).toBe("text-bull");
  });
  it("maps warning to text-warning", () => {
    expect(getLeverageZoneColor("warning")).toBe("text-warning");
  });
  it("maps danger to text-bear", () => {
    expect(getLeverageZoneColor("danger")).toBe("text-bear");
  });
});

describe("getProfitabilityZoneColor", () => {
  it("maps strong to text-bull", () => {
    expect(getProfitabilityZoneColor("strong")).toBe("text-bull");
  });
  it("maps moderate to text-warning", () => {
    expect(getProfitabilityZoneColor("moderate")).toBe("text-warning");
  });
  it("maps weak to text-bear", () => {
    expect(getProfitabilityZoneColor("weak")).toBe("text-bear");
  });
});

describe("getCashFlowZoneColor", () => {
  it("maps strong to text-bull", () => {
    expect(getCashFlowZoneColor("strong")).toBe("text-bull");
  });
  it("maps moderate to text-warning", () => {
    expect(getCashFlowZoneColor("moderate")).toBe("text-warning");
  });
  it("maps weak to text-bear", () => {
    expect(getCashFlowZoneColor("weak")).toBe("text-bear");
  });
});

describe("getGrowthZoneColor", () => {
  it("maps high to text-bull", () => {
    expect(getGrowthZoneColor("high")).toBe("text-bull");
  });
  it("maps moderate to text-warning", () => {
    expect(getGrowthZoneColor("moderate")).toBe("text-warning");
  });
  it("maps low to text-text-secondary", () => {
    expect(getGrowthZoneColor("low")).toBe("text-text-secondary");
  });
  it("maps negative to text-bear", () => {
    expect(getGrowthZoneColor("negative")).toBe("text-bear");
  });
});

describe("getValuationZoneColor", () => {
  it("maps cheap to text-bull", () => {
    expect(getValuationZoneColor("cheap")).toBe("text-bull");
  });
  it("maps fair to text-warning", () => {
    expect(getValuationZoneColor("fair")).toBe("text-warning");
  });
  it("maps expensive to text-bear", () => {
    expect(getValuationZoneColor("expensive")).toBe("text-bear");
  });
});

describe("getSentimentZoneColor", () => {
  it("maps bullish to text-bull", () => {
    expect(getSentimentZoneColor("bullish")).toBe("text-bull");
  });
  it("maps neutral to text-warning", () => {
    expect(getSentimentZoneColor("neutral")).toBe("text-warning");
  });
  it("maps bearish to text-bear", () => {
    expect(getSentimentZoneColor("bearish")).toBe("text-bear");
  });
});

describe("getHealthScoreColor", () => {
  it("maps STRONG to text-bull", () => {
    expect(getHealthScoreColor("STRONG")).toBe("text-bull");
  });
  it("maps MODERATE to text-warning", () => {
    expect(getHealthScoreColor("MODERATE")).toBe("text-warning");
  });
  it("maps WEAK to text-bear", () => {
    expect(getHealthScoreColor("WEAK")).toBe("text-bear");
  });
});

describe("getForensicRiskColor", () => {
  it("maps LOW to text-bull", () => {
    expect(getForensicRiskColor("LOW")).toBe("text-bull");
  });
  it("maps MEDIUM to text-warning", () => {
    expect(getForensicRiskColor("MEDIUM")).toBe("text-warning");
  });
  it("maps HIGH to text-bear", () => {
    expect(getForensicRiskColor("HIGH")).toBe("text-bear");
  });
});

describe("getHealthScoreBorder", () => {
  it("maps STRONG to border-l-bull", () => {
    expect(getHealthScoreBorder("STRONG")).toBe("border-l-bull");
  });
  it("maps MODERATE to border-l-warning", () => {
    expect(getHealthScoreBorder("MODERATE")).toBe("border-l-warning");
  });
  it("maps WEAK to border-l-bear", () => {
    expect(getHealthScoreBorder("WEAK")).toBe("border-l-bear");
  });
});

describe("getForensicRiskBorder", () => {
  it("maps LOW to border-l-bull", () => {
    expect(getForensicRiskBorder("LOW")).toBe("border-l-bull");
  });
  it("maps MEDIUM to border-l-warning", () => {
    expect(getForensicRiskBorder("MEDIUM")).toBe("border-l-warning");
  });
  it("maps HIGH to border-l-bear", () => {
    expect(getForensicRiskBorder("HIGH")).toBe("border-l-bear");
  });
});
