import { ArrowDown, BarChart3, Moon, RotateCcw, Search, Sun } from "lucide-react";
import React, { Suspense, useEffect, useMemo, useRef, useState } from "react";
import { loadBacktest, loadCompanies, loadRecords } from "./data";
import { BacktestFeed, Company, CompaniesFeed, PillarKey } from "./types";

const Plot = React.lazy(() => import("./Plot"));
const PILLARS: PillarKey[] = ["sentiment_dynamics", "transition_readiness", "governance_credibility", "disclosure_behavior"];
type IcRow = { variable: string; label: string; ic_3m: number; t_nw: number; fdr_survived: boolean };
type PlaceboFeed = { realized_spread: number; hist_bins: number[]; hist_counts: number[] };

function useReveal<T extends HTMLElement>() {
  const ref = useRef<T | null>(null);
  useEffect(() => {
    const node = ref.current;
    if (!node) return;
    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) node.classList.add("is-visible");
    }, { threshold: 0.2 });
    observer.observe(node);
    return () => observer.disconnect();
  }, []);
  return ref;
}

function useQueryState(key: string, initial = "") {
  const [value, setValue] = useState(() => new URLSearchParams(location.search).get(key) || initial);
  useEffect(() => {
    const params = new URLSearchParams(location.search);
    if (value) params.set(key, value);
    else params.delete(key);
    history.replaceState(null, "", `${location.pathname}?${params.toString()}${location.hash}`);
  }, [key, value]);
  return [value, setValue] as const;
}

function useMedia(query: string) {
  const [matches, setMatches] = useState(() => matchMedia(query).matches);
  useEffect(() => {
    const media = matchMedia(query);
    const listener = () => setMatches(media.matches);
    listener();
    media.addEventListener("change", listener);
    return () => media.removeEventListener("change", listener);
  }, [query]);
  return matches;
}

export default function App() {
  const [feed, setFeed] = useState<CompaniesFeed | null>(null);
  const [backtest, setBacktest] = useState<BacktestFeed | null>(null);
  const [icRows, setIcRows] = useState<IcRow[]>([]);
  const [placebo, setPlacebo] = useState<PlaceboFeed | null>(null);
  const [dark, setDark] = useState(false);

  useEffect(() => {
    loadCompanies().then(setFeed);
    loadBacktest().then(setBacktest);
    loadRecords<IcRow[]>("ic_table.json", []).then(setIcRows);
    loadRecords<PlaceboFeed | null>("placebo.json", null).then(setPlacebo);
  }, []);

  useEffect(() => {
    document.documentElement.dataset.theme = dark ? "dark" : "light";
  }, [dark]);

  if (!feed) return <Skeleton />;
  return (
    <>
      {feed.data_mode === "synthetic" && <div className="synthetic">SYNTHETIC DEMONSTRATION DATA</div>}
      <header className="topbar">
        <a href="#hero" className="brand">ESG Momentum Engine</a>
        <nav>
          <a href="#leaderboard">Leaderboard</a>
          <a href="#methodology">Methodology</a>
          <a href="#results">Results</a>
          <a href="#risks">Risks</a>
          <button className="iconButton" title="Toggle theme" onClick={() => setDark((v) => !v)}>
            {dark ? <Sun size={18} /> : <Moon size={18} />}
          </button>
        </nav>
      </header>
      <main>
        <Hero feed={feed} />
        <Idea />
        <Leaderboard feed={feed} />
        <Methodology feed={feed} icRows={icRows} placebo={placebo} />
        <Results feed={feed} backtest={backtest} />
        <Risks />
      </main>
      <footer>
        <p>Research demonstration - not investment advice.</p>
        <p>Sources, citations, and retrieval dates are placeholders for Claude prose. Built for PolyFinTech100 2026 | CGS International ESG Intelligence.</p>
      </footer>
    </>
  );
}

function Skeleton() {
  return <div className="skeletonPage"><div /><div /><div /></div>;
}

