# Runtime JSON Schemas v2.0 — Complete Appendix

## Purpose

This document defines the authoritative runtime JSON Schemas for the Bank Statement Intelligence Engine (BSIE).

These schemas are binding contracts between:

- FastAPI backend
- Background workers
- LLM / VLLM agents
- Next.js frontend

Any JSON artifact produced or consumed by the system MUST validate against the corresponding schema before:

- Being persisted
- Being displayed in the UI
- Triggering a state transition

No component may rely on undocumented fields or implicit structure.

---

## General Rules

- JSON Schema draft: **draft-07**
- `additionalProperties: false` everywhere (fail fast)
- All timestamps use ISO-8601 (`date-time`)
- All monetary values are **numeric** (no strings)
- Identifiers are opaque strings (no semantic parsing)
- Bounding boxes are normalized to [0, 1]

---

## Schema Index

| Schema | Artifact File | State Requirement |
|--------|---------------|-------------------|
| IngestReceipt | `ingest_receipt.json` | INGESTED |
| Classification | `classification.json` | CLASSIFIED |
| RouteDecision | `route_decision.json` | ROUTED |
| TemplateBuildReport | `template_build_report.json` | TEMPLATE_DRAFTED |
| TemplateReviewReport | `reviewer_report.json` | TEMPLATE_REVIEW |
| OCRResult | `ocr_result.json` | EXTRACTION_READY (if OCR needed) |
| ExtractionResult | `extraction_result.json` | EXTRACTING → RECONCILING |
| Transactions | `transactions.json` | RECONCILING |
| Reconciliation | `reconciliation.json` | COMPLETED or RECONCILIATION_FAILED |
| FinalTransactions | `final_transactions.json` | COMPLETED |
| CorrectionOverlay | `correction_overlay.json` | HUMAN_REVIEW (if corrections) |
| HumanReviewDecision | `human_review_decision.json` | After HUMAN_REVIEW |
| ExtractionError | `extraction_error.json` | EXTRACTION_FAILED |
| PipelineState | `pipeline_state.json` | All states |

---

## 1. Ingest Receipt Schema

**File:** `ingest_receipt.json`

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "IngestReceipt",
  "type": "object",
  "required": [
    "statement_id",
    "sha256",
    "pages",
    "stored",
    "original_path",
    "uploaded_at"
  ],
  "properties": {
    "statement_id": {
      "type": "string",
      "description": "System-assigned unique statement identifier"
    },
    "sha256": {
      "type": "string",
      "pattern": "^[a-f0-9]{64}$",
      "description": "SHA-256 hash of original PDF"
    },
    "pages": {
      "type": "integer",
      "minimum": 1
    },
    "file_size_bytes": {
      "type": "integer",
      "minimum": 1
    },
    "has_text_layer": {
      "type": "boolean",
      "description": "Whether PDF contains extractable text"
    },
    "stored": {
      "type": "boolean"
    },
    "original_path": {
      "type": "string"
    },
    "original_filename": {
      "type": "string"
    },
    "mime_type": {
      "type": "string",
      "const": "application/pdf"
    },
    "uploaded_at": {
      "type": "string",
      "format": "date-time"
    },
    "uploaded_by": {
      "type": "string"
    }
  },
  "additionalProperties": false
}
```

---

## 2. Classification Schema

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
    "bank_confidence": {
      "type": "number",
      "minimum": 0,
      "maximum": 1
    },
    "statement_type": {
      "type": "string",
      "enum": ["checking", "savings", "credit_card"]
    },
    "type_confidence": {
      "type": "number",
      "minimum": 0,
      "maximum": 1
    },
    "segment": {
      "type": "string",
      "enum": ["personal", "business", "unknown"]
    },
    "segment_confidence": {
      "type": "number",
      "minimum": 0,
      "maximum": 1
    },
    "layout_fingerprint": {"type": "string"},
    "confidence": {
      "type": "number",
      "minimum": 0,
      "maximum": 1,
      "description": "Overall classification confidence"
    },
    "candidate_templates": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["template_id", "version", "score"],
        "properties": {
          "template_id": {"type": "string"},
          "version": {"type": "string"},
          "score": {
            "type": "number",
            "minimum": 0,
            "maximum": 1
          },
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

## 3. Route Decision Schema

**File:** `route_decision.json`

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "RouteDecision",
  "type": "object",
  "required": [
    "statement_id",
    "decision",
    "decided_at"
  ],
  "properties": {
    "statement_id": {"type": "string"},
    "decision": {
      "type": "string",
      "enum": ["template_selected", "template_missing"]
    },
    "selected_template": {
      "type": "object",
      "properties": {
        "template_id": {"type": "string"},
        "version": {"type": "string"},
        "score": {"type": "number"}
      },
      "additionalProperties": false
    },
    "selection_reason": {"type": "string"},
    "alternatives_considered": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "template_id": {"type": "string"},
          "score": {"type": "number"},
          "rejection_reason": {"type": "string"}
        }
      }
    },
    "confidence_threshold_used": {"type": "number"},
    "decided_at": {"type": "string", "format": "date-time"}
  },
  "additionalProperties": false
}
```

