import hashlib
import tempfile
import unittest
from pathlib import Path

from backend.platform.installer_integrity import verify_installer_artifact


class InstallerIntegrityTests(unittest.TestCase):
    def verify(self, path, digest, **kwargs):
        return verify_installer_artifact(
            path,
            expected_sha256=digest,
            source_url=kwargs.pop("source_url", "https://support.apple.com/example"),
            **kwargs,
        )

    def test_trusted_digest_and_https_source_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "macOS-Installer.pkg"
            payload = b"test installer fixture"
            path.write_bytes(payload)
            result = self.verify(path, hashlib.sha256(payload).hexdigest(), expected_size=len(payload))
            self.assertEqual(result["status"], "PASS", result["errors"])
            self.assertEqual(result["artifact_type"], "pkg")

    def test_digest_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "InstallAssistant.dmg"
            path.write_bytes(b"downloaded bytes")
            result = self.verify(path, "0" * 64)
            self.assertEqual(result["status"], "FAIL")
            self.assertTrue(any("SHA-256 mismatch" in error for error in result["errors"]))

    def test_digest_must_be_explicit_and_well_formed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "installer.pkg"
            path.write_bytes(b"payload")
            result = self.verify(path, "")
            self.assertEqual(result["status"], "FAIL")
            self.assertIn("expected_sha256 must be 64 hexadecimal characters", result["errors"])

    def test_non_https_source_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "installer.pkg"
            payload = b"payload"
            path.write_bytes(payload)
            result = self.verify(path, hashlib.sha256(payload).hexdigest(), source_url="http://example.com/installer.pkg")
            self.assertEqual(result["status"], "FAIL")
            self.assertTrue(any("HTTPS" in error for error in result["errors"]))

    def test_size_mismatch_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "installer.iso"
            payload = b"payload"
            path.write_bytes(payload)
            result = self.verify(path, hashlib.sha256(payload).hexdigest(), expected_size=len(payload) + 1)
            self.assertEqual(result["status"], "FAIL")
            self.assertTrue(any("size mismatch" in error for error in result["errors"]))

    def test_empty_or_unsupported_artifact_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "installer.exe"
            path.write_bytes(b"payload")
            result = self.verify(path, hashlib.sha256(b"payload").hexdigest())
            self.assertEqual(result["status"], "FAIL")
            self.assertTrue(any("unsupported installer extension" in error for error in result["errors"]))

    def test_missing_file_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "missing.pkg"
            result = self.verify(path, "a" * 64)
            self.assertEqual(result["status"], "FAIL")
            self.assertTrue(any("missing" in error for error in result["errors"]))


if __name__ == "__main__":
    unittest.main()
