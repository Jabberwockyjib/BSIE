# Product Requirements Document (PRD) v2.0

## Product Name

Bank Statement Intelligence Engine (BSIE)

---

## Purpose & Vision

The Bank Statement Intelligence Engine (BSIE) is a local-first, auditable, deterministic document intelligence system designed to ingest bank-generated PDF statements (checking, savings, credit card; personal and business), extract transactions into a searchable database, and retain full traceability back to the original PDF at the field level.

The system is designed to be:

- **Court-grade defensible** (immutable originals, provenance pointers)
- **Change-resilient** (bank layouts change without breaking the system)
- **LLM-assisted but not LLM-dependent** (LLMs propose, deterministic code executes)
- **Extensible** across banks, statement types, and time

The system will be implemented as a local FastAPI backend callable by a Next.js web application.

---

## Non-Goals

- No direct CSV ingestion as a primary source of truth
- No cloud-only dependency (cloud LLMs may be optional, never required)
- No opaque "AI-only" extraction without reconciliation and provenance
- No modification of original uploaded PDFs

---

## Primary Users

### Internal / Power Users

- Financial analysts
- Receivers / trustees
- Accountants
- Investigators / auditors
- Developers extending adapters

### External / Review Users

- Legal teams
- Clients reviewing extracted data
- Stakeholders validating transaction accuracy

---

## Core Principles (Hard Requirements)

1. **Immutable Evidence**
   - Original PDFs are stored unchanged
   - All derived artifacts reference originals

2. **Deterministic Extraction**
   - LLMs never output transactions directly
   - LLMs generate templates, routing decisions, or repair suggestions only

3. **Full Provenance**
   - Every extracted field (date, amount, description, balance) must reference:
     - page number
     - bounding box
     - source document

4. **Reconciliation-Gated Correctness**
   - Extraction is not considered valid unless balances reconcile within tolerance

5. **Repeatability**
   - Templates must work across multiple statements
   - Versioned templates are never silently changed

---

## High-Level Architecture

### Backend

- Python FastAPI application
- Local execution environment
- Background workers for heavy processing

### Frontend

- Next.js web application
- Upload, review, visualization, and correction UI

### Supporting Services (Local)

- OCRmyPDF + Tesseract (OCR lane)
- pdfplumber / Camelot / Tabula (parsing lane)
- Postgres (metadata, state, transactions)
- Object storage (original PDFs, renders, artifacts)
- Redis (job queue)

---

## Data Standards

| Purpose | Format |
|---------|--------|
| Configuration & Templates | TOML only |
| Runtime Artifacts & Results | JSON only |

No YAML, no ad-hoc formats.

---

## Phased Implementation

### Phase 1: MVP — Manual Template Pipeline (This Release)

**Goal:** Prove the extraction pipeline works end-to-end with hand-crafted templates.

**Scope:**

- Manual template creation by developers
- Template validation and execution
- Full extraction pipeline with provenance
- Reconciliation engine
- Human review UI for corrections
- 2-3 bank templates (hand-crafted)

**Explicitly Out of Scope for Phase 1:**

- LLM-generated templates
- Template Builder Agent
- Dual VLLM Review Loop
- Automatic template creation workflow
- Multi-tenant deployment

**Success Criteria:**

- Process 100 statements with hand-crafted templates
- Reconciliation pass rate ≥ 95%
- Full provenance on 100% of extracted fields
- Human review UI functional

---

### Phase 2: Assisted Template Creation

**Goal:** Introduce LLM assistance for template drafting with human approval.

**Scope:**

- Template Builder Agent (LLM-assisted draft generation)
- Single VLLM reviewer (human approval required)
- Template suggestion UI
- Semi-automated template workflow

---

### Phase 3: Autonomous Template Pipeline

**Goal:** Full automation with dual VLLM review and minimal human intervention.

**Scope:**

- Dual VLLM Review Loop
- Automatic template promotion
- Template regression testing
- Confidence-based routing

---

### Phase 4: Scale & Operations

**Goal:** Production-ready multi-user deployment.

**Scope:**

- Multi-tenant deployment
- Role-based access control
- OFX/QFX corroboration
- Metrics dashboard
- Automated regression testing

---

## Phase 1 End-to-End Workflow

### 1. PDF Upload (Ingest)

**Input:** Bank-generated PDF statement

**System Actions:**

- Store original PDF immutably
- Compute SHA-256 hash
- Assign statement_id
- Record page count and metadata

**Output Artifact:** `ingest_receipt.json`

**State Transition:** `UPLOADED` → `INGESTED`

---

### 2. Classification

**Goal:** Determine routing metadata.

**Inputs:**

- Page 1 rendered image
- Embedded PDF text (if present)
- PDF metadata

**Outputs (`classification.json`):**

- bank_family
- statement_type (checking | savings | credit_card)
- segment (personal | business | unknown)
- layout_fingerprint
- candidate_templates[]
- confidence

**Performance:** Must complete in <2 seconds (synchronous).

**State Transition:** `INGESTED` → `CLASSIFIED`

---

### 3. Routing (Phase 1: Manual Only)

**Logic:**

- Match classification against registered templates
- If matching template exists with confidence ≥ threshold → select it
- Otherwise → `TEMPLATE_MISSING` (requires manual template creation)

**Output:** `route_decision.json`

**State Transitions:**

- `CLASSIFIED` → `ROUTED`
- `ROUTED` → `TEMPLATE_SELECTED` (match found)
- `ROUTED` → `TEMPLATE_MISSING` (no match — manual intervention required)

