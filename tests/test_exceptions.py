"""Tests de la jerarquía de excepciones de SteelOptimizerJm."""
from __future__ import annotations
import pytest

from steeloptimizerjm.exceptions import (
    SteelOptimizerError,
    ConfigurationError,
    ConvergenceError,
    DependencyError,
)


def test_base_is_value_error():
    assert issubclass(SteelOptimizerError, ValueError)


def test_subclasses():
    for cls in (ConfigurationError, ConvergenceError, DependencyError):
        assert issubclass(cls, SteelOptimizerError)
        assert issubclass(cls, ValueError)


def test_raise_caught_as_value_error():
    with pytest.raises(ValueError):
        raise ConfigurationError("bad")


def test_raise_caught_as_base():
    with pytest.raises(SteelOptimizerError):
        raise DependencyError("missing")
