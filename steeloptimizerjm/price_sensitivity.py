"""
Análisis de sensibilidad de la solución óptima al precio del acero (idea #19).

Dado un set de candidatos (peso, costo unitario, deriva, etc.) y un rango
de precios, encuentra cómo cambia el óptimo y la robustez de la solución.

Pure-numpy. Multi-code: precios por país pueden venir de cost_lca.COST_USD_PER_TON
pero el análisis es agnóstico al código.
"""
from dataclasses import dataclass
from typing import List, Tuple
import numpy as np


@dataclass(frozen=True)
class Candidate:
    name: str
    weight_kg: float
    unit_cost_USD_per_ton: float
    other_penalty: float = 0.0   # e.g., deriva excedida, fabricación


@dataclass(frozen=True)
class SensitivityResult:
    price_factors: List[float]
    best_candidate_per_factor: List[str]
    switch_points: List[float]      # precios donde cambia el óptimo
    robust_choice: str               # candidato que gana en más rangos


def evaluate_total_cost(c: Candidate, price_factor: float) -> float:
    """Costo total = peso/1000 * unit_cost * price_factor + penalty."""
    return (c.weight_kg / 1000.0) * c.unit_cost_USD_per_ton * price_factor + c.other_penalty


def sensitivity_sweep(
    candidates: List[Candidate],
    price_factors: List[float] | None = None,
) -> SensitivityResult:
    if not candidates:
        raise ValueError("Se requieren candidatos")
    if price_factors is None:
        price_factors = list(np.linspace(0.5, 2.0, 16))
    if any(f <= 0 for f in price_factors):
        raise ValueError("price_factors > 0")
    best_per: List[str] = []
    for f in price_factors:
        costs = [(c.name, evaluate_total_cost(c, f)) for c in candidates]
        best = min(costs, key=lambda t: t[1])
        best_per.append(best[0])
    # switch points
    switches: List[float] = []
    for i in range(1, len(best_per)):
        if best_per[i] != best_per[i - 1]:
            switches.append(price_factors[i])
    # robust = el que más veces gana
    counts: dict = {}
    for n in best_per:
        counts[n] = counts.get(n, 0) + 1
    robust = max(counts.items(), key=lambda kv: kv[1])[0]
    return SensitivityResult(
        price_factors=list(price_factors),
        best_candidate_per_factor=best_per,
        switch_points=switches,
        robust_choice=robust,
    )


def break_even_price(c1: Candidate, c2: Candidate) -> float:
    """Factor de precio que iguala dos candidatos. None si no cruzan en >0."""
    # f * w1/1000*u1 + p1 = f * w2/1000*u2 + p2
    a = (c1.weight_kg / 1000.0) * c1.unit_cost_USD_per_ton - \
        (c2.weight_kg / 1000.0) * c2.unit_cost_USD_per_ton
    b = c2.other_penalty - c1.other_penalty
    if abs(a) < 1e-12:
        return float("inf") if abs(b) > 1e-12 else 0.0
    return b / a
