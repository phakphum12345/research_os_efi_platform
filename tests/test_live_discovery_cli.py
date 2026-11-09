import contextlib
import io
import sys
import tempfile
import unittest
from unittest.mock import patch

from backend.platform import cli


class LiveDiscoveryCliExitStatusTests(unittest.TestCase):
    def _run_live_discovery(self, overall_status):
        result = {
            "overall_status": overall_status,
            "platform": "linux",
            "read_only": True,
            "mutation_performed": False,
        }
        with tempfile.TemporaryDirectory() as directory:
            output = str(__import__("pathlib").Path(directory) / "evidence.json")
            with patch.object(sys, "argv", ["platform", "live-discovery", output]):
                with patch.object(cli, "collect_live_discovery", return_value=result):
                    with patch.object(cli, "write_live_discovery"):
                        with contextlib.redirect_stdout(io.StringIO()):
                            return cli.main()

    def test_detected_returns_success(self):
        self.assertEqual(self._run_live_discovery("DETECTED"), 0)

    def test_partial_returns_nonzero(self):
        self.assertEqual(self._run_live_discovery("PARTIAL"), 1)

    def test_unknown_returns_nonzero(self):
        self.assertEqual(self._run_live_discovery("UNKNOWN"), 1)


if __name__ == "__main__":
    unittest.main()
