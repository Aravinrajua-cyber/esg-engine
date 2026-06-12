// Dependency-free runtime validation of the /site_data JSON contract (schema_version 1).
// Payloads arrive as `unknown`; nothing is rendered from a file that fails validation.
// Errors name the JSON path of each failure, capped at MAX_ERRORS per file.

import {
  BacktestFeed,
  Company,
  CompaniesFeed,
  GroupSpreadRow,
  IcRow,
  PillarKey,
  PlaceboFeed
} from "./types";

export type ValidationResult<T> = { ok: true; data: T } | { ok: false; errors: string[] };

const MAX_ERRORS = 10;
const GRADES = new Set(["A+", "A", "B", "C", "D"]);
const CLASSIFICATIONS = new Set(["hidden_winner", "future_leader", "overrated_leader", "value_trap"]);
const FLAG_KEYS = new Set(["LOW_COVERAGE", "CONTROVERSY_RISING", "LOW_LIQUIDITY", "HIGH_VOL", "STALE_DATA"]);
const PILLAR_KEYS: PillarKey[] = ["sentiment_dynamics", "transition_readiness", "governance_credibility", "disclosure_behavior"];

class Ctx {
  errors: string[] = [];
  fail(path: string, message: string): false {
    if (this.errors.length < MAX_ERRORS) this.errors.push(`${path}: ${message}`);
    return false;
  }
  full(): boolean {
    return this.errors.length >= MAX_ERRORS;
  }
}

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function str(ctx: Ctx, obj: Record<string, unknown>, key: string, path: string): boolean {
  return typeof obj[key] === "string" && (obj[key] as string).length > 0 ? true : ctx.fail(`${path}.${key}`, "expected non-empty string");
}

function num(ctx: Ctx, value: unknown, path: string, lo = -Infinity, hi = Infinity): boolean {
  if (typeof value !== "number" || !Number.isFinite(value)) return ctx.fail(path, "expected finite number");
  if (value < lo || value > hi) return ctx.fail(path, `expected number in [${lo}, ${hi}]`);
  return true;
}

function bool(ctx: Ctx, value: unknown, path: string): boolean {
  return typeof value === "boolean" ? true : ctx.fail(path, "expected boolean");
}

function numArray(ctx: Ctx, value: unknown, path: string, allowNull = false): value is (number | null)[] {
  if (!Array.isArray(value)) return ctx.fail(path, "expected array");
  for (let i = 0; i < value.length; i++) {
    const x = value[i];
    if (x === null && allowNull) continue;
    if (typeof x !== "number" || !Number.isFinite(x)) return ctx.fail(`${path}[${i}]`, "expected finite number");
  }
  return true;
}

