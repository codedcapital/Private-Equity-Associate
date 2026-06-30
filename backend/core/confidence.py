"""Confidence scoring for agent outputs.

Scores agent results on a 0–1 scale based on data quality, source
reliability, and output completeness.
"""


class ConfidenceScorer:
    """Score agent output confidence based on data quality."""

    # Critical financial fields that must be present for a high score
    _FINANCIAL_CRITICAL_FIELDS = [
        "revenue",
        "ebitda",
        "net_debt",
        "fcf",
        "ebitda_margin",
        "revenue_growth",
    ]

    @staticmethod
    def score_financials(financials: dict) -> float:
        """Score 0–1 based on completeness of financial data.

        Counts how many of the six critical fields are not None.
        If all present: 1.0, if half: 0.5, etc.

        Args:
            financials: A dictionary of financial metrics.

        Returns:
            A float between 0.0 and 1.0.
        """
        if not financials:
            return 0.0

        total = len(ConfidenceScorer._FINANCIAL_CRITICAL_FIELDS)
        present = sum(
            1
            for field in ConfidenceScorer._FINANCIAL_CRITICAL_FIELDS
            if financials.get(field) is not None
        )
        return present / total

    @staticmethod
    def score_competitive(competitors: list, sources: list) -> float:
        """Score 0–1 based on percentage of competitors from structured DB.

        Args:
            competitors: A list of competitor dicts, each with a ``source`` key.
            sources: A list of structured DB names (e.g.
                ``["wikidata", "gleif", "explorium"]``).

        Returns:
            A float between 0.0 and 1.0.
        """
        if not competitors or not sources:
            return 0.0

        structured_set = {s.lower() for s in sources}
        structured_count = sum(
            1
            for c in competitors
            if c.get("source", "").lower() in structured_set
        )
        ratio = structured_count / len(competitors)

        if ratio >= 0.7:
            # 70%+ from structured DB → 0.85–1.0
            return 0.85 + (ratio - 0.7) / (1.0 - 0.7) * 0.15
        elif ratio >= 0.3:
            # 30–70% from structured → 0.5–0.85
            return 0.5 + (ratio - 0.3) / (0.7 - 0.3) * 0.35
        else:
            # <30% from structured → 0.0–0.5
            return ratio / 0.3 * 0.5

    @staticmethod
    def score_research(research: dict) -> float:
        """Score 0–1 based on source citations and data freshness.

        Counts fields that have at least one citation (non-empty list or string).

        Args:
            research: A dictionary of research findings.

        Returns:
            A float between 0.0 and 1.0.
        """
        if not research:
            return 0.0

        total_fields = len(research)
        if total_fields == 0:
            return 0.0

        cited_count = 0
        for value in research.values():
            if isinstance(value, list) and len(value) > 0:
                cited_count += 1
            elif isinstance(value, str) and value.strip():
                cited_count += 1
            elif isinstance(value, dict) and value.get("citations"):
                cited_count += 1

        return cited_count / total_fields

    @staticmethod
    def score_lbo(lbo_result: dict) -> float:
        """Score 0–1 based on assumption quality and output completeness.

        Checks for the presence of scenario results and sensitivity grid.

        Args:
            lbo_result: A dictionary containing LBO model outputs.

        Returns:
            A float between 0.0 and 1.0.
        """
        if not lbo_result:
            return 0.0

        score = 0.0
        checks = 0

        # Check if scenarios have results
        scenarios = lbo_result.get("lbo_scenarios") or lbo_result.get("scenarios")
        if scenarios and isinstance(scenarios, dict) and len(scenarios) > 0:
            score += 0.5
        checks += 1

        # Check if sensitivity grid exists
        sensitivity = lbo_result.get("lbo_sensitivity") or lbo_result.get("sensitivity")
        if sensitivity and isinstance(sensitivity, dict) and len(sensitivity) > 0:
            score += 0.3
        checks += 1

        # Check for base case result (entry_equity, irr, moic)
        base_keys = ["entry_equity", "entry_debt", "irr", "moic"]
        present = sum(1 for k in base_keys if lbo_result.get(k) is not None)
        if present == len(base_keys):
            score += 0.2
        elif present >= len(base_keys) // 2:
            score += 0.1
        checks += 1

        return min(score, 1.0)
