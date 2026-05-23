"""Tests del servicio de optimización."""
from __future__ import annotations
import pytest

from steeloptimizerjm.exceptions import ConfigurationError
from steeloptimizerjm.services.optimizer import (
    GroupSpec, OptimizerInput, run_ga_optimizer, list_catalog,
)


def test_catalog_listing_all():
    cat = list_catalog()
    assert len(cat) >= 20
    designations = {p["designation"] for p in cat}
    assert "IPE300" in designations
    assert "W14X90" in designations


def test_catalog_filter_family():
    ipes = list_catalog(family="IPE")
    assert ipes and all(p["family"] == "IPE" for p in ipes)


def test_optimizer_runs_feasible():
    inp = OptimizerInput(
        groups=[GroupSpec(name="cols", length_total=100.0,
                            min_Ix=2.0e-4, min_A=1.0e-2,
                            family_filter="HEB")],
        population_size=20, n_generations=20, random_seed=42,
    )
    res = run_ga_optimizer(inp)
    assert res.feasible
    assert "cols" in res.assignment
    assert res.weight > 0


def test_optimizer_invalid_no_groups():
    with pytest.raises(ConfigurationError):
        run_ga_optimizer(OptimizerInput(groups=[]))


def test_optimizer_invalid_duplicate_names():
    with pytest.raises(ConfigurationError):
        run_ga_optimizer(OptimizerInput(
            groups=[GroupSpec(name="x", length_total=10),
                    GroupSpec(name="x", length_total=20)],
        ))


def test_optimizer_invalid_rates():
    with pytest.raises(ConfigurationError):
        run_ga_optimizer(OptimizerInput(
            groups=[GroupSpec(name="x", length_total=10)],
            crossover_rate=1.5,
        ))
