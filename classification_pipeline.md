# Classification Pipeline Specification

## Purpose

This document defines the authoritative specification for the Classification Pipeline in the Bank Statement Intelligence Engine (BSIE).

The classification pipeline is responsible for analyzing an uploaded PDF and determining:

- What bank issued the statement
- What type of statement it is
- Which templates are candidates for extraction
- Confidence scores for routing decisions

---

## Performance Requirements

| Metric | Requirement |
|--------|-------------|
| Latency | < 2 seconds end-to-end |
| Mode | Synchronous (blocking) |
| Input | Single PDF |
| Output | `classification.json` |

---

## Pipeline Stages

### Stage 1: PDF Metadata Extraction

**Input:** Raw PDF file

**Operations:**

1. Extract PDF metadata (producer, creator, creation date)
2. Count pages
3. Detect text layer presence (born-digital vs scanned)
4. Extract page dimensions

**Output:**

```json
{
  "page_count": 5,
  "has_text_layer": true,
  "producer": "Adobe PDF Library 15.0",
  "page_dimensions": [
    {"page": 1, "width": 612, "height": 792}
  ]
}
```

**Timeout:** 200ms

---

### Stage 2: First Page Analysis

**Input:** PDF page 1

**Operations:**

1. Render page 1 to image (150 DPI)
2. Extract embedded text (if present)
3. Extract first 2000 characters

**Output:**

```json
{
  "page_1_image_path": "/artifacts/{statement_id}/page_1.png",
  "page_1_text": "CHASE BANK...",
  "text_length": 1847
}
```

**Timeout:** 500ms

---

### Stage 3: Bank Family Detection

**Input:** Page 1 text + metadata

**Method:** Rule-based keyword matching with weighted scoring

**Rules Configuration (`bank_detection_rules.toml`):**

```toml
[[banks]]
family = "chase"
display_name = "Chase Bank"
keywords = ["CHASE", "JPMorgan Chase", "JPMORGAN"]
keyword_weights = [1.0, 1.0, 0.8]
header_patterns = ["chase\\.com", "Chase Bank.*Statement"]
negative_keywords = ["Chase Sapphire Lounge"]  # Avoid false positives
min_score = 0.7

[[banks]]
family = "bofa"
display_name = "Bank of America"
keywords = ["Bank of America", "BANK OF AMERICA", "BofA"]
keyword_weights = [1.0, 1.0, 0.9]
header_patterns = ["bankofamerica\\.com"]
min_score = 0.7

[[banks]]
family = "amex"
display_name = "American Express"
keywords = ["American Express", "AMERICAN EXPRESS", "AMEX"]
keyword_weights = [1.0, 1.0, 0.8]
header_patterns = ["americanexpress\\.com"]
min_score = 0.7
```

**Scoring Algorithm:**

```python
def score_bank_family(text: str, rules: BankRules) -> float:
    score = 0.0
    text_upper = text.upper()
    
    # Keyword matching
    for keyword, weight in zip(rules.keywords, rules.keyword_weights):
        if keyword.upper() in text_upper:
            score += weight
    
    # Pattern matching (regex)
    for pattern in rules.header_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            score += 0.5
    
    # Negative keyword penalty
    for neg_keyword in rules.negative_keywords:
        if neg_keyword.upper() in text_upper:
            score -= 0.3
    
    # Normalize to [0, 1]
    max_possible = sum(rules.keyword_weights) + len(rules.header_patterns) * 0.5
    return min(1.0, max(0.0, score / max_possible))
```

**Output:**

```json
{
  "bank_family": "chase",
  "bank_confidence": 0.92,
  "bank_candidates": [
    {"family": "chase", "score": 0.92},
    {"family": "bofa", "score": 0.05}
  ]
}
```

**Timeout:** 100ms

---

### Stage 4: Statement Type Detection

**Input:** Page 1 text

**Method:** Keyword + pattern matching

**Rules Configuration:**

