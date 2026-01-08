# API Contract Specification

## Purpose

This document defines the authoritative REST API contract for the Bank Statement Intelligence Engine (BSIE).

The API serves as the interface between:

- Next.js frontend application
- External integrations
- Background worker coordination

---

## API Overview

| Property | Value |
|----------|-------|
| Base URL | `/api/v1` |
| Authentication | Bearer token (JWT) |
| Content-Type | `application/json` |
| API Version | `1.0.0` |

---

## Authentication

All endpoints except `/health` require authentication.

**Request Header:**
```
Authorization: Bearer <jwt_token>
```

**Token Claims:**
```json
{
  "sub": "user_123",
  "name": "John Doe",
  "email": "john@example.com",
  "roles": ["reviewer"],
  "exp": 1704067200
}
```

---

## Common Response Formats

### Success Response

```json
{
  "data": { ... },
  "meta": {
    "request_id": "req_abc123",
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

### Error Response

```json
{
  "error": {
    "code": "E1001",
    "category": "VALIDATION",
    "message": "File is not a valid PDF",
    "details": { ... },
    "request_id": "req_abc123",
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

### Paginated Response

```json
{
  "data": [ ... ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total_items": 156,
    "total_pages": 8
  },
  "meta": { ... }
}
```

---

## Endpoints

### Health & Status

#### GET /health

Health check endpoint (no auth required).

**Response 200:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "components": {
    "database": "healthy",
    "redis": "healthy",
    "storage": "healthy"
  }
}
```

---

### Statements

#### POST /statements

Upload a new statement for processing.

**Request:**
- Content-Type: `multipart/form-data`
- Body:
  - `file`: PDF file (required)
  - `metadata`: JSON string (optional)

**Metadata Schema:**
```json
{
  "original_filename": "chase_jan_2024.pdf",
  "source": "email_attachment",
  "tags": ["2024", "chase"]
}
```

**Response 201:**
```json
{
  "data": {
    "statement_id": "stmt_abc123",
    "status": "UPLOADED",
    "uploaded_at": "2024-01-15T10:30:00Z"
  }
}
```

**Errors:**
- `400` - Invalid file format (E1001)
- `413` - File too large
- `422` - Metadata validation failed

---

#### GET /statements

List statements with filtering and pagination.

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | int | 1 | Page number |
| `page_size` | int | 20 | Items per page (max 100) |
| `status` | string | - | Filter by state |
| `bank_family` | string | - | Filter by bank |
| `statement_type` | string | - | Filter by type |
| `from_date` | date | - | Upload date from |
| `to_date` | date | - | Upload date to |
| `sort` | string | `-uploaded_at` | Sort field (prefix `-` for desc) |

**Response 200:**
```json
{
  "data": [
    {
      "statement_id": "stmt_abc123",
      "status": "COMPLETED",
      "bank_family": "chase",
      "statement_type": "checking",
      "uploaded_at": "2024-01-15T10:30:00Z",
      "transaction_count": 45
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total_items": 156,
    "total_pages": 8
  }
}
```

---

#### GET /statements/{statement_id}

Get detailed statement information.

**Response 200:**
```json
{
  "data": {
    "statement_id": "stmt_abc123",
    "status": "COMPLETED",
    "classification": {
      "bank_family": "chase",
      "statement_type": "checking",
      "segment": "personal",
      "confidence": 0.95
    },
    "template": {
      "template_id": "chase_checking_personal_v2",
      "version": "2.1.0"
    },
    "extraction": {
      "transaction_count": 45,
      "date_range": {
        "start": "2024-01-01",
        "end": "2024-01-31"
      }
    },
    "reconciliation": {
      "status": "pass",
      "delta_cents": 0
    },
    "uploaded_at": "2024-01-15T10:30:00Z",
    "completed_at": "2024-01-15T10:31:15Z"
  }
}
```

**Errors:**
- `404` - Statement not found

---

#### GET /statements/{statement_id}/state

Get current pipeline state with history.

**Response 200:**
```json
{
  "data": {
    "statement_id": "stmt_abc123",
    "current_state": "COMPLETED",
    "state_history": [
      {
        "state": "UPLOADED",
        "entered_at": "2024-01-15T10:30:00Z",
        "duration_ms": 1200
      },
      {
        "state": "INGESTED",
        "entered_at": "2024-01-15T10:30:01Z",
        "duration_ms": 800
      }
    ],
    "artifacts": {
      "ingest_receipt": true,
      "classification": true,
      "transactions": true,
      "reconciliation": true
    }
  }
}
```

---

#### DELETE /statements/{statement_id}

Delete a statement and all artifacts.

**Response 204:** No content

**Errors:**
- `404` - Statement not found
- `409` - Statement is being processed

---

### Transactions

#### GET /statements/{statement_id}/transactions

Get transactions for a statement.

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `source` | string | `final` | `raw` or `final` |
| `page` | int | 1 | Page number |
| `page_size` | int | 100 | Items per page |

**Response 200:**
```json
{
  "data": {
    "statement_id": "stmt_abc123",
    "source": "final",
    "transactions": [
      {
        "row_id": "txn_row_1",
        "posted_date": "2024-01-02",
        "description": "PAYROLL DEPOSIT",
        "amount": 3500.00,
        "balance": 4500.00,
        "provenance": {
          "page": 1,
          "bbox": [0.05, 0.30, 0.95, 0.32]
        }
      }
    ],
    "summary": {
      "total_transactions": 45,
      "total_debits": -2500.00,
      "total_credits": 4000.00
    }
  },
  "pagination": { ... }
}
```

---

#### GET /statements/{statement_id}/transactions/export

Export transactions in various formats.

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `format` | string | `csv` | `csv`, `json`, `xlsx` |
| `include_provenance` | bool | false | Include provenance data |

**Response 200:**
- Content-Type varies by format
- Content-Disposition: attachment

---

### Artifacts

#### GET /statements/{statement_id}/artifacts

List all artifacts for a statement.

**Response 200:**
```json
{
  "data": {
    "statement_id": "stmt_abc123",
    "artifacts": [
      {
        "type": "ingest_receipt",
        "filename": "ingest_receipt.json",
        "created_at": "2024-01-15T10:30:01Z",
        "size_bytes": 456
      },
      {
        "type": "pdf_original",
        "filename": "original.pdf",
        "created_at": "2024-01-15T10:30:00Z",
        "size_bytes": 245678
      }
    ]
  }
}
```

---

#### GET /statements/{statement_id}/artifacts/{artifact_type}

Get a specific artifact.

**Artifact Types:**
- `pdf_original` - Original uploaded PDF
- `pdf_render/{page}` - Rendered page image
- `ingest_receipt` - Ingest receipt JSON
- `classification` - Classification JSON
- `transactions` - Raw transactions JSON
- `final_transactions` - Final transactions JSON
- `reconciliation` - Reconciliation JSON
- `correction_overlay` - Human corrections JSON

**Response 200:**
- Returns artifact content with appropriate Content-Type

---

### Human Review

#### GET /reviews

List statements pending human review.

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `status` | string | `pending` | `pending`, `in_progress`, `completed` |
| `assigned_to` | string | - | Filter by assignee |
| `trigger_reason` | string | - | Filter by trigger |

**Response 200:**
```json
{
  "data": [
    {
      "review_id": "rev_xyz789",
      "statement_id": "stmt_abc123",
      "trigger_reason": "reconciliation_failed",
      "priority": "high",
      "created_at": "2024-01-15T10:31:00Z",
      "assigned_to": null,
      "time_in_queue_seconds": 3600
    }
  ]
}
```

---

#### GET /reviews/{review_id}

Get review context bundle.

**Response 200:**
```json
{
  "data": {
    "review_id": "rev_xyz789",
    "statement_id": "stmt_abc123",
    "trigger_reason": "reconciliation_failed",
    "context": {
      "classification": { ... },
      "extraction_result": { ... },
      "reconciliation": { ... },
      "transactions": [ ... ]
    },
    "pdf_pages": [
      {
        "page": 1,
        "render_url": "/api/v1/statements/stmt_abc123/artifacts/pdf_render/1"
      }
    ]
  }
}
```

---

#### POST /reviews/{review_id}/claim

Claim a review for processing.

**Response 200:**
```json
{
  "data": {
    "review_id": "rev_xyz789",
    "assigned_to": "user_123",
    "claimed_at": "2024-01-15T11:30:00Z"
  }
}
```

**Errors:**
- `409` - Review already claimed

---

#### POST /reviews/{review_id}/corrections

Submit corrections for a review.

**Request Body:**
```json
{
  "corrections": [
    {
      "correction_type": "field_edit",
      "row_id": "txn_row_15",
      "field": "amount",
      "corrected_value": -152.50,
      "reason": "OCR misread amount"
    }
  ]
}
```

**Response 200:**
```json
{
  "data": {
    "overlay_id": "ovl_def456",
    "corrections_count": 1,
    "validation_result": {
      "valid": true,
      "new_reconciliation": {
        "status": "pass",
        "delta_cents": 0
      }
    }
  }
}
```

---

#### POST /reviews/{review_id}/decision

Submit review decision.

**Request Body:**
```json
{
  "decision": "approve_with_corrections",
  "correction_overlay_id": "ovl_def456",
  "notes": "Fixed OCR error on row 15"
}
```

**Response 200:**
```json
{
  "data": {
    "decision_id": "dec_ghi789",
    "statement_new_state": "COMPLETED",
    "decided_at": "2024-01-15T11:45:00Z"
  }
}
```

---

### Templates

#### GET /templates

List registered templates.

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `status` | string | `stable` | `draft`, `candidate`, `stable`, `deprecated` |
| `bank_family` | string | - | Filter by bank |

**Response 200:**
```json
{
  "data": [
    {
      "template_id": "chase_checking_personal_v2",
      "version": "2.1.0",
      "status": "stable",
      "bank_family": "chase",
      "statement_type": "checking",
      "segment": "personal",
      "statements_processed": 145,
      "success_rate": 0.97
    }
  ]
}
```

---

#### GET /templates/{template_id}

Get template details.

**Response 200:**
```json
{
  "data": {
    "template_id": "chase_checking_personal_v2",
    "version": "2.1.0",
    "status": "stable",
    "content": "...",  // TOML content
    "metadata": {
      "created_at": "2024-01-01T00:00:00Z",
      "created_by": "user_123",
      "statements_processed": 145,
      "last_used_at": "2024-01-15T10:30:00Z"
    }
  }
}
```

---

#### POST /templates

Create a new template (Phase 1: manual only).

**Request Body:**
```json
{
  "template_id": "bofa_checking_personal_v1",
  "content": "...",  // TOML content
  "metadata": {
    "notes": "Initial template for BofA checking"
  }
}
```

**Response 201:**
```json
{
  "data": {
    "template_id": "bofa_checking_personal_v1",
    "version": "1.0.0",
    "status": "draft",
    "validation": {
      "valid": true,
      "warnings": []
    }
  }
}
```

---

### WebSocket Events

#### WS /ws/statements/{statement_id}

Subscribe to state changes for a statement.

**Connection:** WebSocket upgrade from HTTP

**Server Messages:**

State Change:
```json
{
  "event": "state_change",
  "data": {
    "statement_id": "stmt_abc123",
    "previous_state": "EXTRACTING",
    "current_state": "RECONCILING",
    "timestamp": "2024-01-15T10:30:45Z"
  }
}
```

Progress Update:
```json
{
  "event": "progress",
  "data": {
    "statement_id": "stmt_abc123",
    "stage": "extraction",
    "progress_percent": 75,
    "message": "Processing page 3 of 4"
  }
}
```

Error:
```json
{
  "event": "error",
  "data": {
    "statement_id": "stmt_abc123",
    "error": {
      "code": "E3001",
      "message": "No table detected"
    }
  }
}
```

Completion:
```json
{
  "event": "completed",
  "data": {
    "statement_id": "stmt_abc123",
    "final_state": "COMPLETED",
    "transaction_count": 45
  }
}
```

---

## Rate Limiting

| Endpoint Pattern | Limit |
|------------------|-------|
| POST /statements | 10 req/min |
| GET /* | 100 req/min |
| POST /reviews/* | 30 req/min |
| WS connections | 5 concurrent |

**Rate Limit Headers:**
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1704067260
```

---

## HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created |
| 204 | No Content (successful delete) |
| 400 | Bad Request (validation error) |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |
| 409 | Conflict (state conflict) |
| 413 | Payload Too Large |
| 422 | Unprocessable Entity |
| 429 | Too Many Requests |
| 500 | Internal Server Error |
| 503 | Service Unavailable |

---

## Versioning

- API version in URL path: `/api/v1/`
- Breaking changes require new version
- Deprecation notice 6 months before removal
- Version returned in all responses

---

End of API Contract Specification
