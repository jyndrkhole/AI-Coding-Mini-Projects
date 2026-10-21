export type Account = {
  aws_account_id: string;
  account_alias: string | null;
  region: string;
  authenticated_role: string | null;
  last_scan_at: string | null;
  mock_aws: boolean;
  mode: string;
};

export type LinkedAccountCost = {
  account_id: string;
  account_name: string | null;
  is_this_login: boolean;
  current: number;
  previous: number;
  change: number;
  change_percent: number | null;
};

export type CostSummary = {
  currency: string;
  current_period_label: string;
  previous_period_label: string;
  current_monthly_cost: number;
  previous_monthly_cost: number;
  mom_change_amount: number;
  mom_change_percent: number | null;
  forecasted_monthly_cost: number | null;
  forecast_available: boolean;
  forecast_label: string;
  forecast_lower_bound: number | null;
  forecast_upper_bound: number | null;
  cost_scope_label: string;
  linked_accounts: LinkedAccountCost[];
  mock_aws: boolean;
  history_note: string;
  prior_months_average: number | null;
  months: {
    month: string;
    label: string;
    amount: number;
    partial: boolean;
    compared_to: string | null;
    change: number | null;
    change_percent: number | null;
    components: { service: string; usage_type: string; change: number }[];
    other_component_count: number;
  }[];
};

export type DailyCosts = {
  currency: string;
  period_label: string;
  points: { date: string; amount: number }[];
};

export type ServiceCosts = {
  currency: string;
  current_period_label: string;
  previous_period_label: string;
  services: {
    service: string;
    current: number;
    previous: number;
    change: number;
    change_percent: number | null;
  }[];
};

export type CostExplorer = {
  currency: string;
  source_label: string;
  start: string;
  end: string;
  service: string | null;
  region: string | null;
  linked_account: string | null;
  current_period_label: string;
  previous_period_label: string;
  available_services: string[];
  available_regions: string[];
  available_accounts: string[];
  daily_note: string | null;
  monthly_note: string;
  account_note: string | null;
  pricing_note: string | null;
  daily: { date: string; amount: number }[];
  monthly: { month: string; label: string; amount: number }[];
  services: {
    service: string;
    current: number;
    previous: number;
    change: number;
    change_percent: number | null;
  }[];
  regions: {
    region: string;
    current: number;
    previous: number;
    change: number;
    change_percent: number | null;
  }[];
  usage_types: {
    service: string;
    usage_type: string;
    current: number;
    previous: number;
    change: number;
    change_percent: number | null;
    pricing_available: boolean;
  }[];
  linked_accounts: LinkedAccountCost[];
};

export type ScanResult = {
  status: string;
  steps: { service: string; status: string; error: string | null; detail: string | null; timestamp: string }[];
};

export type RegionCosts = {
  currency: string;
  current_period_label: string;
  previous_period_label: string;
  regions: {
    region: string;
    current: number;
    previous: number;
    change: number;
    change_percent: number | null;
  }[];
};

export type Recommendation = {
  id: number;
  resource_id: string | null;
  title: string;
  description: string;
  service: string;
  category: "safe" | "review" | "architecture";
  current_monthly_cost: number;
  estimated_monthly_savings: number;
  estimated_annual_savings: number;
  confidence: string;
  data_quality: string;
  risk_level: string;
  priority: number;
  action_type: string;
  source: string;
  status: string;
  evidence_summary: string;
  assumptions: string[];
  client_brief?: string;
  client_ask?: string;
  next_steps?: string[];
};

export type Savings = {
  currency: string;
  label: string;
  potential_monthly_savings: number;
  potential_annual_savings: number;
  safe_monthly_savings: number;
  review_monthly_savings: number;
  architecture_monthly_savings: number;
};

export type OptimizationScore = {
  score: number | null;
  maximum: number;
  source: string;
  label: string;
  strengths?: string[];
  opportunities?: string[];
  top_improvements?: string[];
};

export type InventoryResource = {
  id: number;
  resource_id: string;
  resource_type: string;
  service: string;
  region: string;
  name: string | null;
  state: string | null;
  instance_type: string | null;
  environment: string | null;
  tags: Record<string, string>;
  metadata: Record<string, unknown>;
  metrics?: {
    metric_name: string;
    timestamp: string | null;
    average: number | null;
    maximum: number | null;
    sample_count: number | null;
  }[];
};

export type AdvisorAnswer = {
  provider: string;
  narrative_source: string;
  narrative: string;
  facts: string[];
  missing_evidence: string[];
};

export type SimulationResult = {
  label: string;
  currency: string;
  current_monthly_cost: number;
  projected_monthly_cost: number;
  potential_monthly_savings: number;
  potential_annual_savings: number;
  included_resources: string[];
  excluded_resources: string[];
  assumptions: string[];
};

export type MonthlyReport = {
  id: number;
  report_month: string;
  currency: string;
  total_cost: number;
  previous_month_cost: number;
  potential_savings: number;
  html: string;
  narrative: string | null;
};
