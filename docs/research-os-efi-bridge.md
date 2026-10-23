# Research OS to EFI Imaging bridge

- Document ID: EFI-ROS-BRIDGE-001
- Version: 2.0.0
- Status: ACTIVE / PROVENANCE-PINNED
- Canonical reference repository: `phakphum12345/ENTERPRISE_API_ARCHITECTURE_LOGIC_TH`
- Reference commit: `80bb70458e107da64b3f822594709b9a5225df39`
- Component inventory: [research-os-component-adoption.md](research-os-component-adoption.md)

## Boundary

Research OS and EFI Imaging are separate projects. This bridge records provenance and adaptation decisions only. EFI Imaging must not import Research OS modules as runtime dependencies or share its database, evidence store, credentials, checkpoints, or external adapters.

## Reused architectural patterns

- Immutable evidence manifest and source fingerprinting → EFI-native `backend.platform.manifest` and `backend.platform.evidence`.
- Fail-closed orchestration → EFI-native pipeline and preflight gates.
- Human authority boundary → EFI-native authority policy; generation and validation do not authorize hardware mutation.
- Work checkpoint and semantic-change validation → reference-only until EFI-native contracts and tests are implemented.

Source paths, blob SHAs, target components, and adoption statuses are maintained in `backend/platform/research_bridge.py`. Do not follow a moving branch implicitly; update pinned provenance only after reviewing the source diff.

## EFI lifecycle

```text
COLLECT -> NORMALIZE -> REASON -> BUILD_CANDIDATE -> VALIDATE
       -> PREFLIGHT -> HUMAN-APPROVED EXPERIMENT -> OBSERVE
       -> EVIDENCE -> LEARN
```

## Safety and evidence

- GPU `8086:A7A9`, VMD/storage `8086:09AB` / `8086:A77F`, and MT7902 Wi-Fi `14C3:7902` remain unproven for macOS until relevant runtime evidence exists.
- `READY_FOR_HUMAN_BOOT` is repository-side readiness only, not proof of bootability.
- No automatic BIOS, ESP, Secure Boot, VMD, disk, firmware, or bootloader mutation is allowed.
- CI success and valid configuration files do not by themselves prove hardware compatibility.
