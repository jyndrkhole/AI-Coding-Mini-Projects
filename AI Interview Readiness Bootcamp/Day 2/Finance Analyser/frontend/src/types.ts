export type Metric = {
  key: string;
  label: string;
  value: number | null;
  unit: string;
  formula: string;
  period: string | null;
  note: string | null;
  interpretable: boolean;
};

export type Assumption = {
  key: string;
  label: string;
  value: number | number[] | string | null;
  source: string;
  rationale: string;
};

export type HistoryPoint = {
  period: string;
  revenue: number | null;
  net_income: number | null;
  operating_cash_flow: number | null;
  free_cash_flow: number | null;
  operating_margin: number | null;
  net_margin: number | null;
  gross_margin: number | null;
};

export type Report = {
  id: string;
  ticker: string;
  company_name: string;
  created_at: string;
  currency: string | null;
  rating: {
    label: string;
    score: number | null;
    confidence: string;
    components: { name: string; label: string; score: number | null; weight: number }[];
    weight_notes: string[];
    methodology: string;
  };
  disagreement: {
    financial_health: string;
    valuation: string;
    risk: string;
    news: string;
    conflicts: string[];
    consistent: boolean;
  };
  market: {
    ticker: string;
    company_name: string;
    exchange: string | null;
    sector: string | null;
    industry: string | null;
    currency: string | null;
    price: number | null;
    previous_close: number | null;
    price_as_of: string | null;
    market_cap: number | null;
    enterprise_value: number | null;
    enterprise_value_source: string | null;
    shares: number | null;
    shares_source: string | null;
    beta: number | null;
  };
  health: {
    label: string;
    score: number | null;
    basis: string;
    checks_passed: number;
    checks_evaluated: number;
    metrics: Metric[];
    strengths: string[];
    weaknesses: string[];
    evidence: string[];
    history: HistoryPoint[];
  };
  valuation: {
    label: string;
    method_used: string;
    intrinsic_value_per_share: number | null;
    current_price: number | null;
    difference: number | null;
    upside_percent: number | null;
    dcf: {
      status: string;
      model: string;
      methodology: string;
      intrinsic_value_per_share: number | null;
      enterprise_value: number | null;
      equity_value: number | null;
      discount_rate: number | null;
      terminal_growth: number | null;
      terminal_value: number | null;
      terminal_value_share: number | null;
      forecast: { year: number; revenue: number | null; free_cash_flow: number; present_value: number }[];
      sensitivity: { discount_rate: number; terminal_growth: number; value_per_share: number }[];
      margin_sensitivity: { operating_margin: number; value_per_share: number | null }[];
      limitations: string[];
    };
    peers: {
      ticker: string;
      name: string | null;
      price_to_earnings: number | null;
      price_to_sales: number | null;
      price_to_book: number | null;
      ev_to_ebitda: number | null;
      ev_to_revenue: number | null;
      excluded_reason: string | null;
    }[];
    peer_median: Record<string, number | null>;
    peer_implied_value: number | null;
    peer_selection: string;
    excluded_peers: string[];
    target_multiples: Report["valuation"]["peers"][number] | null;
    scenarios: { name: string; intrinsic_value_per_share: number | null; upside_percent: number | null; note: string }[];
    assumptions: Assumption[];
    limitations: string[];
  };
  risk: {
    label: string;
    flags: { category: string; severity: string; title: string; evidence: string; impact: string }[];
    methodology: string;
    limitations: string[];
  };
  news: {
    label: string;
    lookback_days: number;
    articles: {
      title: string;
      publisher: string | null;
      published_at: string | null;
      url: string | null;
      sentiment: string;
      category: string;
    }[];
    method: string;
    limitations: string[];
  };
  data_quality: {
    confidence: string;
    years_annual: number;
    missing_fields: string[];
    limitations: string[];
    coverage_score: number;
  };
  assumptions: Assumption[];
  sections: {
    id: string;
    title: string;
    paragraphs: string[];
    bullets: string[];
    interpretation: string | null;
    interpretation_source: string;
  }[];
  brief_markdown: string;
  trace: { name: string; phase: string; started_offset_ms: number; duration_ms: number }[];
  llm: { provider: string; model: string; used: boolean; message: string };
  disclaimer: string;
};

export type HistoryItem = {
  id: string;
  ticker: string;
  company_name: string;
  created_at: string;
  rating: string;
};

export type Status = {
  llm_provider: string;
  llm_model: string;
  llm_configured: boolean;
  llm_message: string;
};

export type AnalyzeBody = {
  ticker: string;
  news_lookback_days: number;
  peers?: string[];
  assumptions?: {
    revenue_growth?: number;
    operating_margin?: number;
    tax_rate?: number;
    capex_pct_revenue?: number;
    nwc_pct_revenue?: number;
    discount_rate?: number;
    terminal_growth?: number;
    forecast_years?: number;
  };
};
