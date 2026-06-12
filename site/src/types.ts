export type Grade = "A+" | "A" | "B" | "C" | "D";
export type Classification = "hidden_winner" | "future_leader" | "overrated_leader" | "value_trap";
export type PillarKey = "sentiment_dynamics" | "transition_readiness" | "governance_credibility" | "disclosure_behavior";

export interface Company {
  ticker: string;
  name: string;
  country: string;
  exchange: string;
  sector: string;
  mcap_tier: string;
  currency: string;
  rank: number;
  overall_score: number;
  grade: Grade;
  confidence_low: number;
  confidence_high: number;
  coverage_pct: number;
  classification: Classification;
  esg_level_pctile: number;
  esg_momentum_pctile: number;
  pillar_scores: Record<PillarKey | "data_coverage", number>;
  flags: string[];
  explanation: string;
  timeseries: null | { dates: string[]; price_usd: number[]; sentiment_tone: number[]; score: number[] };
}

export interface CompaniesFeed {
  schema_version: 1;
  generated_at: string;
  data_mode: "live" | "synthetic";
  as_of_date: string;
  universe_size: number;
  model: {
    winning_composite: string;
    validated_weights: Record<PillarKey, number>;
    train_end: string;
    headline: {
      net_q5q1_spread_annual_pct: number;
      deflated_sharpe: number;
      test_ic: number;
      sharpe_net: number;
    };
  };
  pillars: { key: string; label: string; description: string }[];
  flags: { key: string; label: string; tooltip: string }[];
  companies: Company[];
}

export interface BacktestFeed {
  dates: string[];
  q5: number[];
  q1: number[];
  benchmark: number[];
  naive_esg_q5: number[];
  net: boolean;
  train_end_index: number;
}

export interface IcRow {
  variable: string;
  label: string;
  ic_3m: number | null;
  t_nw: number | null;
  fdr_survived: boolean;
}

export interface PlaceboFeed {
  realized_spread: number;
  hist_bins: number[];
  hist_counts: number[];
}

export interface GroupSpreadRow {
  key: string;
  spread_net: number;
}
