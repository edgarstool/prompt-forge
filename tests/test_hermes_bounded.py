"""EDG2-73: no-LLM ambiguous guard and scoped deadline interrupt contract."""
import asyncio
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from prompt_forge.hermes_bounded import route_before_agent, run_bounded_view


class FakeView:
    def __init__(self, *, delay=0, session_id="fresh-one", admission="ad-1", result=0):
        self.session_id = session_id
        self.finite_admission = admission
        self.generation = 3
        self.delay = delay
        self.result = result
        self.started = False

    async def run(self, prompt, *, oneshot=False):
        self.started = True
        await asyncio.sleep(self.delay)
        return self.result


class FakeClient:
    def __init__(self, *, refuse_interrupt=False, snapshot=None):
        self.calls = []
        self.refuse_interrupt = refuse_interrupt
        self.snapshot = snapshot or {"execution_generation": 3}

    async def rpc(self, method, **kwargs):
        self.calls.append((method, kwargs))
        if method == "session.resume":
            return self.snapshot
        if method == "session.interrupt":
            if self.refuse_interrupt:
                raise RuntimeError("owner rejected interrupt")
            return {"accepted": True}
        raise AssertionError(method)


class BoundedCanaryTests(unittest.IsolatedAsyncioTestCase):
    async def test_ambiguous_route_stops_before_model(self):
        calls = []
        async def never():
            calls.append("model")
        outcome = await route_before_agent("改 EDGAR 控制中心", never)
        self.assertEqual(outcome["status"], "STOPPED_PRE_MODEL")
        self.assertEqual(outcome["route"]["status"], "AMBIGUOUS")
        self.assertFalse(calls)

    async def test_forbidden_route_stops_before_model(self):
        async def should_not_be_called():
            self.fail("model must not be reached")
        outcome = await route_before_agent("安裝 Ollama 本地模型", should_not_be_called)
        self.assertEqual(outcome["status"], "STOPPED_PRE_MODEL")
        self.assertEqual(outcome["route"]["status"], "BLOCKED")

    async def test_candidate_enters_only_opted_in_canary(self):
        calls = []
        async def run_agent():
            calls.append("run")
            return {"status": "AGENT_FINISHED"}
        outcome = await route_before_agent("修 Hermes 的 LINE approval 卡片", run_agent)
        self.assertEqual(outcome["status"], "AGENT_FINISHED")
        self.assertEqual(calls, ["run"])

    async def test_deadline_requests_interrupt_for_own_session_only(self):
        view = FakeView(delay=1)
        client = FakeClient()
        result = await run_bounded_view(view, client, "verify", timeout_seconds=0.01)
        self.assertTrue(view.started)
        self.assertEqual(result["status"], "INTERRUPT_REQUESTED")
        self.assertEqual(result["session_id"], "fresh-one")
        self.assertEqual([method for method, _ in client.calls], ["session.resume", "session.interrupt"])
        method, params = client.calls[-1]
        self.assertEqual(params["session_id"], "fresh-one")
        self.assertEqual(params["execution_generation"], 3)

    async def test_completed_fast_run_does_not_interrupt(self):
        view = FakeView(delay=0)
        client = FakeClient()
        result = await run_bounded_view(view, client, "verify", timeout_seconds=0.5)
        self.assertEqual(result["status"], "COMPLETED")
        self.assertEqual(result["exit_code"], 0)
        self.assertFalse(client.calls)

    async def test_no_admission_refuses_guess_and_does_not_interrupt(self):
        view = FakeView(delay=1, admission=None)
        client = FakeClient()
        result = await run_bounded_view(view, client, "verify", timeout_seconds=0.01)
        self.assertEqual(result["status"], "ADMISSION_UNKNOWN")
        self.assertFalse(client.calls)

    async def test_refused_interrupt_cannot_be_called_cancelled(self):
        view = FakeView(delay=1)
        client = FakeClient(refuse_interrupt=True)
        result = await run_bounded_view(view, client, "verify", timeout_seconds=0.01)
        self.assertEqual(result["status"], "INTERRUPT_UNVERIFIED")

    async def test_missing_generation_refuses_interrupt(self):
        view = FakeView(delay=1)
        client = FakeClient(snapshot={})
        result = await run_bounded_view(view, client, "verify", timeout_seconds=0.01)
        self.assertEqual(result["status"], "INTERRUPT_UNVERIFIED")
        self.assertEqual([method for method, _ in client.calls], ["session.resume"])


if __name__ == "__main__":
    unittest.main()
