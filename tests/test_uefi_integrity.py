import json
import tempfile
import unittest
from pathlib import Path

from backend.platform.uefi_integrity import (
    MANIFEST_NAME,
    build_integrity_manifest,
    verify_integrity_manifest,
    write_integrity_manifest,
)


def create_installable_tree(root: Path) -> None:
    paths = [
        "EFI/BOOT/BOOTx64.efi",
        "EFI/OC/OpenCore.efi",
        "EFI/OC/config.plist",
        "EFI/OC/Drivers/OpenRuntime.efi",
        "EFI/OC/Kexts/Lilu.kext/Contents/Info.plist",
        "EFI/OC/ACPI/SSDT-Test.aml",
        "EFI/OC/Resources/README.txt",
        "EFI/OC/Tools/OpenShell.efi",
    ]
    for relative in paths:
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(("fixture:" + relative).encode())


class UEFIIntegrityTests(unittest.TestCase):
    def test_candidate_manifest_is_deterministic_and_verifies(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "EFI" / "OC").mkdir(parents=True)
            (root / "EFI" / "OC" / "compatibility-report.json").write_text('{"status":"BLOCKED"}')
            first = build_integrity_manifest(root)
            second = build_integrity_manifest(root)
            self.assertEqual(first, second)
            write_integrity_manifest(root)
            result = verify_integrity_manifest(root)
            self.assertEqual(result["status"], "PASS")

    def test_installable_manifest_blocks_missing_core_boot_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "EFI" / "OC").mkdir(parents=True)
            manifest = build_integrity_manifest(root, artifact_type="installable")
            self.assertEqual(manifest["status"], "BLOCKED")
            self.assertTrue(any("BOOTx64.efi" in error for error in manifest["errors"]))

    def test_installable_package_passes_with_required_payload(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            create_installable_tree(root)
            write_integrity_manifest(root, artifact_type="installable")
            result = verify_integrity_manifest(root, require_installable=True)
            self.assertEqual(result["status"], "PASS", result["errors"])
            self.assertGreaterEqual(result["verified_files"], 8)

    def test_tampered_file_fails_hash_verification(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            create_installable_tree(root)
            write_integrity_manifest(root, artifact_type="installable")
            (root / "EFI" / "OC" / "OpenCore.efi").write_bytes(b"tampered")
            result = verify_integrity_manifest(root, require_installable=True)
            self.assertEqual(result["status"], "FAIL")
            self.assertTrue(any("SHA-256 mismatch" in error for error in result["errors"]))

    def test_unmanifested_extra_file_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            create_installable_tree(root)
            write_integrity_manifest(root, artifact_type="installable")
            (root / "unexpected.bin").write_bytes(b"new file")
            result = verify_integrity_manifest(root, require_installable=True)
            self.assertEqual(result["status"], "FAIL")
            self.assertTrue(any("unmanifested package file" in error for error in result["errors"]))

    def test_unsafe_manifest_path_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertEqual(
                verify_integrity_manifest(root, manifest_name="../outside.json")["status"],
                "FAIL",
            )

    def test_noncanonical_manifest_paths_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            create_installable_tree(root)
            path = write_integrity_manifest(root, artifact_type="installable")
            payload = json.loads(path.read_text())
            payload["files"][0]["path"] = "./" + payload["files"][0]["path"]
            path.write_text(json.dumps(payload))
            result = verify_integrity_manifest(root, require_installable=True)
            self.assertEqual(result["status"], "FAIL")
            self.assertTrue(any("unsafe or recursive" in error for error in result["errors"]))

    def test_manifest_file_is_excluded_from_its_own_hash_inventory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            create_installable_tree(root)
            path = write_integrity_manifest(root, artifact_type="installable")
            payload = json.loads(path.read_text())
            self.assertNotIn(MANIFEST_NAME, [entry["path"] for entry in payload["files"]])


if __name__ == "__main__":
    unittest.main()
