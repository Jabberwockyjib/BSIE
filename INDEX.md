# BSIE Specification Index v2.0

## Bank Statement Intelligence Engine — Architecture Documentation

This index provides navigation to all specification documents for the Bank Statement Intelligence Engine (BSIE).

---

## Document Summary

| Document | Purpose | Version |
|----------|---------|---------|
| [prd_v2.md](./prd_v2.md) | Product requirements with phased implementation | 2.0 |
| [decisions_v2.md](./decisions_v2.md) | Locked architectural decisions | 2.0 |
| [pipeline_state_machine_v2.md](./pipeline_state_machine_v2.md) | Pipeline states and transitions | 2.0 |
| [classification_pipeline.md](./classification_pipeline.md) | Classification algorithm specification | 1.0 |
| [template_adapter_v2.md](./template_adapter_v2.md) | TOML template schema | 2.0 |
| [template_builder_agent.md](./template_builder_agent.md) | LLM agent specification (Phase 2+) | 1.0 |
| [human_review_workflow.md](./human_review_workflow.md) | Human review process and UI | 1.0 |
| [json_schema_v2.md](./json_schema_v2.md) | All runtime JSON schemas | 2.0 |
| [error_taxonomy.md](./error_taxonomy.md) | Error classification and handling | 1.0 |
| [api_contract.md](./api_contract.md) | REST API specification | 1.0 |
| [testing_strategy.md](./testing_strategy.md) | Testing approach and requirements | 1.0 |
| [vllm_review_loop.md](./vllm_review_loop.md) | Dual VLLM review specification (Phase 3) | 1.0 |

---

## Quick Reference

### Phased Implementation

| Phase | Scope | Key Features |
|-------|-------|--------------|
| **Phase 1 (MVP)** | Manual Templates | Hand-crafted templates, full pipeline, human review |
| **Phase 2** | Assisted Creation | Template Builder Agent, single reviewer, human approval |
| **Phase 3** | Autonomous | Dual VLLM review, automatic promotion |
| **Phase 4** | Scale | Multi-tenant, RBAC, OFX corroboration |

### Key Architectural Decisions

1. **Single State Controller** — All state transitions through one component
2. **Immutable Artifacts** — Raw data never modified, overlays for corrections
3. **Template Version Binding** — Statements bound to specific template versions
4. **Git + Postgres Hybrid** — Templates in Git, metadata in Postgres
5. **LLM Proposes, Code Executes** — LLMs generate templates, deterministic code extracts

### State Machine Summary

```
UPLOADED → INGESTED → CLASSIFIED → ROUTED
                                      │
                    ┌─────────────────┴─────────────────┐
                    ▼                                   ▼
          TEMPLATE_SELECTED                    TEMPLATE_MISSING
                    │                                   │
                    ▼                                   ▼
          EXTRACTION_READY                    HUMAN_REVIEW_REQUIRED
                    │                                   │
                    ▼                                   │
              EXTRACTING ──────────────────────────────▶│
                    │                                   │
         ┌─────────┴─────────┐                         │
         ▼                   ▼                         │
    RECONCILING     EXTRACTION_FAILED ────────────────▶│
         │                                             │
    ┌────┴────┐                                        │
    ▼         ▼                                        │
COMPLETED  RECONCILIATION_FAILED ─────────────────────▶│
    ▲                                                  │
    └──────────────────────────────────────────────────┘
```

### JSON Artifacts

| Artifact | State Requirement |
|----------|-------------------|
| ingest_receipt.json | INGESTED |
| classification.json | CLASSIFIED |
| route_decision.json | ROUTED |
| ocr_result.json | EXTRACTION_READY (if OCR) |
| extraction_result.json | RECONCILING |
| transactions.json | RECONCILING |
| reconciliation.json | COMPLETED |
| final_transactions.json | COMPLETED |
| correction_overlay.json | After human review |

### Error Categories

