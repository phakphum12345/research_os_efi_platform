from __future__ import annotations
import hashlib,json,plistlib
from pathlib import Path
from typing import Any

from .uefi_integrity import MANIFEST_NAME, verify_integrity_manifest
REQUIRED={"ACPI","Kernel","Misc","NVRAM","PlatformInfo","UEFI"}
def sha256_file(path:Path)->str:
 h=hashlib.sha256()
 with path.open("rb") as f:
  for c in iter(lambda:f.read(1024*1024),b""): h.update(c)
 return h.hexdigest()
def validate_opencore(efi_root:str)->dict[str,Any]:
 root=Path(efi_root); oc=root/"OC"; cfg=oc/"config.plist"; report=oc/"compatibility-report.json"
 errors=[]; warnings=[]; files=[]
 for d in ("ACPI","Kexts","Drivers","Resources","Tools"):
  if not (oc/d).is_dir(): errors.append(f"missing OC/{d}")
 if not report.is_file(): errors.append("missing OC/compatibility-report.json")
 else:
  try:
   compatibility=json.loads(report.read_text(encoding="utf-8"))
  except Exception as e: compatibility={"status":"INVALID","error":str(e)}; errors.append("invalid compatibility-report.json")
 if cfg.is_file():
  try:
   with cfg.open("rb") as f: config=plistlib.load(f)
   missing=sorted(REQUIRED-set(config))
   errors.extend([f"config.plist missing top-level key: {x}" for x in missing])
   if config.get("PlatformInfo",{}).get("Generic",{}).get("SystemProductName") in (None,""): warnings.append("SystemProductName is empty")
   files.append({"path":str(cfg),"sha256":sha256_file(cfg),"size":cfg.stat().st_size})
  except Exception as e: errors.append(f"invalid config.plist: {e}")
 else:
  warnings.append("config.plist absent (expected when candidate is compatibility-blocked)")
 for p in sorted(oc.rglob("*")):
  if p.is_file() and p!=cfg and p!=report: files.append({"path":str(p),"sha256":sha256_file(p),"size":p.stat().st_size})
 manifest_path = root / MANIFEST_NAME
 integrity = None
 if manifest_path.is_file():
  integrity = verify_integrity_manifest(root)
  if integrity["status"] != "PASS":
   errors.extend(f"integrity: {item}" for item in integrity["errors"])
 else:
  warnings.append("integrity manifest absent; file integrity is not proven")
 return {"schema_version":"1.0","status":"PASS" if not errors else "FAIL","errors":errors,"warnings":warnings,"compatibility":compatibility,"files":files,"integrity":integrity}
