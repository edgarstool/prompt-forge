"""Behavioral contract for EDGAR Codebase routing: positive, negative and ambiguous."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from prompt_forge.codebase_router import resolve_codebase  # noqa: E402
from prompt_forge.pipeline import run_pipeline  # noqa: E402


class CodebaseRouterTests(unittest.TestCase):
    def check(self, prompt, expected_status, primary=None):
        result = resolve_codebase(prompt)
        self.assertEqual(result["status"], expected_status, prompt)
        self.assertEqual(result["primary_repo"], primary, prompt)
        self.assertEqual(result["source"], "PROVISIONAL_INDEX_2026-10-18")
        self.assertIn("verify", result["next_action"].lower())
        return result

    def test_hermes_line_approval(self):
        self.check("修 Hermes 的 LINE approval 卡片", "CANDIDATE", "edgarstool/hermes-agent")

    def test_knowledge_search(self):
        self.check("修 Edgar Knowledge 搜尋索引", "CANDIDATE", "edgarstool/edgars-knowledge-runtime")

    def test_mcp_tools(self):
        self.check("修 edgars-mcp 384 個工具的路由", "CANDIDATE", "edgarstool/edgars-mcp")

    def test_neon_hermes_continuity(self):
        self.check("修 Neon → Hermes materializer 對話同步", "CANDIDATE", "edgarstool/edgar-os-continuity")

    def test_exact_repo_precedes_fuzzy(self):
        self.check("修改 edgarstool/edgar-mail 的 webhook", "CANDIDATE", "edgarstool/edgar-mail")

    def test_unqualified_line_is_ambiguous(self):
        r = self.check("修 LINE bot", "AMBIGUOUS")
        self.assertGreaterEqual(len(r["candidates"]), 2)

    def test_control_center_ambiguous(self):
        r = self.check("改 EDGAR 控制中心", "AMBIGUOUS")
        self.assertEqual(len(r["candidates"]), 2)

    def test_mail_ambiguous(self):
        self.check("修 EDGAR 郵件", "AMBIGUOUS")

    def test_explicit_webmail(self):
        self.check("修 Webmail 的郵件 UI", "CANDIDATE", "edgarstool/edgar-webmail")

    def test_generic_login_avoids_guess(self):
        self.check("修登入 callback", "UNKNOWN")

    def test_edgar_auth(self):
        self.check("修 EDGAR Auth 登入 callback", "CANDIDATE", "edgarstool/edgarstool-universal-auth-ui")

    def test_generic_github_question(self):
        self.check("GitHub 的 codebase 是什麼？", "UNKNOWN")

    def test_local_model_install_denied(self):
        self.check("幫我安裝 ollama 本地模型", "BLOCKED")

    def test_local_model_cleanup_needs_verification(self):
        self.check("清理 ollama repo 的所有下載項目", "REVIEW_REQUIRED")

    def test_unrelated(self):
        self.check("請幫我寫一首詩", "UNKNOWN")

    def test_pipeline_exposes_candidate_in_route(self):
        result = run_pipeline({"request": "修 Hermes 的 LINE approval 卡片"})
        data = result.to_dict()
        self.assertEqual(data["route"]["codebase"]["primary_repo"], "edgarstool/hermes-agent")
        self.assertIn("verify", " ".join(data["route"]["assumptions"]).lower())
        self.assertIn("edgarstool/hermes-agent", data["composition"]["rendered"])

    def test_pipeline_ambiguous_does_not_claim_repo(self):
        result = run_pipeline({"request": "改 EDGAR 控制中心"})
        self.assertEqual(result.route.codebase["status"], "AMBIGUOUS")
        self.assertIsNone(result.route.codebase["primary_repo"])


if __name__ == "__main__":
    unittest.main()
