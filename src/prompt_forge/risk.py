"""Risk check stage."""

from __future__ import annotations

import re

from .schema import IntentResult, RiskResult, UserRequest

_HIGH_PATTERNS = [
    r"secret",
    r"密碼",
    r"金鑰",
    r"api[_\s-]?key",
    r"token",
    r"production",
    r"正式環境",
    r"付款",
    r"payment",
    r"刪除全部",
    r"rm\s+-rf",
    r"force push",
    r"不可逆",
]

_MEDIUM_PATTERNS = [
    r"\brepo\b",
    r"github",
    r"pr\b",
    r"deploy",
    r"部署",
    r"migrate",
    r"migration",
    r"權限",
    r"oauth",
]


def check_risk(req: UserRequest, intent: IntentResult) -> RiskResult:
    text = req.request
    reasons: list[str] = []
    level = "low"
    ask_user = False
    ask_reasons: list[str] = []

    for pat in _HIGH_PATTERNS:
        if re.search(pat, text, flags=re.IGNORECASE):
            level = "high"
            reasons.append(f"high:{pat}")

    if level != "high":
        for pat in _MEDIUM_PATTERNS:
            if re.search(pat, text, flags=re.IGNORECASE):
                level = "medium"
                reasons.append(f"medium:{pat}")

    if intent.task_type == "deterministic-tool" and any(
        re.search(p, text, flags=re.IGNORECASE) for p in (r"secret", r"金鑰", r"api[_\s-]?key", r"token")
    ):
        level = "high"
        reasons.append("secret-handling")

    requires_isolation = level in {"medium", "high"} and intent.task_type in {
        "coding",
        "cloud-saas",
        "agent-workflow",
    }
    forbid_external = level == "high" and bool(
        re.search(r"secret|金鑰|api[_\s-]?key|token|密碼", text, flags=re.IGNORECASE)
    )

    # Ask only when truly blocking (v0.1 policy)
    if re.search(r"production|正式環境|付款|payment", text, flags=re.IGNORECASE):
        ask_user = True
        ask_reasons.append("Touches production or payment; confirm target and blast radius.")
    if not text.strip():
        ask_user = True
        ask_reasons.append("Empty request.")

    if not reasons:
        reasons.append("no-elevated-signals")

    return RiskResult(
        level=level,
        reasons=reasons,
        requires_isolation=requires_isolation,
        forbid_external_secret_exfil=forbid_external,
        ask_user=ask_user,
        ask_reasons=ask_reasons,
    )
