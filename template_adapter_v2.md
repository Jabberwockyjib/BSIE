# Template Adapter Specification v2.0

## Purpose

This document defines the authoritative TOML schema for extraction templates in the Bank Statement Intelligence Engine (BSIE).

Templates are **declarative configurations** that instruct the deterministic extraction engine how to process specific bank statement layouts.

**No executable code in templates.** Templates describe *what* to extract, not *how* to execute.

---

## Design Principles

1. **Declarative** — Templates describe structure, not procedures
2. **Deterministic** — Same template + same PDF = same output
3. **Versioned** — Templates are immutable once promoted to stable
4. **Self-Documenting** — Templates include metadata for human understanding
5. **Composable** — Templates can reference shared components

---

## Template Structure

### Complete Template Skeleton

```toml
# Template metadata
[metadata]
template_id = "chase_checking_personal_v2"
version = "2.1.0"
bank_family = "chase"
statement_type = "checking"
segment = "personal"
description = "Chase personal checking account statements (2023+ layout)"
created_at = "2024-01-01T00:00:00Z"
created_by = "system"

# Detection rules
[detect]
# ... detection configuration

# Preprocessing rules
[preprocess]
# ... preprocessing configuration

# Table location rules
[table]
# ... table detection configuration

# Extraction method configuration
[extraction]
# ... extraction method configuration

# Column mapping rules
[columns]
# ... column mapping configuration

# Parsing rules
[parsing]
# ... parsing configuration

# Normalization rules
[normalization]
# ... normalization configuration

# Provenance tracking
[provenance]
# ... provenance configuration

# Verification rules
[verification]
# ... verification configuration
```

---

## Section: metadata

Required identification and documentation.

```toml
[metadata]
# Required fields
template_id = "chase_checking_personal_v2"  # Unique identifier
version = "2.1.0"                            # Semantic version
bank_family = "chase"                        # Bank identifier
statement_type = "checking"                  # checking | savings | credit_card
segment = "personal"                         # personal | business | unknown

# Optional fields
description = "Chase personal checking (2023+ layout)"
layout_fingerprint = "HML-HHM-LLM-L1T1F1-a3f2c891"  # For matching
created_at = "2024-01-01T00:00:00Z"
created_by = "user_123"
promoted_at = "2024-01-15T00:00:00Z"
promoted_by = "user_456"
statements_processed = 145
success_rate = 0.97

# Documentation
notes = """
This template handles Chase personal checking statements from January 2023 onward.
Key characteristics:
- Logo in top-left corner
- Transaction table starts after "Account Activity" header
- Separate columns for withdrawals and deposits
"""
```

---

## Section: detect

Rules for identifying matching statements.

```toml
[detect]
# Required keywords (any match scores)
keywords = ["CHASE", "JPMorgan Chase Bank"]
keyword_match_threshold = 1  # Minimum keyword matches

# Header patterns (regex, scored)
header_patterns = [
    "CHASE.*CHECKING",
    "Account\\s+Activity",
    "Previous\\s+Balance"
]
header_pattern_threshold = 2  # Minimum pattern matches

# Required text elements (must all be present)
required_text = ["Account Activity", "Ending Balance"]

# Negative patterns (disqualify if matched)
negative_patterns = [
    "BUSINESS CHECKING",      # Wrong segment
    "CHASE SAPPHIRE LOUNGE"   # False positive
]

# Page restrictions
detect_pages = [1]  # Only check first page

# Layout fingerprint for fuzzy matching
expected_fingerprint = "HML-HHM-LLM-L1T1F1-a3f2c891"
fingerprint_tolerance = 0.3  # Max Levenshtein distance ratio
```

---

## Section: preprocess

PDF preprocessing configuration.

