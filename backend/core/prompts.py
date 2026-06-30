# Financial analysis
PROMPT_FINANCIAL_INTERPRET = """You are a senior PE associate at Apollo. Analyze the following financial profile and produce a 3-paragraph narrative:
1. Revenue quality and growth trajectory
2. Profitability and margin trends
3. Cash flow and balance sheet health
Be specific, cite numbers, and flag any red flags."""

# LBO interpretation
PROMPT_LBO_INTERPRET = """You are analyzing an LBO model. Given the entry assumptions, debt schedule, and exit returns, write a 2-paragraph analysis covering:
1. Key value creation levers
2. What could kill this deal (risks, downside scenarios)
Be quantitative and specific."""

# Industry research
PROMPT_INDUSTRY_RESEARCH = """You are a PE industry analyst. Research the following sector and produce a structured analysis with:
- TAM and CAGR
- Growth drivers (3-5 bullet points)
- Key risks (3-5 bullet points)
- Regulatory notes (1 paragraph)
- Key players (5-8 companies)
Cite sources where possible."""

# Competitive positioning
PROMPT_COMPETITIVE_MOAT = """You are a competitive strategy analyst. Assess the target company's differentiation based on:
- Switching costs
- Network effects
- IP / proprietary technology
- Distribution advantages
- Brand / reputation
For each, rate 1-5 and explain. Cite specific competitors by name."""

# Memo sections (8 sections)
PROMPT_MEMO_EXECUTIVE_SUMMARY = """Write an executive summary for an IC memo. 1 page, max 400 words. Cover: investment thesis, key metrics, and recommendation."""
PROMPT_MEMO_COMPANY_OVERVIEW = """Write a company overview section. 1 page. Cover: business model, history, leadership, key products."""
PROMPT_MEMO_INDUSTRY_ANALYSIS = """Write an industry analysis section. 1-2 pages. Use the industry research context."""
PROMPT_MEMO_COMPETITIVE_POSITIONING = """Write a competitive positioning section. 1 page. Use the competitive matrix and moat assessment."""
PROMPT_MEMO_FINANCIAL_ANALYSIS = """Write a financial analysis section. 1-2 pages. Use the financial profile and computed ratios."""
PROMPT_MEMO_LBO_MODEL = """Write an LBO model & returns section. 1-2 pages. Include base/bull/bear scenarios and sensitivity commentary."""
PROMPT_MEMO_RISK_FACTORS = """Write a risk factors section. 1 page. Cover: market, operational, financial, regulatory risks."""
PROMPT_MEMO_RECOMMENDATION = """Write an investment recommendation section. 1 page. State recommendation (proceed / pass), key conditions, and next steps."""
