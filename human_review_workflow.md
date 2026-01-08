# Human Review Workflow Specification

## Purpose

This document defines the authoritative specification for human review workflows in the Bank Statement Intelligence Engine (BSIE).

Human review is a critical safety mechanism that preserves auditability while allowing manual intervention when automated processing fails or requires oversight.

---

## Core Principles

1. **Explicit, Not Implicit** — Human changes are always recorded as overlay artifacts
2. **Non-Destructive** — Raw extraction data is never modified
3. **Auditable** — All changes include who, when, what, and why
4. **Reversible** — Corrections can be undone by removing the overlay
5. **Bounded** — Clear scope of what humans can and cannot change

---

## Trigger Conditions

Human review is required when:

| Trigger | State Transition | Priority |
|---------|------------------|----------|
| Extraction failure after retries | `EXTRACTION_FAILED` → `HUMAN_REVIEW_REQUIRED` | High |
| Reconciliation failure | `RECONCILIATION_FAILED` → `HUMAN_REVIEW_REQUIRED` | High |
| No matching template | `TEMPLATE_MISSING` → `HUMAN_REVIEW_REQUIRED` | Medium |
| Low confidence classification | `CLASSIFIED` (confidence < 0.60) | Medium |
| Template review failure (Phase 2+) | `TEMPLATE_REVIEW_FAILED` (max retries) | Medium |
| User-initiated review | Any state → `HUMAN_REVIEW_REQUIRED` | Low |

---

## Human Review States

### HUMAN_REVIEW_REQUIRED

**Entry Conditions:**

- Automated processing failed or flagged
- Previous state recorded for context

**Available Actions:**

- View full context
- Edit transactions
- Override reconciliation
- Request reprocessing
- Assign to another reviewer
- Escalate/reject

**Exit Transitions:**

- → `COMPLETED` (manual approval)
- → `EXTRACTION_READY` (request reprocessing with hints)
- → `TEMPLATE_DRAFTED` (Phase 2+: trigger template repair)

---

## Review Context Bundle

When a statement enters `HUMAN_REVIEW_REQUIRED`, the system assembles a complete context bundle:

