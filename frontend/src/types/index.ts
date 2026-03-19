export type AssetClassType = "stock" | "crypto" | "fixed_income";

export interface AssetClass {
  id: string;
  user_id: string;
  name: string;
  target_weight: number;
  country: string;
  type: AssetClassType;
  created_at: string;
  updated_at: string;
}

export interface AssetWeight {
  id: string;
  asset_class_id: string;
  symbol: string;
  target_weight: number;
  created_at: string;
  updated_at: string;
}

export interface Transaction {
  id: string;
  user_id: string;
  asset_class_id: string;
  asset_symbol: string;
  type: "buy" | "sell" | "dividend";
  quantity: number | null;
  unit_price: number | null;
  total_value: number;
  currency: string;
  tax_amount: number | null;
  date: string;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface Holding {
  symbol: string;
  asset_class_id: string;
  quantity: number | null;
  avg_price: number | null;
  total_cost: number;
  current_price?: number;
  current_value?: number;
  gain_loss?: number;
  target_weight?: number;
  actual_weight?: number;
  currency?: string;
}

export interface Recommendation {
  symbol: string;
  class_name: string;
  effective_target: number;
  actual_weight: number;
  diff: number;
}

export interface QuarantineStatus {
  asset_symbol: string;
  buy_count_in_period: number;
  is_quarantined: boolean;
  quarantine_ends_at: string | null;
}

export interface QuarantineConfig {
  id: string;
  user_id: string;
  threshold: number;
  period_days: number;
}

export interface FundamentalsScore {
  symbol: string;
  ipo_years: number | null;
  ipo_rating: "green" | "yellow" | "red";
  eps_growth_pct: number | null;
  eps_rating: "green" | "yellow" | "red";
  current_net_debt_ebitda: number | null;
  high_debt_years_pct: number | null;
  debt_rating: "green" | "yellow" | "red";
  profitable_years_pct: number | null;
  profit_rating: "green" | "yellow" | "red";
  composite_score: number;
  updated_at: string | null;
}

export const SPLIT_EVENT_TYPE = {
  SPLIT: "split",
  BONIFICACAO: "bonificacao",
} as const;

export type SplitEventType = (typeof SPLIT_EVENT_TYPE)[keyof typeof SPLIT_EVENT_TYPE];

export interface StockSplit {
  id: string;
  symbol: string;
  split_date: string;
  from_factor: number;
  to_factor: number;
  event_type: SplitEventType;
  detected_at: string;
  current_quantity: number;
  new_quantity: number;
}

export interface DividendHistoryItem {
  symbol: string;
  dividend_type: string;
  value: number;
  quantity: number;
  total: number;
  ex_date: string;
  payment_date: string | null;
}

export interface FundamentalsDetail extends FundamentalsScore {
  raw_data: Array<{
    year: number;
    eps: number;
    net_income: number;
    net_debt_ebitda: number;
  }> | null;
}
