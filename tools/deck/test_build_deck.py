from __future__ import annotations

from pptx import Presentation

from tools.deck.build_deck import DEFAULT_CONTENT, build_deck, load_deck_content, missing_figures


def test_sample_yaml_has_no_missing_figures():
    assert missing_figures(DEFAULT_CONTENT) == []


def test_sample_yaml_generates_expected_slide_count(tmp_path):
    output = tmp_path / "ESG_Momentum_Engine.pptx"
    build_deck(DEFAULT_CONTENT, output)

    content = load_deck_content(DEFAULT_CONTENT)
    deck = Presentation(output)

    assert output.exists()
    assert len(deck.slides) == len(content["slides"]) == 7
