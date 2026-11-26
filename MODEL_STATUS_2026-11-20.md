# ATOCIA — Experimental model status (2026-11-20)

## Repeated short-pulse experiment

Three independent cycles were recorded. Each cycle had 30 s passive baseline, 20 s of one CPU-bound worker, and 30 s passive recovery. Sampling was nominally 1 Hz. The worker was stopped automatically at the end of the phase; a 75 C thermal guard was active. No firmware, voltage, fan, frequency, or power-limit settings were changed.

| Phase | Mean package power | Mean PSys | Mean x86 package temp | Mean TCPU |
|---|---:|---:|---:|---:|
| Baseline (90 samples) | 3.475 W | 9.812 W | 41.089 C | 40.611 C |
| CPU pulse (60 samples) | 5.047 W | 11.958 W | 43.817 C | 43.817 C |
| Recovery (90 samples) | 3.488 W | 9.688 W | 41.656 C | 41.267 C |

Across the three trials, package power increased by about 1.57 W during the pulse. The x86 package sensor mean increased by about 2.73 C and returned to within about 0.57 C of the pooled baseline mean during recovery. The direction of response was consistent in all three trials.

## Longer step observation

A separate run used 30 s baseline, 45 s one-worker CPU activity, and 60 s recovery:

| Phase | Mean package power | Mean PSys | Mean x86 package temp | Max x86 package temp |
|---|---:|---:|---:|---:|
| Baseline | 3.492 W | 10.038 W | 41.10 C | 42 C |
| CPU activity | 5.072 W | 13.691 W | 43.87 C | 46 C |
| Recovery | 3.517 W | 11.485 W | 41.95 C | 43 C |

The longer pulse showed the same qualitative package-power and temperature response. PSys stayed elevated in recovery, likely reflecting platform/background activity or measurement variation; this must be investigated separately and is not CPU package power.

## Model fitting decision

An initial one-step linear regression was explored, but it produced implausibly short apparent time constants and unstable parameters across held-out trials. It is **rejected as a physical RC model** and must not be used for control or claims. The current thermal sensor readings are quantized at approximately 1 C and ambient temperature, fan behavior, battery/AC state, and workload utilization were not recorded. Those omissions make an RC parameter estimate underdetermined or poorly identified.

## Current conclusion

The repeated experiments support a reproducible qualitative observation: a short single-worker CPU activity pulse increases RAPL package power and reported CPU temperature, followed by recovery after the worker stops. They do not yet establish thermal resistance/capacitance, predictive accuracy, energy savings, or an ATOCIA advantage.

## Next measurement requirements

1. Log wall-clock and monotonic timestamps, AC/battery state, CPU frequency/utilization, and all available relevant thermal zones.
2. Measure ambient air temperature with an external thermometer placed near the laptop intake, without obstructing airflow.
3. Record fan RPM if the platform exposes it; otherwise mark fan state unknown.
4. Use multiple pulse lengths and at least three repeats per length, with sufficient passive recovery.
5. Fit candidate one-node and two-node RC models, then evaluate on held-out complete trials. Report confidence intervals and compare against a persistence/EMA baseline.
6. Keep all controller actions in offline simulation or shadow mode until predictive validation is demonstrated.

## Raw data

- `repeated_trials.csv` — three 80 s cycles, 240 samples.
- `long_step_2026-11-20.csv` — one 135 s cycle, 135 samples.
- `step_probe_20s.csv`, `baseline_30s.csv`, `recovery_30s.csv` — earlier exploratory captures.
