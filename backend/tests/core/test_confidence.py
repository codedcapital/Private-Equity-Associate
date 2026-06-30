import pytest

from core.confidence import ConfidenceScorer


# ─────────────────────────────────────────────────────────────────────────────
# score_financials
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "financials,expected",
    [
        (
            {
                "revenue": 100.0,
                "ebitda": 20.0,
                "net_debt": 50.0,
                "fcf": 15.0,
                "ebitda_margin": 0.20,
                "revenue_growth": 0.05,
            },
            1.0,
        ),
        (
            {
                "revenue": 100.0,
                "ebitda": 20.0,
                "net_debt": None,
                "fcf": None,
                "ebitda_margin": None,
                "revenue_growth": 0.05,
            },
            0.5,
        ),
        (
            {
                "revenue": 100.0,
                "ebitda": None,
                "net_debt": None,
                "fcf": None,
                "ebitda_margin": None,
                "revenue_growth": None,
            },
            1 / 6,
        ),
        ({}, 0.0),
        (None, 0.0),
    ],
)
def test_score_financials(financials, expected):
    assert ConfidenceScorer.score_financials(financials) == pytest.approx(expected)


# ─────────────────────────────────────────────────────────────────────────────
# score_competitive
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "competitors,sources,expected_min,expected_max",
    [
        # 100% structured → high score
        (
            [
                {"source": "crunchbase"},
                {"source": "pitchbook"},
                {"source": "crunchbase"},
            ],
            ["crunchbase", "pitchbook"],
            0.85,
            1.0,
        ),
        # 50% structured → mid score
        (
            [
                {"source": "crunchbase"},
                {"source": "web"},
            ],
            ["crunchbase", "pitchbook"],
            0.5,
            0.85,
        ),
        # 0% structured → low score
        (
            [
                {"source": "web"},
                {"source": "news"},
            ],
            ["crunchbase", "pitchbook"],
            0.0,
            0.5,
        ),
        # Empty lists
        ([], ["crunchbase"], 0.0, 0.0),
        ([{"source": "web"}], [], 0.0, 0.0),
    ],
)
def test_score_competitive(competitors, sources, expected_min, expected_max):
    score = ConfidenceScorer.score_competitive(competitors, sources)
    assert expected_min <= score <= expected_max


# ─────────────────────────────────────────────────────────────────────────────
# score_research
# ─────────────────────────────────────────────────────────────────────────────


def test_score_research_with_full_citations():
    research = {
        "market_size": ["source1"],
        "growth_drivers": ["source2"],
        "key_players": ["source3"],
    }
    assert ConfidenceScorer.score_research(research) == pytest.approx(1.0)


def test_score_research_with_partial_citations():
    research = {
        "market_size": ["source1"],
        "growth_drivers": "",
        "key_players": [],
    }
    assert ConfidenceScorer.score_research(research) == pytest.approx(1 / 3)


def test_score_research_empty():
    assert ConfidenceScorer.score_research({}) == 0.0
    assert ConfidenceScorer.score_research(None) == 0.0


# ─────────────────────────────────────────────────────────────────────────────
# score_lbo
# ─────────────────────────────────────────────────────────────────────────────


def test_score_lbo_complete():
    lbo = {
        "entry_equity": 100.0,
        "entry_debt": 200.0,
        "irr": 0.25,
        "moic": 2.5,
        "lbo_scenarios": {"base": {}, "upside": {}},
        "lbo_sensitivity": {"ev_ebitda": {}},
    }
    score = ConfidenceScorer.score_lbo(lbo)
    assert score == pytest.approx(1.0)


def test_score_lbo_partial():
    lbo = {
        "entry_equity": 100.0,
        "entry_debt": 200.0,
        "irr": None,
        "moic": None,
        "lbo_scenarios": {"base": {}},
        "lbo_sensitivity": {},
    }
    score = ConfidenceScorer.score_lbo(lbo)
    # scenarios = 0.5, sensitivity = 0, base_keys = 2/4 = 0.1 → total 0.6
    assert score == pytest.approx(0.6)


def test_score_lbo_empty():
    assert ConfidenceScorer.score_lbo({}) == 0.0
    assert ConfidenceScorer.score_lbo(None) == 0.0
