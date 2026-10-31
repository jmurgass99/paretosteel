import pytest
from paretosteel.services.column_optimizer import (
    ColumnOptimizationInput,
    ColumnOptimizationResult,
    optimize_column,
)

def test_optimize_column_feasible():
    # A standard compression demand of 1500 kN, length 3.5m
    inp = ColumnOptimizationInput(
        L_m=3.5,
        P_Ed_kN=1500.0,
        K=1.0,
        Fy_MPa=345.0,
        section_family="W",
        max_weight_kg_m=150.0,
    )
    res = optimize_column(inp)
    assert res.is_feasible
    assert res.best_section != "<NONE_FEASIBLE>"
    assert res.weight_kg_m <= 150.0
    assert res.P_capacity_kN >= 1500.0
    assert res.utilization_P <= 1.0
    assert res.slenderness <= 200.0
    assert len(res.notes) > 0

def test_optimize_column_infeasible():
    # Extremely high load, should be infeasible for limited weight
    inp = ColumnOptimizationInput(
        L_m=5.0,
        P_Ed_kN=200000.0,  # 200 MN
        K=1.0,
        Fy_MPa=345.0,
        section_family="W",
        max_weight_kg_m=50.0,
    )
    res = optimize_column(inp)
    assert not res.is_feasible
    assert res.best_section == "<NONE_FEASIBLE>"
    assert res.utilization_P == float("inf")

def test_optimize_column_invalid_inputs():
    with pytest.raises(ValueError, match="L_m debe ser positivo"):
        optimize_column(ColumnOptimizationInput(L_m=0.0, P_Ed_kN=100.0))
        
    with pytest.raises(ValueError, match="P_Ed_kN no puede ser negativo"):
        optimize_column(ColumnOptimizationInput(L_m=3.0, P_Ed_kN=-50.0))
