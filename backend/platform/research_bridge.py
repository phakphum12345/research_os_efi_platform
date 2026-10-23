from dataclasses import asdict, dataclass

# Research OS remains a separate project. These are provenance references to
# architectural patterns, not runtime imports or shared data stores.
RESEARCH_OS_REPO = "phakphum12345/ENTERPRISE_API_ARCHITECTURE_LOGIC_TH"
RESEARCH_OS_COMMIT = "80bb70458e107da64b3f822594709b9a5225df39"


@dataclass(frozen=True)
class Capability:
    capability_id: str
    name: str
    source_repo: str
    source_commit: str
    source_path: str
    source_blob_sha: str
    source_symbol: str
    adaptation_reason: str
    target_component: str
    adoption_status: str


DEFAULT_CAPABILITIES = (
    Capability(
        "evidence-manifest",
        "Immutable evidence manifest and source fingerprints",
        RESEARCH_OS_REPO,
        RESEARCH_OS_COMMIT,
        "tools/aeos_autobot_evidence_manifest.py",
        "d760ec69b4ffc7b97db93672c72237c15f06ebd2",
        "SnapshotLock/build_manifest/verify_manifest",
        "Use the pattern to bind EFI research results to source and artifact digests; retain the EFI-native manifest implementation.",
        "backend.platform.manifest + backend.platform.evidence",
        "ADAPTED_EXISTING",
    ),
    Capability(
        "fail-closed-orchestration",
        "Fail-closed multi-step orchestration",
        RESEARCH_OS_REPO,
        RESEARCH_OS_COMMIT,
        "tools/aeos_autobot_orchestrator.py",
        "5bc290839854a20c2427a0934b9cdf52dbf31a42",
        "run_wave/Job/WaveResult",
        "Use explicit per-step outcomes and stop on missing or failed prerequisites; do not import the Research OS orchestrator.",
        "backend.platform.pipeline + backend.platform.preflight",
        "ADAPTED_EXISTING",
    ),
    Capability(
        "authority-boundary",
        "Preparation and human authority separation",
        RESEARCH_OS_REPO,
        RESEARCH_OS_COMMIT,
        "v3/research_os_v3/authority_boundary.py",
        "45bebc53292e9eaad3fd8e9e184b06e33cc532d1",
        "AuthorityBoundary.evaluate",
        "EFI generation and validation must never imply permission to alter BIOS, ESP, firmware, Secure Boot, storage, or bootloader state.",
        "backend.platform.authority",
        "ADAPTED_EXISTING",
    ),
    Capability(
        "work-checkpoint",
        "Resumable work checkpoint tied to canonical source SHA",
        RESEARCH_OS_REPO,
        RESEARCH_OS_COMMIT,
        "tools/platform_work_checkpoint.py",
        "a721f100872d257fb48874c54f4b236f7cf2485e",
        "checkpoint validation and resume guards",
        "Adapt only the source-SHA and evidence-reference continuity contract; store EFI project checkpoints in this repository's own schema and storage.",
        "planned EFI-native checkpoint contract; no Research OS service dependency",
        "REFERENCE_ONLY",
    ),
    Capability(
        "semantic-change-validation",
        "Semantic source-change validation",
        RESEARCH_OS_REPO,
        RESEARCH_OS_COMMIT,
        "owner_special/research_os_friend/aeos_semantic_diff.py",
        "41d26f7eff4c11b1cc7bed99dfdbe51e1bb3facc",
        "semantic diff validation",
        "Adapt the principle of checking meaningful contract changes rather than copying the Research OS implementation.",
        "backend.platform.validator + CI contract tests",
        "REFERENCE_ONLY",
    ),
)


def capability_report():
    capabilities = [asdict(item) for item in DEFAULT_CAPABILITIES]
    for item in capabilities:
        item["source_sha"] = item["source_commit"]
    return {
        "schema_version": "2.0",
        "bridge": "research-os-to-efi-platform",
        # Preserve the established API value for existing callers.
        "source_policy": "PROVENANCE_REQUIRED",
        "project_boundary": "NO_SHARED_RUNTIME_OR_DATA",
        "source_repository": RESEARCH_OS_REPO,
        "source_commit": RESEARCH_OS_COMMIT,
        "capabilities": capabilities,
    }
