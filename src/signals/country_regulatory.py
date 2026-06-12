"""Phase 2.6 / Signal F1 — country ESG-regulatory momentum index (hand-built, fully cited).

A slowly-varying 0–10 country overlay (NOT a per-company signal) scoring each market's ESG
regulatory trajectory from four documented components:
  1. Carbon pricing            (0–3): operational carbon tax / ETS with a rising trajectory
  2. Mandatory climate disclosure (0–3): ISSB-aligned mandatory listed-issuer disclosure
  3. Sustainable-finance taxonomy (0–2): national / adopted green taxonomy
  4. Stewardship & governance code (0–2): institutional-investor stewardship code

Every input is sourced with a public citation + date (see CITATIONS) so the report's framework
registry can reproduce it. Used in Phase 4 as the F1 interaction: company-level signals are
hypothesised stronger in high-regulatory-momentum regimes — tested explicitly, not assumed.

Run:  python -m src.signals.country_regulatory
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.util.log import log_action  # noqa: E402

INTERIM = ROOT / "data" / "interim"
INTERIM.mkdir(parents=True, exist_ok=True)

# country -> component scores. Justifications are summarised; full citations in CITATIONS.
SCORES = {
    "Singapore":  {"carbon_pricing": 3.0, "climate_disclosure": 3.0, "taxonomy": 2.0, "stewardship": 1.5},
    "Malaysia":   {"carbon_pricing": 1.0, "climate_disclosure": 2.5, "taxonomy": 1.5, "stewardship": 1.0},
    "Indonesia":  {"carbon_pricing": 1.5, "climate_disclosure": 2.0, "taxonomy": 1.5, "stewardship": 0.5},
    "Thailand":   {"carbon_pricing": 1.0, "climate_disclosure": 2.0, "taxonomy": 1.5, "stewardship": 1.0},
    "Vietnam":    {"carbon_pricing": 1.0, "climate_disclosure": 1.0, "taxonomy": 0.5, "stewardship": 0.5},
}

CITATIONS = {
    "Singapore": [
        "Carbon Pricing Act 2018: carbon tax operational since 2019 (S$5/tCO2e), rising to "
        "S$25 (2024-25), S$45 (2026-27), and S$50-80 by 2030 (NEA / Ministry of Sustainability).",
        "SGX-ST Listing Rules: climate reporting on ISSB (IFRS S2) basis mandatory for all issuers "
        "from FY2025, phased (SGX RegCo, 2023-2024).",
        "Singapore-Asia Taxonomy for Sustainable Finance (MAS, Dec 2023); ASEAN Taxonomy adoption.",
        "Singapore Stewardship Principles for Responsible Investors (2016, comply-or-explain).",
    ],
    "Malaysia": [
        "Carbon tax announced in Budget 2025 for introduction in 2026 (iron/steel, energy) — not yet "
        "operational; voluntary Bursa Carbon Exchange live 2022.",
        "Bursa Malaysia enhanced Sustainability Reporting Framework; National Sustainability "
        "Reporting Framework adopting ISSB, phased mandatory from FY2025-2027 (SC Malaysia, 2024).",
        "BNM Climate Change and Principle-based Taxonomy (CCPT, 2021); SC SRI-linked taxonomy.",
        "Malaysian Code for Institutional Investors (2014, Securities Commission / MSWG).",
    ],
    "Indonesia": [
        "Carbon tax legislated under Law No. 7/2021 (HPP) but implementation repeatedly delayed; "
        "IDXCarbon exchange operational since Sept 2023.",
        "OJK Regulation POJK 51/2017: sustainability reports mandatory for issuers & financial "
        "institutions; ISSB adoption roadmap in progress.",
        "Indonesia Taxonomy for Sustainable Finance (2024, updating the 2022 Green Taxonomy).",
        "Limited formal stewardship code; OJK governance roadmap.",
    ],
    "Thailand": [
        "Carbon tax proposed via the Excise Department (2025) and a draft Climate Change Act — not "
        "yet operational; T-VER voluntary crediting scheme (TGO).",
        "SEC Thailand 56-1 One Report: ESG disclosure mandatory for listed firms since 2022.",
        "Thailand Taxonomy Phase 1 (2023, energy & transport; BOT/SEC/TGO).",
        "Investment Governance Code for institutional investors (I-Code, 2017).",
    ],
    "Vietnam": [
        "Domestic ETS pilot scheduled 2025-2028 under Decree 06/2022/ND-CP — not yet operational; "
        "no carbon tax.",
        "Listed-company sustainability disclosure nascent (Circular 96/2020/TT-BTC); ISSB adoption "
        "not yet mandated.",
        "National green taxonomy under development (MONRE, draft).",
        "Limited institutional-investor stewardship framework.",
    ],
}


def build() -> pd.DataFrame:
    rows = []
    for country, comp in SCORES.items():
        idx = round(sum(comp.values()), 2)        # 0–10
        rows.append({"country": country, **comp, "reg_momentum_index": idx})
    df = pd.DataFrame(rows).sort_values("reg_momentum_index", ascending=False).reset_index(drop=True)
    # min–max scaled 0–1 helper for downstream interaction terms
    lo, hi = df["reg_momentum_index"].min(), df["reg_momentum_index"].max()
    df["reg_momentum_scaled"] = (df["reg_momentum_index"] - lo) / (hi - lo) if hi > lo else 0.0
    df.to_parquet(INTERIM / "country_regulatory.parquet", index=False)
    (INTERIM / "country_regulatory_citations.json").write_text(
        json.dumps(CITATIONS, indent=2), encoding="utf-8")
    log_action("phase2", "country_regulatory_built", {},
               {"countries": df["country"].tolist(),
                "index": dict(zip(df["country"], df["reg_momentum_index"]))})
    return df


if __name__ == "__main__":
    df = build()
    print("Country ESG-regulatory momentum index (0-10):")
    print(df.to_string(index=False))
