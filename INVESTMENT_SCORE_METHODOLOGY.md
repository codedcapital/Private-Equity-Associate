# Investment Score Methodology

**Version:** 1.0.0  
**Last Updated:** 2026-07-01  
**Owner:** PE Associate Platform  
**Review Cycle:** Monthly (or on data model change)  

---

## 1. Purpose

The Investment Score is a **normalized, 0-100 composite metric** that answers a single question for a PE associate:

> *"At this exact moment, how attractive is this deal relative to the other 50 deals in the pipeline?"*

It is not a valuation. It is not a recommendation to buy or sell. It is a **priority signal** — a weighted synthesis of quantitative data, qualitative intelligence, and market context that helps the team decide where to spend the next hour of diligence time.

### 1.1 Core Principles

| Principle | Rule |
|-----------|------|
| **Transparency** | Every component score must be explainable in one sentence. No black-box LLM synthesis without traceable inputs. |
| **Stability** | Scores do not jitter. A single news headline does not move a score more than 3 points unless it is a structural event. |
| **Versioned** | The scoring model is versioned (v1.0, v1.1). Old scores are preserved so "83 → 87" is historically auditable. |
| **Overrideable** | The system computes the score; a human associate can override it. The override is logged, not hidden. |
| **Confidence-Gated** | If data is sparse, the score is suppressed (not fabricated). A score with Low Confidence is shown as "N/A — insufficient data." |

---

## 2. Score Architecture

The Investment Score is composed of **four weighted dimensions**:

```
Score = (Financials × 0.30) + (Competitive Moat × 0.25) + (Market Context × 0.25) + (Risk Profile × 0.20)
```

Each dimension is scored **0-100** independently. The final composite is a weighted average.

```
┌──────────────────────────────────────────────────────────┐
│                    Investment Score                       │
│                    0 — 100 Composite                      │
│                                                           │
│  ┌──────────────────────────────────────────────────┐    │
│  │ Financials (30%)                                  │    │
│  │ Revenue Growth · Margin Quality · Cash Conv.      │    │
│  │ 0 — 100                                           │    │
│  └──────────────────────────────────────────────────┘    │
│  ┌──────────────────────────────────────────────────┐    │
│  │ Competitive Moat (25%)                            │    │
│  │ Switching Costs · Market Position · Network Eff.  │    │
│  │ 0 — 100                                           │    │
│  └──────────────────────────────────────────────────┘    │
│  ┌──────────────────────────────────────────────────┐    │
│  │ Market Context (25%)                              │    │
│  │ Sector Multiples · Macro Tailwinds · M&A Heat    │    │
│  │ 0 — 100                                           │    │
│  └──────────────────────────────────────────────────┘    │
│  ┌──────────────────────────────────────────────────┐    │
│  │ Risk Profile (20%)                                │    │
│  │ Customer Conc. · Leverage · Legal · Governance    │    │
│  │ 0 — 100                                           │    │
│  └──────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────┘
```

---

## 3. Dimension Scoring Methodology

### 3.1 Financials (30%)

**Purpose:** Measures the company's current operating performance and trajectory.

**Sub-Components:**

| Sub-Component | Weight | Data Source | Description |
|---------------|--------|-------------|-------------|
| Revenue Growth | 25% | 10-K / YFinance | YoY revenue growth. Recurring revenue weighted 2x vs. one-time. |
| Margin Quality | 25% | 10-K / YFinance | EBITDA margin + FCF margin. Bonus for expanding margins. |
| Cash Conversion | 25% | 10-K / YFinance | FCF / EBITDA ratio. Measures earnings quality. |
| Capital Efficiency | 25% | 10-K / YFinance | ROIC and capital intensity. Higher is better. |

**Scoring Logic:**

Each sub-component is scored on a **sector-relative percentile basis** (or absolute benchmark if the company has no clear peers in the pipeline).

```python
def score_revenue_growth(growth_pct, sector):
    if growth_pct > 30:         return 100  # Exceptional
    if growth_pct > 20:         return 85   # Strong
    if growth_pct > 10:         return 70   # Healthy
    if growth_pct > 5:          return 50   # Moderate
    if growth_pct > 0:          return 30   # Slow
    if growth_pct > -10:        return 15   # Declining
    return 0                     # Distressed
```

