# Hidden Senses Lab: research programme

# Research programme: animal senses as dark-sector detector designs

**Bottom line:** in all six hypotheses the animal itself fails as a dark-sector detector, by 9 to 27 orders of magnitude. What survives is a set of instrument designs borrowed from the tissue, plus two biology results worth having for their own sake. All six seats come from one lab, so none of the estimates has been independently checked.

## 1. Recurring mechanisms

| Mechanism | Seats | Status |
|---|---|---|
| **A. Tissue as a calibrated upper-limit detector.** Measure the animal's or cell's psychometric curve, then convert a null result into a bound. | 322, 1079, 1814, 1065 | Sensory thresholds are established; every dark coupling is conjecture. |
| **B. Convert, then sort.** A conducting mirror turns eV dark photons into real photons, which rods or midband-style narrow filters and polarisers then count and sort. | 767, 1079 | Conversion is established physics if the particle exists. |
| **C. Differential linearisation.** Use a twin channel or a phase-stable bias to make a tiny or second-order signal linear. | 1065 (heterodyne), 1488 (gas vs evacuated cell), 322 (bill vs magnetometer) | Conjecture as engineering; the thermal and intensity-noise floors are unmeasured. |
| **D. Shielding as discriminator.** The signal ignores shields (mu-metal for the axion-like particle field and εB′), is made by them (mirror), or is removed by them (lead). | 1065, 322, 1079, 1814 | Follows from each coupling. |
| **E. Chemical amplification.** Radical-pair spin chemistry or redox signalling turns sub-thermal energy into a yield change. | 1065, 1814 | Radical pairs are established in vitro; the mammalian-retina and clustered-damage steps are conjecture. |

A statistical toolkit also recurs across 1065, 1488, 322, 1814 and 767. It consists of an anti-sidereal null, blinded block labels, injected signals and scrambled templates.

## 2. Ten experiments, ranked

Ranking favours cheap experiments whose null result stops a line of work.

| # | Experiment | Measure, with what | Discovery would be | Cost |
|---|---|---|---|---|
| 1 | Heterodyne radical-pair bench (1065) | Flavin–tryptophan fluorescence yield under a 1.5 MHz bias; Larmor sweep at 25–100 µT; injected pT tones | A linear readout that works and a measured B_min, giving the first lab bound on g_aee at 2–12 neV | Bench-top |
| 2 | Lead vs sham worms (1814) | *gst-4::GFP* fluorescence in *C. elegans*, 10 cm lead with gamma dose restored by KCl, blind alternation | A reporter shift of a few percent or more, which then needs experiment 8 to interpret | Bench-top |
| 3 | Rod A/A test (1079) | Toad rods on a suction rig, dummy shutter, permutation test, 340 nm flashes | None; it passes if the false-positive rate is nominal and the stray-photon floor is measured | Bench-top on an existing rig |
| 4 | Comb fit to transition-edge-sensor dark counts (767) | Poisson profile likelihood over R against scrambled combs, on about 10⁶ s of data | None expected (reach ε ≈ 10⁻⁹); it validates the statistic and trials factor | Free data, if a public set exists |
| 5 | Audiogram comparison (1488) | Published infrasound thresholds against middle-ear volume and homing ecology, phylogenetically corrected | A threshold that tracks navigation and not cavity size | Free data |
| 6 | Platypus psychometric curve (322) | Phantom dipoles at 20–100 µV/cm, Ag/AgCl pair, fluxgate, video, one zoo animal | Empty strikes above baseline with a quiet magnetometer | Bench-top |
| 7 | Retinal Larmor scan (1065) | Electroretinogram lock-in on reindeer or other mammalian explants, RF 0.5–3 MHz, static field stepped | A response peak moving at 28 Hz/nT, the first radical-pair proof in a mammal | Lab-scale |
| 8 | Neutron calibration (1814) | Sb-Be source giving 10–10⁵ recoils per worm-hour, with a dose-matched gamma arm | A response that scales with recoil rate and not gamma dose | Lab-scale, licensed source |
| 9 | Mirror with energy-resolving detector (767, 1079) | 1 m² mirror, superconducting sensor at 0.2 eV resolution or better, shutter, off-focus control, rotating polariser | Integer-spaced lines at one R, or a 320–350 nm excess that dies off-focus | Lab- to facility-scale |
| 10 | Twin-cell artificial ear (1488) | Gas-filled and evacuated silica cavities, interferometric readout, underground | A non-integer-Hz line in the gas cell only, at zero lag across sites | Lab-scale, then a three-site network |

