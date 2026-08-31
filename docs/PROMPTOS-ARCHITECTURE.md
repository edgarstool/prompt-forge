# EDGAR PromptOS Architecture

Status: active architecture contract
Updated: 2026-09-01

PromptOS is the EDGAR-OS prompt-governance and task-contract layer. Its job is to convert human intent into a bounded, evidence-aware, executable contract that an agent or deterministic tool can act on and later verify.

Prompt Forge is the executable compiler/router for this contract. It is not the whole PromptOS and it is not an authority for mutable world state.

## Core architecture invariant

```text
EDGAR-OS          = continuity / context / policy / state / evidence owner
PromptOS          = task-contract governance semantics
Prompt Forge      = compiler + router
Skills            = reusable method libraries
SSoT / repo /
provider / live   = authoritative state sources
Agents / tools    = executors
```

**EDGAR-OS owns context; an agent borrows only the context required for the current task.**

Prompt Forge may carry a task-specific projection of evidence/state, but it must not silently become a parallel SSoT.

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
→ Context Policy / Freshness
→ Semantic Compile / Execution-Mode Decision
→ Assumption / Unknown Handling
→ Prompt / Task Contract Composition
→ Prompt Evaluation
→ Execution Handoff (when needed)
→ Validation / Evidence Return
→ State Transition / Write-back
```

The current Prompt Forge implementation covers the deterministic compile/evaluate core:

```text
intent
→ risk
→ route
→ context policy
→ semantic compiler / execution-mode router
→ compose
→ evaluate
```

It can also decide that a prompt artifact should **not** be produced (`DIRECT`) when direct answering/execution is the smaller correct route.

## Execution modes

The v0.2 development compiler supports these task-level modes:

- `DIRECT`
- `EXECUTION_HANDOFF`
- `RESEARCH`
- `BUILD`
- `DEBUG`
- `BROWSER_OPERATOR`
- `MAINTENANCE`
- `SCHEDULED_RUN`
- `STRATEGIC`

These are contract-routing semantics, not permanent agent identities.

## Semantic slots

Inputs are not flattened into a single priority list. Prompt Forge keeps unlike concepts separate:

- Goal
- Authority
- Evidence
- Constraint
- Policy
- Preference
- Method
- Unknown

Only claims competing for the same semantic slot should be directly arbitrated.

For mutable state, the compiler can carry a truth-state label:

- `VERIFIED_CURRENT`
- `DATED_OBSERVATION`
- `HISTORICAL`
- `INFERRED`
- `UNKNOWN`
- `CONFLICTED`

A label is not proof by itself. `VERIFIED_CURRENT` is valid only when backed by appropriate current evidence supplied/retrieved by the surrounding EDGAR-OS workflow.

## Task-contract fields

Fields scale with task complexity. Simple tasks may collapse several fields; complex or risky tasks should make them explicit.

- Goal / Outcome
- Known Facts / Evidence
- Authority & Context
- Scope
- Constraints / Permissions
- Assumptions / Unknowns
- Selected Executor / Tools
- Execution Freedom / Method
- Context Freshness Requirements
- Execution Task
- Validation / Acceptance Criteria
- Deliverables
- Stop Conditions
- Evidence to Return
- State Transition / Write-back Target

The design principle is **strong perimeter, flexible interior**: constrain the outcome, scope and proof more strongly than every implementation keystroke.

The goal is not verbosity. The goal is the smallest sufficient executable, bounded and testable contract.

## Skill relationship

Prompt Forge is not a giant method library.

Reusable methods should live in discoverable Skills and be loaded only when relevant. Examples include scheduled-run startup behavior, workflow-fix promotion, debugging methods, browser-operation methods, or coding methods.

This gives the context flow:

```text
bootloader / dynamic router
→ relevant Skill(s)
→ task-specific current context/evidence
→ Prompt Forge compile
→ bounded contract
```

Stable repeated workflow lessons should become Skill candidates rather than being copied permanently into Prompt Forge's mother instruction.

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
├─ Prompt Forge             # executable compiler + router
│  ├─ Intent classifier
│  ├─ Risk / permission check
│  ├─ Agent/tool route
│  ├─ Context policy
│  ├─ Semantic compiler / execution-mode decision
│  ├─ Composer
│  └─ Evaluator
│
├─ Skills                   # reusable methods
├─ Cloud KB                 # dynamic runtime rules / pointers
├─ Project Instructions     # survival kernel / enforcement
├─ START HERE               # authority navigation
├─ SSoT / Worklog           # durable verified state / evidence
├─ Agent-KB / knowledge     # stable knowledge / playbooks
└─ Execution Agents         # narrow execution + evidence return
```

PromptOS does not replace Cloud KB, Project Instructions, START HERE, SSoT, Skills, Agent-KB or live providers. It defines how the relevant parts become an executable task contract.

## Authority and freshness

For EDGAR-OS operation:

- PromptOS architecture is governed by the canonical EDGAR-OS PromptOS SSoT.
- Prompt Forge executable behavior is governed by this repository's `master` branch and tests.
- Reusable method behavior belongs to the relevant Skills.
- Dynamic collaboration and routing policy belongs to Cloud KB.
- Navigation belongs to START HERE.
- Project/runtime state belongs to the newest relevant SSoT, issue, repo evidence, provider state or live observation.

When a summary conflicts with live implementation, the newer verifiable evidence wins and the stale summary should be corrected rather than silently blended.

## Context freshness policy

Require current primary/official documentation verification when the task materially depends on:

- a library, framework, SDK, API or CLI;
- a fast-changing cloud service;
- a specified version;
- version-sensitive code or configuration.

Do not force live-doc lookups onto stable writing or deterministic tasks when freshness is not material.

## Evaluation principles

Core quality axes include:

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
- Evidence-return quality
- anti-fake-completion behavior

`Executable`, `Goal clarity` and `Validation` remain mandatory baseline qualities.

Important invariants:

- Plausibility is not correctness.
- A plan/command/config change is not a completed outcome.
- Configured ≠ deployed ≠ usable ≠ persistent.
- Prefer verification at the actual consumption boundary.
- Direct execution/answer is preferable to manufacturing a handoff when no handoff is useful.

## Current implementation status

Verified on 2026-09-01 from PR #9 regression work before merge:

- semantic compiler + execution-mode router implemented;
- semantic slots and truth-state representation implemented;
- task-contract composer carries Authority & Context, Execution Freedom, Evidence Return and Write-back semantics;
- legacy pipeline shape remains compatible for existing callers;
- HTTP prototype, EDGAR-OS caller and STDIO MCP adapter remain operational in regression tests;
- GitHub Actions installs project dependencies and runs the complete unittest suite;
- the PR test suite currently runs 24 tests successfully.

This section describes verified PR behavior. Until PR #9 is merged and `master` CI is green, `master` remains the executable authority for released/current branch state.

## Non-goals

PromptOS / Prompt Forge v0.2 development work is not:

- a complete chat product;
- a multi-tenant identity/account platform;
- a prompt marketplace;
- a complex frontend;
- an autonomous production-change platform;
- a public production Prompt Forge service;
- a full long-running Agent Platform.

Local HTTP and STDIO MCP integrations exist, but public endpoint / authentication / hostname / production deployment are separate work.
