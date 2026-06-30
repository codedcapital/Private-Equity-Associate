"""Memo agent package — IC memo generation and PDF export."""

from agents.memo.graph import memo_graph, run_memo_generation
from agents.memo.pdf_renderer import render_memo_pdf
from agents.memo.prompts import (
    PROMPT_MEMO_COMPANY_OVERVIEW,
    PROMPT_MEMO_COMPETITIVE_POSITIONING,
    PROMPT_MEMO_EXECUTIVE_SUMMARY,
    PROMPT_MEMO_FINANCIAL_ANALYSIS,
    PROMPT_MEMO_INDUSTRY_ANALYSIS,
    PROMPT_MEMO_INVESTMENT_RECOMMENDATION,
    PROMPT_MEMO_LBO_MODEL,
    PROMPT_MEMO_RISK_FACTORS,
)

__all__ = [
    "memo_graph",
    "run_memo_generation",
    "render_memo_pdf",
    "PROMPT_MEMO_EXECUTIVE_SUMMARY",
    "PROMPT_MEMO_COMPANY_OVERVIEW",
    "PROMPT_MEMO_INDUSTRY_ANALYSIS",
    "PROMPT_MEMO_COMPETITIVE_POSITIONING",
    "PROMPT_MEMO_FINANCIAL_ANALYSIS",
    "PROMPT_MEMO_LBO_MODEL",
    "PROMPT_MEMO_RISK_FACTORS",
    "PROMPT_MEMO_INVESTMENT_RECOMMENDATION",
]
