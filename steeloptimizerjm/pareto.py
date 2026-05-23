"""
Frente de Pareto peso-costo para optimización multiobjetivo.

Dado un conjunto candidato de soluciones (Peso_kg, Costo_USD), extrae
el frente no-dominado. Útil para presentar al ingeniero alternativas
óptimas en lugar de una sola solución escalar.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class Candidate:
    label: str
    weight_kg: float
    cost_USD: float


def pareto_front(candidates: Sequence[Candidate]) -> list[Candidate]:
    """Devuelve el subconjunto no-dominado.

    Una solución A domina a B si A ≤ B en ambos objetivos y A < B en
    al menos uno.
    """
    front: list[Candidate] = []
    for c in candidates:
        dominated = False
        for other in candidates:
            if other is c:
                continue
            if (other.weight_kg <= c.weight_kg
                    and other.cost_USD <= c.cost_USD
                    and (other.weight_kg < c.weight_kg
                         or other.cost_USD < c.cost_USD)):
                dominated = True
                break
        if not dominated:
            front.append(c)
    return sorted(front, key=lambda x: x.weight_kg)


def crowding_distance(front: Sequence[Candidate]) -> list[float]:
    """Distancia de hacinamiento (NSGA-II) para diversidad del frente."""
    if len(front) <= 2:
        return [float("inf")] * len(front)
    n = len(front)
    dist = [0.0] * n
    for key in ("weight_kg", "cost_USD"):
        sorted_idx = sorted(range(n), key=lambda i: getattr(front[i], key))
        dist[sorted_idx[0]] = float("inf")
        dist[sorted_idx[-1]] = float("inf")
        rng = (getattr(front[sorted_idx[-1]], key)
               - getattr(front[sorted_idx[0]], key)) or 1.0
        for i in range(1, n - 1):
            d = (getattr(front[sorted_idx[i + 1]], key)
                 - getattr(front[sorted_idx[i - 1]], key)) / rng
            dist[sorted_idx[i]] += d
    return dist


__all__ = ["Candidate", "pareto_front", "crowding_distance"]
