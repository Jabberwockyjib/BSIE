# Error Taxonomy Specification

## Purpose

This document defines the authoritative error taxonomy for the Bank Statement Intelligence Engine (BSIE).

Every error in the system must be classified according to this taxonomy. Error classification determines:

- State transitions
- Recovery strategies
- Retry policies
- User messaging
- Alerting behavior

---

## Error Classification Framework

### Primary Categories

| Category | Code Range | Recoverable | Auto-Retry | Human Review |
|----------|------------|-------------|------------|--------------|
| VALIDATION | E1xxx | No | No | No |
| TRANSIENT | E2xxx | Yes | Yes | No |
| EXTRACTION | E3xxx | Partial | Limited | Yes |
| RECONCILIATION | E4xxx | Partial | No | Yes |
| CONFIGURATION | E5xxx | No | No | No (requires fix) |
| SYSTEM | E9xxx | Depends | Limited | Escalate |

---

## Validation Errors (E1xxx)

Validation errors indicate malformed input or schema violations. These are not recoverable without correcting the source.

### E1001: Invalid PDF Format

```json
{
  "code": "E1001",
  "category": "VALIDATION",
  "message": "File is not a valid PDF",
  "details": {
    "mime_type_detected": "application/zip",
    "expected": "application/pdf"
  },
  "recoverable": false,
  "user_action": "Upload a valid PDF file"
}
```

**State Transition:** `UPLOADED` → terminal (rejected)

---

### E1002: PDF Corrupted

```json
{
  "code": "E1002",
  "category": "VALIDATION",
  "message": "PDF file is corrupted or unreadable",
  "details": {
    "parser_error": "Invalid xref table",
    "byte_offset": 12456
  },
  "recoverable": false,
  "user_action": "Re-download or re-scan the original document"
}
```

---

### E1003: PDF Encrypted

```json
{
  "code": "E1003",
  "category": "VALIDATION",
  "message": "PDF is password-protected",
  "details": {
    "encryption_type": "AES-256"
  },
  "recoverable": false,
  "user_action": "Provide an unencrypted version of the PDF"
}
```

---

### E1010: Schema Validation Failed

```json
{
  "code": "E1010",
  "category": "VALIDATION",
  "message": "Artifact does not conform to required schema",
  "details": {
    "schema": "transactions.json",
    "violations": [
      {
        "path": "$.transactions[5].amount",
        "error": "Expected number, got string"
      }
    ]
  },
  "recoverable": false,
  "user_action": null,
  "internal_action": "Fix extraction logic"
}
```

---

### E1011: Invalid Template

```json
{
  "code": "E1011",
  "category": "VALIDATION",
  "message": "Template TOML is invalid",
  "details": {
    "template_id": "chase_checking_v1",
    "parse_error": "Invalid TOML at line 45"
  },
  "recoverable": false,
  "user_action": null,
  "internal_action": "Fix template definition"
}
```

---

### E1012: Bounding Box Out of Range

```json
{
  "code": "E1012",
  "category": "VALIDATION",
  "message": "Bounding box coordinates exceed valid range",
  "details": {
    "bbox": [0.05, 0.22, 1.15, 0.88],
    "invalid_value": 1.15,
    "valid_range": [0.0, 1.0]
  },
  "recoverable": false
}
```

---

### E1020: Invalid State Transition

```json
{
  "code": "E1020",
  "category": "VALIDATION",
  "message": "Attempted invalid state transition",
  "details": {
    "current_state": "CLASSIFIED",
    "attempted_state": "COMPLETED",
    "allowed_transitions": ["ROUTED"]
  },
  "recoverable": false,
  "internal_action": "Bug in state management logic"
}
```

---

## Transient Errors (E2xxx)

Transient errors are temporary failures that may succeed on retry.

### Retry Policy

```python
TRANSIENT_RETRY_POLICY = {
    "max_attempts": 3,
    "initial_delay_seconds": 1,
    "backoff_multiplier": 2,
    "max_delay_seconds": 30
}
```

---

### E2001: Service Unavailable

```json
{
  "code": "E2001",
  "category": "TRANSIENT",
  "message": "External service temporarily unavailable",
  "details": {
    "service": "tesseract_ocr",
    "status_code": 503
  },
  "recoverable": true,
  "retry_after_seconds": 5
}
```