```toml
[statement_types]

[statement_types.checking]
keywords = ["Checking", "CHECKING", "Checking Account", "DDA"]
patterns = ["Checking Statement", "Account Statement.*Checking"]
weight = 1.0

[statement_types.savings]
keywords = ["Savings", "SAVINGS", "Savings Account"]
patterns = ["Savings Statement"]
weight = 1.0

[statement_types.credit_card]
keywords = ["Credit Card", "CREDIT CARD", "Card Statement", "Cardmember"]
patterns = ["Credit Card Statement", "Account Summary.*Credit"]
negative_keywords = ["Debit Card"]  # Avoid confusion
weight = 1.0
```

**Output:**

```json
{
  "statement_type": "checking",
  "type_confidence": 0.88
}
```

---

### Stage 5: Segment Detection

**Input:** Page 1 text

**Method:** Keyword matching

**Rules:**

```toml
[segments]

[segments.business]
keywords = ["Business", "BUSINESS", "Commercial", "Corporate", "LLC", "Inc.", "Corp."]
patterns = ["Business Checking", "Commercial Account"]

[segments.personal]
keywords = ["Personal", "PERSONAL"]
patterns = ["Personal Checking", "Personal Savings"]
default = true  # If no business indicators, assume personal
```

**Output:**

```json
{
  "segment": "personal",
  "segment_confidence": 0.75
}
```

---

### Stage 6: Layout Fingerprint Generation

**Input:** Page 1 text + structure

**Purpose:** Create a stable identifier for statement layouts that can detect when banks change their formats.

**Algorithm:**

```python
def generate_layout_fingerprint(page_text: str, page_image: Image) -> str:
    """
    Generate a fingerprint that identifies statement layout structure.
    Similar layouts should produce similar fingerprints.
    """
    features = []
    
    # 1. Text density zones (divide page into 3x3 grid)
    zones = compute_text_density_zones(page_text, grid=(3, 3))
    features.append(quantize_zones(zones))  # e.g., "HML-HHM-LLM"
    
    # 2. Key structural elements
    has_logo_area = detect_logo_area(page_image, top_20_percent=True)
    has_table_lines = detect_horizontal_lines(page_image)
    has_footer = detect_footer_pattern(page_text)
    features.append(f"L{int(has_logo_area)}T{int(has_table_lines)}F{int(has_footer)}")
    
    # 3. Header keywords hash (first 500 chars)
    header_text = page_text[:500].upper()
    header_words = sorted(set(re.findall(r'\b[A-Z]{4,}\b', header_text)))[:10]
    features.append(hashlib.md5(''.join(header_words).encode()).hexdigest()[:8])
    
    return '-'.join(features)
```

**Example Fingerprint:** `HML-HHM-LLM-L1T1F1-a3f2c891`

**Output:**

```json
{
  "layout_fingerprint": "HML-HHM-LLM-L1T1F1-a3f2c891"
}
```

---

### Stage 7: Template Matching

**Input:** Classification results + Template Registry

**Method:** Multi-factor scoring against registered templates

**Matching Algorithm:**

```python
def match_templates(
    classification: Classification,
    templates: List[Template]
) -> List[TemplateCandidate]:
    
    candidates = []
    
    for template in templates:
        if template.status != "stable":
            continue
            
        score = 0.0
        factors = {}
        
        # Factor 1: Bank family match (required)
        if template.bank_family != classification.bank_family:
            continue
        factors["bank_match"] = 1.0
        score += 0.3
        
        # Factor 2: Statement type match (required)
        if template.statement_type != classification.statement_type:
            continue
        factors["type_match"] = 1.0
        score += 0.3
        
        # Factor 3: Segment match
        if template.segment == classification.segment:
            factors["segment_match"] = 1.0
            score += 0.2
        elif template.segment == "unknown":
            factors["segment_match"] = 0.5
            score += 0.1
        else:
            continue  # Wrong segment
        
        # Factor 4: Layout fingerprint similarity
        fingerprint_sim = compute_fingerprint_similarity(
            classification.layout_fingerprint,
            template.layout_fingerprint
        )
        factors["fingerprint_similarity"] = fingerprint_sim
        score += 0.2 * fingerprint_sim
        
        candidates.append(TemplateCandidate(
            template_id=template.template_id,
            version=template.version,
            score=score,
            factors=factors
        ))
    
    # Sort by score descending
    candidates.sort(key=lambda c: c.score, reverse=True)
    
    return candidates
```

**Selection Threshold:** `score >= 0.80` for automatic selection

