"""Minimal CLI for local Prompt Forge validation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .pipeline import run_pipeline
from .schema import UserRequest

ROOT = Path(__file__).resolve().parents[2]
CASES_DIR = ROOT / "examples" / "cases"


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _print_stage_summary(result) -> None:
    data = result.to_dict()
    print("=== Stage I/O summary ===")
    print(f"input.request: {data['input']['request']}")
    print(
        "intent:",
        data["intent"]["task_type"],
        f"confidence={data['intent']['confidence']}",
    )
    print("risk:", data["risk"]["level"], data["risk"]["reasons"][:4])
    print(
        "route:",
        data["route"]["recommended_agent"],
        data["route"]["supporting_tools"],
        f"confidence={data['route']['confidence']}",
    )
    print(
        "context_policy.use_context7:",
        data["context_policy"]["use_context7"],
        data["context_policy"]["reasons"][:3],
    )
    print(
        "evaluation:",
        f"{data['evaluation']['score']}/{data['evaluation']['max_score']}",
        "PASS" if data["evaluation"]["passed"] else "FAIL",
        f"hard_pass={data['evaluation']['hard_pass']}",
    )


def cmd_run(args: argparse.Namespace) -> int:
    if args.file:
        raw = _load_json(Path(args.file))
        # allow full case files {input, expected, ...} or bare UserRequest
        payload = raw.get("input") if isinstance(raw.get("input"), dict) else raw
    else:
        payload = {
            "request": args.request,
            "preferred_agent": args.agent,
            "known_context": args.context or [],
            "constraints": args.constraint or [],
        }
    result = run_pipeline(payload)
    _print_stage_summary(result)
    if args.show_prompt:
        print("\n=== Composed Prompt ===\n")
        print(result.composition.rendered)
    if args.json_out:
        out = Path(args.json_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nWrote JSON artifact: {out}")
    return 0 if result.evaluation.passed else 2


def _expected_match(result, expected: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    exp_type = expected.get("task_type")
    if exp_type and result.route.task_type != exp_type:
        errors.append(f"task_type expected={exp_type} got={result.route.task_type}")
    exp_agent = expected.get("recommended_agent")
    if exp_agent and result.route.recommended_agent != exp_agent:
        errors.append(
            f"recommended_agent expected={exp_agent} got={result.route.recommended_agent}"
        )
    if "use_context7" in expected:
        if bool(result.context_policy.use_context7) != bool(expected["use_context7"]):
            errors.append(
                f"use_context7 expected={expected['use_context7']} got={result.context_policy.use_context7}"
            )
    if "risk_level" in expected:
        if result.risk.level != expected["risk_level"]:
            errors.append(f"risk_level expected={expected['risk_level']} got={result.risk.level}")
    min_score = expected.get("min_score", 8)
    if result.evaluation.score < min_score:
        errors.append(f"score expected>={min_score} got={result.evaluation.score}")
    if expected.get("must_pass", True) and not result.evaluation.passed:
        failed = [c.name for c in result.evaluation.checks if not c.passed]
        errors.append(f"evaluation failed checks={failed}")
    return errors


def cmd_eval(args: argparse.Namespace) -> int:
    cases_dir = Path(args.cases_dir) if args.cases_dir else CASES_DIR
    paths = sorted(cases_dir.glob("*.json"))
    if args.only:
        paths = [p for p in paths if p.stem in set(args.only)]
    if not paths:
        print(f"No cases found in {cases_dir}", file=sys.stderr)
        return 2

    failed = 0
    print(f"Evaluating {len(paths)} case(s) from {cases_dir}")
    for path in paths:
        case = _load_json(path)
        req = case.get("input") or case
        expected = case.get("expected") or {}
        result = run_pipeline(req)
        errors = _expected_match(result, expected)
        status = "PASS" if not errors else "FAIL"
        if errors:
            failed += 1
        print(
            f"- {path.stem}: {status} "
            f"type={result.route.task_type} agent={result.route.recommended_agent} "
            f"score={result.evaluation.score}/{result.evaluation.max_score} "
            f"ctx7={result.context_policy.use_context7}"
        )
        for e in errors:
            print(f"    ! {e}")
        if args.verbose and not errors:
            print(
                f"    assumptions={result.route.assumptions[:2]} risk={result.risk.level}"
            )

    print(f"\nSummary: {len(paths) - failed}/{len(paths)} passed")
    return 0 if failed == 0 else 1


def cmd_show_io(_: argparse.Namespace) -> int:
    print(
        """
Prompt Forge local stage contracts
----------------------------------
1) input (UserRequest)
   { request: str, preferred_agent?: str|null, known_context?: str[], constraints?: str[] }

2) intent (IntentResult)
   { task_type, signals[], confidence, notes }

3) risk (RiskResult)
   { level: low|medium|high, reasons[], requires_isolation, forbid_external_secret_exfil, ask_user, ask_reasons[] }

4) route (RouteResult)
   { task_type, recommended_agent, supporting_tools[], confidence, assumptions[], rationale[] }

5) context_policy (ContextPolicyResult)
   { use_context7, reasons[], policy_notes[] }

6) composition (ComposedPrompt)
   { sections{name: text}, rendered, meta }

7) evaluation (EvalResult)
   { checks[{name,passed,detail}], score, max_score, hard_pass, passed, threshold }
""".strip()
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="prompt-forge", description="Local Prompt Forge pipeline")
    sub = p.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="Run pipeline on one request")
    run_p.add_argument("--request", help="Free-text request")
    run_p.add_argument("--file", help="JSON file with UserRequest fields")
    run_p.add_argument("--agent", dest="agent", default=None)
    run_p.add_argument("--context", action="append", default=[])
    run_p.add_argument("--constraint", action="append", default=[])
    run_p.add_argument("--show-prompt", action="store_true")
    run_p.add_argument("--json-out", default=None)
    run_p.set_defaults(func=cmd_run)

    eval_p = sub.add_parser("eval", help="Evaluate example cases")
    eval_p.add_argument("--cases-dir", default=None)
    eval_p.add_argument("--only", nargs="*", default=None)
    eval_p.add_argument("--verbose", action="store_true")
    eval_p.set_defaults(func=cmd_eval)

    io_p = sub.add_parser("io", help="Print stage input/output contracts")
    io_p.set_defaults(func=cmd_show_io)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "run" and not args.file and not args.request:
        parser.error("run requires --request or --file")
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