**Margin Quality** uses absolute thresholds (less sector-dependent):

```python
def score_margin_quality(ebitda_margin, fcf_margin):
    base = (ebitda_margin * 0.6) + (fcf_margin * 0.4)
    if base > 35:   return 100
    if base > 25:   return 85
    if base > 15:   return 70
    if base > 10:   return 50
    if base > 5:    return 30
    return 15
```

**Cash Conversion:**

```python
def score_cash_conversion(fcf_ebitda_ratio):
    if ratio > 0.80:   return 100  # Convert almost all EBITDA to cash
    if ratio > 0.60:   return 85
    if ratio > 0.40:   return 70
    if ratio > 0.20:   return 50
    if ratio > 0:      return 30
    return 0
```

**Capital Efficiency:**

```python
def score_capital_efficiency(roic, capex_revenue_ratio):
    # Higher ROIC is good; lower capex intensity is good
    roic_score = min(100, max(0, roic * 5))  # 20% ROIC = 100
    capex_score = max(0, 100 - (capex_revenue_ratio * 20))  # 5% cap/rev = 0
    return (roic_score * 0.7) + (capex_score * 0.3)
```

**Financials Dimension Score:**

```python
financials_score = (
    score_revenue_growth * 0.25 +
    score_margin_quality * 0.25 +
    score_cash_conversion * 0.25 +
    score_capital_efficiency * 0.25
)
```

**Data Requirements for Financials:**
- Minimum 2 fiscal years of data (or 4 quarters for recent IPOs)
- If <2 years: Financials dimension = "N/A (insufficient data)" → composite score suppressed
- All data sourced from SEC filings or YFinance, never extrapolated by LLM

---

### 3.2 Competitive Moat (25%)

**Purpose:** Measures the durability of the company's competitive position.

**Sub-Components:**

| Sub-Component | Weight | Data Source | Description |
|---------------|--------|-------------|-------------|
| Market Position | 30% | Competitive agent / 10-K | Market share, rank in top 3, customer concentration |
| Switching Costs | 25% | Research agent / 10-K | Integration depth, contract terms, data lock-in |
| Network Effects | 20% | Research agent / 10-K | Platform dynamics, marketplace effects, ecosystem |
| Differentiation | 25% | Competitive agent / Research | Product uniqueness, pricing power, brand strength |

**Scoring Logic:**

The Competitive Moat dimension is **partially quantitative, partially qualitative**. The quantitative pieces are hard rules. The qualitative pieces use structured LLM extraction with evidence anchoring.

**Market Position (30%):**

```python
def score_market_position(market_share, is_top_3, customer_concentration):
    if not is_top_3:
        return max(30, market_share * 1.5)  # Capped at 45 if not top 3
    
    base = min(100, market_share * 3)  # 33% share = 100
    
    # Customer concentration penalty: >50% revenue from 1 customer = -20 pts
    if customer_concentration > 0.5:
        base -= 20
    elif customer_concentration > 0.3:
        base -= 10
    
    return max(0, base)
```

**Switching Costs, Network Effects, Differentiation (70% combined):**

These are scored via **structured LLM extraction** from the Competitive Agent and Research Agent outputs. The LLM does not assign a score directly. It extracts evidence, which is then scored by deterministic rules.

Example for Switching Costs:

```python
switching_cost_signals = {
    "multi_year_contracts": 15,
    "deep_integration": 15,
    "data_migration_difficulty": 15,
    "training_required": 10,
    "regulatory_compliance_tied": 15,
    "custom_workflows": 10,
    "no_free_alternative": 10
}
# Score = sum of present signals, capped at 100
```

**Network Effects:**

```python
network_effect_signals = {
    "platform_with_two_sided_market": 20,
    "data_flywheel_described": 20,
    "ecosystem_of_partners": 15,
    "increasing_returns_to_scale": 15,
    "community_or_user_generated_content": 15,
    "api_ecosystem": 15
}
```

**Differentiation:**

