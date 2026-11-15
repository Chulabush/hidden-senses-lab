"""The research agenda: every seat is one agent brief = (animal sense) x (dark-sector portal) x (discipline)."""
import random
from dataclasses import dataclass
from itertools import product

# Animal senses that reach beyond human perception.
SENSES = [
    "migratory songbirds: cryptochrome radical-pair magnetic compass in the retina",
    "sea turtles: geomagnetic map sense (inclination and intensity)",
    "sharks and rays: ampullae of Lorenzini, nanovolt-per-centimetre electroreception",
    "platypus and echidna: bill electroreception",
    "weakly electric fish: active electrolocation with self-generated fields",
    "pit vipers and pythons: infrared pit organs (TRPA1 thermal imaging)",
    "fire-chasing jewel beetles: infrared photomechanical receptors",
    "mantis shrimp: 12+ colour channels and circular-polarisation vision",
    "cephalopods: polarisation vision with a single photoreceptor class",
    "honeybees and bumblebees: UV vision plus electric-field sensing by body hairs",
    "ballooning spiders: lift-off triggered by atmospheric electric fields",
    "reindeer: UV vision in Arctic winter",
    "kestrels and other raptors: UV-sensitive hunting vision",
    "bats: ultrasonic echolocation and Doppler discrimination",
    "elephants: infrasound and seismic communication through the feet",
    "homing pigeons: infrasound maps plus magnetic cues",
    "salmon and eels: magnetite-based navigation across oceans",
    "magnetotactic bacteria: chains of magnetite crystals as cellular compasses",
    "nematodes (C. elegans): magnetic orientation in single identified neurons",
    "fruit flies: cryptochrome-dependent magnetic and circadian responses",
    "monarch butterflies: time-compensated sun compass plus inclination compass",
    "dogs and foxes: magnetic alignment during hunting and marking",
    "cats and dogs: ultrasonic hearing, high flicker-fusion vision, staring at 'nothing'",
    "snakes and scorpions: substrate vibration sensing at nanometre amplitudes",
    "dung beetles and night-migrating insects: polarised moonlight and Milky Way orientation",
    "many species: reported unusual behaviour before earthquakes and storms",
]

# Ways an unseen sector of reality could touch ordinary matter at all.
PORTALS = [
    "gravity only: compact dark-matter clumps passing through a room or an animal's body",
    "axion-like particles coupling to electron spin (acts like a tiny oscillating magnetic field)",
    "dark photons with kinetic mixing (weak oscillating electric and magnetic fields)",
    "millicharged dark particles accumulating in the atmosphere and ground",
    "mirror matter with photon / mirror-photon mixing",
    "ultralight scalar dark matter that makes atomic sizes and reaction rates oscillate",
    "macroscopic composite dark matter (nuggets, Q-balls) crossing air, water and rock",
    "topological defects (domain walls, strings) sweeping across the Earth",
    "dark-matter streams, subhalos and the daily/annual modulation of the dark-matter wind",
    "dark matter gravitationally captured inside the Earth and its slow outflow",
    "rare nuclear and electronic recoils inside living tissue (DNA, ion channels, microtubules)",
    "extra spatial dimensions: gravity or fields leaking between nearby branes at short range",
]

# The discipline each agent argues from.
ROLES = [
    "particle theorist: write down the coupling and estimate its size",
    "sensory neurobiologist: trace the signal from receptor to behaviour",
    "quantum biologist: ask whether coherence or spin chemistry can amplify it",
    "instrument engineer: design a sensor that sees what the animal might see",
    "data scientist: find the public dataset where the signal would already be hiding",
    "field ethologist: design a behavioural experiment with living animals",
    "statistician: define the null test, controls and sample size",
    "evolutionary biologist: ask what selection pressure would build such a sense",
]


@dataclass(frozen=True)
class Seat:
    id: int
    sense: str
    portal: str
    role: str


def all_seats() -> list[Seat]:
    return [Seat(i, s, p, r) for i, (s, p, r) in enumerate(product(SENSES, PORTALS, ROLES), start=1)]


def sample(n: int, seed: int) -> list[Seat]:
    """A stable shuffled order, so a small run still spans the whole space."""
    seats = all_seats()
    random.Random(seed).shuffle(seats)
    return seats[:n]
