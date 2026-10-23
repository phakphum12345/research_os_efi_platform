from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Mapping
from backend.builder.efi_builder import build_efi
from .manifest import build_manifest
from .uefi_integrity import write_integrity_manifest

def generate_candidate(profile: Mapping[str,Any],output: str,strict: bool=True):
    result=build_efi(profile,root=output,strict=strict)
    path=Path(output)/"OC"/"compatibility-report.json"
    manifest=build_manifest(profile,[str(path)])
    manifest_path=Path(output)/"OC"/"evidence-manifest.json"
    manifest_path.write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    integrity_path = write_integrity_manifest(output, artifact_type="candidate")
    result["manifest"]=str(manifest_path)
    result["integrity_manifest"]=str(integrity_path)
    return result
