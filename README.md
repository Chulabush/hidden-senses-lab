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

### Route A: chat subscriptions (no API keys) — `lab.cli.toml`

This drives `claude` and `codex` with existing subscription logins. Gemini uses the manual
Chat Bridge below and is never launched as a CLI. This route needs only Python 3.11+ and the tools; skip the `pip`
step above. Install the tools once (needs a recent Node.js) and log in to each:

```bash
npm install -g @anthropic-ai/claude-code @openai/codex
```

Check both workers, then run a first small batch:

```bash
python -m lab --config lab.cli.toml doctor --ping
```
```bash
python -m lab --config lab.cli.toml run --seats 6
```

On Windows, use `py` in place of `python`. To leave a lab out of a run (for example while its usage
limit resets), name the ones you want:

```bash
python -m lab --config lab.cli.toml --labs claude,codex run --seats 6
```

To aim a run at part of the agenda, filter by keyword (comma-separated, any one may match; the texts
are in `lab/agenda.py`). `--seats` then counts within the matching seats:

```bash
python -m lab --config lab.cli.toml run --seats 6 --sense "songbirds,fruit flies,monarch" --portal "axion,dark photons" --role quantum
```

No model is named in the commands, so each tool uses your subscription's default model. With a single
lab, it reviews and scores its own hypotheses from two opposed stances (experimentalist and theorist).
Gemini participates through the Chat Bridge, using its web or mobile app.

**Bringing in another assistant by hand.** Print a ready-to-paste prompt for a seat (or `0` for the
research programme), paste it into any chat window, then save the answer:

```bash
python -m lab --config lab.cli.toml consult 322
```
```bash
python -m lab --config lab.cli.toml consult 322 --from chatgpt --file reply.txt
```

Their review joins the seat's conversation, and their score counts toward the seat's ranking.

What to expect on this route:

- **Speed:** a seat is 6 model calls and takes a few minutes. Plan on tens of seats per day, not thousands.
- **Usage limits:** a limited worker cools down until its reported reset time (five minutes if absent).
  The remaining worker takes all debate roles. Completed seats persist if both workers are unavailable.
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

## Scout matrix and cloud runs

### Gemini Chat Bridge

```powershell
py -m lab --config lab.cli.toml gemini-export --top 10
# Paste runs/gemini_brief.md into Gemini Chat; request the JSON format in the packet.
py -m lab --config lab.cli.toml gemini-import clipboard
# Or: py -m lab --config lab.cli.toml gemini-import runs/gemini_reply.json
py -m lab --config lab.cli.toml run --seats 6
```

Imports preserve the architectural synthesis and queue new hypotheses ahead of agenda seats.
Identical packets are deduplicated. Invalid JSON changes nothing; copy the returned JSON
object (optionally fenced) rather than surrounding commentary. No Gemini API key or CLI is used.
Windows clipboard reading uses the native API and works with embedded Python.
Other platforms require tkinter for clipboard reading; file imports work everywhere.

The Windows rebuild includes a local Python runtime at `.runtime/python/python.exe` if
`py` is unavailable. Use that path in place of `py` in the examples. The runtime and
database/backup are local ignored artifacts. `[runner]` and `[labs.*]` configure the CLI
route; the older `[run]` and `[providers.*]` configuration remains supported.

The scout matrix has 1,248 combinations (26 visual systems × 4 loops × 12 amplifiers),
with 1,000 selected by default. Workers are asynchronous tasks, not independent OS agents.
CLI process concurrency never exceeds `[runner].cli_processes`, even with more scout tasks.

Use Python 3.11 or newer. The subscription route uses the installed `claude`, `codex`,
executables only. Sign into both CLIs and check them with
`py -m lab --config lab.cli.toml doctor --ping` on Windows. Missing CLIs are skipped.
The roundtable screens each premise before proposing, critiquing, revising, and scoring it.
A rate-limited provider stays out of rotation until the reported reset time (five minutes
if the CLI omits one). With a single provider, that provider fills each role.

```powershell
py -m lab --config lab.cli.toml scout --count 1000 --concurrency 2 --promote-top 3
py -m lab --config lab.cli.toml status
```

The scout saves one result per visual system, coupling class, and amplifier combination.
`--count` selects up to that many unscored combinations. Repeat the command to continue.
Use `--count 0 --promote-top N` to promote saved candidates without scouting again.
The status command ranks completed seats by their normalized judge scores and uses the
lowest recorded gap to break ties. A gap can be conditional on the judge's stated
source benchmark. Compare those assumptions before interpreting gaps across seats.

On an Ubuntu 24.04+ VM, `bash deploy/ubuntu_setup.sh` installs dependencies and starts
a detached tmux session with a 25-worker scout. Authenticate the tools under the VM's
user account. If you use `deploy/push_auth_to_cloud.ps1`, run it only against a trusted
VM account because it copies CLI directories that can include credentials and session
history. Some credentials can require a fresh login on the VM. Restart the tmux session
if the initial run paused before authentication. Stop local lab writers before using
`deploy/pull_results.ps1`, which snapshots the cloud database, backs up any local
database, imports the snapshot, then runs status and synthesis.
