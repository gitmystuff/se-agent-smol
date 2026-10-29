# From se-agent-lite to se-agent-smol to a local model

Software Engineering

**One-sentence version:** last week we turned a one-page brief into a working app with three prompts (lite). Today we try the same job with an *agent* that chooses its own steps (smol), and we finish by running a model on our own computers with Ollama.

---

## Part 0: 

**Say:**

> "Here is today's plan. First a quick look back at last week's se-agent lite and why we built it. Then we get a new project from GitHub, se-agent-smol, and talk about why it is different. **We will finish by running an AI model on a local computer using Ollama.** If you want to follow along on your own computer, install Ollama now, while we talk. It is optional. You can also just watch."

> “Smol” is internet slang for “small”. It’s a playful, deliberately misspelled version of the word, in the same spirit as “doggo” for a dog. The word is popular in online communities and memes, often with a cute or affectionate tone.

### Optional: install Ollama

Works on Windows and Mac. Get it from **<https://ollama.com/download>** and check that page for the supported versions.

**Windows**
1. Download the Windows installer from ollama.com/download.
2. Run the installer and follow the prompts.
3. Ollama starts in the background (look for its icon near the clock).
4. Open a **new** Command Prompt or PowerShell window and type:
   ```
   ollama --version
   ```
   A version number means it worked.

**Mac**
1. Download the Mac version from ollama.com/download.
2. Open the download and move **Ollama** into your **Applications** folder.
3. Open Ollama once. A small icon appears in the menu bar, and it keeps running in the background.
4. Open **Terminal** and type:
   ```
   ollama --version
   ```
   A version number means it worked.

**Then download a model (later, in Part 3)**, because models are several GB and you may be on slow internet. Only start the download if you have the disk space and a decent connection.

**Before you install:**
- Models take several GB of disk. A small one is about 5 GB, and larger ones are 12 GB or more.
- Memory matters: 8 GB is a bare minimum for a small model, and more is better. A GPU helps but is not required.
- If your computer is too small, **that is fine**. Watch the demo and join a partner who has it running. Nobody is graded on their hardware.

---

## Part 1: What we did last week, and why 

### The goal
Take a one-page description of an app (a **brief**) and have an AI turn it into working software using the same pipeline Sommerville describes in Chapters 5 to 8: model, design, implement, test.

### What we built: se-agent lite
Three prompts, run in order by a program of about 100 lines, `lite.py`:

| Step | Prompt | Job | Output |
|---|---|---|---|
| 1 | `1_design.md` | Plan the app | Requirements, pieces, input rules, test cases |
| 2 | `2_build.md` | Write the code | One `index.html` |
| 3 | `3_verify.md` | Check the code | A PASS/FAIL table and a list of bugs |

**The app:** a water tracker. People are often told to drink about 2 litres (2000 ml) of water a day. You tap a button for a glass (250 ml) or a bottle (500 ml), or type an amount, and the page shows your total, percent, what remains, and a streak of days you hit the goal. The app is not the point. It is small, has clear rules, and is easy to test.

### Walk through the code (scroll `lite.py`, one sentence per block)
- **Settings:** which model, how long to pause between steps, how much earlier work to pass along.
- **`ask()`:** the only place we talk to the model. Send text, get text. It retries when the free tier says "slow down" (error 429), and it prints the token counts.
- **`run()`:** a loop. For each prompt file: put the brief in, add the earlier work, ask, remember the answer. **This one loop is the pipeline.**
- **`save()`:** writes each result to a file and pulls the web page out of the build step's reply.

### Show a prompt (`2_build.md`)
The same eight sections we have used all semester: Role, Context, Task, Requirements, Constraints, Process, Output Format, Verification. Point at **Constraints**: "If we don't say this, the model chooses for us."

### Tokens (use the real numbers)
| Step | In | Out | Total |
|---|---:|---:|---:|
| 1 design | 540 | 1,400 | 1,940 |
| 2 build | 1,450 | 1,687 | 3,137 |
| 3 verify | 2,307 | 2,551 | 4,858 |
| **Run** | **4,297** | **5,638** | **9,935** |

