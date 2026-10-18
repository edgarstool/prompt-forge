# Bounded Codebase Routing Canary (EDG2-73)

**Scope:** optional developer/test entrypoint; this does not change Hermes gateway's default client-disconnect policy. Do not call this a fleet-wide fix.

## Zero-token default

```bash
PYTHONPATH=src python3 -m prompt_forge.hermes_bounded --request "改 EDGAR 控制中心"
```

For every route the default command returns the deterministic provisional classification without starting an LLM or connecting to Hermes. For AMBIGUOUS/UNKNOWN/REVIEW_REQUIRED/BLOCKED, `route_before_agent` stops before optional Agent execution as well. Exact repo identity or a single CANDIDATE is still **not** live canonical ownership.

## Explicit live Agent test with bounded deadline

Run with the Python environment that **already has Hermes installed** and has access to the existing live Hermes Gateway. Do not start a second gateway or restart production merely for this test.

```bash
PYTHONPATH=/path/to/prompt-forge/src /path/to/hermes-python -m prompt_forge.hermes_bounded \
  --request "修 Hermes 的 LINE approval 卡片" --agent-canary --timeout 3
```

The helper creates **one fresh session**, toolsets `prompt-forge`, sends one read-only routing request, waits at most the specified time for the turn, then if needed fetches the **same session's** current generation and issues Hermes's standard `session.interrupt` RPC. It never parses another session ID from log text or uses the host-wide process killer. Existing sessions and services are unaffected.

* `COMPLETED`: the session completed within the deadline.
* `INTERRUPT_REQUESTED`: Hermes accepted the RPC without raising. **Not proof that the turn stopped.** Read back `Turn ended` or the authoritative session admission state to verify.
* `INTERRUPT_UNVERIFIED`: cancellation RPC failed, generation was missing, or owner was unavailable. Check that session explicitly; do not report stopped.
* `CANARY_UNVERIFIED`: connection/setup unavailable, no silent fallback.
* `STOPPED_PRE_MODEL`: no Agent invocation occurred; 0 model calls.

Use an **outer process deadline longer than the helper deadline**. A SIGTERM that kills the wrapper first will bypass its cleanup, because arbitrary Hermes terminal detach does not currently cancel accepted server-side work. That is a separate upstream gateway-client behavior to address before global rollout.

## Acceptance evidence (OVH1, 2026-10-18 Asia/Taipei)

- TDD RED: missing `prompt_forge.hermes_bounded` caused test import failure.
- Isolated checkout unit suite 8/8 PASS after implementation.
- `改 EDGAR 控制中心` and `修 LINE bot` -> `STOPPED_PRE_MODEL`, multiple candidate repos, 0 model calls.
- OVH1 live existing gateway canary 20:35:58: `INTERRUPT_REQUESTED` for exact newly created session `local-8c804ca1c64f10e4abeaba81c737254d107e5da2953114304aa321b9b65b5fa6` after timeout=3.
- OVH1 Hermes `agent.log` 20:36:04: `Turn ended: reason=interrupted_by_user ... api_calls=0`. **Scoped cancel effect verified for this canary only.**
- No Hermes production source hot-patch, gateway restart, or owner-wide session interruption.

See [GitHub Control Map](https://docs.google.com/document/d/1vAG_WIvoRAIV5uYe7WlLmMcgiqlAy3VwytUPAMG6yDE/edit) and [YouTrack EDG2-73](https://edgars.youtrack.cloud/issue/EDG2-73).