```toml
[preprocess]
# OCR configuration
requires_ocr = "auto"  # always | never | auto
ocr_engine = "tesseract"
ocr_language = "eng"
ocr_dpi = 300

# Auto-detection rules for OCR
[preprocess.ocr_detection]
# If text density below threshold, use OCR
text_density_threshold = 100  # chars per page
# If confidence below threshold, use OCR
embedded_text_confidence_threshold = 0.8

# Page preprocessing
[preprocess.pages]
deskew = true
remove_watermarks = false
enhance_contrast = false

# PDF handling
[preprocess.pdf]
flatten_forms = true      # Convert form fields to text
remove_annotations = true # Remove sticky notes, etc.
```

---

## Section: table

Table region detection and multi-page handling.

```toml
[table]
# Primary table location (normalized coordinates)
[table.primary]
# Anchor-based detection
anchor_text = "Account Activity"
anchor_position = "above"  # above | below | left | right
anchor_search_pages = [1, 2]  # Pages to search for anchor

# Bounding box (relative to anchor or page)
bbox_mode = "anchor_relative"  # anchor_relative | page_absolute
bbox = [0.0, 0.05, 1.0, 0.85]  # [x0, y0, x1, y1] relative to anchor

# Alternative: absolute page coordinates
# bbox_mode = "page_absolute"
# bbox = [0.05, 0.25, 0.95, 0.90]

# Table end detection
end_anchor_text = "Ending Balance"
end_anchor_position = "below"

# If no end anchor, use distance from start
max_table_height = 0.70  # Max height as fraction of page

# Multi-page table handling
[table.multi_page]
enabled = true
continuation_mode = "detect"  # detect | explicit | all_pages

# Detection-based continuation
[table.multi_page.detection]
# Look for continuation indicators
continuation_indicators = [
    "continued",
    "page \\d+ of \\d+",
    "-- continued --"
]
# Or detect by table structure similarity
structure_similarity_threshold = 0.8

# Explicit page range
# [table.multi_page.explicit]
# pages = [2, 3, 4, 5, 6, 7]

# Header handling on continuation pages
[table.multi_page.headers]
repeat_on_each_page = true
skip_header_rows = 1  # Skip N rows on continuation pages

# Page-specific overrides
[[table.page_overrides]]
page = 1
bbox = [0.05, 0.30, 0.95, 0.90]  # First page has larger header
skip_rows = 0

[[table.page_overrides]]
page = 2
bbox = [0.05, 0.10, 0.95, 0.90]  # Continuation pages start higher
skip_rows = 1  # Skip repeated header

# Table stitching rules
[table.stitching]
# How to combine rows across pages
merge_split_rows = true  # Merge rows split across page boundary
split_row_detection = "hanging_indent"  # hanging_indent | line_continuation | none

# Validation
min_rows = 1
max_rows = 1000  # Sanity check
```

### Multi-Page Table Handling Details

**Challenge:** Transaction tables often span multiple pages with varying headers and footers.

**Stitching Algorithm:**

```python
def stitch_multi_page_table(pages: List[PageTable], config: TableConfig) -> Table:
    """
    Combine tables extracted from multiple pages into a single table.
    """
    all_rows = []
    prev_last_row = None
    
    for i, page_table in enumerate(pages):
        rows = page_table.rows
        
        # Skip header rows on continuation pages
        if i > 0 and config.multi_page.headers.repeat_on_each_page:
            rows = rows[config.multi_page.headers.skip_header_rows:]
        
        # Check for split row at page boundary
        if prev_last_row and config.stitching.merge_split_rows:
            merged = try_merge_split_row(prev_last_row, rows[0], config)
            if merged:
                all_rows[-1] = merged  # Replace last row with merged
                rows = rows[1:]  # Skip first row of current page
        
        all_rows.extend(rows)
        prev_last_row = rows[-1] if rows else None
    
    return Table(rows=all_rows)


def try_merge_split_row(row1: Row, row2: Row, config: TableConfig) -> Optional[Row]:
    """
    Detect and merge rows that were split across a page boundary.
    """
    if config.stitching.split_row_detection == "hanging_indent":
        # Row 2 is continuation if it has no date and description starts with whitespace
        if row2.date is None and row2.description.startswith((' ', '\t')):
            return Row(
                date=row1.date,
                description=row1.description + ' ' + row2.description.strip(),
                amount=row1.amount or row2.amount,
                balance=row2.balance or row1.balance
            )
    
    elif config.stitching.split_row_detection == "line_continuation":
        # Row 2 is continuation if description ends with row1's partial word
        # ... more complex logic
        pass
    
    return None
```

