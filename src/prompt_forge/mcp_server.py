"""STDIO MCP adapter for Prompt Forge.

This module exposes the existing local pipeline (`pipeline.run_pipeline`)
over the Model Context Protocol using the official `mcp` Python SDK's stdio
transport. It only does input validation and structured result shaping; it
does not reimplement the router, composer, evaluator, HTTP service, or the
EDGAR-OS caller.
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from .pipeline import run_pipeline
from .service import SERVICE_NAME, SERVICE_VERSION

mcp = FastMCP(SERVICE_NAME)


def _advertise_version(server: FastMCP, version: str) -> bool:
    """Best-effort: advertise SERVICE_VERSION in the MCP initialize response.

    The `mcp` SDK exposes no public setter for the server version, so this
    reaches into `_mcp_server`. Keep it non-fatal: a private-layout change in a
    future SDK release must not break importing (and therefore starting) the
    adapter -- an unset version only affects what clients display.
    """
    try:
        server._mcp_server.version = version
    except Exception:  # pragma: no cover - depends on future SDK internals
        return False
    return True


_VERSION_ADVERTISED = _advertise_version(mcp, SERVICE_VERSION)


@mcp.tool(
    description=(
        "Compile a free-text request into a full Prompt Forge pipeline artifact: "
        "input, intent, risk, route, context_policy, composition (with rendered "
        "prompt text), and evaluation."
    )
)
def prompt_forge_compile(
    request: str,
    case_id: str | None = None,
    preferred_agent: str | None = None,
    constraints: list[str] | None = None,
    known_context: list[str] | None = None,
) -> dict[str, Any]:
    payload = {
        "request": request,
        "case_id": case_id,
        "preferred_agent": preferred_agent,
        "constraints": constraints or [],
        "known_context": known_context or [],
    }
    result = run_pipeline(payload)
    return result.to_dict()


@mcp.tool(
    description="Report Prompt Forge MCP adapter health and pipeline metadata."
)
def prompt_forge_health() -> dict[str, Any]:
    return {
        "ok": True,
        "service": SERVICE_NAME,
        "version": SERVICE_VERSION,
        "pipeline": "local-deterministic",
        "protocol": "mcp-stdio",
    }


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
