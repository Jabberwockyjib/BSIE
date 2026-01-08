"""Identifier generation utilities."""
import hashlib
import secrets
from pathlib import Path


def generate_statement_id() -> str:
    """Generate a unique statement identifier."""
    return f"stmt_{secrets.token_hex(8)}"


def compute_sha256(file_path: Path) -> str:
    """Compute SHA-256 hash of a file."""
    sha256_hash = hashlib.sha256()

    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256_hash.update(chunk)

    return sha256_hash.hexdigest()
