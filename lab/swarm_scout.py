"""Evaluate a shuffled visual-system × coupling × amplifier matrix."""
import asyncio
import json
import random
from itertools import product

from .agenda import Seat
from .pipeline import LOOPS, Budget, BudgetExhausted, routed_ask
from .providers import ProviderError
from .router import SwarmRouter

VISUAL_SYSTEMS = (
    "migratory songbird retina", "sea turtle retina", "mantis shrimp midband",
    "octopus rhabdomeric retina", "honeybee compound eye", "reindeer retina",
    "kestrel fovea", "fruit fly compound eye", "monarch dorsal rim area",
    "dung beetle dorsal rim area", "deep-sea fish multibank retina", "owl rod-rich retina",
    "cat tapetum and retina", "zebrafish cone mosaic", "frog green rods",
    "gecko nocturnal cones", "jumping spider principal eyes", "scallop mirror eye",
    "horseshoe crab lateral eye", "dragonfly dorsal eye", "squid polarization retina",
    "arctic charr retina", "chameleon fovea", "moth superposition eye",
    "box jellyfish upper lens eye", "elephantnose fish grouped retina",
)
AMPLIFIERS = (
    "radical-pair spin-selective recombination", "transducin cascade gain",
    "rhabdomeric single-photon gain", "synchronous rod pooling",
    "waveguide confinement", "coherent integration over a receptor array",
    "polarization subtraction", "resonant spin accumulation",
    "narrow-band temporal integration", "coincidence detection",
    "stochastic resonance", "reflective double pass",
)
ID_OFFSET = 1_000_000


def candidates(seed):
    matrix = list(product(VISUAL_SYSTEMS, LOOPS, AMPLIFIERS))
    random.Random(seed).shuffle(matrix)
    return matrix


def parse_candidate(text):
    data = json.loads(text.strip().removeprefix("```json").removesuffix("```").strip())
    potential, hypothesis = data["potential"], data["hypothesis"]
    if type(potential) is not int or not 0 <= potential <= 100:
        raise ValueError("potential must be an integer from 0 to 100")
    if not isinstance(hypothesis, str) or not hypothesis.strip():
        raise ValueError("hypothesis must be nonempty")
    return hypothesis, potential


async def scout(store, providers, count, concurrency, seed, budget, log=print):
    pending = [(v, c, a) for v, c, a in candidates(seed) if not store.scout_exists(v, c, a)]
    queue = iter(enumerate(pending[:count]))
    router = SwarmRouter()
    inserted = failed = 0
    stopped = False
    consecutive_failures = 0

    async def worker():
        nonlocal inserted, failed, stopped, consecutive_failures
        while not stopped:
            item = next(queue, None)
            if item is None:
                return
            index, (visual, category, amplifier) = item
            preferred = providers[index % len(providers)]
            prompt = f"""Visual system: {visual}
Coupling class {category}: {LOOPS[category]}
Candidate amplifier: {amplifier}

Find one testable optical or sensory hypothesis, with a quantitative bottleneck and a null control.
Treat any gain or coupling that lacks evidence as conjecture. Give a low score if the mechanism needs
unphysical gain, conflicts with bounds, or has no known pathway in this visual system.
Return a JSON object with hypothesis (a short string) and potential (integer 0 to 100)."""
            try:
                text, _ = await routed_ask(store, budget, providers, router, preferred, 0, "scout", prompt,
                                           record=False)
                hypothesis, potential = parse_candidate(text)
                inserted += store.save_scout(visual, category, amplifier, hypothesis, potential)
                consecutive_failures = 0
            except (BudgetExhausted, ProviderError) as exc:
                log(f"  scout paused: {str(exc) or 'model-call budget reached'}")
                stopped = True
            except (TypeError, ValueError, KeyError) as exc:
                failed += 1
                consecutive_failures += 1
                log(f"  scout candidate failed ({visual}, {category}, {amplifier}): {exc}")
                stopped = consecutive_failures >= 5

    await asyncio.gather(*(worker() for _ in range(min(concurrency, len(pending), count))))
    return inserted, failed


def promotion_seats(store, count):
    return [
        Seat(row["id"] + ID_OFFSET, row["visual_system"],
             f"Class {row['loophole_class']}: {LOOPS[row['loophole_class']]}",
             f"Scout amplifier: {row['amplifier']}. Scout hypothesis: {row['hypothesis']}")
        for row in store.promotion_candidates(count, ID_OFFSET)
    ]