### Context Bundle Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "HumanReviewContext",
  "type": "object",
  "required": [
    "statement_id",
    "review_id",
    "trigger_reason",
    "previous_state",
    "created_at"
  ],
  "properties": {
    "statement_id": {"type": "string"},
    "review_id": {"type": "string"},
    "trigger_reason": {
      "type": "string",
      "enum": [
        "extraction_failed",
        "reconciliation_failed",
        "template_missing",
        "low_confidence",
        "template_review_failed",
        "user_initiated"
      ]
    },
    "previous_state": {"type": "string"},
    "created_at": {"type": "string", "format": "date-time"},
    "classification": {"$ref": "#/definitions/classification"},
    "extraction_result": {"$ref": "#/definitions/extraction_result"},
    "reconciliation_result": {"$ref": "#/definitions/reconciliation_result"},
    "pdf_renders": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "page": {"type": "integer"},
          "image_path": {"type": "string"},
          "thumbnail_path": {"type": "string"}
        }
      }
    },
    "template_used": {
      "type": "object",
      "properties": {
        "template_id": {"type": "string"},
        "version": {"type": "string"}
      }
    },
    "error_details": {
      "type": "object",
      "properties": {
        "error_code": {"type": "string"},
        "error_message": {"type": "string"},
        "stack_trace": {"type": "string"}
      }
    },
    "prior_reviews": {
      "type": "array",
      "items": {"$ref": "#/definitions/review_summary"}
    }
  },
  "additionalProperties": false
}
```

---

## Correction Types

### 1. Transaction Field Edit

Edit a specific field in an extracted transaction.

```json
{
  "correction_type": "field_edit",
  "row_id": "txn_row_15",
  "field": "amount",
  "original_value": -125.50,
  "corrected_value": -152.50,
  "reason": "OCR misread 5 as 2"
}
```

### 2. Transaction Row Delete

Remove an incorrectly extracted row.

```json
{
  "correction_type": "row_delete",
  "row_id": "txn_row_23",
  "reason": "Row is actually a subtotal, not a transaction"
}
```

### 3. Transaction Row Add

Add a missing transaction.

```json
{
  "correction_type": "row_add",
  "row_id": "txn_row_manual_1",
  "transaction": {
    "posted_date": "2024-01-15",
    "description": "TRANSFER FROM SAVINGS",
    "amount": 500.00,
    "balance": 1234.56
  },
  "insert_after": "txn_row_14",
  "reason": "Transaction was missed by extraction",
  "provenance": {
    "page": 2,
    "bbox_normalized": [0.05, 0.45, 0.95, 0.47],
    "source": "manual_entry"
  }
}
```

### 4. Row Merge

Combine split rows that should be one transaction.

```json
{
  "correction_type": "row_merge",
  "source_rows": ["txn_row_16", "txn_row_17"],
  "merged_transaction": {
    "posted_date": "2024-01-18",
    "description": "PAYPAL *MERCHANT NAME LONGER THAN ONE LINE",
    "amount": -45.99,
    "balance": 1188.57
  },
  "reason": "Multi-line description was split incorrectly"
}
```

### 5. Row Split

Split a merged row into separate transactions.

```json
{
  "correction_type": "row_split",
  "source_row": "txn_row_20",
  "split_transactions": [
    {
      "posted_date": "2024-01-20",
      "description": "AMAZON.COM",
      "amount": -29.99,
      "balance": null
    },
    {
      "posted_date": "2024-01-20",
      "description": "AMAZON PRIME",
      "amount": -14.99,
      "balance": 1143.59
    }
  ],
  "reason": "Two transactions were merged into one row"
}
```

### 6. Balance Override

Override the reconciliation result.

```json
{
  "correction_type": "balance_override",
  "override_type": "accept_delta",
  "expected_balance": 1234.56,
  "calculated_balance": 1234.54,
  "delta_cents": 2,
  "reason": "Rounding difference acceptable"
}
```

### 7. Classification Override

Correct the classification.

```json
{
  "correction_type": "classification_override",
  "field": "statement_type",
  "original_value": "checking",
  "corrected_value": "savings",
  "reason": "Misclassified savings account statement"
}
```

---

## Correction Overlay Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "CorrectionOverlay",
  "type": "object",
  "required": [
    "overlay_id",
    "statement_id",
    "review_id",
    "reviewer",
    "corrections",
    "created_at"
  ],
  "properties": {
    "overlay_id": {
      "type": "string",
      "description": "Unique identifier for this overlay"
    },
    "statement_id": {"type": "string"},
    "review_id": {"type": "string"},
    "reviewer": {
      "type": "object",
      "required": ["user_id", "name"],
      "properties": {
        "user_id": {"type": "string"},
        "name": {"type": "string"},
        "email": {"type": "string"}
      }
    },
    "corrections": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["correction_id", "correction_type", "reason"],
        "properties": {
          "correction_id": {"type": "string"},
          "correction_type": {
            "type": "string",
            "enum": [
              "field_edit",
              "row_delete",
              "row_add",
              "row_merge",
              "row_split",
              "balance_override",
              "classification_override"
            ]
          },
          "reason": {"type": "string", "minLength": 10},
          "row_id": {"type": "string"},
          "field": {"type": "string"},
          "original_value": {},
          "corrected_value": {},
          "transaction": {"type": "object"},
          "source_rows": {"type": "array", "items": {"type": "string"}},
          "provenance": {"type": "object"}
        },
        "additionalProperties": false
      }
    },
    "created_at": {"type": "string", "format": "date-time"},
    "notes": {"type": "string"}
  },
  "additionalProperties": false
}
```

---