Run the sidereal and anti-sidereal pipeline, with injected lines, on public collar accelerometry and infrasound archives alongside these. It is free and is a systematics exercise only.

## 3. The prototype one person can start now

Build the heterodyne radical-pair cell from experiment 1:

- **Parts:** a mu-metal box, a Helmholtz pair, an RF coil, a 450 nm LED or diode, a photodiode and an I/Q lock-in.
- **Extra channel:** add a pickup coil beside the cell. An electron-spin coupling acts on spins but induces no voltage in a coil, so a line in the chemistry channel and not in the coil is the signature.
- **Expected signal (my estimate):** with a 1 µT bias and a 1 µs pair lifetime, a 1 pT tone changes the yield by about 6×10⁻⁸. Shot noise reaches that in about a second at 1 mW, so light-source intensity noise will set the real floor.

**It could see:**
- Real RF magnetic fields at pT–nT level through spin chemistry.
- Larmor tracking of the resonance with static field.
- A spin-only pseudo-field at g_aee ≳ 10⁻⁵ for masses of 2–12 neV.

**It could not see:**
- Anything at allowed couplings; it sits eight orders above the stellar bound.
- The benefit of the particle's 0.7 s coherence beyond the lock-in bandwidth, because the pair linewidth gives Q ≈ 1.
- Scalars, eV dark photons or recoils.

## 4. Open questions for the next round

- **Is there any coupling where tissue beats instruments?** None of the six found one. Untested candidates are parity-odd couplings to homochiral biomolecules, hydrogen-rich targets for sub-GeV scattering, and integration over a lifetime or over generations.
- **Do the recalled bounds hold?** Check ε at 1.8–4 eV, g_aee at neV masses, and the scalar strain limit at 0.1–10 Hz against current literature.
- **Which energy-resolved single-photon dark-count datasets are public?** Seat 767 did not check.
- **Does the twin cell's thermal floor really scale with pressure?** If a buffer-gas or large-volume design breaks that scaling, the reach changes.
- **Is clustered sub-ionising bond breakage sensed differently from diffuse radicals?** This is one biology measurement, and it decides seat 1814.
- **Is mammalian cryptochrome photoactive and magnetosensitive in vitro?** Reindeer protein expression is the gating step for experiment 7.
- **What is the avian middle-ear vent corner frequency?** It is unmeasured and sets the pigeon transfer function.
- **Do the numbers survive independent re-derivation?** The other two labs should redo the yield, rate and reach estimates.

## Top hypotheses

| Seat | Score | Proposed by | Sense | Link to the unseen |
|---|---|---|---|---|
| 1065 | 6.62 | claude | reindeer: UV vision in Arctic winter | axion-like particles coupling to electron spin (acts like a tiny oscillating magnetic field) |
| 1488 | 5.88 | claude | homing pigeons: infrasound maps plus magnetic cues | ultralight scalar dark matter that makes atomic sizes and reaction rates oscillate |
| 767 | 5.62 | claude | mantis shrimp: 12+ colour channels and circular-polarisation vision | extra spatial dimensions: gravity or fields leaking between nearby branes at short range |
| 322 | 5.5 | claude | platypus and echidna: bill electroreception | mirror matter with photon / mirror-photon mixing |
| 1079 | 5.38 | claude | reindeer: UV vision in Arctic winter | dark photons with kinetic mixing (weak oscillating electric and magnetic fields) |
| 1814 | 4.75 | claude | nematodes (C. elegans): magnetic orientation in single identified neurons | rare nuclear and electronic recoils inside living tissue (DNA, ion channels, microtubules) |

## Usage

| Lab | Calls | Input tokens | Output tokens |
|---|---|---|---|
| claude | 35 | 39,981 | 18,753 |
