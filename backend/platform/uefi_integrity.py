from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path, PurePosixPath
from typing import Any

MANIFEST_NAME = "EFI-INTEGRITY-MANIFEST.json"
EXCLUDED_METADATA_FILES = {MANIFEST_NAME, "evidence-packet.json"}
MANIFEST_SCHEMA = "1.0"
INSTALLABLE_REQUIRED_FILES = (
    "EFI/BOOT/BOOTx64.efi",
    "EFI/OC/OpenCore.efi",
    "EFI/OC/config.plist",
)
INSTALLABLE_REQUIRED_DIRS = (
    "EFI/OC/ACPI",
    "EFI/OC/Drivers",
    "EFI/OC/Kexts",
    "EFI/OC/Resources",
    "EFI/OC/Tools",
)
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_relative_path(value: Any) -> str | None:
    if not isinstance(value, str) or not value or "\\" in value:
        return None
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in ("", ".", "..") for part in path.parts):
        return None
    return path.as_posix()


def _inventory(root: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            # Symlinks can escape the package root and are not accepted in a
            # portable installer integrity manifest.
            raise ValueError(f"symlink is not allowed in EFI package: {path.relative_to(root).as_posix()}")
        if path.is_file() and path.name not in EXCLUDED_METADATA_FILES:
            entries.append({
                "path": path.relative_to(root).as_posix(),
                "size": path.stat().st_size,
                "sha256": sha256_file(path),
            })
    return entries


def _installable_errors(root: Path) -> list[str]:
    errors: list[str] = []
    for relative in INSTALLABLE_REQUIRED_FILES:
        path = root / relative
        if not path.is_file():
            errors.append(f"missing required installable file: {relative}")
    for relative in INSTALLABLE_REQUIRED_DIRS:
        if not (root / relative).is_dir():
            errors.append(f"missing required installable directory: {relative}")
    return errors


def build_integrity_manifest(
    package_root: str | Path,
    *,
    artifact_type: str = "candidate",
) -> dict[str, Any]:
    """Build a deterministic manifest; this function never modifies firmware or disks.

    artifact_type='candidate' permits a generated, non-bootable research candidate.
    artifact_type='installable' requires the standard x64 UEFI/OpenCore payload.
    """
    root = Path(package_root).resolve()
    if not root.is_dir():
        raise ValueError("package root must be an existing directory")
    if artifact_type not in {"candidate", "installable"}:
        raise ValueError("artifact_type must be 'candidate' or 'installable'")
    entries = _inventory(root)
    errors = _installable_errors(root) if artifact_type == "installable" else []
    return {
        "schema_version": MANIFEST_SCHEMA,
        "artifact_type": artifact_type,
        "hash_algorithm": "sha256",
        "file_count": len(entries),
        "files": entries,
        "status": "PASS" if not errors else "BLOCKED",
        "errors": errors,
        "scope": "package files only; does not prove hardware compatibility or boot success",
    }


def write_integrity_manifest(
    package_root: str | Path,
    *,
    artifact_type: str = "candidate",
    manifest_name: str = MANIFEST_NAME,
) -> Path:
    root = Path(package_root).resolve()
    relative = _safe_relative_path(manifest_name)
    if relative is None or "/" in relative:
        raise ValueError("manifest_name must be a safe filename within the package root")
    manifest_path = root / relative
    manifest = build_integrity_manifest(root, artifact_type=artifact_type)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest_path


def verify_integrity_manifest(
    package_root: str | Path,
    *,
    manifest_name: str = MANIFEST_NAME,
    require_installable: bool = False,
) -> dict[str, Any]:
    """Verify hashes, sizes, inventory completeness, and optional boot payload.

    Any missing, changed, unexpected, unsafe, or symlinked package file fails closed.
    """
    root = Path(package_root).resolve()
    errors: list[str] = []
    relative_manifest = _safe_relative_path(manifest_name)
    if relative_manifest is None or "/" in relative_manifest:
        return {"status": "FAIL", "errors": ["unsafe manifest path"], "verified_files": 0}
    manifest_path = root / relative_manifest
    if not root.is_dir():
        return {"status": "FAIL", "errors": ["package root does not exist"], "verified_files": 0}
    if not manifest_path.is_file():
        return {"status": "FAIL", "errors": ["integrity manifest is missing"], "verified_files": 0}
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"status": "FAIL", "errors": ["integrity manifest is unreadable or invalid JSON"], "verified_files": 0}
    if not isinstance(manifest, dict) or manifest.get("schema_version") != MANIFEST_SCHEMA:
        return {"status": "FAIL", "errors": ["unsupported integrity manifest schema"], "verified_files": 0}
    if manifest.get("hash_algorithm") != "sha256" or not isinstance(manifest.get("files"), list):
        return {"status": "FAIL", "errors": ["invalid integrity manifest structure"], "verified_files": 0}

    listed: dict[str, dict[str, Any]] = {}
    for item in manifest["files"]:
        if not isinstance(item, dict):
            errors.append("invalid file entry")
            continue
        relative = _safe_relative_path(item.get("path"))
        if relative is None or relative in EXCLUDED_METADATA_FILES:
            errors.append("unsafe or recursive manifest file path")
            continue
        if relative in listed:
            errors.append(f"duplicate manifest path: {relative}")
            continue
        listed[relative] = item
        digest = item.get("sha256")
        size = item.get("size")
        if not isinstance(digest, str) or not _SHA256.fullmatch(digest):
            errors.append(f"invalid SHA-256 for {relative}")
            continue
        if not isinstance(size, int) or size < 0:
            errors.append(f"invalid file size for {relative}")
            continue
        target = root / relative
        if not target.is_file() or target.is_symlink():
            errors.append(f"missing or unsafe package file: {relative}")
            continue
        if target.stat().st_size != size:
            errors.append(f"size mismatch: {relative}")
        if sha256_file(target) != digest:
            errors.append(f"SHA-256 mismatch: {relative}")

    try:
        actual = {item["path"] for item in _inventory(root)}
    except (OSError, ValueError) as exc:
        errors.append(str(exc))
        actual = set()
    listed_paths = set(listed)
    for relative in sorted(actual - listed_paths):
        errors.append(f"unmanifested package file: {relative}")
    for relative in sorted(listed_paths - actual):
        # A missing listed file is already reported above; retain a stable
        # inventory-level error as well for easier diagnosis.
        if not (root / relative).is_file():
            errors.append(f"manifest file absent from package: {relative}")

    if require_installable or manifest.get("artifact_type") == "installable":
        errors.extend(_installable_errors(root))
    if manifest.get("file_count") != len(manifest["files"]):
        errors.append("file_count does not match manifest inventory")
    return {
        "status": "PASS" if not errors else "FAIL",
        "errors": sorted(set(errors)),
        "verified_files": len(listed),
        "artifact_type": manifest.get("artifact_type"),
        "manifest": str(manifest_path),
    }
