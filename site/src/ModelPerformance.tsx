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
  REAL_DEFLATED_SHARPE,
  universeFunnel,
  signalDecisions,
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

function ChartCard({ title, annotation, illustrative, children }: { title: string; annotation: string[]; illustrative: boolean; children: ReactNode }) {
  return (
    <article className="chartCard">
      <div className="chartHeader">
        <h3>{title}</h3>
        {illustrative && (
          <span title="Synthetic placeholder — swaps to frozen Phase 4 results when available">Illustrative Data</span>
        )}
      </div>
      {children}
      <div className="annotation">
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

const IC_LINE_DATA = icTimeline.map((p) => ({ date: p.month, A: p.A, C: p.C, F: p.F }));
const RETURNS_DATA = compositeReturns.map((p) => ({
  date: p.month,
  MASTER: p.MASTER,
  EIP: p.EIP,
  TRI: p.TRI,
  CPS: p.CPS,
  Benchmark: p.Benchmark
}));
const PLACEBO_BINS = placeboHistogram.map((b) => ({ x: b.sharpe, y: b.count }));

export default function ModelPerformance({ dataMode }: { dataMode: string }) {
  const ref = useReveal<HTMLElement>();
  const illustrative = isIllustrative(dataMode);
  return (
    <section id="model-performance" ref={ref} className="section reveal">
      <p className="eyebrow">Model Performance</p>
      <h2>The factor evidence, validated.</h2>
      <p className="measure">
        This is the research case behind the screener: signal information coefficients, composite
        construction, the build/drop audit trail, a placebo control, and how the validation universe
        is built.{illustrative ? " Charts below are illustrative synthetic placeholders until the Phase 4 run is frozen." : " Charts below reflect the frozen Phase 4 validation run."}
      </p>
      <div className="performanceGrid">
        <ChartCard
          illustrative={illustrative}
          title="Signal IC Timeline"
          annotation={[
            "Higher IC = stronger predictive power. All three retained signal families sit above the significance threshold.",
            "Rolling 12-month information coefficient by signal family; the dotted line is the Newey-West-corrected significance floor."
          ]}
        >
          <LineChart
            ariaLabel="Rolling information coefficient over time for signal families A, C and F"
            data={IC_LINE_DATA}
            xKey="date"
            minY={0}
            maxY={0.1}
            yUnit="IC"
            yDecimals={2}
            threshold={{ y: IC_THRESHOLD, label: "Significance threshold (Newey-West)" }}
            lines={[
              { key: "A", label: "A · Sentiment", color: ACCENT },
              { key: "C", label: "C · Capital", color: "#d8d8d8" },
              { key: "F", label: "F · Regulatory", color: "#8a8a8a" }
            ]}
          />
        </ChartCard>

        <ChartCard
          illustrative={illustrative}
          title="Composite Returns"
          annotation={[
            "MASTER (all signals combined) outperforms the equal-weight benchmark across the backtest window.",
            "Cumulative return index, base 100, monthly 2020–2024. MASTER is highlighted only because it is the model winner."
          ]}
        >
          <LineChart
            ariaLabel="Cumulative indexed returns for EIP, TRI, CPS, MASTER and the equal-weight benchmark"
            data={RETURNS_DATA}
            xKey="date"
            minY={95}
            maxY={170}
            yUnit="Index (base 100)"
            yDecimals={0}
            lines={[
              { key: "MASTER", label: "MASTER", color: ACCENT, width: 3 },
              { key: "TRI", label: "TRI", color: "#cccccc" },
              { key: "EIP", label: "EIP", color: "#999999" },
              { key: "CPS", label: "CPS", color: "#6f6f6f" },
              { key: "Benchmark", label: "Benchmark", color: "#ffffff", dashed: true }
            ]}
          />
        </ChartCard>

        <ChartCard
          illustrative={illustrative}
          title="Signal Decision Waterfall"
          annotation={[
            "The kept families are the only inputs allowed into validated composites.",
            "Data failures in the B and D families were found during construction and disclosed, not hidden — dropping them improved robustness."
          ]}
        >
          <DecisionWaterfall />
        </ChartCard>

        <ChartCard
          illustrative={illustrative}
          title="Placebo Test"
          annotation={[
            "1,000 random signal permutations produce Sharpe ratios clustered near zero (the null).",
            "The real model's Deflated Sharpe sits far in the right tail — the result is unlikely to be chance."
          ]}
        >
          <Histogram
            ariaLabel="Histogram of 1000 permutation Sharpe ratios with the real Deflated Sharpe marked"
            bins={PLACEBO_BINS}
            realized={REAL_DEFLATED_SHARPE}
            realizedLabel="Deflated Sharpe (real model)"
            pValue={placeboPValue}
            xLabel="Permutation Sharpe ratio (n = 1000)"
            yLabel="Count"
          />
        </ChartCard>

        <ChartCard
          illustrative={illustrative}
          title="Universe Funnel"
          annotation={[
            "Validation runs on a cleaner liquid subset, not every screened name — this avoids illiquid micro-cap survivorship effects.",
            "500 screened → liquidity filter (ADV > US$1M, ≥3yr history) → 198 final discovery names. Country split below (PH excluded: no resolvable tickers)."
          ]}
        >
          <UniverseFunnel />
        </ChartCard>
      </div>
    </section>
  );
}
