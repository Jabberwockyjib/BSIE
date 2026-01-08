# Testing Strategy Specification

## Purpose

This document defines the authoritative testing strategy for the Bank Statement Intelligence Engine (BSIE).

For a system claiming "court-grade defensibility," comprehensive testing is not optional—it's essential to the product's core value proposition.

---

## Testing Pyramid

```
                    ┌───────────────┐
                    │   E2E Tests   │  ← Few, slow, high-value
                    │    (5-10)     │
                    ├───────────────┤
                    │  Integration  │  ← Moderate count
                    │    (50-100)   │
                    ├───────────────┤
                    │  Unit Tests   │  ← Many, fast
                    │   (500+)      │
                    └───────────────┘
```

---

## Test Categories

### 1. Unit Tests

**Scope:** Individual functions and classes in isolation

**Characteristics:**
- Fast (<100ms per test)
- No external dependencies (mocked)
- High coverage target (>80%)

**Key Areas:**

| Component | Focus |
|-----------|-------|
| Schema Validators | All JSON schema validations |
| State Machine | Transition validation logic |
| Classification Rules | Keyword matching, scoring |
| Template Parser | TOML parsing, validation |
| Extraction Methods | Row parsing, normalization |
| Reconciliation | Balance calculations |
| Provenance | Bbox calculations, normalization |

**Example Unit Tests:**

```python
# test_schema_validation.py
class TestTransactionSchema:
    def test_valid_transaction_passes(self):
        txn = {
            "row_id": "txn_1",
            "posted_date": "2024-01-15",
            "description": "DEPOSIT",
            "amount": 100.00,
            "provenance": {
                "page": 1,
                "bbox": [0.1, 0.2, 0.9, 0.3],
                "source_pdf": "stmt.pdf"
            }
        }
        assert validate_transaction(txn) is True
    
    def test_missing_required_field_fails(self):
        txn = {"row_id": "txn_1", "posted_date": "2024-01-15"}
        with pytest.raises(ValidationError):
            validate_transaction(txn)
    
    def test_bbox_out_of_range_fails(self):
        txn = valid_transaction()
        txn["provenance"]["bbox"] = [0.1, 0.2, 1.5, 0.3]  # 1.5 > 1.0
        with pytest.raises(ValidationError):
            validate_transaction(txn)


# test_reconciliation.py
class TestReconciliation:
    def test_checking_account_reconciles(self):
        result = reconcile_checking(
            beginning_balance=1000.00,
            transactions=[
                {"amount": 500.00},
                {"amount": -200.00}
            ],
            ending_balance=1300.00
        )
        assert result.status == "pass"
        assert result.delta_cents == 0
    
    def test_within_tolerance_passes(self):
        result = reconcile_checking(
            beginning_balance=1000.00,
            transactions=[{"amount": 100.00}],
            ending_balance=1100.02,
            tolerance_cents=5
        )
        assert result.status == "pass"
        assert result.delta_cents == 2
    
    def test_outside_tolerance_fails(self):
        result = reconcile_checking(
            beginning_balance=1000.00,
            transactions=[{"amount": 100.00}],
            ending_balance=1110.00,
            tolerance_cents=2
        )
        assert result.status == "fail"
        assert result.delta_cents == 1000
```

---

### 2. Integration Tests

**Scope:** Component interactions, database, external services

**Characteristics:**
- Moderate speed (100ms-5s per test)
- Real database (test instance)
- Mocked external services where appropriate

**Key Areas:**

| Integration | Focus |
|-------------|-------|
| API → Database | CRUD operations, transactions |
| State Controller → Workers | Job dispatch, completion |
| Classification → Template Registry | Template matching |
| Extraction → Storage | Artifact persistence |
| WebSocket → State Changes | Real-time updates |

**Example Integration Tests:**

