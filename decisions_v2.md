# Locked Architectural Decisions v2.0

## Purpose

This document records explicit, irreversible architectural decisions for the Bank Statement Intelligence Engine (BSIE).

These decisions eliminate ambiguity, prevent architectural drift, and serve as binding constraints for all implementation work. Any change to these decisions requires a formal design review and versioned amendment.

---

## Decision 1: State Transition Ownership

### Decision

All pipeline state transitions are owned and enforced by a single, centralized State Controller.

### Rationale

- Ensures all transitions are validated against the Pipeline State Machine
- Prevents illegal or out-of-order transitions
- Guarantees schema validation before state advancement
- Creates a single audit trail for all progress and failures

### Implications

- Workers and agents may not mutate pipeline state directly
- Workers return results and artifacts only
- The State Controller:
  - Validates artifacts against JSON schemas
  - Confirms allowed transitions
  - Records state changes atomically
  - Emits state change events for UI consumption

### Explicit Rejection

- Decentralized state transitions by workers are not allowed

---

## Decision 2: Canonical Source of Truth for Transactions

### Decision

Final transactions are materialized as a derived artifact (`final_transactions.json`).

### Definition

`final_transactions.json` is produced by a deterministic merge of:

- Raw extraction results (`transactions.json`)
- Approved human correction overlays (`correction_overlay.json`, if any)

Raw extraction artifacts are never modified or overwritten.

### Rationale

- Enables reproducible audits
- Simplifies UI rendering and exports
- Prevents ambiguity between "raw" and "final" data
- Supports downstream integrations without recomputation

### Implications

- Downstream systems MUST read from `final_transactions.json`
- Raw artifacts remain available for traceability and review
- Merge logic is deterministic and versioned

---

## Decision 3: Template Version Binding

### Decision

Each statement is permanently bound to the exact template version used during its processing.

### Rules

- Template ID and version are recorded on first successful extraction
- Statements are NOT automatically reprocessed when templates evolve
- Reprocessing requires explicit, intentional user action

### Rationale

- Guarantees reproducibility
- Prevents silent historical changes
- Supports legal defensibility and audit replay

### Implications

- Template registry must retain all historical versions
- Router must select templates without modifying prior bindings
- Template deprecation does not affect already-processed statements

---

## Decision 4: Deterministic Promotion and Immutability

### Decision

Stable templates are immutable.

### Rules

- Any change to a stable template requires a new version
- Older versions remain executable for historical statements
- Promotion to stable requires:
  - Schema validation
  - Successful extraction on ≥ 3 statements (Phase 1)
  - Reconciliation pass on all test statements
  - Provenance completeness ≥ 99%

### Rationale

- Prevents regression
- Enables controlled evolution
- Supports template-level testing and certification

---

## Decision 5: Human Review as a Controlled Override

### Decision

Human review is an explicit, stateful override—not an implicit fix.

### Rules

- Human intervention always produces an auditable overlay artifact
- Manual overrides do not erase or mutate raw extraction data
- Overrides must be explicitly acknowledged and recorded
- Override artifacts include:
  - Reviewer identity
  - Timestamp
  - Reason/justification
  - Specific changes made

### Rationale

- Maintains trust boundaries
- Preserves auditability
- Avoids silent correction bias

---

## Decision 6: Enforcement Priority Order

When evaluating any pipeline step, enforcement order is:

1. JSON schema validation
2. State transition validation
3. Provenance completeness
4. Reconciliation rules
5. Human override (if authorized)

Failure at any level blocks progression.

---

## Decision 7: Template Storage Architecture (RESOLVED)

### Decision

Templates use a hybrid storage model: Git-backed files for template content, Postgres for metadata and relationships.

### Implementation

**Git Repository (Template Content):**

- Template TOML files stored in version-controlled repository
- Each template version is a commit
- Branching for draft/candidate templates
- Tags for stable releases

**Postgres (Metadata):**

- Template registry table with:
  - template_id
  - current_version
  - status (draft | candidate | stable | deprecated)
  - git_commit_sha
  - created_at, updated_at
- Statement-template binding table
- Performance metrics per template

### Rationale

- Git provides natural versioning, diff, and audit trail
- Postgres enables fast queries and relationships
- Separation allows independent scaling