```python
differentiation_signals = {
    "proprietary_technology_patents": 20,
    "pricing_power_evidence": 20,
    "brand_recognition_mentioned": 15,
    "product_uniqueness_vs_peers": 15,
    "customer_loyalty_metrics": 15,
    "regulatory_moat": 15
}
```

**Critical Rule:** Each signal must be **anchored to an explicit evidence string** from the agent output (e.g., a direct quote from a 10-K or earnings call). A signal without evidence is not counted. This prevents hallucination.

**Competitive Moat Score:**

```python
moat_score = (
    score_market_position * 0.30 +
    score_switching_costs * 0.25 +
    score_network_effects * 0.20 +
    score_differentiation * 0.25
)
```

---

### 3.3 Market Context (25%)

**Purpose:** Measures whether the external environment is favorable for this deal.

**Sub-Components:**

| Sub-Component | Weight | Data Source | Description |
|---------------|--------|-------------|-------------|
| Sector Multiples | 35% | Pipeline median / Manual | Where the sector trades vs. 12 months ago |
| Macro Tailwinds | 30% | Interest rates / Fed outlook | Rate environment, inflation, credit availability |
| M&A Heat | 20% | News / SEC filings | Recent deals in sector, sponsor activity |
| Regulatory Environment | 15% | News / Research | Antitrust risk, sector-specific regulation |

**Scoring Logic:**

**Sector Multiples (35%):**

```python
def score_sector_multiples(company_ev_revenue, sector_median_ev_revenue, trend_12m):
    # If the company trades below sector median, entry is more attractive
    discount = (sector_median - company_ev_revenue) / sector_median
    
    if discount > 0.3:     base = 100  # Deep discount
    elif discount > 0.1:  base = 85
    elif discount > -0.1: base = 70   # Near median
    elif discount > -0.3: base = 50   # Premium
    else:                  base = 30   # Expensive
    
    # Trend adjustment: if multiples are expanding, add points
    if trend_12m > 0.2:    base += 15
    elif trend_12m > 0:    base += 5
    elif trend_12m < -0.2:  base -= 15
    
    return max(0, min(100, base))
```

**Macro Tailwinds (30%):**

```python
def score_macro_tailwinds(fed_rate, rate_12m_ago, credit_spread, inflation_yoy):
    score = 50  # Neutral baseline
    
    # Rate direction matters more than absolute level
    if fed_rate < rate_12m_ago:
        score += 20  # Rate cuts = favorable for LBOs
    elif fed_rate > rate_12m_ago + 0.5:
        score -= 15  # Rapid hikes = unfavorable
    
    # Credit spread: tight = good for financing
    if credit_spread < 200:  score += 10
    elif credit_spread > 400: score -= 15
    
    # Inflation: moderate is fine, high is bad
    if inflation_yoy > 4:   score -= 10
    elif inflation_yoy < 2: score += 5
    
    return max(0, min(100, score))
```

**M&A Heat (20%):**

```python
def score_ma_heat(sector_deals_last_12m, sector_deal_value_usd_billions):
    if sector_deals_last_12m > 20:         return 100  # Very active
    if sector_deals_last_12m > 10:         return 85
    if sector_deals_last_12m > 5:          return 70
    if sector_deals_last_12m > 2:          return 50
    if sector_deals_last_12m > 0:         return 30
    return 15
```

**Regulatory Environment (15%):**

```python
def score_regulatory_environment(antitrust_risk_flag, sector_regulation_score):
    # sector_regulation_score: 0 = highly regulated (healthcare), 100 = lightly regulated (SaaS)
    # antitrust_risk_flag: True if the company is large enough to trigger FTC review
    
    base = sector_regulation_score
    if antitrust_risk_flag:
        base -= 25
    return max(0, base)
```

**Market Context Score:**

```python
market_score = (
    score_sector_multiples * 0.35 +
    score_macro_tailwinds * 0.30 +
    score_ma_heat * 0.20 +
    score_regulatory * 0.15
)
```

**Important Caveat:** The Market Context score is **shared across all deals in the same sector**. It does not vary company-to-company within a sector (except for the sector multiples discount). This is intentional — it measures the environment, not the asset.

