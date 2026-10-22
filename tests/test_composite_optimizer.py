"""
Test suite for SteelOptimizerJm Composite Beam Optimizer.
Verifies Pareto multi-objective optimization, discrete catalog evaluation,
standard filtering (ASTM / EN), infeasible demand handling, and memo generation.
"""

import pytest
from steeloptimizerjm.composite_optimizer import (
    CompositeOptimizationDemand,
    CompositeCandidate,
    CompositeOptimizationResult,
    optimize_composite_beam,
)


class TestCompositeBeamOptimizer:
    def test_optimal_beam_selection_aisc(self):
        # Realistic office / light commercial floor: 8 m span, 2.8 m spacing, 3.5 kPa live load
        demand = CompositeOptimizationDemand(
            span_m=8.0,
            spacing_m=2.8,
            dead_load_superimposed_kpa=1.2,
            live_load_kpa=3.5,
            slab_thickness_mm=120.0,
            deck_height_mm=50.0,
            concrete_fc_MPa=28.0,
            standard="AISC_360_16",
        )

        res = optimize_composite_beam(demand)

        assert res.n_evaluated > 0
        assert res.n_feasible > 0
        assert res.selected is not None
        assert res.selected.is_feasible is True
        assert res.selected.governing_dcr <= 1.0

        # Selected candidate must be the lightest in the Pareto front
        assert res.selected == res.pareto_front[0]
        assert all(res.selected.weight_kg_m <= p.weight_kg_m for p in res.pareto_front)

        # Memo should format without error
        memo = res.explanation_memo()
        assert res.selected.section_name in memo
        assert "AISC 360-16" in memo
        assert "Alternativas en la Frontera de Pareto" in memo

    def test_filter_by_standard_astm_and_en(self):
        demand_astm = CompositeOptimizationDemand(
            span_m=7.5,
            spacing_m=2.5,
            dead_load_superimposed_kpa=1.0,
            live_load_kpa=4.0,
            catalog_filter_standard="ASTM",
        )
        res_astm = optimize_composite_beam(demand_astm)
        assert all(c.standard == "ASTM" for c in res_astm.all_evaluated)
        assert res_astm.selected is not None
        assert res_astm.selected.section_name.startswith("W")

        demand_en = CompositeOptimizationDemand(
            span_m=7.5,
            spacing_m=2.5,
            dead_load_superimposed_kpa=1.0,
            live_load_kpa=4.0,
            catalog_filter_standard="EN",
            standard="EUROCODE_4",
        )
        res_en = optimize_composite_beam(demand_en)
        assert all(c.standard == "EN" for c in res_en.all_evaluated)
        assert res_en.selected is not None
        assert any(res_en.selected.section_name.startswith(p) for p in ["IPE", "HEA", "HEB"])

    def test_pareto_frontier_tradeoff_invariants(self):
        """Verifies that the Pareto front trades off weight vs governing DCR."""
        demand = CompositeOptimizationDemand(
            span_m=8.5,
            spacing_m=3.0,
            dead_load_superimposed_kpa=1.5,
            live_load_kpa=5.0,
        )
        res = optimize_composite_beam(demand)
        assert len(res.pareto_front) >= 1

        # In a Pareto front sorted by weight ascending:
        # As weight strictly increases, governing DCR must strictly decrease!
        for i in range(len(res.pareto_front) - 1):
            curr_cand = res.pareto_front[i]
            next_cand = res.pareto_front[i + 1]
            if next_cand.weight_kg_m > curr_cand.weight_kg_m:
                assert next_cand.governing_dcr < curr_cand.governing_dcr

    def test_infeasible_demand_returns_none_cleanly(self):
        """Massive overloaded span that no catalog profile can support."""
        demand = CompositeOptimizationDemand(
            span_m=22.0,  # 22 m span
            spacing_m=6.0,
            dead_load_superimposed_kpa=5.0,
            live_load_kpa=25.0,  # Extreme heavy loading
        )
        res = optimize_composite_beam(demand)
        assert res.n_feasible == 0
        assert res.selected is None
        assert len(res.pareto_front) == 0

        memo = res.explanation_memo()
        assert "Ningún perfil del catálogo resultó factible" in memo

    def test_empty_catalog_filter_raises_value_error(self):
        demand = CompositeOptimizationDemand(
            span_m=6.0,
            spacing_m=2.0,
            dead_load_superimposed_kpa=1.0,
            live_load_kpa=2.0,
        )
        with pytest.raises(ValueError, match="No se encontraron perfiles"):
            optimize_composite_beam(demand, sections=[])
