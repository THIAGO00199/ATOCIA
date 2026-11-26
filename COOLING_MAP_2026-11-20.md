# ATOCIA — ACPI cooling topology snapshot
Date: 2026-11-20
Mode: read-only sysfs inspection.

## Discovered topology

- Thermal zone: thermal_zone0, type acpitz.
- Zone policy at snapshot: step_wise.
- Reported zone temperature during the 30-second passive observation: 51.0°C (after an earlier read of 52.0°C).
- Five linked ACPI cooling-device objects are exposed as type Fan, each with max_state 1.
- Each device is linked to an ACPI active trip point.

| Cooling device | ACPI path | Active trip index | Trip temperature | Cooling state |
|---|---|---:|---:|---:|
| cooling_device4 | \\_TZ_.FAN4 | 6 | 40°C | 0/1 |
| cooling_device3 | \\_TZ_.FAN3 | 5 | 45°C | 0/1 |
| cooling_device2 | \\_TZ_.FAN2 | 4 | 50°C | 0/1 |
| cooling_device1 | \\_TZ_.FAN1 | 3 | 55°C | 0/1 |
| cooling_device0 | \\_TZ_.FAN0 | 2 | 71°C | 0/1 |

During a 30-second passive capture, all five cooling-device state values remained at 0 for all 30 samples. The acpitz zone remained at 51°C throughout that capture. The CPU package sensor varied between 49°C and 51°C.

## Additional ACPI detail

- Each of the five PNP0C0B objects is bound to the acpi-fan driver.
- Each ACPI firmware node reports D3hot for power_state and real_power_state at the sampled instant.
- Runtime power status is reported as unsupported.
- No fan RPM tachometer was exposed through the inspected hwmon paths.

## Important interpretation limits

- These are five ACPI cooling-device objects. They do not establish that the laptop has five physical fans.
- The 0/1 value is a kernel/ACPI cooling-device state, not an RPM measurement and not reliable independent confirmation of physical airflow.
- D3hot is an ACPI device power state, not proof that the physical cooling hardware is stopped.
- The snapshot shows that the reported acpitz temperature was above the first three linked active trip temperatures while all five cooling-device state values were 0. This is an observation worth investigating, not proof that the physical fan was stopped or that cooling is faulty.
- The acpitz zone may not be the same sensor used by the embedded controller for actual fan behavior. Firmware may also manage cooling independently.
- Do not write cooling-device state files. The system's firmware and kernel thermal policy must remain in control.

## ATOCIA opportunity

A diagnostic report can expose cooling topology and explicitly flag a zone-reading / cooling-state mismatch for technician review. It must never translate that observation into an automatic fan-control action or a hardware-fault verdict.