```python
# test_statement_pipeline.py
class TestStatementIngestion:
    @pytest.fixture
    def test_pdf(self):
        return load_fixture("chase_checking_2024_01.pdf")
    
    async def test_upload_creates_statement(self, client, test_pdf):
        response = await client.post(
            "/api/v1/statements",
            files={"file": test_pdf}
        )
        assert response.status_code == 201
        data = response.json()["data"]
        assert data["status"] == "UPLOADED"
        assert "statement_id" in data
    
    async def test_ingestion_computes_hash(self, client, test_pdf):
        response = await client.post("/api/v1/statements", files={"file": test_pdf})
        statement_id = response.json()["data"]["statement_id"]
        
        # Wait for ingestion
        await wait_for_state(statement_id, "INGESTED")
        
        # Verify artifact
        artifact = await get_artifact(statement_id, "ingest_receipt")
        assert artifact["sha256"] == compute_sha256(test_pdf)
        assert artifact["pages"] == 5


# test_state_transitions.py
class TestStateTransitions:
    async def test_valid_transition_succeeds(self, state_controller):
        stmt = create_statement(state="UPLOADED")
        result = await state_controller.transition(
            stmt.id, 
            to_state="INGESTED",
            artifacts={"ingest_receipt": valid_receipt()}
        )
        assert result.success
        assert stmt.current_state == "INGESTED"
    
    async def test_invalid_transition_rejected(self, state_controller):
        stmt = create_statement(state="UPLOADED")
        with pytest.raises(InvalidTransitionError):
            await state_controller.transition(stmt.id, to_state="COMPLETED")
    
    async def test_missing_artifact_blocks_transition(self, state_controller):
        stmt = create_statement(state="UPLOADED")
        with pytest.raises(MissingArtifactError):
            await state_controller.transition(stmt.id, to_state="INGESTED")
```

---

### 3. End-to-End Tests

**Scope:** Complete user workflows

**Characteristics:**
- Slow (5-60s per test)
- Real system, real PDFs
- Limited count, high value

**Key Workflows:**

| Workflow | Description |
|----------|-------------|
| Happy Path | Upload → Complete with stable template |
| OCR Path | Upload scanned PDF → OCR → Extract |
| Human Review | Extraction fails → Review → Correct → Complete |
| Template Missing | No template → Manual creation → Extract |

**Example E2E Tests:**

```python
# test_e2e_workflows.py
class TestHappyPath:
    """Test complete processing with existing stable template."""
    
    @pytest.fixture
    def chase_pdf(self):
        return load_fixture("chase_checking_standard.pdf")
    
    async def test_statement_processes_successfully(self, client, chase_pdf):
        # Upload
        response = await client.post(
            "/api/v1/statements",
            files={"file": chase_pdf}
        )
        statement_id = response.json()["data"]["statement_id"]
        
        # Wait for completion (timeout: 60s)
        final_state = await wait_for_terminal_state(statement_id, timeout=60)
        assert final_state == "COMPLETED"
        
        # Verify transactions
        txn_response = await client.get(
            f"/api/v1/statements/{statement_id}/transactions"
        )
        transactions = txn_response.json()["data"]["transactions"]
        assert len(transactions) > 0
        
        # Verify reconciliation
        state = await client.get(f"/api/v1/statements/{statement_id}")
        assert state.json()["data"]["reconciliation"]["status"] == "pass"
        
        # Verify provenance
        for txn in transactions:
            assert "provenance" in txn
            assert txn["provenance"]["page"] >= 1
            assert len(txn["provenance"]["bbox"]) == 4


class TestHumanReviewWorkflow:
    """Test human review intervention."""
    
    async def test_reconciliation_failure_triggers_review(self, client):
        # Upload PDF that will fail reconciliation
        pdf = load_fixture("chase_checking_bad_ocr.pdf")
        response = await client.post("/api/v1/statements", files={"file": pdf})
        statement_id = response.json()["data"]["statement_id"]
        
        # Wait for human review state
        state = await wait_for_state(statement_id, "HUMAN_REVIEW_REQUIRED")
        assert state == "HUMAN_REVIEW_REQUIRED"
        
        # Get review
        reviews = await client.get("/api/v1/reviews?status=pending")
        review = next(r for r in reviews.json()["data"] if r["statement_id"] == statement_id)
        
        # Claim review
        await client.post(f"/api/v1/reviews/{review['review_id']}/claim")
        
        # Submit correction
        await client.post(
            f"/api/v1/reviews/{review['review_id']}/corrections",
            json={
                "corrections": [{
                    "correction_type": "field_edit",
                    "row_id": "txn_row_5",
                    "field": "amount",
                    "corrected_value": -125.00,
                    "reason": "OCR error"
                }]
            }
        )
        
        # Approve
        await client.post(
            f"/api/v1/reviews/{review['review_id']}/decision",
            json={"decision": "approve_with_corrections"}
        )
        
        # Verify completed
        final_state = await wait_for_state(statement_id, "COMPLETED")
        assert final_state == "COMPLETED"
```

