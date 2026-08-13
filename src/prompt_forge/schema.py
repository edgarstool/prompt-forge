"""Stage input/output schemas for the local Prompt Forge pipeline.

All stages exchange plain dict / dataclass payloads so the flow is easy to
inspect without external dependencies.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


TASK_TYPES = (
    "research",
    "coding",
    "local-files",
    "cloud-saas",
    "agent-workflow",
    "deterministic-tool",
)

REQUIRED_PROMPT_SECTIONS = (
    "Context",
    "Goal",
    "Scope",
    "Known Facts",
    "Assumptions",
    "Execution Task",
    "Validation",
    "Deliverables",
    "Stop Conditions",
    "Output Format",
)

HARD_EVAL_CHECKS = ("Executable", "Goal clarity", "Validation")


@dataclass
class UserRequest:
    """Pipeline input."""

    request: str
    preferred_agent: str | None = None
    known_context: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    case_id: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "UserRequest":
        if not isinstance(data, dict):
            raise TypeError("request payload must be an object")
        request = (data.get("request") or "").strip()
        if not request:
            raise ValueError("`request` is required and must be non-empty")
        preferred = data.get("preferred_agent")
        if preferred is not None:
            preferred = str(preferred).strip() or None
        known = data.get("known_context") or []
        constraints = data.get("constraints") or []
        if not isinstance(known, list) or not isinstance(constraints, list):
            raise TypeError("`known_context` and `constraints` must be arrays")
        return cls(
            request=request,
            preferred_agent=preferred,
            known_context=[str(x) for x in known],
            constraints=[str(x) for x in constraints],
            case_id=(str(data["case_id"]) if data.get("case_id") else None),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class IntentResult:
    """Output of intent classification."""

    task_type: str
    signals: list[str]
    confidence: float
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RiskResult:
    """Output of risk check."""

    level: str  # low | medium | high
    reasons: list[str]
    requires_isolation: bool
    forbid_external_secret_exfil: bool
    ask_user: bool
    ask_reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RouteResult:
    """Output of agent / tool routing."""

    task_type: str
    recommended_agent: str
    supporting_tools: list[str]
    confidence: float
    assumptions: list[str]
    rationale: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ContextPolicyResult:
    """Output of Context7 / docs freshness policy."""

    use_context7: bool
    reasons: list[str]
    policy_notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ComposedPrompt:
    """Composable prompt sections + rendered text."""

    sections: dict[str, str]
    rendered: str
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class EvalCheck:
    name: str
    passed: bool
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class EvalResult:
    checks: list[EvalCheck]
    score: int
    max_score: int
    hard_pass: bool
    passed: bool
    threshold: int = 8

    def to_dict(self) -> dict[str, Any]:
        return {
            "checks": [c.to_dict() for c in self.checks],
            "score": self.score,
            "max_score": self.max_score,
            "hard_pass": self.hard_pass,
            "passed": self.passed,
            "threshold": self.threshold,
        }


@dataclass
class PipelineResult:
    """Full local pipeline artifact."""

    input: UserRequest
    intent: IntentResult
    risk: RiskResult
    route: RouteResult
    context_policy: ContextPolicyResult
    composition: ComposedPrompt
    evaluation: EvalResult

    def to_dict(self) -> dict[str, Any]:
        return {
            "input": self.input.to_dict(),
            "intent": self.intent.to_dict(),
            "risk": self.risk.to_dict(),
            "route": self.route.to_dict(),
            "context_policy": self.context_policy.to_dict(),
            "composition": self.composition.to_dict(),
            "evaluation": self.evaluation.to_dict(),
        }
