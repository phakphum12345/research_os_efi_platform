# Research OS component adoption into EFI Imaging

- Document ID: EFI-ROS-ADOPTION-001
- Version: 1.0.0
- Status: IMPLEMENTATION PLAN / SOURCE-VERIFIED
- Target: `phakphum12345/research_os_efi_platform`
- Reference source: `phakphum12345/ENTERPRISE_API_ARCHITECTURE_LOGIC_TH` at `80bb70458e107da64b3f822594709b9a5225df39`
- Rule: adapt patterns and contracts; do not import or share Research OS runtime, databases, external adapters, credentials, or evidence stores.

## Goal

Strengthen EFI Imaging one component at a time by reusing proven architectural patterns while keeping EFI-specific behavior, safety controls, and evidence inside this repository. Existing EFI components are reused first; this plan is not permission to duplicate capabilities.

## Component map

| Research OS pattern | EFI-native integration point | State | Acceptance evidence |
|---|---|---|---|
| Immutable evidence manifest and source fingerprints (`tools/aeos_autobot_evidence_manifest.py`) | `backend/platform/manifest.py`, `backend/platform/evidence.py` | Adapted existing implementation | Deterministic digest tests; candidate and source hashes recorded |
| Fail-closed orchestration (`tools/aeos_autobot_orchestrator.py`) | `backend/platform/pipeline.py`, `backend/platform/preflight.py` | Adapted existing implementation | Missing/failed prerequisites block downstream candidate promotion |
| Human authority boundary (`v3/research_os_v3/authority_boundary.py`) | `backend/platform/authority.py`, `backend/platform/experiments.py` | Adapted existing implementation | Validation never grants hardware-mutation authority |
| Work checkpoint / resume guards (`tools/platform_work_checkpoint.py`) | Future EFI-native checkpoint contract | Reference only; next component | Resume only when repository identity, source SHA, checkpoint schema, and evidence references validate; drift fails closed |
| Semantic source-change validation (`owner_special/research_os_friend/aeos_semantic_diff.py`) | `backend/platform/validator.py` and CI contract tests | Reference only; incremental adoption | Tests catch meaningful contract changes without importing source implementation |

## EFI-specific lifecycle

```text
DISCOVER HARDWARE
  -> NORMALIZE IDENTITY
  -> COLLECT SOURCES
  -> ASSESS EVIDENCE
  -> BUILD EFI CANDIDATE
  -> VALIDATE CONTRACTS
  -> PREFLIGHT
  -> HUMAN-APPROVED EXPERIMENT
  -> OBSERVE RUNTIME
  -> IMMUTABLE EVIDENCE
  -> LEARN / REVISE
```

Every transition must preserve source provenance. `READY_FOR_HUMAN_BOOT` is a repository-side readiness state only; it is not proof of bootability and does not authorize a boot experiment.

## Explicit non-goals

- No Research OS package imports or network service dependency.
- No shared Research OS database, runtime, credentials, adapters, checkpoints, or evidence store.
- No automatic BIOS, Secure Boot, VMD, ESP, disk, firmware, or bootloader mutation.
- No promotion from observed PCI/USB IDs to macOS support without runtime evidence.
- No claim that CI success proves hardware compatibility.

## Component delivery sequence

1. **Provenance baseline:** pin the source repository, commit, file paths, and blob SHAs in `backend/platform/research_bridge.py`.
2. **Checkpoint continuity:** design an EFI-native schema; bind resumable work to canonical repository SHA and evidence references; reject drift.
3. **Semantic validation:** define contract-sensitive fields and add tests for changes that must fail closed.
4. **Evidence hardening:** verify manifests are deterministic and candidate artifacts are fingerprinted.
5. **Gate audit:** confirm pipeline/preflight gates block on unknown, missing, conflicting, or stale evidence.
6. **Full audit:** run the Python test suite and CI, review the diff and source provenance, then merge only when required gates pass.

## Source provenance

The source commit is pinned for reproducibility. Individual source file blob SHAs are recorded in `backend/platform/research_bridge.py`. If the canonical Research OS source advances, update the bridge only after reviewing the diff; never silently follow a moving branch.
