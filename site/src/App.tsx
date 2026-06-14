import { ArrowDown, BarChart3, RotateCcw, Search } from "lucide-react";
import React, { useEffect, useMemo, useRef, useState } from "react";
import { loadCompanies, LoadIssue } from "./data";
import siteContent from "./site_content.json";
import ModelPerformance from "./ModelPerformance";
import { Company, CompaniesFeed, PillarKey } from "./types";
const PILLARS: PillarKey[] = ["sentiment_dynamics", "transition_readiness", "governance_credibility", "disclosure_behavior"];
const COMPONENT_LABELS: Record<PillarKey, string> = {
  sentiment_dynamics: "S component: Sentiment Dynamics",
  transition_readiness: "E component: Transition Readiness",
  governance_credibility: "G component: Governance Credibility",
  disclosure_behavior: "Non-ESG component: Disclosure Behavior"
};
const RISK_FLAG_WEIGHTS: Record<string, number> = {
  LOW_COVERAGE: 30,
  CONTROVERSY_RISING: 25,
  LOW_LIQUIDITY: 20,
  HIGH_VOL: 15,
  STALE_DATA: 10
};

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
  const [issues, setIssues] = useState<LoadIssue[]>([]);
  const [feedFailed, setFeedFailed] = useState(false);

  useEffect(() => {
    const addIssue = (issue: LoadIssue | null) => {
      if (!issue) return;
      console.error(`site_data validation failed for ${issue.file}:`, issue.errors);
      setIssues((prev) => [...prev, issue]);
    };
    loadCompanies().then((r) => {
      addIssue(r.issue);
      if (r.data) setFeed(r.data);
      else setFeedFailed(true);
    });
  }, []);

  if (feedFailed) return <DataError issues={issues} />;
  if (!feed) return <Skeleton />;
  return (
    <>
      {feed.data_mode === "synthetic" && <div className="synthetic">SYNTHETIC DEMONSTRATION DATA</div>}
      {feed.data_mode === "live" && <div className="liveTag">LIVE DATA · as of {feed.as_of_date}</div>}
      {issues.length > 0 && (
        <div className="issueStrip" role="alert">
          Data files failed validation and were not rendered: {issues.map((issue) => issue.file).join(", ")}. See console for details.
        </div>
      )}
      <header className="topbar">
        <a href="#hero" className="brand">{siteContent.brand}</a>
        <nav>
          <a href="#hero">Overview</a>
          <a href="#model-performance">Model Performance</a>
          <a href="#universe">Universe</a>
          <a href="#risks">Risks</a>
        </nav>
      </header>
      <main>
        <Hero feed={feed} />
        <Idea />
        <Leaderboard feed={feed} />
        <ModelPerformance dataMode={feed.data_mode} />
        <Methodology feed={feed} />
        <Results feed={feed} />
        <Risks />
      </main>
      <footer>
        <p>{siteContent.footer.disclaimer}</p>
        <p>{siteContent.footer.sourceNote}</p>
      </footer>
    </>
  );
}

function Skeleton() {
  return <div className="skeletonPage"><div /><div /><div /></div>;
}