function validateCompany(ctx: Ctx, raw: unknown, path: string): raw is Company {
  if (!isObject(raw)) return ctx.fail(path, "expected object");
  for (const key of ["ticker", "name", "country", "exchange", "sector", "mcap_tier", "currency"]) str(ctx, raw, key, path);
  num(ctx, raw.rank, `${path}.rank`, 1);
  num(ctx, raw.overall_score, `${path}.overall_score`, 0, 100);
  if (typeof raw.grade !== "string" || !GRADES.has(raw.grade)) ctx.fail(`${path}.grade`, "expected grade A+|A|B|C|D");
  num(ctx, raw.confidence_low, `${path}.confidence_low`, 0, 100);
  num(ctx, raw.confidence_high, `${path}.confidence_high`, 0, 100);
  num(ctx, raw.coverage_pct, `${path}.coverage_pct`, 0, 100);
  if (typeof raw.classification !== "string" || !CLASSIFICATIONS.has(raw.classification)) {
    ctx.fail(`${path}.classification`, "unknown classification");
  }
  num(ctx, raw.esg_level_pctile, `${path}.esg_level_pctile`, 0, 100);
  num(ctx, raw.esg_momentum_pctile, `${path}.esg_momentum_pctile`, 0, 100);
  if (!isObject(raw.pillar_scores)) {
    ctx.fail(`${path}.pillar_scores`, "expected object");
  } else {
    for (const key of [...PILLAR_KEYS, "data_coverage"]) num(ctx, raw.pillar_scores[key], `${path}.pillar_scores.${key}`, 0, 100);
  }
  if (!Array.isArray(raw.flags)) {
    ctx.fail(`${path}.flags`, "expected array");
  } else {
    raw.flags.forEach((flag, i) => {
      if (typeof flag !== "string" || !FLAG_KEYS.has(flag)) ctx.fail(`${path}.flags[${i}]`, "unknown flag key");
    });
  }
  str(ctx, raw, "explanation", path);
  if (raw.timeseries !== null && raw.timeseries !== undefined) {
    const ts = raw.timeseries;
    if (!isObject(ts) || !Array.isArray(ts.dates)) {
      ctx.fail(`${path}.timeseries`, "expected null or object with dates[]");
    } else {
      const n = ts.dates.length;
      for (const key of ["price_usd", "sentiment_tone", "score"]) {
        if (numArray(ctx, ts[key], `${path}.timeseries.${key}`, true) && (ts[key] as unknown[]).length !== n) {
          ctx.fail(`${path}.timeseries.${key}`, `length ${(ts[key] as unknown[]).length} != dates length ${n}`);
        }
      }
    }
  }
  return ctx.errors.length === 0;
}

export function validateCompaniesPayload(raw: unknown): ValidationResult<CompaniesFeed> {
  const ctx = new Ctx();
  if (!isObject(raw)) return { ok: false, errors: ["root: expected object"] };
  if (raw.schema_version !== 1) ctx.fail("schema_version", "expected 1");
  if (raw.data_mode !== "live" && raw.data_mode !== "synthetic") ctx.fail("data_mode", "expected 'live' | 'synthetic'");
  str(ctx, raw, "generated_at", "root");
  str(ctx, raw, "as_of_date", "root");
  num(ctx, raw.universe_size, "universe_size", 1);
  if (!isObject(raw.model)) {
    ctx.fail("model", "expected object");
  } else {
    str(ctx, raw.model, "winning_composite", "model");
    str(ctx, raw.model, "train_end", "model");
    if (!isObject(raw.model.validated_weights)) {
      ctx.fail("model.validated_weights", "expected object");
    } else {
      for (const key of PILLAR_KEYS) num(ctx, raw.model.validated_weights[key], `model.validated_weights.${key}`, 0, 1);
    }
    if (!isObject(raw.model.headline)) {
      ctx.fail("model.headline", "expected object");
    } else {
      for (const key of ["net_q5q1_spread_annual_pct", "deflated_sharpe", "test_ic", "sharpe_net"]) {
        num(ctx, raw.model.headline[key], `model.headline.${key}`);
      }
    }
  }
  for (const metaKey of ["pillars", "flags"] as const) {
    const list = raw[metaKey];
    if (!Array.isArray(list) || list.length === 0) {
      ctx.fail(metaKey, "expected non-empty array");
    } else {
      list.forEach((entry, i) => {
        if (!isObject(entry)) {
          ctx.fail(`${metaKey}[${i}]`, "expected object");
          return;
        }
        for (const field of metaKey === "pillars" ? ["key", "label", "description"] : ["key", "label", "tooltip"]) {
          str(ctx, entry, field, `${metaKey}[${i}]`);
        }
      });
    }
  }
  if (!Array.isArray(raw.companies) || raw.companies.length === 0) {
    ctx.fail("companies", "expected non-empty array");
  } else {
    for (let i = 0; i < raw.companies.length && !ctx.full(); i++) {
      validateCompany(ctx, raw.companies[i], `companies[${i}]`);
    }
  }
  return ctx.errors.length ? { ok: false, errors: ctx.errors } : { ok: true, data: raw as unknown as CompaniesFeed };
}

