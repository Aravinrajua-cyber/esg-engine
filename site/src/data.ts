import { BacktestFeed, CompaniesFeed } from "./types";
import { mockBacktest, mockCompaniesFeed } from "./mockData";

async function loadJson<T>(path: string, fallback: T): Promise<T> {
  try {
    const res = await fetch(path, { cache: "no-store" });
    if (!res.ok) return fallback;
    return (await res.json()) as T;
  } catch {
    return fallback;
  }
}

export async function loadCompanies(): Promise<CompaniesFeed> {
  return loadJson<CompaniesFeed>("/site_data/companies.json", mockCompaniesFeed);
}

export async function loadBacktest(): Promise<BacktestFeed> {
  return loadJson<BacktestFeed>("/site_data/backtest.json", mockBacktest);
}

export async function loadRecords<T>(file: string, fallback: T): Promise<T> {
  return loadJson<T>(`/site_data/${file}`, fallback);
}