- A token is a word piece, about 4 characters of plain English. **Input and output both count.**
- Input grows at each step because each step is sent the earlier work.
- The free tier allows about 8,000 tokens a minute (check Groq's page, because limits change). One run is about 9,900, which is why `lite.py` pauses 40 seconds between steps.

### What the results taught us
- **Two runs of the same prompts gave two different designs.** AI output is not repeatable.
- **The verifier said PASS, but the pages had bugs** (decimals accepted, a streak rule that doesn't update when you hit the goal, a date built from a UTC timestamp). A model checking a model's own work is not enough.
- **A bigger version failed.** The full router never produced a working one-page app. It spent its steps on component-level prompts and ran out. That is a real example of a system not meeting its goal.

### Why we did it (say this out loud)
1. **Software engineering is a pipeline,** and a pipeline can be run by prompts.
2. **A prompt is a specification.** Better specification, better software.
3. **Limits are engineering constraints:** tokens, rate limits, cost.
4. **AI output must be tested.** Writing the code got easier. Checking it did not.

---

## Part 2: Clone se-agent-smol, and why we are trying it 

### Clone it 
```
git clone <your-repo-url>/se-agent-smol
cd se-agent-smol
```
Copy your `.env` from the earlier project into this folder (same folder as `smol_demo.py`). It needs `GROQ_API_KEY=...`. Then:
```
uv sync
uv run pytest
```
Expect all tests to pass. The tests use a fake model, so they need no key.

> Students can follow along. If cloning is slow, keep going while it finishes.

### The question: "What if the model decided what to do next?"

| | se-agent lite | se-agent smol |
|---|---|---|
| Who decides the order? | **We do:** design, build, verify | **The model does**, one step at a time |
| Number of model calls | Always 3 | Varies (about 4 in a good run) |
| Who checks the work? | A **model** says PASS or FAIL | A **function** (`check_page`) checks, and the model reacts |
| What the model can touch | Only text | Only the three tools we give it |
| Cost | Predictable | Varies; only capped |

Neither is better. A fixed pipeline is predictable. An agent can adapt: if a check fails, it can fix and re-check without us writing that logic.

### Show the pieces (`smol_demo.py`)
- **Tools** are small functions: `read_file`, `write_file`, `check_page`. The `@tool` line and the docstring make each one something the model can read and call. **The docstring is part of the prompt.**
- **`checks.py`** holds the rules as plain Python, so we can unit-test them.
- **`smol_prompts/agent.md`** is the agent's instructions, in the same eight-section format.
- **The loop:** the model picks a tool, we run it, we show the result, the model picks again, until `final_answer` or the 8-step limit. smolagents (from Hugging Face) runs the loop.

### Run it 
```
uv run python smol_demo.py water-tracker.md
```
A good run prints one line per step: `read_file`, `write_file`, `check_page`, `final_answer`, with token counts. Open `trace.md` and `index.html` afterward.

### Real failures we hit while building it (tell these stories)
Each one is a real lesson, and all of them happened last night:

1. **The model answered in plain text instead of calling a tool.** The library demanded a tool call and the service returned an error, which killed the run. *Fix:* let the model reply in plain text, correct it and continue; and save what we have if it still fails. **An agent must handle a model that doesn't follow instructions.**
2. **The model kept passing a file name to a tool that took none.** Then it sent `null`, and the service rejected that too. *Fix:* we stopped fighting it and offered `read_file(filename)`, which is what it reaches for anyway. **Design the interface for the user, and here the user is a model.**
3. **The check said "OK" and the app was broken.** `check_page` reads the page's text but never runs it. The page crashed because it read data left by an earlier page in the browser's storage, in a different shape. *Fix:* the page now uses its own storage key and fills in missing fields. **A static check is a first filter, not proof (Chapter 8). Saved data has a shape, and shapes change (Chapter 9).**

Quick fix to show if a student's page misbehaves: press F12, Console, type `localStorage.clear()`, reload.

### Why smol? (the point of this part)
1. **To compare two designs for the same job** and see the trade-offs: predictable vs. flexible, a model checking vs. a function checking.
2. **To meet agents,** a major pattern in current AI tools. Many tools you will use are loops like this one.
3. **To practice judging a system:** where did it fail, why, and what would catch it?
4. **The model is a part we can swap.** One setting in `.env` changes where it runs. That leads to the next part.

> Ask: "When would you use a fixed pipeline? When an agent? What would you add as a fourth tool, and what new risk does it bring?"

---

## Part 3: Ollama, discuss and demo 

### Discuss 
**Hosted** (Groq, OpenAI, Hugging Face): someone else's computers run the model, and you send them your text. **Local** (Ollama): a program on your own computer runs it.

| | Hosted | Local |
|---|---|---|
| Cost | Free tier or pay per token | No token bill (your electricity and time) |
| Limits | Rate limits, token caps | Your memory and speed |
| Privacy | Your text goes to another company | Stays on your computer |
| Quality | Large, strong models | Smaller models; weaker at long instructions and tools |
| Speed | Fast | Slower, especially without a GPU |
| Setup | An API key | Install and download several GB |
| Works offline | No | Yes |

**Say:** "Choosing where the model runs is an engineering decision, like choosing a database. It is a trade-off, not a right answer."

**Ollama** is a free program that downloads models and runs them locally. It gives them the same kind of API as the hosted services, so **our code does not change. Only `.env` does.** Many models on Hugging Face can be run this way too.

### Demo (8 min)
1. **Show what is installed:**
   ```
   ollama list
   ```
2. **Pull a model if you haven't (do this before class):**
   ```
   ollama pull <model-name>
   ```
   Choose a model with the **tools** label on its page at <https://ollama.com/library>. Without tool support, the agent will fail. Pick one that fits your memory: a model around 7B to 8B parameters is about 5 GB, and larger ones need much more.
3. **Point the agent at it.** In `.env`:
   ```
   PROFILE=ollama
   SMOL_MODEL=<the exact name shown by ollama list>
   ```
4. **Run it:**
   ```
   uv run python smol_demo.py water-tracker.md
   ```
5. **While it runs,** open another window and type `ollama ps`. It shows which model is loaded and whether it uses the GPU or CPU.
6. **Compare on the board:**

   | | Groq (hosted, free) | Ollama (local) |
   |---|---|---|
   | Time for the run | | |
   | Steps the agent took | | |
   | Did the page work? | | |
   | Rate-limit pauses? | | |
   | Cost | | |
   | Where did the text go? | | |

**Point out:**
- No pauses and no 429 errors. The limits we designed around are gone, and the limits are now memory and speed.
- It may be slower, and it may pick tools worse. **If it fails, that is a good result.** A smaller model is not the same as a bigger one.
- **The context window:** the agent re-sends its whole history every step (see `tokens.md`). A local model has a maximum it can read at once, and some setups quietly cut off older text. If a local run behaves oddly late in the loop, check the model's context setting in Ollama's docs.

### Quick vote 
Hosted, local or either?
1. A student project, on a laptop with a free account.
2. A company's private codebase, and the contract forbids sending code to outside companies.
3. A public app with 100,000 users a day.

(Full version: `worksheet-hosted-vs-local.md`.)

### If the demo fails
- Show the saved Groq trace and the saved Ollama result from before class, and say "this is a real run from earlier".
- Or turn the failure into the lesson: read the error, and ask the class what went wrong and what would fix it.

---

## Part 4: Wrap-up 

**Three things to remember**
1. **The model is a component.** Where it runs, and who decides what it does next, are design choices with trade-offs.
2. **Writing code got easier. Checking it did not.** Every failure we saw today was caught by a person looking, not by the AI saying "OK".
3. **Limits are real:** tokens, rate limits, memory, cost. Engineers plan for them.

**What to do next (optional)**
- Run `se-agent-smol` on your own computer and read `trace.md`.
- Try the Ollama lab in `local-models.md` if your computer can run a model.
- Fill in `worksheet-hosted-vs-local.md`.
- Write your own one-page brief and run it through lite or smol.

**Preview:** next we bring these ideas together in the full se-agent, with a cost estimate and a choice of free, paid, or local.

