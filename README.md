# Prompt Forge

> Turn vague ideas into executable task contracts.
>
> 把模糊的想法，鍛造成可以交給 AI / Agent / Tool 執行、驗收與回傳證據的任務契約。

Prompt Forge 是 EDGAR PromptOS 的 executable compiler / router。它不是 Prompt 收藏夾，也不是另一份世界狀態資料庫；它負責把 request + relevant context + policy 編譯成最小但足夠的 bounded executable prompt / handoff，並用固定 evaluator 檢查品質。

## PromptOS、Prompt Forge、Skills、State

- **EDGAR-OS** owns continuity, context, policy, state and evidence.
- **PromptOS** defines prompt governance / task-contract semantics.
- **Prompt Forge** compiles intent and routes the task into an executable contract.
- **Skills** provide reusable methods; they are loaded only when relevant.
- **SSoT / repo / provider / live runtime** provide authoritative mutable state.
- **Agents / tools** execute and return evidence.

因此：

- PromptOS ≠ Prompt 收藏庫。
- PromptOS ≠ Prompt Forge。
- Prompt Forge = **compiler + router**，不是巨型 method library。
- Prompt Forge 不擁有 Current State；它只攜帶本次任務需要的 state/evidence projection。
- Agent 不擁有 EDGAR-OS continuity；Agent 借用本次任務需要的 context。
- 更大的 Agent Platform 才負責 team selection、tool attachment、long-running orchestration、evidence collection 與 durable state write-back execution。

詳見 [`docs/PROMPTOS-ARCHITECTURE.md`](docs/PROMPTOS-ARCHITECTURE.md)。

## v0.2 Compiler / Router semantics

2026-09-01 起，Prompt Forge 的 deterministic pipeline 在既有 intent / risk / route / context policy 上增加 semantic compiler：

```text
human request
→ intent
→ risk / permission
→ executor / tool route
→ context freshness policy
→ semantic compile + execution-mode decision
→ task-contract composition
→ evaluation
```

Compiler 先判斷「這次是否真的需要產生 handoff prompt」，避免為了 Prompt 而製造 Prompt。

支援的 execution modes：

- `DIRECT`
- `EXECUTION_HANDOFF`
- `RESEARCH`
- `BUILD`
- `DEBUG`
- `BROWSER_OPERATOR`
- `MAINTENANCE`
- `SCHEDULED_RUN`
- `STRATEGIC`

核心 semantic slots 保持分離：

- Goal
- Authority
- Evidence
- Constraint
- Policy
- Preference
- Method
- Unknown

Mutable state 可標記：

- `VERIFIED_CURRENT`
- `DATED_OBSERVATION`
- `HISTORICAL`
- `INFERRED`
- `UNKNOWN`
- `CONFLICTED`

這些分類的目的不是增加格式，而是避免把記憶、推測、偏好與可驗證事實混成同一層。

## Task Contract

輸出的 contract 依任務複雜度縮放。核心概念是 **strong perimeter, flexible interior**：明確定義 outcome / scope / acceptance / evidence，但讓 executor 在邊界內自行選擇合理實作方法。

常用欄位：

- Goal / Outcome
- Known Facts / Evidence
- Authority & Context
- Scope
- Constraints / Permissions
- Assumptions / Unknowns
- Selected Executor / Tools
- Execution Freedom / Method
- Context Freshness Requirements
- Execution Task
- Validation / Acceptance Criteria
- Deliverables
- Stop Conditions
- Evidence to Return
- State Transition / Write-back Target

Prompt Forge 不要求每份輸出都塞滿所有欄位。**Complexity belongs in the compiler; only necessary complexity belongs in the compiled task.**

## 產品原則

