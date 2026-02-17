import type {
  AnalysisResponse,
  ComprehensiveAnalysis,
  SearchResponse,
} from "@/types/analysis";
import type { PortfolioResponse } from "@/types/portfolio";
import type { AlertsResponse } from "@/types/alerts";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

async function fetchApi<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE}/api${endpoint}`;
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });
  if (!response.ok) {
    let errorData: Record<string, unknown> = {};
    try { errorData = await response.json(); } catch { /* empty */ }
    const msg = (errorData?.error as Record<string, unknown>)?.message || `API Error: ${response.status}`;
    throw new Error(String(msg));
  }
  return response.json() as Promise<T>;
}

/**
 * Fetch analysis for a ticker. Returns the full AnalysisResponse which includes
 * both legacy `forensic_metrics` and the new `comprehensive_analysis` object.
 */
export async function analyzeTicker(ticker: string): Promise<AnalysisResponse> {
  return fetchApi<AnalysisResponse>(`/analyze/${ticker.toUpperCase()}`);
}

/**
 * Force-refresh analysis for a ticker (bypasses cache).
 * Returns the same AnalysisResponse shape as analyzeTicker.
 */
export async function refreshAnalysis(ticker: string): Promise<AnalysisResponse> {
  return fetchApi<AnalysisResponse>(`/analyze/${ticker.toUpperCase()}/refresh`);
}

/**
 * Helper to safely extract comprehensive analysis from an AnalysisResponse.
 * Handles backward compatibility: if comprehensive_analysis is missing (old cached
 * response), returns null so callers can fall back to forensic_metrics.
 */
export function getComprehensiveAnalysis(
  response: AnalysisResponse
): ComprehensiveAnalysis | null {
  return response.comprehensive_analysis ?? null;
}

/**
 * Check whether an AnalysisResponse includes the new comprehensive analysis data.
 * Useful for conditionally rendering new UI panels vs legacy view.
 */
export function hasComprehensiveAnalysis(response: AnalysisResponse): boolean {
  return (
    response.comprehensive_analysis != null &&
    response.comprehensive_analysis.profitability != null
  );
}

export async function searchTickers(query: string): Promise<SearchResponse> {
  return fetchApi<SearchResponse>(`/search?q=${encodeURIComponent(query)}`);
}

export async function getPortfolio(): Promise<PortfolioResponse> {
  return fetchApi<PortfolioResponse>("/portfolio");
}

export async function addHolding(data: { ticker: string; shares: number; costBasis: number; purchaseDate: string }) {
  return fetchApi("/portfolio", { method: "POST", body: JSON.stringify(data) });
}

export async function deleteHolding(id: number) {
  return fetchApi(`/portfolio/${id}`, { method: "DELETE" });
}

export async function getAlerts(): Promise<AlertsResponse> {
  return fetchApi<AlertsResponse>("/alerts");
}

export async function dismissAlert(id: number) {
  return fetchApi(`/alerts/${id}`, { method: "DELETE" });
}
