from __future__ import annotations

import hashlib
import json
import shutil
import struct
from pathlib import Path, PurePosixPath
from typing import Any

MANIFEST_NAME = "MULTIBOOT-INTEGRITY-MANIFEST.json"
REQUIRED_OC_FILES = (
    "OpenCore.efi",
    "config.plist",
)
REQUIRED_OC_DIRS = ("ACPI", "Drivers", "Kexts", "Resources", "Tools")
REQUIRED_OUTPUT_FILES = (
    "EFI/BOOT/BOOTx64.efi",
    "EFI/OC/OpenCore.efi",
    "EFI/OC/config.plist",
    "images/research-os.iso",
    "boot/grub/grub.cfg",
    "boot/grub/research-os.cfg",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _regular_file(path: str | Path, label: str) -> Path:
    value = Path(path)
    if value.is_symlink() or not value.is_file():
        raise ValueError(f"{label} must be a regular, non-symlink file")
    return value.resolve(strict=True)


def _directory(path: str | Path, label: str) -> Path:
    value = Path(path)
    if value.is_symlink() or not value.is_dir():
        raise ValueError(f"{label} must be an existing, non-symlink directory")
    root = value.resolve(strict=True)
    for item in root.rglob("*"):
        if item.is_symlink():
            raise ValueError(f"{label} contains a symlink: {item.relative_to(root)}")
    return root


def _is_x86_64_uefi_pe(path: Path) -> bool:
    with path.open("rb") as stream:
        header = stream.read(4096)
    if len(header) < 64 or header[:2] != b"MZ":
        return False
    pe_offset = struct.unpack_from("<I", header, 0x3C)[0]
    return (
        pe_offset + 6 <= len(header)
        and header[pe_offset : pe_offset + 4] == b"PE\0\0"
        and struct.unpack_from("<H", header, pe_offset + 4)[0] == 0x8664
    )


def _is_iso9660(path: Path) -> bool:
    # ISO-9660 primary volume descriptor begins at logical sector 16.
    with path.open("rb") as stream:
        stream.seek(16 * 2048)
        descriptor = stream.read(7)
    return len(descriptor) == 7 and descriptor[0] == 1 and descriptor[1:6] == b"CD001" and descriptor[6] == 1


def _safe_manifest_path(value: Any) -> str | None:
    if not isinstance(value, str) or not value or "\\" in value:
        return None
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        return None
    return path.as_posix() if path.as_posix() == value else None


def _inventory(root: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"symlink is not allowed: {path.relative_to(root)}")
        if path.is_file() and path.name != MANIFEST_NAME:
            relative = path.relative_to(root).as_posix()
            entries.append({"path": relative, "size": path.stat().st_size, "sha256": sha256_file(path)})
    return entries


def build_multiboot_staging(
    opencore_efi_root: str | Path,
    research_os_iso: str | Path,
    grub_efi_binary: str | Path,
    research_os_grub_entry: str | Path,
    output_dir: str | Path,
) -> dict[str, Any]:
    """Compose a non-destructive Multi-Boot staging directory.

    This function never discovers, formats, mounts, or writes to a physical USB.
    It accepts an already-built Research OS ISO and its GRUB menu fragment.
    """
    oc_root = _directory(opencore_efi_root, "OpenCore EFI root")
    iso = _regular_file(research_os_iso, "Research OS ISO")
    grub = _regular_file(grub_efi_binary, "GRUB UEFI binary")
    grub_entry = _regular_file(research_os_grub_entry, "Research OS GRUB entry")
    output = Path(output_dir)

    if output.exists() or output.is_symlink():
        raise ValueError("output_dir must not exist; refusing to overwrite existing data")
    if not _is_x86_64_uefi_pe(grub):
        raise ValueError("GRUB binary is not a valid x86_64 PE/COFF UEFI application")
    if not _is_iso9660(iso):
        raise ValueError("Research OS image is not a recognized ISO-9660 image")

    for relative in REQUIRED_OC_FILES:
        candidate = oc_root / "OC" / relative
        if not candidate.is_file() or candidate.is_symlink():
            raise ValueError(f"OpenCore package is missing required file: OC/{relative}")
    for relative in REQUIRED_OC_DIRS:
        candidate = oc_root / "OC" / relative
        if not candidate.is_dir() or candidate.is_symlink():
            raise ValueError(f"OpenCore package is missing required directory: OC/{relative}")

    entry_text = grub_entry.read_text(encoding="utf-8")
    if "menuentry" not in entry_text or "research-os.iso" not in entry_text:
        raise ValueError("Research OS GRUB fragment must define a menuentry referencing research-os.iso")

    output.mkdir(parents=True)
    try:
        (output / "EFI" / "BOOT").mkdir(parents=True)
        (output / "EFI" / "OC").mkdir(parents=True)
        (output / "images").mkdir()
        (output / "boot" / "grub").mkdir(parents=True)

        shutil.copy2(grub, output / "EFI" / "BOOT" / "BOOTx64.efi")
        shutil.copytree(oc_root / "OC", output / "EFI" / "OC", dirs_exist_ok=True)
        shutil.copy2(iso, output / "images" / "research-os.iso")
        shutil.copy2(grub_entry, output / "boot" / "grub" / "research-os.cfg")

        (output / "boot" / "grub" / "grub.cfg").write_text(
            "set timeout=10\n"
            "set default=0\n"
            "menuentry 'OpenCore — macOS installation path' {\n"
            "    chainloader /EFI/OC/OpenCore.efi\n"
            "}\n"
            "source /boot/grub/research-os.cfg\n",
            encoding="utf-8",
        )
        entries = _inventory(output)
        manifest = {
            "schema_version": "1.0",
            "artifact_type": "multiboot-staging",
            "architecture": "x86_64-uefi",
            "hash_algorithm": "sha256",
            "file_count": len(entries),
            "files": entries,
            "status": "PASS",
            "scope": "staging directory integrity only; does not prove boot success or write to USB media",
        }
        (output / MANIFEST_NAME).write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return manifest
    except Exception:
        shutil.rmtree(output, ignore_errors=True)
        raise


def verify_multiboot_staging(staging_dir: str | Path) -> dict[str, Any]:
    root = Path(staging_dir)
    if root.is_symlink() or not root.is_dir():
        return {"status": "FAIL", "errors": ["staging directory is missing or unsafe"], "verified_files": 0}
    try:
        manifest_path = root / MANIFEST_NAME
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"status": "FAIL", "errors": ["Multi-Boot manifest is missing or invalid"], "verified_files": 0}
    if not isinstance(manifest, dict) or manifest.get("schema_version") != "1.0" or manifest.get("hash_algorithm") != "sha256":
        return {"status": "FAIL", "errors": ["unsupported Multi-Boot manifest schema"], "verified_files": 0}

    errors: list[str] = []
    listed: dict[str, dict[str, Any]] = {}
    for item in manifest.get("files", []):
        if not isinstance(item, dict):
            errors.append("invalid manifest entry")
            continue
        relative = _safe_manifest_path(item.get("path"))
        if relative is None or relative == MANIFEST_NAME or relative in listed:
            errors.append("unsafe or duplicate manifest path")
            continue
        listed[relative] = item
        target = root / relative
        if target.is_symlink() or not target.is_file():
            errors.append(f"missing or unsafe file: {relative}")
            continue
        if not isinstance(item.get("size"), int) or target.stat().st_size != item["size"]:
            errors.append(f"size mismatch: {relative}")
        digest = item.get("sha256")
        if not isinstance(digest, str) or sha256_file(target) != digest:
            errors.append(f"SHA-256 mismatch: {relative}")

    try:
        actual = {entry["path"] for entry in _inventory(root)}
    except (OSError, ValueError) as exc:
        errors.append(str(exc))
        actual = set()
    for missing in sorted(set(REQUIRED_OUTPUT_FILES) - actual):
        errors.append(f"missing required Multi-Boot file: {missing}")
    for extra in sorted(actual - set(listed)):
        errors.append(f"unmanifested file: {extra}")
    for missing in sorted(set(listed) - actual):
        errors.append(f"manifest entry absent from staging: {missing}")
    if manifest.get("file_count") != len(manifest.get("files", [])):
        errors.append("file_count does not match manifest")
    return {
        "status": "PASS" if not errors else "FAIL",
        "errors": sorted(set(errors)),
        "verified_files": len(listed),
        "architecture": manifest.get("architecture"),
        "artifact_type": manifest.get("artifact_type"),
    }
