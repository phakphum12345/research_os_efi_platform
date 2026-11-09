import json
import struct
import tempfile
import unittest
from pathlib import Path

from backend.platform.multiboot import (
    MANIFEST_NAME,
    build_multiboot_staging,
    verify_multiboot_staging,
)


def _write_pe(path: Path, machine: int = 0x8664) -> None:
    payload = bytearray(0x90)
    payload[:2] = b"MZ"
    struct.pack_into("<I", payload, 0x3C, 0x80)
    payload[0x80:0x84] = b"PE\0\0"
    struct.pack_into("<H", payload, 0x84, machine)
    path.write_bytes(payload)


def _write_iso(path: Path) -> None:
    payload = bytearray(17 * 2048)
    payload[16 * 2048 : 16 * 2048 + 7] = b"\x01CD001\x01"
    path.write_bytes(payload)


def _make_inputs(root: Path):
    oc = root / "opencore"
    (oc / "OC" / "ACPI").mkdir(parents=True)
    for folder in ("Drivers", "Kexts", "Resources", "Tools"):
        (oc / "OC" / folder).mkdir()
    (oc / "OC" / "OpenCore.efi").write_bytes(b"fixture-opencore-binary")
    (oc / "OC" / "config.plist").write_text("<plist/>", encoding="utf-8")
    (oc / "OC" / "Drivers" / "OpenRuntime.efi").write_bytes(b"driver")
    iso = root / "research-os.iso"
    _write_iso(iso)
    grub = root / "grubx64.efi"
    _write_pe(grub)
    entry = root / "research-os.cfg"
    entry.write_text(
        "menuentry 'Research OS' {\n"
        "  loopback loop /images/research-os.iso\n"
        "  # Kernel/initramfs boot commands are supplied by the Research OS build.\n"
        "}\n",
        encoding="utf-8",
    )
    return oc, iso, grub, entry


class MultiBootStagingTests(unittest.TestCase):
    def test_builds_and_verifies_staging_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            oc, iso, grub, entry = _make_inputs(root)
            output = root / "multiboot"
            manifest = build_multiboot_staging(oc, iso, grub, entry, output)
            self.assertEqual(manifest["status"], "PASS")
            self.assertTrue((output / "EFI/BOOT/BOOTx64.efi").is_file())
            self.assertTrue((output / "EFI/OC/OpenCore.efi").is_file())
            self.assertTrue((output / "images/research-os.iso").is_file())
            config = (output / "boot/grub/grub.cfg").read_text(encoding="utf-8")
            self.assertIn("chainloader /EFI/OC/OpenCore.efi", config)
            self.assertIn("source /boot/grub/research-os.cfg", config)
            result = verify_multiboot_staging(output)
            self.assertEqual(result["status"], "PASS", result["errors"])
            self.assertTrue((output / MANIFEST_NAME).is_file())

    def test_refuses_to_overwrite_existing_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            oc, iso, grub, entry = _make_inputs(root)
            output = root / "multiboot"
            output.mkdir()
            sentinel = output / "keep.txt"
            sentinel.write_text("preserve", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "must not exist"):
                build_multiboot_staging(oc, iso, grub, entry, output)
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "preserve")

    def test_rejects_non_x86_64_grub_binary(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            oc, iso, grub, entry = _make_inputs(root)
            _write_pe(grub, machine=0xAA64)
            with self.assertRaisesRegex(ValueError, "x86_64"):
                build_multiboot_staging(oc, iso, grub, entry, root / "multiboot")

    def test_rejects_non_iso_input(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            oc, iso, grub, entry = _make_inputs(root)
            iso.write_bytes(b"not an iso")
            with self.assertRaisesRegex(ValueError, "ISO-9660"):
                build_multiboot_staging(oc, iso, grub, entry, root / "multiboot")

    def test_rejects_missing_research_os_menu_entry(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            oc, iso, grub, entry = _make_inputs(root)
            entry.write_text("set timeout=0\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "menuentry"):
                build_multiboot_staging(oc, iso, grub, entry, root / "multiboot")

    def test_tampered_staging_file_fails_verification(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            oc, iso, grub, entry = _make_inputs(root)
            output = root / "multiboot"
            build_multiboot_staging(oc, iso, grub, entry, output)
            (output / "EFI/OC/OpenCore.efi").write_bytes(b"tampered")
            result = verify_multiboot_staging(output)
            self.assertEqual(result["status"], "FAIL")
            self.assertTrue(any("SHA-256 mismatch" in item for item in result["errors"]))

    def test_unmanifested_file_fails_verification(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            oc, iso, grub, entry = _make_inputs(root)
            output = root / "multiboot"
            build_multiboot_staging(oc, iso, grub, entry, output)
            (output / "unexpected.bin").write_bytes(b"unexpected")
            result = verify_multiboot_staging(output)
            self.assertEqual(result["status"], "FAIL")
            self.assertTrue(any("unmanifested file" in item for item in result["errors"]))

    def test_rejects_symlink_in_opencore_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            oc, iso, grub, entry = _make_inputs(root)
            target = oc / "OC" / "Resources" / "escape"
            target.symlink_to(root, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "symlink"):
                build_multiboot_staging(oc, iso, grub, entry, root / "multiboot")


if __name__ == "__main__":
    unittest.main()