---

## 4. Template Build Report Schema

**File:** `template_build_report.json`

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
    "template_version": {"type": "string"},
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
        "table_detection": {"type": "number"},
        "column_mapping": {"type": "number"},
        "extraction_method": {"type": "number"}
      },
      "required": ["overall"],
      "additionalProperties": false
    },
    "warnings": {
      "type": "array",
      "items": {"type": "string"}
    },
    "prior_feedback_addressed": {
      "type": "array",
      "items": {"type": "string"}
    },
    "generated_at": {"type": "string", "format": "date-time"}
  },
  "additionalProperties": false
}
```

---

## 5. Template Review Report Schema

**File:** `reviewer_report.json`

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "TemplateReviewReport",
  "type": "object",
  "required": [
    "reviewer_id",
    "reviewer_model",
    "template_id",
    "pass",
    "issues",
    "reviewed_at"
  ],
  "properties": {
    "reviewer_id": {
      "type": "string",
      "description": "Unique identifier for this reviewer instance"
    },
    "reviewer_model": {
      "type": "string",
      "description": "Model identifier of reviewing VLLM"
    },
    "reviewer_role": {
      "type": "string",
      "enum": ["layout_geometry", "semantic_financial"],
      "description": "Which review perspective this report covers"
    },
    "template_id": {"type": "string"},
    "template_version": {"type": "string"},
    "pass": {"type": "boolean"},
    "issues": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["issue_id", "severity", "message"],
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
          "location": {
            "type": "object",
            "properties": {
              "section": {"type": "string"},
              "field": {"type": "string"}
            }
          },
          "suggested_fix": {"type": "string"},
          "confidence": {"type": "number"}
        },
        "additionalProperties": false
      }
    },
    "risk_flags": {
      "type": "array",
      "items": {"type": "string"}
    },
    "review_duration_ms": {"type": "integer"},
    "reviewed_at": {"type": "string", "format": "date-time"}
  },
  "additionalProperties": false
}
```

---

## 6. OCR Result Schema