---

### 3.4 Risk Profile (20%)

**Purpose:** Measures downside exposure and red flags.

**Sub-Components:**

| Sub-Component | Weight | Data Source | Description |
|---------------|--------|-------------|-------------|
| Customer Concentration | 25% | 10-K / Agent | Revenue dependency on top 1/3/5 customers |
| Leverage & Liquidity | 25% | 10-K / YFinance | Net Debt/EBITDA, interest coverage, cash runway |
| Legal & Litigation | 20% | SEC / News | Lawsuits, regulatory actions, IP disputes |
| Governance & Key Person | 20% | SEC / Research | CEO changes, board issues, insider selling |
| Operational Risk | 10% | Research / News | Cyber incidents, supply chain, geo exposure |

**Scoring Logic:**

Risk Profile is **inverted**: higher risk = lower score. A company with zero red flags scores 100.

**Customer Concentration (25%):**

```python
def score_customer_concentration(top1_pct, top3_pct, top5_pct):
    # Penalty is the dominant factor
    penalty = 0
    if top1_pct > 0.50:   penalty += 40
    elif top1_pct > 0.30: penalty += 25
    elif top1_pct > 0.15: penalty += 10
    
    if top3_pct > 0.70:   penalty += 20
    elif top3_pct > 0.50: penalty += 10
    
    if top5_pct > 0.80:   penalty += 10
    
    return max(0, 100 - penalty)
```

**Leverage & Liquidity (25%):**

```python
def score_leverage(net_debt_ebitda, interest_coverage, cash_runway_months):
    penalty = 0
    if net_debt_ebitda > 6:     penalty += 35
    elif net_debt_ebitda > 4:   penalty += 25
    elif net_debt_ebitda > 3:   penalty += 15
    elif net_debt_ebitda > 2:   penalty += 5
    
    if interest_coverage < 2:    penalty += 25
    elif interest_coverage < 3:  penalty += 15
    elif interest_coverage < 5:  penalty += 5
    
    if cash_runway_months < 12:  penalty += 15
    elif cash_runway_months < 6: penalty += 25
    
    return max(0, 100 - penalty)
```

**Legal & Litigation (20%):**

```python
def score_legal(lawsuits_active, material_regulatory_actions, ip_disputes):
    penalty = 0
    if lawsuits_active > 2:        penalty += 25
    elif lawsuits_active > 0:      penalty += 10
    
    if material_regulatory_actions: penalty += 20
    if ip_disputes:                 penalty += 15
    
    return max(0, 100 - penalty)
```

**Governance & Key Person (20%):**

```python
def score_governance(ceo_tenure_years, ceo_change_last_24m, insider_selling_pct, board_independence_pct):
    penalty = 0
    if ceo_change_last_24m:        penalty += 30
    elif ceo_tenure_years < 2:     penalty += 15
    
    if insider_selling_pct > 0.20:  penalty += 20
    elif insider_selling_pct > 0.10: penalty += 10
    
    if board_independence_pct < 0.5: penalty += 15
    
    return max(0, 100 - penalty)
```

**Operational Risk (10%):**

```python
def score_operational(cyber_incident_last_24m, supply_chain_concentration, geo_exposure_risk):
    penalty = 0
    if cyber_incident_last_24m:     penalty += 20
    if supply_chain_concentration > 0.5: penalty += 15
    if geo_exposure_risk == "high": penalty += 15
    elif geo_exposure_risk == "medium": penalty += 5
    
    return max(0, 100 - penalty)
```

**Risk Profile Score:**

```python
risk_score = (
    score_customer_concentration * 0.25 +
    score_leverage * 0.25 +
    score_legal * 0.20 +
    score_governance * 0.20 +
    score_operational * 0.10
)
```

---

## 4. Composite Score Calculation

```python
investment_score = round(
    financials_score * 0.30 +
    moat_score * 0.25 +
    market_score * 0.25 +
    risk_score * 0.20
)
```

**Rounding Rule:** Round to nearest integer. Never show decimals.

**Score Distribution Expectation:**