**Output:**

```json
{
  "candidate_templates": [
    {
      "template_id": "chase_checking_personal_v2",
      "version": "2.1.0",
      "score": 0.95,
      "factors": {
        "bank_match": 1.0,
        "type_match": 1.0,
        "segment_match": 1.0,
        "fingerprint_similarity": 0.85
      }
    },
    {
      "template_id": "chase_checking_personal_v1",
      "version": "1.3.0",
      "score": 0.82,
      "factors": {
        "bank_match": 1.0,
        "type_match": 1.0,
        "segment_match": 1.0,
        "fingerprint_similarity": 0.60
      }
    }
  ]
}
```

---

## Final Output Schema

**File:** `classification.json`

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "StatementClassification",
  "type": "object",
  "required": [
    "statement_id",
    "bank_family",
    "statement_type",
    "segment",
    "layout_fingerprint",
    "confidence",
    "candidate_templates",
    "classified_at"
  ],
  "properties": {
    "statement_id": {"type": "string"},
    "bank_family": {"type": "string"},
    "bank_confidence": {"type": "number", "minimum": 0, "maximum": 1},
    "statement_type": {
      "type": "string",
      "enum": ["checking", "savings", "credit_card"]
    },
    "type_confidence": {"type": "number", "minimum": 0, "maximum": 1},
    "segment": {
      "type": "string",
      "enum": ["personal", "business", "unknown"]
    },
    "segment_confidence": {"type": "number", "minimum": 0, "maximum": 1},
    "layout_fingerprint": {"type": "string"},
    "confidence": {
      "type": "number",
      "minimum": 0,
      "maximum": 1,
      "description": "Overall classification confidence (weighted average)"
    },
    "candidate_templates": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["template_id", "version", "score"],
        "properties": {
          "template_id": {"type": "string"},
          "version": {"type": "string"},
          "score": {"type": "number", "minimum": 0, "maximum": 1},
          "factors": {
            "type": "object",
            "additionalProperties": {"type": "number"}
          }
        },
        "additionalProperties": false
      }
    },
    "classified_at": {"type": "string", "format": "date-time"},
    "classifier_version": {"type": "string"}
  },
  "additionalProperties": false
}
```

---

## Confidence Calculation

**Overall Confidence Formula:**

```python
confidence = (
    0.35 * bank_confidence +
    0.35 * type_confidence +
    0.15 * segment_confidence +
    0.15 * (top_template_score if candidate_templates else 0)
)
```

**Confidence Thresholds:**

| Confidence | Interpretation | Action |
|------------|----------------|--------|
| ≥ 0.90 | High confidence | Auto-select top template |
| 0.80 - 0.89 | Good confidence | Auto-select with logging |
| 0.60 - 0.79 | Medium confidence | Require confirmation |
| < 0.60 | Low confidence | Manual review required |

---

## Error Handling

### No Bank Match

```json
{
  "bank_family": "unknown",
  "bank_confidence": 0.0,
  "candidate_templates": [],
  "confidence": 0.15
}
```

**State Transition:** → `TEMPLATE_MISSING`

### Multiple High-Confidence Templates

If multiple templates score ≥ 0.90, select the one with:

1. Higher fingerprint similarity
2. More recent version
3. More statements processed (stability indicator)

### Classification Timeout

If classification exceeds 2 seconds:

- Return partial results with reduced confidence
- Log timeout for investigation
- Proceed with available information

---

## Extensibility

### Adding New Banks

1. Add entry to `bank_detection_rules.toml`
2. Create template for new bank
3. No code changes required

### Improving Detection

1. Classification accuracy metrics tracked per bank
2. False positive/negative logging
3. Rule weights adjustable without code changes

---

## Testing Requirements

### Unit Tests

- Each stage independently testable
- Mock PDF inputs for each bank family
- Edge cases: multi-bank PDFs, corrupted text, no text layer

### Integration Tests

- End-to-end classification with real PDFs
- Performance benchmarks (<2 seconds)
- Accuracy benchmarks (>95% correct bank detection)

### Test Fixtures

Maintain test PDFs for:

- Each supported bank family
- Each statement type
- Each segment
- Edge cases (poor quality, unusual layouts)

---

End of Classification Pipeline Specification
