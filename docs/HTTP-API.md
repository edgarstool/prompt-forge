# Prompt Forge HTTP API v0.2 Prototype

這一層的目的不是直接上 production，而是先驗證：既有 Prompt Forge pipeline 能不能被其他程式用穩定 JSON 契約呼叫。

## 啟動

Windows PowerShell：

```powershell
cd V:\projects\prompt-forge
$env:PYTHONPATH = "$PWD\src"
python -m prompt_forge.service --host 127.0.0.1 --port 8787
```

若已用 `pip install -e .` 安裝：

```powershell
cd V:\projects\prompt-forge
prompt-forge-service --host 127.0.0.1 --port 8787
```

預設只綁定 `127.0.0.1`，避免原型階段意外對外暴露。

## EDGAR-OS caller

service 啟動後，可由最小 caller 呼叫同一份 HTTP contract：

```powershell
cd V:\projects\prompt-forge
$env:PYTHONPATH = "$PWD\src"
python -m prompt_forge.edgar_os "幫我修好這個 repo，測試完開 PR。"
```

caller 只負責送出 `/v1/compile` request，並確認 response 包含完整 pipeline
artifact；不負責 production hostname、authentication 或 workflow execution。

## GET /health

Request：

```text
GET http://127.0.0.1:8787/health
```

Response：

```json
{
  "ok": true,
  "service": "prompt-forge",
  "version": "0.2.0-dev",
  "pipeline": "local-deterministic"
}
```

## POST /v1/compile

最小 request：

```json
{
  "request": "幫我把這個資料夾整理好。"
}
```

完整可選欄位沿用 `UserRequest`：

```json
{
  "request": "研究目前可用的免費 VM 與 credits。",
  "preferred_agent": "Gemini Deep Research",
  "known_context": ["只接受 recurring cost = $0"],
  "constraints": ["優先官方來源", "列出有效期限"],
  "case_id": "vm-research-demo"
}
```

PowerShell 範例：

```powershell
cd V:\projects\prompt-forge
$Body = @{
  request = "幫我把這個資料夾整理好。"
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8787/v1/compile" `
  -ContentType "application/json" `
  -Body $Body
```

成功 response：

```json
{
  "ok": true,
  "result": {
    "input": {},
    "intent": {},
    "risk": {},
    "route": {},
    "context_policy": {},
    "composition": {
      "sections": {},
      "rendered": "...",
      "meta": {}
    },
    "evaluation": {}
  }
}
```

## Error contract

原型階段統一使用 JSON：

```json
{
  "ok": false,
  "error": "invalid_request",
  "detail": "`request` is required and must be non-empty"
}
```

目前錯誤類型：

- `not_found`
- `invalid_content_length`
- `empty_body`
- `invalid_json`
- `payload_must_be_object`
- `invalid_request`

## 設計選擇：為什麼先不用 FastAPI

v0.2 先用 Python standard library 的 `http.server`，原因是這輪要驗證的是 API contract，不是 web framework。

這讓原型：

- 不新增 dependency。
- 不需要先處理 framework version。
- 可以直接重用 `run_pipeline()`。
- 失敗時容易回退到 local CLI。

若 API contract 通過實際使用，再評估 FastAPI、Cloudflare、container packaging 或 MCP adapter。

## Non-goals

本版本不包含：

- production deployment
- authentication
- rate limiting
- multi-tenant state
- database
- frontend
- live Context7 request
- long-running Agent orchestration

## 驗收

```powershell
cd V:\projects\prompt-forge
$env:PYTHONPATH = "$PWD\src"
python -m unittest discover -s tests -v
```

至少必須驗證：

1. `/health` 回 200。
2. 合法 `/v1/compile` 回完整 pipeline artifact。
3. 缺少 `request` 回 400。
4. malformed JSON 回 400。
5. 未知 endpoint 回 404。
6. 原有 pipeline tests 仍通過。
