# PromptOS Continuation Policy

Status: development contract
Related: #13, PR #14

## Purpose

PromptOS already distinguishes goal, scope, authority, evidence, validation and stop conditions. This document adds the missing execution-horizon semantic: what an executor should do **after one bounded cut passes validation while the parent goal is still incomplete**.

The core invariant is:

> Bounded execution does not imply single-cut execution.

A sustained task remains bounded when every cut is inside the same parent scope/authority, independently verified, persisted when meaningful, and followed by a fresh decision about the next safe cut.

## Orthogonality

Execution mode answers **what kind of work is this?**

Examples:

- `BUILD`
- `DEBUG`
- `RESEARCH`
- `BROWSER_OPERATOR`
- `MAINTENANCE`

Continuation policy answers **how far should the executor continue?**

Current policies:

- `SINGLE_CUT`
- `CONTINUE_UNTIL_GOAL`
- `CONTINUE_UNTIL_BLOCKED`

Therefore a contract may be:

```text
execution_mode = BUILD
continuation_policy = CONTINUE_UNTIL_BLOCKED
```

Continuation is not a replacement execution mode such as `LONG_RUNNING`.

## Policy semantics

### `SINGLE_CUT`

Perform one bounded outcome, validate it, return evidence, and stop.

This remains the default when the user does not express sustained-execution intent.

### `CONTINUE_UNTIL_GOAL`

After each verified bounded cut:

1. persist meaningful evidence/state transition;
2. reassess the parent goal;
3. if incomplete, select the highest-value next bounded cut inside the existing scope and authority;
4. continue without asking the human for routine implementation decisions;
5. stop when the parent goal is verifiably reached or a real terminal gate is encountered.

### `CONTINUE_UNTIL_BLOCKED`

Use the same bounded-cut loop, but the primary terminal semantics are:

- parent goal reached; or
- no safe authorized next cut exists because a real human/authority/capability gate blocks continuation.

Ordinary diagnosable implementation failures are not automatically terminal. Build failures, tests, type errors, API 400/401/403 responses, repo conflicts and similar recoverable failures should normally be diagnosed and retried when that remains safe and in scope.

## Runtime loop contract

Prompt Forge compiles this behavior but does not execute the long-running loop itself.

```text
parent goal
  ↓
select bounded cut
  ↓
execute
  ↓
verify acceptance / consumption boundary
  ↓
persist meaningful evidence/state
  ↓
reassess parent goal + authority + scope + resource guard
  ↓
continue OR terminal state
```

The runtime/orchestrator remains the responsibility of the selected capable executor or Agent Platform.

## Human and authority gates

Continuation never means auto-approve everything.

Typical terminal/escalation gates include:

- human login, MFA, OAuth consent, or identity proof that must be performed by the owner;
- new payment or billing commitment;
- irreversible destructive action;
- force-push or destructive shared-history rewrite;
- production credential revocation/rotation or secret mutation with material impact;
- material production policy/DNS/route mutation without delegated authority;
- true architecture conflict with no safe reversible default;
- required verification unavailable such that success would be speculative.

The task contract should ask the human for the **minimum action needed to unblock continuation**, not hand the whole task back when the executor can safely resume afterward.

## Resource guard

Sustained execution is not permission for unbounded resource consumption.

The compiled contract must preserve these rules:

- no new purchase or paid commitment without authority;
- no inference that missing budget means unlimited budget;
- explicit time/token/platform-credit/cut limits must be respected when supplied;
- resource exhaustion is a legitimate terminal condition;
- optimization or exploration must not silently expand beyond the parent goal to keep an agent busy.

A future structured `resource_guard` field may be added if runtime integrations need machine-readable limits. The current minimal implementation keeps the guard in the compiled continuation section.

## Evaluation invariant

`Continuation discipline` is a separate quality axis from `Stop conditions`.

For sustained tasks the evaluator requires both:

- positive continuation semantics: bounded cut → verify → persist → continue;
- runaway protection: stop conditions plus a paid/budget resource guard.

A sustained contract fails the hard evaluation gate if continuation discipline is missing.

This catches both failure modes:

1. **premature stop**: one subtask passes, parent goal remains incomplete, safe next work exists, executor stops anyway;
2. **runaway continuation**: executor widens scope, bypasses authority, or consumes unbounded paid resources merely because continuation was requested.

## Current implementation boundary

PR #14 implements the first deterministic compiler/composer/evaluator cut:

- continuation intent detection in `compiler.py`;
- `SemanticContract.continuation_policy`;
- positive `Continuation Policy` prompt section for sustained tasks;
- continuation policy surfaced in prompt metadata;
- `Continuation discipline` evaluator check;
- sustained continuation discipline is a hard check;
- regression coverage for default single-cut, continue-until-goal and continue-until-blocked behavior.

Prompt Forge still does **not** become the long-running runtime/orchestrator.
