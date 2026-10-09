"""PromptOS compiler/router semantics for Prompt Forge v0.2.

This module keeps semantic interpretation separate from prompt rendering:
- Prompt Forge decides whether a handoff is useful and what execution mode fits.
- It carries distinct Goal / Authority / Evidence / Constraint / Policy /
  Preference / Method / Unknown slots.
- Composer turns that contract into the smallest useful executable prompt.

The implementation is deterministic and intentionally conservative. It does
not claim live state beyond evidence supplied to the compiler.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import re

from .schema import ContextPolicyResult, IntentResult, RiskResult, RouteResult, UserRequest

EXECUTION_MODES = (
    "DIRECT",
    "EXECUTION_HANDOFF",
    "RESEARCH",
    "BUILD",
    "DEBUG",
    "BROWSER_OPERATOR",
    "MAINTENANCE",
    "SCHEDULED_RUN",
    "STRATEGIC",
)

CONTINUATION_POLICIES = (
    "SINGLE_CUT",
    "CONTINUE_UNTIL_GOAL",
    "CONTINUE_UNTIL_BLOCKED",
)

TRUTH_STATES = (
    "VERIFIED_CURRENT",
    "DATED_OBSERVATION",
    "HISTORICAL",
    "INFERRED",
    "UNKNOWN",
    "CONFLICTED",
)


@dataclass
class CompilationDecision:
    execution_mode: str
    should_compile: bool
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass
class SemanticContract:
    goal: str
    authority: list[str]
    evidence: list[str]
    constraints: list[str]
    policy: list[str]
    preferences: list[str]
    methods: list[str]
    unknowns: list[str]
    truth_state: str
    continuation_policy: str
    acceptance: str
    evidence_return: str
    write_back: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _contains(text: str, patterns: tuple[str, ...]) -> bool:
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)


def _is_explicit_handoff(text: str) -> bool:
    return _contains(
        text,
        (
            r"\bprompt\b",
            r"\bhandoff\b",
            r"代理任務",
            r"給\s*(?:codex|claude|gemini|agent)",
            r"叫\s*(?:codex|claude|gemini|agent|hermes|openclaw)",
            r"交給",
            r"委派",
            r"可執行任務",
        ),
    )


def _looks_direct(text: str) -> bool:
    question = _contains(
        text,
        (
            r"差在哪",
            r"是什麼",
            r"什麼是",
            r"怎麼理解",
            r"介紹",
            r"解釋",
            r"\?$",
            r"？$",
        ),
    )
    action = _contains(
        text,
        (
            r"幫我.*(?:做|修|改|部署|建立|執行|搬|整理)",
            r"請.*(?:做|修|改|部署|建立|執行)",
            r"每小時|每天|每週|排程|定期",
        ),
    )
    return question and not action and not _is_explicit_handoff(text)


def _execution_mode(req: UserRequest, intent: IntentResult) -> CompilationDecision:
    text = req.request.lower()

    if _looks_direct(text):
        return CompilationDecision(
            execution_mode="DIRECT",
            should_compile=False,
            reasons=["simple-answer-better-than-handoff"],
        )

    if _contains(text, (r"每小時", r"每天", r"每週", r"排程", r"定期", r"scheduled", r"recurring")):
        return CompilationDecision(
            execution_mode="SCHEDULED_RUN",
            should_compile=True,
            reasons=["recurring-or-unattended-trigger"],
        )

    if _contains(text, (r"chrome", r"browser", r"dashboard", r"瀏覽器", r"網頁介面", r"\bui\b")):
        return CompilationDecision(
            execution_mode="BROWSER_OPERATOR",
            should_compile=True,
            reasons=["authenticated-or-cross-page-ui-work"],
        )

    if intent.task_type == "coding":
        mode = "DEBUG" if _contains(text, (r"debug", r"root cause", r"為什麼.*壞", r"查.*原因")) else "BUILD"
        return CompilationDecision(mode, True, [f"task-type={intent.task_type}"])

    if intent.task_type == "research":
        return CompilationDecision("RESEARCH", True, ["research-intent"])

    if intent.task_type in {"local-files", "cloud-saas", "agent-workflow", "deterministic-tool"}:
        mode = "MAINTENANCE" if _contains(text, (r"修復", r"維護", r"reconcile", r"cleanup", r"整理現況")) else "EXECUTION_HANDOFF"
        return CompilationDecision(mode, True, [f"task-type={intent.task_type}"])

    return CompilationDecision("EXECUTION_HANDOFF", True, ["fallback-handoff"])


def _continuation_policy(req: UserRequest, decision: CompilationDecision) -> str:
    """Resolve how far the executor should continue after one verified cut.

    Continuation is intentionally orthogonal to execution mode. A BUILD can be
    single-cut or sustained; DIRECT answers stay single-cut. Explicit negation
    of continuation wins over positive continuation keywords so the compiler
    never reverses a requested single-cut boundary.
    """

    if not decision.should_compile or decision.execution_mode == "DIRECT":
        return "SINGLE_CUT"

    text = req.request.lower().replace("’", "'").replace("‘", "'")

    explicit_single_cut = _contains(
        text,
        (
            r"(?:do\s+not|don't|dont|never)\s+(?:keep|continue)\s+(?:going|working|work)",
            r"(?:do\s+not|don't|dont|never)\s+continue\b",
            r"(?:不要|別|不可)(?:再)?(?:繼續|接著|持續)(?:做|執行|施工|工作|處理|推進)?",
            r"(?:只|僅)(?:做|處理|修|執行).*(?:一個|一項|第一個|第一步).*(?:就停|後停止|後就停|不要再做)",
        ),
    )
    if explicit_single_cut:
        return "SINGLE_CUT"

    until_goal = _contains(
        text,
        (
            r"直到.*(?:完成|做完|達成|結束)",
            r"(?:做到|一路做到|持續做到).*(?:完成|做完|達成)",
            r"(?:完成|做完|達成).*為止",
            r"until\s+(?:(?:(?:the\s+)?(?:task|goal|work)|it|everything)(?:\s+is|'s)?\s+)?(?:done|complete|completed|finished|completion)\b",
            r"(?:run|work(?:\s+on\s+it)?|continue(?:\s+working)?)\s+until\s+completion\b",
        ),
    )
    if until_goal:
        return "CONTINUE_UNTIL_GOAL"

    until_blocked = _contains(
        text,
        (
            r"不要.*(?:停|停下|停工)",
            r"(?:持續|繼續|接著).*(?:做|執行|施工|推進)",
            r"只有.*(?:授權|批准|人工|人類|我).*(?:才停|再停|停下)",
            r"直到.*(?:阻塞|卡住|需要.*授權|需要.*批准)",
            r"continue\s+until\s+blocked",
            r"keep\s+(?:going|working)",
        ),
    )
    if until_blocked:
        return "CONTINUE_UNTIL_BLOCKED"

    return "SINGLE_CUT"


def _truth_state(known_context: list[str]) -> str:
    upper = "\n".join(known_context).upper()
    for state in TRUTH_STATES:
        if state in upper:
            return state
    return "DATED_OBSERVATION" if known_context else "UNKNOWN"


def _acceptance(decision: CompilationDecision, req: UserRequest, risk: RiskResult) -> str:
    checks = [
        "Use observable acceptance conditions, not a plausible completion claim.",
        "Verify the actual consumption boundary when a runnable system or integration is involved.",
        f"Respect risk level `{risk.level}` and report a real blocker instead of inventing success.",
    ]
    if decision.execution_mode == "BROWSER_OPERATOR":
        checks.append("After the UI mutation, perform read-back from the affected page/state and confirm the intended value is visible.")
    if decision.execution_mode == "SCHEDULED_RUN":
        checks.append("The run must be self-contained, produce continuation evidence, and remain usable without stale chat-only context.")
    if decision.execution_mode in {"BUILD", "DEBUG"}:
        checks.append("Run the repository's relevant tests/checks and verify the user-visible or caller-visible behavior that motivated the change.")
    if decision.execution_mode == "DIRECT":
        checks.append("Answer the question directly without manufacturing an execution handoff.")
    return " ".join(checks)


def compile_request(
    req: UserRequest,
    intent: IntentResult,
    risk: RiskResult,
    route: RouteResult,
    ctx: ContextPolicyResult,
) -> tuple[CompilationDecision, SemanticContract]:
    """Compile request semantics before rendering the executable prompt."""

    decision = _execution_mode(req, intent)
    continuation_policy = _continuation_policy(req, decision)
    evidence = req.known_context[:] or ["No verified evidence supplied to this compile request."]
    constraints = req.constraints[:]
    if risk.level == "high":
        constraints.append("High-impact actions require the corresponding authority/confirmation gate.")

    authority = [
        "The user's current request is authoritative for the goal and explicit constraints.",
        "Mutable external state must be resolved from current evidence, not memory or repetition.",
    ]
    if req.preferred_agent:
        authority.append(f"Preferred executor: {req.preferred_agent}; implementation details remain flexible inside scope.")

    preferences = []
    if req.preferred_agent:
        preferences.append(f"Prefer executor `{req.preferred_agent}` when capable and authorized.")

    methods = [
        f"Recommended executor: {route.recommended_agent}.",
        f"Supporting tools: {', '.join(route.supporting_tools) if route.supporting_tools else 'none specified'}.",
    ]
    if ctx.use_context7:
        methods.append("Use version-matched primary/official documentation for freshness-sensitive claims.")

    unknowns: list[str] = []
    if not req.known_context:
        unknowns.append("Runtime/project state was not supplied; retrieve or live-verify it when material to execution.")
    unknowns.extend(route.assumptions)

    policy = [
        "Wide judgment, narrow execution.",
        "Prefer existing capability and reversible execution over unnecessary new infrastructure.",
        "Configured != deployed != usable != persistent; verify the boundary that matters.",
        "Do not turn plans, config edits, commands, or agent claims into verified completion without evidence.",
    ]

    contract = SemanticContract(
        goal=f"Make this outcome true: {req.request}",
        authority=authority,
        evidence=evidence,
        constraints=constraints,
        policy=policy,
        preferences=preferences,
        methods=methods,
        unknowns=unknowns or ["No material unknowns identified from supplied input."],
        truth_state=_truth_state(req.known_context),
        continuation_policy=continuation_policy,
        acceptance=_acceptance(decision, req, risk),
        evidence_return=(
            "Return an evidence package describing what changed, where, verification performed, observed result, "
            "identifiers/URLs/commits when relevant, remaining limits, and unresolved unknowns."
        ),
        write_back=(
            "Write-back meaningful decisions, blockers, source conflicts, and verified state transitions to the "
            "appropriate canonical authority when the task changes durable EDGAR-OS state."
        ),
    )
    return decision, contract