export function validateBacktestPayload(raw: unknown): ValidationResult<BacktestFeed> {
  const ctx = new Ctx();
  if (!isObject(raw)) return { ok: false, errors: ["root: expected object"] };
  if (!Array.isArray(raw.dates) || raw.dates.length === 0 || raw.dates.some((d) => typeof d !== "string")) {
    ctx.fail("dates", "expected non-empty string array");
  }
  const n = Array.isArray(raw.dates) ? raw.dates.length : 0;
  for (const key of ["q5", "q1", "benchmark"]) {
    if (numArray(ctx, raw[key], key) && (raw[key] as unknown[]).length !== n) ctx.fail(key, `length != dates length ${n}`);
  }
  if (numArray(ctx, raw.naive_esg_q5, "naive_esg_q5")) {
    const len = (raw.naive_esg_q5 as unknown[]).length;
    if (len !== 0 && len !== n) ctx.fail("naive_esg_q5", `length must be 0 or ${n}`);
  }
  bool(ctx, raw.net, "net");
  if (!Number.isInteger(raw.train_end_index) || (raw.train_end_index as number) < 0 || (raw.train_end_index as number) >= Math.max(n, 1)) {
    ctx.fail("train_end_index", `expected integer in [0, ${Math.max(n - 1, 0)}]`);
  }
  return ctx.errors.length ? { ok: false, errors: ctx.errors } : { ok: true, data: raw as unknown as BacktestFeed };
}

export function validateIcTablePayload(raw: unknown): ValidationResult<IcRow[]> {
  const ctx = new Ctx();
  if (!Array.isArray(raw)) return { ok: false, errors: ["root: expected array"] };
  raw.forEach((row, i) => {
    if (ctx.full()) return;
    if (!isObject(row)) {
      ctx.fail(`[${i}]`, "expected object");
      return;
    }
    str(ctx, row, "variable", `[${i}]`);
    str(ctx, row, "label", `[${i}]`);
    if (row.ic_3m !== null) num(ctx, row.ic_3m, `[${i}].ic_3m`);
    if (row.t_nw !== null) num(ctx, row.t_nw, `[${i}].t_nw`);
    bool(ctx, row.fdr_survived, `[${i}].fdr_survived`);
  });
  return ctx.errors.length ? { ok: false, errors: ctx.errors } : { ok: true, data: raw as unknown as IcRow[] };
}

export function validatePlaceboPayload(raw: unknown): ValidationResult<PlaceboFeed> {
  const ctx = new Ctx();
  if (!isObject(raw)) return { ok: false, errors: ["root: expected object"] };
  num(ctx, raw.realized_spread, "realized_spread");
  numArray(ctx, raw.hist_bins, "hist_bins");
  numArray(ctx, raw.hist_counts, "hist_counts");
  if (Array.isArray(raw.hist_bins) && Array.isArray(raw.hist_counts)) {
    const bins = raw.hist_bins.length;
    const counts = raw.hist_counts.length;
    // accept either bin-edge convention (counts + 1) or aligned bin centers
    if (bins !== counts && bins !== counts + 1) ctx.fail("hist_bins", `length ${bins} incompatible with hist_counts ${counts}`);
    if ((raw.hist_counts as number[]).some((c) => c < 0)) ctx.fail("hist_counts", "expected non-negative counts");
  }
  return ctx.errors.length ? { ok: false, errors: ctx.errors } : { ok: true, data: raw as unknown as PlaceboFeed };
}

export function validateGroupSpreadPayload(raw: unknown): ValidationResult<GroupSpreadRow[]> {
  const ctx = new Ctx();
  if (!Array.isArray(raw)) return { ok: false, errors: ["root: expected array"] };
  raw.forEach((row, i) => {
    if (ctx.full()) return;
    if (!isObject(row)) {
      ctx.fail(`[${i}]`, "expected object");
      return;
    }
    str(ctx, row, "key", `[${i}]`);
    num(ctx, row.spread_net, `[${i}].spread_net`);
  });
  return ctx.errors.length ? { ok: false, errors: ctx.errors } : { ok: true, data: raw as unknown as GroupSpreadRow[] };
}
