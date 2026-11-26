# ATOCIA — Session handoff
Date: 2026-11-20
Version milestone: passive diagnostic prototype (0.5 groundwork)

## Final verification in this session

Command completed successfully as the ordinary local user:

    python3 ~/ATOCIA/atocia.py --report-dir ~/ATOCIA/USER_MODE_DEMO_V05 doctor --duration 2 --interval 1

Result:
- Exit code: 0.
- Unit tests: 24 passed, 0 failed.
- Powercap/CPU-policy audit generated.
- Battery/charging audit generated.
- Thermal-zone/cooling-topology audit generated.
- Two-second passive CSV capture generated.
- RAPL energy was marked unavailable to the ordinary user because sysfs permissions are root-only. The remaining sensors and reports still worked.
- No stress workload was launched.

## Files introduced or materially updated

- pulse_v04.py — read-only portable telemetry capture.
- audit_powercap.py — dynamic MSR/MMIO/PSys and processor-thermal PCI discovery.
- audit_battery.py — battery status/capacity report without serial-number collection.
- audit_thermal.py — thermal zones, trip points, cooling links and hwmon fan RPM audit.
- atocia.py — selftest, audit, capture and doctor commands.
- test_pulse_v04.py, test_audit_tools.py, test_audit_thermal.py — 24 offline unit tests.
- ATOCIA_PRODUCT_HYPOTHESIS_2026-11-20.md — updated product/competitor reality check.
- NEXT_VALIDATION_BLOCKERS_2026-11-20.md — exact outside evidence still needed.
- USER_MODE_DEMO_V05/ — reports and passive capture from the final successful normal-user run.

## Findings worth keeping

1. Intel Tiger Lake 8086:9A03 is exposed through proc_thermal on this Samsung.
2. Package energy appears through both RAPL MSR and MMIO. They are highly similar, overlapping views; do not sum.
3. PSys is a separate platform energy domain; do not add it to package power.
4. MSR long-term limit reads 40 W, MMIO long-term reads 10 W, and the Linux PL1 max-power reference reads 28 W. The reference is mapped to THERMAL_SPEC_POWER by the Linux common driver, so this is an observation, not proof of a bad limit or which path is enforced.
5. Five ACPI Fan cooling-device objects and several processor cooling devices are mapped to thermal trips. Their state is not RPM and does not prove physical fan count or fan failure.
6. Battery controller reports roughly 84.4% full-capacity retention relative to design, with 207 cycles and an 85% charge threshold. It is not a battery-fault diagnosis.
7. Three short CPU pulse trials showed repeatable qualitative power/temperature changes, but no validated thermal RC model or energy-saving claim exists.

## Commercial reality

Competitors already cover hardware probing, operability, logs, thermal/load diagnosis, power monitoring and firmware tests: hw-probe, Culprit, HardwareMonitorCpp, FWTS, PowerTOP, thermald, TLP and power-profiles-daemon.

The revised product hypothesis is not another Linux optimizer or generic hardware report. It is a technician-oriented, local-first, before/after service workflow that standardizes evidence for battery, AC, thermal/ACPI and power telemetry. There is no customer validation, willingness-to-pay signal or revenue yet.

## What is now blocked without outside help

- A second Linux laptop (preferably AMD or a different Intel generation) with owner's consent to test hardware compatibility.
- Later: an external wall-power meter for whole-system power validation and a room/ambient thermometer for thermal characterization.
- A controlled longer load/recovery window only when the owner is not gaming or doing important work, with explicit approval.
- Repair-shop / IT-admin interviews to determine whether the report changes a decision and saves enough time to justify payment.

## Safety and integrity

No BIOS, firmware, kernel, power limit, governor, EPP, power profile, service or fan state was changed. No package was installed. No remote upload was made. All newly written scripts are intended to read telemetry and create local reports only.