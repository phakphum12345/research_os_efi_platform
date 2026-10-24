from __future__ import annotations

import json
import os
import plistlib
from typing import Any, Mapping

from .compatibility import evaluate_hardware, result_to_dict
from .config_gen import generate_config
from .kext_resolver import resolve_kexts
from backend.platform.uefi_integrity import write_integrity_manifest


def create_structure(root: str = "EFI") -> None:
    paths = [
        os.path.join(root, "OC"),
        os.path.join(root, "OC", "ACPI"),
        os.path.join(root, "OC", "Kexts"),
        os.path.join(root, "OC", "Drivers"),
        os.path.join(root, "OC", "Resources"),
        os.path.join(root, "OC", "Tools"),
    ]
    for path in paths:
        os.makedirs(path, exist_ok=True)


def build_efi(
    profile: Mapping[str, Any],
    root: str = "EFI",
    strict: bool = True,
) -> dict[str, Any]:
    """Build only when compatibility evidence clears the safety gate.

    A blocked machine still gets an inspectable compatibility report, but no
    bootable-looking config is emitted. This prevents unsupported hardware
    guesses from becoming EFI artifacts.
    """
    result = evaluate_hardware(profile)
    create_structure(root)

    report = result_to_dict(result)
    report_path = os.path.join(root, "OC", "compatibility-report.json")
    with open(report_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)

    if result.status == "BLOCKED" and strict:
        integrity_path = write_integrity_manifest(root, artifact_type="candidate")
        return {
            "status": "EFI_BLOCKED",
            "compatibility": report,
            "report": report_path,
            "integrity_manifest": str(integrity_path),
        }

    kexts = resolve_kexts(profile)
    config = generate_config(profile, kexts)

    config_path = os.path.join(root, "OC", "config.plist")
    with open(config_path, "wb") as handle:
        plistlib.dump(config, handle, fmt=plistlib.FMT_XML, sort_keys=False)
    integrity_path = write_integrity_manifest(root, artifact_type="candidate")

    return {
        "status": "EFI_CREATED",
        "kexts": kexts,
        "compatibility": report,
        "config": config_path,
        "integrity_manifest": str(integrity_path),
    }
