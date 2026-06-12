from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_SOURCE = PROJECT_ROOT / "site" / "src" / "App.tsx"
CSS_SOURCE = PROJECT_ROOT / "site" / "src" / "styles.css"


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


def test_synthetic_and_not_investment_advice_labels_are_present():
    source = APP_SOURCE.read_text(encoding="utf-8")
    assert "SYNTHETIC DEMONSTRATION DATA" in source
    assert "Research demonstration - not investment advice." in source

