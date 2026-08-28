"""steeloptimizerjm.reuse
=========================
Motor de emparejamiento de reuso y cálculo de ahorro de huella de carbono de acero.
Consolidado desde CircularSteelJm.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class DemandItem:
    id: str
    required: float


@dataclass(frozen=True)
class InventoryItem:
    id: str
    capacity: float
    embodied_carbon_saved: float = 0.0


@dataclass(frozen=True)
class Assignment:
    demand_id: str
    required: float
    inventory_id: str | None
    capacity: float | None
    embodied_carbon_saved: float | None
    matched: bool


@dataclass(frozen=True)
class MatchResult:
    assignments: tuple[Assignment, ...]
    reuse_ratio: float
    total_embodied_carbon_saved: float
    matched_demands: int
    unmatched_demands: int


def match_reuse(demands: Sequence[DemandItem], inventory: Sequence[InventoryItem]) -> MatchResult:
    """Algoritmo greedy determinista de emparejamiento para reuso de perfiles."""
    if not demands:
        raise ValueError("demand must contain at least one item")
    if not inventory:
        raise ValueError("inventory must contain at least one item")

    available = list(enumerate(inventory))
    assignments: list[Assignment] = []
    total_required = 0.0
    matched_required = 0.0
    carbon_saved = 0.0
    n_matched = 0

    for d in demands:
        total_required += d.required
        best_pos = None
        best_key = None
        for pos, (orig_idx, inv) in enumerate(available):
            if inv.capacity >= d.required:
                key = (inv.capacity, orig_idx)
                if best_key is None or key < best_key:
                    best_key = key
                    best_pos = pos

        if best_pos is None:
            assignments.append(
                Assignment(
                    demand_id=d.id,
                    required=d.required,
                    inventory_id=None,
                    capacity=None,
                    embodied_carbon_saved=None,
                    matched=False,
                )
            )
        else:
            orig_idx, inv = available.pop(best_pos)
            matched_required += d.required
            carbon_saved += inv.embodied_carbon_saved
            n_matched += 1
            assignments.append(
                Assignment(
                    demand_id=d.id,
                    required=d.required,
                    inventory_id=inv.id,
                    capacity=inv.capacity,
                    embodied_carbon_saved=inv.embodied_carbon_saved,
                    matched=True,
                )
            )

    reuse_ratio = matched_required / total_required if total_required > 0 else 0.0
    return MatchResult(
        assignments=tuple(assignments),
        reuse_ratio=reuse_ratio,
        total_embodied_carbon_saved=carbon_saved,
        matched_demands=n_matched,
        unmatched_demands=len(demands) - n_matched,
    )


__all__ = ["DemandItem", "InventoryItem", "Assignment", "MatchResult", "match_reuse"]
