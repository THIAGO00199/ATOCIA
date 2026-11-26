# ATOCIA — Thermal and cooling audit

- Collected (UTC): 2026-11-20T20:05:28.231263+00:00
- Mode: read-only; no thermal policy, fan state or firmware setting was changed.

## Thermal zones and cooling devices

### thermal_zone0 — acpitz

- Temperature: 52.00°C
- Policy: step_wise
- Mode: enabled

| Trip | Type | Temperature |
|---:|---|---:|
| 0 | critical | 119.00°C |
| 1 | passive | 95.00°C |
| 2 | active | 71.00°C |
| 3 | active | 55.00°C |
| 4 | active | 50.00°C |
| 5 | active | 45.00°C |
| 6 | active | 40.00°C |

| Cooling device | Type | Linked trip | Current state | Device path |
|---|---|---|---:|---|
| cooling_device12 | Processor | 1 (passive, 95.0°C) | 0/3 | /sys/devices/LNXSYSTM:00/LNXSYBUS:00/LNXCPU:07 |
| cooling_device11 | Processor | 1 (passive, 95.0°C) | 0/3 | /sys/devices/LNXSYSTM:00/LNXSYBUS:00/LNXCPU:06 |
| cooling_device2 | Fan | 4 (active, 50.0°C) | 0/1 | /sys/devices/platform/PNP0C0B:02 |
| cooling_device1 | Fan | 3 (active, 55.0°C) | 0/1 | /sys/devices/platform/PNP0C0B:01 |
| cooling_device0 | Fan | 2 (active, 71.0°C) | 0/1 | /sys/devices/platform/PNP0C0B:00 |
| cooling_device10 | Processor | 1 (passive, 95.0°C) | 0/3 | /sys/devices/LNXSYSTM:00/LNXSYBUS:00/LNXCPU:05 |
| cooling_device9 | Processor | 1 (passive, 95.0°C) | 0/3 | /sys/devices/LNXSYSTM:00/LNXSYBUS:00/LNXCPU:04 |
| cooling_device8 | Processor | 1 (passive, 95.0°C) | 0/3 | /sys/devices/LNXSYSTM:00/LNXSYBUS:00/LNXCPU:03 |
| cooling_device7 | Processor | 1 (passive, 95.0°C) | 0/3 | /sys/devices/LNXSYSTM:00/LNXSYBUS:00/LNXCPU:02 |
| cooling_device6 | Processor | 1 (passive, 95.0°C) | 0/3 | /sys/devices/LNXSYSTM:00/LNXSYBUS:00/LNXCPU:01 |
| cooling_device5 | Processor | 1 (passive, 95.0°C) | 0/3 | /sys/devices/LNXSYSTM:00/LNXSYBUS:00/LNXCPU:00 |
| cooling_device4 | Fan | 6 (active, 40.0°C) | 0/1 | /sys/devices/platform/PNP0C0B:04 |
| cooling_device3 | Fan | 5 (active, 45.0°C) | 0/1 | /sys/devices/platform/PNP0C0B:03 |

### thermal_zone1 — SEN2

- Temperature: 39.05°C
- Policy: step_wise
- Mode: enabled

| Trip | Type | Temperature |
|---:|---|---:|
| 0 | passive | -274.00°C |
| 1 | passive | -274.00°C |
| 2 | critical | 80.05°C |
| 3 | hot | 75.05°C |
| 4 | passive | 65.05°C |
| 5 | active | 60.05°C |
| 6 | active | 50.05°C |
| 7 | active | 40.05°C |

### thermal_zone2 — SEN3

- Temperature: 48.05°C
- Policy: step_wise
- Mode: enabled

| Trip | Type | Temperature |
|---:|---|---:|
| 0 | passive | -274.00°C |
| 1 | passive | -274.00°C |
| 2 | critical | 80.05°C |
| 3 | hot | 75.05°C |
| 4 | passive | 65.05°C |

### thermal_zone3 — INT3400 Thermal

- Temperature: 20.00°C
- Policy: step_wise
- Mode: disabled

### thermal_zone4 — TCPU

- Temperature: 52.00°C
- Policy: step_wise
- Mode: enabled

| Trip | Type | Temperature |
|---:|---|---:|
| 0 | critical | 110.05°C |
| 1 | hot | 110.05°C |
| 2 | passive | 110.05°C |
| 3 | active | 109.05°C |
| 4 | active | 107.05°C |
| 5 | active | 106.05°C |
| 6 | active | 104.55°C |
| 7 | active | 103.05°C |

### thermal_zone5 — x86_pkg_temp

- Temperature: 52.00°C
- Policy: step_wise
- Mode: enabled

| Trip | Type | Temperature |
|---:|---|---:|
| 0 | passive | -274.00°C |
| 1 | passive | -274.00°C |

### thermal_zone6 — iwlwifi_1

- Temperature: 53.00°C
- Policy: step_wise
- Mode: enabled

| Trip | Type | Temperature |
|---:|---|---:|
| 0 | passive | -274.00°C |
| 1 | passive | -274.00°C |
| 2 | passive | -274.00°C |
| 3 | passive | -274.00°C |
| 4 | passive | -274.00°C |
| 5 | passive | -274.00°C |
| 6 | passive | -274.00°C |
| 7 | passive | -274.00°C |

## hwmon fan tachometers

No fan RPM input was exposed through inspected hwmon interfaces.

## Review-only observations

The following patterns merit technician review and are not fault verdicts:
- thermal_zone0 (acpitz) reads 52.0°C at/above active trip 4 (50.0°C), while cooling_device2 reports state 0. Review sensor/firmware mapping; this does not establish physical fan failure.
- thermal_zone0 (acpitz) reads 52.0°C at/above active trip 6 (40.0°C), while cooling_device4 reports state 0. Review sensor/firmware mapping; this does not establish physical fan failure.
- thermal_zone0 (acpitz) reads 52.0°C at/above active trip 5 (45.0°C), while cooling_device3 reports state 0. Review sensor/firmware mapping; this does not establish physical fan failure.

## Interpretation limits

- ACPI cooling-device states are not RPM readings and do not establish physical fan count or airflow.
- A zone may not be the sensor used by the embedded controller for physical fan behavior.
- Firmware may independently manage cooling; a state mismatch is not proof of a stopped fan or cooling fault.
- The audit never writes cooling-device state, fan controls, thermal policies or firmware.
