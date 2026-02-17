export interface Holding {
  id: number;
  ticker: string;
  shares: number;
  cost_basis: number;
  purchase_date: string;
  current_price: number | null;
  market_value: number | null;
  gain_loss: number | null;
  gain_loss_percent: number | null;
}

export interface PortfolioSummary {
  total_market_value: number;
  total_cost_basis: number;
  total_gain_loss: number;
  holding_count: number;
}

export interface PortfolioResponse {
  holdings: Holding[];
  summary: PortfolioSummary;
}
