#!/usr/bin/env python3
"""ATOCIA physics baseline: exact one-node lumped thermal RC model.

Passive/offline model only. It does not read sensors, control fans, or change
system settings. Assumes constant power and ambient temperature per step.
"""
from __future__ import annotations
from dataclasses import dataclass
import math
from typing import Iterable, Sequence


@dataclass(frozen=True)
class ThermalState:
    time_s: float
    temperature_c: float


@dataclass(frozen=True)
class SingleNodeRC:
    """Lumped thermal mass with R_th [K/W] and C_th [J/K].

    Energy balance: C_th * dT/dt = P_in - (T - T_ambient) / R_th.
    The exact zero-order-hold update is used for numerical stability.
    """
    resistance_k_per_w: float
    capacitance_j_per_k: float

    def __post_init__(self) -> None:
        if not math.isfinite(self.resistance_k_per_w) or self.resistance_k_per_w <= 0:
            raise ValueError("thermal resistance must be finite and > 0 K/W")
        if not math.isfinite(self.capacitance_j_per_k) or self.capacitance_j_per_k <= 0:
            raise ValueError("thermal capacitance must be finite and > 0 J/K")

    @property
    def time_constant_s(self) -> float:
        return self.resistance_k_per_w * self.capacitance_j_per_k

    def equilibrium_temperature_c(self, power_w: float, ambient_c: float) -> float:
        self._validate_inputs(power_w, ambient_c, 1.0)
        return ambient_c + self.resistance_k_per_w * power_w

    def step(self, temperature_c: float, power_w: float,
             ambient_c: float, dt_s: float) -> float:
        """Advance one interval with constant power and ambient conditions."""
        self._validate_inputs(power_w, ambient_c, dt_s)
        if not math.isfinite(temperature_c):
            raise ValueError("temperature must be finite")
        decay = math.exp(-dt_s / self.time_constant_s)
        equilibrium = ambient_c + self.resistance_k_per_w * power_w
        return equilibrium + (temperature_c - equilibrium) * decay

    def simulate(self, initial_temperature_c: float,
                 samples: Iterable[tuple[float, float, float]]) -> list[ThermalState]:
        """Simulate samples of (time_s, power_w, ambient_c), zero-order-held.

        The first sample defines the initial timestamp and conditions. Each
        subsequent sample's power/ambient apply over the interval ending there.
        """
        rows = list(samples)
        if not rows:
            raise ValueError("at least one sample is required")
        t0, p0, a0 = rows[0]
        self._validate_inputs(p0, a0, 1.0)
        if not math.isfinite(t0) or not math.isfinite(initial_temperature_c):
            raise ValueError("initial time and temperature must be finite")
        out = [ThermalState(float(t0), float(initial_temperature_c))]
        temp = float(initial_temperature_c)
        previous_t = float(t0)
        for timestamp, power, ambient in rows[1:]:
            if not math.isfinite(timestamp) or timestamp <= previous_t:
                raise ValueError("timestamps must be finite and strictly increasing")
            dt = float(timestamp) - previous_t
            temp = self.step(temp, float(power), float(ambient), dt)
            out.append(ThermalState(float(timestamp), temp))
            previous_t = float(timestamp)
        return out

    @staticmethod
    def _validate_inputs(power_w: float, ambient_c: float, dt_s: float) -> None:
        if not math.isfinite(power_w):
            raise ValueError("power must be finite")
        if not math.isfinite(ambient_c):
            raise ValueError("ambient temperature must be finite")
        if not math.isfinite(dt_s) or dt_s <= 0:
            raise ValueError("time step must be finite and > 0 s")


def predict_constant_power(model: SingleNodeRC, temperature_c: float,
                           power_w: float, ambient_c: float,
                           horizon_s: float) -> float:
    """Scenario forecast assuming future power and ambient remain constant.

    This is a conditional physical projection, not a workload forecast.
    """
    return model.step(temperature_c, power_w, ambient_c, horizon_s)
