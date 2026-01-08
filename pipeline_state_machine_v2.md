# Pipeline State Machine Specification v2.0

## Purpose

This document defines the authoritative state machine for the Bank Statement Intelligence Engine (BSIE) pipeline.

The state machine is the **single source of truth** for:

- All valid pipeline states
- All legal state transitions
- Required artifacts for each transition
- Timeout and retry policies
- Error handling paths

**No component may transition state without going through the State Controller.**

---

## Design Principles

1. **Explicit States** — Every meaningful pipeline position is a named state
2. **Guarded Transitions** — Transitions require artifact validation
3. **No Orphans** — Every state has defined entry and exit paths
4. **Timeout Aware** — Every async state has a timeout
5. **Error Paths** — Failures route to defined error states

---

## State Definitions

### Phase 1 States (MVP)

| State | Description | Type | Timeout |
|-------|-------------|------|---------|
| `UPLOADED` | PDF received, pending ingestion | Transient | 30s |
| `INGESTED` | PDF stored, hash computed | Stable | — |
| `CLASSIFIED` | Bank/type/segment determined | Stable | — |
| `ROUTED` | Routing decision made | Transient | 5s |
| `TEMPLATE_SELECTED` | Template chosen for extraction | Stable | — |
| `TEMPLATE_MISSING` | No matching template found | Terminal (Phase 1) | — |
| `EXTRACTION_READY` | Ready to begin extraction | Transient | 10s |
| `EXTRACTING` | Extraction in progress | Transient | 120s |
| `EXTRACTION_FAILED` | Extraction could not complete | Error | — |
| `RECONCILING` | Validating extracted transactions | Transient | 10s |
| `RECONCILIATION_FAILED` | Transactions don't balance | Error | — |
| `HUMAN_REVIEW_REQUIRED` | Manual intervention needed | Stable | 7 days |
| `COMPLETED` | Successfully processed | Terminal | — |

### Phase 2+ States (Future)

| State | Description | Phase |
|-------|-------------|-------|
| `TEMPLATE_DRAFTING` | Agent generating template | 2 |
| `TEMPLATE_DRAFTED` | Template generated, pending review | 2 |
| `TEMPLATE_REVIEW` | VLLM reviewing template | 2/3 |
| `TEMPLATE_REVIEW_FAILED` | Review failed, needs retry/escalation | 2/3 |
| `TEMPLATE_APPROVED` | Template passed review | 2/3 |

---

## State Diagram

### Phase 1 (MVP) Flow

```
                                    ┌─────────────────────────────────────┐
                                    │                                     │
                                    ▼                                     │
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌────────┐    ┌─────────────────┐
│ UPLOADED │───▶│ INGESTED │───▶│CLASSIFIED│───▶│ ROUTED │───▶│TEMPLATE_SELECTED│
└──────────┘    └──────────┘    └──────────┘    └────────┘    └─────────────────┘
     │              │               │               │                  │
     │              │               │               │                  │
     ▼              ▼               ▼               ▼                  ▼
 [timeout]     [E1001-E1003]   [E3021]        ┌──────────────┐  ┌─────────────────┐
     │              │               │         │TEMPLATE_     │  │EXTRACTION_READY │
     ▼              ▼               ▼         │MISSING       │  └─────────────────┘
┌──────────────────────────────────────┐      └──────────────┘          │
│        HUMAN_REVIEW_REQUIRED         │◀──────────────────────────────┐│
└──────────────────────────────────────┘                               ││
     │         │         │                                             ││
     │         │         │                                             ▼│
     │         │         │                                      ┌──────────┐
     │         │         │                                      │EXTRACTING│
     │         │         │                                      └──────────┘
     │         │         │                                        │      │
     │         │         │                    ┌────────────────────┘      │
     │         │         │                    │                          │
     │         │         │                    ▼                          ▼
     │         │         │            ┌──────────────────┐      ┌───────────────┐
     │         │         │            │EXTRACTION_FAILED │      │  RECONCILING  │
     │         │         │            └──────────────────┘      └───────────────┘
     │         │         │                    │                    │         │
     │         │         │                    │                    │         │
     │         │         │                    │                    ▼         ▼
     │         │         │                    │           ┌───────────┐  ┌─────────────────────┐
     │         │         │                    └──────────▶│ COMPLETED │  │RECONCILIATION_FAILED│
     │         │         │                                └───────────┘  └─────────────────────┘
     │         │         │                                      ▲                   │
     │         │         │                                      │                   │
     │         │         └──────────────────────────────────────┘                   │
     │         │              (approve / approve_with_corrections)                  │
     │         │                                                                    │
     │         └────────────────────────────────────────────────────────────────────┘
     │                            (route to human review)
     │
     └─────────────────────────▶ EXTRACTION_READY (request reprocessing)
```

