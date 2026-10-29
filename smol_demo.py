"""
se-agent smol -- the same job as se-agent lite, done by an AGENT instead of a fixed pipeline.

  se-agent lite:  WE decide the order: design, then build, then verify.
  se-agent smol:  the MODEL decides what to do next, one step at a time,
                  by choosing from the tools we hand it. This repeating
                  "think, act, look at the result" cycle is called the agent loop.

The tools (read_file, write_file, check_page) are small plain functions.
The library (smolagents, from Hugging Face) runs the loop for us.

Usage:   uv run python smol_demo.py water-tracker.md
Needs:   a .env file with a key for your PROFILE (see README.md)
"""
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from openai import BadRequestError
from smolagents import OpenAIServerModel, ToolCallingAgent, tool
from smolagents.memory import ActionStep
from smolagents.monitoring import LogLevel
from smolagents.utils import AgentError

import checks

HERE = Path(__file__).parent
PROMPT_FILE = HERE / "smol_prompts" / "agent.md"
OUTPUT = HERE / "output_smol"
MAX_STEPS = 8          # the agent may not loop forever
MAX_REPLY_TOKENS = 3000

# Where the model lives. All of these speak the same "OpenAI-style" API,
# so one model class (OpenAIServerModel) covers every one of them.
PROFILES = {
    "groq":   {"api_base": "https://api.groq.com/openai/v1", "key_env": "GROQ_API_KEY",
               "model": "openai/gpt-oss-120b", "pause": 20},     # free, but 8,000 tokens/minute
    "ollama": {"api_base": "http://localhost:11434/v1", "key_env": None,
               "model": "gpt-oss:20b", "pause": 0},               # on your own computer
    "huggingface": {"api_base": "https://router.huggingface.co/v1", "key_env": "HF_TOKEN",
               "model": "openai/gpt-oss-120b", "pause": 10},      # Hugging Face "Inference Providers"
    "openai": {"api_base": None, "key_env": "OPENAI_API_KEY",
               "model": None, "pause": 0},                        # paid: set SMOL_MODEL
    "custom": {"api_base": None, "key_env": None,
               "model": None, "pause": 0},                        # any OpenAI-style service
}


class SetupError(Exception):
    """Something is missing from the setup. The message says what to do."""


def get_profile(env=None):
    """Read PROFILE (and the optional overrides) from the environment."""
    env = os.environ if env is None else env
    name = env.get("PROFILE", "groq").strip().lower()
    if name not in PROFILES:
        raise SetupError(f"PROFILE='{name}' is not one of: {', '.join(PROFILES)}.")
    p = dict(PROFILES[name], name=name)
    if name == "custom":
        p["api_base"] = env.get("SMOL_API_BASE")
        p["key_env"] = env.get("SMOL_API_KEY_ENV", "SMOL_API_KEY")
        if not p["api_base"]:
            raise SetupError("PROFILE=custom needs SMOL_API_BASE in your .env.")
    p["model"] = env.get("SMOL_MODEL") or p["model"]
    if not p["model"]:
        raise SetupError(f"PROFILE={name} needs SMOL_MODEL (the model name) in your .env.")
    if p["pause"] is not None and env.get("SMOL_PAUSE"):
        p["pause"] = int(env["SMOL_PAUSE"])
    p["api_key"] = env.get(p["key_env"]) if p["key_env"] else "not-needed"
    if not p["api_key"]:
        raise SetupError(f"No key found. Put {p['key_env']}=... in your .env file "
                         f"(same folder as smol_demo.py).")
    return p


def _is_bad_tool_call(error):
    """True if a 400 error means 'the model's tool call was malformed', which is worth retrying."""
    text = str(error).lower()
    return "tool call validation failed" in text or "tool choice is required" in text or "failed to call a function" in text


class ForgivingModel(OpenAIServerModel):
    """An OpenAI-style model that lets the agent recover when the model forgets to call a tool.

    By default smolagents tells the service "you MUST call a tool". Some services (Groq among
    them) then answer a plain-text reply with a hard error (400), and the whole run dies.
    With tool_choice="auto" a plain-text reply comes back normally; smolagents notes that
    no tool was called, tells the model so, and the loop continues.
    """
    RETRIES = 2

    def generate(self, messages, stop_sequences=None, response_format=None,
                 tools_to_call_from=None, **kwargs):
        if tools_to_call_from:                      # tool_choice only makes sense with tools
            kwargs.setdefault("tool_choice", "auto")
        for attempt in range(self.RETRIES + 1):
            try:
                return super().generate(messages, stop_sequences=stop_sequences,
                                        response_format=response_format,
                                        tools_to_call_from=tools_to_call_from, **kwargs)
            except BadRequestError as problem:
                # The service rejected the model's tool call (for example a wrong argument).
                # Models are not exact, so asking again often works.
                if not _is_bad_tool_call(problem) or attempt == self.RETRIES:
                    raise
                print(f"  [retry] the service rejected the model's tool call; asking again "
                      f"({attempt + 1} of {self.RETRIES}).")


def make_model(profile):
    return ForgivingModel(
        model_id=profile["model"], api_base=profile["api_base"], api_key=profile["api_key"],
        client_kwargs={"max_retries": 5},           # the service may say "slow down"; retry
        max_tokens=MAX_REPLY_TOKENS,
    )


