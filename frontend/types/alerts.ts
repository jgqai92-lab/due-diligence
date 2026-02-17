export interface Alert {
  id: number;
  ticker: string;
  alert_type: string;
  severity: string;
  message: string;
  dismissed: boolean;
  created_at: string;
  previous_value: number | null;
  current_value: number | null;
}

export interface AlertsResponse {
  alerts: Alert[];
  count: number;
  undismissed_count: number;
}
