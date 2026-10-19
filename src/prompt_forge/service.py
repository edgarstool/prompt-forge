"""Minimal HTTP service wrapper for Prompt Forge.

This is intentionally stdlib-only.  The goal is to validate the external API
contract before choosing a production web framework.
"""

from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from .pipeline import run_pipeline

SERVICE_NAME = "prompt-forge"
SERVICE_VERSION = "0.2.0.dev0"
COMPILE_PATHS = frozenset({"/compile", "/v1/compile"})


def _json_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def normalize_path(path: str) -> str:
    """Strip query string and trailing slash (except root)."""

    cleaned = (path or "/").split("?", 1)[0]
    if len(cleaned) > 1:
        cleaned = cleaned.rstrip("/")
    return cleaned or "/"


def health_payload() -> dict[str, Any]:
    return {
        "ok": True,
        "service": SERVICE_NAME,
        "version": SERVICE_VERSION,
        "pipeline": "local-deterministic",
    }


def _compile_from_body(body: bytes | str | None) -> tuple[int, dict[str, Any]]:
    if body is None:
        return 400, {"ok": False, "error": "empty_body"}

    if isinstance(body, str):
        raw = body.encode("utf-8")
    else:
        raw = body

    if not raw:
        return 400, {"ok": False, "error": "empty_body"}

    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return 400, {"ok": False, "error": "invalid_json"}

    if not isinstance(payload, dict):
        return 400, {"ok": False, "error": "payload_must_be_object"}

    try:
        result = run_pipeline(payload)
    except (TypeError, ValueError) as exc:
        return 400, {"ok": False, "error": "invalid_request", "detail": str(exc)}

    return 200, {"ok": True, "result": result.to_dict()}


def dispatch(
    method: str,
    path: str,
    body: bytes | str | None = None,
) -> tuple[int, dict[str, Any]]:
    """Shared HTTP contract used by the local server and the Lambda adapter."""

    verb = (method or "GET").upper()
    route = normalize_path(path)

    if verb == "GET" and route == "/health":
        return 200, health_payload()

    if verb == "POST" and route in COMPILE_PATHS:
        return _compile_from_body(body)

    return 404, {"ok": False, "error": "not_found"}


class PromptForgeHandler(BaseHTTPRequestHandler):
    server_version = "PromptForgeHTTP/0.2"

    def log_message(self, format: str, *args: object) -> None:  # noqa: A003
        # Keep the service quiet by default; a real deployment can attach
        # structured logging later.
        return

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = _json_bytes(payload)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        status, payload = dispatch("GET", self.path)
        self._send_json(status, payload)

    def do_POST(self) -> None:  # noqa: N802
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._send_json(400, {"ok": False, "error": "invalid_content_length"})
            return

        if content_length <= 0:
            self._send_json(400, {"ok": False, "error": "empty_body"})
            return

        raw = self.rfile.read(content_length)
        status, payload = dispatch("POST", self.path, raw)
        self._send_json(status, payload)


def create_server(host: str = "127.0.0.1", port: int = 8787) -> ThreadingHTTPServer:
    """Create, but do not start, the HTTP server."""

    return ThreadingHTTPServer((host, port), PromptForgeHandler)


def serve(host: str = "127.0.0.1", port: int = 8787) -> None:
    """Run the service until interrupted."""

    server = create_server(host, port)
    print(f"Prompt Forge API listening on http://{host}:{server.server_port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the Prompt Forge HTTP API")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    args = parser.parse_args(argv)
    serve(args.host, args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