## Human Review Decision Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "HumanReviewDecision",
  "type": "object",
  "required": [
    "decision_id",
    "review_id",
    "statement_id",
    "decision",
    "reviewer",
    "decided_at"
  ],
  "properties": {
    "decision_id": {"type": "string"},
    "review_id": {"type": "string"},
    "statement_id": {"type": "string"},
    "decision": {
      "type": "string",
      "enum": [
        "approve",
        "approve_with_corrections",
        "reject",
        "request_reprocessing",
        "escalate"
      ]
    },
    "reviewer": {
      "type": "object",
      "required": ["user_id", "name"],
      "properties": {
        "user_id": {"type": "string"},
        "name": {"type": "string"}
      }
    },
    "correction_overlay_id": {
      "type": "string",
      "description": "Reference to corrections if decision is approve_with_corrections"
    },
    "reprocessing_hints": {
      "type": "object",
      "description": "Hints for reprocessing if decision is request_reprocessing",
      "properties": {
        "suggested_template": {"type": "string"},
        "bbox_adjustments": {"type": "array"},
        "extraction_method_override": {"type": "string"}
      }
    },
    "rejection_reason": {
      "type": "string",
      "description": "Required if decision is reject"
    },
    "escalation_reason": {
      "type": "string",
      "description": "Required if decision is escalate"
    },
    "decided_at": {"type": "string", "format": "date-time"},
    "time_spent_seconds": {"type": "integer"}
  },
  "additionalProperties": false
}
```

---

## UI Requirements

### Review Queue View

Display list of statements awaiting review:

- Statement ID and upload date
- Trigger reason with icon
- Priority indicator
- Time in queue
- Assigned reviewer (if any)
- Quick preview thumbnail

### Review Detail View

#### Left Panel: PDF Viewer

- Page navigation
- Zoom controls
- Bounding box overlays (toggle)
- Highlight extracted regions
- Click-to-select rows

#### Center Panel: Transaction Table

- Editable transaction grid
- Row status indicators (original/edited/added/deleted)
- Inline validation
- Diff view (original vs corrected)

#### Right Panel: Context

- Classification summary
- Reconciliation status
- Error details
- Prior review history
- Quick actions

### Required UI Components

```typescript
interface ReviewUIComponents {
  // PDF Viewer
  PDFViewer: {
    pages: PDFPage[];
    currentPage: number;
    zoom: number;
    overlays: BoundingBoxOverlay[];
    onRegionSelect: (bbox: BBox) => void;
  };
  
  // Transaction Editor
  TransactionTable: {
    rows: TransactionRow[];
    editableFields: string[];
    onFieldEdit: (rowId: string, field: string, value: any) => void;
    onRowDelete: (rowId: string) => void;
    onRowAdd: (insertAfter: string) => void;
  };
  
  // Reconciliation Panel
  ReconciliationPanel: {
    expected: number;
    calculated: number;
    delta: number;
    status: 'pass' | 'fail' | 'overridden';
    onOverride: (reason: string) => void;
  };
  
  // Decision Controls
  DecisionControls: {
    onApprove: () => void;
    onApproveWithCorrections: () => void;
    onReject: (reason: string) => void;
    onRequestReprocessing: (hints: ReprocessingHints) => void;
  };
}
```

---

## Workflow State Machine

```
┌─────────────────────────────────────────────────────────────┐
│                   HUMAN_REVIEW_REQUIRED                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────┐     ┌──────────┐     ┌──────────────────┐   │
│  │ QUEUED   │────▶│ ASSIGNED │────▶│ IN_REVIEW        │   │
│  └──────────┘     └──────────┘     └──────────────────┘   │
│       │                                    │               │
│       │                                    ▼               │
│       │                           ┌──────────────────┐    │
│       │                           │ DECISION_PENDING │    │
│       │                           └──────────────────┘    │
│       │                                    │               │
│       ▼                                    ▼               │
│  ┌──────────┐                     ┌──────────────────┐    │
│  │ EXPIRED  │                     │ Decision Made    │    │
│  └──────────┘                     └──────────────────┘    │
│                                            │               │
└────────────────────────────────────────────┼───────────────┘
                                             │
                    ┌────────────────────────┼────────────────────────┐
                    │                        │                        │
                    ▼                        ▼                        ▼
            ┌──────────────┐        ┌──────────────┐        ┌──────────────┐
            │  COMPLETED   │        │ EXTRACTION_  │        │  ESCALATED   │
            │              │        │    READY     │        │              │
            └──────────────┘        └──────────────┘        └──────────────┘