---

## Section: extraction

Extraction method configuration.

```toml
[extraction]
# Ordered list of methods to try
methods = [
    "camelot_lattice",   # Best for tables with visible grid lines
    "camelot_stream",    # For tables without lines but clear columns
    "tabula_stream",     # Alternative stream-based extraction
    "pdfplumber_columns" # Fallback for irregular layouts
]

# Method-specific configuration
[extraction.camelot_lattice]
flavor = "lattice"
line_scale = 40
process_background = true

[extraction.camelot_stream]
flavor = "stream"
edge_tol = 50
row_tol = 10

[extraction.tabula_stream]
guess = false
stream = true

[extraction.pdfplumber_columns]
# Define column boundaries manually
column_boundaries = [0.05, 0.15, 0.55, 0.70, 0.85, 0.95]

# Method selection rules
[extraction.selection]
# Prefer lattice if grid lines detected
prefer_lattice_if_lines = true
# Fall back to next method if row count below threshold
min_rows_threshold = 5
# Use method that extracts most rows (within reason)
prefer_max_rows = true
max_row_difference = 0.2  # Don't switch for <20% more rows
```

---

## Section: columns

Column mapping configuration.

```toml
[columns]
# Expected column count
expected_count = 6
count_tolerance = 1  # Allow +/- 1 column

# Header detection
[columns.headers]
enabled = true
header_row = 0  # First row is header
expected_headers = ["Date", "Description", "Withdrawals", "Deposits", "Balance"]
header_match_threshold = 0.7  # Fuzzy match threshold

# Column mapping (header name or col_N index)
[columns.map]
posted_date = "col_1"      # First column
description = "col_2"      # Second column
debit_amount = "col_3"     # Withdrawals column
credit_amount = "col_4"    # Deposits column  
balance = "col_5"          # Balance column

# Alternative: header-based mapping
# posted_date = "Date"
# description = "Description"
# debit_amount = "Withdrawals"
# credit_amount = "Deposits"
# balance = "Balance"

# Optional columns (don't fail if missing)
[columns.optional]
check_number = "col_6"
reference_number = "col_7"
effective_date = "col_8"

# Column merging rules
[columns.merge]
# Merge debit and credit into single amount
amount_from_split = true
debit_column = "col_3"
credit_column = "col_4"

# Column validation
[columns.validation]
date_column_must_have_dates = true
amount_column_must_have_numbers = true
allow_empty_balance = true  # Running balance may not always be present
```

---

## Section: parsing

Data parsing rules.

```toml
[parsing]
# Date parsing
[parsing.date]
formats = [
    "%m/%d/%Y",    # 01/15/2024
    "%m/%d/%y",    # 01/15/24
    "%m/%d",       # 01/15 (year inferred)
    "%b %d, %Y",   # Jan 15, 2024
    "%b %d"        # Jan 15 (year inferred)
]
year_inference = "statement_period"  # statement_period | current_year | previous_row
statement_period_source = "header"   # Where to find statement date range

# Amount parsing
[parsing.amount]
# Negative indicators
negative_formats = [
    "parentheses",  # (123.45) is negative
    "minus_prefix", # -123.45
    "minus_suffix", # 123.45-
    "cr_suffix"     # 123.45 CR (credit, context dependent)
]

# Thousand separators
thousand_separator = ","
decimal_separator = "."

# Currency symbol handling
strip_currency_symbols = ["$", "USD"]

# Handle amounts without decimal
implicit_decimal = false  # If true, "12345" becomes 123.45

# Balance parsing  
[parsing.balance]
inherit_amount_rules = true

# Description parsing
[parsing.description]
# Clean up extracted descriptions
trim_whitespace = true
normalize_whitespace = true  # Multiple spaces → single space
max_length = 500
```

---

