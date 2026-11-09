# Dual Bootable Images Delivery Plan

## Decision

Deliver all three outputs, in this order:

1. A standalone OpenCore EFI package / image (A), kept separate from the Research OS.
2. A standalone Research OS image (B).
3. A Multi-Boot USB layout that presents both entries, produced only after A and B pass their independent release gates.

The standalone artifacts remain independently usable. The Multi-Boot layout is an additional packaging target, not a combined operating system image.

## Repository boundary

This repository is the EFI and hardware-research platform. Research OS remains a separate product/codebase. Any Research OS source, kernel, root filesystem, runtime, or database must not be silently imported as a runtime dependency into this repository. Cross-project integration must use documented, versioned artifact or API contracts.

## A — OpenCore EFI / macOS installation path

Current state is research-only. The tracked ASUS Vivobook X1504VA profile is intentionally blocked because Intel UHD 8086:A7A9 acceleration and Intel VMD storage behavior are not proven. MT7902 Wi-Fi, Bluetooth, touchpad ACPI, and audio layout also require evidence.

Release gates:

- Obtain OpenCore and every driver, kext, ACPI table, and resource from trusted upstream sources; pin versions and independently verify available signatures/checksums.
- Generate a machine-specific config only from verified hardware evidence. Do not mark a candidate installable merely because config.plist parses or required filenames exist.
- Use only a legally obtained, vendor-provided macOS installer. Do not bundle or redistribute macOS proprietary installer payloads.
- Validate the complete package manifest and referenced files.
- Run static/configuration tests and a virtual UEFI smoke test where technically meaningful.
- Keep X1504VA marked BLOCKED until GPU and VMD evidence supports the intended macOS version and a real-machine boot test succeeds.

An installable structural manifest is not proof of binary authenticity, hardware compatibility, or successful boot.

## B — Research OS image

Initial implementation target: a custom Research OS distribution based on a pinned, supported upstream Linux kernel, not a kernel written from scratch. Research OS owns its kernel configuration/patch set, boot configuration, initramfs, root filesystem, userland, installer, update/recovery model, and Control Center integration.

Required design/build stages:

1. Define target architecture (initially x86_64 UEFI), kernel baseline and license inventory.
2. Create reproducible kernel and initramfs build inputs with pinned versions and source provenance.
3. Assemble a minimal root filesystem with init, essential system services, user/session model, storage/network diagnostics, and recovery shell.
4. Integrate the Research OS Control Center through explicit local service/API contracts; do not assume the separate EFI platform backend is an OS runtime.
5. Build a bootable ISO and, if supported, a raw USB image. Publish SHA-256 manifests and SBOM/provenance.
6. Test UEFI boot in QEMU/OVMF, install/upgrade/recovery in disposable virtual disks, and hardware discovery on the target laptop without writing to its internal disk.

## C — Multi-Boot USB

### Implemented safe staging foundation (not a bootable release)

The isolated branch now contains `backend/platform/multiboot.py`, a CLI entry point, and unit tests for a non-destructive staging-directory composer. It:

- accepts an already-built x86_64 GRUB UEFI PE/COFF binary, an OpenCore EFI tree, a Research OS ISO-9660 image, and a Research OS-provided GRUB menu fragment;
- builds a new staging directory only and refuses to overwrite an existing output directory;
- places GRUB at the removable-media UEFI path, preserves OpenCore under `EFI/OC`, places the Research OS ISO under `images/`, and combines the menu entries;
- creates and verifies a SHA-256 inventory, rejecting symlinks, missing/extra files, size changes, and hash mismatches.

CLI:

```powershell
python -m backend.platform.cli multiboot-stage --opencore-efi-root .\\input\\EFI --research-os-iso .\\input\\research-os.iso --grub-efi-binary .\\input\\grubx64.efi --research-os-grub-entry .\\input\\research-os.cfg --output .\\out\\multiboot
python -m backend.platform.cli verify-multiboot .\\out\\multiboot
```

This is only a package-staging and integrity foundation. It does not create GRUB, create the Research OS ISO, prove that the supplied Research OS GRUB fragment can boot its ISO, perform a QEMU boot, or write to physical USB media. The supplied GRUB binary and OS menu fragment remain trusted build inputs and require independent provenance/signature review. Unit fixtures are structural tests, not boot evidence.


Create a separate, non-destructive layout specification and builder after A and B have independent artifacts. The menu must contain distinct entries for OpenCore and Research OS, with explicit labels and independent paths. Validate paths, hashes, file sizes, filesystem limits, and boot configuration. Prefer a data-preserving file-copy workflow where the chosen USB filesystem and firmware support it; document any limitation that would require repartitioning.

Do not write to a physical USB device, repartition/format media, alter the internal EFI System Partition, change BIOS/Secure Boot/VMD settings, or install a bootloader without a separate, explicit approval naming the target device and operation.

## Required verification and release evidence

- Unit tests for image assembly, manifests, path traversal/symlink rejection, and Multi-Boot menu generation.
- Reproducible build metadata: source commit, toolchain versions, upstream source URLs, pinned versions, artifact size, SHA-256, and SBOM.
- QEMU/OVMF UEFI boot evidence for each artifact independently, then for the Multi-Boot menu.
- Hardware results must be reported separately from VM results.
- CI Required Checks and repository audit must pass before a PR is eligible for merge.
- Never claim a release is hardware-bootable based only on structural checks or CI.

## Execution sequence

READ current repository and workflows → ANALYZE architecture and missing prerequisites → MODIFY on an isolated branch → TEST each artifact and safety boundary → AUDIT manifests, provenance, CI, and release claims.

No merge is authorized by this plan. No destructive media or firmware operation is authorized by this plan.