### Phase 2+ Flow (Template Generation)

```
TEMPLATE_MISSING
       │
       ▼
┌──────────────────┐
│TEMPLATE_DRAFTING │ (Agent generating)
└──────────────────┘
       │
       ▼
┌──────────────────┐
│ TEMPLATE_DRAFTED │ (Pending review)
└──────────────────┘
       │
       ▼
┌──────────────────┐     ┌───────────────────────┐
│ TEMPLATE_REVIEW  │────▶│ TEMPLATE_REVIEW_FAILED│
└──────────────────┘     └───────────────────────┘
       │                          │
       │ (pass)                   │ (retry < max)
       ▼                          ▼
┌──────────────────┐     ┌──────────────────┐
│TEMPLATE_APPROVED │     │ TEMPLATE_DRAFTING│ (retry)
└──────────────────┘     └──────────────────┘
       │                          │
       │                          │ (retry >= max)
       ▼                          ▼
┌──────────────────┐     ┌───────────────────────┐
│ EXTRACTION_READY │     │ HUMAN_REVIEW_REQUIRED │
└──────────────────┘     └───────────────────────┘
```

---

## Transition Definitions

### UPLOADED → INGESTED

**Trigger:** Automatic (background worker)

**Required Artifacts:**
- `ingest_receipt.json` (validated against schema)

**Validations:**
- PDF is valid and readable
- SHA-256 computed
- Page count determined
- File stored successfully

**Timeout:** 30 seconds → `HUMAN_REVIEW_REQUIRED`

**Errors:**
- E1001 (Invalid PDF) → Terminal rejection
- E1002 (Corrupted) → Terminal rejection
- E1003 (Encrypted) → Terminal rejection
- E2xxx (Transient) → Retry (3x) → `HUMAN_REVIEW_REQUIRED`

---

### INGESTED → CLASSIFIED

**Trigger:** Automatic (background worker)

**Required Artifacts:**
- `classification.json` (validated against schema)

**Validations:**
- Bank family identified (or "unknown")
- Statement type determined
- Layout fingerprint generated
- Candidate templates scored

**Timeout:** 5 seconds (sync operation, should not timeout)

**Errors:**
- E3021 (Header not found) → Classification with `confidence: 0.0`

---

### CLASSIFIED → ROUTED

**Trigger:** Automatic (State Controller)

**Required Artifacts:**
- `route_decision.json`

**Logic:**

```python
def route_statement(classification: Classification) -> RouteDecision:
    candidates = classification.candidate_templates
    
    if not candidates:
        return RouteDecision(
            decision="template_missing",
            selection_reason="No candidate templates found"
        )
    
    top_candidate = candidates[0]
    
    if top_candidate.score >= SELECTION_THRESHOLD:
        return RouteDecision(
            decision="template_selected",
            selected_template=top_candidate,
            selection_reason=f"Score {top_candidate.score} >= threshold {SELECTION_THRESHOLD}"
        )
    else:
        return RouteDecision(
            decision="template_missing",
            selection_reason=f"Top score {top_candidate.score} < threshold {SELECTION_THRESHOLD}",
            alternatives_considered=candidates
        )
```

**Thresholds:**

| Parameter | Value | Description |
|-----------|-------|-------------|
| `SELECTION_THRESHOLD` | 0.80 | Minimum score for auto-selection |
| `HIGH_CONFIDENCE_THRESHOLD` | 0.95 | No logging required |
| `REVIEW_THRESHOLD` | 0.60 | Below this → human review |

**Tiebreaker Rules (when multiple templates score equally):**

1. Higher fingerprint similarity
2. More recent template version
3. Higher statement count (more battle-tested)
4. Alphabetical template_id (deterministic fallback)

---

### ROUTED → TEMPLATE_SELECTED

**Condition:** `route_decision.decision == "template_selected"`

**Required Artifacts:**
- `route_decision.json` with `selected_template`

**Side Effects:**
- Template binding recorded (immutable)
- Template version locked for this statement

---

