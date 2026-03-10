export interface AssetClass {
  id: string;
  user_id: string;
  name: string;
  target_weight: number;
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
  quantity: number;
  unit_price: number;
  total_value: number;
  currency: "BRL" | "USD";
  tax_amount: number;
  date: string;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface Holding {
  symbol: string;
  asset_class_id: string;
  quantity: number;
  avg_price: number;
  total_cost: number;
  current_price?: number;
  current_value?: number;
  gain_loss?: number;
  target_weight?: number;
  actual_weight?: number;
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
