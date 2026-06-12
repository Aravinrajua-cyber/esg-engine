import { BacktestFeed, CompaniesFeed, Company } from "./types";

const companies: Company[] = Array.from({ length: 96 }, (_, index) => {
  const score = Math.max(35, 92 - index * 0.42);
  const country = ["SG", "MY", "TH", "ID", "VN"][index % 5];
  const sector = ["Financials", "Industrials", "Technology", "Consumer", "Utilities", "Materials"][index % 6];
  return {
    ticker: `DEMO${index + 1}.${country}`,
    name: `Synthetic Company ${index + 1}`,
    country,
    exchange: country === "SG" ? "SGX" : country,
    sector,
    mcap_tier: index % 3 === 0 ? "mega" : index % 3 === 1 ? "large" : "mid",
    currency: country === "SG" ? "SGD" : country === "MY" ? "MYR" : country === "TH" ? "THB" : country === "ID" ? "IDR" : "VND",
    rank: index + 1,
    overall_score: Number(score.toFixed(1)),
    grade: score >= 90 ? "A+" : score >= 80 ? "A" : score >= 65 ? "B" : score >= 50 ? "C" : "D",
    confidence_low: Number(Math.max(0, score - 8).toFixed(1)),
    confidence_high: Number(Math.min(100, score + 8).toFixed(1)),
    coverage_pct: 55 + (index % 40),
    classification: ["future_leader", "hidden_winner", "overrated_leader", "value_trap"][index % 4] as Company["classification"],
    esg_level_pctile: (index * 9) % 100,
    esg_momentum_pctile: (index * 13) % 100,
    pillar_scores: {
      sentiment_dynamics: 50 + ((index * 7) % 45),
      transition_readiness: 48 + ((index * 5) % 45),
      governance_credibility: 52 + ((index * 3) % 42),
      disclosure_behavior: 45 + ((index * 11) % 48),
      data_coverage: 55 + (index % 40)
    },
    flags: index % 11 === 0 ? ["LOW_COVERAGE"] : index % 13 === 0 ? ["HIGH_VOL"] : [],
    explanation: `Synthetic demo score ${score.toFixed(0)} based on placeholder pillar patterns for frontend testing.`,
    timeseries:
      index < 12
        ? {
            dates: Array.from({ length: 18 }, (_, i) => `2025-${String((i % 12) + 1).padStart(2, "0")}-01`),
            price_usd: Array.from({ length: 18 }, (_, i) => Number((90 + i * 1.7 + (index % 5)).toFixed(2))),
            sentiment_tone: Array.from({ length: 18 }, (_, i) => Number((-1.2 + i * 0.13).toFixed(2))),
            score: Array.from({ length: 18 }, (_, i) => Number((score - 4 + i * 0.35).toFixed(1)))
          }
        : null
  };
});

export const mockCompaniesFeed: CompaniesFeed = {
  schema_version: 1,
  generated_at: new Date().toISOString(),
  data_mode: "synthetic",
  as_of_date: new Date().toISOString().slice(0, 10),
  universe_size: companies.length,
  model: {
    winning_composite: "synthetic_demo",
    validated_weights: {
      sentiment_dynamics: 0.35,
      transition_readiness: 0.25,
      governance_credibility: 0.25,
      disclosure_behavior: 0.15
    },
    train_end: "2021-12-31",
    headline: {
      net_q5q1_spread_annual_pct: 8.7,
      deflated_sharpe: 0.82,
      test_ic: 0.038,
      sharpe_net: 1.14
    }
  },
  pillars: [
    { key: "sentiment_dynamics", label: "Sentiment dynamics", description: "News tone and attention momentum." },
    { key: "transition_readiness", label: "Transition readiness", description: "Capital allocation and transition indicators." },
    { key: "governance_credibility", label: "Governance credibility", description: "Governance quality and consistency." },
    { key: "disclosure_behavior", label: "Disclosure behavior", description: "Frequency and quality of sustainability disclosure." }
  ],
  flags: [
    { key: "LOW_COVERAGE", label: "Low coverage", tooltip: "Fewer source observations than the model prefers." },
    { key: "HIGH_VOL", label: "High volatility", tooltip: "Recent return volatility is elevated." }
  ],
  companies
};

export const mockBacktest: BacktestFeed = {
  dates: Array.from({ length: 60 }, (_, i) => `${2019 + Math.floor(i / 12)}-${String((i % 12) + 1).padStart(2, "0")}-01`),
  q5: Array.from({ length: 60 }, (_, i) => 100 + i * 1.35),
  q1: Array.from({ length: 60 }, (_, i) => 100 + i * 0.38),
  benchmark: Array.from({ length: 60 }, (_, i) => 100 + i * 0.72),
  naive_esg_q5: Array.from({ length: 60 }, (_, i) => 100 + i * 0.58),
  net: true,
  train_end_index: 35
};