**File:** `ocr_result.json`

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "OCRResult",
  "type": "object",
  "required": [
    "statement_id",
    "ocr_engine",
    "ocr_version",
    "pages",
    "processed_at"
  ],
  "properties": {
    "statement_id": {"type": "string"},
    "ocr_engine": {
      "type": "string",
      "enum": ["tesseract", "ocrmypdf"]
    },
    "ocr_version": {"type": "string"},
    "ocr_language": {"type": "string", "default": "eng"},
    "pages": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["page_number", "text", "confidence"],
        "properties": {
          "page_number": {"type": "integer", "minimum": 1},
          "text": {"type": "string"},
          "confidence": {
            "type": "number",
            "minimum": 0,
            "maximum": 1
          },
          "words": {
            "type": "array",
            "items": {
              "type": "object",
              "required": ["text", "bbox", "confidence"],
              "properties": {
                "text": {"type": "string"},
                "bbox": {
                  "type": "array",
                  "items": {"type": "number"},
                  "minItems": 4,
                  "maxItems": 4,
                  "description": "Normalized [x0, y0, x1, y1]"
                },
                "confidence": {"type": "number"}
              },
              "additionalProperties": false
            }
          },
          "image_dimensions": {
            "type": "object",
            "properties": {
              "width": {"type": "integer"},
              "height": {"type": "integer"},
              "dpi": {"type": "integer"}
            }
          }
        },
        "additionalProperties": false
      }
    },
    "overall_confidence": {
      "type": "number",
      "minimum": 0,
      "maximum": 1
    },
    "processing_time_ms": {"type": "integer"},
    "processed_at": {"type": "string", "format": "date-time"}
  },
  "additionalProperties": false
}
```

---

## 7. Extraction Result Schema

**File:** `extraction_result.json`

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "ExtractionResult",
  "type": "object",
  "required": [
    "statement_id",
    "template_id",
    "status",
    "extracted_at"
  ],
  "properties": {
    "statement_id": {"type": "string"},
    "template_id": {"type": "string"},
    "template_version": {"type": "string"},
    "status": {
      "type": "string",
      "enum": ["complete", "partial", "failed"]
    },
    "method_used": {
      "type": "string",
      "enum": ["camelot_lattice", "camelot_stream", "tabula_stream", "pdfplumber_columns"]
    },
    "methods_attempted": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "method": {"type": "string"},
          "success": {"type": "boolean"},
          "rows_extracted": {"type": "integer"},
          "error": {"type": "string"}
        }
      }
    },
    "pages_processed": {
      "type": "array",
      "items": {"type": "integer"}
    },
    "tables_found": {"type": "integer"},
    "rows_extracted": {"type": "integer"},
    "rows_with_issues": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "row_index": {"type": "integer"},
          "issue": {"type": "string"},
          "severity": {"type": "string"}
        }
      }
    },
    "balances": {
      "type": "object",
      "properties": {
        "beginning_balance": {"type": "number"},
        "ending_balance": {"type": "number"},
        "beginning_balance_found": {"type": "boolean"},
        "ending_balance_found": {"type": "boolean"}
      }
    },
    "warnings": {
      "type": "array",
      "items": {"type": "string"}
    },
    "processing_time_ms": {"type": "integer"},
    "extracted_at": {"type": "string", "format": "date-time"}
  },
  "additionalProperties": false
}
```

---

## 8. Transactions Schema

