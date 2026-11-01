"""Tests para mejoras de paretosteel: LTB y deflexión en selector, rutas LCA multi-objetivo, costos por país y optimizador heurístico."""
from __future__ import annotations

import pytest

from paretosteel.beam_selector import BeamDemand, optimize_beam as select_beam
from paretosteel.cost_by_country import get_cost, list_countries
from paretosteel.optimizer import SteelSectionOptimizer
from paretosteel.pareto_lca import ParetoGroupSpec, ParetoOptimizeInput, run_pareto_lca_optimizer
from paretosteel.services.beam_optimizer import BeamOptimizationInput, optimize_beam as optimize_beam_service


def test_beam_selector_ltb_and_deflection():
    demand_braced = BeamDemand(M_kNm=180.0, V_kN=60.0, L_b_m=0.0)
    demand_unbraced = BeamDemand(M_kNm=180.0, V_kN=60.0, L_b_m=6.0, L_span_m=6.0, w_service_kN_m=15.0)
    res_braced = select_beam(demand_braced)
    res_unbraced = select_beam(demand_unbraced)
    assert res_braced.selected is not None
    assert res_unbraced.selected is not None
    assert res_unbraced.selected.chi_LT < 1.0
    assert res_unbraced.selected.deflection_mm > 0.0
    assert res_unbraced.selected.weight_kg_m >= res_braced.selected.weight_kg_m


def test_beam_optimizer_service_plastic_and_ltb():
    res_el = optimize_beam_service(
        BeamOptimizationInput(L_m=6.0, M_Ed_kNm=200.0, V_Ed_kN=80.0, use_plastic_modulus=False)
    )
    res_pl = optimize_beam_service(
        BeamOptimizationInput(L_m=6.0, M_Ed_kNm=200.0, V_Ed_kN=80.0, use_plastic_modulus=True)
    )
    assert res_el.is_feasible and res_pl.is_feasible
    assert res_pl.weight_kg_m <= res_el.weight_kg_m


def test_pareto_lca_route_tradeoff_multi_solution():
    inp = ParetoOptimizeInput(
        groups=[
            ParetoGroupSpec(
                name="Vigas",
                length_total=100.0,
                min_Ix=2000.0,
                min_A=20.0,
                family_filter="IPE",
                country="US",
            )
        ],
        population_size=30,
        n_generations=15,
        random_seed=7,
        allow_route_tradeoff=True,
    )
    out = run_pareto_lca_optimizer(inp)
    assert out.n_solutions >= 2
    assert out.solutions[0].total_cost_USD < out.solutions[-1].total_cost_USD
    assert out.solutions[0].total_co2_tCO2 > out.solutions[-1].total_co2_tCO2


def test_cost_by_country_iso_codes_and_heuristic_optimizer():
    assert "CN" in list_countries()
    assert get_cost("CL").code == "CL"
    assert get_cost("CN").USD_per_ton_raw == pytest.approx(850.0)

    opt = SteelSectionOptimizer()
    res = opt.analyze_beam("HEB240", L=6.0, L_b=1.5, M_Ed=120.0, util_ratio=0.35, fail_mode="CrossSection")
    assert res["action"] == "OPTIMIZE_WEIGHT"
    assert res["proposed_section"] == "IPE360"
    assert res["estimated_weight_savings_pct"] == pytest.approx((83.2 - 57.1) / 83.2 * 100.0, abs=0.05)
