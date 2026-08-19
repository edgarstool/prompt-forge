from __future__ import annotations

import json
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from prompt_forge.service import create_server


class PromptForgeServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = create_server("127.0.0.1", 0)
        cls.port = cls.server.server_port
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def _get_json(self, path: str) -> tuple[int, dict]:
        with urlopen(f"http://127.0.0.1:{self.port}{path}", timeout=3) as response:
            return response.status, json.loads(response.read().decode("utf-8"))

    def _post_json(self, path: str, payload: object) -> tuple[int, dict]:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = Request(
            f"http://127.0.0.1:{self.port}{path}",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=3) as response:
            return response.status, json.loads(response.read().decode("utf-8"))

    def test_health(self) -> None:
        status, payload = self._get_json("/health")
        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["service"], "prompt-forge")

    def test_compile_returns_pipeline_artifact_and_preserves_traditional_chinese(self) -> None:
        request_text = "幫我把這個資料夾整理好。"
        status, payload = self._post_json(
            "/v1/compile",
            {"request": request_text},
        )
        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"])
        result = payload["result"]
        self.assertEqual(result["input"]["request"], request_text)
        self.assertEqual(result["intent"]["task_type"], "local-files")
        self.assertEqual(result["route"]["recommended_agent"], "hermes-local")
        self.assertTrue(result["composition"]["rendered"])
        self.assertIn("passed", result["evaluation"])

    def test_missing_request_is_400(self) -> None:
        request = Request(
            f"http://127.0.0.1:{self.port}/v1/compile",
            data=b"{}",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with self.assertRaises(HTTPError) as ctx:
            urlopen(request, timeout=3)
        self.assertEqual(ctx.exception.code, 400)
        payload = json.loads(ctx.exception.read().decode("utf-8"))
        self.assertEqual(payload["error"], "invalid_request")

    def test_malformed_json_is_400(self) -> None:
        request = Request(
            f"http://127.0.0.1:{self.port}/v1/compile",
            data=b"{broken",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with self.assertRaises(HTTPError) as ctx:
            urlopen(request, timeout=3)
        self.assertEqual(ctx.exception.code, 400)
        payload = json.loads(ctx.exception.read().decode("utf-8"))
        self.assertEqual(payload["error"], "invalid_json")

    def test_unknown_endpoint_is_404(self) -> None:
        with self.assertRaises(HTTPError) as ctx:
            urlopen(f"http://127.0.0.1:{self.port}/nope", timeout=3)
        self.assertEqual(ctx.exception.code, 404)


if __name__ == "__main__":
    unittest.main()
