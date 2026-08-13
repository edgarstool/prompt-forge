# Local Prompt Pipeline (EDG-342)

## Goal

Provide a **local, iterative** loop for:

1. intent classification
2. risk check
3. routing
4. composition
5. evaluation

No public service / auth / multi-tenant entry in this slice.

## Flow

```text
UserRequest JSON
→ intent
→ risk
→ route
→ context_policy
→ composition
→ evaluation
→ artifact (stdout / JSON)
```

## Stage I/O

### input

```json
{
  "request": "幫我把這個資料夾整理好。",
  "preferred_agent": null,
  "known_context": [],
  "constraints": []
}
```

### intent

```json
{
  "task_type": "local-files",
  "signals": ["local-files:資料夾"],
  "confidence": 0.7,
  "notes": "..."
}
```

### risk

```json
{
  "level": "low",
  "reasons": ["no-elevated-signals"],
  "requires_isolation": false,
  "forbid_external_secret_exfil": false,
  "ask_user": false,
  "ask_reasons": []
}
```

### route

```json
{
  "task_type": "local-files",
  "recommended_agent": "hermes-local",
  "supporting_tools": ["filesystem"],
  "confidence": 0.7,
  "assumptions": ["..."],
  "rationale": ["intent=local-files", "risk=low"]
}
```

### context_policy

```json
{
  "use_context7": false,
  "reasons": ["default-no-context7"],
  "policy_notes": ["No Context7 injection; ..."]
}
```

### composition

- `sections`: named prompt blocks
- `rendered`: copy-pasteable markdown prompt
- `meta`: task_type / agent / risk / ctx7 flags

### evaluation

```json
{
  "score": 10,
  "max_score": 10,
  "hard_pass": true,
  "passed": true,
  "threshold": 8,
  "checks": [{"name": "Executable", "passed": true, "detail": "..."}]
}
```

## Commands (Windows PowerShell)

From repo root:

```powershell
$env:PYTHONPATH = "V:\projects\prompt-forge\src"
python -m prompt_forge io
python -m prompt_forge eval
python -m prompt_forge run --request "幫我修好這個 repo，測試完開 PR。" --show-prompt
python -m prompt_forge run --file examples\cases\case_a_local_files.json --json-out G:\AI_WORK_512\tmp\pf-case-a.json
python -m unittest discover -s tests -v
```

## Minimal cases

| ID | Request theme | Expected type |
|---|---|---|
| case_a | folder organize | local-files |
| case_b | free VM / credits | research |
| case_c | repo fix + PR | coding |
| case_d | secret import list | deterministic-tool |

## Acceptance mapping (EDG-342)

| Criterion | Evidence |
|---|---|
| 本地流程可跑 | `python -m prompt_forge eval` exit 0 |
| 各階段 I/O 清楚 | `python -m prompt_forge io` + this doc |
| 最小案例可驗證 | four JSON cases under `examples/cases/` |

## Non-goals

- public HTTP API
- cloud hosting
- Team Presets / Hermes Inn UI integration
- live Context7 network calls