---

### 4. Template Selection

**Phase 1 Behavior:**

- Only pre-registered stable templates are available
- No automatic template generation
- `TEMPLATE_MISSING` requires developer to create template manually

**State Transition:** `TEMPLATE_SELECTED` → `EXTRACTION_READY`

---

### 5. Deterministic Extraction

**Inputs:**

- Approved template (TOML)
- Working PDF (OCR if needed)

**Steps:**

1. OCR (if required) — store as immutable artifact
2. Table extraction using ordered methods
3. Row normalization
4. Multiline stitching
5. Sign normalization
6. Provenance attachment

**Outputs:**

- `ocr_result.json` (if OCR performed)
- `extraction_result.json`
- `transactions.json`

**State Transitions:**

- `EXTRACTION_READY` → `EXTRACTING`
- `EXTRACTING` → `RECONCILING` (success)
- `EXTRACTING` → `EXTRACTION_FAILED` (failure)

---

### 6. Reconciliation

**Checking / Savings:**

Beginning balance + Σ transactions ≈ Ending balance

**Credit Cards:**

Previous balance + charges + fees − payments ≈ New balance

**Tolerance:** Configurable per template, default ≤ $0.02

**Outputs:**

- `reconciliation.json`

**State Transitions:**

- `RECONCILING` → `COMPLETED` (pass)
- `RECONCILING` → `RECONCILIATION_FAILED` (fail)

---

### 7. Human Review (Phase 1)

**Trigger Conditions:**

- `EXTRACTION_FAILED`
- `RECONCILIATION_FAILED`
- `TEMPLATE_MISSING`

**Capabilities:**

- View PDF with bounding box overlays
- Edit extracted transactions
- Add/remove rows
- Override reconciliation
- Request template modification

**Outputs:**

- `correction_overlay.json`
- `human_review_decision.json`

**State Transitions:**

- `HUMAN_REVIEW_REQUIRED` → `COMPLETED` (manual override)
- `HUMAN_REVIEW_REQUIRED` → `EXTRACTION_READY` (retry with corrections)

---

## Template Requirements (Phase 1)

Templates must be:

- Written in TOML
- Fully declarative
- Deterministic
- Hand-crafted by developers

Each template must define:

- Detection rules
- Preprocessing rules (OCR or not)
- Table region strategy
- Extraction method order
- Column mappings
- Parsing rules
- Normalization rules
- Provenance requirements
- Reconciliation strategy

Templates may not:

- Contain executable code
- Depend on global state
- Assume fixed page counts

---

## Provenance Model (Hard Requirement)

Every extracted field must reference:

- Source PDF (original or derived)
- Page number
- Bounding box (normalized to PDF coordinate space)
- Extraction method
- Confidence score

Extractions without provenance are invalid.

---

## Error Handling & Human Review

The system must surface:

- Bounding box overlays on PDF renders
- Extracted row previews
- Reconciliation deltas
- Field-level confidence indicators

Human edits:

- Never overwrite raw extraction
- Are stored as overlay artifacts
- Are fully auditable

---

## Performance Targets

| Operation | Target | Mode |
|-----------|--------|------|
| Classification | < 2 seconds | Synchronous |
| OCR | < 1 sec/page (average) | Async (queued) |
| Extraction | < 5 seconds/statement | Async (queued) |
| Reconciliation | < 1 second | Synchronous |
| UI feedback | Every state change | WebSocket push |

---

## Security & Audit

- No outbound network calls required
- Optional cloud LLM usage must be explicit (Phase 2+)
- All artifacts versioned
- Full audit trail from transaction → PDF → upload

---

## Phase 1 MVP Scope Summary

| Feature | Included | Notes |
|---------|----------|-------|
| PDF upload & storage | ✅ | Immutable storage |
| Classification | ✅ | Rule-based + heuristics |
| Manual templates | ✅ | Developer-created TOML |
| Template execution | ✅ | Deterministic extraction |
| Provenance tracking | ✅ | Field-level |
| Reconciliation | ✅ | Balance matching |
| Human review UI | ✅ | Correction overlays |
| Transaction search | ✅ | Basic queries |
| Export (JSON/CSV) | ✅ | With provenance |
| LLM template generation | ❌ | Phase 2 |
| VLLM review loop | ❌ | Phase 3 |
| Multi-tenant | ❌ | Phase 4 |
| RBAC | ❌ | Phase 4 |

---

## Success Criteria (Phase 1)

The system is successful if:

- Transactions can be searched and exported
- Every number can be traced to its source PDF location
- Hand-crafted templates process statements correctly
- Human review workflow is functional
- Reconciliation catches extraction errors

---

## Resolved Decisions

| Decision | Resolution | Rationale |
|----------|------------|-----------|
| Template storage | Git-backed (files) + Postgres (metadata) | Audit trail via Git, queries via Postgres |
| Confidence scoring | Heuristic weights (Phase 1), ML calibration (Phase 2+) | Simpler MVP |
| Human review escalation | Any failure → human review (Phase 1) | Conservative approach |
| Initial bank support | Chase, Bank of America, American Express | Common formats, good coverage |
| Bounding box reference | Original PDF coordinate space | Before OCR transforms |

---

## Open Decisions (Phase 2+)

- LLM model selection for Template Builder Agent
- VLLM reviewer prompt engineering
- Template promotion threshold (N statements)
- Automatic retry limits

---

End of PRD v2.0
