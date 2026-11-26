# ATOCIA — Battery and charging audit

- Collected (UTC): 2026-11-20T20:05:28.918144+00:00
- Mode: read-only; no charge thresholds or power settings were changed.

## AC adapter

- Online: 1

## Battery 1 (BAT1)

- Present: 1
- Status: Not charging
- State of charge: 83.0%
- Estimated full-capacity retention: 84.4%
- Charge cycles: 207
- Current end-charge threshold: 85%
- Voltage: 12.201 V
- Current: 0.000 A
- Current stored charge: 2.647 Ah
- Full charge capacity: 3.190 Ah
- Design charge capacity: 3.780 Ah

## Interpretation guardrails

- Capacity retention is estimated from the battery controller's reported full-charge and design capacities. Calibration, temperature and battery age can affect it.
- Cycle count and percentage alone do not diagnose a battery fault.
- A charge threshold is recorded as reported; this audit does not change it or assume it explains the current charge state.
- Current and voltage readings are instantaneous snapshots, not a stable whole-system power measurement.
- Battery telemetry does not replace an external power meter when validating whole-system energy savings.
- The report intentionally does not collect battery serial numbers or other unique device identifiers.
