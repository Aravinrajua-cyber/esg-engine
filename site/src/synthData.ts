// Illustrative synthetic data for the Model Performance charts, shaped to match what the model
// produces (IC 0.02-0.08, composite Deflated Sharpe ~1.1). Every chart shows an "Illustrative Data"
// badge; swap these arrays for frozen Phase 4 outputs (validation_results.json / phase4_results.pkl)
// when the run is frozen. The signal-decision waterfall and the universe funnel use REAL documented
// numbers, not synthetic.

function mulberry32(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const MONTHS: string[] = [];
for (let y = 2020; y <= 2024; y++) for (let m = 1; m <= 12; m++) MONTHS.push(`${y}-${String(m).padStart(2, "0")}`);
const N = MONTHS.length; // 60

// ---- Section 1: rolling 12m IC per signal family --------------------------------------------------
// A (sentiment) peaks ~0.07 mid-2022; C (fundamentals) steady 0.04-0.05; F (regulatory) noisier.
const icRng = mulberry32(42);
export const IC_THRESHOLD = 0.03; // Newey-West-corrected significance floor (illustrative)
export interface ICPoint { month: string; A: number; C: number; F: number; }
export const icTimeline: ICPoint[] = MONTHS.map((month, i) => {
  const bump = Math.exp(-(((i - 30) / 14) ** 2)); // peak at i=30 (mid-2022)
  return {
    month,
    A: +(0.04 + 0.03 * bump + (icRng() - 0.5) * 0.006).toFixed(4),
    C: +(0.045 + (icRng() - 0.5) * 0.012).toFixed(4),
    F: +(0.04 + 0.018 * Math.sin(i / 4) + (icRng() - 0.5) * 0.016).toFixed(4)
  };
});

// ---- Section 2: cumulative return index (start 100), MASTER ends ~165, benchmark ~118 -------------
function pathTo(target: number, vol: number, seed: number): number[] {
  const r = mulberry32(seed);
  const drift = Math.log(target / 100) / (N - 1);
  let v = 100;
  const out = [100];
  for (let i = 1; i < N; i++) {
    v *= Math.exp(drift + (r() - 0.5) * vol);
    out.push(+v.toFixed(2));
  }
  return out;
}
const compLines = {
  MASTER: pathTo(165, 0.022, 7),
  TRI: pathTo(150, 0.026, 11),
  EIP: pathTo(139, 0.03, 17),
  CPS: pathTo(127, 0.028, 23),
  Benchmark: pathTo(118, 0.018, 29)
};
export interface CompPoint { month: string; EIP: number; TRI: number; CPS: number; MASTER: number; Benchmark: number; }
export const compositeReturns: CompPoint[] = MONTHS.map((month, i) => ({
  month,
  EIP: compLines.EIP[i],
  TRI: compLines.TRI[i],
  CPS: compLines.CPS[i],
  MASTER: compLines.MASTER[i],
  Benchmark: compLines.Benchmark[i]
}));

// ---- Section 4: 1,000-permutation placebo Sharpe histogram (20 bins) ------------------------------
export const REAL_DEFLATED_SHARPE = 1.12;
const pRng = mulberry32(2026);
const placeboSharpes: number[] = [];
for (let i = 0; i < 1000; i++) {
  const u1 = Math.max(pRng(), 1e-9);
  const u2 = pRng();
  // N(0.30, 0.40) -> ~top 2% lies beyond the real Deflated Sharpe of 1.12
  placeboSharpes.push(0.3 + Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2) * 0.4);
}
const BINS = 20;
const lo = Math.min(...placeboSharpes);
const hi = Math.max(...placeboSharpes);
const w = (hi - lo) / BINS;
const counts = new Array(BINS).fill(0);
placeboSharpes.forEach((s) => counts[Math.min(BINS - 1, Math.floor((s - lo) / w))]++);
export interface PlaceboBin { sharpe: number; count: number; }
export const placeboHistogram: PlaceboBin[] = counts.map((count, i) => ({
  sharpe: +(lo + w * (i + 0.5)).toFixed(3),
  count
}));
export const placeboPValue = +(placeboSharpes.filter((s) => s >= REAL_DEFLATED_SHARPE).length / placeboSharpes.length).toFixed(3);

// ---- Section 5: universe funnel — REAL documented numbers -----------------------------------------
export interface FunnelLevel { label: string; n: number; pct: number; accent?: boolean; }
export interface CountryCount { c: string; n: number; }
export const universeFunnel: { levels: FunnelLevel[]; byCountry: CountryCount[] } = {
  levels: [
    { label: "ASEAN companies screened", n: 500, pct: 100 },
    { label: "Filtered · ADV > US$1M, ≥3yr history", n: 198, pct: 60 },
    { label: "Final discovery universe", n: 198, pct: 40, accent: true }
  ],
  // real discovery breakdown (sums to 198). PH excluded — no resolvable PSE tickers (documented).
  byCountry: [
    { c: "SG", n: 47 },
    { c: "MY", n: 46 },
    { c: "ID", n: 43 },
    { c: "TH", n: 37 },
    { c: "VN", n: 25 }
  ]
};

// ---- Section 3: signal-decision waterfall — REAL build outcomes -----------------------------------
export interface SignalDecision { family: string; label: string; kept: boolean; reason: string; }
export const signalDecisions: SignalDecision[] = [
  { family: "A", label: "Sentiment Dynamics", kept: true, reason: "GDELT 2.0 news sentiment — significant IC after FDR correction." },
  { family: "B", label: "ESG Scores", kept: false, reason: "Yahoo Finance ESG endpoint dead — no data fallback available." },
  { family: "C", label: "Capital Allocation", kept: true, reason: "yfinance fundamentals — clean data, consistent IC." },
  { family: "D", label: "Disclosure Behaviour", kept: false, reason: "SGX/Bursa announcement feed returned empty across the universe." },
  { family: "F", label: "Regulatory Overlay", kept: true, reason: "Country-level hand-constructed overlay — additive alpha." }
];