In a healthy pipeline, scores should be roughly normally distributed:
- **0-40:** Weak / Declining (auto-filtered from attention table)
- **40-60:** Marginal (shown only if there is a specific catalyst)
- **60-80:** Solid / Attractive (bulk of the pipeline)
- **80-95:** Strong / High Priority (gets attention table placement)
- **95-100:** Exceptional (rare, requires manual review)

---

## 5. Score Change Detection & Attribution

### 5.1 What Triggers a Score Recalculation?

A score is recomputed when **any** of the following events occur:

| Event | Data Source | Impact on Score |
|-------|-------------|-----------------|
| New 10-K or 10-Q filed | SEC EDGAR | Financials dimension recalculated |
| Earnings release | SEC / YFinance | Financials + Market Context |
| Insider trading report | SEC EDGAR | Risk Profile (Governance) |
| New 8-K (material event) | SEC EDGAR | Risk Profile or Competitive Moat |
| Agent run completion | Agent output | Competitive Moat or Risk Profile |
| Weekly macro update | Manual / API | Market Context (if rates/spreads change) |
| Manual override | User action | Score overridden, flagged as such |
| Pipeline sector update | Pipeline median | Market Context (if sector multiples change) |

### 5.2 Score Change Threshold

A score change is **not reported** unless it exceeds ±3 points. This prevents noise from minor data refreshes.

```python
def report_score_change(old_score, new_score):
    if abs(new_score - old_score) < 3:
        return None  # No dashboard notification
    return {
        "old_score": old_score,
        "new_score": new_score,
        "delta": new_score - old_score,
        "reason": determine_reason(old_score, new_score),  # See 5.3
        "timestamp": now()
    }
```

### 5.3 Change Attribution (The "Why")

When a score change is reported, the system must attribute it to a **primary cause**. This is computed by comparing the dimension scores before and after the event:

```python
def determine_reason(old_dimensions, new_dimensions, event_type):
    # Calculate change in each dimension
    diffs = {
        "financials": new_dimensions["financials"] - old_dimensions["financials"],
        "moat": new_dimensions["moat"] - old_dimensions["moat"],
        "market": new_dimensions["market"] - old_dimensions["market"],
        "risk": new_dimensions["risk"] - old_dimensions["risk"]
    }
    
    # The dimension with the largest absolute change is the primary driver
    primary_driver = max(diffs, key=lambda k: abs(diffs[k]))
    
    # Map to human-readable reason based on event_type
    reason_map = {
        ("financials", "earnings"): "Earnings released",
        ("financials", "filing"): "New financial filing",
        ("moat", "competitive"): "Competitive position updated",
        ("moat", "research"): "Research findings updated",
        ("market", "macro"): "Market multiples shifted",
        ("market", "sector"): "Sector activity increased",
        ("risk", "litigation"): "New legal filing detected",
        ("risk", "governance"): "Governance change detected",
        ("risk", "insider"): "Insider activity reported"
    }
    
    return reason_map.get((primary_driver, event_type), f"{primary_driver.title()} updated")
```

**Critical Note:** If the primary driver changed by <5 points, the reason is flagged as **"Minor data refresh"** and the score change is still reported but with a lower-confidence indicator (gray, not colored).

---

## 6. Confidence Levels

A score without confidence is dangerous. The system displays **four confidence tiers**:

| Tier | Requirements | Display Behavior |
|------|-------------|------------------|
| **High** | ≥3 years of data, all 4 dimensions have sufficient data, no agent errors in last run | Score shown in full color, bold |
| **Medium** | ≥2 years of data, 3/4 dimensions have data, one agent warning | Score shown normally, ⚠️ badge on hover |
| **Low** | ≥1 year of data, 2/4 dimensions have data, or multiple agent warnings | Score faded, "Low Confidence" badge, ⚠️ visible |
| **Insufficient** | <1 year of data, or >2 dimensions missing | Score suppressed, shows "N/A — insufficient data" |

### 6.1 Confidence Calculation

