// Model Performance — factor-validation evidence page (added alongside, not replacing, the screener).
// Dependency-neutral inline React SVG charts (no Plotly, no recharts, no network fonts). Every chart
// is labelled "Illustrative Data" and reads from synthData.ts, which is shaped to be swapped for
// frozen Phase 4 artifacts (validation_results.json / phase4_results.pkl) in minutes.

import type { ReactNode } from "react";
import { useEffect, useRef } from "react";
import {
  icTimeline,
  IC_THRESHOLD,
  compositeReturns,
  placeboHistogram,
  placeboPValue,
  PLACEBO_REALIZED_SPREAD,
  REAL_DEFLATED_SHARPE,
  universeFunnel,
  signalDecisions,
  factorHeatmap,
  isIllustrative
} from "./synthData";

const ACCENT = "#c8ff00";

function useReveal<T extends HTMLElement>() {
  const ref = useRef<T | null>(null);
  useEffect(() => {
    const node = ref.current;
    if (!node) return;
    const observer = new IntersectionObserver(
      ([entry]) => entry.isIntersecting && node.classList.add("is-visible"),
      { threshold: 0.12 }
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, []);
  return ref;
}

function ChartCard({ title, explain, howTo, annotation, illustrative, children }: { title: string; explain: string; howTo: string; annotation: string[]; illustrative: boolean; children: ReactNode }) {
  return (
    <article className="chartCard">
      <div className="chartHeader">
        <h3>
          {title}
          <span className="infoIcon" tabIndex={0} role="note" aria-label={`How to read ${title}: ${howTo}`} data-tip={howTo}>i</span>
        </h3>
        {illustrative && (
          <span className="badge" title="Synthetic placeholder — swaps to frozen Phase 4 results when available">Illustrative Data</span>
        )}
      </div>
      <p className="chartExplain">{explain}</p>
      {children}
      <div className="annotation">
        <p className="takeawayLabel">What this tells you</p>
        {annotation.map((line) => (
          <p key={line}>{line}</p>
        ))}
      </div>
    </article>
  );
}

interface LineSpec {
  key: string;
  label: string;
  color: string;
  width?: number;
  dashed?: boolean;
}

function LineChart({
  data,
  xKey,
  lines,
  minY,
  maxY,
  yUnit,
  yDecimals = 2,
  threshold,
  ariaLabel
}: {
  data: Record<string, number | string>[];
  xKey: string;
  lines: LineSpec[];
  minY: number;
  maxY: number;
  yUnit: string;
  yDecimals?: number;
  threshold?: { y: number; label: string };
  ariaLabel: string;
}) {
  const W = 760;
  const H = 340;
  const pad = { left: 60, right: 22, top: 40, bottom: 46 };
  const plotW = W - pad.left - pad.right;
  const plotH = H - pad.top - pad.bottom;
  const x = (i: number) => pad.left + (i / Math.max(1, data.length - 1)) * plotW;
  const y = (v: number) => pad.top + (1 - (v - minY) / (maxY - minY)) * plotH;
  const ticks = [minY, minY + (maxY - minY) / 2, maxY];
  const firstX = String(data[0][xKey]);
  const lastX = String(data[data.length - 1][xKey]);

  return (
    <svg className="chartSvg" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={ariaLabel} preserveAspectRatio="xMidYMid meet">
      <title>{ariaLabel}</title>
      <rect x={0} y={0} width={W} height={H} rx={8} />
      <text x={16} y={24} className="axisUnit">{yUnit}</text>
      {ticks.map((t) => (
        <g key={t}>
          <line x1={pad.left} x2={W - pad.right} y1={y(t)} y2={y(t)} className="gridLine" />
          <text x={pad.left - 10} y={y(t) + 4} className="axisText" textAnchor="end">{t.toFixed(yDecimals)}</text>
        </g>
      ))}
      {threshold && (
        <g>
          <line x1={pad.left} x2={W - pad.right} y1={y(threshold.y)} y2={y(threshold.y)} className="thresholdLine" />
          <text x={W - pad.right} y={y(threshold.y) - 8} className="thresholdText" textAnchor="end">{threshold.label}</text>
        </g>
      )}
      {lines.map((line) => {
        const d = data
          .map((p, i) => `${i === 0 ? "M" : "L"} ${x(i).toFixed(1)} ${y(Number(p[line.key])).toFixed(1)}`)
          .join(" ");
        return (
          <path
            key={line.key}
            d={d}
            fill="none"
            stroke={line.color}
            strokeWidth={line.width || 2}
            strokeDasharray={line.dashed ? "7 7" : undefined}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        );
      })}
      <text x={pad.left} y={H - 14} className="axisText">{firstX}</text>
      <text x={W - pad.right} y={H - 14} className="axisText" textAnchor="end">{lastX}</text>
      <g className="legend">
        {lines.map((line, i) => (
          <g key={line.key} transform={`translate(${pad.left + i * 132}, 14)`}>
            <line x1={0} x2={22} y1={0} y2={0} stroke={line.color} strokeWidth={line.width || 2} strokeDasharray={line.dashed ? "6 6" : undefined} />
            <text x={28} y={4}>{line.label}</text>
          </g>
        ))}
      </g>
    </svg>
  );
}

function Histogram({
  bins,
  realized,
  realizedLabel,
  pValue,
  xLabel,
  yLabel,
  ariaLabel
}: {
  bins: { x: number; y: number }[];
  realized: number;
  realizedLabel: string;
  pValue: number;
  xLabel: string;
  yLabel: string;
  ariaLabel: string;
}) {
  const W = 760;
  const H = 340;
  const pad = { left: 52, right: 26, top: 36, bottom: 48 };
  const plotW = W - pad.left - pad.right;
  const plotH = H - pad.top - pad.bottom;
  const maxY = Math.max(...bins.map((b) => b.y), 1);
  const xMin = Math.min(...bins.map((b) => b.x), realized);
  const xMax = Math.max(...bins.map((b) => b.x), realized);
  const x = (v: number) => pad.left + ((v - xMin) / (xMax - xMin || 1)) * plotW;
  const y = (v: number) => pad.top + (1 - v / maxY) * plotH;
  const barW = Math.max(2, plotW / bins.length - 2);
  const realizedX = x(realized);

  return (
    <svg className="chartSvg" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={ariaLabel} preserveAspectRatio="xMidYMid meet">
      <title>{ariaLabel}</title>
      <rect x={0} y={0} width={W} height={H} rx={8} />
      <text x={16} y={22} className="axisUnit">{yLabel}</text>
      <line x1={pad.left} x2={W - pad.right} y1={H - pad.bottom} y2={H - pad.bottom} className="gridLine" />
      {bins.map((b) => (
        <rect key={b.x} x={x(b.x) - barW / 2} y={y(b.y)} width={barW} height={H - pad.bottom - y(b.y)} className="histBar" />
      ))}
      <line x1={realizedX} x2={realizedX} y1={pad.top} y2={H - pad.bottom} className="realizedLine" />
      <text x={Math.min(realizedX + 8, W - pad.right)} y={pad.top + 14} className="thresholdText" textAnchor={realizedX > W - 200 ? "end" : "start"}>
        {realizedLabel} = {realized.toFixed(2)}
      </text>
      <text x={pad.left} y={H - 14} className="axisText">{xLabel}</text>
      <text x={W - pad.right} y={H - 14} className="axisText" textAnchor="end">p = {pValue.toFixed(3)}</text>
    </svg>
  );
}

function DecisionWaterfall() {
  return (
    <div className="decisionList">
      {signalDecisions.map((d) => (
        <div className={d.kept ? "decision kept" : "decision dropped"} key={d.family}>
          <span className="decisionIcon" aria-hidden="true">{d.kept ? "✓" : "✕"}</span>
          <div>
            <strong>
              {d.family}-family ({d.label}): {d.kept ? "KEPT" : "DROPPED"}
            </strong>
            <p>{d.reason}</p>
          </div>
        </div>
      ))}
    </div>
  );
}

function UniverseFunnel() {
  const max = Math.max(...universeFunnel.byCountry.map((b) => b.n), 1);
  return (
    <div className="funnel">
      {universeFunnel.levels.map((lvl) => (
        <div
          className={`funnelStep${lvl.accent ? " accent" : ""}`}
          key={lvl.label}
          style={{ width: `${lvl.pct}%` }}
        >
          <strong>{lvl.n}</strong>
          <span>{lvl.label}</span>
        </div>
      ))}
      <div className="countryBars" aria-label="Final discovery universe by country">
        {universeFunnel.byCountry.map((b) => (
          <div key={b.c}>
            <span>{b.c}</span>
            <i><b style={{ width: `${(b.n / max) * 100}%` }} /></i>
            <em>{b.n}</em>
          </div>
        ))}
      </div>
    </div>
  );
}

function Heatmap() {
  const vals = factorHeatmap.rows.flatMap((r) => r.cells.map((c) => c.ic)).filter((v): v is number => v != null);
  const maxAbs = Math.max(...vals.map((v) => Math.abs(v)), 0.01);
  const color = (ic: number | null) => {
    if (ic == null) return "#161616";
    const t = Math.min(1, Math.abs(ic) / maxAbs);
    return ic >= 0 ? `rgba(200,255,0,${(0.12 + t * 0.72).toFixed(2)})` : `rgba(130,130,130,${(0.12 + t * 0.5).toFixed(2)})`;
  };
  return (
    <div className="heatmap" role="img" aria-label="Predictive power (information coefficient) of each signal across 1-, 3-, 6- and 12-month horizons">
      <div className="heatRow heatHead">
        <span className="heatLabel" />
        {factorHeatmap.horizons.map((h) => (
          <span key={h} className="heatColHead">{h}m</span>
        ))}
      </div>
      {factorHeatmap.rows.map((r) => (
        <div className="heatRow" key={r.variable}>
          <span className="heatLabel">{r.label}</span>
          {r.cells.map((c) => (
            <span
              key={c.h}
              className={`heatCell${c.fdr ? " fdr" : ""}`}
              style={{ background: color(c.ic) }}
              title={`${r.label} @ ${c.h}m: predictive power ${c.ic == null ? "n/a" : c.ic.toFixed(3)}${c.fdr ? " (passed reliability check)" : ""}`}
            >
              {c.ic == null ? "" : c.ic.toFixed(2)}
            </span>
          ))}
        </div>
      ))}
    </div>
  );
}

// Real per-date family IC (noisy, can be negative); drop warmup rows missing any family.
const IC_LINE_DATA: Record<string, number | string>[] = icTimeline
  .filter((p) => p.A != null && p.C != null && p.F != null)
  .map((p) => ({ date: p.month, A: p.A as number, C: p.C as number, F: p.F as number }));
const _icVals = IC_LINE_DATA.flatMap((r) => [Number(r.A), Number(r.C), Number(r.F)]);
const IC_MIN = Math.floor(Math.min(..._icVals, 0) * 100) / 100;
const IC_MAX = Math.ceil(Math.max(..._icVals, IC_THRESHOLD) * 100) / 100;

// Real frozen backtest: winning-composite quintile NAV (net), start = 1.0.
const RETURNS_DATA: Record<string, number | string>[] = compositeReturns.map((p) => ({
  date: p.month,
  q5: p.q5,
  q1: p.q1,
  benchmark: p.benchmark
}));
const _rVals = RETURNS_DATA.flatMap((r) => [Number(r.q5), Number(r.q1), Number(r.benchmark)]);
const RET_MIN = Math.floor(Math.min(..._rVals) * 10) / 10;
const RET_MAX = Math.ceil(Math.max(..._rVals) * 10) / 10;

const PLACEBO_BINS = placeboHistogram.map((b) => ({ x: b.sharpe, y: b.count }));

export default function ModelPerformance({ dataMode }: { dataMode: string }) {
  const ref = useReveal<HTMLElement>();
  const illustrative = isIllustrative(dataMode);
  return (
    <section id="model-performance" ref={ref} className="section reveal">
      <p className="eyebrow">Model Performance</p>
      <h2>Does the model actually work? The honest evidence.</h2>
      <p className="measure">
        A plain-English walkthrough of the research behind the rankings: whether each signal predicts
        returns, how a "top companies vs bottom companies" strategy would have performed after trading
        costs, which signals we kept or dropped, and whether the result could just be luck. Hover the
        small "i" on any chart for how to read it.{illustrative ? " (Charts below are illustrative placeholders until the model run is frozen.)" : ""}
      </p>
      <div className="performanceGrid">
        <ChartCard
          illustrative={illustrative}
          title="Signal IC Timeline"
          explain="Does each signal actually predict future returns? This tracks each signal's predictive power, month by month."
          howTo="Each line is a signal family. Above zero means the signal pointed the right way that month. It is meant to be small and jumpy - what matters is the long-run average, tested in the heatmap and placebo below."
          annotation={[
            "Predictive power is small and jumpy month to month - normal for stock-market signals.",
            "Over the full period only the two news-attention signals (A3 attention, A4 tone) passed our statistical reliability check; sentiment-velocity, fundamentals and regulatory did not."
          ]}
        >
          <LineChart
            ariaLabel="Per-period information coefficient over time for signal families A, C and F"
            data={IC_LINE_DATA}
            xKey="date"
            minY={IC_MIN}
            maxY={IC_MAX}
            yUnit="Rank IC (3m fwd)"
            yDecimals={2}
            threshold={{ y: IC_THRESHOLD, label: "FDR reference (q=0.10)" }}
            lines={[
              { key: "A", label: "A Sentiment", color: ACCENT },
              { key: "C", label: "C Capital", color: "#d8d8d8" },
              { key: "F", label: "F Regulatory", color: "#8a8a8a" }
            ]}
          />
        </ChartCard>

        <ChartCard
          illustrative={illustrative}
          title="Composite Returns"
          explain="If you had held the model's top-ranked companies vs the bottom vs the whole market, how would $1 have grown - after trading costs?"
          howTo="Top = the model's best-scored fifth of companies; Bottom = the worst-scored fifth; Benchmark = holding every company equally. Lines show the growth of $1, net of costs."
          annotation={[
            "The top fifth (green) finishes above the market; the bottom fifth below it - the ranking lines companies up the right way.",
            "But the Top-vs-Bottom spread, after costs, is +6.8%/yr with a confidence range of -1.8% to +15.8%. Because that range includes zero, it is not yet statistically reliable."
          ]}
        >
          <LineChart
            ariaLabel="Net cumulative quintile NAV for the winning composite versus the equal-weight benchmark"
            data={RETURNS_DATA}
            xKey="date"
            minY={RET_MIN}
            maxY={RET_MAX}
            yUnit="Net cumulative (start 1.0)"
            yDecimals={1}
            lines={[
              { key: "q5", label: "Q5 (top)", color: ACCENT, width: 3 },
              { key: "benchmark", label: "Benchmark", color: "#ffffff", dashed: true },
              { key: "q1", label: "Q1 (bottom)", color: "#8a8a8a" }
            ]}
          />
        </ChartCard>

        <ChartCard
          illustrative={illustrative}
          title="Signal Decision Waterfall"
          explain="Which signals we kept, which we dropped, and the honest reason for each."
          howTo="A green check means the signal had usable data and was tested. A grey strike-through means it was dropped. We show failures instead of hiding them."
          annotation={[
            "Kept: news sentiment (A), plus fundamentals (C) and regulatory (F) which had data but tested weaker.",
            "Dropped for missing data: ESG scores (Yahoo's feed went dead) and disclosures (the exchange feed was empty)."
          ]}
        >
          <DecisionWaterfall />
        </ChartCard>

        <ChartCard
          illustrative={illustrative}
          title="Placebo Test"
          explain="Could the result just be luck? We reshuffled the rankings 1,000 times to build a 'pure luck' distribution, then checked where the real result lands."
          howTo="Grey bars = results from 1,000 random shuffles (pure chance). The green line = our real result. The further right of the grey pile, the less likely it is luck. 'p' is the share of lucky shuffles that beat us."
          annotation={[
            `Before costs, the real result beats about ${(100 - placeboPValue * 100).toFixed(1)}% of random shuffles (p=${placeboPValue}) - the ranking carries genuine information.`,
            `After costs it is inconclusive (the Top-vs-Bottom range includes zero). Risk-adjusted score (Deflated Sharpe): ${REAL_DEFLATED_SHARPE}. The signal is real before costs; costs erode it.`
          ]}
        >
          <Histogram
            ariaLabel="Histogram of 1000 permutation gross Q5 minus Q1 spreads with the realized spread marked"
            bins={PLACEBO_BINS}
            realized={PLACEBO_REALIZED_SPREAD}
            realizedLabel="Realized gross spread"
            pValue={placeboPValue}
            xLabel="Permutation Q5-Q1 spread, annualized (n=1000)"
            yLabel="Count"
          />
        </ChartCard>

        <ChartCard
          illustrative={illustrative}
          title="Universe Funnel"
          explain="How we narrowed the broad ASEAN market down to the 198 liquid companies the model is actually tested and traded on."
          howTo="Each bar is a filter step; the final green bar is the tested universe. The small bars below split those 198 names by country."
          annotation={[
            "We validate on liquid large-caps only, so the result is not flattered by tiny, untradeable stocks.",
            "500 screened, filtered to names with over US$1M average daily volume and 3+ years of history, leaving 198 across SG / MY / ID / TH / VN (the Philippines had no resolvable tickers)."
          ]}
        >
          <UniverseFunnel />
        </ChartCard>

        <ChartCard
          illustrative={illustrative}
          title="Factor Heatmap"
          explain="Predictive power of each signal at different look-ahead windows, from 1 to 12 months."
          howTo="Rows are signals; columns are how far ahead we predict. Greener = stronger positive predictive power; an outlined cell passed the statistical reliability check (FDR)."
          annotation={[
            "News-attention and tone signals are the strongest, and they strengthen at longer horizons.",
            "Only two cells are outlined (A3 at 3 months, A4 at 12 months) - the only signals that survived multiple-testing correction."
          ]}
        >
          <Heatmap />
        </ChartCard>
      </div>
    </section>
  );
}