---

### E2002: Timeout

```json
{
  "code": "E2002",
  "category": "TRANSIENT",
  "message": "Operation timed out",
  "details": {
    "operation": "ocr_page",
    "timeout_seconds": 30,
    "elapsed_seconds": 31.2
  },
  "recoverable": true
}
```

---

### E2003: Resource Exhausted

```json
{
  "code": "E2003",
  "category": "TRANSIENT",
  "message": "System resources temporarily exhausted",
  "details": {
    "resource": "memory",
    "available_mb": 128,
    "required_mb": 512
  },
  "recoverable": true,
  "retry_after_seconds": 60
}
```

---

### E2004: Queue Full

```json
{
  "code": "E2004",
  "category": "TRANSIENT",
  "message": "Job queue is full",
  "details": {
    "queue": "extraction_jobs",
    "depth": 1000,
    "max_depth": 1000
  },
  "recoverable": true,
  "retry_after_seconds": 30
}
```

---

### E2010: Database Connection Failed

```json
{
  "code": "E2010",
  "category": "TRANSIENT",
  "message": "Database connection temporarily unavailable",
  "details": {
    "database": "postgres",
    "error": "connection refused"
  },
  "recoverable": true
}
```

---

## Extraction Errors (E3xxx)

Extraction errors occur during table detection and data extraction. These may be partially recoverable with human assistance.

---

### E3001: No Table Detected

```json
{
  "code": "E3001",
  "category": "EXTRACTION",
  "message": "No transaction table found in document",
  "details": {
    "pages_scanned": [1, 2, 3, 4, 5],
    "detection_methods_tried": ["camelot_lattice", "camelot_stream"],
    "anchor_text_searched": "Date"
  },
  "recoverable": true,
  "requires_human_review": true,
  "suggested_actions": [
    "Verify correct template selected",
    "Adjust table detection bounding box",
    "Try different extraction method"
  ]
}
```

**State Transition:** `EXTRACTING` → `EXTRACTION_FAILED` → `HUMAN_REVIEW_REQUIRED`

---

### E3002: Partial Table Extraction

```json
{
  "code": "E3002",
  "category": "EXTRACTION",
  "message": "Table partially extracted with missing rows",
  "details": {
    "expected_rows_estimate": 45,
    "extracted_rows": 38,
    "pages_with_issues": [3, 4],
    "confidence": 0.84
  },
  "recoverable": true,
  "requires_human_review": true
}
```

---

### E3003: Column Mapping Failed

```json
{
  "code": "E3003",
  "category": "EXTRACTION",
  "message": "Unable to map columns to expected fields",
  "details": {
    "detected_columns": 6,
    "expected_columns": 4,
    "header_row": ["Date", "Check #", "Description", "Withdrawals", "Deposits", "Balance"]
  },
  "recoverable": true,
  "requires_human_review": true,
  "suggested_actions": [
    "Update column mapping in template",
    "Handle merged debit/credit columns"
  ]
}
```

---

### E3004: Date Parse Failed

```json
{
  "code": "E3004",
  "category": "EXTRACTION",
  "message": "Unable to parse transaction dates",
  "details": {
    "sample_values": ["Jan 15", "01-15", "1/15/24"],
    "formats_tried": ["%m/%d/%Y", "%m/%d"],
    "parse_failures": 12
  },
  "recoverable": true,
  "requires_human_review": true
}
```

---

### E3005: Amount Parse Failed

```json
{
  "code": "E3005",
  "category": "EXTRACTION",
  "message": "Unable to parse transaction amounts",
  "details": {
    "sample_values": ["$1,234.56", "(45.00)", "1234.56-"],
    "parse_failures": 8
  },
  "recoverable": true
}
```

---

### E3010: OCR Quality Too Low

```json
{
  "code": "E3010",
  "category": "EXTRACTION",
  "message": "OCR quality insufficient for reliable extraction",
  "details": {
    "average_confidence": 0.45,
    "minimum_required": 0.70,
    "worst_pages": [2, 3],
    "sample_low_confidence_text": "Che<k #1234"
  },
  "recoverable": true,
  "requires_human_review": true,
  "suggested_actions": [
    "Request higher quality scan",
    "Manual transcription required"
  ]
}
```