**File:** `transactions.json`

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "StatementTransactions",
  "type": "object",
  "required": [
    "statement_id",
    "template_id",
    "transactions",
    "extracted_at"
  ],
  "properties": {
    "statement_id": {"type": "string"},
    "template_id": {"type": "string"},
    "template_version": {"type": "string"},
    "transactions": {
      "type": "array",
      "items": {
        "type": "object",
        "required": [
          "row_id",
          "posted_date",
          "description",
          "amount",
          "provenance"
        ],
        "properties": {
          "row_id": {"type": "string"},
          "row_index": {"type": "integer"},
          "posted_date": {"type": "string", "format": "date"},
          "effective_date": {"type": "string", "format": "date"},
          "description": {"type": "string"},
          "amount": {"type": "number"},
          "balance": {"type": ["number", "null"]},
          "check_number": {"type": "string"},
          "reference_number": {"type": "string"},
          "transaction_type": {
            "type": "string",
            "enum": ["debit", "credit", "unknown"]
          },
          "category": {"type": "string"},
          "provenance": {
            "type": "object",
            "required": ["page", "bbox", "source_pdf"],
            "properties": {
              "page": {"type": "integer", "minimum": 1},
              "bbox": {
                "type": "array",
                "items": {"type": "number"},
                "minItems": 4,
                "maxItems": 4,
                "description": "Normalized [x0, y0, x1, y1]"
              },
              "source_pdf": {"type": "string"},
              "extraction_method": {"type": "string"},
              "confidence": {
                "type": "number",
                "minimum": 0,
                "maximum": 1
              }
            },
            "additionalProperties": false
          },
          "raw": {
            "type": "object",
            "properties": {
              "raw_row_text": {"type": "string"},
              "raw_columns": {
                "type": "array",
                "items": {"type": "string"}
              }
            },
            "additionalProperties": false
          }
        },
        "additionalProperties": false
      }
    },
    "summary": {
      "type": "object",
      "properties": {
        "total_transactions": {"type": "integer"},
        "total_debits": {"type": "number"},
        "total_credits": {"type": "number"},
        "date_range": {
          "type": "object",
          "properties": {
            "start": {"type": "string", "format": "date"},
            "end": {"type": "string", "format": "date"}
          }
        }
      }
    },
    "extracted_at": {"type": "string", "format": "date-time"}
  },
  "additionalProperties": false
}
```

---

## 9. Reconciliation Schema

**File:** `reconciliation.json`

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "ReconciliationResult",
  "type": "object",
  "required": [
    "statement_id",
    "status",
    "reconciled_at"
  ],
  "properties": {
    "statement_id": {"type": "string"},
    "status": {
      "type": "string",
      "enum": ["pass", "fail", "warning", "overridden"]
    },
    "reconciliation_type": {
      "type": "string",
      "enum": ["checking", "savings", "credit_card"]
    },
    "beginning_balance": {"type": "number"},
    "ending_balance": {"type": "number"},
    "calculated_ending_balance": {"type": "number"},
    "total_debits": {"type": "number"},
    "total_credits": {"type": "number"},
    "transaction_count": {"type": "integer"},
    "delta_cents": {"type": "integer"},
    "tolerance_cents": {"type": "integer"},
    "within_tolerance": {"type": "boolean"},
    "running_balance_check": {
      "type": "object",
      "properties": {
        "performed": {"type": "boolean"},
        "passed": {"type": "boolean"},
        "discontinuities": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "row_id": {"type": "string"},
              "expected": {"type": "number"},
              "actual": {"type": "number"}
            }
          }
        }
      }
    },
    "override": {
      "type": "object",
      "properties": {
        "overridden": {"type": "boolean"},
        "reason": {"type": "string"},
        "overridden_by": {"type": "string"},
        "overridden_at": {"type": "string", "format": "date-time"}
      }
    },
    "notes": {"type": "string"},
    "reconciled_at": {"type": "string", "format": "date-time"}
  },
  "additionalProperties": false
}
```

---

## 10. Final Transactions Schema

**File:** `final_transactions.json`

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "FinalTransactions",
  "type": "object",
  "required": [
    "statement_id",
    "transactions",
    "source",
    "finalized_at"
  ],
  "properties": {
    "statement_id": {"type": "string"},
    "transactions": {
      "type": "array",
      "items": {
        "$ref": "#/definitions/transaction"
      }
    },
    "source": {
      "type": "object",
      "required": ["raw_transactions_id"],
      "properties": {
        "raw_transactions_id": {"type": "string"},
        "correction_overlay_id": {"type": ["string", "null"]},
        "corrections_applied": {"type": "integer", "default": 0}
      }
    },
    "summary": {
      "type": "object",
      "properties": {
        "total_transactions": {"type": "integer"},
        "total_debits": {"type": "number"},
        "total_credits": {"type": "number"},
        "net_change": {"type": "number"}
      }
    },
    "finalized_at": {"type": "string", "format": "date-time"}
  },
  "definitions": {
    "transaction": {
      "type": "object",
      "required": ["row_id", "posted_date", "description", "amount", "provenance"],
      "properties": {
        "row_id": {"type": "string"},
        "posted_date": {"type": "string", "format": "date"},
        "description": {"type": "string"},
        "amount": {"type": "number"},
        "balance": {"type": ["number", "null"]},
        "provenance": {"type": "object"},
        "correction_source": {
          "type": "string",
          "enum": ["original", "edited", "added", "merged"]
        }
      }
    }
  },
  "additionalProperties": false
}
```

---

## 11. Extraction Error Schema

**File:** `extraction_error.json`

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "ExtractionError",
  "type": "object",
  "required": [
    "statement_id",
    "error_code",
    "error_category",
    "message",
    "occurred_at"
  ],
  "properties": {
    "statement_id": {"type": "string"},
    "error_code": {
      "type": "string",
      "pattern": "^E[0-9]{4}$"
    },
    "error_category": {
      "type": "string",
      "enum": ["VALIDATION", "TRANSIENT", "EXTRACTION", "RECONCILIATION", "CONFIGURATION", "SYSTEM"]
    },
    "message": {"type": "string"},
    "details": {
      "type": "object",
      "additionalProperties": true
    },
    "template_id": {"type": "string"},
    "method_attempted": {"type": "string"},
    "page": {"type": "integer"},
    "recoverable": {"type": "boolean"},
    "suggested_actions": {
      "type": "array",
      "items": {"type": "string"}
    },
    "stack_trace": {"type": "string"},
    "occurred_at": {"type": "string", "format": "date-time"}
  },
  "additionalProperties": false
}
```