- **Mainline first.** 先讓真正想要的 outcome 變成可驗證狀態。
- **Wide judgment, narrow execution.** 判斷可以寬，交付給 executor 的工作要收斂。
- **Plausibility is not correctness.** 看起來合理不算完成。
- **Configured ≠ deployed ≠ usable ≠ persistent.** 驗證真正 consumption boundary。
- **Evidence over claims.** plan、command、config edit、agent statement 都不是 completion proof。
- **Unknown stays unknown.** 不把記憶、重述或 inference 偷升格成 current truth。
- **Prefer direct execution when possible.** 能直接安全完成，就不要多製造一層 prompt/handoff。
- **Prefer existing capability and reversible execution.** 不為了架構漂亮新增不必要系統。
- **Ask the human only at real human-only boundaries.** 偏好、secret、付款、身份／authority、不可逆破壞或真正缺失的阻塞事實。
- **Skills are reusable methods.** 重複 workflow lesson 應升成 Skill，而不是膨脹 mother prompt。
- **No parallel SSoT.** Prompt Forge 編譯 state，不取代 state authority。

## 目前能力狀態

| 能力 | 狀態 |
| --- | --- |
| Local deterministic pipeline (`run_pipeline`) | ✅ 可用 |
| Semantic compiler / execution-mode router | ✅ 可用（v0.2 dev） |
| Task-contract composer + evaluator | ✅ 可用 |
| HTTP service (`127.0.0.1:8787`) | ✅ prototype，本機 |
| EDGAR-OS HTTP caller (`prompt_forge.edgar_os`) | ✅ 可用 |
| STDIO MCP adapter (`prompt-forge-mcp`) | ✅ 可用，本機 STDIO |
| GitHub Actions regression suite | ✅ PR / master CI |
| External MCP endpoint (public HTTP/SSE/Streamable HTTP) | ❌ 未建立 |
| Production deployment | ❌ 未建立 |
| Public authentication / hostname | ❌ 未建立 |
| Full long-running Agent Platform | ❌ 不屬於目前 Prompt Forge runtime |

這代表 compiler/router、local HTTP 與 STDIO MCP 接線已有 executable implementation；**不代表 Prompt Forge 已是 public production service**。

## 驗證

PR / `master` 會跑完整 unittest suite。v0.2 compiler/router regression cases 包含：

- Codex coding handoff → `BUILD`
- authenticated dashboard task → `BROWSER_OPERATOR`
- recurring agent task → `SCHEDULED_RUN`
- simple factual question → `DIRECT` / no handoff
- semantic-slot separation + truth-state preservation
- 舊 pipeline cases、HTTP service、EDGAR-OS caller、MCP STDIO regression

## 本地快速開始（Windows PowerShell）

```powershell
cd V:\projects\prompt-forge
$env:PYTHONPATH = "$PWD\src"

# 安裝 project + MCP dependency
python -m pip install -e .

# 各階段輸入輸出契約
python -m prompt_forge io

# 跑案例 / evaluator
python -m prompt_forge eval

# 單次 compile + 顯示 task contract
python -m prompt_forge run --request "給 Codex 一個任務，把登入 callback bug 修好並驗證。" --show-prompt

# 完整 regression suite
python -m unittest discover -s tests -v

# 本機 HTTP caller
python -m prompt_forge.edgar_os "幫我修好這個 repo，測試完開 PR。"

# STDIO MCP adapter
prompt-forge-mcp
# 或
python -m prompt_forge.mcp_server
```

## 目錄

```text
prompt-forge/
├─ docs/                 # PromptOS boundary / local/API/MCP docs
├─ src/prompt_forge/     # compiler + deterministic pipeline + HTTP/MCP
├─ prompts/              # prompt/template notes
├─ routers/              # routing notes
├─ evaluators/           # evaluation notes
├─ examples/cases/       # regression examples
├─ tests/                # unittest
├─ adapters/             # external-source adapter notes
├─ .github/workflows/    # CI
└─ scripts/
```

## 專案角色

- **產品擁有者：** 王世鈞（Edgar）／德德
- **協作原則：** models / agents / tools are replaceable collaborators; EDGAR-OS retains continuity and authority boundaries.

## Version

Current development package version: `0.2.0.dev0`.

這是 development version 對齊，不等於正式 release/tag。

## License

尚未定案。正式發布前再選擇合適授權方式。
