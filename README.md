# Hidden Senses Lab

AI models working as one research group (Claude, with ChatGPT and Gemini as reviewers or full labs) on a single question: could some animals
sense parts of reality that humans and current instruments miss, and could that include a dark sector
(dark matter and its possible forces)?

## How the labs talk to each other

The agenda is a grid of **2,496 agent seats**: 26 animal senses × 12 ways the unseen could touch ordinary
matter × 8 scientific disciplines (`lab/agenda.py`). Each seat is one conversation:

1. **Propose** – one lab writes a hypothesis (the proposer rotates across labs seat by seat).
2. **Critique** – the other labs review it, to strengthen it rather than veto it.
3. **Revise** – the proposer rewrites it using the reviews.
4. **Score** – the reviewers score novelty, testability, mechanism and consistency with existing data.

Then `synthesize` has the lead lab turn the best hypotheses into a research programme, which the other
labs review before it is finalised. Every message is stored in SQLite (`runs/lab.sqlite`), so you can
read any conversation in full. Reports worth keeping are copied to `results/`.

## Setup

```bash
python3 -m venv .venv
```
```bash
.venv/bin/pip install -r requirements.txt
```

There are two ways to connect the three models. Both write to the same database, so you can start with
one and continue with the other.

### Route A: Claude subscription (no API keys) — `lab.cli.toml`

This drives Claude's command-line tool, logged in with your Claude subscription. Install it once
(needs a recent Node.js; checked with Node 22) and log in on the machine that will run the lab:

```bash
npm install -g @anthropic-ai/claude-code
```
```bash
claude
```

Then check it and run a first small batch:

```bash
.venv/bin/python -m lab --config lab.cli.toml doctor --ping
```
```bash
.venv/bin/python -m lab --config lab.cli.toml run --seats 6
```

With Claude as the only lab, it reviews and scores its own hypotheses from two opposed stances
(experimentalist and theorist). The command names no model, so it uses your subscription's default.

**Bringing in ChatGPT and Gemini by hand.** Print a ready-to-paste prompt for a seat (or `0` for the
research programme), paste it into a ChatGPT or Gemini chat, then save the answer:

```bash
.venv/bin/python -m lab --config lab.cli.toml consult 322
```
```bash
.venv/bin/python -m lab --config lab.cli.toml consult 322 --from chatgpt --file reply.txt
```

Their review joins the seat's conversation, and their score counts toward the seat's ranking. To make
ChatGPT and Gemini full automatic labs instead, uncomment their blocks in `lab.cli.toml` and log in to
`codex` and `gemini` (`npm install -g @openai/codex @google/gemini-cli`); those two are untested.

What to expect on this route:

- **Speed:** a seat is 6 model calls and takes a few minutes. Plan on tens of seats per day, not thousands.
- **Usage limits:** subscriptions cap usage. When a tool starts failing, the run stops after 5 failures in a
  row; finished seats are kept and you continue later with the same command.
- **Memory:** one tool call peaks at roughly 250 MB. `cli_processes` in `lab.cli.toml` caps how many run at
  once (default 2, so about 0.5 GB). Set it to 1 on a very small machine.

### Route B: API keys — `lab.toml`

```bash
cp .env.example .env
```

Put pay-as-you-go API keys from each vendor's developer console in `.env`. A chat subscription does not
include them. This is the route that scales to the whole agenda.

## Use

| Command | What it does |
|---|---|
| `python -m lab doctor` | Checks each key and lists the models it can use (`--ping` sends one tiny request) |
| `python -m lab plan --seats 300` | Shows how many calls a run would make |
| `python -m lab run --seats 30` | Works 30 seats; rerun with a larger number to continue |
| `python -m lab status` | Progress, token usage, current leaders |
| `python -m lab show 2222` | Full conversation for one seat |
| `python -m lab synthesize --top 30` | Writes `runs/report.md` |
| `python -m lab consult 2222` | Prints a prompt to paste into another chat assistant; `--from NAME` saves its answer |

The table uses the API-key config. For the subscription route put `--config lab.cli.toml` right after
`lab`, as in the examples above. Add `--mock` to `run`, `status`, `show` or `synthesize` to exercise
everything offline at no cost.

Spending is capped per run by `max_calls` and `max_output_tokens` in `lab.toml`. A run that hits the cap
stops cleanly and resumes next time. Model IDs are set per lab in `lab.toml`.
