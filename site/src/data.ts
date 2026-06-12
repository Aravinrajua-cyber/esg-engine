import { BacktestFeed, CompaniesFeed, IcRow, PlaceboFeed } from "./types";
import { mockBacktest, mockCompaniesFeed } from "./mockData";
import {
  ValidationResult,
  validateBacktestPayload,
  validateCompaniesPayload,
  validateIcTablePayload,
  validatePlaceboPayload
} from "./validate";

export interface LoadIssue {
  file: string;
  errors: string[];
}

// data: null with an issue means the file existed but failed validation — callers must not
// render from it. data: null without an issue means the optional file was simply absent.
// fromMock means the file could not be fetched (dev mode) and the bundled synthetic mock was
// used instead; the mock is data_mode "synthetic" so the banner stays on.
export interface Loaded<T> {
  data: T | null;
  issue: LoadIssue | null;
  fromMock: boolean;
}

const FETCH_FAILED = Symbol("fetch-failed");

async function fetchJson(path: string): Promise<unknown | typeof FETCH_FAILED> {
  try {
    const res = await fetch(path, { cache: "no-store" });
    if (!res.ok) return FETCH_FAILED;
    return (await res.json()) as unknown;
  } catch {
    return FETCH_FAILED;
  }
}

async function loadValidated<T>(
  file: string,
  validate: (raw: unknown) => ValidationResult<T>,
  mockFallback?: T
): Promise<Loaded<T>> {
  const raw = await fetchJson(`/site_data/${file}`);
  if (raw === FETCH_FAILED) {
    return mockFallback !== undefined
      ? { data: mockFallback, issue: null, fromMock: true }
      : { data: null, issue: null, fromMock: false }; // optional file absent: render without it
  }
  const result = validate(raw);
  return result.ok
    ? { data: result.data, issue: null, fromMock: false }
    : { data: null, issue: { file, errors: result.errors }, fromMock: false };
}

export function loadCompanies(): Promise<Loaded<CompaniesFeed>> {
  return loadValidated("companies.json", validateCompaniesPayload, mockCompaniesFeed);
}

export function loadBacktest(): Promise<Loaded<BacktestFeed>> {
  return loadValidated("backtest.json", validateBacktestPayload, mockBacktest);
}

export function loadIcTable(): Promise<Loaded<IcRow[]>> {
  return loadValidated("ic_table.json", validateIcTablePayload);
}

export function loadPlacebo(): Promise<Loaded<PlaceboFeed>> {
  return loadValidated("placebo.json", validatePlaceboPayload);
}
