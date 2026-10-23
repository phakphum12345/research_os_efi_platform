import unittest

from backend.platform.research_bridge import (
    DEFAULT_CAPABILITIES,
    RESEARCH_OS_COMMIT,
    RESEARCH_OS_REPO,
    capability_report,
)


class ResearchBridgeTests(unittest.TestCase):
    def test_report_pins_canonical_source_and_commit(self):
        report = capability_report()
        self.assertEqual(report["source_repository"], RESEARCH_OS_REPO)
        self.assertEqual(report["source_commit"], RESEARCH_OS_COMMIT)
        self.assertEqual(report["source_policy"], "PROVENANCE_REQUIRED")
        self.assertEqual(report["project_boundary"], "NO_SHARED_RUNTIME_OR_DATA")
        self.assertEqual(len(RESEARCH_OS_COMMIT), 40)

    def test_every_capability_has_complete_provenance(self):
        for capability in DEFAULT_CAPABILITIES:
            self.assertEqual(capability.source_repo, RESEARCH_OS_REPO)
            self.assertEqual(len(capability.source_commit), 40)
            self.assertRegex(capability.source_blob_sha, r"^[0-9a-f]{40}$")
            self.assertTrue(capability.source_path)
            self.assertTrue(capability.target_component)
            self.assertTrue(capability.adaptation_reason)

    def test_reference_only_components_are_not_claimed_as_implemented(self):
        report = capability_report()
        by_id = {item["capability_id"]: item for item in report["capabilities"]}
        self.assertEqual(by_id["work-checkpoint"]["adoption_status"], "REFERENCE_ONLY")
        self.assertEqual(by_id["semantic-change-validation"]["adoption_status"], "REFERENCE_ONLY")
        self.assertEqual(by_id["evidence-manifest"]["adoption_status"], "ADAPTED_EXISTING")

    def test_report_does_not_offer_shared_runtime_or_data(self):
        report = capability_report()
        self.assertEqual(report["project_boundary"], "NO_SHARED_RUNTIME_OR_DATA")
        for capability in report["capabilities"]:
            self.assertNotIn("shared service", capability["adaptation_reason"].lower())


if __name__ == "__main__":
    unittest.main()
