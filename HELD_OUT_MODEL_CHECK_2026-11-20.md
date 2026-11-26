# ATOCIA — Offline held-out predictive check

Existing repeated_trials.csv only; no hardware workload was run.
Target: next 1-second x86 package-temperature sample.
Candidate: T[t+1] = c + a*T[t] + b*Ppackage[t].
Baselines: persistence and EMA(alpha=0.20). Validation: leave-one-whole-trial-out.

| Held-out trial | ARX RMSE °C | Persistence RMSE °C | EMA RMSE °C | coefficients (c, a, b) |
|---:|---:|---:|---:|---|
| 1 | 1.166 | 1.939 | 1.046 | 41.052, 0.08883, -0.69477 |
| 2 | 1.414 | 2.120 | 1.175 | 34.802, 0.27307, -1.11564 |
| 3 | 1.362 | 2.225 | 1.182 | 36.235, 0.22328, -0.94646 |

## Interpretation

This is a small-sample predictive diagnostic, not physical RC identification. Sensor quantization is about 1 °C; ambient temperature and fan behavior are missing.
Only a model that consistently beats simple baselines on held-out complete trials and remains physically plausible should advance.
No controller action or system configuration change was performed.
