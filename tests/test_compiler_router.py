import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from prompt_forge.compiler import compile_request  # noqa: E402
from prompt_forge.intent import classify_intent  # noqa: E402
from prompt_forge.risk import check_risk  # noqa: E402
from prompt_forge.router import route_request  # noqa: E402
from prompt_forge.context_policy import apply_context_policy  # noqa: E402
from prompt_forge.schema import UserRequest  # noqa: E402


class CompilerRouterTests(unittest.TestCase):
    def _compile(self, payload):
        req = UserRequest.from_dict(payload)
        intent = classify_intent(req)
        risk = check_risk(req, intent)
        route = route_request(req, intent, risk)
        ctx = apply_context_policy(req, intent, route)
        return compile_request(req, intent, risk, route, ctx)

    def test_coding_handoff_compiles_bounded_contract(self):
        decision, contract = self._compile(
            {
                "request": "給 Codex 一個任務，把登入 callback bug 修好並驗證。",
                "preferred_agent": "codex",
                "known_context": ["Repo exists and the failure is reproducible."],
            }
        )
        self.assertEqual(decision.execution_mode, "BUILD")
        self.assertTrue(decision.should_compile)
        self.assertIn("Repo exists", contract.evidence[0])
        self.assertTrue(contract.goal)
        self.assertIn("observable", contract.acceptance.lower())
        self.assertIn("evidence", contract.evidence_return.lower())

    def test_browser_operator_mode_detected(self):
        decision, contract = self._compile(
            {
                "request": "叫 Claude in Chrome 幫我把 Cloudflare dashboard 這個設定改好並讀回確認。",
                "preferred_agent": "claude-in-chrome",
            }
        )
        self.assertEqual(decision.execution_mode, "BROWSER_OPERATOR")
        self.assertTrue(decision.should_compile)
        self.assertIn("read-back", contract.acceptance.lower())

    def test_browser_work_routes_to_capability_without_brand_hint(self):
        req = UserRequest.from_dict(
            {
                "request": "把 Cloudflare dashboard 裡的設定改好並讀回確認。",
            }
        )
        intent = classify_intent(req)
        risk = check_risk(req, intent)
        route = route_request(req, intent, risk)
        ctx = apply_context_policy(req, intent, route)
        decision, _ = compile_request(req, intent, risk, route, ctx)
        self.assertEqual(decision.execution_mode, "BROWSER_OPERATOR")
        self.assertEqual(route.recommended_agent, "browser-operator")
        self.assertIn("browser", route.supporting_tools)

    def test_scheduled_run_mode_detected(self):
        decision, contract = self._compile(
            {
                "request": "做一個每小時給 agent 跑的 VPS 任務 prompt，完成後要寫回狀態。",
            }
        )
        self.assertEqual(decision.execution_mode, "SCHEDULED_RUN")
        self.assertTrue(decision.should_compile)
        self.assertIn("write-back", contract.write_back.lower())

    def test_simple_fact_prefers_direct(self):
        decision, contract = self._compile(
            {
                "request": "Markdown 跟 JSON 差在哪？",
            }
        )
        self.assertEqual(decision.execution_mode, "DIRECT")
        self.assertFalse(decision.should_compile)
        self.assertTrue(contract.goal)

    def test_semantic_slots_stay_distinct(self):
        decision, contract = self._compile(
            {
                "request": "幫我整理成可執行任務。",
                "known_context": ["VERIFIED_CURRENT: endpoint returns 200"],
                "constraints": ["Do not change billing"],
            }
        )
        self.assertNotEqual(contract.evidence, contract.constraints)
        self.assertEqual(contract.truth_state, "VERIFIED_CURRENT")
        self.assertIn("Do not change billing", contract.constraints)


if __name__ == "__main__":
    unittest.main()
