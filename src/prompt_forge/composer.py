"""Prompt composition."""

from __future__ import annotations

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
        "cloud-saas": "Inspect current config, propose minimal safe change, validate endpoints.",
        "agent-workflow": "Map agents/tools, define handoff, produce runnable workflow notes.",
        "deterministic-tool": "Use local scripts/parsers only; define schema and validation; avoid LLM for secret values.",
    }
    excludes = {
        "research": "Do not purchase, sign up with payment, or change production accounts.",
        "coding": "Do not merge to default branch, force-push, or touch unrelated dirty files.",
        "local-files": "Do not mass-delete; do not move secrets into chat logs.",
        "cloud-saas": "Do not rotate production secrets or change billing without explicit confirm.",
        "agent-workflow": "Do not deploy production automations in v0.1 local validation.",
        "deterministic-tool": "Do not paste raw secret values to external models or tickets.",
    }
    return includes.get(task_type, "Complete the requested outcome."), excludes.get(
        task_type, "Avoid irreversible production changes."
    )


def _execution_steps(
    req: UserRequest,
    intent: IntentResult,
    risk: RiskResult,
    route: RouteResult,
    ctx: ContextPolicyResult,
) -> str:
    steps: list[str] = []
    steps.append(f"1. Restate the goal in one sentence based on: {req.request}")
    steps.append(f"2. Work as agent `{route.recommended_agent}` using tools: {', '.join(route.supporting_tools) or 'none'}.")

    if ctx.use_context7:
        steps.append(
            "3. Before version-sensitive claims, query Context7 (or official docs) for matching library/service version."
        )
        n = 4
    else:
        n = 3

    if intent.task_type == "local-files":
        steps.append(f"{n}. Inventory the target folder (counts, types, obvious clusters) before moving anything.")
        steps.append(f"{n+1}. Classify into keep / archive / review; preserve originals; avoid destructive deletes.")
        steps.append(f"{n+2}. Apply low-risk moves only after classification; write a change report.")
    elif intent.task_type == "research":
        steps.append(f"{n}. Search current sources; record source + date + eligibility limits.")
        steps.append(f"{n+1}. Compare options in a table: free tier, region, limits, signup friction, risks.")
        steps.append(f"{n+2}. Recommend top 1-2 options with why.")
    elif intent.task_type == "coding":
        steps.append(f"{n}. Create/use a feature branch; keep scope tight to the reported failure.")
        steps.append(f"{n+1}. Implement fix; run the repo's existing tests/linters if present.")
        steps.append(f"{n+2}. Open or update a PR with Status / Files / Verification / Risks.")
    elif intent.task_type == "deterministic-tool":
        steps.append(f"{n}. Keep secret values local. Prefer schema + dry-run validation over model rewriting of secrets.")
        steps.append(f"{n+1}. Define import schema fields and required validation rules.")
        steps.append(f"{n+2}. Produce a redacted sample and a checklist for human import.")
    else:
        steps.append(f"{n}. Gather facts from known context, then execute the smallest useful change.")
        steps.append(f"{n+1}. Validate with a concrete check the user can re-run.")
        steps.append(f"{n+2}. Report outcomes and leftover risks.")

    if risk.requires_isolation:
        steps.append("Isolation: use a dedicated branch/worktree; do not mix unrelated workspace dirt.")
    if risk.forbid_external_secret_exfil:
        steps.append("Security: never send raw secret values to external LLMs, web forms, or public issues.")

    return "\n".join(steps)


def compose_prompt(
    req: UserRequest,
    intent: IntentResult,
    risk: RiskResult,
    route: RouteResult,
    ctx: ContextPolicyResult,
) -> ComposedPrompt:
    include, exclude = _scope_for(intent.task_type)
    known = req.known_context[:] or ["No extra known_context provided."]
    assumptions = list(route.assumptions)
    if not assumptions:
        assumptions = ["No extra assumptions beyond the user request text."]

    constraints = req.constraints[:]
    if risk.level == "high":
        constraints.append("High-risk task: prefer reversible steps and explicit stop on uncertainty.")

    sections = {
        "Context": (
            f"User request: {req.request}\n"
            f"Task type: {intent.task_type} (confidence {intent.confidence}).\n"
            f"Risk level: {risk.level}.\n"
            f"Recommended agent: {route.recommended_agent}."
        ),
        "Goal": f"Produce a completed outcome for: {req.request}",
        "Scope": f"In scope: {include}\nOut of scope: {exclude}",
        "Known Facts": "\n".join(f"- {k}" for k in known),
        "Assumptions": "\n".join(f"- {a}" for a in assumptions),
        "Execution Task": _execution_steps(req, intent, risk, route, ctx),
        "Validation": (
            "Success means:\n"
            "- The main user-visible goal is done or a blocked reason is explicit.\n"
            "- Concrete verification steps were run or clearly impossible with reason.\n"
            f"- Risk controls for level `{risk.level}` were respected."
        ),
        "Deliverables": (
            "- Short status\n"
            "- What changed (paths/commands)\n"
            "- Verification evidence\n"
            "- Known limits / risks\n"
            "- Next step (only if needed)"
        ),
        "Stop Conditions": (
            "Stop and report instead of guessing when:\n"
            "- Required target path/repo/service cannot be identified.\n"
            "- Action needs production/payment/secret rotation confirmation.\n"
            "- Further work would be irreversible without backup.\n"
            + (
                "\n".join(f"- ASK USER: {r}" for r in risk.ask_reasons)
                if risk.ask_user
                else "- Do not block on non-essential clarifications; state assumptions instead."
            )
        ),
        "Output Format": (
            "Reply in Traditional Chinese unless the user request is pure code.\n"
            "Use sections: Status / Files Changed / What Changed / Verification / Known Limits / Risks / Next."
        ),
    }

    if risk.requires_isolation or intent.task_type == "coding":
        sections["Branch / Worktree Isolation"] = (
            "Use a dedicated branch for the change. Do not commit unrelated dirty files. "
            "Prefer worktree only when dual checkouts are truly required."
        )
        sections["Rollback"] = "Keep changes reversible via git revert/reset on the feature branch; no force-push to shared default."
        sections["Forbidden Actions"] = (
            "No merge to default branch, no secrets in commits, no mass delete, no production credential rotation."
        )

    if ctx.use_context7:
        sections["Context Freshness"] = (
            "Use Context7 or official docs for libraries/SDKs/CLIs/cloud APIs mentioned. "
            "Prefer version-matched references; cite what was checked."
        )
    if constraints:
        sections["Constraints"] = "\n".join(f"- {c}" for c in constraints)

    # Render in stable order: required first, then optional extras
    ordered_keys = list(REQUIRED_PROMPT_SECTIONS) + [
        k for k in sections.keys() if k not in REQUIRED_PROMPT_SECTIONS
    ]
    lines = ["# Executable Prompt (Prompt Forge local)", ""]
    for key in ordered_keys:
        if key not in sections:
            continue
        lines.append(f"## {key}")
        lines.append(sections[key].rstrip())
        lines.append("")

    rendered = "\n".join(lines).strip() + "\n"
    meta = {
        "task_type": intent.task_type,
        "recommended_agent": route.recommended_agent,
        "risk_level": risk.level,
        "use_context7": ctx.use_context7,
        "section_count": len(sections),
    }
    return ComposedPrompt(sections=sections, rendered=rendered, meta=meta)
