# -*- coding: utf-8 -*-
"""Selector óptimo de vigas de acero (Loadpath) — Pareto multi-objetivo JIT.

Conecta el catálogo unificado de perfiles (`catalog_unified`) con el kernel
NSGA-II compilado (`nsga2_jit.non_dominated_sort_jit`) para elegir, dada una
demanda de momento flector y cortante, el perfil de **mínimo peso que resiste**
las solicitaciones.

Enfoque (honesto sobre lo que es):
    El catálogo es un conjunto DISCRETO y finito de perfiles, por lo que NO se
    corre evolución genética (cruce/mutación): se ENUMERA el catálogo, se calculan
    los dos objetivos por perfil y se aplica la CLASIFICACIÓN NO DOMINADA de
    NSGA-II (el kernel JIT) para extraer la frontera de Pareto. La evolución GA es
    innecesaria para un espacio de decisión finito y enumerable.

Dos objetivos a MINIMIZAR (en conflicto, de ahí el trade-off de Pareto):
    1. Peso (kg/m) — proxy de costo (costo ∝ peso para el mismo grado de acero;
       no se mezclan costos por país).
    2. Ratio de esfuerzo a flexión (demanda/capacidad) — utilización.

Verificación de capacidad:
    - Flexión: momento plástico de sección compacta φ·Mn = φ·Zx·Fy si L_b_m == 0;
      si L_b_m > 0 se evalúa el pandeo lateral-torsional (LTB) reduciendo la
      capacidad nominal mediante χ_LT (EN 1993-1-1 §6.3.2) con It e Iw deducidos
      de la geometría de doble T del perfil.
    - Cortante: Vn = 0.6·Fy·Aw con Aw = h·tw (AISC 360 §G2.1, Cv = 1.0), φv = 0.90.
    - Deflexión ELS opcional: si L_span_m > 0 y w_service_kN_m > 0, verifica
      δ = 5·w·L⁴ / (384·E·Ix) ≤ L / deflection_limit.
    - Factibilidad: flexural_ratio ≤ 1.0, shear_ratio ≤ 1.0 y (si aplica) deflection_ratio ≤ 1.0.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence

import numpy as np

from .catalog_unified import UnifiedSection, all_sections
from .design_codes import (
    LtbEc3Input,
    SteelBeamInput,
    design_beam_compact,
    get_ec3_ltb_curve,
    lateral_torsional_buckling_ec3,
)
from .nsga2_jit import non_dominated_sort_jit

# Densidad del acero estructural (kg/m³) para derivar peso lineal desde el área.
_STEEL_DENSITY_KG_M3 = 7850.0
# Factor de resistencia a cortante (AISC 360 §G1, LRFD).
_PHI_SHEAR = 0.90


@dataclass(frozen=True)
class BeamDemand:
    """Solicitaciones de diseño sobre la viga."""
    M_kNm: float
    V_kN: float = 0.0
    Fy_MPa: float = 345.0   # ASTM A992 / grado común
    code: str = "US"        # base de diseño homogénea (LRFD)
    L_b_m: float = 0.0      # longitud no arriostrada lateralmente (m); 0 = compacta arriostrada
    L_span_m: float = 0.0   # luz para verificación de flecha ELS (m)
    w_service_kN_m: float = 0.0  # carga uniforme de servicio para flecha (kN/m)
    deflection_limit: float = 360.0  # límite L / deflection_limit


@dataclass(frozen=True)
class BeamCandidate:
    """Perfil evaluado frente a la demanda."""
    name: str
    profile_type: str          # "steel_ipe" | "steel_w_shape"
    standard: str              # "ASTM" | "EN"
    weight_kg_m: float
    Mn_design_kNm: float       # capacidad de diseño a flexión (φMn o χ_LT·φMn)
    Vn_design_kN: float        # capacidad de diseño a cortante (φVn)
    flexural_ratio: float      # M_demanda / φMn
    shear_ratio: float         # V_demanda / φVn
    feasible: bool
    deflection_mm: float = 0.0
    deflection_ratio: float = 0.0
    chi_LT: float = 1.0


@dataclass(frozen=True)
class BeamOptimizationResult:
    """Resultado de la optimización multi-objetivo."""
    selected: Optional[BeamCandidate]   # perfil óptimo (None si nada resiste)
    pareto_front: List[str]             # nombres en la frontera de Pareto factible
    candidates: List[BeamCandidate]     # todos los perfiles evaluados
    n_evaluated: int
    n_feasible: int


def _profile_type(sec: UnifiedSection) -> str:
    """Mapea el perfil al tipo que entiende el listener pyRevit / parser."""
    return "steel_ipe" if sec.name.upper().startswith("IPE") else "steel_w_shape"


def _estimate_it_iw_mm(sec: UnifiedSection) -> tuple[float, float]:
    """Estima It (mm⁴) e Iw (mm⁶) para sección doble T simétrica."""
    h_w = max(sec.h_mm - 2.0 * sec.tf_mm, 0.0)
    it_mm4 = (2.0 * sec.bf_mm * (sec.tf_mm ** 3) + h_w * (sec.tw_mm ** 3)) / 3.0
    iz_mm4 = sec.Iy_cm4 * 1.0e4
    h0 = max(sec.h_mm - sec.tf_mm, 1.0)
    iw_mm6 = iz_mm4 * (h0 ** 2) / 4.0
    return max(it_mm4, 1.0), max(iw_mm6, 1.0)


def _evaluate(sec: UnifiedSection, demand: BeamDemand) -> BeamCandidate:
    """Calcula peso y ratios de utilización de un perfil frente a la demanda."""
    # Peso lineal: A[cm²] -> A[m²] (×1e-4) × densidad.
    weight = sec.A_cm2 * 1.0e-4 * _STEEL_DENSITY_KG_M3

    # Flexión base compacta: φMn = φ·Zx·Fy  (Zx[cm³] -> mm³ ×1e3).
    flex = design_beam_compact(
        SteelBeamInput(plastic_modulus_mm3=sec.Zx_cm3 * 1.0e3,
                       Fy_MPa=demand.Fy_MPa, code=demand.code)
    )
    Mn_d = flex.M_design_kNm
    chi_lt = 1.0
    if demand.L_b_m > 0.0:
        it_mm4, iw_mm6 = _estimate_it_iw_mm(sec)
        _, alpha_lt = get_ec3_ltb_curve(sec.h_mm, sec.bf_mm, is_welded=False)
        ltb_res = lateral_torsional_buckling_ec3(
            LtbEc3Input(
                L_unrestrained_mm=demand.L_b_m * 1000.0,
                Iz_mm4=sec.Iy_cm4 * 1.0e4,
                Iw_mm6=iw_mm6,
                It_mm4=it_mm4,
                Wpl_y_mm3=sec.Zx_cm3 * 1.0e3,
                fy_MPa=demand.Fy_MPa,
                alpha_LT=alpha_lt,
            )
        )
        chi_lt = ltb_res.chi_LT
        Mn_d = Mn_d * chi_lt

    flexural_ratio = demand.M_kNm / Mn_d if Mn_d > 0 else float("inf")

    # Cortante: Vn = 0.6·Fy·Aw,  Aw = h·tw (mm²);  N -> kN (÷1e3).
    Aw_mm2 = sec.h_mm * sec.tw_mm
    Vn_d = _PHI_SHEAR * 0.6 * demand.Fy_MPa * Aw_mm2 / 1.0e3
    shear_ratio = demand.V_kN / Vn_d if Vn_d > 0 else float("inf")

    # Deflexión ELS opcional
    defl_mm = 0.0
    defl_ratio = 0.0
    defl_ok = True
    if demand.L_span_m > 0.0 and demand.w_service_kN_m > 0.0:
        E_Pa = 200000.0 * 1.0e6
        Ix_m4 = sec.Ix_cm4 * 1.0e-8
        w_N_m = demand.w_service_kN_m * 1000.0
        defl_m = (5.0 * w_N_m * (demand.L_span_m ** 4)) / (384.0 * E_Pa * Ix_m4)
        defl_mm = defl_m * 1000.0
        lim_mm = (demand.L_span_m * 1000.0) / max(demand.deflection_limit, 1.0)
        defl_ratio = defl_mm / lim_mm if lim_mm > 0 else float("inf")
        defl_ok = defl_ratio <= 1.0

    feasible = flexural_ratio <= 1.0 and shear_ratio <= 1.0 and defl_ok
    return BeamCandidate(
        name=sec.name,
        profile_type=_profile_type(sec),
        standard=sec.standard,
        weight_kg_m=weight,
        Mn_design_kNm=Mn_d,
        Vn_design_kN=Vn_d,
        flexural_ratio=flexural_ratio,
        shear_ratio=shear_ratio,
        feasible=feasible,
        deflection_mm=defl_mm,
        deflection_ratio=defl_ratio,
        chi_LT=chi_lt,
    )


def optimize_beam(
    demand: BeamDemand,
    sections: Optional[Sequence[UnifiedSection]] = None,
    standard: Optional[str] = None,
) -> BeamOptimizationResult:
    """Selecciona el perfil óptimo (mínimo peso factible) por Pareto NSGA-II JIT."""
    if sections is None:
        sections = all_sections()
    if standard is not None:
        std = standard.upper()
        sections = [s for s in sections if s.standard == std]

    candidates = [_evaluate(s, demand) for s in sections]
    feasibles = [c for c in candidates if c.feasible]

    if not feasibles:
        return BeamOptimizationResult(
            selected=None, pareto_front=[], candidates=candidates,
            n_evaluated=len(candidates), n_feasible=0,
        )

    # Objetivos a minimizar: (peso, ratio de flexión). Clasificación no dominada JIT.
    fit = np.array(
        [[c.weight_kg_m, c.flexural_ratio] for c in feasibles], dtype=np.float64
    )
    ranks = non_dominated_sort_jit(fit)
    front = [feasibles[i] for i in range(len(feasibles)) if ranks[i] == 0]

    # De la frontera de Pareto factible, el diseño económico óptimo es el más ligero.
    selected = min(front, key=lambda c: c.weight_kg_m)

    return BeamOptimizationResult(
        selected=selected,
        pareto_front=[c.name for c in front],
        candidates=candidates,
        n_evaluated=len(candidates),
        n_feasible=len(feasibles),
    )


__all__ = [
    "BeamDemand",
    "BeamCandidate",
    "BeamOptimizationResult",
    "optimize_beam",
]
