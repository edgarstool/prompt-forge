"""AWS Lambda Function URL adapter for the Prompt Forge HTTP contract.

No extra runtime dependencies.  The zip uploaded to Lambda contains only
``prompt_forge`` (not the MCP extra).
"""

from __future__ import annotations

import base64
import json
from typing import Any

from .service import dispatch


def _event_method(event: dict[str, Any]) -> str:
    request_context = event.get("requestContext") or {}
    http = request_context.get("http") or {}
    return str(http.get("method") or event.get("httpMethod") or "GET")


def _event_path(event: dict[str, Any]) -> str:
    request_context = event.get("requestContext") or {}
    http = request_context.get("http") or {}
    return str(
        event.get("rawPath")
        or http.get("path")
        or event.get("path")
        or "/"
    )


def _event_body(event: dict[str, Any]) -> bytes | None:
    body = event.get("body")
    if body is None:
        return None
    if event.get("isBase64Encoded"):
        if isinstance(body, str):
            return base64.b64decode(body)
        return base64.b64decode(body)
    if isinstance(body, bytes):
        return body
    return str(body).encode("utf-8")


def lambda_handler(event: dict[str, Any], context: object | None = None) -> dict[str, Any]:
    """Handle a Lambda Function URL / HTTP API v2 event."""

    del context
    status, payload = dispatch(_event_method(event), _event_path(event), _event_body(event))
    return {
        "statusCode": status,
        "headers": {"content-type": "application/json; charset=utf-8"},
        "body": json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
    }
