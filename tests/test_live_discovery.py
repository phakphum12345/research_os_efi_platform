import json
import subprocess
import unittest

from backend.platform.live_discovery import collect_live_discovery


class LiveDiscoveryTests(unittest.TestCase):
    def test_non_windows_reports_unknown_without_running_commands(self):
        def forbidden(_command):
            raise AssertionError("non-Windows discovery must not run PowerShell")

        result = collect_live_discovery("linux", runner=forbidden)
        self.assertEqual(result["overall_status"], "UNKNOWN")
        self.assertTrue(result["read_only"])
        self.assertFalse(result["mutation_performed"])
        self.assertTrue(all(
            item["status"] == "UNKNOWN"
            for item in result["evidence"].values()
        ))

    def test_windows_collects_read_only_evidence_and_marks_partial(self):
        def runner(command):
            if "Confirm-SecureBootUEFI" in command:
                return subprocess.CompletedProcess([], 0, '{"supported":true,"enabled":false}', "")
            if "bcdedit.exe" in command:
                return subprocess.CompletedProcess([], 1, "", "access denied")
            if "Win32_BIOS" in command:
                return subprocess.CompletedProcess([], 0, '{"SMBIOSBIOSVersion":"test"}', "")
            if "Win32_DiskDrive" in command:
                return subprocess.CompletedProcess([], 0, '[{"Model":"disk"}]', "")
            if "Get-Partition" in command:
                return subprocess.CompletedProcess([], 0, '', "")
            self.fail("unexpected query")

        result = collect_live_discovery("windows", runner=runner)
        self.assertEqual(result["overall_status"], "PARTIAL")
        self.assertEqual(result["evidence"]["bios"]["status"], "DETECTED")
        self.assertEqual(result["evidence"]["disks"]["value"][0]["Model"], "disk")
        self.assertEqual(result["evidence"]["efi_system_partitions"]["status"], "UNKNOWN")
        self.assertEqual(result["evidence"]["secure_boot"]["value"], {"enabled": False})
        self.assertEqual(result["evidence"]["firmware_boot_entries"]["status"], "UNKNOWN")
        self.assertFalse(result["mutation_performed"])
        self.assertTrue(result["collected_at"])

    def test_json_writer_emits_valid_document(self):
        result = collect_live_discovery("linux")
        import tempfile
        from pathlib import Path
        from backend.platform.live_discovery import write_live_discovery

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "evidence.json"
            write_live_discovery(result, str(path))
            self.assertEqual(json.loads(path.read_text())["platform"], "linux")


if __name__ == "__main__":
    unittest.main()
