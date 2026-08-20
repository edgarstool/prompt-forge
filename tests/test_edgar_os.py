from __future__ import annotations

import threading
import unittest

from prompt_forge.edgar_os import EDGAROSPromptForgeClient, PIPELINE_STAGES
from prompt_forge.service import create_server


class EDGAROSPromptForgeClientTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = create_server("127.0.0.1", 0)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.client = EDGAROSPromptForgeClient(
            f"http://127.0.0.1:{cls.server.server_port}"
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def test_compile_returns_complete_pipeline_artifact(self) -> None:
        artifact = self.client.compile(
            "幫我修好這個 repo，測試完開 PR。",
            known_context=["repository identity 已確認"],
            constraints=["recurring cost = $0"],
            case_id="edgar-os-caller-smoke",
        )

        self.assertTrue(set(PIPELINE_STAGES).issubset(artifact))
        self.assertEqual(artifact["input"]["case_id"], "edgar-os-caller-smoke")
        self.assertEqual(artifact["intent"]["task_type"], "coding")
        self.assertTrue(artifact["composition"]["rendered"])
        self.assertTrue(artifact["evaluation"]["passed"])


if __name__ == "__main__":
    unittest.main()
