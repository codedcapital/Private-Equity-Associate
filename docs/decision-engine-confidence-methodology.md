# Decision Engine Confidence Scoring Methodology

## How Module-Level Confidence Propagates to the Final Investment Score

Last updated: 2025-07-02

---

## 1. Architecture Overview

The Decision Engine receives **N EvidenceModules** (financial, research, competitive, market, valuation) and produces three outputs:

| Output | Type | Range | Description |
|--------|------|-------|-------------|
| `investment_score` | int | 0-100 | Weighted average of module scores minus risk penalties |
| `confidence_score` | float | 0.0-1.0 | Weighted average of module-level confidence scores |
| `recommendation` | str | PROCEED / CONDITIONAL / PASS | Threshold-based decision |

Every number is **traceable to a specific EvidenceMetric** with a source and confidence score.

---

## 2. The Five Layers of Confidence

### Layer 1: Metric-Level Confidence
Each `EvidenceMetric` has a `confidence` field (0.0-1.0) set by the intelligence module that produced it.

```python
class EvidenceMetric(BaseModel):
    name: str                    # e.g. "Revenue CAGR"
    value: str | float | None    # e.g. "14.9%"
    confidence: float          # 0.0-1.0 — how sure we are about this metric
    is_supporting: bool          # Does this support the investment thesis?
    is_contradictory: bool     # Does this contradict the thesis?
    evidence_text: str           # Raw evidence
    source: str                 # "Yahoo Finance", "SEC 10-K", "Expert Call"
    source_type: str            # "api", "filing", "expert_call", "web"
```

**How confidence is assigned:**
- **Yahoo Finance / SEC 10-K**: 0.85-0.90 (audited financials)
- **Expert calls**: 0.70-0.80 (primary research, subjective)
- **Web research / Tavily**: 0.60-0.75 (secondary sources)
- **LLM synthesis**: 0.50-0.65 (interpretive, not primary data)
- **Placeholder / forecast**: 0.50-0.65 (forward-looking, uncertain)

### Layer 2: Module-Level Confidence
Each `EvidenceModule` computes `overall_confidence` as the average of its metric confidences:

```python
overall_confidence = sum(m.confidence for m in metrics) / len(metrics)
```

This represents the **average reliability of all evidence in that module**.

**Example:**
```python
financial_metrics = [
    EvidenceMetric(name="Revenue CAGR", confidence=0.90, ...),
    EvidenceMetric(name="EBITDA Margin", confidence=0.88, ...),
    EvidenceMetric(name="Leverage", confidence=0.85, ...),
    EvidenceMetric(name="Cash Conversion", confidence=0.85, ...),
]
# overall_confidence = (0.90 + 0.88 + 0.85 + 0.85) / 4 = 0.87
```

### Layer 3: Module Score
The module score (0-100) measures **how favorable the evidence is to the investment thesis**, independent of confidence:

```python
base_score = (supporting_metrics / total_metrics) * 100
penalty = (contradictory_count * 15) + (warning_count * 5)
module_score = max(0, min(100, base_score - penalty))
```

| Component | Weight |
|-----------|--------|
| Each supporting metric | +100/total_metrics points |
| Each contradictory metric | -15 points |
| Each warning | -5 points |

**Example:**
```python
# Financial module: 7 metrics, all supporting, 0 contradictory, 0 warnings
base_score = (7 / 7) * 100 = 100
penalty = (0 * 15) + (0 * 5) = 0
module_score = 100

# Valuation module: 4 metrics, 1 supporting, 0 contradictory, 3 warnings
base_score = (1 / 4) * 100 = 25
penalty = (0 * 15) + (3 * 5) = 15
module_score = max(0, 25 - 15) = 10
```

### Layer 4: Weighted Investment Score
The investment score is the **weighted average of module scores** minus a risk penalty:

```python
MODULE_WEIGHTS = {
    "financial": 0.25,   # Financial health is the foundation
    "research": 0.20,    # Market thesis matters
    "competitive": 0.20, # Moat quality
    "market": 0.15,      # Market context
    "valuation": 0.20,    # Returns are what PE cares about
}

weighted_score = sum(
    module_score * weight for module, weight in MODULE_WEIGHTS.items()
)

risk_penalty = min(20, contradictory_total * 5 + warnings_total * 3)
investment_score = max(0, min(100, int(weighted_score - risk_penalty)))
```

