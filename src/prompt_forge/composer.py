"""Prompt composition."""

from __future__ import annotations

from .compiler import CompilationDecision, SemanticContract, compile_request
from .schema import (
    REQUIRED_PROMPT_SECTIONS,
    ComposedPrompt,
    ContextPolicyResult,
    IntentResult,
    RiskResult,
    RouteResult,
    UserRequest,
)


def _scope_for(task_type: str) -> tuple[str, str]:
    includes = {
        "research": "Collect current options, constraints, sources with dates, and a short comparison.",
        "coding": "Reproduce issue, implement minimal fix on a branch, run tests, open/update PR.",
        "local-files": "Inventory folder, propose classification, execute non-destructive organize, write report.",
        "cloud-saas": "Inspect current config, make the smallest useful authorized change, validate the intended interface.",
        "agent-workflow": "Map the required actors/tools, define bounded handoff, and produce runnable workflow instructions.",
        "deterministic-tool": "Use deterministic local tooling for structured transformation and validation.",
    }
    excludes = {
        "research": "Do not purchase, sign up with payment, or change production accounts unless explicitly authorized.",
        "coding": "Do not force-push, rewrite shared history, or touch unrelated dirty files.",
        "local-files": "Do not mass-delete or move unrelated material outside the agreed scope.",
        "cloud-saas": "Do not change billing, identity authority, or unrelated production configuration.",
        "agent-workflow": "Do not widen privileges or create unrelated parallel automation.",
        "deterministic-tool": "Do not send sensitive raw values to unrelated external systems.",
    }
    return includes.get(task_type, "Complete the requested outcome."), excludes.get(
        task_type, "Avoid irreversible or unrelated changes."
    )


def _execution_steps(
    req: UserRequest,
    intent: IntentResult,
    risk: RiskResult,
    route: RouteResult,
    ctx: ContextPolicyResult,
    decision: CompilationDecision,
) -> str:
    if not decision.should_compile:
        return (
            "1. Answer the user's question directly.\n"
            "2. Do not manufacture an execution handoff or large task contract.\n"
            "3. State uncertainty only when it materially affects the answer."
        )

    steps: list[str] = [
        f"1. Preserve this outcome without silently shrinking it: {req.request}",
        f"2. Execute as `{route.recommended_agent}` with the smallest sufficient set of tools: {', '.join(route.supporting_tools) or 'none specified'}.",
        "3. Retrieve or live-verify mutable state before relying on it; do not promote memory or agent repetition into current truth.",
    ]

    n = 4
    if ctx.use_context7:
        steps.append(
            f"{n}. Check version-matched primary/official documentation before version-sensitive claims or edits."
        )
        n += 1

    if decision.execution_mode == "BROWSER_OPERATOR":
        steps.extend(
            [
                f"{n}. Use the authenticated browser/operator surface; change only the intended setting or page state.",
                f"{n+1}. Read the affected UI state back after the change and verify the intended value is visible.",
            ]
        )
    elif decision.execution_mode == "SCHEDULED_RUN":
        steps.extend(
            [
                f"{n}. Bootstrap from canonical/current sources instead of stale chat-only state.",
                f"{n+1}. Perform one bounded run, emit continuation evidence, and write back durable state when warranted.",
            ]
        )
    elif intent.task_type == "coding":
        steps.extend(
            [
                f"{n}. Reproduce or characterize the target behavior before changing production code.",
                f"{n+1}. Make the smallest relevant code change on an isolated branch and run the repo's existing checks.",
                f"{n+2}. Verify the caller/user-visible behavior and return branch/commit/PR evidence.",
            ]
        )
    elif intent.task_type == "research":
        steps.extend(
            [
                f"{n}. Gather current evidence from independent/primary sources when freshness matters.",
                f"{n+1}. Separate verified facts, dated observations, inference, and unresolved conflict.",
                f"{n+2}. Synthesize the smallest decision-useful result instead of dumping sources.",
            ]
        )
    else:
        steps.extend(
            [
                f"{n}. Execute the smallest useful authorized change inside scope.",
                f"{n+1}. Verify the actual consumption boundary rather than the intermediate configuration alone.",
            ]
        )

    if risk.requires_isolation:
        steps.append("Isolation: keep unrelated workspace state out of the change; use a branch/worktree when appropriate.")
    if risk.forbid_external_secret_exfil:
        steps.append("Sensitive-data boundary: keep raw secret values on an authorized deterministic/local path.")

    return "\n".join(steps)


