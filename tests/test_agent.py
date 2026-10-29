"""
Test the whole agent loop with a FAKE model that follows a script.
No key, no network, no tokens spent. The fake model says which tool to call at each
step; the real smolagents loop and our real tools run underneath it.
"""
import pytest
from smolagents import Model
from smolagents.models import ChatMessage, ChatMessageToolCall, ChatMessageToolCallFunction
from smolagents.monitoring import TokenUsage

import smol_demo

PAGE = """<!DOCTYPE html><html><body><h1>Water</h1><button id="b">+250</button>
<span id="total">0</span>
<script>const k=localStorage.getItem('x');
document.getElementById('b').onclick=()=>{document.getElementById('total').textContent=1};
</script></body></html>"""
BAD_PAGE = "<html><body></body></html>"


def call(name, **arguments):
    return ChatMessage(
        role="assistant", content="",
        tool_calls=[ChatMessageToolCall(id=f"c-{name}", type="function",
                                        function=ChatMessageToolCallFunction(name=name, arguments=arguments))],
        token_usage=TokenUsage(input_tokens=100, output_tokens=20),
    )


class ScriptedModel(Model):
    """Replies with the next scripted tool call each time it is asked."""
    def __init__(self, script):
        super().__init__(model_id="scripted")
        self.script, self.seen = list(script), []

    def generate(self, messages, stop_sequences=None, response_format=None, tools_to_call_from=None, **kwargs):
        self.seen.append(len(messages))
        return self.script.pop(0)


BRIEF = "Build a tiny water tracker."


def happy_script():
    return [call("read_file", filename="brief.md"),
            call("write_file", filename="index.html", content=PAGE),
            call("check_page", filename="index.html"),
            call("final_answer", answer="Built it. check_page said OK.")]


def test_the_loop_runs_tools_and_saves_the_page(tmp_path):
    model = ScriptedModel(happy_script())
    answer, steps, tin, tout = smol_demo.run(BRIEF, model, tmp_path)
    assert (tmp_path / "index.html").read_text(encoding="utf-8") == PAGE
    assert "check_page said OK" in answer
    assert [c.name for s in steps for c in s.tool_calls] == ["read_file", "write_file", "check_page", "final_answer"]

def test_tokens_are_added_up(tmp_path):
    _, steps, tin, tout = smol_demo.run(BRIEF, ScriptedModel(happy_script()), tmp_path)
    assert (tin, tout) == (100 * len(steps), 20 * len(steps))

def test_each_step_sees_a_longer_history(tmp_path):
    model = ScriptedModel(happy_script())
    smol_demo.run(BRIEF, model, tmp_path)
    assert model.seen == sorted(model.seen) and len(set(model.seen)) == len(model.seen)

def test_the_agent_can_fix_a_page_after_a_failed_check(tmp_path):
    script = [call("read_file", filename="brief.md"),
              call("write_file", filename="index.html", content=BAD_PAGE),
              call("check_page", filename="index.html"),
              call("write_file", filename="index.html", content=PAGE),
              call("check_page", filename="index.html"),
              call("final_answer", answer="Fixed it.")]
    smol_demo.run(BRIEF, ScriptedModel(script), tmp_path)
    assert (tmp_path / "index.html").read_text(encoding="utf-8") == PAGE

def test_the_check_tool_reports_problems_to_the_agent(tmp_path):
    script = [call("write_file", filename="index.html", content=BAD_PAGE),
              call("check_page", filename="index.html"),
              call("final_answer", answer="done")]
    _, steps, _, _ = smol_demo.run(BRIEF, ScriptedModel(script), tmp_path)
    assert "PROBLEMS FOUND" in steps[1].observations

def test_a_path_escape_is_refused_and_nothing_is_written(tmp_path):
    out = tmp_path / "out"
    script = [call("write_file", filename="../evil.html", content="x"),
              call("final_answer", answer="done")]
    _, steps, _, _ = smol_demo.run(BRIEF, ScriptedModel(script), out)
    assert "NOT SAVED" in steps[0].observations
    assert not (tmp_path / "evil.html").exists()

def test_checking_a_file_that_was_never_saved(tmp_path):
    script = [call("check_page", filename="index.html"), call("final_answer", answer="done")]
    _, steps, _, _ = smol_demo.run(BRIEF, ScriptedModel(script), tmp_path)
    assert "has not been saved yet" in steps[0].observations

