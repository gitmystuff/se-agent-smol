# Running a model on your own computer (Ollama)

**Why this is here:** to show that *where the model runs* is an engineering decision. It is a short instructor demo plus an optional lab. Groq stays the default for everything students must run.

Hosted (Groq, OpenAI, Hugging Face) means someone else's computers run the model and you send them your text. Local means a program on your own machine runs it. **[Ollama](https://ollama.com)** is a free program that downloads models and runs them locally. It gives them the same kind of API as the hosted services, so our code does not change. Only `.env` does.

---

## Part 1: Instructor demo (10 to 15 minutes, on your machine)

**Before class**
1. Install Ollama from <https://ollama.com> and pull one small model that supports tools:
   ```
   ollama pull gpt-oss:20b
   ```
   (About a dozen GB. If your machine is small, pick a smaller model: on ollama.com/library, look for the **tools** label on the model page.)
2. Test it once. Run `ollama run <model>` and ask it a question. Then run the agent:
   ```
   PROFILE=ollama
   SMOL_MODEL=gpt-oss:20b
   ```
   in `.env`, then `uv run python smol_demo.py water-tracker.md`.
3. Note how long a run took, and whether the agent followed the tools.
4. Keep a saved `trace.md` from a Groq run to compare.

**In class**
1. **Say what you will show:** "Same agent, same brief, different place for the model."
2. **Run it live** (or play a saved run if it is slow). While it runs, run `ollama ps` in another window. It shows which model is loaded and whether it uses the GPU or the CPU.
3. **Compare, on the board:**

   | | Groq (hosted, free) | Ollama (local) |
   |---|---|---|
   | Time for the run | | |
   | Steps the agent took | | |
   | Did the page work? | | |
   | Token limit errors? | | |
   | Cost | | |
   | Where did the data go? | | |
4. **Ask the class** the three scenarios from the worksheet (`worksheet-hosted-vs-local.md`) and take a quick vote on each.

**Things to point out**
- No 429 errors, no pause between steps: the limits we designed around are gone. The limits now are memory and speed.
- It may be slower, and it may choose tools worse. If the agent failed, that is a good outcome for the lesson: **a smaller model is not the same as a bigger one**. Say so.
- **The context window.** The agent re-sends its whole history every step (see `tokens.md`). A local model has a maximum size it can read at once, and some setups use a small default and quietly cut the older text off, with no error. If a local run behaves strangely late in the loop, check the model's context setting in Ollama's docs (the setting is often called `num_ctx`).

---

## Part 2: Optional lab (for students with the hardware and curiosity)

**Check first:** 8 GB of memory is a bare minimum for a small model, and more is better. A GPU helps but is not required. If a student's computer is too small, they can work with a partner or skip it. **Nobody is graded on their hardware.**

1. Install Ollama (<https://ollama.com>).
2. **Pick a model.** On <https://ollama.com/library> or <https://huggingface.co/models>, read the model card and write down: its size, its license, whether it supports **tools**, and how much memory it needs.
3. **Download it:**
   ```
   ollama pull <model-name>
   ```
   Many models on Hugging Face can also be pulled with `ollama run hf.co/<user>/<repo>` if they are in GGUF format. Check Ollama's docs for the exact form.
4. **Make sure it is running:** `ollama list` shows what you have installed.
5. **Point the agent at it:** in `.env`,
   ```
   PROFILE=ollama
   SMOL_MODEL=<model-name>
   ```
6. **Run:** `uv run python smol_demo.py water-tracker.md`
7. **Record** in `worksheet-hosted-vs-local.md`, Part 1: the time, the steps, whether `index.html` worked, and what went wrong.

**If it fails:**

| What you see | What to do |
|---|---|
| Connection refused | Ollama is not running. Start the Ollama app, or run `ollama serve`. |
| Model not found | The name in `SMOL_MODEL` must match `ollama list` exactly. |
| Error about tools | The model may not support tool calling. Pick one with the **tools** label. |
| Very slow | It is running on the CPU. Try a smaller model. |
| Out of memory, or the computer freezes | The model is too big. Close other programs or choose a smaller one. |
| The agent loops or ignores the instructions | The model may be too small for agent work. Report that. It is a valid result. |

---

## Why bother? (the lesson, in three lines)

1. The model is a **component**. Our code treats it that way: one setting changes where it lives.
2. Every choice has a price: cost, speed, quality, privacy, effort to maintain.
3. Whoever runs the model, **you still have to test what it produces**.