function DataError({ issues }: { issues: LoadIssue[] }) {
  return (
    <div className="dataError" role="alert">
      <h1>Data failed validation</h1>
      <p>The site data did not match the expected schema and was not rendered.</p>
      {issues.map((issue) => (
        <section key={issue.file}>
          <h2>{issue.file}</h2>
          <ul>{issue.errors.map((error) => <li key={error}>{error}</li>)}</ul>
        </section>
      ))}
      <p>Regenerate the feed (`python -m src.scoring.score`) or check `SCHEMAS.md`.</p>
    </div>
  );
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
        <p className="eyebrow">{siteContent.hero.eyebrow}</p>
        <h1>{siteContent.hero.title}</h1>
        <p className="lead">{siteContent.hero.lead}</p>
        <div className="heroStat" title={siteContent.hero.statTitle}>
          <strong>{value.toFixed(1)}%</strong>
          <span>{siteContent.hero.statLabel}</span>
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
      <p className="eyebrow">{siteContent.idea.eyebrow}</p>
      <h2>{siteContent.idea.title}</h2>
      <div className="ideaGrid">
        {siteContent.idea.cards.map((card) => (
          <article className="ideaPanel" key={card.title}>
            <svg viewBox="0 0 112 64" aria-hidden="true"><path d={card.path} /></svg>
            <h3>{card.title}</h3>
            <p>{card.body}</p>
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
    <section id="universe" className="leaderboard section">
      <p className="eyebrow">The Universe</p>
      <h2>{feed.universe_size} ASEAN companies, ranked by ESG momentum</h2>
      <p className="measure">Search, filter and sort every company the model scores. Click a row to open its score breakdown, risk flags and confidence range. Drag the sliders to re-weight the four signal groups and the ranking updates live.</p>
      <div className="toolbar">
        <label className="search"><Search size={18} /><input value={query} onChange={(e) => setQuery(e.target.value)} placeholder={siteContent.leaderboard.searchPlaceholder} /></label>
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
        <h3>{siteContent.leaderboard.weightSandboxTitle}</h3>
        <p>{siteContent.leaderboard.weightSandboxBody}</p>
      </div>
      {custom && <strong className="customBanner">{siteContent.leaderboard.customWeightsBanner}</strong>}
      <div className="sliders">
        {PILLARS.map((key) => (
          <label key={key} title="Changes recompute the client-side weighted score.">
            <span>{labelFor(key)}</span>
            <input type="range" min="0" max="1" step="0.01" value={weights[key]} onChange={(e) => setWeights({ ...weights, [key]: Number(e.target.value) })} />
            <output>{weights[key].toFixed(2)}</output>
          </label>
        ))}
      </div>
      <button className="secondary" onClick={() => setWeights(defaults)}><RotateCcw size={16} /> {siteContent.leaderboard.resetLabel}</button>
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
  const riskIndex = derivedRiskIndex(company);
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
        <div className="pillarBlock">{PILLARS.map((key) => <div className="bar" key={key} title={`${COMPONENT_LABELS[key]} score`}><span>{COMPONENT_LABELS[key]}</span><i><b style={{ width: `${company.pillar_scores[key]}%` }} /></i><em>{company.pillar_scores[key].toFixed(0)}</em></div>)}</div>
        <Matrix company={company} />
        <Timeline company={company} />
        <div className="coverageBlock">
          <h3>Risk index</h3>
          <strong title="Derived client-side from uncovered data plus weighted active flags; not stored in the source schema.">{riskIndex}</strong>
          <p>Derived from coverage gaps and active flags.</p>
          <h3>Risk flags</h3>
          {company.flags.length ? company.flags.map((flag) => <span className="flag" key={flag} title={flags.find((f) => f.key === flag)?.tooltip || flag}>{flag.replaceAll("_", " ")}</span>) : <p>No active risk flags.</p>}
          <h3>Data coverage</h3>
          <strong>{company.coverage_pct.toFixed(0)}%</strong>
        </div>
      </div>
      {compareCompanies.length > 0 && <Compare companies={compareCompanies} />}
    </section>
  );
}

function Matrix({ company }: { company: Company }) {
  return (
    <div className="matrixWrap">
      <h3>Level vs momentum</h3>
      <div className="matrix" title="Horizontal = current ESG level percentile. Vertical = ESG momentum percentile. The dot is this company.">
        <i style={{ left: `${company.esg_level_pctile}%`, bottom: `${company.esg_momentum_pctile}%` }} />
        <span>Momentum ↑</span>
        <b>ESG level →</b>
      </div>
      <p className="matrixCaption">Dot = this company. Top-left = improving fast but still low on ESG level (a "hidden winner").</p>
    </div>
  );
}

function Timeline({ company }: { company: Company }) {
  if (!company.timeseries) return <div className="emptyState">No score history available for this company.</div>;
  const arr = company.timeseries.score;
  const points = arr
    .map((value, index) => (value == null ? null : `${(index / Math.max(1, arr.length - 1)) * 100},${100 - value}`))
    .filter((p): p is string => p !== null)
    .join(" ");
  return <div className="timeline"><svg viewBox="0 0 100 100" preserveAspectRatio="none"><polyline points={points} /></svg><span>Score over time (higher = better)</span></div>;
}

function Compare({ companies }: { companies: Company[] }) {
  return (
    <div className="comparePanel">
      <h3>Compare ({companies.length})</h3>
      <div>
        {companies.map((company) => (
          <article key={company.ticker}>
            <strong>{company.name}</strong>
            <span>Score {company.overall_score.toFixed(1)} · Grade {company.grade}</span>
            {PILLARS.map((key) => (
              <div className="compareBar" key={key}>
                <small>{labelFor(key)}</small>
                <i><b style={{ width: `${company.pillar_scores[key]}%` }} /></i>
                <em>{company.pillar_scores[key].toFixed(0)}</em>
              </div>
            ))}
          </article>
        ))}
      </div>
    </div>
  );
}

function Methodology({ feed }: { feed: CompaniesFeed }) {
  const ref = useReveal<HTMLElement>();
  const [open, setOpen] = useState(false);
  return (
    <section id="methodology" ref={ref} className="section reveal">
      <p className="eyebrow">{siteContent.methodology.eyebrow}</p>
      <h2>{siteContent.methodology.title}</h2>
      <button className="secondary" onClick={() => setOpen((v) => !v)}>{siteContent.methodology.buttonLabel}</button>
      {open && <p className="measure">{siteContent.methodology.explainer}</p>}
      <p className="measure">The validation evidence — signal ICs, composite returns, the build/drop audit trail, the placebo control and the universe funnel — is on the <a href="#model-performance">Model Performance</a> page.</p>
      <p className="measure">{siteContent.methodology.validatedWeightsPrefix} {PILLARS.map((key) => `${labelFor(key)} ${feed.model.validated_weights[key].toFixed(2)}`).join(", ")}.</p>
    </section>
  );
}

function Results({ feed }: { feed: CompaniesFeed }) {
  const ref = useReveal<HTMLElement>();
  return (
    <section id="results" ref={ref} className="section reveal">
      <p className="eyebrow">{siteContent.results.eyebrow}</p>
      <h2>{siteContent.results.title}</h2>
      <div className="stats">
        <Metric label={siteContent.results.metrics.deflatedSharpe} value={feed.model.headline.deflated_sharpe.toFixed(2)} />
        <Metric label={siteContent.results.metrics.testIc} value={feed.model.headline.test_ic.toFixed(3)} />
        <Metric label={siteContent.results.metrics.netSharpe} value={feed.model.headline.sharpe_net.toFixed(2)} />
      </div>
      <p className="measure">These are the frozen model results in plain terms: a risk-adjusted score, out-of-sample predictive power, and after-cost return per unit of risk. The net top-vs-bottom edge is positive but not yet statistically reliable — the full picture is on the <a href="#model-performance">Model Performance</a> charts.</p>
    </section>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return <div className="metric" title={`Definition for ${label}.`}><span>{label}</span><strong>{value}</strong></div>;
}

function Risks() {
  return <section id="risks" className="section risks"><p className="eyebrow">{siteContent.risks.eyebrow}</p><h2>{siteContent.risks.title}</h2>{siteContent.risks.cards.map((risk) => <article key={risk.title}><strong>{risk.severity}</strong><h3>{risk.title}</h3><p>{risk.body}</p></article>)}</section>;
}

function unique(values: string[]) {
  return Array.from(new Set(values.filter(Boolean))).sort();
}

function isCompany(company: Company | undefined): company is Company {
  return Boolean(company);
}

function derivedRiskIndex(company: Company) {
  const coverageGap = Math.max(0, 100 - company.coverage_pct);
  const flagLoad = company.flags.reduce((sum, flag) => sum + (RISK_FLAG_WEIGHTS[flag] || 0), 0);
  return Math.min(100, Math.round(coverageGap + flagLoad));
}

function labelFor(key: PillarKey) {
  return key.split("_").map((part) => part[0].toUpperCase() + part.slice(1)).join(" ");
}
