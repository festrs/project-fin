export interface Money {
  amount: string;
  currency: string;
}

export type AssetClassType = "stock" | "crypto" | "fixed_income";

export interface AssetClass {
  id: string;
  user_id: string;
  name: string;
  target_weight: number;
  country: string;
  type: AssetClassType;
  is_emergency_reserve: boolean;
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
  unit_price: Money | null;
  total_value: Money;
  tax_amount: Money | null;
  date: string;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface Holding {
  symbol: string;
  asset_class_id: string;
  quantity: number | null;
  avg_price: Money | null;
  total_cost: Money;
  current_price?: Money;
  current_value?: Money;
  gain_loss?: Money;
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

export interface InvestmentRecommendation {
  symbol: string;
  class_name: string;
  effective_target: number;
  actual_weight: number;
  diff: number;
  price: Money;
  quantity: number;
  invest_amount: Money;
}

export interface InvestmentPlan {
  recommendations: InvestmentRecommendation[];
  total_invested: Money;
  exchange_rate: number | null;
  exchange_rate_pair: string | null;
  remainder: Money;
  empty_reason: "no_holdings" | "all_quarantined" | "amount_too_small" | null;
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
  value: Money;
  quantity: number;
  total: Money;
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

export interface UserInfo {
  id: string;
  name: string;
  email: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: UserInfo;
}

export interface DividendClassData {
  asset_class_id: string;
  class_name: string;
  annual_income: { amount: string; currency: string };
  currency: string;
}

export interface DividendsResponse {
  dividends: DividendClassData[];
  total_annual_income: { amount: string; currency: string };
}

export interface PortfolioSnapshot {
  date: string;
  total_value_brl: string;
}

export interface MarketIndex {
  symbol: string;
  name: string;
  value: string | null;
  change_pct: number | null;
}

export interface MarketMover {
  symbol: string;
  name: string;
  change_pct: number;
  current_price: string;
}

export interface MarketMoversResponse {
  gainers: MarketMover[];
  losers: MarketMover[];
}

export interface TaxMonthlyEntry {
  month: number;
  stocks: {
    total_sales: string;
    total_gain: string;
    exempt: boolean;
    tax_due: string;
  };
  fiis: {
    total_sales: string;
    total_gain: string;
    tax_due: string;
  };
  total_tax_due: string;
}
