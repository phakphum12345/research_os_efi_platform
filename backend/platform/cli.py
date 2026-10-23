from __future__ import annotations

import argparse
import json
from pathlib import Path

from .acpi_graph import topology_for
from .candidate import generate_candidate
from .collector import write_snapshot
from .multihardware import discover_profiles
from .preflight import build_preflight, write_preflight
from .runtime import write_runtime_event
from .validator import validate_candidate
from .research_bridge import capability_report
from .efi_knowledge import knowledge_report
from .research_case import ResearchCase
from .orchestrator import build_plan
from .opencore import validate_opencore
from .pipeline import build_evidence_packet, write_evidence_packet
from .runtime_evidence import RuntimeObservation, create_runtime_evidence, write_runtime_evidence
from .runtime_learning import learn_from_runtime_evidence
from .universal.discovery import discover_product
from .universal.discovery.evidence import write_discovery_result
from .universal.discovery.runner import provider_for
from .universal.platforms import host_platform, normalize_platform, platform_report
from .universal.runtime.engine import RuntimeEngine
from .universal.runtime.evidence import write_session_evidence
from .installer_integrity import verify_installer_artifact


def main():
    p = argparse.ArgumentParser(prog="hackintosh-platform")
    s = p.add_subparsers(dest="command", required=True)

    x = s.add_parser("collect")
    x.add_argument("output")
    x = s.add_parser("discover-product")
    x.add_argument("output")
    x.add_argument("--platform", default=None, choices=["windows", "linux", "macos"])
    x.add_argument("--source-sha", default="local-development")
    x.add_argument("--source-pinned", action="store_true")
    x = s.add_parser("platforms")
    x = s.add_parser("runtime-operations")
    x.add_argument("--platform", default=None, choices=["windows", "linux", "macos"])
    x = s.add_parser("runtime-exec")
    x.add_argument("--platform", default=None, choices=["windows", "linux", "macos"])
    x.add_argument("--operation", required=True)
    x.add_argument("--keep-going", action="store_true")
    x = s.add_parser("runtime-session")
    x.add_argument("output")
    x.add_argument("--platform", default=None, choices=["windows", "linux", "macos"])
    x.add_argument("--operation", action="append", required=True)
    x.add_argument("--case-id", required=True)
    x.add_argument("--hardware-identity-sha", required=True)
    x.add_argument("--source-sha", default="local-development")
    x.add_argument("--keep-going", action="store_true")
    x = s.add_parser("acpi")
    x.add_argument("dsl")
    x.add_argument("--name", action="append", default=[])
    x = s.add_parser("candidate")
    x.add_argument("profile")
    x.add_argument("output")
    x = s.add_parser("validate")
    x.add_argument("efi")
    x = s.add_parser("preflight")
    x.add_argument("profile")
    x.add_argument("efi")
    x.add_argument("experiment")
    x.add_argument("output")
    x = s.add_parser("runtime")
    x.add_argument("event")
    x.add_argument("output")
    x.add_argument("--artifact", action="append", default=[])
    x = s.add_parser("runtime-evidence")
    x.add_argument("output")
    x.add_argument("--case-id", required=True)
    x.add_argument("--source-sha", required=True)
    x.add_argument("--candidate-sha", required=True)
    x.add_argument("--result", choices=["PASSED", "FAILED", "INCONCLUSIVE", "ABORTED"], required=True)
    x.add_argument("--platform", required=True)
    x.add_argument("--observation", action="append", default=[])
    x.add_argument("--artifact", action="append", default=[])
    x = s.add_parser("profiles")
    x.add_argument("--directory", default="hardware")
    s.add_parser("bridge")
    s.add_parser("efi-knowledge")
    x = s.add_parser("validate-opencore")
    x.add_argument("efi")
    x = s.add_parser("verify-installer")
    x.add_argument("artifact")
    x.add_argument("--sha256", required=True, help="Expected SHA-256 from an independent trusted source")
    x.add_argument("--source-url", required=True, help="HTTPS source URL used to obtain the artifact")
    x.add_argument("--expected-size", type=int, default=None)
    x = s.add_parser("plan")
    x.add_argument("profile")
    x.add_argument("--source-sha", required=True)
    x.add_argument("--case-id", default="x1504va-research")
    x = s.add_parser("pipeline")
    x.add_argument("profile")
    x.add_argument("output")
    x.add_argument("--source-sha", required=True)
    x.add_argument("--hypothesis", required=True)
    x.add_argument("--case-id", default="x1504va-research")
    x = s.add_parser("learn-runtime")
    x.add_argument("case")
    x.add_argument("evidence")

    a = p.parse_args()

    if a.command == "collect":
        write_snapshot(a.output)
    elif a.command == "discover-product":
        target = normalize_platform(a.platform or host_platform())
        result = discover_product(
            provider_for(target),
            source_sha=a.source_sha,
            source_pinned=a.source_pinned,
        )
        write_discovery_result(result, a.output)
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
    elif a.command == "platforms":
        print(json.dumps(platform_report(), indent=2, ensure_ascii=False))
    elif a.command == "runtime-operations":
        target = normalize_platform(a.platform or host_platform())
        print(
            json.dumps(
                {
                    "platform": target.value,
                    "operations": RuntimeEngine().manager.operations(target),
                },
                indent=2,
            )
        )
    elif a.command == "runtime-exec":
        target = normalize_platform(a.platform or host_platform())
        session = RuntimeEngine().run(
            target.value,
            [a.operation],
            fail_closed=not a.keep_going,
        )
        print(json.dumps(session.to_dict(), indent=2, ensure_ascii=False))
        return 0 if all(item.returncode == 0 for item in session.results) else 1
    elif a.command == "runtime-session":
        target = normalize_platform(a.platform or host_platform())
        session = RuntimeEngine().run(
            target.value,
            a.operation,
            fail_closed=not a.keep_going,
        )
        write_session_evidence(
            session,
            a.output,
            source_sha=a.source_sha,
            case_id=a.case_id,
            hardware_identity_sha=a.hardware_identity_sha,
        )
        print(json.dumps(session.to_dict(), indent=2, ensure_ascii=False))
        return 0 if all(item.returncode == 0 for item in session.results) else 1
    elif a.command == "acpi":
        lines = Path(a.dsl).read_text(encoding="utf-8", errors="replace").splitlines()
        print(json.dumps(
            topology_for(lines, set(a.name or ["GFX0", "VMD0", "NVD1", "ETPD"])),
            indent=2,
        ))
    elif a.command == "candidate":
        profile = json.loads(Path(a.profile).read_text(encoding="utf-8"))
        print(json.dumps(generate_candidate(profile, a.output), indent=2))
    elif a.command == "validate":
        print(json.dumps(validate_candidate(a.efi), indent=2))
    elif a.command == "preflight":
        profile = json.loads(Path(a.profile).read_text(encoding="utf-8"))
        experiment = json.loads(Path(a.experiment).read_text(encoding="utf-8"))
        result = build_preflight(profile, a.efi, experiment)
        write_preflight(result, a.output)
        print(json.dumps(result, indent=2))
    elif a.command == "runtime":
        write_runtime_event(a.event, a.output, a.artifact)
    elif a.command == "runtime-evidence":
        observations = [RuntimeObservation("other", value) for value in a.observation]
        evidence = create_runtime_evidence(
            a.case_id, a.source_sha, a.candidate_sha, a.result, a.platform,
            observations, a.artifact
        )
        write_runtime_evidence(evidence, a.output)
        print(json.dumps(evidence.to_dict(), indent=2, ensure_ascii=False))
    elif a.command == "profiles":
        print(json.dumps(discover_profiles(a.directory), indent=2))
    elif a.command == "bridge":
        print(json.dumps(capability_report(), indent=2))
    elif a.command == "efi-knowledge":
        print(json.dumps(knowledge_report(), indent=2))
    elif a.command == "validate-opencore":
        print(json.dumps(validate_opencore(a.efi), indent=2))
    elif a.command == "verify-installer":
        result = verify_installer_artifact(
            a.artifact,
            expected_sha256=a.sha256,
            source_url=a.source_url,
            expected_size=a.expected_size,
        )
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if result["status"] == "PASS" else 1
    elif a.command == "pipeline":
        profile = json.loads(Path(a.profile).read_text(encoding="utf-8"))
        packet = build_evidence_packet(
            profile, a.output, a.source_sha, a.hypothesis, a.case_id
        )
        out = Path(a.output) / "evidence-packet.json"
        write_evidence_packet(packet, str(out))
        print(json.dumps(packet, indent=2))
    elif a.command == "plan":
        profile = json.loads(Path(a.profile).read_text(encoding="utf-8"))
        case = ResearchCase.from_profile(
            a.case_id,
            a.source_sha,
            "X1504VA",
            "controlled evidence-first EFI research",
            profile,
            capability_report()["capabilities"],
        )
        print(json.dumps(build_plan(case).to_dict(), indent=2))
    elif a.command == "learn-runtime":
        case_value = json.loads(Path(a.case).read_text(encoding="utf-8"))
        case = ResearchCase(
            case_value["case_id"],
            case_value["source_sha"],
            case_value["profile"],
            case_value["hypothesis"],
            tuple(case_value.get("facts", [])),
            tuple(case_value.get("observations", [])),
            tuple(case_value.get("provenance", [])),
        )
        updated, knowledge = learn_from_runtime_evidence(case, a.evidence)
        print(json.dumps({"case": updated.to_dict(), "knowledge": knowledge.to_dict()}, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
