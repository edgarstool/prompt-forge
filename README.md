# Prompt Forge

> Turn vague ideas into executable prompts.
>
> 把模糊的想法，鍛造成可以交給 AI 執行的任務。

Prompt Forge 是一個面向多種 AI Agent 的 Prompt 生產系統。它不是 Prompt 收藏夾，而是一條可測試、可改良、可交付的任務鍛造流程。

## PromptOS 與 Prompt Forge

**PromptOS** 是 EDGAR-OS 的一級 Prompt governance / task-contract architecture（提示治理／任務契約架構）。它負責把 human intent 解析成有 authority、evidence、scope、constraints、assumptions、validation、stop conditions 與 evidence return 的可執行任務契約。

**Prompt Forge** 是 PromptOS 的 executable compiler / factory：把 request + context + policy 編譯成 bounded executable prompt / handoff，並用固定 evaluator 檢查品質。

因此：

- PromptOS ≠ Prompt 收藏庫。
- PromptOS ≠ Prompt Forge。
- Prompt Forge 是 PromptOS 的可執行子系統。
- 更大的 Agent Platform 才負責 team selection、tool attachment、workflow execution、long-running orchestration 與 state write-back。

詳見 [`docs/PROMPTOS-ARCHITECTURE.md`](docs/PROMPTOS-ARCHITECTURE.md)。

## 產品目標

使用者只需要描述目標，Prompt Forge 應該能：

1. 判斷任務類型與真正意圖。
2. 分離 known facts / evidence、authority、constraints 與 assumptions。
3. 選擇適合的 Agent、工具與資料來源。
4. 補上合理且可逆的假設，而不是不斷反問。
5. 產出可以直接複製執行的完整 Prompt / task contract。
6. 內建驗收、停止條件、證據回傳與必要的回復方式。
7. 在涉及 library、SDK、API、CLI 或 framework 時，透過 Context7 或等效 primary / official source 取得版本相符的最新文件。

## 產品原則

- **先給可用版本，再一起修。**
- **只有真正阻塞或高風險時才提問。**
- **Prompt 是施工單，不是理論課。**
- **把 unknown / assumption 明示，不把猜測寫成事實。**
- **能由確定性工具完成的事，不交給模型猜。**
- **安全措施要與風險成比例，不用棉被包住螺絲起子。**
- **每次交付都應可驗收、可比較、可停止，並知道要回傳什麼 evidence。**

## v0.1 範圍

第一版核心包含：

- Prompt Router：判斷任務類型與建議執行者。
- Prompt Composer：把需求組成完整可執行 Prompt / task contract。
- Context Policy：需要時加入版本／新鮮度查核。
- Prompt Evaluation：用固定測試判斷輸出是否完整、簡潔、可執行。
- 四個最小案例。
- CLI / unittest test runner。

暫時不做：

- 完整聊天產品
- 多租戶與帳號系統
- 自動執行 production 變更
- Prompt 市集
- 複雜前端介面
- 完整 Agent Platform / long-running orchestrator

## 預計結構

```text
prompt-forge/
├─ docs/          # 產品設計、PromptOS 邊界、決策與交付流程
├─ prompts/       # 可組合的 Prompt 模板
├─ routers/       # 任務分類與工具路由規則
├─ skills/        # 特定 Agent / 領域能力包
├─ evaluators/    # Prompt 品質檢查規則
├─ examples/      # 真實輸入與預期輸出
├─ tests/         # 驗收案例
└─ adapters/      # Context7、GitHub 等外部來源接口
```

## 目前狀態

**Local pipeline 可跑（EDG-342），並已加上 STDIO MCP adapter。**

已有確定性本地閉環：intent → risk → route → context policy → compose → evaluate。
四個最小案例與 CLI / unittest 可在本機反覆驗證。另有綁定
`127.0.0.1` 的 HTTP prototype、最小 EDGAR-OS caller，以及可被 MCP client
（Claude Desktop、Claude Code、MCP Inspector 等）呼叫的 STDIO MCP adapter。

明確能力狀態，避免誤讀成「已經上線」：

| 能力 | 狀態 |
| --- | --- |
| Local pipeline（`run_pipeline`） | ✅ 可用 |
| HTTP service（`127.0.0.1:8787`，prototype） | ✅ 可用（僅本機） |
| EDGAR-OS HTTP caller（`prompt_forge.edgar_os`） | ✅ 可用 |
| STDIO MCP adapter（`prompt-forge-mcp`） | ✅ 可用（僅本機 STDIO，見 `docs/MCP.md`） |
| External MCP endpoint（對外 HTTP/SSE/Streamable HTTP MCP） | ❌ 未建立 |
| Production deployment | ❌ 未建立 |
| Authentication | ❌ 未建立 |
| Cloudflare hostname | ❌ 未建立 |

這代表 local executable loop、本機 HTTP 接線與本機 MCP 接線都已存在；對外服務、
production deployment、hostname、authentication 與完整 Agent Platform integration
仍未建立。

詳細 I/O 與指令：`docs/LOCAL-PIPELINE.md`、`docs/HTTP-API.md`、`docs/MCP.md`。

## 本地快速開始（Windows PowerShell）

```powershell
cd V:\projects\prompt-forge
$env:PYTHONPATH = "$PWD\src"

# 各階段輸入輸出契約
python -m prompt_forge io

# 跑四個最小案例
python -m prompt_forge eval

# 單次組裝 + 顯示 Prompt
python -m prompt_forge run --request "幫我把這個資料夾整理好。" --show-prompt

# 單元測試
python -m unittest discover -s tests -v

# 另一個 PowerShell 視窗啟動本機 service 後，由 EDGAR-OS caller 呼叫
python -m prompt_forge.edgar_os "幫我修好這個 repo，測試完開 PR。"

# 啟動 STDIO MCP adapter（供 MCP client 連接，見 docs/MCP.md）
pip install -e .
prompt-forge-mcp
# 或不安裝，直接：
python -m prompt_forge.mcp_server

# 或用 helper
.\scripts\run-local.ps1 eval
.\scripts\run-local.ps1 test
```

### 目錄對應

```text
prompt-forge/
├─ docs/                 # 產品設計 + PromptOS boundary + LOCAL-PIPELINE + MCP
├─ src/prompt_forge/     # 可執行 pipeline（stdlib）+ HTTP + MCP adapter
├─ prompts/              # 模板說明
├─ routers/              # 路由規則說明
├─ evaluators/           # 評估檢查說明
├─ examples/cases/       # 最小案例 A–D
├─ tests/                # unittest
├─ adapters/             # 外部來源接口說明
└─ scripts/run-local.ps1
```

## 專案角色

- **產品擁有者：** 王世鈞（Edgar）／德德
- **協作方式：** AI 提議與施工，Edgar 保留方向決定權；任何設計都可以根據實際使用推翻重做。

## License

尚未定案。正式發布前再選擇合適授權方式。