---

### E3011: Mixed OCR Results

```json
{
  "code": "E3011",
  "category": "EXTRACTION",
  "message": "OCR produced inconsistent results across pages",
  "details": {
    "high_confidence_pages": [1, 2],
    "low_confidence_pages": [3, 4, 5],
    "confidence_variance": 0.35
  },
  "recoverable": true
}
```

---

### E3020: Multi-Page Table Stitching Failed

```json
{
  "code": "E3020",
  "category": "EXTRACTION",
  "message": "Unable to stitch transaction table across pages",
  "details": {
    "pages_with_table": [2, 3, 4],
    "stitching_point_issues": [
      {
        "from_page": 2,
        "to_page": 3,
        "issue": "Column count mismatch"
      }
    ]
  },
  "recoverable": true
}
```

---

### E3021: Header Row Not Found

```json
{
  "code": "E3021",
  "category": "EXTRACTION",
  "message": "Transaction table header row not detected",
  "details": {
    "anchor_text": "Date",
    "pages_searched": [1, 2]
  },
  "recoverable": true
}
```

---

## Reconciliation Errors (E4xxx)

Reconciliation errors occur when extracted transactions don't balance.

---

### E4001: Balance Mismatch

```json
{
  "code": "E4001",
  "category": "RECONCILIATION",
  "message": "Transaction totals do not match statement balance",
  "details": {
    "beginning_balance": 1000.00,
    "total_credits": 2500.00,
    "total_debits": -2234.56,
    "expected_ending_balance": 1265.44,
    "statement_ending_balance": 1265.46,
    "delta_cents": 2,
    "tolerance_cents": 2
  },
  "recoverable": true,
  "requires_human_review": true,
  "auto_approvable": true,
  "reason": "Delta within tolerance"
}
```

---

### E4002: Large Balance Discrepancy

```json
{
  "code": "E4002",
  "category": "RECONCILIATION",
  "message": "Significant balance discrepancy detected",
  "details": {
    "expected_ending_balance": 1265.44,
    "statement_ending_balance": 1465.44,
    "delta_cents": 20000,
    "tolerance_cents": 2
  },
  "recoverable": true,
  "requires_human_review": true,
  "suggested_causes": [
    "Missing transactions",
    "Incorrect amount extraction",
    "Wrong sign convention"
  ]
}
```

---

### E4003: Beginning Balance Not Found

```json
{
  "code": "E4003",
  "category": "RECONCILIATION",
  "message": "Unable to extract beginning balance from statement",
  "details": {
    "searched_regions": ["header", "summary_box"],
    "patterns_tried": ["Beginning Balance", "Previous Balance"]
  },
  "recoverable": true,
  "requires_human_review": true
}
```

---

### E4004: Ending Balance Not Found

```json
{
  "code": "E4004",
  "category": "RECONCILIATION",
  "message": "Unable to extract ending balance from statement",
  "recoverable": true,
  "requires_human_review": true
}
```

---

### E4010: Running Balance Discontinuity

```json
{
  "code": "E4010",
  "category": "RECONCILIATION",
  "message": "Running balance sequence has discontinuities",
  "details": {
    "discontinuities": [
      {
        "row": 15,
        "expected_balance": 1234.56,
        "actual_balance": 1334.56,
        "gap": 100.00
      }
    ]
  },
  "recoverable": true,
  "suggested_causes": [
    "Missing transaction between rows",
    "Incorrect amount on adjacent row"
  ]
}
```

---

## Configuration Errors (E5xxx)

Configuration errors indicate missing or invalid system configuration.

---

### E5001: Template Not Found

```json
{
  "code": "E5001",
  "category": "CONFIGURATION",
  "message": "Referenced template does not exist",
  "details": {
    "template_id": "chase_checking_v99",
    "available_versions": ["v1", "v2"]
  },
  "recoverable": false
}
```

---

### E5002: Extraction Method Not Available

```json
{
  "code": "E5002",
  "category": "CONFIGURATION",
  "message": "Specified extraction method is not installed",
  "details": {
    "method": "camelot_lattice",
    "error": "Camelot not installed"
  },
  "recoverable": false,
  "internal_action": "Install required dependency"
}
```

