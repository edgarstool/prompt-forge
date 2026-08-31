"""End-to-end local pipeline orchestration."""

from __future__ import annotations

from typing import Any

from .compiler import compile_request
from .composer import compose_prompt
from .context_policy import apply_context_policy
from .evaluator import evaluate_prompt
from .intent import classify_intent
from .risk import check_risk
from .router import route_request
from .schema import PipelineResult, UserRequest


def run_pipeline(payload: dict[str, Any] | UserRequest) -> PipelineResult:
    req = payload if isinstance(payload, UserRequest) else UserRequest.from_dict(payload)
    intent = classify_intent(req)
    risk = check_risk(req, intent)
    route = route_request(req, intent, risk)
    ctx = apply_context_policy(req, intent, route)
    decision, contract = compile_request(req, intent, risk, route, ctx)
    composition = compose_prompt(
        req,
        intent,
        risk,
        route,
        ctx,
        decision=decision,
        contract=contract,
    )
    evaluation = evaluate_prompt(req, intent, risk, route, ctx, composition)
    return PipelineResult(
        input=req,
        intent=intent,
        risk=risk,
        route=route,
        context_policy=ctx,
        composition=composition,
        evaluation=evaluation,
    )
