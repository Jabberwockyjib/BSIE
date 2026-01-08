"""Utility function tests."""
import pytest
import re

from bsie.utils.identifiers import generate_statement_id, compute_sha256


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