function Hero({ feed }: { feed: CompaniesFeed }) {
  const ref = useReveal<HTMLElement>();
  const [value, setValue] = useState(0);
  useEffect(() => {
    const target = feed.model.headline.net_q5q1_spread_annual_pct;
    if (matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setValue(target);
      return;
    }
    let frame = 0;
    const total = 42;
    const id = setInterval(() => {
      frame += 1;
      setValue(Number((target * Math.min(1, frame / total)).toFixed(1)));
      if (frame >= total) clearInterval(id);
    }, 16);
    return () => clearInterval(id);
  }, [feed.model.headline.net_q5q1_spread_annual_pct]);
  return (
    <section id="hero" className="hero reveal is-visible" ref={ref}>
      <div>
        <p className="eyebrow">CGS International ESG Intelligence</p>
        <h1>ESG scores are slow. The signal isn't.</h1>
        <p className="lead">A client-side research demo ranking ASEAN companies by early ESG momentum, confidence, and data coverage.</p>
        <div className="heroStat" title="Net annual Q5 minus Q1 spread from the model headline artifact.">
          <strong>{value.toFixed(1)}%</strong>
          <span>net Q5-Q1 annual spread</span>
        </div>
      </div>
      <a className="scrollCue" href="#idea" aria-label="Scroll to the idea"><ArrowDown size={20} /></a>
    </section>
  );
}

function Idea() {
  const ref = useReveal<HTMLElement>();
  return (
    <section id="idea" ref={ref} className="section reveal">
      <p className="eyebrow">The idea</p>
      <h2>Find the movement before the score catches up.</h2>
      <div className="ideaGrid">
        {[
          ["Lagging scores", "Static ESG ratings can update after market attention has already shifted.", "M0 48 C24 44 34 16 58 18 C78 20 84 42 112 28"],
          ["Alternative signals", "News tone, disclosure behavior, and transition proxies update at a faster tempo.", "M0 44 L28 30 L54 36 L80 12 L112 20"],
          ["Early entry", "The model ranks improving companies before they look obvious on static scorecards.", "M0 52 L112 12 M76 12 L112 12 L112 48"]
        ].map(([title, body, d]) => (
          <article className="ideaPanel" key={title}>
            <svg viewBox="0 0 112 64" aria-hidden="true"><path d={d} /></svg>
            <h3>{title}</h3>
            <p>{body}</p>
          </article>
        ))}
      </div>
    </section>
  );
}

function Leaderboard({ feed }: { feed: CompaniesFeed }) {
  const [query, setQuery] = useQueryState("q");
  const [country, setCountry] = useQueryState("country");
  const [sector, setSector] = useQueryState("sector");
  const [grade, setGrade] = useQueryState("grade");
  const [classification, setClassification] = useQueryState("class");
  const [flag, setFlag] = useQueryState("flag");
  const [sort, setSort] = useState<keyof Company>("rank");
  const [weights, setWeights] = useState(feed.model.validated_weights);
  const [selected, setSelected] = useQueryState("ticker");
  const [compare, setCompare] = useState<string[]>([]);

  const customWeights = PILLARS.some((key) => weights[key] !== feed.model.validated_weights[key]);
  const scored = useMemo(() => {
    const rows = feed.companies.map((company) => {
      const customScore = PILLARS.reduce((sum, key) => sum + weights[key] * company.pillar_scores[key], 0);
      return { ...company, overall_score: Number(customScore.toFixed(1)) };
    });
    return rows
      .filter((company) => {
        const term = query.toLowerCase();
        return (!term || `${company.name} ${company.ticker}`.toLowerCase().includes(term)) &&
          (!country || company.country === country) &&
          (!sector || company.sector === sector) &&
          (!grade || company.grade === grade) &&
          (!classification || company.classification === classification) &&
          (!flag || company.flags.includes(flag));
      })
      .sort((a, b) => {
        if (sort === "rank") return a.rank - b.rank;
        if (sort === "overall_score" || sort === "coverage_pct") return Number(b[sort]) - Number(a[sort]);
        return String(a[sort]).localeCompare(String(b[sort]));
      })
      .map((company, index) => ({ ...company, rank: customWeights ? index + 1 : company.rank }));
  }, [classification, country, customWeights, feed.companies, flag, grade, query, sector, sort, weights]);

  const selectedCompany = scored.find((company) => company.ticker === selected) || scored[0];
  const countries = unique(feed.companies.map((c) => c.country));
  const sectors = unique(feed.companies.map((c) => c.sector));
  const grades = ["A+", "A", "B", "C", "D"];
  const classes = ["hidden_winner", "future_leader", "overrated_leader", "value_trap"];
  const flags = unique(feed.companies.flatMap((c) => c.flags));

  return (
    <section id="leaderboard" className="leaderboard section">
      <p className="eyebrow">Leaderboard</p>
      <h2>{feed.universe_size} companies, ranked by momentum.</h2>
      <div className="toolbar">
        <label className="search"><Search size={18} /><input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search company or ticker" /></label>
        <Select label="Country" value={country} setValue={setCountry} options={countries} />
        <Select label="Sector" value={sector} setValue={setSector} options={sectors} />
        <Select label="Grade" value={grade} setValue={setGrade} options={grades} />
        <Select label="Class" value={classification} setValue={setClassification} options={classes} />
        <Select label="Flag" value={flag} setValue={setFlag} options={flags} />
      </div>
      <WeightSandbox weights={weights} setWeights={setWeights} defaults={feed.model.validated_weights} custom={customWeights} />
      <VirtualTable rows={scored} sort={sort} setSort={setSort} onOpen={setSelected} onCompare={(ticker) => setCompare((items) => items.includes(ticker) ? items.filter((item) => item !== ticker) : items.length < 4 ? [...items, ticker] : items)} compare={compare} />
      {selectedCompany && <CompanyDetail company={selectedCompany} flags={feed.flags} compareCompanies={compare.map((ticker) => scored.find((c) => c.ticker === ticker)).filter(isCompany)} />}
    </section>
  );
}

