from __future__ import annotations

import base64
import json
import unittest

from prompt_forge.lambda_handler import lambda_handler
from prompt_forge.service import dispatch


def _function_url_event(
    method: str,
    path: str,
    body: str | None = None,
    *,
    base64_encoded: bool = False,
) -> dict:
    event = {
        "version": "2.0",
        "rawPath": path,
        "requestContext": {"http": {"method": method, "path": path}},
        "isBase64Encoded": base64_encoded,
    }
    if body is not None:
        event["body"] = body
    return event


class DispatchContractTests(unittest.TestCase):
    def test_health(self) -> None:
        status, payload = dispatch("GET", "/health")
        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["service"], "prompt-forge")

    def test_health_ignores_query_string(self) -> None:
        status, payload = dispatch("GET", "/health?probe=1")
        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"])

    def test_unknown_is_404(self) -> None:
        status, payload = dispatch("GET", "/nope")
        self.assertEqual(status, 404)
        self.assertEqual(payload["error"], "not_found")


class LambdaHandlerTests(unittest.TestCase):
    def test_health_function_url_event(self) -> None:
        response = lambda_handler(_function_url_event("GET", "/health"))
        self.assertEqual(response["statusCode"], 200)
        payload = json.loads(response["body"])
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["service"], "prompt-forge")
        self.assertEqual(payload["pipeline"], "local-deterministic")

    def test_compile_function_url_event(self) -> None:
        request_text = "幫我把這個資料夾整理好。"
        response = lambda_handler(
            _function_url_event(
                "POST",
                "/compile",
                json.dumps({"request": request_text}, ensure_ascii=False),
            )
        )
        self.assertEqual(response["statusCode"], 200)
        payload = json.loads(response["body"])
        self.assertTrue(payload["ok"])
        result = payload["result"]
        self.assertEqual(result["input"]["request"], request_text)
        self.assertEqual(result["intent"]["task_type"], "local-files")
        self.assertIn("passed", result["evaluation"])

    def test_v1_compile_alias_still_works(self) -> None:
        response = lambda_handler(
            _function_url_event(
                "POST",
                "/v1/compile",
                json.dumps({"request": "幫我把這個資料夾整理好。"}, ensure_ascii=False),
            )
        )
        self.assertEqual(response["statusCode"], 200)
        payload = json.loads(response["body"])
        self.assertTrue(payload["ok"])

    def test_malformed_json_is_400(self) -> None:
        response = lambda_handler(_function_url_event("POST", "/compile", "{broken"))
        self.assertEqual(response["statusCode"], 400)
        payload = json.loads(response["body"])
        self.assertEqual(payload["error"], "invalid_json")

    def test_base64_body(self) -> None:
        raw = json.dumps({"request": "幫我把這個資料夾整理好。"}, ensure_ascii=False).encode("utf-8")
        response = lambda_handler(
            _function_url_event(
                "POST",
                "/compile",
                base64.b64encode(raw).decode("ascii"),
                base64_encoded=True,
            )
        )
        self.assertEqual(response["statusCode"], 200)
        payload = json.loads(response["body"])
        self.assertTrue(payload["ok"])


if __name__ == "__main__":
    unittest.main()
