# se-agent smol

**One job, done by an agent.** This is the sister project of se-agent lite. Lite runs a fixed pipeline (design, build, verify) that *we* control. Here a small **agent** gets the same brief and a few **tools**, and the **model decides** what to do next.

```
                  ┌────────────────────────── the agent loop ──────────────────────────┐
water-tracker.md →│ think → choose a tool → run it → read the result → think again ... │→ index.html
  (the brief)     └─────────────  read_file · write_file · check_page   ───────────────┘
```

It uses [smolagents](https://huggingface.co/docs/smolagents), a small open-source agent library from Hugging Face. The library runs the loop. We write the tools and the prompt.

## Run it

You need [uv](https://docs.astral.sh/uv/) and an API key (your Groq key from earlier works; it is free).

1. **Clone this repo and go into it.**
2. **Make your `.env`.** Copy `.env.example` to `.env` and put your key in it. (Or copy the `.env` from your earlier project and add the line `PROFILE=groq`.) It must be in the same folder as `smol_demo.py`.
3. **Install:** `uv sync`
4. **Run:**
   ```
   uv run python smol_demo.py water-tracker.md
   ```
   You will see one line per step: which tool the model chose and how many tokens it used. On Groq's free tier it pauses 20 seconds between steps.
5. **Open the app:** `output_smol/<timestamp>/index.html`. Also open `trace.md` in the same folder. It shows everything the agent did.

## Where the model lives (`PROFILE` in `.env`)

| PROFILE | Model runs on | Needs in `.env` |
|---|---|---|
| `groq` (default) | Groq, free tier | `GROQ_API_KEY` |
| `huggingface` | Hugging Face "Inference Providers" | `HF_TOKEN` (see `huggingface.md`) |
| `ollama` | your own computer | `SMOL_MODEL` only, no key. Install Ollama, pull a model with the **tools** label, and use the name from `ollama list`. See `local-models.md`. |
| `openai` | OpenAI, paid | `OPENAI_API_KEY` and `SMOL_MODEL` |
| `custom` | any service with an OpenAI-style API | `SMOL_API_BASE`, `SMOL_MODEL`, and `SMOL_API_KEY` |

`SMOL_MODEL` overrides the model name for any profile, and `SMOL_PAUSE` overrides the pause between steps (in seconds).

## Run the tests

```
uv run pytest
```

The tests use a **fake model** that follows a script, so they need no key and no internet.

## What is in here

| File | What it is |
|---|---|
| `smol_demo.py` | The agent: profiles, tools, the loop, saving the trace. |
| `checks.py` | The plain-Python rules the tools use (safe file names, page checks). |
| `smol_prompts/agent.md` | The agent's instructions, in the 8-section prompt format. |
| `water-tracker.md` | The brief. |
| `tests/` | Tests for the rules, the profiles, and the whole loop. |
| `walkthrough.md` | Step-by-step explanation for class, with lite vs smol. |
| `tokens.md` | Why an agent loop uses tokens the way it does. |
| `local-models.md` | An instructor demo and an optional lab for running a model locally with Ollama. |
| `worksheet-hosted-vs-local.md` | A worksheet comparing hosted and local models. |
| `huggingface.md` | A hands-on tour of Hugging Face: models, tokens, and running the agent through it. |

## Troubleshooting

| What you see | What to do |
|---|---|
| `Setup problem: No key found` | Check the name in `.env` (for example `GROQ_API_KEY=...`), no quotes, same folder as `smol_demo.py`. |
| `401` or "invalid API key" | The key is wrong or expired. |
| `429` or "rate limit" | Free-tier limit. Wait a minute and run again. Raise `SMOL_PAUSE` to slow down. |
| The agent stops with no `index.html` | It may have hit the 8-step limit. Open `trace.md` to see what it did. Run again; each run differs. |
| `index.html` loads but the buttons do nothing, or the console (F12) shows `Cannot read properties of undefined` | Old data from another page is in your browser's storage. Browsers share `localStorage` between pages opened from files. Open the page, press F12, type `localStorage.clear()` in the Console, and reload. |
| `index.html` was saved but is still broken | The model sometimes writes a broken page, and `check_page` only reads the page, it does not run it. Read `trace.md`, then run the agent again (each run differs) or compare with a neighbour. That is part of today's discussion. |
| Error about tools or tool calls | The model may not support tool calling. Try another model with `SMOL_MODEL`. |

**Never commit your `.env` file or post your key.** `.gitignore` keeps it out of git.

**Status note:** the loop, tools and profiles are tested with a fake model. Before class, run it once with a real model and check the output.
