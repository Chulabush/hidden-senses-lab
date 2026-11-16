"""The conversation between labs: propose -> critique -> revise -> score, then a joint synthesis."""
import asyncio
import json
import re

SYSTEM = """You are one researcher in a three-lab collaboration (Claude, ChatGPT and Gemini) working on an open question: \
could some animals sense parts of reality that humans and today's instruments miss, in particular a dark sector \
(dark matter and whatever forces it may carry)?

Imagination leads here. Never dismiss an idea for being unconventional. Your job is to carry it far enough that a \
sensor or a dataset could confirm it or rule it out. Be specific: name the particle or field and its coupling, the \
tissue or receptor, orders of magnitude, the dataset or instrument. Say plainly which parts are established and which \
are conjecture. No filler, no praise, no restating the brief."""

MAX_FAILURE_STREAK = 5
SCORE_KEYS = ["novelty", "testability", "mechanism", "survives_known_data"]


class BudgetExhausted(Exception):
    pass


class Budget:
    def __init__(self, max_calls: int, max_output_tokens: int):
        self.max_calls, self.max_out = max_calls, max_output_tokens
        self.calls = self.out = 0

    def take(self) -> None:
        if self.calls >= self.max_calls or self.out >= self.max_out:
            raise BudgetExhausted
        self.calls += 1


def brief(seat) -> str:
    return f"Animal sense: {seat.sense}\nPossible link to the unseen: {seat.portal}\nYour discipline: {seat.role}"


def parse_scores(text: str) -> dict | None:
    # A review may contain other braces (LaTeX such as \text{...}), so try each flat {...} block, last first.
    for block in reversed(re.findall(r"\{[^{}]*\}", text)):
        try:
            data = json.loads(block)
            scores = {k: max(1, min(10, int(data[k]))) for k in SCORE_KEYS}
        except (ValueError, KeyError, TypeError):
            continue
        scores["one_line"] = str(data.get("one_line", ""))[:300]
        return scores
    return None


async def ask(store, budget, provider, seat_id, step, prompt) -> str:
    budget.take()
    reply = await provider.complete(SYSTEM, prompt, step.split(":")[0])
    budget.out += reply.out_tokens
    store.add_message(seat_id, step, provider.name, reply)
    return reply.text


# With a single lab connected, it reviews its own work from two opposed stances.
SOLO_REVIEWERS = [
    ("experimentalist", "Review as a bench experimentalist who has to build the apparatus and beat the noise."),
    ("theorist", "Review as a theorist who checks every coupling, estimate and existing bound."),
]


def reviewers(providers, proposer) -> list[tuple]:
    """(provider, label, stance) for each reviewer of a seat."""
    others = [p for p in providers if p is not proposer]
    if others:
        return [(p, p.name, "") for p in others]
    return [(proposer, label, stance + " ") for label, stance in SOLO_REVIEWERS]


def rescore(store, seat_id: int) -> None:
    """Seat score = mean over every verdict on record (judges plus any outside consults)."""
    parsed = [s for m in store.transcript(seat_id) if m["step"].startswith(("judge:", "consult:"))
              if (s := parse_scores(m["content"]))]
    if not parsed:
        store.finish_seat(seat_id, "done", None, "no parseable scores")
        return
    score = sum(sum(s[k] for k in SCORE_KEYS) for s in parsed) / (len(parsed) * len(SCORE_KEYS))
    store.finish_seat(seat_id, "done", round(score, 2), " | ".join(s["one_line"] for s in parsed))


REVIEW_ASK = """Review it to make it stronger, not to veto it. Give: (1) the weakest link in the chain from mechanism \
to measurement, with numbers if you can; (2) the ordinary explanations a test must exclude; (3) one concrete change \
that makes it more detectable or easier to test. Under 250 words."""

SCORE_ASK = """Score it from 1 to 10 on each axis and reply with JSON only:
{"novelty": n, "testability": n, "mechanism": n, "survives_known_data": n, "one_line": "why, in one sentence"}
novelty = new idea rather than a restatement; testability = a real experiment or dataset could decide it; \
mechanism = every step of the chain is spelled out; survives_known_data = existing measurements do not already \
exclude it."""


def consult_prompt(store, seat_id: int) -> str:
    """A self-contained prompt to paste into another assistant's chat window."""
    if seat_id == 0:
        programme = store.message(0, "synthesis:final") or store.message(0, "synthesis:draft")
        if not programme:
            raise SystemExit("No research programme yet. Run `synthesize` first.")
        return (f"{SYSTEM}\n\n---\n\nA colleague drafted this research programme from the collaboration's best "
                f"hypotheses. Say what is missing, what is ranked wrongly and why, and which experiment you would "
                f"add. Under 400 words.\n\n{programme}")
    seat = store.seat(seat_id)
    final = store.message(seat_id, "revise")
    if not seat or not final:
        raise SystemExit(f"Seat {seat_id} has no finished hypothesis yet.")
    head = f"Animal sense: {seat['sense']}\nPossible link to the unseen: {seat['portal']}\nDiscipline: {seat['role']}"
    return (f"{SYSTEM}\n\n---\n\n{head}\n\nFinal hypothesis from {seat['proposer']}:\n\n{final}\n\n{REVIEW_ASK}\n\n"
            f"Finally: {SCORE_ASK.replace('reply with JSON only', 'end with this JSON on its own line')}")