---

## Test Fixtures

### PDF Fixtures

Maintain a library of test PDFs organized by:

```
fixtures/
├── pdfs/
│   ├── chase/
│   │   ├── checking/
│   │   │   ├── standard_2024_01.pdf      # Happy path
│   │   │   ├── multi_page_50_txn.pdf     # Many transactions
│   │   │   ├── scanned_low_quality.pdf   # OCR challenge
│   │   │   └── new_layout_2024.pdf       # Layout change
│   │   └── credit_card/
│   │       └── ...
│   ├── bofa/
│   │   └── ...
│   └── amex/
│       └── ...
├── templates/
│   ├── chase_checking_personal_v1.toml
│   └── ...
└── expected_outputs/
    ├── chase_checking_standard_transactions.json
    └── ...
```

### Fixture Metadata

Each PDF fixture includes metadata:

```json
{
  "fixture_id": "chase_checking_standard_2024_01",
  "bank_family": "chase",
  "statement_type": "checking",
  "pages": 5,
  "expected_transactions": 45,
  "expected_beginning_balance": 1000.00,
  "expected_ending_balance": 1500.00,
  "known_issues": [],
  "template_id": "chase_checking_personal_v2"
}
```

---

## Template Testing

### Template Validation Tests

Every template must pass validation tests before promotion:

```python
class TestTemplateValidation:
    def test_required_sections_present(self, template):
        required = ["detect", "preprocess", "table", "extraction", 
                    "columns", "parsing", "provenance", "verification"]
        for section in required:
            assert section in template
    
    def test_bbox_values_in_range(self, template):
        bboxes = extract_all_bboxes(template)
        for bbox in bboxes:
            for value in bbox:
                assert 0.0 <= value <= 1.0
    
    def test_extraction_methods_valid(self, template):
        valid_methods = {"camelot_lattice", "camelot_stream", 
                        "tabula_stream", "pdfplumber_columns"}
        for method in template["extraction"]["methods"]:
            assert method in valid_methods
```

### Template Regression Tests

When templates are modified, run against known good outputs:

```python
class TestTemplateRegression:
    @pytest.mark.parametrize("fixture", get_fixtures_for_template("chase_checking_v2"))
    async def test_extraction_matches_expected(self, fixture):
        result = await extract_with_template(
            pdf=fixture.pdf_path,
            template=fixture.template
        )
        
        expected = load_expected_output(fixture.expected_path)
        
        # Compare transaction count
        assert len(result.transactions) == len(expected.transactions)
        
        # Compare each transaction
        for actual, expected in zip(result.transactions, expected.transactions):
            assert actual["posted_date"] == expected["posted_date"]
            assert actual["amount"] == expected["amount"]
            assert abs(actual["balance"] - expected["balance"]) < 0.01
```

---

## Performance Tests

### Benchmarks

