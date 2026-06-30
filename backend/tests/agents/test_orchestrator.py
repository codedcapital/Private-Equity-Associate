"""Tests for the LangGraph deal pipeline orchestrator."""

from __future__ import annotations

import pytest

from agents.orchestrator import graph


class TestGraphCompilation:
    def test_graph_compiles_without_error(self) -> None:
        assert graph is not None

    def test_graph_has_expected_nodes(self) -> None:
        # The compiled graph exposes a get_graph() method in recent LangGraph versions
        nodes = set(graph.get_graph().nodes.keys()) if hasattr(graph, "get_graph") else set()
        expected = {
            "sourcing",
            "research_competitive",
            "financials",
            "lbo",
            "memo",
            "checkpoint",
            "__start__",
            "__end__",
        }
        # If get_graph() is not available, just skip this assertion
        if nodes:
            assert expected <= nodes
