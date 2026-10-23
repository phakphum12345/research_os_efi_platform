# Installer artifact integrity contract

## Scope

This gate is separate from the UEFI/OpenCore folder manifest. It verifies a downloaded installer file such as `.dmg`, `.pkg`, `.iso`, or `.zip` against an independently obtained SHA-256 digest and optional expected byte size.

## Trust rule

- Obtain the expected digest from an official vendor page or a trusted, independently authenticated release channel.
- Do not treat a digest downloaded from the same untrusted mirror as independent proof.
- This module never downloads files or looks up expected hashes automatically.
- The source URL must use HTTPS; that alone does not prove the source is authentic.

## Python API

`backend/platform/installer_integrity.py::verify_installer_artifact`

Required inputs: local artifact path, expected SHA-256, and source URL. Optional input: expected size. It streams the file in chunks, rejects missing/empty/unsupported files, checks the expected size when provided, and fails closed when the digest differs.

## Command-line use

Run from the repository root after obtaining the expected digest from an independent trusted source:

```powershell
python -m backend.platform.cli verify-installer .\\downloads\\InstallAssistant.pkg --sha256 YOUR_TRUSTED_SHA256 --source-url https://support.apple.com/example --expected-size YOUR_EXPECTED_BYTES
```

The command emits a JSON report and returns exit code 0 only when verification passes; otherwise it returns 1. Replace the example URL and values with the actual source and independently verified digest. Do not paste secrets into command-line arguments.

## Separate release gates

1. Verify the installer checksum against an independent trusted source.
2. On macOS, separately verify the Apple/vendor code signature and package assessment using the platform's supported tools when applicable.
3. Validate the UEFI/OpenCore package manifest.
4. Validate config references, ACPI, drivers, kexts, and tools.
5. Attach source commit, source URL, expected digest, actual digest, and validation report to the evidence packet.
6. Test the actual target hardware separately; matching a digest does not prove that the installer is genuine unless the expected digest source is trusted, nor does it prove boot compatibility.

No installer is downloaded, executed, mounted, or installed by this checker. It does not alter the EFI System Partition, firmware, Secure Boot, VMD/storage settings, or bootloader.
