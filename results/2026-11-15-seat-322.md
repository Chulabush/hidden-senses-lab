Seat 322 [done] score=5.5
platypus and echidna: bill electroreception
mirror matter with photon / mirror-photon mixing
sensory neurobiologist: trace the signal from receptor to behaviour

--- propose · claude (claude CLI) ---
## Claim
Conjecture: platypus bill electroreceptors could register the ordinary electric field, suppressed by the mixing parameter ε, of net mirror-charged clumps of Earth-bound mirror matter passing through the water within centimetres of the bill. My own estimate says this almost certainly fails, by many orders of magnitude.

## Mechanism
1. Photon/mirror-photon kinetic mixing (ε ≲ 10⁻⁹, from cosmology and orthopositronium limits) makes a mirror charge Q′ act on ordinary ions as charge εQ′.
2. A clump drifting through stream water imposes an effective field εE′ on Na⁺ and Cl⁻ in the water and in the mucous-gland duct.
3. That drives current down the duct to the bare trigeminal terminals at its base (about 40,000 glands, established).
4. Afferents converge on the bimodal electro/mechanosensory stripes of S1 cortex (established).
5. The animal makes a head saccade and snaps at a "prey" location where nothing is.

## Size of the effect
- **Threshold:** behaviour is triggered at about 50 µV/cm and cortical responses at about 20 µV/cm, which is 2×10⁻³ V/m. Single afferents need about 1 mV/cm.
- **Field required:** with ε = 10⁻⁹, the mirror-sector field must be E′ ≈ 2×10⁶ V/m over centimetres, which a mirror plasma would itself neutralise.
- **Screening:** stream water (σ ≈ 10⁻² S/m) relaxes in about 70 ns, so ordinary ions cancel εE′ long before the receptor's 20–200 Hz passband can respond. Only a source moving faster than about 10⁵ m/s escapes screening, and its transit is then too brief for the receptor to follow.
- **Noise to beat:** prey electromyogenic fields (shrimp tail-flicks, about 1 mV/cm) and streaming potentials.
- **Net:** the shortfall is at least 6 orders of magnitude before screening, and worse after.

## What we would observe
- Strikes or saccades with no prey and no mechanical stimulus.
- A sidereal (23.93 h) or annual modulation in their rate, if the source is a halo wind and not Earth-bound.
- Persistence of these strikes in an electrically quiet tank.

## How to test it
- **Empty-tank recording:** film a captive platypus in a prey-free, vibration-isolated tank while Ag/AgCl electrode pairs (noise about 1 nV/cm/√Hz, roughly 10⁴ times better than the bill) and a SQUID or fluxgate record the same water. Any field of this kind moves electrode ions exactly as it moves duct ions.
- **Existing data:** zoo and field accelerometer or video logs of foraging, checked for a sidereal periodicity in empty strikes.
- **Shielding control:** a Faraday enclosure also cancels εE′ from external mirror sources, because conductor electrons rearrange against it. Only clumps inside the cage would get through.

## What would count against it
- No spurious strikes above the baseline rate.
- Strikes that coincide with nothing on electrodes that are 10⁴ times more sensitive.
- No sidereal or annual term in the strike rate.

Any one of these kills the hypothesis. Because the signal reaches the receptor through ordinary ions, the animal cannot outperform an electrode in the same water. The useful output is therefore a null result, with the platypus as a cheap 40,000-channel coincidence detector.

--- critique:claude · claude (claude CLI) ---
**1. Weakest link: screening (step 2), which is worse than stated**

- **Static screening:** ordinary ions form a Debye cloud around an effective charge εQ′. In roughly 1 mM stream water the Debye length is about 10 nm, so no field survives beyond that.
- **Moving source:** the unscreened fraction is about vτ/r. For a clump drifting at 1 m/s, with τ = 70 ns and r = 1 cm, that is about 7×10⁻⁶, a further 5 orders on top of the 6-order shortfall.
- **Receptor pooling:** the 50 µV/cm behavioural threshold against about 1 mV/cm per afferent implies pooling across much of the bill. The field must therefore be coherent over centimetres.
- **Passband:** the platypus converts DC fields to AC with its own head sweeps, so the source need not fall in the 20–200 Hz band, but that does not rescue a screened field.

**2. Ordinary explanations to exclude**

- Push-rod mechanoreceptor triggers from microturbulence.
- Spontaneous exploratory strikes and learned anticipation of feeding.
- Mains pickup at 50 Hz, which is in the passband.
- Galvanic fields from tank metals and from the recording electrodes themselves.
- Streaming potentials.
- Solar-day activity rhythms, which only separate from the sidereal period (23.93 h vs 24 h) with at least a year of data.