async def work_seat(seat, providers, store, budget) -> None:
    proposer = providers[seat.id % len(providers)]
    critics = reviewers(providers, proposer)
    store.start_seat(seat, proposer.name)

    hypothesis = await ask(store, budget, proposer, seat.id, "propose", f"""{brief(seat)}

Propose ONE hypothesis for how this sense could register this part of reality. Use these headings:
Claim / Mechanism (step by step, from the unseen thing to a nerve signal or behaviour) / Size of the effect \
(order of magnitude, and the noise it must beat) / What we would observe / How to test it with data that exists or \
a sensor that can be built / What result would count against it.
Under 450 words.""")

    critiques = await asyncio.gather(*(
        ask(store, budget, c, seat.id, f"critique:{label}", f"""{brief(seat)}

A colleague at {proposer.name} proposed:

{hypothesis}

{stance}{REVIEW_ASK}""")
        for c, label, stance in critics))

    notes = "\n\n".join(f"Review from {label}:\n{t}" for (_, label, _), t in zip(critics, critiques))
    await ask(store, budget, proposer, seat.id, "revise", f"""{brief(seat)}

Your hypothesis:

{hypothesis}

{notes}

Rewrite the hypothesis using the same headings, taking the reviews into account. Keep what survived, fix or drop what \
did not, and end with the single cheapest first experiment. Under 500 words.""")
    revised = store.message(seat.id, "revise")

    await asyncio.gather(*(
        ask(store, budget, c, seat.id, f"judge:{label}", f"""{brief(seat)}

Final hypothesis from {proposer.name}:

{revised}

{stance}{SCORE_ASK}""")
        for c, label, stance in critics))
    rescore(store, seat.id)


async def run(seats, providers, store, budget, concurrency: int, log=print) -> dict:
    queue: asyncio.Queue = asyncio.Queue()
    for seat in seats:
        queue.put_nowait(seat)
    stats = {"done": 0, "failed": 0, "stopped": False, "streak": 0}

    async def worker():
        while not stats["stopped"]:
            try:
                seat = queue.get_nowait()
            except asyncio.QueueEmpty:
                return
            try:
                await work_seat(seat, providers, store, budget)
                stats["done"] += 1
                stats["streak"] = 0
                if stats["done"] % 25 == 0:
                    log(f"  {stats['done']} seats done, {budget.calls} calls, {budget.out:,} output tokens")
            except BudgetExhausted:
                store.finish_seat(seat.id, "pending")
                stats["stopped"] = True
            except Exception as e:  # one bad seat must not end a long run; it is recorded and retried next run
                store.finish_seat(seat.id, "failed", error=f"{type(e).__name__}: {e}")
                stats["failed"] += 1
                log(f"  seat {seat.id} failed: {type(e).__name__}: {e}")
                stats["streak"] += 1
                if stats["streak"] >= MAX_FAILURE_STREAK:  # usually a rate limit or a logged-out CLI
                    stats["stopped"] = True

    await asyncio.gather(*(worker() for _ in range(concurrency)))
    return stats


async def synthesize(providers, lead_name, store, budget, top_k: int) -> str:
    rows = store.top(top_k)
    if not rows:
        raise SystemExit("No scored hypotheses yet. Run `python -m lab run` first.")
    lead = next((p for p in providers if p.name == lead_name), providers[0])
    others = [p for p in providers if p is not lead]
    store.clear_synthesis()
    digest = "\n\n".join(
        f"### Seat {r['id']} (score {r['score']}, proposed by {r['proposer']})\n{r['sense']}\n{r['portal']}\n\n"
        f"{store.message(r['id'], 'revise')}" for r in rows)

    draft = await ask(store, budget, lead, 0, "synthesis:draft", f"""Below are the {len(rows)} highest-scoring hypotheses \
from the collaboration. Write the research programme they add up to:
1. The 3-5 recurring mechanisms, each with the seats that support it.
2. A ranked list of the 10 experiments worth doing first: what to measure, with which animal, sensor or public dataset, \
what result would be a discovery, and rough cost (free data / bench-top / lab-scale / facility-scale).
3. The one sensor prototype a single person could start building now, and what it could and could not see.
4. Open questions the next round of agents should take on.

{digest}""")
    if not others:
        return draft
    reviews = await asyncio.gather(*(
        ask(store, budget, p, 0, f"synthesis:review:{p.name}", f"""{lead.name} drafted this research programme from the \
collaboration's best hypotheses. Say what is missing, what is ranked wrongly and why, and which experiment you would \
add. Under 400 words.

{draft}""") for p in others))
    notes = "\n\n".join(f"Review from {p.name}:\n{t}" for p, t in zip(others, reviews))
    return await ask(store, budget, lead, 0, "synthesis:final", f"""Your draft programme:

{draft}

{notes}

Produce the final programme, incorporating the reviews. Same four sections.""")
