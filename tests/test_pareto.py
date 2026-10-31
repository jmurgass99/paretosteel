"""Tests para Pareto front."""
import pytest

from paretosteel.pareto import Candidate, crowding_distance, pareto_front


def test_front_basico():
    cands = [
        Candidate("A", weight_kg=100, cost_USD=500),
        Candidate("B", weight_kg=150, cost_USD=400),  # mejor en costo
        Candidate("C", weight_kg=120, cost_USD=600),  # dominada por A
        Candidate("D", weight_kg=80, cost_USD=700),   # mejor en peso
    ]
    front = pareto_front(cands)
    labels = {c.label for c in front}
    assert "C" not in labels
    assert "A" in labels and "B" in labels and "D" in labels


def test_front_unico():
    cands = [Candidate("X", weight_kg=100, cost_USD=500)]
    assert pareto_front(cands) == cands


def test_crowding_extremos_inf():
    front = [
        Candidate("A", 100, 500),
        Candidate("B", 150, 400),
        Candidate("C", 200, 350),
    ]
    d = crowding_distance(front)
    assert d[0] == float("inf") or d[2] == float("inf")
