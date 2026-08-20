# Prompt Forge MCP Adapter (STDIO)

這一層讓其他 MCP client（例如 Claude Desktop、Claude Code、MCP Inspector）可以直接呼叫既有的
Prompt Forge local pipeline，而不需要先啟動 HTTP service。

它只做 **input validation → 呼叫既有 pipeline (`pipeline.run_pipeline`) → 回傳 structured result**，
不重寫 Router、Composer、Evaluator、HTTP service 或 EDGAR-OS caller。

Transport 是 **STDIO**（standard input/output），不是網路 endpoint；沒有對外 HTTP/SSE，也沒有
production 部署或 authentication。

## Tools

| Tool | 說明 |
| --- | --- |
| `prompt_forge_compile` | 輸入 `request`（必填）與可選的 `case_id` / `preferred_agent` / `constraints` / `known_context`，輸出完整 pipeline artifact：`input` / `intent` / `risk` / `route` / `context_policy` / `composition`（含 `composition.rendered`）/ `evaluation`。 |
| `prompt_forge_health` | 輸出 `{ ok, service, version, pipeline, protocol }`，用來確認 adapter 與 pipeline 是否正常。 |

輸入驗證沿用既有 `UserRequest.from_dict()`；不合法輸入（例如空字串 `request`）會回傳
`isError: true` 的 MCP tool 錯誤，錯誤訊息帶原因，而不是網路層的 protocol error。

## 安裝與啟動

```powershell
cd V:\projects\prompt-forge
pip install -e .
```

安裝後會註冊主控台指令 `prompt-forge-mcp`（也可以直接用
`python -m prompt_forge.mcp_server` 啟動，不需要 `pip install -e .`）。

啟動後它會等待 stdin 上的 MCP JSON-RPC 訊息；直接執行不會有互動輸出，這是正常行為，
因為 stdout 保留給 MCP 協定訊息，所有 log 都導向 stderr。

## 在 Windows 上找到 `prompt-forge-mcp` 的實際路徑

`pip install -e .` 會把主控台指令裝進目前 Python 環境的 `Scripts` 目錄。不要假設固定路徑，
用下列任一方式現場查詢：

```powershell
# 方法一：直接問 PATH
where.exe prompt-forge-mcp

# 方法二：問 Python 自己的 Scripts 目錄
python -c "import sysconfig; print(sysconfig.get_path('scripts'))"
```

在其中一台開發機上，這會回報例如：

```text
C:\Users\<你的帳號>\AppData\Local\Programs\Python\Python313\Scripts\prompt-forge-mcp.exe
```

實際路徑依 Python 安裝方式（系統安裝、`venv`、`conda` 等）而不同，請以上面兩個指令的即時輸出為準，
不要照抄別人機器上的路徑。

## Generic STDIO MCP client 設定

大多數支援 STDIO transport 的 MCP client 設定格式類似：

```json
{
  "mcpServers": {
    "prompt-forge": {
      "command": "prompt-forge-mcp",
      "args": [],
      "env": {}
    }
  }
}
```

如果 client 找不到 `prompt-forge-mcp`（例如它不在該 client 進程可見的 PATH 上），改用完整路徑
（用上面「查找實際路徑」的方法取得）或改叫 Python 模組：

```json
{
  "mcpServers": {
    "prompt-forge": {
      "command": "python",
      "args": ["-m", "prompt_forge.mcp_server"],
      "cwd": "V:\\projects\\prompt-forge",
      "env": {
        "PYTHONPATH": "V:\\projects\\prompt-forge\\src"
      }
    }
  }
}
```

`cwd` 與 `PYTHONPATH` 只有在**沒有** `pip install -e .` 的情況下才需要；已安裝的環境可以省略。

## 手動驗證（不依賴任何特定 IDE）

用官方 `mcp` Python SDK 的 client，透過真正的 STDIO transport 驗證 `initialize` →
`tools/list` → 呼叫兩個 tool：

```powershell
cd V:\projects\prompt-forge
$env:PYTHONPATH = "$PWD\src"
$script = @"
import asyncio, sys
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

async def main():
    params = StdioServerParameters(command=sys.executable, args=['-m', 'prompt_forge.mcp_server'])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            print(await session.initialize())
            print(await session.list_tools())
            print(await session.call_tool('prompt_forge_health', {}))
            print(await session.call_tool('prompt_forge_compile', {'request': '幫我把這個資料夾整理好。'}))

asyncio.run(main())
"@
python -c $script
```

或直接跑自動化測試（同樣透過真實 STDIO subprocess，見
`tests/test_mcp_server.py::McpServerStdioProcessTests`）：

```powershell
python -m unittest tests.test_mcp_server -v
```

## Non-goals（本文件不涵蓋）

- External MCP endpoint（HTTP / SSE / Streamable HTTP 對外服務）
- Production deployment、hostname、TLS
- Authentication / authorization
- Cloudflare Tunnel 或任何對外路由

這些都尚未建立；目前只有本機 STDIO adapter。
