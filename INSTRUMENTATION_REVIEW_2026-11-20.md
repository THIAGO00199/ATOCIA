# ATOCIA — Instrumentation review

## 60-second instrumented passive capture

File: `instrumented_baseline_60s.csv` (60 samples, nominal 1 Hz).

- AC adapter: online for all 60 samples.
- Battery: 83% for all samples; status `Not charging`.
- CPU governor: `powersave` for all samples; driver: `intel_pstate`.
- CPU 0 frequency observed: 400 MHz to 1.540 GHz; mean about 825 MHz. This is CPU 0's sampled frequency, not an all-core frequency measurement.
- Aggregate CPU utilization: mean 4.53%, range 3.54–7.21%.
- RAPL package power: mean 3.488 W, range 2.984–4.200 W.
- PSys: mean 9.905 W, range 8.280–12.888 W.
- x86 package temperature: mean 41.35 C, range 40–43 C.
- Fan RPM: no `fan*_input` attribute was exposed through the discovered hwmon interfaces.

## Instrumentation gaps

- No ambient-air temperature sensor was found in the available kernel interfaces. An external thermometer is required for a meaningful ambient reference.
- Fan RPM is not exposed through the inspected hwmon interfaces. Fan state must remain unknown unless another supported source is identified.
- The CPU frequency reading is from CPU 0 only. Future versions should collect per-core or policy-level frequency and utilization.
- The 1 Hz package power samples show a repeating high/low pattern. The 60-second mean is useful for a coarse baseline, but higher-rate sampling and validation against an independent power meter are recommended before fine-grained control decisions.

## Data quality note

AC was connected, but the battery reported `Not charging` at 83%. This condition should be documented consistently across trials. It does not establish that all system power is supplied directly by the adapter without battery contribution under every transient.
