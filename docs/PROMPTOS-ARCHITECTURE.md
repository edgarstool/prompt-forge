# EDGAR PromptOS Architecture

Status: active architecture contract

PromptOS is the EDGAR-OS prompt-governance and task-contract layer. Its job is to convert human intent into a bounded, evidence-aware, executable contract that an agent or deterministic tool can act on and later verify.

Prompt Forge is the executable compiler/factory for this contract. It is not the whole PromptOS.

## Core responsibilities

PromptOS should resolve or explicitly carry:

1. **Intent / Goal** — what outcome is actually wanted.
2. **Authority** — who or what has decision authority.
3. **Evidence** — what has been observed or verified.
4. **Constraints / Permissions / Risk** — what is allowed, forbidden, expensive, irreversible or dangerous.
5. **Unknowns / Assumptions** — what is still unknown and what reversible assumptions are being made.
6. **Agent / Tool Routing** — which executor and tools fit the task.
7. **Context Policy** — what context is needed and how fresh it must be.
8. **Task Contract Composition** — how the work is expressed as a bounded executable prompt/handoff.
9. **Evaluation / Validation** — how prompt quality and execution success are judged.
10. **Stop / Escalation** — when execution must stop or return to the human.
11. **Evidence Return / State Transition** — what proof comes back and where durable state is written.

## Canonical flow

```text
Human Intent
→ Intent Classification
→ Authority / Evidence / Constraint Resolution
→ Risk & Permission Check
→ Agent / Tool Routing
→ Context Policy
→ Assumption / Unknown Handling
→ Prompt / Task Contract Composition
→ Prompt Evaluation
→ Execution Handoff
→ Validation / Evidence Return
→ State Transition / Write-back
```

The current Prompt Forge local implementation covers the central deterministic compile/evaluate loop:

```text
intent → risk → route → context policy → compose → evaluate
```

The larger EDGAR-OS runtime may later wrap this with team selection, tool attachment, long-running orchestration, evidence collection and state write-back.

## Task-contract fields

Fields scale with task complexity. Simple tasks may collapse several fields; complex or risky tasks should make them explicit.

- Goal
- Known Facts / Evidence
- Authority
- Scope
- Constraints / Permissions
- Assumptions / Unknowns
- Selected Executor / Tools
- Context Freshness Requirements
- Execution Task
- Validation / Acceptance Criteria
- Deliverables
- Stop Conditions
- Evidence to Return
- State Transition / Write-back Target

The goal is not verbosity. The goal is an executable, bounded and testable contract.

## Architecture boundary

```text
EDGAR-OS
├─ PromptOS                  # governance / task-contract architecture
│  ├─ authority & evidence
│  ├─ constraints / permission / risk
│  ├─ assumptions / unknowns
│  ├─ routing
│  ├─ context freshness
│  ├─ validation / stop conditions
│  └─ evidence return / state transition
│
├─ Prompt Forge             # executable PromptOS compiler / factory
│  ├─ Router
│  ├─ Composer
│  ├─ Context Policy
│  └─ Evaluator
│
├─ Cloud KB                 # dynamic runtime rules / pointers
├─ Project Instructions     # survival kernel / enforcement
├─ START HERE               # authority navigation
├─ Agent-KB                 # stable agent-side rules / playbooks
└─ Execution Agents         # narrow execution + evidence return
```

PromptOS does not replace Cloud KB, Project Instructions, START HERE or Agent-KB. It defines how their relevant rules and facts become an executable task contract.

## Authority and freshness

For EDGAR-OS operation:

- PromptOS architecture is governed by the canonical EDGAR-OS PromptOS SSoT.
- Prompt Forge executable behavior is governed by this repository's `master` branch and tests.
- Dynamic collaboration and routing policy belongs to Cloud KB.
- Navigation belongs to START HERE.
- Project/runtime state belongs to the newest relevant SSoT, issue, repo evidence or live observation.

When a summary conflicts with live implementation, the newer verifiable evidence wins and the stale summary should be corrected rather than silently blended.

## Context freshness policy

Require Context7 or equivalent primary/official documentation verification when the task depends on:

- a library, framework, SDK, API or CLI;
- a fast-changing cloud service;
- a specified version;
- version-sensitive code or configuration.

Do not force live-doc lookups onto stable writing or deterministic local-file tasks when freshness is not material.

## Evaluation principles

Core quality axes:

- Executable
- Goal clarity
- Scope clarity
- Validation
- Deliverables
- Stop conditions
- Assumption discipline
- Context freshness
- Proportional safety
- Concision

`Executable`, `Goal clarity` and `Validation` are mandatory qualities.

## Non-goals

PromptOS / Prompt Forge v0.1 is not:

- a complete chat product;
- a multi-tenant identity/account platform;
- a prompt marketplace;
- a complex frontend;
- an autonomous production-change platform;
- a full long-running Agent Platform.

## Current implementation status

As verified on 2026-08-19 from `master`:

- the local pipeline is runnable (EDG-342);
- the deterministic loop exists;
- four minimal cases exist;
- CLI and unittest exist;
- external service/API packaging is not yet implemented.

Therefore older descriptions saying Router / Composer / Evaluator / CLI are still missing are stale and must not be used as current state.