| Category | Code Range | Retry | Human Review |
|----------|------------|-------|--------------|
| VALIDATION | E1xxx | No | No |
| TRANSIENT | E2xxx | Yes (3x) | No |
| EXTRACTION | E3xxx | Limited | Yes |
| RECONCILIATION | E4xxx | No | Yes |
| CONFIGURATION | E5xxx | No | No |
| SYSTEM | E9xxx | Limited | Escalate |

---

## Implementation Priorities

### P0 — Blocks All Work

- [ ] State Controller implementation
- [ ] Template registry (Git + Postgres)
- [ ] Schema validation for all artifacts
- [ ] Ingest pipeline

### P1 — Blocks Core Features

- [ ] Classification pipeline
- [ ] Deterministic extraction engine
- [ ] Reconciliation engine
- [ ] Human review UI
- [ ] 3 initial templates (Chase, BofA, Amex)

### P2 — Blocks Integration

- [ ] API implementation (FastAPI)
- [ ] WebSocket state notifications
- [ ] Transaction export (CSV, JSON)
- [ ] Test fixture library

### P3 — Production Readiness

- [ ] Error handling for all paths
- [ ] Performance optimization
- [ ] Monitoring and alerting
- [ ] Documentation

---

## Technology Stack

| Component | Technology |
|-----------|------------|
| Backend | Python 3.11+, FastAPI |
| Frontend | Next.js 14, React |
| Database | PostgreSQL 15 |
| Queue | Redis 7 |
| OCR | Tesseract 5, OCRmyPDF |
| Table Extraction | Camelot, Tabula, pdfplumber |
| Storage | Local filesystem (Phase 1), S3-compatible (Phase 4) |

---

## Configuration Formats

| Purpose | Format | Location |
|---------|--------|----------|
| Templates | TOML | `/templates/*.toml` |
| Runtime artifacts | JSON | `/artifacts/{statement_id}/*.json` |
| Classification rules | TOML | `/config/classification/` |
| Application config | TOML | `/config/app.toml` |

---

## API Base URL

```
/api/v1/
```

### Key Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | /statements | Upload PDF |
| GET | /statements/{id} | Get statement details |
| GET | /statements/{id}/transactions | Get transactions |
| GET | /reviews | List pending reviews |
| POST | /reviews/{id}/decision | Submit review decision |
| GET | /templates | List templates |

---

## Performance Targets

| Operation | Target |
|-----------|--------|
| Classification | < 2 seconds |
| OCR (per page) | < 1 second |
| Extraction (per statement) | < 5 seconds |
| Reconciliation | < 1 second |
| API response | < 200ms |

---

## Success Criteria (Phase 1)

- [ ] Process 100 statements with manual templates
- [ ] Reconciliation pass rate ≥ 95%
- [ ] 100% provenance coverage on extracted fields
- [ ] Human review workflow functional
- [ ] Export to JSON/CSV working

---

## Document Changelog

### v2.0 (Current)

- Revised MVP scope to manual templates only
- Resolved template storage decision (Git + Postgres)
- Added classification pipeline specification
- Added complete JSON schemas for all artifacts
- Added error taxonomy
- Added API contract
- Added testing strategy
- Fixed state machine orphaned transitions
- Added multi-page table handling to template schema
- Added OCR artifact immutability

### v1.0 (Original)

- Initial architecture documents
- Incomplete specifications
- Unresolved infrastructure decisions

---

## Getting Started

1. Read [prd_v2.md](./prd_v2.md) for product context
2. Review [decisions_v2.md](./decisions_v2.md) for constraints
3. Study [pipeline_state_machine_v2.md](./pipeline_state_machine_v2.md) for workflow
4. Implement State Controller first (P0)
5. Build classification pipeline
6. Create first template using [template_adapter_v2.md](./template_adapter_v2.md)
7. Test with [testing_strategy.md](./testing_strategy.md) approach

---

## Questions?

If specifications are unclear or conflicting, defer to:

1. Locked decisions (decisions_v2.md)
2. State machine (pipeline_state_machine_v2.md)
3. JSON schemas (json_schema_v2.md)

Ambiguity in other documents should be resolved by referencing these primary sources.

---

End of Specification Index
