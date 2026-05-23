"""
SteelOptimizerJm - AI Copilot for structural steel optimization and frame design.
"""
__version__ = "1.0.0"

from .catalogs import SteelProfile, all_profiles, filter_profiles
from .genetic import optimize, GAConfig, GAResult, ElementGroup
from .nsga2_jit import (
    fast_dominates,
    non_dominated_sort_jit,
    calculate_crowding_distance_jit,
)
from .exceptions import (
    SteelOptimizerError,
    ConfigurationError,
    ConvergenceError,
    DependencyError,
)
from .diff_evolution import (
    optimize_beam_de,
    optimize_column_de,
    pareto_weight_cost,
    DEBeamResult,
    DEColumnResult,
    ParetoResult,
)

__all__ = [
    "SteelProfile",
    "all_profiles",
    "filter_profiles",
    "optimize",
    "GAConfig",
    "GAResult",
    "ElementGroup",
    "fast_dominates",
    "non_dominated_sort_jit",
    "calculate_crowding_distance_jit",
    "SteelOptimizerError",
    "ConfigurationError",
    "ConvergenceError",
    "DependencyError",
    "optimize_beam_de",
    "optimize_column_de",
    "pareto_weight_cost",
    "DEBeamResult",
    "DEColumnResult",
    "ParetoResult",
]
