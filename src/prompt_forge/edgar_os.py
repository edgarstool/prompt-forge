"""Minimal EDGAR-OS HTTP caller for the Prompt Forge compile endpoint."""

from __future__ import annotations

import argparse
import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


PIPELINE_STAGES = (
    "input",
    "intent",
    "risk",
    "route",
    "context_policy",
    "composition",
    "evaluation",
)


class PromptForgeConnectionError(RuntimeError):
    """Raised when Prompt Forge cannot be reached or returns an invalid artifact."""


class EDGAROSPromptForgeClient:
    """Small adapter from EDGAR-OS to the Prompt Forge HTTP prototype."""

    def __init__(self, base_url: str = "http://127.0.0.1:8787", timeout: float = 5.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def compile(self, request_text: str, **options: Any) -> dict[str, Any]:
        payload = {"request": request_text, **options}
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = Request(
            f"{self.base_url}/v1/compile",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urlopen(request, timeout=self.timeout) as response:
                response_payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise PromptForgeConnectionError(
                f"Prompt Forge returned HTTP {exc.code}: {detail}"
            ) from exc
        except (URLError, TimeoutError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise PromptForgeConnectionError(f"Prompt Forge request failed: {exc}") from exc

        if not isinstance(response_payload, dict) or response_payload.get("ok") is not True:
            raise PromptForgeConnectionError("Prompt Forge returned an unsuccessful response")

        artifact = response_payload.get("result")
        if not isinstance(artifact, dict):
            raise PromptForgeConnectionError("Prompt Forge response is missing the pipeline artifact")

        missing = [stage for stage in PIPELINE_STAGES if stage not in artifact]
        if missing:
            raise PromptForgeConnectionError(
                f"Prompt Forge pipeline artifact is incomplete: missing {', '.join(missing)}"
            )
        return artifact


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Call Prompt Forge from EDGAR-OS")
    parser.add_argument("request", help="Human request to compile")
    parser.add_argument("--base-url", default="http://127.0.0.1:8787")
    parser.add_argument("--timeout", type=float, default=5.0)
    args = parser.parse_args(argv)

    client = EDGAROSPromptForgeClient(args.base_url, args.timeout)
    artifact = client.compile(args.request)
    print(json.dumps(artifact, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
