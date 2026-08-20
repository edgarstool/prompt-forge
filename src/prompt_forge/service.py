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
SERVICE_VERSION = "0.2.0-dev"


def _json_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


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
        if self.path == "/health":
            self._send_json(
                200,
                {
                    "ok": True,
                    "service": SERVICE_NAME,
                    "version": SERVICE_VERSION,
                    "pipeline": "local-deterministic",
                },
            )
            return

        self._send_json(404, {"ok": False, "error": "not_found"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/v1/compile":
            self._send_json(404, {"ok": False, "error": "not_found"})
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._send_json(400, {"ok": False, "error": "invalid_content_length"})
            return

        if content_length <= 0:
            self._send_json(400, {"ok": False, "error": "empty_body"})
            return

        try:
            raw = self.rfile.read(content_length)
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._send_json(400, {"ok": False, "error": "invalid_json"})
            return

        if not isinstance(payload, dict):
            self._send_json(400, {"ok": False, "error": "payload_must_be_object"})
            return

        try:
            result = run_pipeline(payload)
        except (TypeError, ValueError) as exc:
            self._send_json(
                400,
                {
                    "ok": False,
                    "error": "invalid_request",
                    "detail": str(exc),
                },
            )
            return

        self._send_json(200, {"ok": True, "result": result.to_dict()})


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