function Select({ label, value, setValue, options }: { label: string; value: string; setValue: (v: string) => void; options: string[] }) {
  return <label className="select">{label}<select value={value} onChange={(e) => setValue(e.target.value)}><option value="">All</option>{options.map((option) => <option key={option}>{option}</option>)}</select></label>;
}

function WeightSandbox({ weights, setWeights, defaults, custom }: { weights: Record<PillarKey, number>; setWeights: (v: Record<PillarKey, number>) => void; defaults: Record<PillarKey, number>; custom: boolean }) {
  return (
    <aside className="sandbox">
      <div>
        <h3>Weight sandbox</h3>
        <p>Data coverage is display-only and excluded from the weighted score.</p>
      </div>
      {custom && <strong className="customBanner">Custom weights - rankings differ from the validated model</strong>}
      <div className="sliders">
        {PILLARS.map((key) => (
          <label key={key} title="Changes recompute the client-side weighted score.">
            <span>{labelFor(key)}</span>
            <input type="range" min="0" max="1" step="0.01" value={weights[key]} onChange={(e) => setWeights({ ...weights, [key]: Number(e.target.value) })} />
            <output>{weights[key].toFixed(2)}</output>
          </label>
        ))}
      </div>
      <button className="secondary" onClick={() => setWeights(defaults)}><RotateCcw size={16} /> Reset</button>
    </aside>
  );
}

