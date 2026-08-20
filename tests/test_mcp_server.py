from __future__ import annotations

import sys
import unittest
from pathlib import Path

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.shared.memory import create_connected_server_and_client_session

from prompt_forge.mcp_server import mcp as prompt_forge_mcp
from prompt_forge.schema import REQUIRED_PROMPT_SECTIONS

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

PIPELINE_STAGES = (
    "input",
    "intent",
    "risk",
    "route",
    "context_policy",
    "composition",
    "evaluation",
)


class McpServerInProcessTests(unittest.IsolatedAsyncioTestCase):
    """Exercises the real MCP protocol (initialize/list_tools/call_tool)
    against the FastMCP app in-process via the SDK's memory transport."""

    async def test_server_initializes(self) -> None:
        async with create_connected_server_and_client_session(prompt_forge_mcp) as session:
            # create_connected_server_and_client_session() only yields the
            # session after ClientSession.initialize() has completed.
            self.assertIsNotNone(session)

    async def test_tools_list_contains_expected_tools(self) -> None:
        async with create_connected_server_and_client_session(prompt_forge_mcp) as session:
            tools = await session.list_tools()
            names = {tool.name for tool in tools.tools}
            self.assertIn("prompt_forge_compile", names)
            self.assertIn("prompt_forge_health", names)

    async def test_health_tool_success(self) -> None:
        async with create_connected_server_and_client_session(prompt_forge_mcp) as session:
            result = await session.call_tool("prompt_forge_health", {})
            self.assertFalse(result.isError)
            self.assertTrue(result.structuredContent["ok"])
            self.assertEqual(result.structuredContent["service"], "prompt-forge")

    async def test_compile_tool_success_returns_full_artifact(self) -> None:
        async with create_connected_server_and_client_session(prompt_forge_mcp) as session:
            result = await session.call_tool(
                "prompt_forge_compile",
                {"request": "幫我把這個資料夾整理好。"},
            )
            self.assertFalse(result.isError)
            artifact = result.structuredContent
            for stage in PIPELINE_STAGES:
                self.assertIn(stage, artifact)
            self.assertTrue(artifact["composition"]["rendered"])
            for section in REQUIRED_PROMPT_SECTIONS:
                self.assertIn(section, artifact["composition"]["sections"])
            self.assertIn("passed", artifact["evaluation"])
            self.assertIsInstance(artifact["evaluation"]["passed"], bool)

    async def test_compile_tool_preserves_traditional_chinese(self) -> None:
        request_text = (
            "幫我找 2026 年目前適合 AI Agent 使用的免費 VM 與 cloud credits，"
            "優先查官方來源。"
        )
        async with create_connected_server_and_client_session(prompt_forge_mcp) as session:
            result = await session.call_tool(
                "prompt_forge_compile", {"request": request_text}
            )
            self.assertFalse(result.isError)
            self.assertEqual(result.structuredContent["input"]["request"], request_text)
            self.assertIn(request_text, result.structuredContent["composition"]["rendered"])

    async def test_compile_tool_supports_optional_fields(self) -> None:
        async with create_connected_server_and_client_session(prompt_forge_mcp) as session:
            result = await session.call_tool(
                "prompt_forge_compile",
                {
                    "request": "幫我修好這個 repo，測試完開 PR。",
                    "case_id": "mcp-adapter-smoke",
                    "known_context": ["repository identity 已確認"],
                    "constraints": ["recurring cost = $0"],
                },
            )
            self.assertFalse(result.isError)
            artifact = result.structuredContent
            self.assertEqual(artifact["input"]["case_id"], "mcp-adapter-smoke")
            self.assertEqual(artifact["route"]["task_type"], "coding")

    async def test_compile_tool_invalid_input_returns_explicit_mcp_error(self) -> None:
        async with create_connected_server_and_client_session(prompt_forge_mcp) as session:
            result = await session.call_tool("prompt_forge_compile", {"request": ""})
            self.assertTrue(result.isError)
            self.assertTrue(result.content)
            text = result.content[0].text
            self.assertTrue(text)


class McpServerStdioProcessTests(unittest.IsolatedAsyncioTestCase):
    """Spawns the real `prompt-forge-mcp` STDIO entry point in a subprocess
    and drives it with the official MCP client. If any debug/log output were
    written to stdout instead of stderr, the JSON-RPC line framing used by
    the client's stdout reader would break and this end-to-end handshake
    would fail (or the response payloads below would not decode cleanly)."""

    async def test_stdio_entry_point_end_to_end(self) -> None:
        server_params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "prompt_forge.mcp_server"],
            cwd=str(ROOT),
            env={"PYTHONPATH": str(SRC)},
        )
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                init_result = await session.initialize()
                self.assertEqual(init_result.serverInfo.name, "prompt-forge")

                tools = await session.list_tools()
                names = {tool.name for tool in tools.tools}
                self.assertIn("prompt_forge_compile", names)
                self.assertIn("prompt_forge_health", names)

                health = await session.call_tool("prompt_forge_health", {})
                self.assertFalse(health.isError)
                self.assertTrue(health.structuredContent["ok"])

                compiled = await session.call_tool(
                    "prompt_forge_compile",
                    {"request": "幫我把這個資料夾整理好。"},
                )
                self.assertFalse(compiled.isError)
                self.assertTrue(compiled.structuredContent["composition"]["rendered"])


if __name__ == "__main__":
    unittest.main()