def test_the_step_limit_stops_a_looping_agent(tmp_path):
    script = [call("read_file", filename="brief.md") for _ in range(10)] + [ChatMessage(role="assistant", content="gave up")]
    answer, steps, _, _ = smol_demo.run(BRIEF, ScriptedModel(script), tmp_path, max_steps=3)
    assert len([s for s in steps if s.tool_calls]) <= 3

def test_the_trace_file_lists_every_step(tmp_path):
    answer, steps, tin, tout = smol_demo.run(BRIEF, ScriptedModel(happy_script()), tmp_path)
    text = smol_demo.trace_text(answer, steps, tin, tout)
    for name in ("read_file", "write_file", "check_page", "final_answer"):
        assert name in text
    assert "Total tokens" in text

def test_the_pause_is_used_between_steps(tmp_path, monkeypatch):
    waits = []
    monkeypatch.setattr(smol_demo.time, "sleep", lambda s: waits.append(s))
    smol_demo.run(BRIEF, ScriptedModel(happy_script()), tmp_path, pause=7)
    assert waits and set(waits) == {7}


# ---- things a real model does that a tidy script does not ---------------------------------
def text(message):
    """A reply with NO tool call, the way a real model sometimes answers."""
    return ChatMessage(role="assistant", content=message,
                       token_usage=TokenUsage(input_tokens=100, output_tokens=5))


def test_a_plain_text_reply_does_not_kill_the_run(tmp_path):
    script = [call("read_file", filename="brief.md"),
              call("write_file", filename="index.html", content=PAGE),
              call("check_page", filename="index.html"),
              text("All done! The page is ready."),           # forgot to call a tool
              call("final_answer", answer="Built it.")]
    answer, steps, _, _ = smol_demo.run(BRIEF, ScriptedModel(script), tmp_path)
    assert answer == "Built it."
    assert any(s.error for s in steps)                         # the slip was recorded, not hidden

def test_a_service_failure_saves_what_was_done(tmp_path):
    class Breaks(ScriptedModel):
        def generate(self, messages, **kw):
            if len(self.script) == 1:
                raise RuntimeError("Error code: 400 - Tool choice is required, but model did not call a tool")
            return super().generate(messages, **kw)
    script = [call("read_file", filename="brief.md"), call("write_file", filename="index.html", content=PAGE),
              call("check_page", filename="index.html")]
    # the next call (no scripted replies left but one) raises
    model = Breaks(script + [call("final_answer", answer="never reached")])
    answer, steps, tin, tout = smol_demo.run(BRIEF, model, tmp_path)
    assert answer.startswith("STOPPED EARLY")
    assert (tmp_path / "index.html").exists()                  # the work so far survived
    assert "STOPPED EARLY" in smol_demo.trace_text(answer, steps, tin, tout)


# ---- the model asks for tools politely, not by force ------------------------------------
class _Capture:
    """Stands in for the OpenAI client and records what it was asked."""
    def __init__(self):
        self.kwargs = None
        outer = self
        class Completions:
            def create(self, **kw):
                outer.kwargs = kw
                msg = type("M", (), {"role": "assistant", "content": "hi", "tool_calls": None})
                use = type("U", (), {"prompt_tokens": 1, "completion_tokens": 1})
                return type("R", (), {"choices": [type("C", (), {"message": msg})], "usage": use})()
        self.chat = type("Chat", (), {"completions": Completions()})()


def _model():
    m = smol_demo.make_model({"model": "m", "api_base": "http://x/v1", "api_key": "k"})
    m.client = _Capture()
    return m


def test_tools_are_offered_with_tool_choice_auto(tmp_path):
    m = _model()
    tools = smol_demo.make_tools(BRIEF, tmp_path)
    m.generate([{"role": "user", "content": "hi"}], tools_to_call_from=tools)
    assert m.client.kwargs["tool_choice"] == "auto" and m.client.kwargs["tools"]

def test_no_tool_choice_is_sent_when_there_are_no_tools():
    m = _model()
    m.generate([{"role": "user", "content": "hi"}])
    assert "tool_choice" not in m.client.kwargs


def test_read_file_returns_the_brief_by_its_name(tmp_path):
    script = [call("read_file", filename="brief.md"), call("final_answer", answer="ok")]
    _, steps, _, _ = smol_demo.run(BRIEF, ScriptedModel(script), tmp_path)
    assert steps[0].observations.strip() == BRIEF and not steps[0].error

def test_read_file_uses_the_real_brief_name(tmp_path):
    script = [call("read_file", filename="water-tracker.md"), call("final_answer", answer="ok")]
    _, steps, _, _ = smol_demo.run(BRIEF, ScriptedModel(script), tmp_path, brief_name="water-tracker.md")
    assert steps[0].observations.strip() == BRIEF

