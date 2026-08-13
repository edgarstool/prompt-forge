"""Prompt evaluation (10 binary checks)."""

from __future__ import annotations

import re

from .schema import (
    HARD_EVAL_CHECKS,
    REQUIRED_PROMPT_SECTIONS,
    ComposedPrompt,
    ContextPolicyResult,
    EvalCheck,
    EvalResult,
    IntentResult,
    RiskResult,
    RouteResult,
    UserRequest,
)


def _has_section(prompt: ComposedPrompt, name: str) -> bool:
    if name in prompt.sections and prompt.sections[name].strip():
        return True
    return bool(re.search(rf"^##\s+{re.escape(name)}\s*$", prompt.rendered, flags=re.M))


def evaluate_prompt(
    req: UserRequest,
    intent: IntentResult,
    risk: RiskResult,
    route: RouteResult,
    ctx: ContextPolicyResult,
    prompt: ComposedPrompt,
) -> EvalResult:
    text = prompt.rendered
    checks: list[EvalCheck] = []

    # 1 Executable
    executable = (
        all(_has_section(prompt, s) for s in ("Goal", "Execution Task", "Output Format"))
        and len(text) > 200
        and "TODO: ask user everything" not in text.lower()
    )
    checks.append(
        EvalCheck(
            "Executable",
            executable,
            "Has goal + execution + output format and is long enough to run."
            if executable
            else "Missing core executable sections or too thin.",
        )
    )

    # 2 Goal clarity
    goal_ok = _has_section(prompt, "Goal") and len(prompt.sections.get("Goal", "")) >= 12
    checks.append(
        EvalCheck("Goal clarity", goal_ok, "Goal section present and specific." if goal_ok else "Goal weak/missing.")
    )

    # 3 Scope clarity
    scope_txt = prompt.sections.get("Scope", "")
    scope_ok = ("In scope" in scope_txt or "包含" in scope_txt) and (
        "Out of scope" in scope_txt or "不包含" in scope_txt or "Out of scope" in text
    )
    checks.append(
        EvalCheck("Scope clarity", scope_ok, "Includes in/out scope." if scope_ok else "Scope incomplete.")
    )

    # 4 Validation
    val = prompt.sections.get("Validation", "")
    val_ok = _has_section(prompt, "Validation") and len(val) >= 20
    checks.append(
        EvalCheck("Validation", val_ok, "Validation present." if val_ok else "Validation missing/weak.")
    )

    # 5 Deliverables
    del_ok = _has_section(prompt, "Deliverables") and len(prompt.sections.get("Deliverables", "")) >= 10
    checks.append(
        EvalCheck("Deliverables", del_ok, "Deliverables present." if del_ok else "Deliverables missing.")
    )

    # 6 Stop conditions
    stop_ok = _has_section(prompt, "Stop Conditions") and (
        "Stop" in prompt.sections.get("Stop Conditions", "") or "停下" in prompt.sections.get("Stop Conditions", "")
    )
    checks.append(
        EvalCheck("Stop conditions", stop_ok, "Stop conditions present." if stop_ok else "Stop conditions missing.")
    )

    # 7 Assumption discipline
    assume_ok = _has_section(prompt, "Assumptions") and not re.search(
        r"請先回答以下\d+個問題|ask the user all missing details", text, flags=re.I
    )
    checks.append(
        EvalCheck(
            "Assumption discipline",
            assume_ok,
            "Assumptions stated without interrogation spam."
            if assume_ok
            else "Assumptions missing or prompt over-asks.",
        )
    )

    # 8 Context freshness
    if ctx.use_context7:
        fresh_ok = (
            "Context7" in text
            or "official docs" in text.lower()
            or _has_section(prompt, "Context Freshness")
        )
        detail = "Context7/docs requirement present." if fresh_ok else "Needed Context7 but missing."
    else:
        # pass if we did NOT unnecessarily inject Context7 for local/secret tasks
        unnecessary = "Context7" in text and intent.task_type in {"local-files", "deterministic-tool"}
        fresh_ok = not unnecessary
        detail = (
            "Correctly omitted Context7."
            if fresh_ok
            else "Context7 injected where policy says no."
        )
    checks.append(EvalCheck("Context freshness", fresh_ok, detail))

    # 9 Proportional safety
    if risk.level == "low":
        # fail if oversized ceremony
        ceremony = len(re.findall(r"Forbidden Actions|Rollback|multi-party approval", text))
        prop_ok = ceremony <= 2 and "change advisory board" not in text.lower()
        detail = "Low-risk prompt stays light." if prop_ok else "Over-weighted safety for low risk."
    elif risk.level == "high":
        prop_ok = (
            risk.forbid_external_secret_exfil is False
            or ("never send raw secret" in text.lower() or "secret values" in text.lower())
        ) and ("Stop" in text or "停下" in text)
        detail = "High-risk controls present." if prop_ok else "High-risk controls incomplete."
    else:
        prop_ok = risk.requires_isolation is False or (
            "branch" in text.lower() or "Isolation" in text
        )
        detail = "Medium-risk isolation/guidance proportional." if prop_ok else "Medium-risk controls weak."
    checks.append(EvalCheck("Proportional safety", prop_ok, detail))

    # 10 Concision
    # soft heuristic: not a novel; still complete
    wordish = len(text)
    concise_ok = 400 <= wordish <= 9000 and text.count("## ") <= 20
    checks.append(
        EvalCheck(
            "Concision",
            concise_ok,
            f"Length={wordish} within local band." if concise_ok else f"Length={wordish} out of band or too many sections.",
        )
    )

    score = sum(1 for c in checks if c.passed)
    hard_pass = all(c.passed for c in checks if c.name in HARD_EVAL_CHECKS)
    passed = score >= 8 and hard_pass

    return EvalResult(
        checks=checks,
        score=score,
        max_score=len(checks),
        hard_pass=hard_pass,
        passed=passed,
        threshold=8,
    )
