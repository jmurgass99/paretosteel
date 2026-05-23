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

Verificación de capacidad (SIMPLIFICACIONES declaradas):
    - Flexión: momento plástico de sección compacta  φ·Mn = φ·Zx·Fy
      (AISC 360 §F2.1 vía `design_codes.design_beam_compact`), ASUMIENDO
      arriostramiento lateral adecuado (Lb ≤ Lp). NO es el pandeo lateral-torsional
      (LTB, §F2.2) completo: `UnifiedSection` no expone rts/J/Cw/Sx. Se puede
      extender cuando esas propiedades estén disponibles en el catálogo.
    - Cortante: Vn = 0.6·Fy·Aw con Aw = h·tw (AISC 360 §G2.1, Cv = 1.0), φv = 0.90.
    - Factibilidad: flexural_ratio ≤ 1.0 Y shear_ratio ≤ 1.0.
    - Todos los perfiles se comparan con el MISMO código (LRFD por defecto) para que
      la optimización use una base homogénea.

Selección final: de la frontera de Pareto factible (rango 0) se toma el perfil de
MENOR peso (el diseño económico óptimo que cumple).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence

import numpy as np

from .catalog_unified import UnifiedSection, all_sections
from .design_codes import SteelBeamInput, design_beam_compact
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


@dataclass(frozen=True)
class BeamCandidate:
    """Perfil evaluado frente a la demanda."""
    name: str
    profile_type: str          # "steel_ipe" | "steel_w_shape"
    standard: str              # "ASTM" | "EN"
    weight_kg_m: float
    Mn_design_kNm: float       # capacidad de diseño a flexión (φMn)
    Vn_design_kN: float        # capacidad de diseño a cortante (φVn)
    flexural_ratio: float      # M_demanda / φMn
    shear_ratio: float         # V_demanda / φVn
    feasible: bool


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


def _evaluate(sec: UnifiedSection, demand: BeamDemand) -> BeamCandidate:
    """Calcula peso y ratios de utilización de un perfil frente a la demanda."""
    # Peso lineal: A[cm²] -> A[m²] (×1e-4) × densidad.
    weight = sec.A_cm2 * 1.0e-4 * _STEEL_DENSITY_KG_M3

    # Flexión: φMn = φ·Zx·Fy  (Zx[cm³] -> mm³ ×1e3).
    flex = design_beam_compact(
        SteelBeamInput(plastic_modulus_mm3=sec.Zx_cm3 * 1.0e3,
                       Fy_MPa=demand.Fy_MPa, code=demand.code)
    )
    Mn_d = flex.M_design_kNm
    flexural_ratio = demand.M_kNm / Mn_d if Mn_d > 0 else float("inf")

    # Cortante: Vn = 0.6·Fy·Aw,  Aw = h·tw (mm²);  N -> kN (÷1e3).
    Aw_mm2 = sec.h_mm * sec.tw_mm
    Vn_d = _PHI_SHEAR * 0.6 * demand.Fy_MPa * Aw_mm2 / 1.0e3
    shear_ratio = demand.V_kN / Vn_d if Vn_d > 0 else float("inf")

    feasible = flexural_ratio <= 1.0 and shear_ratio <= 1.0
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
    )


def optimize_beam(
    demand: BeamDemand,
    sections: Optional[Sequence[UnifiedSection]] = None,
    standard: Optional[str] = None,
) -> BeamOptimizationResult:
    """Selecciona el perfil óptimo (mínimo peso factible) por Pareto NSGA-II JIT.

    Args:
        demand: solicitaciones M, V (+ Fy, code opcionales).
        sections: catálogo a considerar; por defecto `catalog_unified.all_sections()`.
        standard: filtra por norma ("ASTM" o "EN"); None = ambas.

    Returns:
        BeamOptimizationResult con el perfil seleccionado, la frontera de Pareto
        factible y todos los candidatos evaluados. `selected` es None si ningún
        perfil del catálogo resiste la demanda.
    """
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
