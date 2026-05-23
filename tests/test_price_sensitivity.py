"""Tests sensibilidad al precio."""
import pytest
from steeloptimizerjm.price_sensitivity import (
    Candidate, sensitivity_sweep, break_even_price, evaluate_total_cost,
)


def _cands():
    return [
        Candidate("W14x90", weight_kg=134.0, unit_cost_USD_per_ton=1200.0),
        Candidate("W14x82", weight_kg=122.0, unit_cost_USD_per_ton=1200.0),
        Candidate("W14x68_with_stiffener", weight_kg=101.0,
                  unit_cost_USD_per_ton=1200.0, other_penalty=50.0),
    ]


def test_sensitivity_basic():
    r = sensitivity_sweep(_cands())
    assert len(r.best_candidate_per_factor) == 16
    assert r.robust_choice in {"W14x90", "W14x82", "W14x68_with_stiffener"}


def test_eval_total_cost():
    c = Candidate("X", 1000.0, 1000.0, other_penalty=10.0)
    assert evaluate_total_cost(c, 1.0) == pytest.approx(1010.0)
    assert evaluate_total_cost(c, 2.0) == pytest.approx(2010.0)


def test_break_even_simple():
    a = Candidate("a", 1000.0, 1000.0, 0.0)
    b = Candidate("b", 800.0, 1000.0, 200.0)
    f = break_even_price(a, b)
    # 1000*f = 800*f + 200 -> 200*f = 200 -> f=1
    assert f == pytest.approx(1.0)


def test_invalid_input():
    with pytest.raises(ValueError):
        sensitivity_sweep([])
    with pytest.raises(ValueError):
        sensitivity_sweep(_cands(), price_factors=[0.0, 1.0])
