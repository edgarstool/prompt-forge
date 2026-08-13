# Router Rules (local v0.1)

Deterministic keyword-weighted classification lives in `src/prompt_forge/intent.py`.
Routing defaults live in `src/prompt_forge/router.py`.

## Task types

| Type | Default agent | Default tools |
|---|---|---|
| research | chatgpt | web-search |
| coding | codex | github, git (+ git-branch if isolation) |
| local-files | hermes-local | filesystem |
| cloud-saas | codex | docs, cli |
| agent-workflow | hermes | mcp, workflow-notes |
| deterministic-tool | local-script | python, powershell |

## Overrides

1. `preferred_agent` overrides default agent label.
2. High-risk secret handling forces `local-script` and blocks external secret exfil.
3. Coding + medium/high risk adds branch isolation assumption.

## Out of scope for this file

- LLM-based classifiers
- Production multi-tenant policy packs
