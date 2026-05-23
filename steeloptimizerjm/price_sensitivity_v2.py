"""Price sensitivity v2 - extiende price_sensitivity.py original con:

- Sensibilidad multi-variable (acero + montaje + transporte)
- Monte Carlo simple para distribuciones triangular/normal
- Output con percentiles P10/P50/P90
"""
from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass(frozen=True)
class PriceSensitivityV2Input:
    base_tons: float
    base_steel_usd_ton: float
    base_erection_usd_ton: float
    base_transport_usd_ton: float
    sigma_steel_pct: float = 0.15
    sigma_erection_pct: float = 0.10
    sigma_transport_pct: float = 0.25
    n_samples: int = 1000
    seed: int = 42


@dataclass(frozen=True)
class PriceSensitivityV2Result:
    P10_usd: float
    P50_usd: float
    P90_usd: float
    mean_usd: float


def monte_carlo(inp: PriceSensitivityV2Input) -> PriceSensitivityV2Result:
    rng = random.Random(inp.seed)
    samples = []
    for _ in range(inp.n_samples):
        s = inp.base_steel_usd_ton * (1 + rng.gauss(0, inp.sigma_steel_pct))
        e = inp.base_erection_usd_ton * (1 + rng.gauss(0, inp.sigma_erection_pct))
        t = inp.base_transport_usd_ton * (1 + rng.gauss(0, inp.sigma_transport_pct))
        samples.append((s + e + t) * inp.base_tons)
    samples.sort()
    n = len(samples)

    def pct(p: float) -> float:
        idx = max(0, min(n - 1, int(p * n)))
        return samples[idx]

    mean = sum(samples) / n
    return PriceSensitivityV2Result(pct(0.10), pct(0.50), pct(0.90), mean)


__all__ = ["PriceSensitivityV2Input", "PriceSensitivityV2Result", "monte_carlo"]