### ROUTED → TEMPLATE_MISSING

**Condition:** `route_decision.decision == "template_missing"`

**Phase 1 Behavior:** → `HUMAN_REVIEW_REQUIRED` (manual template creation needed)

**Phase 2+ Behavior:** → `TEMPLATE_DRAFTING`

---

### TEMPLATE_SELECTED → EXTRACTION_READY

**Trigger:** Automatic

**Required Artifacts:** None (template already selected)

**Validations:**
- Selected template exists in registry
- Template is in `stable` status
- Template schema validates

---

### EXTRACTION_READY → EXTRACTING

**Trigger:** Background worker claims job

**Required Artifacts:** None

**Side Effects:**
- Job assigned to worker
- Extraction timer started

---

### EXTRACTING → RECONCILING

**Condition:** Extraction completes successfully

**Required Artifacts:**
- `ocr_result.json` (if OCR was needed)
- `extraction_result.json` with `status: "complete"`
- `transactions.json`

**Validations:**
- All required fields present
- Provenance attached to each transaction
- Beginning/ending balance extracted

---

### EXTRACTING → EXTRACTION_FAILED

**Condition:** Extraction fails or times out

**Required Artifacts:**
- `extraction_error.json`

**Error Categories:**
- E3001 (No table) → `EXTRACTION_FAILED`
- E3002 (Partial) → `EXTRACTION_FAILED` (with partial data)
- E3003-E3005 (Parse errors) → `EXTRACTION_FAILED`
- E3010-E3011 (OCR quality) → `EXTRACTION_FAILED`
- Timeout (120s) → `EXTRACTION_FAILED`

---

### EXTRACTION_FAILED → HUMAN_REVIEW_REQUIRED

**Trigger:** Automatic

**Context Bundle:** Error details, partial extraction (if any), PDF renders

---

### RECONCILING → COMPLETED

**Condition:** Reconciliation passes

**Required Artifacts:**
- `reconciliation.json` with `status: "pass"`
- `final_transactions.json`

**Validations:**
- Delta within tolerance
- Running balance checks pass (if performed)

---

### RECONCILING → RECONCILIATION_FAILED

**Condition:** Reconciliation fails

**Required Artifacts:**
- `reconciliation.json` with `status: "fail"`

**Error Details:**
- Delta amount
- Expected vs calculated balance
- Suspect transactions (if identifiable)

---

### RECONCILIATION_FAILED → HUMAN_REVIEW_REQUIRED

**Trigger:** Automatic

**Context Bundle:** Reconciliation details, transactions, PDF renders

---

### HUMAN_REVIEW_REQUIRED → COMPLETED

**Condition:** Reviewer approves (with or without corrections)

**Required Artifacts:**
- `human_review_decision.json` with `decision: "approve"` or `"approve_with_corrections"`
- `correction_overlay.json` (if corrections made)
- `final_transactions.json` (merged with corrections)
- `reconciliation.json` (recalculated if corrections made)

---

### HUMAN_REVIEW_REQUIRED → EXTRACTION_READY

**Condition:** Reviewer requests reprocessing

**Required Artifacts:**
- `human_review_decision.json` with `decision: "request_reprocessing"`

**Side Effects:**
- Previous extraction artifacts archived (not deleted)
- Reprocessing hints stored
- Retry counter incremented

---

### HUMAN_REVIEW_REQUIRED → (Terminal Rejection)

**Condition:** Reviewer rejects statement

**Required Artifacts:**
- `human_review_decision.json` with `decision: "reject"`

**Side Effects:**
- Statement marked as rejected
- No further processing
- Rejection reason recorded

---

## Timeout Policies

| State | Timeout | Action |
|-------|---------|--------|
| `UPLOADED` | 30s | → `HUMAN_REVIEW_REQUIRED` |
| `ROUTED` | 5s | → `HUMAN_REVIEW_REQUIRED` |
| `EXTRACTION_READY` | 10s | → `EXTRACTING` (force start) |
| `EXTRACTING` | 120s | → `EXTRACTION_FAILED` |
| `RECONCILING` | 10s | → `RECONCILIATION_FAILED` |
| `HUMAN_REVIEW_REQUIRED` | 7 days | Alert, no auto-transition |

---

## Retry Policies

