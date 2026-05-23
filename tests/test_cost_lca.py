"""Tests cost_lca."""
from steeloptimizerjm.cost_lca import CostLCAInput, evaluate_cost_lca


def test_pais_default():
    r = evaluate_cost_lca(CostLCAInput(weight_kg=1000, country="CL"))
    assert r["cost_USD"] == 1450.0
    assert r["co2_emissions_tCO2"] == 1.85


def test_low_carbon():
    r = evaluate_cost_lca(CostLCAInput(
        weight_kg=1000, country="DE", steel_grade="low_carbon",
    ))
    assert r["co2_emissions_tCO2"] == 0.40


def test_default_fallback():
    r = evaluate_cost_lca(CostLCAInput(weight_kg=500, country="ZZ"))
    assert r["cost_per_ton_USD"] == 1300.0
