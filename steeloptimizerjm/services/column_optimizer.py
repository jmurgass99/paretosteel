"""Optimizador de columnas de acero - minimiza peso sujeto a capacidades de compresión AISC 360-16 LRFD.
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Optional
from .beam_optimizer import _load_family_profiles

log = logging.getLogger("steeloptimizerjm.column_optimizer")

@dataclass(frozen=True)
class ColumnOptimizationInput:
    """Entrada del optimizador de columna.

    Atributos:
        L_m: longitud/altura de la columna en metros.
        P_Ed_kN: carga axial de compresión de diseño (kN).
        K: factor de longitud efectiva (default 1.0).
        Fy_MPa: tensión de fluencia (default 345 = A992 Gr 50).
        E_MPa: módulo elástico (default 200000).
        section_family: 'W' | 'HSS' | 'M' | 'S' | 'C' | 'HP' | 'IPE' | 'HEB'.
        max_weight_kg_m: filtro máximo de peso.
    """
    L_m: float
    P_Ed_kN: float
    K: float = 1.0
    Fy_MPa: float = 345.0
    E_MPa: float = 200000.0
    section_family: str = "W"
    max_weight_kg_m: float = 200.0


@dataclass(frozen=True)
class ColumnOptimizationResult:
    """Resultado del optimizador de columna."""
    best_section: str
    weight_kg_m: float
    P_capacity_kN: float
    utilization_P: float
    slenderness: float
    is_feasible: bool
    n_candidates_evaluated: int
    notes: list[str] = field(default_factory=list)


def optimize_column(inp: ColumnOptimizationInput) -> ColumnOptimizationResult:
    """Selecciona el perfil más liviano del catálogo que cumple la resistencia axial AISC.

    Estrategia: ordena el catálogo filtrado por peso ascendente y devuelve el
    primero que cumple la capacidad a compresión según la sección E de AISC 360-16.

    Args:
        inp: ColumnOptimizationInput validada.

    Returns:
        ColumnOptimizationResult con diagnóstico completo.
    """
    if inp.L_m <= 0:
        raise ValueError("L_m debe ser positivo")
    if inp.P_Ed_kN < 0:
        raise ValueError("P_Ed_kN no puede ser negativo")

    profiles = _load_family_profiles(inp.section_family)
    if not profiles:
        raise ValueError(
            f"catalog vacio para familia '{inp.section_family}'"
        )

    # Filtrar por peso máximo y ordenar ascendente
    profiles = [p for p in profiles if p.weight_per_m <= inp.max_weight_kg_m]
    profiles.sort(key=lambda p: p.weight_per_m)

    n_evaluated = 0
    best: Optional[dict] = None

    Fy_Pa = inp.Fy_MPa * 1e6
    E_Pa = inp.E_MPa * 1e6
    L_m = inp.L_m
    K = inp.K

    for p in profiles:
        n_evaluated += 1
        if p.A <= 0 or p.Ix <= 0 or p.Iy <= 0:
            continue

        # Calcula radios de giro r = sqrt(I/A)
        rx = math.sqrt(p.Ix / p.A)
        ry = math.sqrt(p.Iy / p.A)
        r_min = min(rx, ry)

        # Esbeltez KL/r
        kl_over_r = (K * L_m) / r_min

        # Límite de esbeltez recomendado por AISC (200 para compresión)
        if kl_over_r > 200.0:
            continue

        # Fe = pi^2 * E / (kl/r)^2
        Fe = (math.pi ** 2 * E_Pa) / (kl_over_r ** 2)

        # Fcr (AISC E3-2 y E3-3)
        if kl_over_r <= 4.71 * math.sqrt(E_Pa / Fy_Pa):
            Fcr = (0.658 ** (Fy_Pa / Fe)) * Fy_Pa
        else:
            Fcr = 0.877 * Fe

        # Nominal capacity Pn = Fcr * Ag
        Pn_kN = (Fcr * p.A) / 1000.0
        # Design capacity LRFD phi_c = 0.90
        phi_Pn_kN = 0.9 * Pn_kN

        if phi_Pn_kN < inp.P_Ed_kN:
            continue

        util = inp.P_Ed_kN / phi_Pn_kN if phi_Pn_kN > 0 else float("inf")
        best = {
            "name": p.designation,
            "weight": p.weight_per_m,
            "Pn": phi_Pn_kN,
            "util": util,
            "slenderness": kl_over_r,
        }
        break

    if best is None:
        return ColumnOptimizationResult(
            best_section="<NONE_FEASIBLE>",
            weight_kg_m=0.0,
            P_capacity_kN=0.0,
            utilization_P=float("inf"),
            slenderness=0.0,
            is_feasible=False,
            n_candidates_evaluated=n_evaluated,
            notes=[
                f"Ningun perfil de familia {inp.section_family} cumple "
                f"(max_weight={inp.max_weight_kg_m} kg/m, "
                f"P_Ed={inp.P_Ed_kN} kN, L={inp.L_m} m)"
            ],
        )

    return ColumnOptimizationResult(
        best_section=best["name"],
        weight_kg_m=best["weight"],
        P_capacity_kN=best["Pn"],
        utilization_P=best["util"],
        slenderness=best["slenderness"],
        is_feasible=True,
        n_candidates_evaluated=n_evaluated,
        notes=[
            f"Perfil seleccionado: {best['name']} ({best['weight']:.1f} kg/m)",
            f"P_Ed/phi*Pn = {best['util']*100:.1f}%",
            f"Esbeltez KL/r = {best['slenderness']:.1f} (limite <= 200)",
            f"Evaluados {n_evaluated} perfiles del catalog",
        ],
    )
