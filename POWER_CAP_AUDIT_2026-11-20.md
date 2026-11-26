# ATOCIA — Powercap consistency audit

- Collected (UTC): 2026-11-20T20:03:12.344124+00:00
- Mode: read-only; no hardware or system settings were changed.

## Device

- Manufacturer: SAMSUNG ELECTRONICS CO., LTD.
- Model: 550XDA
- Board: NP550XDA-KS3BR
- BIOS: P23CFB.053.241029.HQ
- CPU: 11th Gen Intel(R) Core(TM) i7-1165G7 @ 2.80GHz
- Kernel: 7.1.8-zen1-3-zen
- Processor Thermal PCI ID: 0000:00:04.0 0x8086:0x9a03
- Processor Thermal driver: proc_thermal
- Power profile: power-saver

## CPU policies

| Policy | CPUs | Governor | EPP | Min MHz | Max MHz |
|---|---|---|---|---:|---:|
| policy0 | 0 | powersave | power | 400 | 4700 |
| policy1 | 1 | powersave | power | 400 | 4700 |
| policy2 | 2 | powersave | power | 400 | 4700 |
| policy3 | 3 | powersave | power | 400 | 4700 |
| policy4 | 4 | powersave | power | 400 | 4700 |
| policy5 | 5 | powersave | power | 400 | 4700 |
| policy6 | 6 | powersave | power | 400 | 4700 |
| policy7 | 7 | powersave | power | 400 | 4700 |

## RAPL interfaces

### MSR

- Name: package-0
- Energy counter: 44061263240 µJ
- Counter wrap range: 262143328850 µJ

| Constraint | Configured limit | Reference value | Window | Comparison |
|---|---:|---:|---:|---|
| long_term | 40.00 W | 28.00 W | 27.984 s | above thermal-spec reference |
| short_term | 45.00 W | 0.00 W | 0.002 s | not comparable |
| peak_power | 80.00 W | 0.00 W | n/a | not comparable |

### PSys

- Name: psys
- Energy counter: 195847469515 µJ
- Counter wrap range: 262143328850 µJ

| Constraint | Configured limit | Reference value | Window | Comparison |
|---|---:|---:|---:|---|
| long_term | 57.00 W | n/a | 27.984 s | not comparable |
| short_term | 57.00 W | n/a | 0.001 s | not comparable |

### MMIO

- Name: package-0
- Energy counter: 44061275935 µJ
- Counter wrap range: 262143328850 µJ

| Constraint | Configured limit | Reference value | Window | Comparison |
|---|---:|---:|---:|---|
| long_term | 10.00 W | 28.00 W | 27.984 s | at/below thermal-spec reference |
| short_term | 45.00 W | 0.00 W | 0.002 s | not comparable |
| peak_power | 80.00 W | 0.00 W | n/a | not comparable |

## Cross-interface comparison

- Absolute energy-counter difference at read time: 12695 µJ (0.00002881% of the counter magnitude).
- The counters are two views of the package domain. Do not add them together.
- A tiny difference can result from the sequential reads occurring at slightly different instants.

## Power-management services

| Service | State |
|---|---|
| power-profiles-daemon | active |
| thermald | inactive |
| tlp | inactive |
| auto-cpufreq | inactive |
| tuned | inactive |

## Interpretation guardrails

- A power limit is a configured constraint, not the instantaneous power draw.
- MSR and MMIO are separate access interfaces; their limits must be recorded separately.
- A difference between interfaces is a diagnostic observation, not automatically a defect.
- For the RAPL PL1/long_term constraint, the Linux driver currently maps max_power_uw to THERMAL_SPEC_POWER. Treat it as a thermal-spec/TDP reference, not automatically as a hard register ceiling.
- A configured PL1 above that reference is recorded for review, not automatically classified as a defect.
- Package energy counters are alternative views of the package domain and must not be summed.
- This audit does not estimate savings, benchmark performance, or assert which limit is effective.

## Technical references

- Linux kernel Tiger Lake processor-thermal PCI support and MMIO RAPL registration: https://lkml.iu.edu/hypermail/linux/kernel/2011.3/03463.html
- Linux processor thermal MMIO RAPL implementation: https://kernel.googlesource.com/pub/scm/linux/kernel/git/torvalds/linux/+/1334d2a3b3235d062e5e1f51aebe7a64ed57cf72/drivers/thermal/intel/int340x_thermal/processor_thermal_rapl.c
- Linux powercap sysfs interface: https://www.kernel.org/doc/html/latest/power/powercap/powercap.html
- Linux RAPL common code maps PL1 max-power reporting to THERMAL_SPEC_POWER: https://github.com/torvalds/linux/blob/master/drivers/powercap/intel_rapl_common.c
- Intel Core i7-1165G7 product specifications (cTDP-down 12 W, cTDP-up 28 W): https://www.intel.com/content/www/us/en/products/sku/208662/intel-core-i71165g7-processor-12m-cache-up-to-4-70-ghz/specifications.html
