from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

_SHA256 = re.compile(r"^[0-9a-fA-F]{64}$")
_SUPPORTED_SUFFIXES = {".dmg", ".pkg", ".iso", ".zip"}


def sha256_path(path: str | Path) -> str:
    """Stream a file's SHA-256 without loading a large installer into memory."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_installer_artifact(
    artifact_path: str | Path,
    *,
    expected_sha256: str,
    source_url: str,
    expected_size: int | None = None,
) -> dict[str, Any]:
    """Verify an installer against a separately obtained trusted digest.

    This deliberately does not download the installer or fetch its expected
    digest. The caller must obtain the digest from a trusted, independent
    vendor/source channel. It does not claim to verify Apple signatures or
    prove that an installer is compatible with the target hardware.
    """
    path = Path(artifact_path)
    errors: list[str] = []
    if not _SHA256.fullmatch(expected_sha256 or ""):
        return {"status": "FAIL", "errors": ["expected_sha256 must be 64 hexadecimal characters"]}
    parsed = urlparse(source_url or "")
    if parsed.scheme != "https" or not parsed.netloc:
        errors.append("source_url must be an HTTPS URL")
    if path.suffix.lower() not in _SUPPORTED_SUFFIXES:
        errors.append(f"unsupported installer extension: {path.suffix or '<none>'}")
    if not path.is_file() or path.is_symlink():
        errors.append("installer file is missing or is a symlink")
        return {"status": "FAIL", "errors": errors, "artifact": path.name}
    size = path.stat().st_size
    if size <= 0:
        errors.append("installer file is empty")
    if expected_size is not None:
        if not isinstance(expected_size, int) or expected_size <= 0:
            errors.append("expected_size must be a positive integer")
        elif size != expected_size:
            errors.append(f"size mismatch: expected {expected_size}, got {size}")
    actual_sha256 = sha256_path(path)
    if actual_sha256.lower() != expected_sha256.lower():
        errors.append("SHA-256 mismatch against independently supplied expected digest")
    return {
        "schema_version": "1.0",
        "artifact": path.name,
        "artifact_type": path.suffix.lower().lstrip("."),
        "size": size,
        "sha256": actual_sha256,
        "expected_sha256": expected_sha256.lower(),
        "source_url": source_url,
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "scope": "byte-integrity only; source trust, Apple signature, installer validity, and hardware compatibility are separate gates",
    }
