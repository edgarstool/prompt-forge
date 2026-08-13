"""Intent classification (deterministic, local)."""

from __future__ import annotations

import re

from .schema import IntentResult, UserRequest

# keyword / phrase → task_type weights
_RULES: list[tuple[str, list[str], float]] = [
    (
        "deterministic-tool",
        [
            r"secret",
            r"密碼",
            r"金鑰",
            r"api[_\s-]?key",
            r"token",
            r"匯入清單",
            r"csv",
            r"regex",
            r"parser",
            r"批次轉換",
            r"json schema",
        ],
        3.0,
    ),
    (
        "coding",
        [
            r"\brepo\b",
            r"github",
            r"pr\b",
            r"pull request",
            r"測試",
            r"test",
            r"bug",
            r"修",
            r"實作",
            r"code",
            r"程式",
            r"branch",
            r"commit",
            r"lint",
            r"ci\b",
        ],
        2.0,
    ),
    (
        "local-files",
        [
            r"資料夾",
            r"folder",
            r"整理檔",
            r"檔案",
            r"desktop",
            r"下載",
            r"downloads",
            r"搬移",
            r"分類.*檔",
            r"目錄",
        ],
        2.0,
    ),
    (
        "research",
        [
            r"研究",
            r"查",
            r"找.*免費",
            r"比較",
            r"調研",
            r"credits?",
            r"vm\b",
            r"方案",
            r"哪家",
            r"最新",
            r"survey",
        ],
        2.0,
    ),
    (
        "cloud-saas",
        [
            r"cloudflare",
            r"aws",
            r"gcp",
            r"azure",
            r"vercel",
            r"supabase",
            r"saas",
            r"oauth",
            r"dns",
            r"tunnel",
            r"worker",
        ],
        2.0,
    ),
    (
        "agent-workflow",
        [
            r"agent",
            r"workflow",
            r"n8n",
            r"orchestr",
            r"多代理",
            r"hermes",
            r"mcp",
            r"技能",
            r"skill",
            r"自動化流程",
        ],
        1.8,
    ),
]


def classify_intent(req: UserRequest) -> IntentResult:
    text = req.request.lower()
    scores: dict[str, float] = {t: 0.0 for t, _, _ in _RULES}
    signals: list[str] = []

    for task_type, patterns, weight in _RULES:
        for pat in patterns:
            if re.search(pat, text, flags=re.IGNORECASE):
                scores[task_type] += weight
                signals.append(f"{task_type}:{pat}")

    # light boosts from known_context / constraints
    blob = " ".join(req.known_context + req.constraints).lower()
    if "repo" in blob or "github" in blob:
        scores["coding"] += 1.0
        signals.append("context:repo")
    if "secret" in blob or "1password" in blob:
        scores["deterministic-tool"] += 1.5
        signals.append("context:secret")

    # preferred agent soft signal
    if req.preferred_agent:
        agent = req.preferred_agent.lower()
        if agent in {"codex", "claude", "cursor"}:
            scores["coding"] += 0.5
            signals.append(f"preferred_agent:{agent}")
        if agent in {"chatgpt", "perplexity"}:
            scores["research"] += 0.5
            signals.append(f"preferred_agent:{agent}")

    best_type = max(scores, key=scores.get)
    best_score = scores[best_type]
    if best_score <= 0:
        best_type = "research"
        signals.append("fallback:research")
        confidence = 0.35
        notes = "No strong keyword match; defaulted to research for discovery."
    else:
        total = sum(scores.values()) or 1.0
        confidence = round(min(0.95, 0.45 + (best_score / total) * 0.5), 2)
        notes = f"Top scores: { {k: round(v, 2) for k, v in scores.items() if v > 0} }"

    return IntentResult(
        task_type=best_type,
        signals=signals,
        confidence=confidence,
        notes=notes,
    )
