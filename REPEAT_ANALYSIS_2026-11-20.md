# ATOCIA — Repeated-trial descriptive analysis

Source: `repeated_trials.csv` (existing data only; no new CPU workload).

## Per-trial phase means

| Trial | Phase | Samples | Package W | PSys W | CPU package °C |
|---:|---|---:|---:|---:|---:|
| 1 | baseline | 30 | 3.478 | 9.971 | 40.80 |
| 1 | load | 20 | 5.083 | 12.080 | 43.45 |
| 1 | recovery | 30 | 3.483 | 9.612 | 41.57 |
| 2 | baseline | 30 | 3.493 | 9.828 | 41.30 |
| 2 | load | 20 | 4.991 | 11.858 | 43.85 |
| 2 | recovery | 30 | 3.478 | 9.688 | 41.77 |
| 3 | baseline | 30 | 3.455 | 9.637 | 41.17 |
| 3 | load | 20 | 5.067 | 11.936 | 44.15 |
| 3 | recovery | 30 | 3.503 | 9.764 | 41.63 |

## Within-trial changes (load minus baseline; recovery minus baseline)

| Trial | Package Δ W | CPU temp Δ °C | Recovery temp Δ °C | Recovery package Δ W |
|---:|---:|---:|---:|---:|
| 1 | 1.605 | 2.65 | 0.77 | 0.005 |
| 2 | 1.497 | 2.55 | 0.47 | -0.016 |
| 3 | 1.612 | 2.98 | 0.47 | 0.048 |

## Pooled descriptive summary

- Package power increase during load: mean 1.571, trial range 1.497 to 1.612.
- CPU package temperature increase during load: mean 2.728, trial range 2.550 to 2.983.
- Recovery temperature offset: mean 0.567, trial range 0.467 to 0.767.
- Recovery package power offset: mean 0.013, trial range -0.016 to 0.048.

## Interpretation and limits

- All three trials show increased package power and CPU package temperature during the CPU pulse.
- Package power during recovery is close to baseline in all three trials; temperature is still slightly above baseline at the end of the 30-second recovery window.
- These are descriptive results from three short repetitions, not a population-level statistical claim.
- The CPU temperature sensor is quantized at roughly 1 °C and the sampling interval is about one second. This is too coarse for trustworthy fine-grained thermal time-constant identification.
- Ambient temperature and fan RPM were not measured. The experiment therefore cannot identify absolute thermal resistance or a calibrated two-node RC model.
- PSys is a distinct platform energy domain and must not be added to package power.
- No causal claim about energy savings or controller superiority is supported.

## Next offline modeling step

Use these data to define the observation model and sensor uncertainty. For physical parameter identification, collect longer and varied pulse lengths with ambient temperature and fan behavior recorded. Keep controller work in offline simulation until the model passes held-out-trial prediction checks.
