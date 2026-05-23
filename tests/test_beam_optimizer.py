"""Tests del optimizador de viga (services/beam_optimizer.py)."""
from __future__ import annotations

import pytest

from steeloptimizerjm.services.beam_optimizer import (
    BeamOptimizationInput,
    optimize_beam,
)


def test_optimize_beam_typical_finds_w_section() -> None:
    res = optimize_beam(BeamOptimizationInput(
        L_m=6.0, M_Ed_kNm=200.0, w_service_kN_m=10.0,
        section_family="W", max_weight_kg_m=200.0,
    ))
    assert res.is_feasible, res.notes
    assert res.best_section.upper().startswith("W")
    assert res.utilization_M <= 1.0
    assert res.weight_kg_m > 0
    assert res.deflection_OK


def test_optimize_beam_impossible_returns_infeasible() -> None:
    """Demanda extrema imposible con max_weight muy bajo."""
    res = optimize_beam(BeamOptimizationInput(
        L_m=10.0, M_Ed_kNm=10000.0, w_service_kN_m=50.0,
        section_family="W", max_weight_kg_m=50.0,
    ))
    assert not res.is_feasible
    assert res.best_section == "<NONE_FEASIBLE>"


def test_optimize_beam_invalid_L_m() -> None:
    with pytest.raises(ValueError):
        optimize_beam(BeamOptimizationInput(
            L_m=-5.0, M_Ed_kNm=100.0, w_service_kN_m=10.0,
            section_family="W",
        ))


def test_optimize_beam_invalid_negative_moment() -> None:
    with pytest.raises(ValueError):
        optimize_beam(BeamOptimizationInput(
            L_m=6.0, M_Ed_kNm=-1.0, w_service_kN_m=10.0,
            section_family="W",
        ))


def test_optimize_beam_higher_load_higher_weight() -> None:
    r1 = optimize_beam(BeamOptimizationInput(
        L_m=6.0, M_Ed_kNm=100.0, w_service_kN_m=8.0,
        section_family="W",
    ))
    r2 = optimize_beam(BeamOptimizationInput(
        L_m=6.0, M_Ed_kNm=500.0, w_service_kN_m=20.0,
        section_family="W",
    ))
    if r1.is_feasible and r2.is_feasible:
        assert r2.weight_kg_m >= r1.weight_kg_m


def test_optimize_beam_unknown_family_raises() -> None:
    with pytest.raises(ValueError):
        optimize_beam(BeamOptimizationInput(
            L_m=6.0, M_Ed_kNm=100.0, w_service_kN_m=10.0,
            section_family="ZZZ",
        ))


def test_optimize_beam_evaluates_some_candidates() -> None:
    res = optimize_beam(BeamOptimizationInput(
        L_m=6.0, M_Ed_kNm=200.0, w_service_kN_m=10.0,
        section_family="W", max_weight_kg_m=200.0,
    ))
    assert res.n_candidates_evaluated >= 1
