"""Golden test para optimización multiobjetivo Pareto Coste/CO2 con NSGA-II.

Requisitos:
1. Toda solución del frente de Pareto resultante es factible y cumple las restricciones estructurales.
2. Ninguna solución del frente devuelto domina a otra del mismo frente (verificación estricta de dominancia de Pareto).
"""
from __future__ import annotations

import pytest
from steeloptimizerjm.pareto_lca import (
    ParetoGroupSpec,
    ParetoOptimizeInput,
    run_pareto_lca_optimizer,
)


def test_golden_nsga2_pareto_front_feasibility_and_non_dominance():
    """GOLDEN. Validación de factibilidad y no-dominancia estricta en el frente de Pareto NSGA-II."""
    groups = [
        ParetoGroupSpec(
            name="Vigas_Ppal",
            length_total=60.0,
            min_Ix=15000.0,  # cm4
            min_A=45.0,      # cm2
            family_filter="IPE",
            country="DE",
            steel_grade="average_global",
        ),
        ParetoGroupSpec(
            name="Columnas",
            length_total=36.0,
            min_Ix=12000.0,  # cm4
            min_A=60.0,      # cm2
            family_filter="HEB",
            country="DE",
            steel_grade="low_carbon",
        ),
    ]

    inp = ParetoOptimizeInput(
        groups=groups,
        population_size=30,
        n_generations=20,
        random_seed=123,
    )

    res = run_pareto_lca_optimizer(inp)

    assert res.n_solutions > 0
    assert len(res.solutions) == res.n_solutions

    # 1. Toda solución del frente es factible
    for sol in res.solutions:
        assert sol.feasible is True
        assert sol.total_cost_USD > 0.0
        assert sol.total_co2_tCO2 > 0.0
        assert "Vigas_Ppal" in sol.assignment
        assert "Columnas" in sol.assignment

    # 2. Verificación formal de no-dominancia estricta entre todos los pares del frente
    # Sean dos soluciones A y B del frente: A no domina a B y B no domina a A.
    for i, a in enumerate(res.solutions):
        for j, b in enumerate(res.solutions):
            if i == j:
                continue

            # a domina a b si: Cost_a <= Cost_b AND CO2_a <= CO2_b AND (Cost_a < Cost_b OR CO2_a < CO2_b)
            a_dominates_b = (
                (a.total_cost_USD <= b.total_cost_USD)
                and (a.total_co2_tCO2 <= b.total_co2_tCO2)
                and ((a.total_cost_USD < b.total_cost_USD) or (a.total_co2_tCO2 < b.total_co2_tCO2))
            )
            assert not a_dominates_b, (
                f"Inconsistencia en el frente de Pareto: solución {i} ({a.total_cost_USD:.1f}, {a.total_co2_tCO2:.2f}) "
                f"domina a solución {j} ({b.total_cost_USD:.1f}, {b.total_co2_tCO2:.2f})"
            )
