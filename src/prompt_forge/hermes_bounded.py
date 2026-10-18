"""Optional bounded Hermes canary with a zero-LLM codebase preflight.

Uses Hermes' existing gateway session.create / session.interrupt RPC verbs.
Not a global Hermes timeout patch, automatic deployment, or write approval.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from .codebase_router import resolve_codebase


async def route_before_agent(
    request: str, agent_canary: Callable[[], Awaitable[dict[str, Any]]]
) -> dict[str, Any]:
    """Never spend tokens if a provisional route cannot select one candidate."""
    route = resolve_codebase(request)
    if route["status"] != "CANDIDATE":
        return {"status": "STOPPED_PRE_MODEL", "route": route, "model_calls": 0}
    return await agent_canary()


async def run_bounded_view(
    view: Any, client: Any, prompt: str, *, timeout_seconds: float
) -> dict[str, Any]:
    """Bound exactly one newly created canary turn.

    The owner might not acknowledge an interrupt. An accepted RPC is therefore
    INTERRUPT_REQUESTED rather than COMPLETED/CANCELLED. Do not reuse a session
    or infer a session ID from a process list / log. A lost admission is UNKNOWN.
    """
    if not 0 < timeout_seconds <= 600:
        raise ValueError("timeout_seconds must be between 0 and 600")
    session = view.session_id
    try:
        code = await asyncio.wait_for(view.run(prompt, oneshot=True), timeout_seconds)
        return {"status": "COMPLETED", "session_id": session, "exit_code": code}
    except asyncio.TimeoutError:
        # A failed submit may have been admitted: do NOT invent a cancel target.
        if not getattr(view, "finite_admission", None):
            return {"status": "ADMISSION_UNKNOWN", "session_id": session}
        try:
            snapshot = await asyncio.wait_for(
                client.rpc("session.resume", session_id=session), 5
            )
            gen = snapshot.get("execution_generation")
            if type(gen) is not int or gen < 0:
                return {"status": "INTERRUPT_UNVERIFIED", "session_id": session}
            await asyncio.wait_for(
                client.rpc(
                    "session.interrupt",
                    session_id=session,
                    execution_generation=gen,
                ),
                5,
            )
            return {
                "status": "INTERRUPT_REQUESTED",
                "session_id": session,
                "execution_generation": gen,
                "verified_cancelled": False,
            }
        except (Exception, asyncio.CancelledError) as exc:
            return {
                "status": "INTERRUPT_UNVERIFIED",
                "session_id": session,
                "error_type": type(exc).__name__,
            }


async def _agent_canary(request: str, timeout_seconds: float) -> dict[str, Any]:
    # Load Hermes only if the user explicitly requested a live agent canary.
    # This module remains importable, usable and testable without Hermes.
    from hermes_cli.gateway_client import connect_gateway
    from hermes_cli.gateway_chat_view import GatewayChatView

    async with connect_gateway() as client:
        capabilities = await client.rpc("runtime.describe")
        sources = (capabilities.get("session_create") or {}).get("sources") or []
        if "oneshot" not in sources:
            return {"status": "UNSUPPORTED_GATEWAY", "model_calls": 0}
        snapshot = await client.rpc(
            "session.create",
            source="oneshot",
            request_id=uuid.uuid4().hex,
            toolsets=["prompt-forge"],
        )
        view = GatewayChatView(client, snapshot, quiet=True)
        view.unattended = True
        # Read-only canary; do not run the user's requested change.
        prompt = (
            "唯讀工具路由驗收。只呼叫一次 prompt_forge_codebase，"
            f"request={request}。根據工具回傳給出 status 和 primary_repo。"
            "不得修改程式碼、部署或進行其他工具搜尋。"
        )
        return await run_bounded_view(
            view, client, prompt, timeout_seconds=timeout_seconds
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="prompt-forge-bounded-hermes",
        description="Zero-token codebase guard, optional scoped live Hermes canary.",
    )
    parser.add_argument("--request", required=True)
    parser.add_argument("--agent-canary", action="store_true",
                        help="Explicitly spend model tokens for read-only Hermes MCP canary")
    parser.add_argument("--timeout", type=float, default=30)
    args = parser.parse_args(argv)
    if not 0 < args.timeout <= 600:
        parser.error("--timeout must be 0 < seconds <= 600")

    if not args.agent_canary:
        route = resolve_codebase(args.request)
        print(json.dumps(
            {"status": "STOPPED_PRE_MODEL", "route": route, "model_calls": 0},
            ensure_ascii=False,
        ))
        return 0 if route["status"] != "BLOCKED" else 3

    try:
        result = asyncio.run(
            route_before_agent(
                args.request,
                lambda: _agent_canary(args.request, args.timeout),
            )
        )
    except (ImportError, OSError, RuntimeError) as exc:
        print(json.dumps(
            {"status": "CANARY_UNVERIFIED", "error_type": type(exc).__name__},
            ensure_ascii=False,
        ))
        return 4
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["status"] in {"COMPLETED", "STOPPED_PRE_MODEL"} else 124


if __name__ == "__main__":
    sys.exit(main())
