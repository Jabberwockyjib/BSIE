"""Utility function tests."""
import re
from datetime import datetime, timezone

from bsie.utils.identifiers import generate_statement_id, compute_sha256
from bsie.utils.timestamps import utc_now, format_iso8601, parse_iso8601


def test_generate_statement_id_format():
    stmt_id = generate_statement_id()
    assert stmt_id.startswith("stmt_")
    assert len(stmt_id) == 21  # stmt_ + 16 chars


def test_generate_statement_id_unique():
    ids = [generate_statement_id() for _ in range(100)]
    assert len(set(ids)) == 100  # All unique


def test_compute_sha256(tmp_path):
    test_file = tmp_path / "test.pdf"
    test_file.write_bytes(b"test content")

    hash_value = compute_sha256(test_file)

    assert len(hash_value) == 64
    assert re.match(r"^[a-f0-9]{64}$", hash_value)


def test_compute_sha256_deterministic(tmp_path):
    test_file = tmp_path / "test.pdf"
    test_file.write_bytes(b"same content")

    hash1 = compute_sha256(test_file)
    hash2 = compute_sha256(test_file)

    assert hash1 == hash2


def test_utc_now_returns_utc_datetime():
    now = utc_now()
    assert now.tzinfo is not None
    assert now.tzinfo == timezone.utc


def test_format_iso8601():
    dt = datetime(2024, 1, 15, 10, 30, 45, tzinfo=timezone.utc)
    formatted = format_iso8601(dt)
    assert formatted == "2024-01-15T10:30:45Z"


def test_parse_iso8601():
    parsed = parse_iso8601("2024-01-15T10:30:45Z")
    assert parsed.year == 2024
    assert parsed.month == 1
    assert parsed.day == 15
    assert parsed.tzinfo == timezone.utc


def test_roundtrip():
    original = utc_now()
    formatted = format_iso8601(original)
    parsed = parse_iso8601(formatted)
    # Microseconds are lost in formatting, so compare to second precision
    assert abs((original - parsed).total_seconds()) < 1
