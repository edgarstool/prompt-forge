"""Agent / tool routing."""

from __future__ import annotations

import re

from .schema import IntentResult, RiskResult, RouteResult, UserRequest

# Default agent map for local validation. Not a product lock-in.
_AGENT_BY_TYPE = {
    "research": "chatgpt",
    "coding": "codex",
    "local-files": "hermes-local",
    "cloud-saas": "codex",
    "agent-workflow": "hermes",
    "deterministic-tool": "local-script",
}

_TOOLS_BY_TYPE = {
    "research": ["web-search"],
    "coding": ["github", "git"],
    "local-files": ["filesystem"],
    "cloud-saas": ["docs", "cli"],
    "agent-workflow": ["mcp", "workflow-notes"],
    "deterministic-tool": ["python", "powershell"],
}

_BROWSER_PATTERNS = (
    r"\bchrome\b",
    r"\bbrowser\b",
    r"dashboard",
    r"瀏覽器",
    r"網頁介面",
    r"\bui\b",
)


def _looks_like_browser_work(text: str) -> bool:
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in _BROWSER_PATTERNS)


def route_request(
    req: UserRequest,
    intent: IntentResult,
    risk: RiskResult,
) -> RouteResult:
    task_type = intent.task_type
    agent = _AGENT_BY_TYPE.get(task_type, "chatgpt")
    tools = list(_TOOLS_BY_TYPE.get(task_type, []))
    assumptions: list[str] = []
    rationale: list[str] = [f"intent={task_type}", f"risk={risk.level}"]

    # Route by capability before brand. Authenticated/cross-page UI work should
    # land on a browser operator rather than a coding agent by default.
    if _looks_like_browser_work(req.request):
        agent = "browser-operator"
        tools = list(dict.fromkeys(tools + ["browser", "ui-read-back"]))
        rationale.append("capability=browser-operator")
        assumptions.append(
            "The task depends on browser/UI state; use an authorized browser operator and read the affected state back after mutation."
        )

    # An explicit preferred executor remains a user preference, provided no
    # stronger secret-safety boundary below requires deterministic local work.
    if req.preferred_agent:
        agent = req.preferred_agent
        rationale.append(f"preferred_agent_override={req.preferred_agent}")
        assumptions.append(
            f"User preferred agent `{req.preferred_agent}`; routing honors preference."
        )

    if risk.forbid_external_secret_exfil:
        agent = "local-script"
        tools = ["python", "powershell", "schema-validator"]
        rationale.append("secret-safe-local-only")
        assumptions.append(
            "Secret values must stay on local deterministic tooling; do not send raw secrets to external LLMs."
        )

    if task_type == "coding":
        assumptions.append("Repository is already available to the selected agent.")
        if risk.requires_isolation:
            tools = list(dict.fromkeys(tools + ["git-branch"]))
            assumptions.append("Work on a feature branch; do not commit unrelated dirty files.")

    if task_type == "local-files":
        assumptions.append("Target folder is accessible on the local machine.")
        assumptions.append("Prefer inventory + classification before any destructive move.")

    if task_type == "research":
        assumptions.append("Fresh web sources are required; cite dates and limits.")

    # confidence blends intent confidence with risk certainty
    confidence = round(min(0.95, intent.confidence * (0.9 if risk.level == "high" else 1.0)), 2)

    return RouteResult(
        task_type=task_type,
        recommended_agent=agent,
        supporting_tools=tools,
        confidence=confidence,
        assumptions=assumptions,
        rationale=rationale,
    )
