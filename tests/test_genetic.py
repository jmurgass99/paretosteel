"""Tests para el GA del SteelOptimizer."""
from __future__ import annotations
import pytest

from paretosteel.catalogs import (
    SteelProfile, all_profiles, filter_profiles, ALL_CATALOGS,
)
from paretosteel.genetic import (
    ElementGroup, GAConfig, optimize,
)


def test_catalog_has_profiles():
    profs = all_profiles()
    assert len(profs) >= 20
    assert any(p.designation == "IPE300" for p in profs)
    assert any(p.designation == "W14X90" for p in profs)


def test_filter_by_family():
    ipes = filter_profiles(family="IPE")
    assert all(p.family == "IPE" for p in ipes)
    assert len(ipes) >= 5


def test_filter_by_min_Ix():
    big = filter_profiles(min_Ix=1e-4)
    assert all(p.Ix >= 1e-4 for p in big)


def test_optimize_single_group():
    groups = [ElementGroup(name="cols", length_total=100.0,
                             min_Ix=2.0e-4, min_A=1.0e-2, family_filter="HEB")]
    res = optimize(groups, config=GAConfig(population_size=20, n_generations=30,
                                              random_seed=42))
    assert res.best.weight > 0
    assert res.best.penalty == 0  # con catálogo suficiente debe haber solución factible
    # El perfil elegido debe satisfacer los mínimos
    asgn = dict(res.best.assignment)
    p = next(p for p in all_profiles() if p.designation == asgn["cols"])
    assert p.Ix >= 2.0e-4
    assert p.A >= 1.0e-2


def test_optimize_multi_group():
    groups = [
        ElementGroup(name="cols", length_total=60.0, min_Ix=2.5e-4, family_filter="HEB"),
        ElementGroup(name="beams", length_total=80.0, min_Ix=8.0e-5, family_filter="IPE"),
    ]
    res = optimize(groups, config=GAConfig(population_size=30, n_generations=40,
                                              random_seed=7))
    assert res.best.penalty == 0
    asgn = dict(res.best.assignment)
    assert "cols" in asgn and "beams" in asgn


def test_optimize_infeasible_returns_least_bad():
    """Pide Ix imposible — el GA debe terminar de todas formas (con penalty)."""
    groups = [ElementGroup(name="x", length_total=10.0, min_Ix=1.0, family_filter="IPE")]
    res = optimize(groups, config=GAConfig(population_size=10, n_generations=10,
                                              random_seed=1))
    assert res.best.penalty > 0  # imposible
    assert isinstance(res.history, list)


def test_history_monotonic_nonincreasing():
    """El mejor fitness por generación no debería empeorar (con elitismo)."""
    groups = [ElementGroup(name="x", length_total=50.0, min_Ix=1e-4, family_filter="IPE")]
    res = optimize(groups, config=GAConfig(population_size=20, n_generations=20,
                                              elitism=2, random_seed=99))
    for i in range(1, len(res.history)):
        assert res.history[i] <= res.history[i-1] + 1e-9


def test_optimize_preserves_seed():
    g = [ElementGroup(name="x", length_total=50.0, min_Ix=1e-4, family_filter="IPE")]
    cfg = GAConfig(population_size=15, n_generations=15, random_seed=123)
    r1 = optimize(g, config=cfg)
    r2 = optimize(g, config=cfg)
    assert r1.best.fitness == r2.best.fitness