## Section: normalization

Post-extraction normalization.

```toml
[normalization]
# Sign convention normalization
[normalization.signs]
# Define what positive and negative mean for this statement
convention = "debit_negative"  # debit_negative | debit_positive | infer

# Force signs based on column source
debit_column_sign = "negative"   # Values from debit column are negative
credit_column_sign = "positive"  # Values from credit column are positive

# Keyword-based sign inference
[normalization.signs.keywords]
negative_keywords = ["withdrawal", "payment", "debit", "fee", "charge"]
positive_keywords = ["deposit", "credit", "transfer in", "interest"]

# Multiline description handling
[normalization.multiline]
enabled = true
# How to detect continuation lines
detection_method = "indent"  # indent | no_date | pattern
indent_threshold = 4  # Characters of indent
continuation_pattern = "^\\s{4,}"  # Regex for continuation

# Join behavior
join_separator = " "
max_lines = 5

# Row deduplication
[normalization.deduplication]
enabled = true
# Consider rows duplicates if these fields match
match_fields = ["posted_date", "amount", "description"]
description_similarity_threshold = 0.9

# Row filtering
[normalization.filter]
# Remove rows matching patterns
exclude_patterns = [
    "^\\s*$",           # Empty rows
    "^-+$",             # Separator rows
    "^Page \\d+",       # Page numbers
    "^Continued",       # Continuation markers
    "^Subtotal",        # Subtotals
    "^Total"            # Totals
]

# Remove rows with specific values
exclude_if_description_contains = ["BEGINNING BALANCE", "ENDING BALANCE"]

# Date range filtering
[normalization.date_filter]
enabled = true
filter_mode = "statement_period"  # statement_period | explicit
# explicit_start = "2024-01-01"
# explicit_end = "2024-01-31"
```

---

## Section: provenance

Provenance tracking configuration.

```toml
[provenance]
# Enable provenance tracking
enabled = true
required = true  # Fail extraction if provenance cannot be attached

# Coordinate system
coordinate_system = "pdf_points_bottom_left"
normalize_coordinates = true  # Store as [0,1] range

# Field-level provenance
[provenance.fields]
track_all = true  # Track provenance for every field

# Or specify which fields to track
# tracked_fields = ["amount", "balance", "posted_date"]

# Row-level provenance
[provenance.row]
include_raw_text = true
include_bounding_box = true
include_page_number = true
include_extraction_method = true
include_confidence = true

# Confidence scoring
[provenance.confidence]
enabled = true
# Factors that affect confidence
factors = [
    "ocr_confidence",      # If OCR was used
    "extraction_method",   # Some methods more reliable
    "parse_success",       # Did parsing succeed cleanly
    "validation_pass"      # Did value pass validation
]
```

---

## Section: verification

Post-extraction verification rules.

```toml
[verification]
# Reconciliation configuration
[verification.reconciliation]
enabled = true
strategy = "running_balance"  # running_balance | summary_only | both

# Running balance verification
[verification.reconciliation.running_balance]
enabled = true
# Check each row's balance against computed running total
tolerance_cents = 2
# How to handle missing balances
missing_balance_action = "skip"  # skip | fail | interpolate

# Summary reconciliation
[verification.reconciliation.summary]
enabled = true
formula = "beginning + credits - debits = ending"  # or custom formula

# Where to find summary values
[verification.reconciliation.summary.sources]
beginning_balance = { anchor = "Previous Balance", offset = [0.5, 0.02] }
ending_balance = { anchor = "Ending Balance", offset = [0.5, 0.02] }

# Tolerance
tolerance_cents = 2

# Row validation
[verification.rows]
# Minimum fields required for valid row
required_fields = ["posted_date", "description", "amount"]

# Value range checks
[verification.rows.ranges]
amount_min = -1000000
amount_max = 1000000
balance_min = -1000000
balance_max = 10000000

# Date validation
[verification.rows.dates]
must_be_valid_date = true
must_be_within_statement_period = true
allow_future_dates = false

# Integrity checks
[verification.integrity]
# Check for suspicious patterns
check_duplicate_rows = true
check_sequential_dates = false  # Dates don't have to be sequential
check_balance_continuity = true
```

