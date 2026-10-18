# EDGAR-OS Codebase Resolver (EDG2-73)
Status: review branch only. Not deployed or automatically consumed by agent fleet.
Source: https://docs.google.com/document/d/1vAG_WIvoRAIV5uYe7WlLmMcgiqlAy3VwytUPAMG6yDE/edit
Task: https://edgars.youtrack.cloud/issue/EDG2-73

## Use
Run after installing Prompt Forge locally:
python -m prompt_forge route-codebase --request "修 Hermes 的 LINE approval 卡片"
python -m prompt_forge run --request "修 Hermes 的 LINE approval 卡片" --show-prompt
python -m unittest discover -s tests -v

Existing STDIO MCP consumers can use prompt_forge_codebase(request) after install/restart.
Existing prompt_forge_compile includes route.codebase in its output and verification caveats in the composed prompt.

## Status contract
CANDIDATE: one provisional source repo candidate, NOT write authority.
AMBIGUOUS: multiple possible repos, do not choose for writes without authoritative verification.
UNKNOWN: insufficient evidence, do not invent a repo.
REVIEW_REQUIRED: verify ownership/dependencies first (such as Ollama cleanup).
BLOCKED: prohibited local-model installation/download/execution.

Each decision cites PROVISIONAL_INDEX_2026-10-18 and must be checked against live GitHub branches/PRs, YouTrack and provider runtime before code changes or deployment.
No paid API, automatic write, merge, or production deployment.

Acceptance includes positive Hermes LINE, Knowledge search, MCP, auth and continuity cases; ambiguous control center/mail/LINE cases; negative generic Github/login, unrelated query; forbidden Ollama installation.
GitHub PR / Actions and actual agent MCP client consumption remain separate acceptance gates.
