# Dual VLLM Review Loop Specification

## Purpose

This document defines the authoritative specification for the Dual VLLM Review Loop in the Bank Statement Intelligence Engine (BSIE).

**Phase:** This is a **Phase 3** feature. Phase 2 uses single VLLM review with mandatory human approval.

---

## Overview

The Dual VLLM Review Loop uses two independent Vision-Language Model reviewers with complementary expertise to validate LLM-generated templates before they can be promoted to stable status.

**Key Insight:** Two reviewers with different perspectives catch more issues than a single reviewer, while remaining faster than human review.

---

## Reviewer Roles

### Reviewer 1: Layout Geometry Reviewer

**Focus:** Structural and spatial correctness

**Evaluates:**
- Bounding box accuracy
- Table region completeness
- Header/footer exclusion
- Multi-page continuity
- Column alignment

**Prompt Persona:**
```
You are a Layout Geometry Reviewer specializing in document structure analysis.
Your expertise is in spatial relationships, bounding boxes, and table detection.
You focus on WHETHER the template correctly identifies the physical location of data.
```

---

### Reviewer 2: Semantic Financial Reviewer

**Focus:** Financial logic and data correctness

**Evaluates:**
- Column mapping accuracy
- Sign convention correctness
- Date format handling
- Amount parsing rules
- Reconciliation feasibility

**Prompt Persona:**
```
You are a Semantic Financial Reviewer specializing in bank statement analysis.
Your expertise is in financial data interpretation, accounting conventions, and data quality.
You focus on WHETHER the template will correctly interpret the meaning of extracted data.
```

---

## Review Protocol

### Phase 1: Independent Review

Both reviewers analyze the template independently and simultaneously.

**Inputs (identical for both):**

```json
{
  "template_id": "chase_checking_draft_v1",
  "template_content": "...",  // TOML
  "statement_renders": [
    {"page": 1, "image": "<base64>"},
    {"page": 2, "image": "<base64>"}
  ],
  "sample_extraction": {
    "transactions": [...],
    "reconciliation": {...}
  },
  "prior_issues": []
}
```

**Process:**
1. Each reviewer analyzes template against rendered pages
2. Each reviewer checks sample extraction for issues
3. Each produces independent `reviewer_report.json`

---

### Phase 2: Consensus Check

After both reviews complete, the system checks for consensus.

**Consensus Rules:**

| R1 Pass | R2 Pass | Result |
|---------|---------|--------|
| ✓ | ✓ | **APPROVED** |
| ✓ | ✗ | Disagreement → Arbitration |
| ✗ | ✓ | Disagreement → Arbitration |
| ✗ | ✗ | **REJECTED** → Retry |

---

### Phase 3: Arbitration (If Needed)

When reviewers disagree, an arbitration round resolves the conflict.

**Arbitration Input:**

```json
{
  "template_id": "chase_checking_draft_v1",
  "template_content": "...",
  "reviewer_1_report": {...},
  "reviewer_2_report": {...},
  "disagreement_points": [
    {
      "issue_id": "issue_001",
      "r1_assessment": "pass",
      "r2_assessment": "fail",
      "r1_reasoning": "...",
      "r2_reasoning": "..."
    }
  ]
}
```

**Arbitration Prompt:**

```
You are an Arbitration Reviewer resolving disagreements between two reviewers.

Reviewer 1 (Layout Geometry) found: {r1_summary}
Reviewer 2 (Semantic Financial) found: {r2_summary}

They disagree on: {disagreement_points}

For each disagreement, determine:
1. Which reviewer's assessment is correct
2. Whether the issue is blocking (high/critical severity)
3. Your confidence in the arbitration

Rules:
- Layout issues defer to Reviewer 1 expertise
- Financial logic issues defer to Reviewer 2 expertise
- If uncertainty remains, err on the side of caution (fail)
```

**Arbitration Output:**

```json
{
  "arbitration_id": "arb_xyz789",
  "final_decision": "reject",
  "resolutions": [
    {
      "issue_id": "issue_001",
      "winning_reviewer": "reviewer_2",
      "final_severity": "high",
      "confidence": 0.85,
      "reasoning": "..."
    }
  ],
  "arbitrated_at": "2024-01-15T10:35:00Z"
}
```

---

## Pass Criteria

### Individual Reviewer Pass

A reviewer passes a template if:

1. **Zero critical issues**
2. **Zero high severity issues** (or all high issues have suggested fixes that don't require structural changes)
3. **Medium issues ≤ 3**
4. **Low issues ≤ 10**

### Combined Pass (Both Reviewers)

Template is approved if:

1. Both reviewers pass independently, OR
2. Arbitration resolves all blocking issues in favor of pass

---

## Issue Severity Definitions

| Severity | Definition | Blocking? |
|----------|------------|-----------|
| **Critical** | Template will produce incorrect data | Yes |
| **High** | Template will miss significant data or misclassify | Yes |
| **Medium** | Template may have edge case failures | Conditional |
| **Low** | Template could be improved but functions | No |

### Severity Examples

**Critical:**
- Bounding box excludes transaction table entirely
- Sign convention inverted (debits shown as credits)
- Wrong column mapped to amount field

**High:**
- Bounding box cuts off first/last rows
- Date format wrong for some transactions
- Multi-line descriptions truncated

**Medium:**
- Balance column mapping could be more precise
- Extra whitespace in extracted descriptions
- Some check numbers not captured

**Low:**
- Bounding box slightly larger than necessary
- Minor formatting inconsistencies
- Suboptimal extraction method choice

---

## Issue Deduplication

When both reviewers report similar issues, they are deduplicated:

**Deduplication Rules:**

```python
def are_issues_duplicates(issue_1: Issue, issue_2: Issue) -> bool:
    # Same category
    if issue_1.category != issue_2.category:
        return False
    
    # Similar location (if applicable)
    if issue_1.page and issue_2.page:
        if issue_1.page != issue_2.page:
            return False
    
    # Similar field/section
    if issue_1.location and issue_2.location:
        if issue_1.location.section != issue_2.location.section:
            return False
    
    # Semantic similarity of message
    similarity = compute_text_similarity(issue_1.message, issue_2.message)
    return similarity > 0.7
```

**Merged Issue:**
- Takes higher severity
- Combines suggested fixes
- Notes both reviewers identified it

---

## Issue Category Caps

To prevent runaway issue lists, caps are enforced per category:

| Category | Max Issues | Rationale |
|----------|------------|-----------|
| bbox_accuracy | 5 | Beyond 5, template needs major rework |
| column_mapping | 3 | Core structural issues |
| sign_logic | 2 | Binary decision |
| date_format | 3 | Limited variations |
| multiline_handling | 3 | Edge cases |
| reconciliation_strategy | 2 | High-level issue |
| provenance | 5 | Per-field tracking |
| other | 5 | Catch-all |

If a category exceeds its cap, only the highest severity issues are retained.

---

## Convergence Tracking

The system tracks whether the review loop is making progress toward approval.

### Convergence Metrics

```python
@dataclass
class ConvergenceState:
    attempt: int
    total_issues: int
    critical_issues: int
    high_issues: int
    issues_fixed_from_prior: int
    new_issues_introduced: int
    
    @property
    def convergence_score(self) -> float:
        """
        Score from -1.0 (diverging) to 1.0 (converging).
        """
        if self.attempt == 1:
            return 0.0  # No prior comparison
        
        fixed_ratio = self.issues_fixed_from_prior / max(1, self.prior_total_issues)
        new_ratio = self.new_issues_introduced / max(1, self.total_issues)
        
        return fixed_ratio - new_ratio
```

### Convergence Actions

| Score | Status | Action |
|-------|--------|--------|
| > 0.5 | Converging | Continue |
| 0.0 to 0.5 | Slow progress | Continue with warning |
| -0.2 to 0.0 | Stalled | One more attempt |
| < -0.2 | Diverging | Escalate to human |

---

## Retry Flow

When template is rejected, the system initiates a retry:

### Retry Input to Template Builder Agent

```json
{
  "retry_attempt": 2,
  "prior_template": "...",
  "reviewer_feedback": {
    "layout_reviewer": {
      "pass": false,
      "issues": [...]
    },
    "semantic_reviewer": {
      "pass": false,
      "issues": [...]
    }
  },
  "consolidated_issues": [
    {
      "issue_id": "issue_001",
      "severity": "high",
      "category": "bbox_accuracy",
      "message": "Table bounding box excludes header row",
      "suggested_fix": "Expand bbox y0 from 0.25 to 0.22",
      "reported_by": ["layout_reviewer"]
    }
  ],
  "convergence_status": "converging",
  "max_attempts_remaining": 2
}
```

### Retry Limits

| Scenario | Max Retries | Escalation |
|----------|-------------|------------|
| Both reviewers fail | 3 | Human review |
| Arbitration needed | 2 | Human review |
| Convergence stuck | 2 | Human review |
| Diverging | 1 | Immediate human review |

---

## Timing & Performance

### Timeout Budgets

| Operation | Timeout | Notes |
|-----------|---------|-------|
| Single reviewer | 60s | Per reviewer |
| Both reviewers (parallel) | 90s | With buffer |
| Arbitration | 45s | Focused scope |
| Full review cycle | 180s | Total |

### Parallelization

```
┌─────────────────────────────────────────────────────────────┐
│                      Review Cycle                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────┐     ┌─────────────────────┐       │
│  │ Layout Reviewer     │     │ Semantic Reviewer    │       │
│  │                     │     │                      │       │
│  │ [Parallel - 60s]    │     │ [Parallel - 60s]     │       │
│  └──────────┬──────────┘     └──────────┬───────────┘       │
│             │                           │                   │
│             └───────────┬───────────────┘                   │
│                         │                                   │
│                         ▼                                   │
│                 ┌───────────────┐                           │
│                 │ Consensus     │                           │
│                 │ Check [5s]    │                           │
│                 └───────┬───────┘                           │
│                         │                                   │
│          ┌──────────────┼──────────────┐                   │
│          ▼              ▼              ▼                   │
│     [Approved]    [Arbitration]   [Rejected]               │
│                        │                                    │
│                        ▼                                    │
│                 ┌───────────────┐                           │
│                 │ Arbitrator    │                           │
│                 │ [45s]         │                           │
│                 └───────────────┘                           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Reviewer Report Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "VLLMReviewerReport",
  "type": "object",
  "required": [
    "reviewer_id",
    "reviewer_role",
    "template_id",
    "pass",
    "issues",
    "summary",
    "reviewed_at"
  ],
  "properties": {
    "reviewer_id": {"type": "string"},
    "reviewer_role": {
      "type": "string",
      "enum": ["layout_geometry", "semantic_financial", "arbitrator"]
    },
    "reviewer_model": {"type": "string"},
    "template_id": {"type": "string"},
    "template_version": {"type": "string"},
    "pass": {"type": "boolean"},
    "issues": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["issue_id", "severity", "category", "message"],
        "properties": {
          "issue_id": {"type": "string"},
          "severity": {
            "type": "string",
            "enum": ["low", "medium", "high", "critical"]
          },
          "category": {
            "type": "string",
            "enum": [
              "bbox_accuracy",
              "column_mapping", 
              "sign_logic",
              "date_format",
              "multiline_handling",
              "reconciliation_strategy",
              "provenance",
              "other"
            ]
          },
          "message": {"type": "string"},
          "page": {"type": "integer"},
          "evidence": {
            "type": "object",
            "properties": {
              "expected": {"type": "string"},
              "actual": {"type": "string"},
              "location": {"type": "string"}
            }
          },
          "suggested_fix": {"type": "string"},
          "confidence": {
            "type": "number",
            "minimum": 0,
            "maximum": 1
          }
        }
      }
    },
    "summary": {
      "type": "object",
      "properties": {
        "strengths": {
          "type": "array",
          "items": {"type": "string"}
        },
        "weaknesses": {
          "type": "array", 
          "items": {"type": "string"}
        },
        "overall_quality_score": {
          "type": "number",
          "minimum": 0,
          "maximum": 1
        }
      }
    },
    "review_duration_ms": {"type": "integer"},
    "tokens_used": {
      "type": "object",
      "properties": {
        "input": {"type": "integer"},
        "output": {"type": "integer"}
      }
    },
    "reviewed_at": {"type": "string", "format": "date-time"}
  }
}
```

---

## Arbitration Report Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "ArbitrationReport",
  "type": "object",
  "required": [
    "arbitration_id",
    "template_id",
    "final_decision",
    "resolutions",
    "arbitrated_at"
  ],
  "properties": {
    "arbitration_id": {"type": "string"},
    "template_id": {"type": "string"},
    "input_reports": {
      "type": "object",
      "properties": {
        "layout_reviewer_id": {"type": "string"},
        "semantic_reviewer_id": {"type": "string"}
      }
    },
    "final_decision": {
      "type": "string",
      "enum": ["approve", "reject"]
    },
    "resolutions": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["issue_id", "winning_reviewer", "final_severity"],
        "properties": {
          "issue_id": {"type": "string"},
          "winning_reviewer": {
            "type": "string",
            "enum": ["layout_geometry", "semantic_financial", "neither"]
          },
          "final_severity": {
            "type": "string",
            "enum": ["low", "medium", "high", "critical", "dismissed"]
          },
          "confidence": {"type": "number"},
          "reasoning": {"type": "string"}
        }
      }
    },
    "unresolved_issues": {
      "type": "array",
      "items": {"type": "string"},
      "description": "Issue IDs where arbitration was uncertain"
    },
    "recommendation": {"type": "string"},
    "arbitrated_at": {"type": "string", "format": "date-time"}
  }
}
```

---

## Model Requirements

### Primary Reviewers

| Requirement | Specification |
|-------------|---------------|
| Vision capability | Required (for page images) |
| Context length | ≥ 32K tokens |
| Structured output | Preferred (JSON mode) |
| Latency | < 60s per review |

### Recommended Models

| Model | Role | Notes |
|-------|------|-------|
| Claude 3.5 Sonnet | Both reviewers | Good vision, structured output |
| GPT-4V | Arbitrator | Strong reasoning |
| Claude 3 Opus | High-stakes arbitration | Most capable |

### Model Diversity

For maximum issue detection, consider using different models for each reviewer:

```python
REVIEWER_CONFIG = {
    "layout_geometry": {
        "model": "claude-3-5-sonnet",
        "temperature": 0.1  # Precise, consistent
    },
    "semantic_financial": {
        "model": "gpt-4-vision",
        "temperature": 0.2  # Slightly more exploratory
    },
    "arbitrator": {
        "model": "claude-3-opus",
        "temperature": 0.0  # Maximum consistency
    }
}
```

---

## Metrics & Monitoring

### Review Quality Metrics

| Metric | Description |
|--------|-------------|
| First-pass approval rate | % templates approved on first review |
| Arbitration rate | % reviews requiring arbitration |
| Disagreement categories | Which issue types cause disagreements |
| Convergence rate | % templates that converge within retry limit |

### Cost Tracking

```json
{
  "review_cycle_id": "rc_abc123",
  "template_id": "chase_checking_draft_v1",
  "attempts": 2,
  "total_tokens": {
    "input": 45000,
    "output": 8500
  },
  "estimated_cost_usd": 0.85,
  "final_outcome": "approved"
}
```

---

## Human Escalation

### Escalation Triggers

1. Max retries exceeded
2. Diverging convergence
3. Arbitration uncertainty > 50%
4. Reviewer timeout/failure
5. Critical issue disagreement

### Escalation Context

When escalating to human review, provide:

```json
{
  "escalation_reason": "max_retries_exceeded",
  "attempt_count": 4,
  "all_reviewer_reports": [...],
  "arbitration_reports": [...],
  "convergence_history": [
    {"attempt": 1, "issues": 8, "score": 0.0},
    {"attempt": 2, "issues": 6, "score": 0.25},
    {"attempt": 3, "issues": 5, "score": 0.17},
    {"attempt": 4, "issues": 5, "score": 0.0}
  ],
  "persistent_issues": [
    {
      "issue_id": "issue_bbox_header",
      "reported_in_attempts": [1, 2, 3, 4],
      "suggested_fixes_tried": ["...", "..."]
    }
  ],
  "recommendation": "Manual bounding box adjustment may be required"
}
```

---

## Configuration

### Default Settings

```toml
[vllm_review]
enabled = true  # Phase 3 only

[vllm_review.reviewers]
layout_model = "claude-3-5-sonnet"
semantic_model = "claude-3-5-sonnet"
arbitrator_model = "claude-3-opus"

[vllm_review.timeouts]
single_reviewer_seconds = 60
total_cycle_seconds = 180
arbitration_seconds = 45

[vllm_review.retry]
max_attempts = 3
convergence_threshold = -0.2

[vllm_review.pass_criteria]
max_critical = 0
max_high = 0
max_medium = 3
max_low = 10

[vllm_review.issue_caps]
bbox_accuracy = 5
column_mapping = 3
sign_logic = 2
date_format = 3
multiline_handling = 3
reconciliation_strategy = 2
provenance = 5
other = 5
```

---

End of Dual VLLM Review Loop Specification