def test_read_file_can_read_back_a_saved_page(tmp_path):
    script = [call("write_file", filename="index.html", content=PAGE),
              call("read_file", filename="index.html"), call("final_answer", answer="ok")]
    _, steps, _, _ = smol_demo.run(BRIEF, ScriptedModel(script), tmp_path)
    assert steps[1].observations.strip() == PAGE.strip()

def test_read_file_lists_what_exists_when_a_name_is_wrong(tmp_path):
    script = [call("read_file", filename="nope.html"), call("final_answer", answer="ok")]
    _, steps, _, _ = smol_demo.run(BRIEF, ScriptedModel(script), tmp_path)
    assert "NOT FOUND" in steps[0].observations and "brief.md" in steps[0].observations

def test_read_file_refuses_paths_outside_the_folder(tmp_path):
    (tmp_path / "secret.md").write_text("TOP-SECRET-CONTENTS")
    out = tmp_path / "out"
    script = [call("read_file", filename="../secret.md"), call("final_answer", answer="ok")]
    _, steps, _, _ = smol_demo.run(BRIEF, ScriptedModel(script), out)
    assert "NOT READ" in steps[0].observations and "TOP-SECRET-CONTENTS" not in steps[0].observations

def test_an_unknown_argument_on_another_tool_is_a_recoverable_step_error(tmp_path):
    script = [call("check_page", file="index.html"),            # wrong argument name
              call("final_answer", answer="ok")]
    answer, steps, _, _ = smol_demo.run(BRIEF, ScriptedModel(script), tmp_path)
    assert answer == "ok" and steps[0].error


# ---- the service rejects a malformed tool call: retry, don't die (seen in a real run) --------
from types import SimpleNamespace
from openai import BadRequestError


def _bad_request(text):
    """A 400 error like the one the service sends, built without any HTTP library."""
    response = SimpleNamespace(request=SimpleNamespace(), status_code=400, headers={})
    return BadRequestError(text, response=response, body=None)


class _Flaky(_Capture):
    """Fails the first `failures` calls with a 400, then answers."""
    def __init__(self, failures, text):
        super().__init__()
        self.calls, self.failures, self.text = 0, failures, text
        outer, real = self, self.chat.completions.create
        class Completions:
            def create(self, **kw):
                outer.calls += 1
                if outer.calls <= outer.failures:
                    raise _bad_request(outer.text)
                return real(**kw)
        self.chat = type("Chat", (), {"completions": Completions()})()


VALIDATION = "Error code: 400 - Tool call validation failed: parameters for tool read_file did not match schema"


def _flaky_model(failures, text=VALIDATION):
    m = smol_demo.make_model({"model": "m", "api_base": "http://x/v1", "api_key": "k"})
    m.client = _Flaky(failures, text)
    m.retryer = lambda fn, *a, **k: fn(*a, **k)         # no waiting in tests
    return m


def test_a_rejected_tool_call_is_retried_and_then_works(tmp_path):
    m = _flaky_model(failures=2)
    tools = smol_demo.make_tools(BRIEF, tmp_path)
    reply = m.generate([{"role": "user", "content": "hi"}], tools_to_call_from=tools)
    assert reply.content == "hi" and m.client.calls == 3

def test_retries_stop_after_the_limit(tmp_path):
    m = _flaky_model(failures=99)
    tools = smol_demo.make_tools(BRIEF, tmp_path)
    with pytest.raises(BadRequestError):
        m.generate([{"role": "user", "content": "hi"}], tools_to_call_from=tools)
    assert m.client.calls == smol_demo.ForgivingModel.RETRIES + 1

def test_other_bad_requests_are_not_retried(tmp_path):
    m = _flaky_model(failures=99, text="Error code: 400 - invalid api key format")
    with pytest.raises(BadRequestError):
        m.generate([{"role": "user", "content": "hi"}], tools_to_call_from=smol_demo.make_tools(BRIEF, tmp_path))
    assert m.client.calls == 1

def test_the_tool_choice_required_error_is_also_retried(tmp_path):
    m = _flaky_model(failures=1, text="Error code: 400 - Tool choice is required, but model did not call a tool")
    reply = m.generate([{"role": "user", "content": "hi"}], tools_to_call_from=smol_demo.make_tools(BRIEF, tmp_path))
    assert reply.content == "hi" and m.client.calls == 2