| Transition | Max Retries | Backoff | Final Action |
|------------|-------------|---------|--------------|
| Ingestion | 3 | Exponential (1s, 2s, 4s) | `HUMAN_REVIEW_REQUIRED` |
| Classification | 2 | None | Proceed with low confidence |
| Extraction | 1 | None | `EXTRACTION_FAILED` |
| Reconciliation | 0 | — | `RECONCILIATION_FAILED` |

---

## Concurrency Rules

1. **Single Writer** — Only one worker may process a statement at a time
2. **Optimistic Locking** — State transitions use version numbers
3. **Idempotent Transitions** — Repeated calls with same data succeed
4. **Queue Priority** — Human review items prioritized over new uploads

---

## State Controller Interface

```python
class StateController:
    async def transition(
        self,
        statement_id: str,
        to_state: str,
        artifacts: Dict[str, Any] = None,
        trigger: str = None,
        metadata: Dict[str, Any] = None
    ) -> TransitionResult:
        """
        Attempt a state transition.
        
        Validates:
        1. Current state allows transition to to_state
        2. Required artifacts are present and valid
        3. No concurrent modification
        
        Returns:
        - success: bool
        - previous_state: str
        - current_state: str
        - error: Optional[str]
        """
        pass
    
    async def get_state(self, statement_id: str) -> PipelineState:
        """Get current pipeline state with full history."""
        pass
    
    async def get_allowed_transitions(self, statement_id: str) -> List[str]:
        """Get list of valid next states from current state."""
        pass
    
    async def force_transition(
        self,
        statement_id: str,
        to_state: str,
        reason: str,
        actor: str
    ) -> TransitionResult:
        """
        Admin override for stuck states.
        Requires elevated permissions.
        Fully audited.
        """
        pass
```

---

## Transition Matrix

| From State | To State | Condition | Auto/Manual |
|------------|----------|-----------|-------------|
| `UPLOADED` | `INGESTED` | Ingestion complete | Auto |
| `UPLOADED` | `HUMAN_REVIEW_REQUIRED` | Timeout/error | Auto |
| `INGESTED` | `CLASSIFIED` | Classification complete | Auto |
| `CLASSIFIED` | `ROUTED` | Routing decision made | Auto |
| `ROUTED` | `TEMPLATE_SELECTED` | Template found | Auto |
| `ROUTED` | `TEMPLATE_MISSING` | No template | Auto |
| `TEMPLATE_SELECTED` | `EXTRACTION_READY` | Always | Auto |
| `TEMPLATE_MISSING` | `TEMPLATE_DRAFTING` | Phase 2+ | Auto |
| `TEMPLATE_MISSING` | `HUMAN_REVIEW_REQUIRED` | Phase 1 | Auto |
| `EXTRACTION_READY` | `EXTRACTING` | Worker claims | Auto |
| `EXTRACTING` | `RECONCILING` | Extraction success | Auto |
| `EXTRACTING` | `EXTRACTION_FAILED` | Extraction fails | Auto |
| `EXTRACTION_FAILED` | `HUMAN_REVIEW_REQUIRED` | Always | Auto |
| `RECONCILING` | `COMPLETED` | Reconciliation pass | Auto |
| `RECONCILING` | `RECONCILIATION_FAILED` | Reconciliation fail | Auto |
| `RECONCILIATION_FAILED` | `HUMAN_REVIEW_REQUIRED` | Always | Auto |
| `HUMAN_REVIEW_REQUIRED` | `COMPLETED` | Reviewer approves | Manual |
| `HUMAN_REVIEW_REQUIRED` | `EXTRACTION_READY` | Reviewer requests retry | Manual |

---

## Audit Events

Every state transition emits an audit event:

```json
{
  "event_type": "state_transition",
  "statement_id": "stmt_abc123",
  "from_state": "EXTRACTING",
  "to_state": "RECONCILING",
  "trigger": "extraction_complete",
  "artifacts_created": ["extraction_result.json", "transactions.json"],
  "duration_in_previous_state_ms": 4532,
  "worker_id": "worker_01",
  "timestamp": "2024-01-15T10:30:45Z"
}
```

---

## Monitoring & Alerts

| Metric | Warning | Critical |
|--------|---------|----------|
| Statements in `EXTRACTING` > 2 min | 5 | 20 |
| Statements in `HUMAN_REVIEW_REQUIRED` > 1 day | 10 | 50 |
| State transition failures/hour | 5 | 20 |
| Timeout rate (any state) | 1% | 5% |

---

End of Pipeline State Machine Specification v2.0