**Why these weights?**
- Financial (25%): Can't fix a broken balance sheet
- Valuation (20%): PE is a returns business — entry price matters enormously
- Research (20%): Need a growth thesis
- Competitive (20%): Need a moat to protect returns
- Market (15%): Context matters but less than fundamentals

**Example — Microsoft:**
```python
financial:     100 * 0.25 = 25.0
research:      100 * 0.20 = 20.0
competitive:   100 * 0.20 = 20.0
valuation:      10 * 0.20 =  2.0
weighted_score = 67.0

risk_penalty = min(20, 0 * 5 + 3 * 3) = 9
investment_score = 67 - 9 = 58
```

**Example — Intel:**
```python
financial:       0 * 0.25 =  0.0
research:       65 * 0.20 = 13.0
competitive:     0 * 0.20 =  0.0
valuation:      65 * 0.20 = 13.0
weighted_score = 26.0

risk_penalty = min(20, 8 * 5 + 9 * 3) = 20
investment_score = 26 - 20 = 6
```

### Layer 5: Weighted Confidence Score
The **confidence score** is independent of the investment score. It measures **how reliable the evidence is**, not how favorable:

```python
total_weight = sum(MODULE_WEIGHTS[ms.module_type] for ms in module_scores)

confidence_score = sum(
    ms.confidence * MODULE_WEIGHTS[ms.module_type] for ms in module_scores
) / total_weight
```

**Example — Microsoft:**
```python
financial:     0.87 * 0.25 = 0.2175
research:      0.78 * 0.20 = 0.1560
competitive:   0.84 * 0.20 = 0.1680
valuation:     0.70 * 0.20 = 0.1400
confidence_score = (0.2175 + 0.1560 + 0.1680 + 0.1400) / 0.85 = 0.80
```

**Example — Intel:**
```python
financial:     0.82 * 0.25 = 0.2050
research:      0.70 * 0.20 = 0.1400
competitive:   0.72 * 0.20 = 0.1440
valuation:     0.70 * 0.20 = 0.1400
confidence_score = (0.2050 + 0.1400 + 0.1440 + 0.1400) / 0.85 = 0.74
```

---

## 3. Recommendation Logic

The final recommendation uses **both** the investment score and confidence score:

```python
if investment_score >= 75 and confidence_score >= 0.70:
    recommendation = "PROCEED"
    conviction = "STRONG" if investment_score >= 85 else "MODERATE"
elif investment_score >= 60 and confidence_score >= 0.50:
    recommendation = "CONDITIONAL"
    conviction = "MODERATE" if investment_score >= 70 else "WEAK"
else:
    recommendation = "PASS"
    conviction = "WEAK"
```

| Investment Score | Confidence Score | Recommendation | Conviction | Meaning |
|------------------|------------------|----------------|------------|---------|
| ≥ 85 | ≥ 0.70 | **PROCEED** | **STRONG** | Clear yes, high confidence |
| 75-84 | ≥ 0.70 | **PROCEED** | **MODERATE** | Good deal, decent confidence |
| 60-74 | ≥ 0.50 | **CONDITIONAL** | **MODERATE** | Needs work, but worth pursuing |
| 60-74 | ≥ 0.50 | **CONDITIONAL** | **WEAK** | Barely above threshold |
| < 60 | any | **PASS** | **WEAK** | Don't do this deal |

**Why both scores matter:**
- A high investment score with low confidence = might be a good deal, but we don't know enough
- A low investment score with high confidence = we know it's a bad deal with certainty
- Both must be high for PROCEED

---

## 4. Confidence Propagation Flow

```
Raw Data (YFinance, SEC, Tavily)
    ↓
[Metric Confidence]  ← 0.85 for audited, 0.65 for web, 0.50 for LLM
    ↓
EvidenceMetric.confidence
    ↓
[Module Confidence]  ← average of metric confidences
    ↓
EvidenceModule.overall_confidence
    ↓
[Weighted Confidence]  ← weighted by MODULE_WEIGHTS
    ↓
DecisionOutput.confidence_score
    ↓
[Recommendation]  ← combined with investment_score
    ↓
PROCEED / CONDITIONAL / PASS
```

