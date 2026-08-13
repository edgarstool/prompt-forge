import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from prompt_forge.pipeline import run_pipeline  # noqa: E402
from prompt_forge.schema import REQUIRED_PROMPT_SECTIONS  # noqa: E402

CASES = ROOT / "examples" / "cases"


class PipelineCaseTests(unittest.TestCase):
    def _load(self, name: str):
        with (CASES / name).open(encoding="utf-8") as f:
            return json.load(f)

    def _assert_case(self, filename: str):
        case = self._load(filename)
        result = run_pipeline(case["input"])
        expected = case["expected"]
        self.assertEqual(result.route.task_type, expected["task_type"])
        self.assertEqual(result.route.recommended_agent, expected["recommended_agent"])
        self.assertEqual(result.context_policy.use_context7, expected["use_context7"])
        self.assertEqual(result.risk.level, expected["risk_level"])
        self.assertGreaterEqual(result.evaluation.score, expected.get("min_score", 8))
        self.assertTrue(result.evaluation.passed)
        for section in REQUIRED_PROMPT_SECTIONS:
            self.assertIn(section, result.composition.sections)
            self.assertTrue(result.composition.sections[section].strip())

    def test_case_a_local_files(self):
        self._assert_case("case_a_local_files.json")

    def test_case_b_research(self):
        self._assert_case("case_b_research_vm.json")

    def test_case_c_coding(self):
        self._assert_case("case_c_coding_repo.json")

    def test_case_d_secrets(self):
        self._assert_case("case_d_secrets_deterministic.json")

    def test_secret_not_routed_to_external_agent(self):
        result = run_pipeline(
            {
                "request": "幫我把這些 secret 整理成可匯入清單。",
            }
        )
        self.assertEqual(result.route.recommended_agent, "local-script")
        self.assertTrue(result.risk.forbid_external_secret_exfil)
        self.assertFalse(result.context_policy.use_context7)


if __name__ == "__main__":
    unittest.main()