**3. One change: switch to the magnetic channel**

A time-varying mirror field εB′ is not screened by water (skin depth at 100 Hz is about 500 m) and induces an ordinary field E ≈ ωBr/2 in the bill. Reaching threshold needs an effective B of about 2×10⁻⁴ T, so B′ ≈ 2×10⁵ T at ε = 10⁻⁹. That is still hopeless for the animal, but a SQUID in the same water (fT/√Hz) beats the bill by about 10 orders.

To make the null quantitative, inject calibrated phantom dipole fields at 20–100 µV/cm to measure the strike psychometric function. "No excess strikes" then becomes an upper limit on the effective field rate.

--- revise · claude (claude CLI) ---
## Claim
Conjecture: a time-varying mirror magnetic field εB′, from moving mirror-charged matter coupled by photon/mirror-photon kinetic mixing, could induce an ordinary electric field in the platypus bill. The original electric-field route is dropped because it is screened. By my estimate the magnetic route also fails for the animal, by about 9 orders of magnitude. What survives is the platypus as a calibrated coincidence detector that yields an upper limit.

## Mechanism
1. Kinetic mixing (ε ≲ 10⁻⁹; conjectural physics, bounded by experiment) makes mirror currents act on ordinary charges as an effective field εB′.
2. Water does not screen it: the skin depth at 100 Hz and σ ≈ 10⁻² S/m is about 500 m.
3. Faraday induction gives E ≈ ωBr/2 around the bill and drives ion current down the mucous-gland ducts to the trigeminal terminals (about 40,000 glands, established).
4. Afferents pool across the bill into the bimodal S1 stripes (established), so the field must be coherent over centimetres. An induced field is.
5. The animal makes a head saccade or strike at nothing.

Dropped: the electrostatic route. The Debye length is about 10 nm, and a clump drifting at 1 m/s leaves an unscreened fraction of about 7×10⁻⁶.

## Size of the effect
- **Threshold:** about 50 µV/cm for behaviour and 20 µV/cm for cortex (2×10⁻³ V/m).
- **Field required:** an effective B of about 2×10⁻⁴ T at 100 Hz with r ≈ 3 cm, so B′ ≈ 2×10⁵ T at ε = 10⁻⁹.
- **Plausible source:** even a mirror field as strong as Earth's (5×10⁻⁵ T, itself generous) falls short by about 9 orders.
- **Instrument comparison:** a SQUID in the same water (fT/√Hz) beats the bill by about 10 orders.
- **Noise to beat:** 50 Hz mains, galvanic and streaming potentials, and prey EMG at about 1 mV/cm.

## What we would observe
- Strikes with no prey and no mechanical stimulus, coincident with a magnetometer transient.
- A sidereal (23.93 h) or annual term in the strike rate, which needs at least a year of data to separate from the solar day.

## How to test it
- **Calibration:** inject phantom dipole fields at 20–100 µV/cm to measure the strike psychometric function.
- **Empty-tank recording:** use a prey-free, vibration-isolated, metal-free tank with Ag/AgCl pairs, a SQUID or fluxgate, and a hydrophone or accelerometer to veto push-rod triggers from microturbulence.
- **Baseline:** log spontaneous and feeding-anticipation strikes on a randomised feeding schedule.
- **Shielding control:** mu-metal or a superconducting shield does not block εB′, since ordinary matter responds only at order ε. A strike rate that is unchanged while the magnetometer stays quiet would be the signature.

## What would count against it
- An empty-strike rate equal to the baseline, converted through the psychometric curve into an upper limit on the effective-field event rate.
- Strikes with no coincident magnetometer or electrode signal.
- No sidereal or annual term.

Because the signal arrives as an ordinary induced field, the animal cannot outperform the magnetometer. A null result is the expected and useful outcome.

## Cheapest first experiment
Use one captive platypus in its existing zoo tank for a week. A battery-driven dipole (two carbon electrodes and a function generator) delivers randomised phantom fields at 20–100 µV/cm, while one Ag/AgCl pair, a fluxgate, and a video camera record. This gives the psychometric function and the empty-strike baseline for a few hundred dollars, and every later null result depends on those two numbers.

--- judge:claude · claude (claude CLI) ---
{"novelty": 5, "testability": 7, "mechanism": 8, "survives_known_data": 2, "one_line": "The receptor-to-behaviour chain is fully traced and the calibration experiment is cheap and real, but the author's own numbers put the bill about 9 orders short of any plausible source and 10 orders behind a SQUID, so the dark-sector link is effectively excluded and only a conventional psychometric upper limit remains."}