```python
def compute_confidence(deal, dimensions, agent_logs):
    dimension_coverage = sum(1 for d in dimensions.values() if d is not None) / 4
    
    # Data freshness: how old is the newest financial?
    newest_filing_age_days = (now() - deal.last_filing_date).days
    freshness_score = 1 if newest_filing_age_days < 45 else 0.7 if newest_filing_age_days < 90 else 0.4
    
    # Agent health: any errors in last run?
    last_run_errors = sum(1 for log in agent_logs if log.status == "error")
    agent_health = 1 if last_run_errors == 0 else 0.7 if last_run_errors <= 2 else 0.4
    
    confidence_index = (dimension_coverage * 0.5) + (freshness_score * 0.3) + (agent_health * 0.2)
    
    if confidence_index >= 0.85: return "HIGH"
    if confidence_index >= 0.65: return "MEDIUM"
    if confidence_index >= 0.45: return "LOW"
    return "INSUFFICIENT"
```

---

## 7. Attention Algorithm

Not all score changes deserve attention. A deal enters the **"Attention Required"** list when **any** of the following are true:

### 7.1 Hard Rules (Always Attention)

| Condition | Rationale |
|-----------|-----------|
| Stage = "IC Ready" | Associate needs to prepare materials |
| Score dropped > 10 points in 7 days | Structural deterioration |
| New 8-K filed with material adverse event | Requires immediate review |
| Outstanding questions > 5 and none resolved in 14 days | Stalled deal |
| Score > 85 but no associate has viewed deal in 7 days | High-priority deal being ignored |

### 7.2 Soft Rules (Attention if Score > 60)

| Condition | Rationale |
|-----------|-----------|
| Score changed by ±5 to ±10 points | Meaningful shift |
| New competitor entered market | Moat risk |
| Sector multiple compressed > 10% | Entry opportunity or warning |
| Insider selling > $5M | Governance signal |
| Earnings surprise (beat or miss) > 10% | Financials update |

### 7.3 Attention Deduplication

A deal cannot appear in the Attention list for the same reason twice within 7 days. If "New earnings released" caused attention on Monday, the same earnings filing does not re-trigger attention on Tuesday.

---

## 8. Human Override

### 8.1 Override Rules

Any associate can override a score. The override:
- Is logged with user_id, timestamp, and reason
- Is displayed with a "Manual Override" badge on the dashboard
- Does not delete the system score — it creates a parallel field `override_score`
- Can be removed by the same associate or an admin

### 8.2 Override Behavior

```python
if deal.override_score is not None:
    display_score = deal.override_score
    display_confidence = "OVERRIDE"
    show_badge = "Manual Override by J. Reyes on 2026-06-28"
else:
    display_score = deal.system_score
    display_confidence = compute_confidence(...)
```

### 8.3 When to Override

Overrides are appropriate when:
- The associate has non-public information (e.g., management meeting notes)
- The system is missing a qualitative factor (e.g., "CEO is a known value destroyer")
- The sector-relative scoring is inappropriate (e.g., a company transforming from hardware to SaaS)

Overrides are **not** appropriate for:
- Disagreeing with the score without a reason
- Gaming the attention algorithm
- Hiding a deal from the pipeline

---

## 9. Governance & Versioning

### 9.1 Versioning

The scoring methodology is versioned:

- **Major version (v1.0, v2.0):** Changes to dimension weights, new dimensions, or scoring logic
- **Minor version (v1.1, v1.2):** Threshold adjustments, new sub-components, bug fixes
- **Patch (v1.0.1):** Documentation updates, no scoring changes

When a new version is deployed:
- All existing scores are recomputed using the new version
- The old scores are preserved in `score_history` with the old version number
- The dashboard shows the current version in the footer
- A changelog is published internally

### 9.2 Review Cycle

| Review | Frequency | Owner | Output |
|--------|-----------|-------|--------|
| Data Quality | Weekly | Platform Team | Agent error report, stale data report |
| Score Accuracy | Monthly | Senior Associate | Backtest: did scores correlate with IC outcomes? |
| Methodology | Quarterly | Product + Senior Associate | Recommend threshold adjustments |
| Full Review | Annually | Product + Partners | Major version changes, new dimensions |

### 9.3 Backtesting

