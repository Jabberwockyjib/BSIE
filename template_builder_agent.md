# Template Builder Agent Specification

## Purpose

This document defines the authoritative specification for the Template Builder Agent in the Bank Statement Intelligence Engine (BSIE).

**Note:** This agent is **Phase 2 scope**. Phase 1 uses manually-created templates only. This specification is provided for planning and design purposes.

---

## Overview

The Template Builder Agent is an LLM-powered component that generates candidate TOML templates for bank statements that have no matching template in the registry.

**Key Principle:** The agent proposes, humans approve (Phase 2), or dual VLLM reviewers approve (Phase 3).

---

## Agent Responsibilities

1. Analyze PDF structure and content
2. Identify transaction table regions
3. Determine optimal extraction method
4. Generate valid TOML template
5. Provide confidence assessments
6. Incorporate reviewer feedback on retry

---

## Input Context

### Required Inputs

```json
{
  "statement_id": "stmt_abc123",
  "classification": {
    "bank_family": "chase",
    "statement_type": "checking",
    "segment": "personal"
  },
  "page_renders": [
    {
      "page": 1,
      "image_path": "/artifacts/stmt_abc123/page_1.png",
      "dimensions": {"width": 612, "height": 792}
    }
  ],
  "extracted_text": {
    "page_1": "CHASE BANK...",
    "page_2": "..."
  },
  "pdf_metadata": {
    "page_count": 5,
    "has_text_layer": true
  },
  "similar_templates": [
    {
      "template_id": "chase_checking_business_v1",
      "similarity_score": 0.65,
      "template_content": "..."
    }
  ],
  "prior_attempts": [],
  "schema_version": "1.0.0"
}
```

### Retry Context (If Applicable)

```json
{
  "prior_attempts": [
    {
      "attempt": 1,
      "template_generated": "...",
      "reviewer_feedback": [
        {
          "reviewer": "layout_reviewer",
          "pass": false,
          "issues": [
            {
              "severity": "high",
              "message": "Table bounding box excludes header row",
              "suggested_fix": "Expand bbox y0 from 0.25 to 0.22"
            }
          ]
        }
      ]
    }
  ]
}
```

---

## Output Specification

### Required Outputs

1. **Candidate Template (TOML)**
2. **Build Report (JSON)**

### Template Output

Must conform exactly to `template_adapter.md` schema. The agent must generate valid TOML that passes schema validation.

### Build Report Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "TemplateBuildReport",
  "type": "object",
  "required": [
    "statement_id",
    "template_id",
    "attempt_number",
    "agent_model",
    "decisions",
    "confidence_scores",
    "generated_at"
  ],
  "properties": {
    "statement_id": {"type": "string"},
    "template_id": {"type": "string"},
    "attempt_number": {"type": "integer", "minimum": 1},
    "agent_model": {
      "type": "string",
      "description": "Model identifier used for generation"
    },
    "decisions": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["category", "decision", "reasoning"],
        "properties": {
          "category": {
            "type": "string",
            "enum": [
              "table_detection",
              "extraction_method",
              "column_mapping",
              "multiline_handling",
              "sign_convention",
              "reconciliation_strategy"
            ]
          },
          "decision": {"type": "string"},
          "reasoning": {"type": "string"},
          "alternatives_considered": {
            "type": "array",
            "items": {"type": "string"}
          },
          "confidence": {
            "type": "number",
            "minimum": 0,
            "maximum": 1
          }
        },
        "additionalProperties": false
      }
    },
    "confidence_scores": {
      "type": "object",
      "properties": {
        "overall": {"type": "number", "minimum": 0, "maximum": 1},
        "table_detection": {"type": "number", "minimum": 0, "maximum": 1},
        "column_mapping": {"type": "number", "minimum": 0, "maximum": 1},
        "extraction_method": {"type": "number", "minimum": 0, "maximum": 1}
      },
      "required": ["overall"]
    },
    "warnings": {
      "type": "array",
      "items": {"type": "string"}
    },
    "generated_at": {"type": "string", "format": "date-time"}
  },
  "additionalProperties": false
}
```

---

## Prompting Strategy

### System Prompt Structure

```
You are a Template Builder Agent for the Bank Statement Intelligence Engine.

Your task is to analyze bank statement PDFs and generate TOML template configurations
that enable deterministic transaction extraction.

## Constraints (MUST follow exactly)

