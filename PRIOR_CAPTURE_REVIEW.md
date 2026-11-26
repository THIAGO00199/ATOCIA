# Review of pre-existing ATOCIA captures

These two captures and the step-response log were already present in the project directory before this review. They were not created or modified by the current diagnostic run. Their exact workload procedure and environmental conditions are not documented in the files, so they are treated as exploratory data only.

## 60-second capture

- 60 samples over 60.01 s
- Package mean: 3.469 W (median 3.438 W; min 3.340 W; max 3.702 W)
- PSys mean: 9.961 W (median 9.669 W; min 9.195 W; max 11.601 W)
- CPU package temperature mean: 41.40 C; max: 43 C

## 90-second exploratory transient

- 90 samples over 90.01 s
- Package mean across full capture: 3.715 W
- PSys mean across full capture: 10.046 W
- CPU package temperature mean: 42.08 C; max: 45 C

Ten-second windows show a clear transient during seconds 11–30, followed by a return near the initial level:

| Seconds | Package mean | PSys mean | CPU package temp mean | CPU package temp max |
|---|---:|---:|---:|---:|
| 1–10 | 3.483 W | 9.721 W | 41.30 C | 42 C |
| 11–20 | 4.956 W | 11.954 W | 43.90 C | 45 C |
| 21–30 | 4.213 W | 10.803 W | 43.10 C | 45 C |
| 31–40 | 3.501 W | 9.729 W | 42.20 C | 43 C |
| 41–50 | 3.453 W | 9.638 W | 41.90 C | 43 C |
| 51–60 | 3.479 W | 9.590 W | 41.90 C | 43 C |
| 61–70 | 3.429 W | 9.561 W | 41.30 C | 42 C |
| 71–80 | 3.449 W | 9.693 W | 41.60 C | 42 C |
| 81–90 | 3.473 W | 9.725 W | 41.50 C | 42 C |

## Interpretation

The transient is consistent with a short increase in system activity followed by recovery, but the files do not identify the workload or prove a controlled step input. This is not sufficient to estimate an RC thermal model or claim ATOCIA performance. Repeat with a documented workload, controlled initial condition, and ambient-temperature measurement.