Every month, the team conducts a **score backtest**:

1. Take all deals that reached IC in the last 12 months
2. Compare their score at the time of IC to the actual IC decision (Proceed / Pass / Watch)
3. Measure: correlation, precision, recall
4. Target: >70% of "Proceed" decisions had scores >75; >80% of "Pass" decisions had scores <60

If the backtest fails, the methodology is reviewed.

---

## 10. Edge Cases & Special Handling

### 10.1 Recent IPOs / SPACs

- **Problem:** <2 years of data, limited filings, high volatility
- **Handling:** Financials dimension = "N/A". Moat and Risk dimensions scored from available data. Market dimension scored normally. Composite score is **suppressed** (Insufficient Confidence). Deal is tracked but not scored until 2+ years of data exist.

### 10.2 Distressed / Turnaround Situations

- **Problem:** Revenue declining, negative margins, but potential upside
- **Handling:** Financials dimension will score low (0-30). This is correct. The associate must rely on qualitative analysis (Research, Memo) and override the score if they believe the turnaround thesis is valid. The low score is a feature, not a bug — it forces explicit justification.

### 10.3 Platform / Multi-Business Companies

- **Problem:** Company has multiple segments with different profiles (e.g., SaaS + Hardware)
- **Handling:** Financials dimension is scored at the consolidated level. For Moat and Risk, the agent must identify the dominant segment (>50% of revenue) and score primarily on that segment, with a penalty for diversification complexity.

### 10.4 Private Companies (No Ticker)

- **Problem:** No SEC filings, no YFinance data
- **Handling:** All quantitative dimensions require manual data entry or third-party data (e.g., PitchBook). If no data is available, score = N/A. The platform is designed for public companies first; private company scoring is a Phase 2 feature.

### 10.5 Cross-Border Deals

- **Problem:** Different accounting standards, currency risk, geopolitical exposure
- **Handling:** Financials are standardized to USD using period-end FX rates. A "Cross-Border Penalty" of -5 to -15 points is applied to the Risk dimension based on:
  - Currency volatility (emerging market = -15, developed = -5)
  - Political risk index
  - Repatriation restrictions

---

## 11. Appendices

### Appendix A: Example Score Calculation — AppFolio (APPF)

**Data Snapshot:**
- Revenue Growth: 24% YoY
- EBITDA Margin: 22%
- FCF Margin: 18%
- FCF/EBITDA: 0.82
- ROIC: 16%
- Market Share: 12% (Top 3 in vertical SaaS for property management)
- Customer Concentration: 18% (top 1), 42% (top 5)
- Net Debt/EBITDA: 1.2x
- Interest Coverage: 8.5x
- Sector EV/Revenue: 8.2x (AppFolio trades at 6.8x)
- Fed Rate: 4.25% (down from 4.50% 6 months ago)
- No material litigation, no CEO change, no insider selling

**Dimension Scores:**

| Dimension | Sub-Component | Raw Score | Weighted |
|-----------|--------------|-----------|----------|
| **Financials** | Revenue Growth: 24% → 85 | 85 | 0.30 × 85 = 25.5 |
| | Margin Quality: 22% + 18% = 40% → 100 | 100 | |
| | Cash Conversion: 0.82 → 100 | 100 | |
| | Capital Efficiency: 16% ROIC → 80 | 80 | |
| | **Financials Dimension** | **91** | |
| **Moat** | Market Position: 12% share, top 3 → 75 | 75 | 0.25 × 75 = 18.75 |
| | Switching Costs: Multi-year contracts, deep integration → 70 | 70 | |
| | Network Effects: Platform + data flywheel → 55 | 55 | |
| | Differentiation: Proprietary tech, pricing power → 80 | 80 | |
| | **Moat Dimension** | **73** | |
| **Market** | Sector Multiples: 6.8x vs 8.2x median, discount = 17% → 85 | 85 | 0.25 × 85 = 21.25 |
| | Macro Tailwinds: Rate cuts, tight spreads → 85 | 85 | |
| | M&A Heat: 4 deals in sector last 12m → 50 | 50 | |
| | Regulatory: Lightly regulated, no antitrust risk → 90 | 90 | |
| | **Market Dimension** | **80** | |
| **Risk** | Customer Concentration: 18% top 1 → 90 | 90 | 0.20 × 90 = 18.0 |
| | Leverage: 1.2x net debt, 8.5x coverage → 95 | 95 | |
| | Legal: No material litigation → 100 | 100 | |
| | Governance: CEO tenure 8 years, no insider selling → 100 | 100 | |
| | Operational: No cyber incidents → 100 | 100 | |
| | **Risk Dimension** | **97** | |
| | | | |
| **Composite** | **91×0.30 + 73×0.25 + 80×0.25 + 97×0.20** | **85** | **85** |

