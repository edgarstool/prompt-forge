import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from prompt_forge.compiler import compile_request  # noqa: E402
from prompt_forge.context_policy import apply_context_policy  # noqa: E402
from prompt_forge.evaluator import evaluate_prompt  # noqa: E402
from prompt_forge.intent import classify_intent  # noqa: E402
from prompt_forge.pipeline import run_pipeline  # noqa: E402
from prompt_forge.risk import check_risk  # noqa: E402
from prompt_forge.router import route_request  # noqa: E402
from prompt_forge.schema import UserRequest  # noqa: E402


class ContinuationReviewEdgeTests(unittest.TestCase):
    def _compile(self, request: str):
        req = UserRequest.from_dict({"request": request})
        intent = classify_intent(req)
        risk = check_risk(req, intent)
        route = route_request(req, intent, risk)
        ctx = apply_context_policy(req, intent, route)
        return compile_request(req, intent, risk, route, ctx)

    def test_polite_sustained_questions_do_not_collapse_to_direct(self):
        for request in (
            "Could you please keep working until the task is complete?",
            "Would you please continue until it is done?",
        ):
            with self.subTest(request=request):
                decision, contract = self._compile(request)
                self.assertNotEqual(decision.execution_mode, "DIRECT")
                self.assertTrue(decision.should_compile)
                self.assertEqual(contract.continuation_policy, "CONTINUE_UNTIL_GOAL")

    def test_conditional_do_not_finish_is_a_sustained_goal_horizon(self):
        decision, contract = self._compile(
            "Don't finish until all tests pass; keep working through failures."
        )
        self.assertNotEqual(decision.execution_mode, "DIRECT")
        self.assertTrue(decision.should_compile)
        self.assertEqual(contract.continuation_policy, "CONTINUE_UNTIL_GOAL")

    def test_double_tampered_single_cut_metadata_fails_against_request_semantics(self):
        result = run_pipeline(
            {
                "request": "持續把這個 repo 做下去，直到整個目標完成。",
                "known_context": ["Repo exists."],
            }
        )
        prompt = copy.deepcopy(result.composition)
        prompt.meta["continuation_policy"] = "SINGLE_CUT"
        prompt.meta["semantic_contract"]["continuation_policy"] = "SINGLE_CUT"

        evaluation = evaluate_prompt(
            result.input,
            result.intent,
            result.risk,
            result.route,
            result.context_policy,
            prompt,
        )
        checks = {check.name: check for check in evaluation.checks}
        self.assertFalse(checks["Continuation discipline"].passed)
        self.assertFalse(evaluation.hard_pass)
        self.assertFalse(evaluation.passed)


if __name__ == "__main__":
    unittest.main()
