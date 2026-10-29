# Tokens in an agent loop

Read this after `tokens.md` in se-agent lite (what a token is, input vs. output, free-tier limits). This page is about what changes in a loop.

## Every step re-sends the whole conversation

A model remembers nothing between calls. So at each step the library sends:

1. the instructions and the tool descriptions,
2. the task,
3. **every earlier step**: each tool call the model made and each result that came back.

That means **input tokens grow with every step**, even if each tool result is small. `tests/test_agent.py` checks exactly this: each call sees a longer history than the one before.

```
Step 1:  instructions + task                                  →  small
Step 2:  ... + step 1's call and result                       →  bigger
Step 3:  ... + steps 1 and 2                                  →  bigger still
Step 4:  ... + steps 1, 2 and 3 (including the whole page!)   →  biggest
```

The page the agent wrote is sent back to the model each time it appears in history. A page is the largest thing in the conversation, so the steps after `write_file` are the expensive ones. If the agent has to fix the page, the second `write_file` adds another full copy.

## Lite vs. smol

| | lite | smol |
|---|---|---|
| Number of model calls | Fixed (3) | Decided by the model |
| Cost of a run | Predictable | Varies run to run |
| What grows | Earlier work we pass along, trimmed to `MAX_EARLIER` | The whole history, untrimmed by default |
| Brake | The loop ends after 3 prompts | `MAX_STEPS = 8` and `max_tokens` per reply |

A fixed pipeline lets you **budget** before you run. An agent lets you only **cap**: you can say "no more than 8 steps", but not exactly what it will use.

## Why the pause on the free tier

Each step's line shows `[N in + M out]`. Add up a minute's worth and compare it with the free tier's limit of about 8,000 tokens a minute (check Groq's rate-limits page, because limits change). Later steps send more, so they eat more of the minute. `PAUSE` (20 seconds on Groq) spaces the steps out, and the library also retries when the service says "slow down" (error 429).

## Ways to spend less

- Lower `MAX_STEPS`. Fewer loops means fewer re-sent histories.
- Keep tool results short. A tool that returns a whole file adds a lot of tokens.
- Keep the instructions short. They are re-sent at every step.
- Use a smaller or cheaper model for simple jobs.
- Use a **local** model (Ollama): no token bill, but you pay in speed and memory.

## Questions

1. Why is the last step usually the most expensive one?
2. What would happen to the total if the agent wrote the page three times?
3. How would you reduce what is re-sent? What could you lose by doing that?
4. If one step costs about 3,000 tokens and the free limit is 8,000 per minute, how long must we wait between steps?
5. Which is easier to predict the cost of, lite or smol? Why does that matter for a real project?