1. Output ONLY valid TOML conforming to the provided schema
2. All bounding boxes MUST be in range [0.0, 1.0]
3. Column mappings MUST use col_1, col_2, etc.
4. Extraction methods MUST be from: camelot_lattice, camelot_stream, tabula_stream, pdfplumber_columns
5. Date formats MUST be Python strptime compatible
6. Template MUST define sign convention explicitly

## Schema Reference

[Insert template_adapter.md schema here]

## Your Approach

1. First, identify the transaction table boundaries by finding:
   - Header row with Date, Description, Amount columns
   - First transaction row
   - Last transaction row
   - Footer/summary area to exclude

2. Then, determine extraction method based on:
   - Table has visible grid lines → camelot_lattice
   - Table has no lines but clear columns → camelot_stream
   - Columns are irregular → pdfplumber_columns

3. Map columns by analyzing header text

4. Determine sign convention by looking for:
   - Separate Debit/Credit columns
   - Negative amounts in parentheses
   - +/- prefixes

5. Output the complete TOML template
```

### User Prompt Structure

```
## Statement Information

Bank: {bank_family}
Type: {statement_type}
Segment: {segment}
Pages: {page_count}

## Page 1 Text (first 3000 chars)

{page_1_text}

## Similar Templates (for reference)

{similar_templates_toml}

## Prior Attempt Feedback (if any)

{reviewer_feedback}

## Task

Generate a TOML template for this statement type. Include a build report explaining your decisions.

Output format:
1. First, output the TOML template inside ```toml blocks
2. Then, output the build report as JSON inside ```json blocks
```

---

## Schema Enforcement

### Pre-Submission Validation

Before the agent's output is accepted, it must pass:

1. **TOML Syntax Validation**
   - Parse without errors
   - No undefined values

2. **Schema Compliance**
   - All required fields present
   - All values in valid ranges
   - Bounding boxes in [0, 1]
   - Enum values from allowed set

3. **Logical Consistency**
   - Column count matches mapping
   - Date formats are valid
   - Extraction methods exist

### Validation Pipeline

```python
def validate_agent_output(toml_string: str, schema: dict) -> ValidationResult:
    # Step 1: Parse TOML
    try:
        template = toml.loads(toml_string)
    except toml.TomlDecodeError as e:
        return ValidationResult(
            valid=False,
            stage="toml_parse",
            error=str(e)
        )
    
    # Step 2: Schema validation
    try:
        jsonschema.validate(template, schema)
    except jsonschema.ValidationError as e:
        return ValidationResult(
            valid=False,
            stage="schema_validation",
            error=e.message,
            path=list(e.path)
        )
    
    # Step 3: Semantic validation
    errors = []
    
    # Check bounding boxes
    for bbox in extract_all_bboxes(template):
        if not all(0 <= v <= 1 for v in bbox):
            errors.append(f"Bounding box out of range: {bbox}")
    
    # Check column mappings
    if template.get("columns", {}).get("map"):
        for field, col in template["columns"]["map"].items():
            if not re.match(r"col_\d+", col):
                errors.append(f"Invalid column reference: {col}")
    
    # Check extraction methods
    valid_methods = {"camelot_lattice", "camelot_stream", "tabula_stream", "pdfplumber_columns"}
    for method in template.get("extraction", {}).get("methods", []):
        if method not in valid_methods:
            errors.append(f"Unknown extraction method: {method}")
    
    if errors:
        return ValidationResult(
            valid=False,
            stage="semantic_validation",
            errors=errors
        )
    
    return ValidationResult(valid=True)
```

---

## Constrained Generation Approach

To prevent creative drift and ensure schema compliance, the agent uses structured output techniques:

### Option A: JSON Mode with Post-Processing

1. Request JSON output following strict schema
2. Convert JSON to TOML after validation
3. Advantage: Better schema enforcement
4. Disadvantage: Less natural for TOML-specific syntax

### Option B: Few-Shot Examples

1. Provide 3-5 complete template examples in prompt
2. Agent follows established patterns
3. Advantage: Learns conventions from examples
4. Disadvantage: May miss edge cases

### Option C: Guided Generation (Recommended)

1. Generate template section by section
2. Validate each section before proceeding
3. Allow backtracking on validation failure

```python
async def guided_template_generation(context: AgentContext) -> Template:
    sections = [
        ("metadata", generate_metadata),
        ("detect", generate_detect),
        ("preprocess", generate_preprocess),
        ("table", generate_table),
        ("extraction", generate_extraction),
        ("columns", generate_columns),
        ("parsing", generate_parsing),
        ("normalization", generate_normalization),
        ("provenance", generate_provenance),
        ("verification", generate_verification)
    ]
    
    template_parts = {}
    
    for section_name, generator in sections:
        for attempt in range(3):
            section = await generator(context, template_parts)
            validation = validate_section(section_name, section)
            
            if validation.valid:
                template_parts[section_name] = section
                break
            else:
                context.add_feedback(section_name, validation.errors)
        else:
            raise TemplateGenerationError(f"Failed to generate {section_name}")
    
    return assemble_template(template_parts)
