from __future__ import annotations

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_SOURCE = PROJECT_ROOT / "site" / "src" / "App.tsx"
CSS_SOURCE = PROJECT_ROOT / "site" / "src" / "styles.css"
SITE_CONTENT = PROJECT_ROOT / "site" / "src" / "site_content.json"


def test_leaderboard_source_uses_virtualized_rows_and_keyboard_open():
    source = APP_SOURCE.read_text(encoding="utf-8")
    assert "function VirtualTable" in source
    assert "rows.slice(start, end)" in source
    assert "onScroll" in source
    assert 'e.key === "Enter"' in source
    assert "tabIndex={0}" in source


def test_leaderboard_has_desktop_tablet_mobile_responsive_rules():
    css = CSS_SOURCE.read_text(encoding="utf-8")
    assert ".thead, .row" in css
    assert "grid-template-columns: 70px minmax(220px, 1.4fr)" in css
    assert "@media (max-width: 900px)" in css
    assert "grid-template-columns: 44px minmax(0, 1fr) 64px" in css
    assert ".virtual { height: 620px !important; }" in css
    assert ":focus-visible" in css


def test_synthetic_and_not_investment_advice_labels_are_present():
    source = APP_SOURCE.read_text(encoding="utf-8")
    content = SITE_CONTENT.read_text(encoding="utf-8")
    assert "SYNTHETIC DEMONSTRATION DATA" in source
    assert "Research demonstration - not investment advice." in content
    assert "siteContent.footer.disclaimer" in source


def test_frontend_copy_is_loaded_from_site_content_file():
    source = APP_SOURCE.read_text(encoding="utf-8")
    content = json.loads(SITE_CONTENT.read_text(encoding="utf-8"))
    assert 'import siteContent from "./site_content.json"' in source
    assert content["hero"]["title"]
    assert content["methodology"]["explainer"]
    assert content["results"]["metrics"]["deflatedSharpe"]
    assert content["risks"]["cards"]


def test_company_detail_exposes_schema_safe_risk_index():
    source = APP_SOURCE.read_text(encoding="utf-8")
    assert "function derivedRiskIndex" in source
    assert "100 - company.coverage_pct" in source
    assert "RISK_FLAG_WEIGHTS" in source
    assert "Risk index" in source
    assert "not stored in the source schema" in source


def test_company_detail_labels_esg_and_non_esg_components():
    source = APP_SOURCE.read_text(encoding="utf-8")
    assert "E component: Transition Readiness" in source
    assert "S component: Sentiment Dynamics" in source
    assert "G component: Governance Credibility" in source
    assert "Non-ESG component: Disclosure Behavior" in source