---

## Section: credit_card (Statement Type Specific)

Additional configuration for credit card statements.

```toml
[credit_card]
# Credit card specific reconciliation
[credit_card.reconciliation]
formula = "previous + purchases + fees + interest - payments - credits = new_balance"

# Balance components
[credit_card.components]
previous_balance = { anchor = "Previous Balance", offset = [0.5, 0.02] }
payments = { anchor = "Payments", offset = [0.5, 0.02] }
purchases = { anchor = "Purchases", offset = [0.5, 0.02] }
fees = { anchor = "Fees", offset = [0.5, 0.02] }
interest = { anchor = "Interest", offset = [0.5, 0.02] }
new_balance = { anchor = "New Balance", offset = [0.5, 0.02] }

# Transaction categorization
[credit_card.categories]
payment_keywords = ["PAYMENT", "THANK YOU"]
purchase_keywords = ["PURCHASE", "RETAIL"]
fee_keywords = ["FEE", "CHARGE"]
interest_keywords = ["INTEREST"]
```

---

## Template Inheritance (Future)

Templates can inherit from base templates:

```toml
[metadata]
template_id = "chase_checking_business_v1"
inherits_from = "chase_checking_personal_v2"

# Override only what's different
[detect]
required_text = ["Business Checking", "Account Activity"]

[columns.map]
# Business statements have additional columns
entity_name = "col_7"
```

---

## Validation

All templates must pass schema validation before use.

### Required Sections

- `metadata`
- `detect`
- `table`
- `columns`
- `verification`

### Value Constraints

- All bounding boxes in range [0.0, 1.0]
- All page numbers ≥ 1
- Version must be valid semantic version
- Date formats must be valid strptime strings
- Extraction methods must be from allowed set

---

## Example: Complete Chase Checking Template

```toml
[metadata]
template_id = "chase_checking_personal_v2"
version = "2.1.0"
bank_family = "chase"
statement_type = "checking"
segment = "personal"
description = "Chase personal checking statements (2023+ layout)"

[detect]
keywords = ["CHASE", "JPMorgan Chase Bank", "CHECKING"]
required_text = ["Account Activity", "Ending Balance"]
header_patterns = ["CHASE.*Statement", "Account\\s+Activity"]
detect_pages = [1]

[preprocess]
requires_ocr = "auto"
ocr_engine = "tesseract"

[table]
[table.primary]
anchor_text = "Account Activity"
anchor_position = "above"
bbox_mode = "anchor_relative"
bbox = [0.0, 0.05, 1.0, 0.85]
end_anchor_text = "Ending Balance"

[table.multi_page]
enabled = true
continuation_mode = "detect"

[table.multi_page.headers]
repeat_on_each_page = true
skip_header_rows = 1

[table.stitching]
merge_split_rows = true
split_row_detection = "hanging_indent"

[extraction]
methods = ["camelot_stream", "pdfplumber_columns"]

[columns]
expected_count = 5

[columns.map]
posted_date = "col_1"
description = "col_2"
debit_amount = "col_3"
credit_amount = "col_4"
balance = "col_5"

[columns.merge]
amount_from_split = true
debit_column = "col_3"
credit_column = "col_4"

[parsing.date]
formats = ["%m/%d"]
year_inference = "statement_period"

[parsing.amount]
negative_formats = ["parentheses", "minus_prefix"]
thousand_separator = ","
strip_currency_symbols = ["$"]

[normalization.signs]
convention = "debit_negative"
debit_column_sign = "negative"
credit_column_sign = "positive"

[normalization.multiline]
enabled = true
detection_method = "indent"

[provenance]
enabled = true
required = true

[verification.reconciliation]
enabled = true
strategy = "running_balance"

[verification.reconciliation.running_balance]
tolerance_cents = 2

[verification.rows]
required_fields = ["posted_date", "description", "amount"]
```

---

End of Template Adapter Specification v2.0