---

### E5003: Missing Environment Variable

```json
{
  "code": "E5003",
  "category": "CONFIGURATION",
  "message": "Required environment variable not set",
  "details": {
    "variable": "TESSERACT_PATH"
  },
  "recoverable": false
}
```

---

## System Errors (E9xxx)

System errors indicate infrastructure failures.

---

### E9001: Internal Server Error

```json
{
  "code": "E9001",
  "category": "SYSTEM",
  "message": "Unexpected internal error",
  "details": {
    "exception_type": "NullPointerException",
    "stack_trace": "..."
  },
  "recoverable": false,
  "alert_ops": true
}
```

---

### E9002: Storage Write Failed

```json
{
  "code": "E9002",
  "category": "SYSTEM",
  "message": "Failed to write to object storage",
  "details": {
    "path": "/artifacts/stmt_123/page_1.png",
    "error": "Disk full"
  },
  "recoverable": false,
  "alert_ops": true
}
```

---

### E9003: State Corruption Detected

```json
{
  "code": "E9003",
  "category": "SYSTEM",
  "message": "Pipeline state is inconsistent",
  "details": {
    "statement_id": "stmt_123",
    "expected_artifacts": ["classification.json"],
    "missing_artifacts": ["classification.json"],
    "current_state": "ROUTED"
  },
  "recoverable": false,
  "alert_ops": true,
  "internal_action": "Manual state repair required"
}
```

---

## Error Response Schema

All errors returned by the API follow this schema:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "ErrorResponse",
  "type": "object",
  "required": ["error"],
  "properties": {
    "error": {
      "type": "object",
      "required": ["code", "category", "message"],
      "properties": {
        "code": {
          "type": "string",
          "pattern": "^E[0-9]{4}$"
        },
        "category": {
          "type": "string",
          "enum": ["VALIDATION", "TRANSIENT", "EXTRACTION", "RECONCILIATION", "CONFIGURATION", "SYSTEM"]
        },
        "message": {"type": "string"},
        "details": {"type": "object"},
        "recoverable": {"type": "boolean"},
        "requires_human_review": {"type": "boolean"},
        "retry_after_seconds": {"type": "integer"},
        "suggested_actions": {
          "type": "array",
          "items": {"type": "string"}
        },
        "user_action": {"type": "string"},
        "request_id": {"type": "string"},
        "timestamp": {"type": "string", "format": "date-time"}
      },
      "additionalProperties": false
    }
  }
}
```

---

## Error Handling Decision Tree

```
Error Occurs
    │
    ▼
Is it VALIDATION error?
    │
    ├─ Yes → Reject immediately, no retry
    │
    ▼
Is it TRANSIENT error?
    │
    ├─ Yes → Retry with backoff (max 3 attempts)
    │         │
    │         ├─ Success → Continue
    │         └─ Failure → Escalate to SYSTEM error
    │
    ▼
Is it EXTRACTION or RECONCILIATION error?
    │
    ├─ Yes → Log error details
    │         │
    │         ├─ Auto-recoverable? → Apply automatic fix
    │         │
    │         └─ Requires review → Transition to HUMAN_REVIEW_REQUIRED
    │
    ▼
Is it CONFIGURATION error?
    │
    ├─ Yes → Alert operations team, block processing
    │
    ▼
Is it SYSTEM error?
    │
    └─ Yes → Alert operations team
              Log full context
              Attempt recovery if possible
```

---

## Metrics & Alerting

### Error Rate Thresholds

| Category | Warning Threshold | Critical Threshold |
|----------|-------------------|-------------------|
| VALIDATION | >5% of uploads | >10% of uploads |
| TRANSIENT | >1% of operations | >5% of operations |
| EXTRACTION | >10% of statements | >25% of statements |
| RECONCILIATION | >5% of statements | >15% of statements |
| SYSTEM | Any occurrence | Any occurrence |

### Alert Destinations

| Severity | Channel |
|----------|---------|
| Warning | Slack #bsie-alerts |
| Critical | PagerDuty + Slack |

---

End of Error Taxonomy Specification
