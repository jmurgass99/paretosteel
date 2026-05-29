"""Tests unitarios para la optimización multiobjetivo Pareto (Costo vs CO2) en SteelOptimizerJm."""

import pytest
from fastapi.testclient import TestClient
from steeloptimizerjm.pareto_lca import (
    run_pareto_lca_optimizer,
    ParetoOptimizeInput,
    ParetoGroupSpec,
)
from steeloptimizerjm.api.app import create_app

client = TestClient(create_app())


def test_pareto_lca_optimization_valid():
    """Prueba física del optimizador Pareto NSGA-II Costo vs CO2."""
    # Dos grupos de miembros con requerimientos muy bajos de inercia y área en unidades SI (m4 y m2)
    # para asegurar que siempre encontremos soluciones factibles rápidamente.
    # p.Ix y p.A en el catálogo están almacenados en m4 y m2.
    inp = ParetoOptimizeInput(
        groups=[
            ParetoGroupSpec(
                name="G1_Columnas",
                length_total=40.0,
                min_Ix=1.0e-6,       # m4 (muy bajo, equivalente a 100 cm4)
                min_A=1.0e-4,        # m2 (muy bajo, equivalente a 1 cm2)
                family_filter="IPE",
                country="US",
                steel_grade="secondary_EAF"
            ),
            ParetoGroupSpec(
                name="G2_Vigas",
                length_total=60.0,
                min_Ix=2.0e-6,       # m4 (muy bajo, equivalente a 200 cm4)
                min_A=2.0e-4,        # m2 (muy bajo, equivalente a 2 cm2)
                family_filter="W",
                country="CN",
                steel_grade="primary_BF"
            )
        ],
        population_size=15,
        n_generations=10,
        random_seed=42
    )
    res = run_pareto_lca_optimizer(inp)
    
    assert res.n_solutions > 0
    assert len(res.solutions) > 0
    
    # Verificar una solución
    sol = res.solutions[0]
    assert "G1_Columnas" in sol.assignment
    assert "G2_Vigas" in sol.assignment
    assert sol.total_weight_kg > 0.0
    assert sol.total_cost_USD > 0.0
    assert sol.total_co2_tCO2 > 0.0
    assert sol.feasible is True


def test_api_pareto_lca_endpoint():
    """Prueba del endpoint FastAPI para optimización Pareto Costo vs CO2."""
    payload = {
        "groups": [
            {
                "name": "Columnas",
                "length_total": 50.0,
                "min_Ix": 1.0e-6,
                "min_A": 1.0e-4,
                "family_filter": "W",
                "country": "CL",
                "steel_grade": "average_global"
            }
        ],
        "population_size": 12,
        "n_generations": 8,
        "random_seed": 100
    }
    response = client.post("/api/steel-opt/pareto-lca", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "n_solutions" in data
    assert "solutions" in data
    assert len(data["solutions"]) > 0
    assert "total_cost_USD" in data["solutions"][0]
    assert "total_co2_tCO2" in data["solutions"][0]
    assert "assignment" in data["solutions"][0]