### Interface Contract

```python
class TemplateRegistry:
    def get_template(template_id: str, version: str = None) -> Template
    def list_stable_templates() -> List[TemplateMeta]
    def register_template(template: Template) -> TemplateMeta
    def promote_to_stable(template_id: str, version: str) -> None
    def deprecate(template_id: str, version: str) -> None
```

---

## Decision 8: OCR Artifact Immutability (NEW)

### Decision

OCR output is stored as an immutable artifact, separate from the extraction result.

### Rules

- OCR is performed once per PDF (unless explicitly re-requested)
- OCR output (`ocr_result.json`) includes:
  - Full text per page
  - Word-level bounding boxes
  - Confidence scores
  - Tesseract version used
- Extraction operates on OCR artifact, not raw PDF (for OCR'd documents)
- "Deterministic extraction" means deterministic given the same OCR artifact

### Rationale

- OCR can vary between Tesseract versions
- Storing OCR output enables reproducibility
- Allows debugging extraction without re-running OCR
- Enables future OCR quality improvements without invalidating past results

---

## Decision 9: Bounding Box Coordinate System (NEW)

### Decision

All bounding boxes use PDF coordinate space (points from bottom-left origin), normalized to page dimensions.

### Specification

```json
{
  "bbox": [x0, y0, x1, y1],
  "page_width": 612,
  "page_height": 792,
  "coordinate_system": "pdf_points_bottom_left"
}
```

**Normalized form (stored):**

```json
{
  "bbox_normalized": [0.05, 0.10, 0.95, 0.85],
  "reference": "pdf_page_dimensions"
}
```

### Rules

- All stored bounding boxes are normalized to [0, 1] range
- Reference is always the original PDF page dimensions
- OCR/render transforms must map back to PDF coordinates
- UI must transform for display (PDF coordinates → screen pixels)

### Rationale

- PDF coordinates are stable across renders
- Normalization enables resolution-independent storage
- Single coordinate system prevents conversion errors

---

## Decision 10: Synchronous vs Asynchronous Operations (NEW)

### Decision

Operations are explicitly categorized as synchronous or asynchronous.

### Synchronous Operations (Blocking, <2 seconds)

- Classification
- Reconciliation calculation
- Schema validation
- State transitions

### Asynchronous Operations (Queued via Redis)

- PDF ingestion and storage
- OCR processing
- Table extraction
- Human review queue management

### Implementation

- Sync operations return results directly in HTTP response
- Async operations return job_id immediately
- State changes trigger WebSocket notifications
- UI polls or subscribes for async completion

### Rationale

- Clear performance contracts
- Predictable user experience
- Scalable background processing

---

## Decision 11: Error Classification (NEW)

### Decision

All errors are classified into explicit categories that determine recovery paths.

### Error Categories

| Category | Recoverable | Auto-Retry | Human Review |
|----------|-------------|------------|--------------|
| VALIDATION_ERROR | No | No | No |
| TRANSIENT_ERROR | Yes | Yes (3x) | No |
| EXTRACTION_ERROR | Partial | No | Yes |
| RECONCILIATION_ERROR | Partial | No | Yes |
| SYSTEM_ERROR | Depends | Yes (1x) | Escalate |

### Rules

- Every error must be categorized
- Category determines state transition
- Transient errors retry automatically with backoff
- Extraction/Reconciliation errors always surface to human review
- System errors alert operations team

---

## Decision 12: API Versioning (NEW)

### Decision

API uses URL path versioning with explicit deprecation policy.

### Implementation

- Base path: `/api/v1/`
- Breaking changes require new version
- Old versions supported for 6 months after deprecation notice
- Version included in all responses

### Rationale

- Simple, explicit versioning
- Frontend can target specific versions
- Clear upgrade path

---

## Non-Negotiable Summary

- One state controller
- One canonical transaction artifact
- Immutable template bindings
- Immutable OCR artifacts
- Declarative templates only
- Human review is explicit and auditable
- Git + Postgres hybrid storage
- PDF coordinate system for bounding boxes
- Explicit sync/async boundaries
- Classified error handling

---

These decisions are final for the current system version (v2.0).

---

End of Locked Architectural Decisions v2.0
