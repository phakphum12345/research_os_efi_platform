from __future__ import annotations

import json
import platform as host_platform
import subprocess
from datetime import datetime, timezone
from typing import Any, Callable


EFI_PARTITION_TYPE = "c12a7328-f81f-11d2-ba4b-00a0c93ec93b"


def _run_powershell(command: str) -> subprocess.CompletedProcess[str]:
    """Run a fixed, read-only PowerShell query; callers cannot supply commands."""
    return subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


def _unknown(reason: str) -> dict[str, Any]:
    return {"status": "UNKNOWN", "value": None, "reason": reason}


def _collect_windows_query(
    command: str,
    *,
    runner: Callable[[str], subprocess.CompletedProcess[str]],
    parse_json: bool = True,
) -> dict[str, Any]:
    try:
        result = runner(command)
    except (OSError, subprocess.SubprocessError, RuntimeError) as exc:
        return _unknown(f"query unavailable: {type(exc).__name__}")
    if result.returncode != 0:
        return _unknown("query failed or access was unavailable")
    output = result.stdout.strip()
    if not output:
        return _unknown("query returned no data")
    if not parse_json:
        return {"status": "DETECTED", "value": output, "reason": None}
    try:
        value = json.loads(output)
    except json.JSONDecodeError:
        return _unknown("query returned invalid JSON")
    if value is None or value == [] or value == {}:
        return {"status": "UNAVAILABLE", "value": value, "reason": "no matching records"}
    return {"status": "DETECTED", "value": value, "reason": None}


def collect_live_discovery(
    target_platform: str | None = None,
    *,
    runner: Callable[[str], subprocess.CompletedProcess[str]] | None = None,
) -> dict[str, Any]:
    """Collect timestamped, read-only host evidence. Never changes boot or disk state.

    The Windows queries are deliberately fixed and read-only. Other platforms
    report UNKNOWN until their boot-metadata providers have been implemented.
    """
    target = (target_platform or host_platform.system()).strip().lower()
    aliases = {"windows": "windows", "linux": "linux", "darwin": "macos", "macos": "macos"}
    target = aliases.get(target, target)
    collected_at = datetime.now(timezone.utc).isoformat()
    evidence: dict[str, dict[str, Any]]

    if target != "windows":
        reason = f"read-only boot metadata provider is not implemented for {target}"
        evidence = {
            key: _unknown(reason)
            for key in ("bios", "disks", "efi_system_partitions", "secure_boot", "firmware_boot_entries")
        }
    else:
        execute = runner or _run_powershell
        queries = {
            "bios": (
                "Get-CimInstance Win32_BIOS | Select-Object Manufacturer,SMBIOSBIOSVersion,ReleaseDate | ConvertTo-Json -Compress",
                True,
            ),
            "disks": (
                "Get-CimInstance Win32_DiskDrive | Select-Object Model,InterfaceType,Size,Index | ConvertTo-Json -Compress",
                True,
            ),
            "efi_system_partitions": (
                f"Get-Partition | Where-Object {{ $_.GptType -eq '{EFI_PARTITION_TYPE}' }} | Select-Object DiskNumber,PartitionNumber,Size,DriveLetter,GptType | ConvertTo-Json -Compress",
                True,
            ),
            "secure_boot": (
                "try { @{ supported = $true; enabled = [bool](Confirm-SecureBootUEFI) } | ConvertTo-Json -Compress } catch { @{ supported = $false; enabled = $null; reason = $_.Exception.GetType().Name } | ConvertTo-Json -Compress }",
                True,
            ),
            "firmware_boot_entries": ("bcdedit.exe /enum firmware", False),
        }
        evidence = {
            key: _collect_windows_query(command, runner=execute, parse_json=parse_json)
            for key, (command, parse_json) in queries.items()
        }
        secure = evidence["secure_boot"]
        if secure["status"] == "DETECTED" and isinstance(secure["value"], dict):
            payload = secure["value"]
            if payload.get("supported") is False or payload.get("enabled") is None:
                evidence["secure_boot"] = _unknown(
                    "Secure Boot state could not be read on this firmware/session"
                )
            else:
                evidence["secure_boot"] = {
                    "status": "DETECTED",
                    "value": {"enabled": bool(payload["enabled"])},
                    "reason": None,
                }

    statuses = [item["status"] for item in evidence.values()]
    overall = "DETECTED" if all(value == "DETECTED" for value in statuses) else (
        "UNKNOWN" if all(value == "UNKNOWN" for value in statuses) else "PARTIAL"
    )
    return {
        "schema_version": "1.0",
        "collected_at": collected_at,
        "platform": target,
        "overall_status": overall,
        "read_only": True,
        "mutation_performed": False,
        "evidence": evidence,
        "limitations": [
            "Read-only inventory only; no firmware, EFI/ESP, BCD, boot entry, disk, or security setting is changed.",
            "Detected EFI partitions or firmware entries do not prove that an operating system can boot.",
            "UNKNOWN means the state was not established; it must not be interpreted as absent or disabled.",
        ],
    }


def write_live_discovery(result: dict[str, Any], output: str) -> None:
    from pathlib import Path

    Path(output).write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
