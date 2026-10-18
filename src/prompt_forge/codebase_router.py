"""Conservative, offline EDGAR Codebase shortlist; never asserts canonical/live truth.

Source: 2026-10-18 EDGAR GitHub Control Map. No network, model or paid API.
This module only suggests source repositories; callers must verify against
current GitHub, YouTrack and provider/runtime before writes or deployment.
"""
from __future__ import annotations

import re

SOURCE = "PROVISIONAL_INDEX_2026-10-18"
MAP_URL = "https://docs.google.com/document/d/1vAG_WIvoRAIV5uYe7WlLmMcgiqlAy3VwytUPAMG6yDE/edit"

# Only task-shaped shortlist candidates, not the full 87-repository inventory.
ROUTES = {
    "edgarstool/Agent-KB": (r"agent[- ]kb", r"跨代理規則", r"session.boot", r"\bskill\b"),
    "edgarstool/edgars-mcp": (r"edgars[- ]mcp", r"\bmcp\b", r"384.{0,5}工具"),
    "edgarstool/hermes-agent": (r"hermes", r"amon", r"阿蒙"),
    "edgarstool/edgars-knowledge-runtime": (r"knowledge", r"知識庫", r"知識搜尋", r"語意搜尋", r"qmd"),
    "edgarstool/edgar-os-continuity": (r"materializer", r"continuity", r"對話同步", r"sessiondb"),
    "edgarstool/edgarstool-universal-auth-ui": (r"descope", r"\bauth\b", r"身分驗證"),
    "edgarstool/edgar-webmail": (r"webmail", r"郵件介面"),
    "edgarstool/edgar-mail": (r"edgar[- ]mail", r"郵件後端", r"寄信.*api"),
    "edgarstool/edgar-docker-platform": (r"docker", r"honcho", r"compose"),
    "edgarstool/edgars-cf-workspace": (r"cloudflare", r"\bworker[s]?\b"),
    "edgarstool/edgar-os-control-center": (r"edgar.os.control.center",),
    "edgarstool/edgar-command-center": (r"edgar.command.center",),
    "edgarstool/prompt-forge": (r"prompt[- ]forge", r"promptos"),
}

MAIL = ["edgarstool/edgar-webmail", "edgarstool/edgar-mail"]
CENTERS = ["edgarstool/edgar-os-control-center", "edgarstool/edgar-command-center"]
LINE = ["edgarstool/hermes-agent", "edgarstool/haodai-linebot"]


def _decision(status: str, candidates: list[str], reason: str) -> dict[str, object]:
    return {
        "status": status,
        "primary_repo": candidates[0] if status == "CANDIDATE" and len(candidates) == 1 else None,
        "candidates": [{"repo": repo, "url": f"https://github.com/{repo}"} for repo in candidates],
        "reason": reason,
        "source": SOURCE,
        "source_url": MAP_URL,
        "next_action": (
            "verify YouTrack issue, GitHub repo/branch/PR, canonical ownership and live runtime; "
            "do not mutate or deploy based only on this provisional index"
        ),
    }


def resolve_codebase(request: str) -> dict[str, object]:
    """Return CANDIDATE, AMBIGUOUS, UNKNOWN, REVIEW_REQUIRED or BLOCKED.

    Shortlisting is fail-closed. Even a single candidate is NOT an approved
    working copy, active deployment or authorization to make changes.
    """
    text = request.strip()
    low = text.lower()
    if not low:
        return _decision("UNKNOWN", [], "empty request")

    if re.search(r"\bollama\b|本地模型|local[- ]model", low):
        if re.search(r"清理|刪除|移除|卸載|uninstall|remove|cleanup", low):
            return _decision("REVIEW_REQUIRED", [], "local-model cleanup needs ownership/dependency review")
        if re.search(r"安裝|下載|運行|執行|啟動|部署|install|download|run|deploy", low):
            return _decision("BLOCKED", [], "local model execution/download prohibited")
        return _decision("REVIEW_REQUIRED", [], "local-model cleanup needs ownership/dependency review")

    # An explicit repo identity wins over incidental domain words.
    for name in ROUTES:
        if re.search(r"(?<![\w/-])" + re.escape(name.lower()) + r"(?![\w/-])", low):
            return _decision("CANDIDATE", [name], "exact repository identity supplied")

    # A named cross-system bridge belongs to continuity, not Hermes in general.
    if re.search(r"materializer|continuity|對話同步|sessiondb", low):
        return _decision("CANDIDATE", ["edgarstool/edgar-os-continuity"], "continuity integration signal")

    if re.search(r"控制中心|control[- ]?center|command[- ]?center", low):
        return _decision("AMBIGUOUS", CENTERS, "overlapping control-center repositories")

    if re.search(r"郵件|寄信|mail\b|email\b|webmail", low):
        if re.search(r"webmail|郵件介面|郵件.{0,5}(?:ui|前端)", low):
            return _decision("CANDIDATE", [MAIL[0]], "webmail UI scope")
        if re.search(r"edgar[- ]mail|郵件後端|寄信.*api|mail api", low):
            return _decision("CANDIDATE", [MAIL[1]], "mail backend scope")
        return _decision("AMBIGUOUS", MAIL, "mail UI/backend boundary unresolved")

    # LINE by itself is shared by several products; do not guess Hermes.
    if re.search(r"\bline\b|linebot|line bot", low):
        if re.search(r"hermes|amon|阿蒙", low):
            return _decision("CANDIDATE", [LINE[0]], "Hermes + LINE explicit intersection")
        return _decision("AMBIGUOUS", LINE, "LINE product owner not specified")

    if re.search(r"登入|callback|oauth", low) and not re.search(r"edgar|descope|\bauth\b", low):
        return _decision("UNKNOWN", [], "generic login request without EDGAR ownership evidence")

    # Knowledge stable-rules requests must not be mistaken for runtime changes.
    if re.search(r"agent[- ]kb|跨代理規則", low):
        return _decision("CANDIDATE", ["edgarstool/Agent-KB"], "canonical rules source")

    matches = []
    for name, patterns in ROUTES.items():
        if any(re.search(pat, low, re.IGNORECASE) for pat in patterns):
            matches.append(name)

    if len(matches) == 1:
        return _decision("CANDIDATE", matches, "single indexed domain match")
    if len(matches) > 1:
        return _decision("AMBIGUOUS", matches, "multiple indexed domains match")
    return _decision("UNKNOWN", [], "no supported repo identity; do not invent one")
