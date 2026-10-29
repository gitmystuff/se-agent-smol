# Hugging Face: a hands-on tour

Hugging Face is a website and a set of tools for sharing AI work. Think of it as **GitHub for AI models**: people publish models, datasets, and small demo apps there, and anyone can look at them. The library we use in this repo, smolagents, comes from Hugging Face.

You do **not** need a Hugging Face account to run this repo on Groq. You need one for Part C below.

## What lives on Hugging Face

| Part | What it is | Like |
|---|---|---|
| **Models** | Published AI models, each with a page | repositories |
| **Datasets** | Collections of data used to train or test models | data repositories |
| **Spaces** | Small running apps and demos | a live demo site |
| **Libraries** | Code such as `transformers` and `smolagents` | open-source packages |
| **Inference Providers** | A service that runs models for you and bills by use | an API |

## Part A: explore with no account (15 min)

1. Go to <https://huggingface.co/models>. Search for `gpt-oss`.
2. Open a model page and find its **model card**. Write down:
   - Who published it, and when was it last updated?
   - What **license** does it have? May you use it in a product?
   - How big is it (the number of **parameters**)? Could it run on your laptop?
   - What does the card say about **limitations** and intended use?
   - Is there an example of how to call it?
3. Compare two models of different sizes. What do you gain and lose?
4. Open **Datasets** and **Spaces**. Try one Space.

> Discussion: a model card is documentation. What would you want in one for your own project? (Think of the README and requirements work from earlier chapters.)

## Part B: where this fits in our course (10 min)

- **Choosing a model is a design decision** (Chapter 6 and 7): size, speed, cost, license, and where it runs are trade-offs, like choosing a database.
- **Versions and licenses are an evolution problem** (Chapter 9): a model can be updated or retired, and your app may change behavior when it does.
- **Open vs. closed models:** an open-weight model can be run on your own machine (Ollama). A closed one is reached only through its owner's API.
- **Model output still has to be tested** (Chapter 8), whoever hosts it.

## Part C: run our agent through Hugging Face (20 min)

1. Make a free account at <https://huggingface.co>.
2. Open **Settings → Access Tokens** and create a **fine-grained** token. Give it the permission **"Make calls to Inference Providers"** and nothing else.
3. Put it in your `.env`, in the same folder as `smol_demo.py`:
   ```
   PROFILE=huggingface
   HF_TOKEN=hf_paste-your-token-here
   ```
4. Run it:
   ```
   uv run python smol_demo.py water-tracker.md
   ```
5. Open `output_smol/<timestamp>/trace.md` and `index.html`.

How it works: the code sends the same kind of request to `https://router.huggingface.co/v1` as it sends to Groq. Hugging Face then forwards it to a company that runs the model. You can steer that choice by adding a suffix to the model name in `SMOL_MODEL`:

| Model name | Meaning |
|---|---|
| `openai/gpt-oss-120b` or `...:fastest` | the fastest provider (default) |
| `openai/gpt-oss-120b:cheapest` | the lowest price per output token |
| `openai/gpt-oss-120b:groq` | one named provider |

> **Cost:** Inference Providers is pay-as-you-go. Hugging Face's docs say PRO and Team accounts get monthly included credits and do not state an allowance for free accounts. Check <https://huggingface.co/docs/inference-providers/pricing> and your account's billing page before class, and watch your usage. **Groq stays the free route.**

Compare with your Groq run. It is the same model name. What is different (speed, tokens, the steps the agent took)? Why might two runs of the same model differ?

## Part D (optional): run a model locally

Many models on the Hub can be downloaded and run on your own computer. See `local-models.md` for a demo and a lab, and `worksheet-hosted-vs-local.md` for the comparison.

## Safety

- A token is like a password. **Never** paste it into a Space, a notebook you share, a public repo, or a screenshot. `.gitignore` already keeps `.env` out of git.
- Give a token the fewest permissions it needs. That is why we used a fine-grained one.
- If a token leaks, delete it in Settings and make a new one.

## Questions

1. Which model would you pick for a class project, and what would you check first on its model card?
2. What are the pros and cons of running a model on your own computer vs. through a service?
3. A model you depend on is retired next year. What would you have done earlier to make switching easy? (Hint: look at how `PROFILE` works in this repo.)
4. Why is it a good design that `smol_demo.py` can switch providers by changing `.env` and not the code?
