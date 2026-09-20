from pathlib import Path
import unittest

from aidlc.api import dashboard_payload
from aidlc.models import RunRequest
from aidlc.skills import STAGE_SKILLS, architecture_payload, discover_skills, load_skill_context


ROOT = Path(__file__).resolve().parents[1]


class FrameworkTest(unittest.TestCase):
    def test_official_and_platform_skills_are_present(self):
        skills = discover_skills(ROOT)
        self.assertIn("openspec-propose", skills)
        self.assertIn("openspec-apply-change", skills)
        self.assertIn("aidlc-python-development", skills)
        self.assertIn("aidlc-security-review", skills)

    def test_every_pipeline_stage_has_registered_skills(self):
        skills = discover_skills(ROOT)
        for stage, names in STAGE_SKILLS.items():
            with self.subTest(stage=stage):
                self.assertTrue(names)
                self.assertTrue(all(name in skills for name in names))

    def test_skill_context_is_loaded(self):
        context = load_skill_context(["openspec-apply-change", "aidlc-python-development"], ROOT)
        self.assertIn("SKILL", context)
        self.assertIn("Python Development", context)

    def test_customer_input_contract(self):
        request = RunRequest()
        self.assertEqual(request.base_branch, "main")
        self.assertEqual(request.requirement_file, "demo/GITHUB_ISSUE.md")
        self.assertEqual(request.model, "glm-5.2")

    def test_architecture_exposes_cloud_boundaries(self):
        payload = architecture_payload()
        self.assertEqual(payload["execution_region"], "Huawei Cloud sa-brazil-1")
        self.assertEqual(payload["model_region"], "Huawei Cloud ap-southeast-1")
        self.assertIn("Huawei Cloud DCS Redis", payload["components"])

    def test_dashboard_aggregates_history_tokens_and_events(self):
        class FakeBus:
            def list_runs(self, limit=100):
                return [{
                    "run_id": "run-test",
                    "status": "COMPLETED",
                    "created_at": "2026-09-19T10:00:00+00:00",
                    "updated_at": "2026-09-19T10:00:12+00:00",
                    "final_decision": "ALLOW_PR",
                    "request": {"repository": "https://example.test/repo", "base_branch": "main"},
                    "results": {
                        "dev": {"outputs": {"model": {"usage": {"prompt_tokens": 100, "completion_tokens": 20}}}},
                        "review": {"outputs": {"model_review": {"usage": {"prompt_tokens": 40, "completion_tokens": 10}}}},
                    },
                    "pull_request": {"number": 7, "url": "https://example.test/pull/7"},
                }]

            def events(self, run_id):
                return [{"at": "2026-09-19T10:00:01+00:00", "actor": "aidlc-api"}]

        payload = dashboard_payload(FakeBus())
        self.assertEqual(payload["summary"]["total_runs"], 1)
        self.assertEqual(payload["summary"]["success_rate"], 100.0)
        self.assertEqual(payload["summary"]["total_tokens"], 170)
        self.assertEqual(payload["runs"][0]["event_count"], 1)
        self.assertEqual(payload["runs"][0]["duration_seconds"], 12.0)


if __name__ == "__main__":
    unittest.main()