def _lines(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items)


def compose_prompt(
    req: UserRequest,
    intent: IntentResult,
    risk: RiskResult,
    route: RouteResult,
    ctx: ContextPolicyResult,
    *,
    decision: CompilationDecision | None = None,
    contract: SemanticContract | None = None,
) -> ComposedPrompt:
    if decision is None or contract is None:
        decision, contract = compile_request(req, intent, risk, route, ctx)

    include, exclude = _scope_for(intent.task_type)
    constraints = contract.constraints[:] or ["No additional explicit constraints supplied."]

    sections = {
        "Context": (
            f"Execution mode: {decision.execution_mode}.\n"
            f"Task type: {intent.task_type} (confidence {intent.confidence}).\n"
            f"Risk level: {risk.level}.\n"
            f"Recommended executor: {route.recommended_agent}.\n"
            f"Truth state: {contract.truth_state}."
        ),
        "Goal": contract.goal,
        "Scope": f"In scope: {include}\nOut of scope: {exclude}",
        "Known Facts": _lines(contract.evidence),
        "Assumptions": _lines(contract.unknowns),
        "Execution Task": _execution_steps(req, intent, risk, route, ctx, decision),
        "Validation": contract.acceptance,
        "Deliverables": (
            "- Short status\n"
            "- What changed / what was learned\n"
            "- Verification evidence\n"
            "- Remaining limitations or unresolved unknowns\n"
            "- Next bounded action only when needed"
        ),
        "Stop Conditions": (
            "Stop and report rather than improvising indefinitely when:\n"
            "- the required target cannot be identified or current evidence materially conflicts;\n"
            "- a new payment, identity/authority decision, irreversible destructive action, or force-push/history rewrite is required;\n"
            "- required verification cannot be performed and success would otherwise be speculative."
        ),
        "Output Format": (
            "Return a concise completion receipt with outcome, evidence, limits, and write-back status. "
            "Do not call configuration/planning/attempts 'done' without acceptance evidence."
        ),
        "Authority & Context": _lines(contract.authority),
        "Execution Freedom": _lines(contract.methods + contract.preferences + contract.policy),
        "Evidence Return": contract.evidence_return,
        "Write-back": contract.write_back,
        "Constraints": _lines(constraints),
    }

    if ctx.use_context7:
        sections["Context Freshness"] = (
            "Use version-matched primary/official documentation for libraries, SDKs, CLIs, APIs, or fast-changing services."
        )

    ordered_keys = list(REQUIRED_PROMPT_SECTIONS) + [
        "Authority & Context",
        "Execution Freedom",
        "Evidence Return",
        "Write-back",
        "Constraints",
        "Context Freshness",
    ]

    title = (
        "# Direct Answer Recommendation (Prompt Forge)"
        if not decision.should_compile
        else "# Executable Task Contract (Prompt Forge)"
    )
    lines = [title, ""]
    for key in ordered_keys:
        value = sections.get(key)
        if not value or not value.strip():
            continue
        lines.append(f"## {key}")
        lines.append(value.rstrip())
        lines.append("")

    rendered = "\n".join(lines).strip() + "\n"
    meta = {
        "task_type": intent.task_type,
        "recommended_agent": route.recommended_agent,
        "risk_level": risk.level,
        "use_context7": ctx.use_context7,
        "execution_mode": decision.execution_mode,
        "should_compile": decision.should_compile,
        "compile_reasons": decision.reasons,
        "truth_state": contract.truth_state,
        "semantic_contract": contract.to_dict(),
        "section_count": len([k for k in ordered_keys if sections.get(k)]),
    }
    return ComposedPrompt(sections=sections, rendered=rendered, meta=meta)