| Operation | Target | Test |
|-----------|--------|------|
| Classification | < 2s | `test_classification_latency` |
| OCR per page | < 1s | `test_ocr_latency` |
| Extraction | < 5s | `test_extraction_latency` |
| API response | < 200ms | `test_api_latency` |

### Load Tests

```python
class TestLoad:
    async def test_concurrent_uploads(self, client):
        """Verify system handles 10 concurrent uploads."""
        pdfs = [load_fixture(f"pdf_{i}.pdf") for i in range(10)]
        
        async def upload(pdf):
            return await client.post("/api/v1/statements", files={"file": pdf})
        
        start = time.time()
        results = await asyncio.gather(*[upload(pdf) for pdf in pdfs])
        duration = time.time() - start
        
        assert all(r.status_code == 201 for r in results)
        assert duration < 30  # All uploads complete within 30s
    
    async def test_sustained_throughput(self, client):
        """Process 100 statements over 10 minutes."""
        # ... implementation
```

---

## Test Data Management

### Principles

1. **No production data in tests** — Use synthetic or anonymized fixtures
2. **Deterministic fixtures** — Same input always produces same output
3. **Version controlled** — Fixtures stored in repository
4. **Documented** — Each fixture has metadata explaining its purpose

### Fixture Generation

For new bank formats, create fixtures by:

1. Obtain sample statements (with permission)
2. Anonymize sensitive data
3. Manually verify expected extraction
4. Add to fixture library with metadata

---

## Continuous Integration

### Pipeline Stages

```yaml
stages:
  - lint
  - unit-tests
  - integration-tests
  - e2e-tests
  - performance-tests

lint:
  script:
    - ruff check .
    - mypy src/
  
unit-tests:
  script:
    - pytest tests/unit -v --cov=src --cov-report=xml
  coverage:
    minimum: 80%

integration-tests:
  services:
    - postgres:15
    - redis:7
  script:
    - pytest tests/integration -v
  
e2e-tests:
  script:
    - pytest tests/e2e -v --timeout=300
  only:
    - main
    - merge_requests

performance-tests:
  script:
    - pytest tests/performance -v
  only:
    - main
```

### Quality Gates

| Gate | Requirement |
|------|-------------|
| Unit test coverage | ≥ 80% |
| All tests passing | Required |
| No new lint errors | Required |
| Type check passing | Required |
| Performance regression | < 10% slower |

---

## Test Environment

### Local Development

```bash
# Run all unit tests
pytest tests/unit

# Run specific test file
pytest tests/unit/test_reconciliation.py

# Run with coverage
pytest tests/unit --cov=src --cov-report=html

# Run integration tests (requires Docker)
docker-compose -f docker-compose.test.yml up -d
pytest tests/integration
```

### CI Environment

- Isolated database per test run
- Fresh Redis instance
- Mounted fixture volume
- Artifact storage for failed test outputs

---

## Debugging Failed Tests

### Artifact Collection

On test failure, collect:

1. Input PDF (if applicable)
2. Generated artifacts (JSON files)
3. State history
4. Log output
5. Screenshots (for UI tests)

### Reproduction

Each test failure includes reproduction steps:

```
FAILED test_extraction_matches_expected[chase_checking_2024_01]

Reproduction:
  1. Load fixture: fixtures/pdfs/chase/checking/standard_2024_01.pdf
  2. Apply template: chase_checking_personal_v2
  3. Compare output to: fixtures/expected_outputs/chase_checking_standard_transactions.json

Artifacts saved to: /tmp/test_artifacts/test_extraction_2024_01_15_103000/
```

---

## Test Maintenance

### Weekly

- Review flaky test report
- Update fixtures for new bank layouts

### Monthly

- Review coverage trends
- Performance benchmark comparison
- Fixture audit (remove obsolete)

### Quarterly

- Test strategy review
- New bank fixture creation
- E2E test expansion

---

End of Testing Strategy Specification