function VirtualTable({ rows, sort, setSort, onOpen, onCompare, compare }: { rows: Company[]; sort: keyof Company; setSort: (v: keyof Company) => void; onOpen: (ticker: string) => void; onCompare: (ticker: string) => void; compare: string[] }) {
  const isMobile = useMedia("(max-width: 900px)");
  const rowHeight = isMobile ? 120 : 72;
  const height = 560;
  const [scrollTop, setScrollTop] = useState(0);
  const start = Math.max(0, Math.floor(scrollTop / rowHeight) - 4);
  const end = Math.min(rows.length, start + Math.ceil(height / rowHeight) + 9);
  const visible = rows.slice(start, end);
  const sortButton = (key: keyof Company, label: string) => <button className={sort === key ? "activeSort" : ""} onClick={() => setSort(key)}>{label}</button>;
  return (
    <div className="tableShell">
      <div className="thead">{sortButton("rank", "Rank")}{sortButton("name", "Company")}{sortButton("country", "Country")}{sortButton("sector", "Sector")}{sortButton("overall_score", "Score")}{sortButton("classification", "Class")}{sortButton("coverage_pct", "Coverage")}</div>
      <div className="virtual" style={{ height }} onScroll={(e) => setScrollTop(e.currentTarget.scrollTop)}>
        <div style={{ height: rows.length * rowHeight, position: "relative" }}>
          {visible.map((company, idx) => (
            <div className="row" key={company.ticker} style={{ transform: `translateY(${(start + idx) * rowHeight}px)` }} tabIndex={0} onKeyDown={(e) => e.key === "Enter" && onOpen(company.ticker)}>
              <button onClick={() => onOpen(company.ticker)} className="cell rank">{company.rank}</button>
              <button onClick={() => onOpen(company.ticker)} className="cell company"><strong>{company.name}</strong><span>{company.ticker}</span></button>
              <span className="cell">{company.country}</span>
              <span className="cell truncate">{company.sector}</span>
              <span className="cell score"><b>{company.overall_score.toFixed(1)}</b><em>{company.grade}</em><i style={{ width: `${company.confidence_high - company.confidence_low}%`, left: `${company.confidence_low}%` }} /></span>
              <span className={`chip ${company.classification}`}>{company.classification.replaceAll("_", " ")}</span>
              <span className="cell coverage">{company.coverage_pct.toFixed(0)}%</span>
              <button className={compare.includes(company.ticker) ? "compare on" : "compare"} onClick={() => onCompare(company.ticker)}>Compare</button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function CompanyDetail({ company, flags, compareCompanies }: { company: Company; flags: CompaniesFeed["flags"]; compareCompanies: Company[] }) {
  return (
    <section className="detail" id="company">
      <div className="detailHeader">
        <div className="radial" style={{ "--score": `${company.overall_score * 3.6}deg` } as React.CSSProperties}><span>{company.overall_score.toFixed(0)}</span></div>
        <div>
          <p className="eyebrow">{company.ticker} | {company.country} | {company.sector}</p>
          <h2>{company.name}</h2>
          <p className="explanation">{company.explanation}</p>
        </div>
      </div>
      <div className="detailGrid">
        <div className="pillarBlock">{PILLARS.map((key) => <div className="bar" key={key} title={`${labelFor(key)} score`}><span>{labelFor(key)}</span><i><b style={{ width: `${company.pillar_scores[key]}%` }} /></i><em>{company.pillar_scores[key].toFixed(0)}</em></div>)}</div>
        <Matrix company={company} />
        <Timeline company={company} />
        <div className="coverageBlock"><h3>Risk flags</h3>{company.flags.length ? company.flags.map((flag) => <span className="flag" key={flag} title={flags.find((f) => f.key === flag)?.tooltip || flag}>{flag.replaceAll("_", " ")}</span>) : <p>No active risk flags.</p>}<h3>Data coverage</h3><strong>{company.coverage_pct.toFixed(0)}%</strong></div>
      </div>
      {compareCompanies.length > 0 && <Compare companies={compareCompanies} />}
    </section>
  );
}

function Matrix({ company }: { company: Company }) {
  return <div className="matrix"><span>Momentum</span><i style={{ left: `${company.esg_level_pctile}%`, bottom: `${company.esg_momentum_pctile}%` }} /><b>Level</b></div>;
}

function Timeline({ company }: { company: Company }) {
  if (!company.timeseries) return <div className="emptyState">No timeseries available for this company.</div>;
  const points = company.timeseries.score.map((value, index, arr) => `${(index / (arr.length - 1)) * 100},${100 - value}`).join(" ");
  return <div className="timeline"><svg viewBox="0 0 100 100" preserveAspectRatio="none"><polyline points={points} /></svg><span>Score timeline</span></div>;
}

function Compare({ companies }: { companies: Company[] }) {
  return <div className="comparePanel"><h3>Compare</h3><div>{companies.map((company) => <article key={company.ticker}><strong>{company.name}</strong><span>{company.overall_score.toFixed(1)} | {company.grade}</span>{PILLARS.map((key) => <i key={key}><b style={{ width: `${company.pillar_scores[key]}%` }} /></i>)}</article>)}</div></div>;
}

function Methodology({ feed, icRows, placebo }: { feed: CompaniesFeed; icRows: IcRow[]; placebo: PlaceboFeed | null }) {
  const ref = useReveal<HTMLElement>();
  const [open, setOpen] = useState(false);
  return (
    <section id="methodology" ref={ref} className="section reveal">
      <p className="eyebrow">Methodology</p>
      <h2>Transparent variables, composites, and validation.</h2>
      <button className="secondary" onClick={() => setOpen((v) => !v)}>How to read this</button>
      {open && <p className="measure">Each chart reads from the JSON contracts. Placeholder prose remains intentionally brief until Claude supplies final research text.</p>}
      <div className="chartGrid">
        <Suspense fallback={<div className="chartSkeleton" />}>
          <Plot title="Validation IC" data={[{ type: "bar", x: icRows.map((r) => r.label || r.variable), y: icRows.map((r) => r.ic_3m), marker: { color: "#3B3BFF" } }]} />
          <Plot title="Placebo" data={[{ type: "bar", x: placebo?.hist_bins || [0], y: placebo?.hist_counts || [1], marker: { color: "#BFC0FF" } }]} shapes={placebo ? [{ type: "line", x0: placebo.realized_spread, x1: placebo.realized_spread, y0: 0, y1: 1, yref: "paper", line: { color: "#3B3BFF", width: 3 } }] : []} />
        </Suspense>
      </div>
      <p className="measure">Validated weights: {PILLARS.map((key) => `${labelFor(key)} ${feed.model.validated_weights[key].toFixed(2)}`).join(", ")}.</p>
    </section>
  );
}

function Results({ feed, backtest }: { feed: CompaniesFeed; backtest: BacktestFeed | null }) {
  const ref = useReveal<HTMLElement>();
  return (
    <section id="results" ref={ref} className="section reveal">
      <p className="eyebrow">Results</p>
      <h2>Interactive model outputs.</h2>
      <div className="stats">
        <Metric label="Deflated Sharpe" value={feed.model.headline.deflated_sharpe.toFixed(2)} />
        <Metric label="Test IC" value={feed.model.headline.test_ic.toFixed(3)} />
        <Metric label="Net Sharpe" value={feed.model.headline.sharpe_net.toFixed(2)} />
      </div>
      {backtest && (
        <Suspense fallback={<div className="chartSkeleton" />}>
          <Plot title="Q5 vs Q1 vs benchmark" data={[
            { type: "scatter", mode: "lines", name: "Q5", x: backtest.dates, y: backtest.q5 },
            { type: "scatter", mode: "lines", name: "Q1", x: backtest.dates, y: backtest.q1 },
            { type: "scatter", mode: "lines", name: "Benchmark", x: backtest.dates, y: backtest.benchmark },
            { type: "scatter", mode: "lines", name: "Naive ESG", x: backtest.dates, y: backtest.naive_esg_q5 }
          ]} shapes={[{ type: "line", x0: backtest.dates[backtest.train_end_index], x1: backtest.dates[backtest.train_end_index], y0: 0, y1: 1, yref: "paper", line: { dash: "dot", color: "#555" } }]} />
        </Suspense>
      )}
    </section>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return <div className="metric" title={`Definition for ${label}.`}><span>{label}</span><strong>{value}</strong></div>;
}

function Risks() {
  return <section id="risks" className="section risks"><p className="eyebrow">Risks</p><h2>Limits are part of the product.</h2>{["Data coverage", "Market microstructure", "Model drift"].map((risk, index) => <article key={risk}><strong>Severity {index + 1}</strong><h3>{risk}</h3><p>Placeholder risk text for Claude to replace with final report language.</p></article>)}</section>;
}

function unique(values: string[]) {
  return Array.from(new Set(values.filter(Boolean))).sort();
}

function isCompany(company: Company | undefined): company is Company {
  return Boolean(company);
}

function labelFor(key: PillarKey) {
  return key.split("_").map((part) => part[0].toUpperCase() + part.slice(1)).join(" ");
}
