"""Context7 / official-docs freshness policy."""

from __future__ import annotations

import re

from .schema import ContextPolicyResult, IntentResult, RouteResult, UserRequest

_TECH_HINTS = [
    r"sdk",
    r"api",
    r"cli",
    r"framework",
    r"library",
    r"npm",
    r"pip",
    r"cloudflare",
    r"tensorflow",
    r"pytorch",
    r"docker",
    r"kubernetes",
    r"版本",
    r"v\d+\.\d+",
]


def apply_context_policy(
    req: UserRequest,
    intent: IntentResult,
    route: RouteResult,
) -> ContextPolicyResult:
    text = req.request
    reasons: list[str] = []
    notes: list[str] = []

    tech_hit = any(re.search(p, text, flags=re.IGNORECASE) for p in _TECH_HINTS)
    type_wants_docs = intent.task_type in {"coding", "cloud-saas", "agent-workflow"}
    version_pin = bool(re.search(r"v\d+|版本|version", text, flags=re.IGNORECASE))

    use = False
    if type_wants_docs and tech_hit:
        use = True
        reasons.append("technical-task-with-library-or-service-signal")
    if version_pin:
        use = True
        reasons.append("explicit-version-sensitivity")
    if intent.task_type == "coding" and re.search(r"repo|github|pr\b|sdk|api", text, flags=re.IGNORECASE):
        # repo repair often needs current tooling docs; keep soft-on
        use = True
        reasons.append("coding-repo-task")

    # Do NOT force Context7 for pure local organize / generic writing / secret list shaping
    if intent.task_type in {"local-files", "deterministic-tool"} and not version_pin:
        if use and intent.task_type == "local-files":
            use = False
            reasons = ["suppressed:local-files-no-external-api"]
        if intent.task_type == "deterministic-tool" and re.search(
            r"secret|金鑰|token|api[_\s-]?key", text, flags=re.IGNORECASE
        ):
            use = False
            reasons = ["suppressed:secret-local-processing"]

    if use:
        notes.append("Require version-matched official docs via Context7 (or equivalent) before coding claims.")
        if "context7" not in route.supporting_tools:
            # non-mutating note only; router remains source of tools list
            notes.append("Composer will instruct agent to use Context7 even if tool list was generic.")
    else:
        notes.append("No Context7 injection; task does not need external API/SDK freshness.")

    if not reasons:
        reasons.append("default-no-context7")

    return ContextPolicyResult(use_context7=use, reasons=reasons, policy_notes=notes)