**Confidence:** HIGH (3 years of data, all dimensions complete, no agent errors)

**Dashboard Display:**
- Score: **85** (High Confidence)
- Breakdown: Financials 91 · Moat 73 · Market 80 · Risk 97
- Attention Status: None (stable, no recent changes)

---

### Appendix B: Example Score Change — HubSpot (HUBS)

**Event:** Peer multiples compressed 15% following a competitor's miss.

**Before Event:**
- Market Dimension: 80 (trading at premium, but sector was hot)
- Score: 82

**After Event:**
- Sector EV/Revenue dropped from 10.2x to 8.7x
- HubSpot still trades at 9.5x (premium widened from 8% to 20%)
- Market Dimension: 50 (premium now excessive, or entry less attractive)
- Score: 75

**Change:** 82 → 75 (-7)

**Primary Driver:** Market Context (changed from 80 → 50, -30 points)

**Reason:** "Peer multiples compressed"

**Dashboard Display:**
- Company: HubSpot
- Score: 75 ▼ -7
- Stage: Screening
- Why: Peer multiples compressed
- Action: Watch (re-evaluate entry valuation)

---

### Appendix C: Score History Schema

```sql
CREATE TABLE score_history (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    deal_id         UUID NOT NULL REFERENCES deal_pipeline(id),
    score           INTEGER NOT NULL,
    financials      INTEGER,
    moat            INTEGER,
    market          INTEGER,
    risk            INTEGER,
    confidence      VARCHAR(20) NOT NULL,  -- HIGH, MEDIUM, LOW, INSUFFICIENT
    methodology_version VARCHAR(10) NOT NULL, -- e.g., "1.0.0"
    reason          TEXT,                    -- Human-readable change reason
    event_type      VARCHAR(50),             -- earnings, filing, macro, etc.
    overridden_by   UUID REFERENCES users(id),
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for fast dashboard queries
CREATE INDEX idx_score_history_deal_time ON score_history(deal_id, created_at DESC);
```

---

### Appendix D: Glossary

| Term | Definition |
|------|------------|
| **Investment Score** | 0-100 composite metric indicating deal attractiveness at a point in time |
| **Dimension** | One of four components: Financials, Competitive Moat, Market Context, Risk Profile |
| **Sub-Component** | A specific metric within a dimension (e.g., Revenue Growth within Financials) |
| **Confidence** | Data sufficiency and quality indicator (High/Medium/Low/Insufficient) |
| **Attention** | A deal flagged for immediate review based on score change or event |
| **Override** | A human-modified score that supersedes the system score |
| **Version** | A numbered release of the scoring methodology (e.g., v1.0.0) |
| **Backtest** | Retrospective evaluation of score accuracy against actual IC decisions |
| **Signal** | A discrete event (earnings, insider trade, M&A) that may affect a score |
| **Evidence Anchor** | A direct quote or data point from a primary source that justifies a scoring signal |

---

### Appendix E: Changelog

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-07-01 | Platform Team | Initial methodology release |

---

## Document Signatures

**Methodology Owner:** ________________________ Date: ____________  
**Senior Associate Review:** ________________________ Date: ____________  
**Product Lead Review:** ________________________ Date: ____________  

---

*This document is a living specification. Proposed changes must be reviewed by the Senior Associate and Product Lead before deployment. Emergency hotfixes (critical bugs) may be deployed by the Platform Team with a mandatory post-hoc review within 48 hours.*
