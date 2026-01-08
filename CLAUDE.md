# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Bank Statement Intelligence Engine (BSIE) — A local-first, court-grade defensible document intelligence system for extracting transactions from bank statement PDFs with full provenance traceability.

**Current Status:** Specification documents only. Implementation not yet started.

## Key Architectural Constraints

These are locked decisions that must not be violated:

1. **Single State Controller** — All pipeline state transitions through one centralized component
2. **Immutable Artifacts** — Raw extraction data never modified; corrections stored as overlays
3. **Template Version Binding** — Statements permanently bound to template version used for extraction
4. **LLM Proposes, Code Executes** — LLMs generate templates/suggestions, deterministic code extracts data
5. **Git + Postgres Hybrid** — Templates in Git (versioned), metadata in Postgres (queryable)
6. **Provenance Required** — Every extracted field must reference page, bounding box, and source PDF

## Document Hierarchy

When specifications conflict, defer to this priority order:
1. `decisions_v2.md` — Locked architectural decisions
2. `pipeline_state_machine_v2.md` — State definitions and transitions
3. `json_schema_v2.md` — Artifact schemas
4. Other specification documents

## Technology Stack

| Component | Technology |
|-----------|------------|
| Backend | Python 3.11+, FastAPI |
| Frontend | Next.js 14, React |
| Database | PostgreSQL 15 |
| Queue | Redis 7 |
| OCR | Tesseract 5, OCRmyPDF |
| Table Extraction | Camelot, Tabula, pdfplumber |

## Configuration Formats

- **TOML** for templates and configuration (`/templates/*.toml`, `/config/`)
- **JSON** for runtime artifacts (`/artifacts/{statement_id}/*.json`)
- **No YAML** — explicitly prohibited

## Pipeline States (MVP)

```
UPLOADED → INGESTED → CLASSIFIED → ROUTED → TEMPLATE_SELECTED → EXTRACTION_READY → EXTRACTING → RECONCILING → COMPLETED
```

Error states route to `HUMAN_REVIEW_REQUIRED`. See `pipeline_state_machine_v2.md` for complete diagram.

## Error Code Ranges

| Category | Range | Behavior |
|----------|-------|----------|
| VALIDATION | E1xxx | No retry, reject |
| TRANSIENT | E2xxx | Auto-retry 3x with backoff |
| EXTRACTION | E3xxx | Human review |
| RECONCILIATION | E4xxx | Human review |
| CONFIGURATION | E5xxx | Requires fix |
| SYSTEM | E9xxx | Alert ops |

## API Base Path

`/api/v1/`

## Implementation Priority

1. **P0** — State Controller, Template Registry, Schema Validation, Ingest Pipeline
2. **P1** — Classification, Extraction Engine, Reconciliation, Human Review UI
3. **P2** — API endpoints, WebSocket notifications, Export functionality
4. **P3** — Error handling, Performance optimization, Monitoring

## Testing Requirements

- Unit test coverage ≥ 80%
- All JSON artifacts must validate against schemas before state transitions
- Templates require validation tests before promotion to stable
- Test fixtures in `fixtures/` with PDF samples and expected outputs

## Key JSON Schemas

All artifacts must validate against schemas in `json_schema_v2.md`:
- `ingest_receipt.json` — PDF ingestion metadata
- `classification.json` — Bank/type/segment classification
- `transactions.json` — Extracted transactions with provenance
- `reconciliation.json` — Balance verification result
- `final_transactions.json` — Merged raw + corrections

## Phased Implementation

- **Phase 1 (MVP):** Manual templates, full pipeline, human review
- **Phase 2:** Template Builder Agent (LLM-assisted), single reviewer
- **Phase 3:** Dual VLLM review, automatic promotion
- **Phase 4:** Multi-tenant, RBAC, OFX corroboration