---

## 5. Real-World Test Matrix

| Company | Financial Score | Thesis Score | Competitive Score | Valuation Score | Risk Score | **Investment Score** | **Confidence** | **Recommendation** |
|---------|----------------|--------------|-------------------|-----------------|------------|----------------------|----------------|----------------------|
| **MSFT** | 100 | 100 | 100 | 10 | 0 | **58** | 0.80 | **PASS** |
| **INTC** | 0 | 65 | 0 | 65 | 50 | **6** | 0.74 | **PASS** |
| Strong Deal | 100 | 100 | 100 | 100 | 0 | **100** | 0.81 | **PROCEED** |
| Weak Deal | 55 | 61 | 100 | 40 | 30 | **36** | 0.76 | **PASS** |
| Conditional | 100 | 75 | 100 | 56 | 15 | **62** | 0.79 | **CONDITIONAL** |

---

## 6. Key Design Decisions

### Why confidence is weighted, not just averaged
A simple average would give equal weight to a 50% confidence market module and a 90% confidence financial module. Weighting by module importance ensures financial data (most reliable) dominates the confidence score.

### Why risk penalty is separate from module scores
The risk penalty (contradictory metrics + warnings) is applied **after** weighting, not within each module. This ensures that a single module with many warnings doesn't disproportionately drag down the score — instead, the penalty is spread across all modules proportionally.

### Why the maximum risk penalty is 20 points
Without a cap, a company with 10 warnings would get a 30-point penalty, making it impossible to score above 70 even with perfect metrics. The 20-point cap ensures the score stays responsive to strengths, not just weaknesses.

### Why valuation has 20% weight (same as research/competitive)
In PE, entry price is everything. A great business at 25x is a bad deal. A mediocre business at 6x can be a great deal. Valuation gets equal weight to thesis and moat because without returns, the rest doesn't matter.

---

## 7. Source Confidence Table

| Data Source | Typical Confidence | Source Type | Rationale |
|-------------|---------------------|-------------|-----------|
| Yahoo Finance (SEC filings) | 0.85-0.90 | api | Audited, GAAP, quarterly reported |
| SEC EDGAR (10-K, 10-Q) | 0.88-0.92 | filing | Primary source, regulatory filing |
| Expert calls | 0.70-0.80 | expert_call | Primary research, but subjective |
| Tavily web search | 0.60-0.75 | web | Secondary, may be outdated |
| Competitive analysis (LLM) | 0.65-0.80 | api | LLM synthesis of multiple sources |
| LBO model | 0.70-0.80 | internal | Assumption-driven, forward-looking |
| Forecast projections | 0.50-0.65 | internal | Inherently uncertain |

---

## 8. How to Trace Any Score Back to Source

Every score is traceable through the chain:

```python
decision.investment_score  # 58
    → module_scores[0].score  # financial = 100
        → EvidenceModule.metrics[0]  # Revenue CAGR = 14.9%
            → EvidenceMetric.source  # "Yahoo Finance"
            → EvidenceMetric.source_type  # "api"
            → EvidenceMetric.confidence  # 0.90
```

This is the "Palantir meets Bloomberg" principle: **every number has a source, every source has a confidence, every confidence feeds into a score**.

---

## 9. File Locations

| Component | Path | Purpose |
|-----------|------|---------|
| Evidence schemas | `backend/schemas/evidence.py` | EvidenceMetric, EvidenceModule, DecisionOutput |
| Decision Engine | `backend/services/decision_engine.py` | Scoring logic, recommendation logic |
| Data Provider | `backend/services/data_provider.py` | Cache-first YFinance fetcher |
| Financial module | `backend/agents/financials/graph.py` | Produces financial EvidenceModule |
| API endpoints | `backend/api/routers/intelligence.py` | POST /decision, GET /decision, POST /refresh-data |

---

## 10. Refreshing Data

```bash
# Force a live YFinance fetch for a company
POST /intelligence/{company_id}/refresh-data

# Generate a new decision from latest evidence
POST /intelligence/{company_id}/decision

# Retrieve cached decision
GET /intelligence/{company_id}/decision
```
