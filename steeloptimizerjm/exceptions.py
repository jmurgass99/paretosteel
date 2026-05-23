"""Jerarquía de excepciones de SteelOptimizerJm.

Heredan adicionalmente de ``ValueError`` por compatibilidad hacia atrás.
"""
from __future__ import annotations


class SteelOptimizerError(ValueError):
    """Excepción base del paquete SteelOptimizerJm."""


class ConfigurationError(SteelOptimizerError):
    """Configuración inválida del optimizador (grupos, GA params...)."""


class ConvergenceError(SteelOptimizerError):
    """El optimizador no encontró una solución factible aceptable."""


class DependencyError(SteelOptimizerError):
    """Falta una dependencia opcional (FastAPI, etc.)."""


__all__ = [
    "SteelOptimizerError",
    "ConfigurationError",
    "ConvergenceError",
    "DependencyError",
]