def make_tools(brief_text, out_dir, brief_name="brief.md"):
    """The three tools the agent may use. Each is a small, testable function.

    Tool design tip: models call tools the way they are used to. A model asked to read a brief
    reaches for read_file(filename), so that is the tool we offer."""
    out_dir = Path(out_dir)

    @tool
    def read_file(filename: str) -> str:
        """Reads a text file and returns its contents. You can read the project brief (its file
        name is given in the task) and any file you saved with write_file.

        Args:
            filename: The name of the file to read, such as the brief's file name or index.html.
        """
        name = filename.strip() if isinstance(filename, str) else ""
        if name == brief_name:
            return brief_text
        try:
            name = checks.safe_filename(name)
        except ValueError as problem:
            return f"NOT READ: {problem}"
        path = out_dir / name
        if not path.is_file():
            saved = sorted(p.name for p in out_dir.glob("*") if p.is_file()) if out_dir.is_dir() else []
            return f"NOT FOUND: {name}. Files you can read: {', '.join([brief_name] + saved)}."
        return path.read_text(encoding="utf-8")

    @tool
    def write_file(filename: str, content: str) -> str:
        """Saves a file into the output folder, replacing any older file with the same name.

        Args:
            filename: A plain file name such as index.html (no folders).
            content: The complete text of the file.
        """
        try:
            name = checks.safe_filename(filename)
        except ValueError as problem:
            return f"NOT SAVED: {problem}"
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / name).write_text(content, encoding="utf-8")
        return f"Saved {name} ({len(content):,} characters)."

    @tool
    def check_page(filename: str) -> str:
        """Runs a quick static check on a saved web page and lists any problems found.

        Args:
            filename: The name of a file already saved with write_file, such as index.html.
        """
        try:
            name = checks.safe_filename(filename)
        except ValueError as problem:
            return f"NOT CHECKED: {problem}"
        path = out_dir / name
        if not path.is_file():
            return f"NOT CHECKED: {name} has not been saved yet. Call write_file first."
        return checks.describe_problems(checks.check_html(path.read_text(encoding="utf-8")))

    return [read_file, write_file, check_page]


def _short(value, limit=70):
    text = str(value).replace("\n", " ")
    return text if len(text) <= limit else text[:limit] + "..."


def step_line(step):
    """One readable line for a finished step."""
    calls = ", ".join(f"{c.name}({_short(c.arguments)})" for c in (step.tool_calls or [])) or "(no tool call)"
    usage = step.token_usage
    tokens = (f"  [{usage.input_tokens:,} in + {usage.output_tokens:,} out]" if usage else "")
    note = f"  ERROR: {_short(step.error)}" if step.error else ""
    return f"Step {step.step_number}: {calls}{tokens}{note}"


def run(brief_text, model, out_dir, pause=0, max_steps=MAX_STEPS, brief_name="brief.md"):
    """Run the agent. Returns (final_answer, steps, tokens_in, tokens_out)."""
    def after_step(step, agent=None):
        print(step_line(step))
        if pause and not step.is_final_answer:
            time.sleep(pause)               # stay under the free tier's tokens-per-minute limit

    agent = ToolCallingAgent(
        tools=make_tools(brief_text, out_dir, brief_name),
        model=model,
        instructions=PROMPT_FILE.read_text(encoding="utf-8"),
        max_steps=max_steps,
        verbosity_level=LogLevel.ERROR,
        step_callbacks={ActionStep: [after_step]},
    )
    try:
        answer = agent.run(f"Build the app described in the brief. The brief is the file {brief_name}: "
                           f"read it with read_file first.")
    except AgentError as problem:                   # the model service failed mid-run
        answer = f"STOPPED EARLY: {_short(problem, 300)}"
        print(f"\n{answer}\nSaving what the agent did so far.")
    steps = [s for s in agent.memory.steps if isinstance(s, ActionStep)]
    tokens_in = sum(s.token_usage.input_tokens for s in steps if s.token_usage)
    tokens_out = sum(s.token_usage.output_tokens for s in steps if s.token_usage)
    return str(answer), steps, tokens_in, tokens_out


def trace_text(answer, steps, tokens_in, tokens_out):
    """A readable record of the whole loop, saved as trace.md."""
    lines = ["# What the agent did", ""]
    for s in steps:
        lines.append(f"## Step {s.step_number}")
        lines.append(f"- Action: {', '.join(f'{c.name}({_short(c.arguments, 200)})' for c in (s.tool_calls or [])) or 'none'}")
        if s.observations:
            lines.append(f"- Result: {_short(s.observations, 400)}")
        if s.error:
            lines.append(f"- Error: {_short(s.error, 300)}")
        if s.token_usage:
            lines.append(f"- Tokens: {s.token_usage.input_tokens:,} in + {s.token_usage.output_tokens:,} out")
        lines.append("")
    lines += ["## Final answer", answer, "",
              f"Total tokens: {tokens_in:,} in + {tokens_out:,} out = {tokens_in + tokens_out:,}"]
    return "\n".join(lines)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        sys.exit("Usage: uv run python smol_demo.py <brief-file>")
    load_dotenv()
    try:
        profile = get_profile()
    except SetupError as problem:
        sys.exit(f"Setup problem: {problem}")
    brief = Path(argv[0]).read_text(encoding="utf-8").strip()
    out_dir = OUTPUT / time.strftime("%Y%m%d-%H%M%S")
    print(f"Profile: {profile['name']}   Model: {profile['model']}   Max steps: {MAX_STEPS}\n")
    answer, steps, tin, tout = run(brief, make_model(profile), out_dir, pause=profile["pause"],
                                 brief_name=Path(argv[0]).name)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "trace.md").write_text(trace_text(answer, steps, tin, tout), encoding="utf-8")
    print(f"\nAgent says: {answer}")
    print(f"Total tokens: {tin:,} in + {tout:,} out = {tin + tout:,}")
    print(f"\nSaved to {out_dir}")
    if (out_dir / "index.html").exists():
        print(f"Open in your browser: {out_dir / 'index.html'}")


if __name__ == "__main__":
    main()
