# Next Sprint: Sprint 4 - Template Registry

## Project Status

**BSIE (Bank Statement Intelligence Engine)** - Local-first document intelligence system for extracting transactions from bank statement PDFs.

### Completed Sprints

| Sprint | Name | Tasks | Status |
|--------|------|-------|--------|
| 1 | Project Foundation | 18 | ✅ Complete |
| 2 | Schema Validation | 14 | ✅ Complete |
| 3 | State Controller | 18 | ✅ Complete |

**Total tests passing:** 108

### Sprint 3 Deliverables (Just Completed)

- `src/bsie/state/` - Full StateController implementation
  - State enum with 13 MVP states
  - Transition matrix validation
  - Required artifact checking
  - State history audit trail
  - Optimistic locking
  - Admin force_transition
  - Template binding on TEMPLATE_SELECTED
  - Error tracking on failure states
  - Timeout detection

---

## Sprint 4: Template Registry (16 tasks)

**Goal:** Implement Git+Postgres hybrid template storage with TOML parsing and validation.

**Milestone:** Templates loadable from filesystem, metadata queryable from Postgres, version tracking working.

### Reference Documents
- `/Users/brian/dev/BSIE/docs/plans/2026-01-08-p0-implementation.md` (line ~5090)
- `/Users/brian/dev/BSIE/template_adapter_v2.md`
- `/Users/brian/dev/BSIE/decisions_v2.md`

### Key Architecture Points
- Templates stored as TOML files in Git
- Metadata indexed in Postgres for querying
- Templates are version-bound to statements permanently
- Template status: draft → candidate → stable

### Sprint 4 Tasks Preview

1. **Task 4.1:** Create Template Database Model
2. **Task 4.2:** Create TOML Schema Definition
3. **Task 4.3:** Implement TOML Parser
4. **Task 4.4:** Create Template Registry Core
5. **Task 4.5:** Implement Template Loading
6. **Task 4.6:** Add Template Validation
7. **Task 4.7:** Implement Template Lookup by Bank
8. **Task 4.8:** Add Template Version Management
9. **Task 4.9:** Implement Template Caching
10. **Task 4.10:** Add Template Status Transitions
11. **Task 4.11:** Create Template Indexer
12. **Task 4.12:** Add Git SHA Tracking
13. **Task 4.13:** Implement Template Search
14. **Task 4.14:** Add Template Export
15. **Task 4.15:** Create Template Dependencies
16. **Task 4.16:** Run Full Test Suite

---

## How to Start

1. Read the implementation plan:
   ```
   Read /Users/brian/dev/BSIE/docs/plans/2026-01-08-p0-implementation.md
   ```
   Start at line ~5090 for Sprint 4 details.

2. Use the executing-plans skill:
   ```
   /superpowers:execute-plan sprint 4
   ```

3. Or manually start with Task 4.1 following TDD pattern:
   - Write failing test
   - Run test to verify failure
   - Write minimal implementation
   - Run test to verify pass
   - Commit

---

## Quick Commands

```bash
# Run all tests
python -m pytest tests/ -v

# Run state tests only
python -m pytest tests/state/ -v

# Check test count
python -m pytest tests/ --collect-only | tail -1
```

---

## Existing Patterns to Follow

- **Models:** `src/bsie/db/models/` - SQLAlchemy 2.0 async
- **Schemas:** `src/bsie/schemas/` - Pydantic v2 with strict mode
- **State:** `src/bsie/state/` - Centralized state controller
- **Tests:** `tests/` - pytest with async fixtures
