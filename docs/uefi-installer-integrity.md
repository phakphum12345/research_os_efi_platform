# UEFI and installer integrity contract

## Purpose

EFI Imaging distinguishes a research candidate from an installable UEFI package. A generated directory or a syntactically valid `config.plist` is not sufficient evidence that the boot payload is complete.

## Package modes

- **candidate**: may contain only an inspectable generated configuration and reports. It can be useful for analysis but is not declared bootable.
- **installable**: must include the x64 removable-media boot path `EFI/BOOT/BOOTx64.efi`, `EFI/OC/OpenCore.efi`, `EFI/OC/config.plist`, and the expected OpenCore ACPI, Drivers, Kexts, Resources, and Tools directories.

The installable check is a structural gate, not proof that each third-party binary is authentic, compatible, or safe. Where a trusted upstream checksum or signature exists, validate it separately before packaging.

## Integrity manifest

`backend/platform/uefi_integrity.py` provides deterministic SHA-256 inventory and verification. Each entry records a safe relative path, file size, and digest. Verification fails closed on missing files, modified bytes, size mismatch, duplicate/unsafe paths, symlinks, or unmanifested files. The manifest does not include its own hash in its file inventory.

EFI candidate generation now writes a candidate-mode manifest automatically, and OpenCore validation checks that manifest when present. Generate the manifest only after all package files are finalized. Any subsequent package change requires regenerating the manifest and rerunning verification. The installable package check remains a separate strict mode because generated research candidates intentionally may not contain bootloader binaries.

## Release acceptance gates

1. UEFI boot path and OpenCore payload present.
2. OpenCore configuration parses and contains required top-level sections.
3. Referenced drivers, kexts, ACPI tables, and tools exist in the package.
4. Trusted-source checksums/signatures are verified where available.
5. SHA-256 manifest verifies with no missing, changed, unsafe, or extra files.
6. Compatibility evidence and source provenance are attached to the candidate.
7. CI and audit pass. This still does not prove the target machine boots successfully.

## Safety boundary

These checks only read package files. They do not format or mount partitions, write an ESP, change BIOS or Secure Boot settings, modify VMD/storage settings, or install a bootloader. Installation and hardware boot experiments remain separate, explicitly approved steps.
