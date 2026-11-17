"""The conversation between labs: propose -> critique -> revise -> score, then a joint synthesis."""
import asyncio
import json
import re

from .providers import ProviderError
from .router import ROLES, SwarmRouter

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


def parse_scores(text: str, *, legacy=False) -> dict | None:
    # A review may contain other braces (LaTeX such as \text{...}), so try each flat {...} block, last first.
    for block in reversed(re.findall(r"\{[^{}]*\}", text)):
        try:
            data = json.loads(block)
            gap = data.get("gap_orders")
            category = data.get("loophole_class")
            model = data.get("judge_model")
            if not legacy or any(v is not None for v in (gap, category, model)):
                if (type(gap) is not int or not -(2**63) <= gap < 2**63
                        or category not in LOOPS or not isinstance(model, str) or not model.strip()):
                    continue
            scores = {k: max(1, min(10, int(data[k]))) for k in SCORE_KEYS}
        except (ValueError, KeyError, TypeError):
            continue
        scores.update(gap_orders=gap, loophole_class=category, judge_model=model)
        scores["one_line"] = str(data.get("one_line", ""))[:300]
        return scores
    return None


async def ask(store, budget, provider, seat_id, step, prompt, *, record=True) -> str:
    budget.take()
    reply = await provider.complete(SYSTEM, prompt, step.split(":")[0])
    budget.out += reply.out_tokens
    if record:
        store.add_message(seat_id, step, provider.name, reply)
    return reply.text


LOOPS = {
    "A": "Mirror or atomic dark matter and kinetic mixing with specialized photoreceptors.",
    "B": "Ultralight axion wave spin resonance and cryptochrome radical pairs.",
    "C": "Coherent bosonic wave phase interference in densely packed retinal arrays.",
    "D": "Macroscopic dark nuggets or topological defects generating transient ocular photons.",
}


async def routed_ask(store, budget, providers, router, preferred, seat_id, step, prompt, avoid=(), *, record=True):
    ordered = sorted(providers, key=lambda p: (p.name in avoid, p is not preferred))
    for provider in ordered:
        if not router.active(provider):
            continue
        role = ROLES.get(provider.name, "Interdisciplinary researcher.")
        try:
            text = await ask(store, budget, provider, seat_id, step, f"Your specialty: {role}\n\n{prompt}", record=record)
            return text, provider
        except (ProviderError, OSError) as exc:
            router.failed(provider, exc)
    raise ProviderError("No provider active. Check doctor --ping or retry after the logged cooldown.")


def rescore(store, seat_id: int) -> None:
    verdicts = []
    for row in store.transcript(seat_id):
        if not row["step"].startswith(("judge:", "consult:")):
            continue
        scores = parse_scores(row["content"], legacy=True)
        if scores:
            # API adapters know the exact serving model; subscription CLIs may only identify the tool.
            if not row["model"].endswith(" CLI") or not scores["judge_model"]:
                scores["judge_model"] = row["model"]
            verdicts.append((row["id"], row["provider"], scores))
    store.save_verdicts(seat_id, verdicts, SCORE_KEYS)


REVIEW_ASK = """Review it to make it stronger, not to veto it. Give: (1) the weakest link in the chain from mechanism \
to measurement, with numbers if you can; (2) the ordinary explanations a test must exclude; (3) one concrete change \
that makes it more detectable or easier to test. Under 250 words."""

SCORE_ASK = """Score it from 1 to 10 on each axis and reply with JSON only:
{"novelty": n, "testability": n, "mechanism": n, "survives_known_data": n, "gap_orders": integer, "loophole_class": "A|B|C|D",\n "judge_model": "your model", "one_line": "why, in one sentence"}
novelty = new idea rather than a restatement; testability = a real experiment or dataset could decide it; \
mechanism = every step of the chain is spelled out; survives_known_data = existing measurements do not already \
exclude it. Score the quantitative candidate, not the polish of a rejection. Compute gap_orders as rounded
log10(biological threshold / predicted signal) using comparable units and explain the numerical basis in
one_line. If the true source strength is unknown, use a labeled, explicit, finite benchmark and report a conditional gap. Never use null or invent a measured source strength. Negative values mean
above threshold. Use the class of the actual mechanism. Give low mechanism
and survival scores if the estimate requires unsupported gain or violates measured bounds."""


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


def parse_screen(text):
    data = json.loads(text.strip().removeprefix("```json").removesuffix("```").strip())
    if data["action"] not in {"keep", "pivot", "reject"} or data["loophole_class"] not in LOOPS:
        raise ValueError("invalid screening verdict")
    premise = data["premise"]
    if not isinstance(premise, str) or not premise.strip():
        raise ValueError("missing screening premise")
    return data


async def work_seat(seat, providers, store, budget, router=None) -> None:
    if router is None:
        router = SwarmRouter()
    index = seat.id % len(providers)
    plan = providers[index:] + providers[:index]
    preferred = plan[0]
    store.start_seat(seat, preferred.name)
    catalogue = "\n".join(f"{name}. {description}" for name, description in LOOPS.items())
    screen, _ = await routed_ask(store, budget, plan, router, preferred, seat.id, "screen", f"""{brief(seat)}

Screen the premise. Reject or pivot naive single-particle Newtonian WIMP gravity and hypotheses with no
plausible chain to a biological signal. Keep a premise only if it fits one class below. A pivot must name an
alternative coupling and receptor. Return only a JSON object with action (keep, pivot, or reject),
loophole_class (one of A/B/C/D, closest class if rejected), and premise (one sentence).
{catalogue}""")
    verdict = parse_screen(screen)
    if verdict["action"] == "reject":
        store.finish_seat(seat.id, "rejected", verdict=verdict["premise"])
        return
    context = (f"{brief(seat)}\nScreened premise: {verdict['premise']}\n"
               f"Class {verdict['loophole_class']}: {LOOPS[verdict['loophole_class']]}."
               "\nTreat the screened premise as the hypothesis to evaluate.")
    hypothesis, proposer = await routed_ask(store, budget, plan, router, preferred, seat.id, "propose", f"""{context}

Propose one testable mechanism. Trace field to receptor to behavior, estimate signal and ordinary noise,
under an explicit finite benchmark if the actual source is unknown, and give a falsifiable prediction and
a feasible control experiment. Under 450 words.""")
    store.set_proposer(seat.id, proposer.name)
    critique, critic = await routed_ask(
        store, budget, plan, router, plan[min(1, len(plan)-1)], seat.id, "critique",
        f"{context}\n\n{hypothesis}\n\n{REVIEW_ASK}", avoid=(proposer.name,))
    revised, reviser = await routed_ask(
        store, budget, plan, router, proposer, seat.id, "revise",
        f"{context}\n\nHypothesis:\n{hypothesis}\n\nReview:\n{critique}\n\n"
        "Revise the mechanism and bounds using the review, keep one explicit conditional numerical gap "
        "if the source is unknown, and end with the cheapest falsification test. Under 500 words.")
    judge, _ = await routed_ask(
        store, budget, plan, router, plan[-1], seat.id, "judge:roundtable",
        f"{context}\n\n{revised}\n\n{SCORE_ASK}", avoid=(proposer.name, reviser.name, critic.name))
    if parse_scores(judge) is None:
        raise ValueError("judge returned invalid score data")
    rescore(store, seat.id)


async def run(seats, providers, store, budget, concurrency: int, log=print) -> dict:
    router = SwarmRouter()
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
                await work_seat(seat, providers, store, budget, router)
                outcome = store.seat(seat.id)["status"]
                stats[outcome] = stats.get(outcome, 0) + 1
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
