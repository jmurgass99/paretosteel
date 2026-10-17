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

from .boq import (
    SteelBoQItem,
    ProfileBoQSummary,
    SteelBoQReport,
    calculate_steel_boq,
)
from .design_codes import (
    LtbEc3Input,
    LtbEc3Result,
    get_ec3_ltb_curve,
    lateral_torsional_buckling_ec3,
    AiscBeamColumnInput,
    AiscBeamColumnResult,
    calc_B1,
    aisc_beam_column_interaction,
)
from .bracing import (
    BracingType,
    SteelBraceSection,
    BracingSystemDemand,
    SteelBraceResult,
    ChevronBeamDemand,
    GussetPlateResult,
    calculate_effective_lengths,
    aisc_e3_critical_stress,
    design_steel_brace,
    calculate_chevron_beam_unbalanced_demand,
    calc_shear_lag_factor_U,
    calc_net_effective_area,
    check_gusset_plate,
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
    "SteelBoQItem",
    "ProfileBoQSummary",
    "SteelBoQReport",
    "calculate_steel_boq",
    "LtbEc3Input",
    "LtbEc3Result",
    "get_ec3_ltb_curve",
    "lateral_torsional_buckling_ec3",
    "AiscBeamColumnInput",
    "AiscBeamColumnResult",
    "calc_B1",
    "aisc_beam_column_interaction",
    "BracingType",
    "SteelBraceSection",
    "BracingSystemDemand",
    "SteelBraceResult",
    "ChevronBeamDemand",
    "GussetPlateResult",
    "calculate_effective_lengths",
    "aisc_e3_critical_stress",
    "design_steel_brace",
    "calculate_chevron_beam_unbalanced_demand",
    "calc_shear_lag_factor_U",
    "calc_net_effective_area",
    "check_gusset_plate",
    "EC3_2022_STEEL_GRADES",
    "Ec3SemiCompactInput",
    "Ec3SemiCompactResult",
    "compute_epsilon_ec3_2022",
    "verify_member_ec3_2022",
    "Aisc360HssH36Input",
    "Aisc360HssH36Result",
    "compute_hss_torsional_constant_c",
    "compute_rect_hss_design_torsion_strength",
    "verify_aisc360_22_hss_h3_6",
]

from . import section_bridge
from .ec3_2022_2g import (
    EC3_2022_STEEL_GRADES,
    Ec3SemiCompactInput,
    Ec3SemiCompactResult,
    compute_epsilon_ec3_2022,
    verify_member_ec3_2022,
)
from .aisc360_22_hss import (
    Aisc360HssH36Input,
    Aisc360HssH36Result,
    compute_hss_torsional_constant_c,
    compute_rect_hss_design_torsion_strength,
    verify_aisc360_22_hss_h3_6,
)



