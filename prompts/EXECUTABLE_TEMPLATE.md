# Executable Prompt Template

Composer fills these sections for every local run:

1. Context
2. Goal
3. Scope
4. Known Facts
5. Assumptions
6. Execution Task
7. Validation
8. Deliverables
9. Stop Conditions
10. Output Format

Optional when task/risk needs them:

- Continuation Policy
- Authority & Context
- Execution Freedom
- Evidence Return
- Write-back
- Branch / Worktree Isolation
- Rollback
- Forbidden Actions
- Context Freshness
- Constraints

`Continuation Policy` is emitted only for sustained tasks. It is orthogonal to execution mode and defines whether the executor stops after one bounded cut or continues through verified bounded cuts until the parent goal or a real gate is reached. See `docs/CONTINUATION-POLICY.md`.