```

---

## Final Transactions Merge Logic

When corrections are applied, `final_transactions.json` is generated:

```python
def merge_transactions(
    raw_transactions: List[Transaction],
    overlay: CorrectionOverlay
) -> List[Transaction]:
    """
    Merge raw extraction with human corrections.
    Overlay takes precedence for any conflicts.
    """
    result = []
    deleted_ids = set()
    merged_ids = set()
    
    # Index corrections by type
    corrections_by_row = defaultdict(list)
    for correction in overlay.corrections:
        if correction.row_id:
            corrections_by_row[correction.row_id].append(correction)
        if correction.correction_type == "row_delete":
            deleted_ids.add(correction.row_id)
        if correction.correction_type == "row_merge":
            merged_ids.update(correction.source_rows)
    
    # Process each raw transaction
    for txn in raw_transactions:
        if txn.row_id in deleted_ids:
            continue  # Skip deleted rows
        
        if txn.row_id in merged_ids:
            continue  # Skip merged source rows (merged result added separately)
        
        # Apply field edits
        modified_txn = txn.copy()
        for correction in corrections_by_row.get(txn.row_id, []):
            if correction.correction_type == "field_edit":
                setattr(modified_txn, correction.field, correction.corrected_value)
            elif correction.correction_type == "row_split":
                # Replace with split transactions
                result.extend(correction.split_transactions)
                modified_txn = None
                break
        
        if modified_txn:
            result.append(modified_txn)
    
    # Add new rows and merged rows
    for correction in overlay.corrections:
        if correction.correction_type == "row_add":
            result.append(correction.transaction)
        elif correction.correction_type == "row_merge":
            result.append(correction.merged_transaction)
    
    # Sort by date and insert position
    result.sort(key=lambda t: (t.posted_date, t.row_id))
    
    return result
```

---

## Audit Trail

Every human review action is logged:

```json
{
  "audit_id": "audit_xyz789",
  "timestamp": "2024-01-15T10:30:00Z",
  "actor": {
    "user_id": "user_123",
    "name": "John Reviewer",
    "ip_address": "192.168.1.100"
  },
  "action": "correction_added",
  "resource": {
    "type": "statement",
    "id": "stmt_abc123"
  },
  "details": {
    "correction_type": "field_edit",
    "row_id": "txn_row_15",
    "field": "amount",
    "before": -125.50,
    "after": -152.50
  }
}
```

---

## Access Control (Phase 4)

### Roles

| Role | Permissions |
|------|-------------|
| Viewer | View statements, view corrections |
| Reviewer | All Viewer + make corrections, approve |
| Senior Reviewer | All Reviewer + override reconciliation, escalate |
| Admin | All permissions + user management |

### Permissions Matrix

| Action | Viewer | Reviewer | Senior | Admin |
|--------|--------|----------|--------|-------|
| View review queue | ✓ | ✓ | ✓ | ✓ |
| Claim review | ✗ | ✓ | ✓ | ✓ |
| Edit transactions | ✗ | ✓ | ✓ | ✓ |
| Approve | ✗ | ✓ | ✓ | ✓ |
| Override reconciliation | ✗ | ✗ | ✓ | ✓ |
| Reject statement | ✗ | ✗ | ✓ | ✓ |
| Manage users | ✗ | ✗ | ✗ | ✓ |

---

## Performance Requirements

| Metric | Target |
|--------|--------|
| Context bundle load | < 3 seconds |
| PDF page render | < 500ms |
| Correction save | < 1 second |
| Decision submit | < 2 seconds |
| Concurrent reviewers | 10+ |

---

End of Human Review Workflow Specification
