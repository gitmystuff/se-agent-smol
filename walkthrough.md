# se-agent smol: Walkthrough

A guided tour for class. Read it next to `smol_demo.py`. For the lite version, see the se-agent-lite repo.

## 1. The big idea

An **agent** is a program that lets a model decide what to do next. We give the model:

1. a **goal** ("build the app in the brief"),
2. a set of **tools** (small functions it may call), and
3. **instructions** (a structured prompt).

Then a loop runs: the model looks at everything so far, picks a tool, we run the tool, and we show the model the result. This repeats until the model calls `final_answer` or we stop it at `MAX_STEPS`.

## 2. Lite vs. smol: same job, different control

| | se-agent lite | se-agent smol |
|---|---|---|
| Who decides the order? | **We do**: `1_design`, `2_build`, `3_verify`, always | **The model does**, one step at a time |
| How many model calls? | Always 3 | Varies: 3 to 8 in a good run |
| Who checks the work? | A **model** reads its own code and says PASS or FAIL | A **function** (`check_page`) checks the page, and the model must react to the result |
| What the model can touch | Nothing but text | Only the three tools we gave it |
| Predictability | High | Lower: two runs may take different paths |
| Where the intelligence is | In the prompts | In the prompt **and** in how the model chooses tools |

Neither is "better". Lite is easier to predict, to test, and to budget. An agent can adapt: if `check_page` finds a problem, it can fix the page and check again, without us writing that logic.

## 3. The brief

`water-tracker.md` is the same brief as lite. The app tracks daily water intake (about 2000 ml is a common daily goal): you tap 250 ml for a glass, 500 ml for a bottle, or type an amount, and the page shows your total, percent, what remains, and a streak.

## 4. The tools (`smol_demo.py`, function `make_tools`)

| Tool | What it does | Why it is safe |
|---|---|---|
| `read_file(filename)` | Returns a file's text: the brief, or a page it saved | Read-only; the name is checked by `checks.safe_filename`, so no folders or `..` |
| `write_file(filename, content)` | Saves a file in the output folder | The name is checked by `checks.safe_filename`: no folders, no `..`, only `.html .css .js .md` |
| `check_page(filename)` | Runs `checks.check_html` on a saved page | Read-only |

Two things to notice:

- Each tool is a few lines. The `@tool` line and the docstring turn it into something the model can read and call. **The docstring is part of the prompt**: it is how the model learns what the tool does.
- A tool that refuses (for example `NOT SAVED: ...`) **returns a message** instead of crashing. The agent reads it and can try again.
- **Design tools the way models use them.** Our first version had a `read_brief()` tool with no arguments. In real runs the model kept calling it as `read_brief(filename=...)`, first with a file name and then with `null`, and the service rejected both. The fix was to offer `read_file(filename)`, which is what the model reaches for anyway. Fitting the interface to the user is an old software-engineering lesson, and here the "user" is a model.

## 5. The rules behind the tools (`checks.py`)

Plain Python with no AI. `check_html` looks for the mistakes we saw in real runs of a bigger version of this project:

- an empty `<body>` (a page that shows nothing),
- JavaScript modules (`import` / `export`), which browsers block when you double-click a file,
- loading outside files,
- no `localStorage`,
- a script that asks for an element id that does not exist.

> Ask: this check is much simpler than running the page. What could it miss? (Plenty: wrong math, a bad streak rule. It is a first filter, not a proof.)

## 6. The agent's instructions (`smol_prompts/agent.md`)

The same eight sections as every prompt in this course: Role, Context, Task, Requirements, Constraints, Process, Output Format, Verification. Notice the Constraints ("at most two `write_file` calls", "do not claim it works unless `check_page` said OK") and the Process (the steps we expect). **The model may ignore them.** That is the difference from lite: in lite the order is code, here it is a request.

## 7. The loop (`run` in `smol_demo.py`)

- `ToolCallingAgent(...)` builds the agent from the model, the tools, and the instructions. `max_steps` caps the loop.
- `agent.run("Build the app described in the brief.")` starts it.
- `after_step` prints one line per step, and sleeps on the free tier to respect the token limit.
- After the run we add up tokens from each step and save `trace.md`.

smolagents has two kinds of agent. `ToolCallingAgent` (used here) makes the model name a tool and its arguments. `CodeAgent` makes the model **write Python code** that calls the tools. Code agents can be more flexible, but running code a model wrote is a security risk, so you need a sandbox. We use the tool-calling kind to keep today's demo safe and simple.

## 8. Run it and read the trace

```
uv run python smol_demo.py water-tracker.md
```

A good run looks like this:

```
Step 1: read_file({'filename': 'water-tracker.md'})   [... in + ... out]
Step 2: write_file({'filename': 'index.html', ...})   [... in + ... out]
Step 3: check_page({'filename': 'index.html'})        [... in + ... out]
Step 4: final_answer({'answer': '...'})               [... in + ... out]
```

Open `output_smol/<timestamp>/trace.md`. Questions:

1. What did `check_page` say? Did the agent change anything after it?
2. Did the agent follow the Process in `agent.md`, or invent its own?
3. How many steps did it take? Compare with a neighbour.
4. Open `index.html` and try the app (250, 0, -5, 5000, reload). Does it work? Does the check agree with what you see?

## 8b. When the check says OK and the app is broken

A real run of this project passed `check_page` and still crashed on the first click. The page was reading data that an earlier page had saved in the browser, in a different shape. Two lessons:

- **A static check is a first filter, not proof.** `check_page` reads the page's text and never runs it. Only running the app, or testing its logic, finds this kind of bug (Chapter 8).
- **Saved data has a shape, and shapes change** (Chapter 9). Code that reads old data must not assume the shape. `agent.md` now tells the model to use its own storage key and to fill in missing fields with defaults.

If your page crashes, press F12, open the Console, type `localStorage.clear()`, and reload.

## 9. How we test an agent (`tests/`)

- **`test_checks.py`** tests the rules directly, like any function.
- **`test_agent.py`** runs the real loop with a **fake model** that follows a script ("call read_file, then write_file, ...") so we can test: the page is saved, a failed check leads to a fix, a path like `../evil.html` is refused, the step limit stops a loop, and the history grows each step.
- **`test_profiles.py`** tests how the model is chosen from `.env`.

The model's *judgement* is the one thing these tests cannot check. That is why a real run, and a human reading the result, still matter.

## 10. Discussion

1. When would you choose a fixed pipeline (lite) over an agent? When an agent?
2. The agent can only do what its tools allow. What is the worst thing `write_file` could do if we had not checked file names?
3. `check_page` is a function, not a model. Why might that be more trustworthy than a model saying PASS?
4. What would you add as a fourth tool? What new risks does it bring?
5. How would you know the agent is getting *worse* over time? (Think Chapter 9: evolution and regression tests.)