```

---

## Feedback Integration

When the agent receives reviewer feedback, it must:

### 1. Parse Feedback

```python
def parse_reviewer_feedback(feedback: List[ReviewerReport]) -> AgentGuidance:
    guidance = AgentGuidance()
    
    for report in feedback:
        for issue in report.issues:
            if issue.severity in ["high", "critical"]:
                guidance.must_fix.append(issue)
            else:
                guidance.should_consider.append(issue)
            
            if issue.suggested_fix:
                guidance.suggestions.append(issue.suggested_fix)
    
    return guidance
```

### 2. Apply Corrections

The agent's retry prompt includes:

```
## Previous Attempt Issues (MUST ADDRESS)

{must_fix_issues}

## Suggested Fixes

{suggestions}

## Instructions

Generate a corrected template that addresses ALL high/critical issues.
Explain how each issue was resolved in your build report.
```

### 3. Track Convergence

```python
def check_convergence(attempts: List[AttemptResult]) -> ConvergenceStatus:
    if len(attempts) < 2:
        return ConvergenceStatus.IN_PROGRESS
    
    current_issues = set(i.id for i in attempts[-1].issues)
    previous_issues = set(i.id for i in attempts[-2].issues)
    
    # Check if making progress
    if current_issues == previous_issues:
        return ConvergenceStatus.STUCK
    
    if len(current_issues) > len(previous_issues):
        return ConvergenceStatus.DIVERGING
    
    if len(current_issues) == 0:
        return ConvergenceStatus.CONVERGED
    
    return ConvergenceStatus.IMPROVING
```

---

## Retry Policy

| Attempt | Action | Escalation |
|---------|--------|------------|
| 1 | Initial generation | — |
| 2 | Incorporate feedback, retry | — |
| 3 | Incorporate feedback, retry | — |
| 4+ | Escalate to human review | `HUMAN_REVIEW_REQUIRED` |

### Retry Decision Logic

```python
def should_retry(attempt: int, convergence: ConvergenceStatus) -> Decision:
    if attempt >= MAX_RETRIES:
        return Decision.ESCALATE
    
    if convergence == ConvergenceStatus.STUCK:
        return Decision.ESCALATE  # Agent can't make progress
    
    if convergence == ConvergenceStatus.DIVERGING:
        return Decision.ESCALATE  # Getting worse
    
    return Decision.RETRY
```

---

## Agent Selection (Phase 2+)

### Model Requirements

- Vision capability (for page image analysis)
- Long context (for multi-page statements)
- Structured output support
- Tool use capability (optional, for guided generation)

### Recommended Models

| Model | Use Case | Notes |
|-------|----------|-------|
| Claude 3.5 Sonnet | Primary generation | Good balance of quality/cost |
| GPT-4V | Backup/comparison | Alternative vision model |
| Local VLLM | Air-gapped deployments | Requires fine-tuning |

---

## Metrics & Monitoring

### Generation Metrics

- Attempts per successful template
- Validation failure rate by stage
- Average generation time
- Issue category distribution

### Quality Metrics

- First-attempt success rate
- Convergence rate (within 3 attempts)
- Human escalation rate
- Post-approval extraction success rate

---

## Testing Strategy

### Unit Tests

- TOML generation validity
- Schema compliance
- Feedback integration
- Convergence detection

### Integration Tests

- End-to-end generation with mock LLM
- Reviewer feedback loop
- Escalation triggers

### Evaluation Set

Maintain a set of "ground truth" templates for:

- Comparison against agent output
- Measuring structural similarity
- Tracking improvement over time

---

## Phase 2 vs Phase 3 Differences

| Aspect | Phase 2 | Phase 3 |
|--------|---------|---------|
| Approval | Human required | Dual VLLM |
| Retry limit | 2 before escalation | 3 before escalation |
| Confidence threshold | 0.90 for suggestions | 0.85 for auto-approval |
| Feedback source | Human reviewers | VLLM reviewers |

---

End of Template Builder Agent Specification