---

## 12. Pipeline State Schema

**File:** `pipeline_state.json`

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "PipelineState",
  "type": "object",
  "required": [
    "statement_id",
    "current_state",
    "state_history",
    "updated_at"
  ],
  "properties": {
    "statement_id": {"type": "string"},
    "current_state": {
      "type": "string",
      "enum": [
        "UPLOADED",
        "INGESTED",
        "CLASSIFIED",
        "ROUTED",
        "TEMPLATE_SELECTED",
        "TEMPLATE_MISSING",
        "TEMPLATE_DRAFTED",
        "TEMPLATE_REVIEW",
        "TEMPLATE_REVIEW_FAILED",
        "TEMPLATE_APPROVED",
        "EXTRACTION_READY",
        "EXTRACTING",
        "EXTRACTION_FAILED",
        "RECONCILING",
        "RECONCILIATION_FAILED",
        "HUMAN_REVIEW_REQUIRED",
        "COMPLETED"
      ]
    },
    "state_history": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["state", "entered_at"],
        "properties": {
          "state": {"type": "string"},
          "entered_at": {"type": "string", "format": "date-time"},
          "exited_at": {"type": ["string", "null"], "format": "date-time"},
          "duration_ms": {"type": ["integer", "null"]},
          "trigger": {"type": "string"},
          "metadata": {"type": "object"}
        },
        "additionalProperties": false
      }
    },
    "artifacts": {
      "type": "object",
      "properties": {
        "ingest_receipt": {"type": "string"},
        "classification": {"type": "string"},
        "route_decision": {"type": "string"},
        "ocr_result": {"type": "string"},
        "extraction_result": {"type": "string"},
        "transactions": {"type": "string"},
        "reconciliation": {"type": "string"},
        "final_transactions": {"type": "string"},
        "correction_overlay": {"type": "string"}
      },
      "additionalProperties": true
    },
    "template_binding": {
      "type": "object",
      "properties": {
        "template_id": {"type": "string"},
        "template_version": {"type": "string"},
        "bound_at": {"type": "string", "format": "date-time"}
      }
    },
    "error": {
      "type": "object",
      "properties": {
        "code": {"type": "string"},
        "message": {"type": "string"},
        "occurred_at": {"type": "string", "format": "date-time"}
      }
    },
    "retry_count": {"type": "integer", "default": 0},
    "created_at": {"type": "string", "format": "date-time"},
    "updated_at": {"type": "string", "format": "date-time"}
  },
  "additionalProperties": false
}
```

---

## Validation Enforcement

- FastAPI MUST validate incoming and outgoing JSON against these schemas
- Background workers MUST validate artifacts before persisting
- LLM outputs MUST be post-validated and rejected on failure
- UI MUST NOT render invalid artifacts
- State Controller MUST verify required artifacts exist and validate before transitions

**Schema validation failures are hard errors and must block state transitions.**

---

## Schema Versioning

Schemas are versioned alongside the system:

- Schema version: `2.0.0`
- Breaking changes require major version bump
- Additive changes (new optional fields) are minor version

All artifacts include implicit schema version based on system version at creation time.

---

End of Runtime JSON Schemas v2.0
