"""Optimizador de viga de acero - minimiza peso sujeto a capacidades AISC.

Multi-objetivo simplificado: peso minimo + restricciones (M_demand <= phi*Mn,
deflexion <= L/360, cortante V_Ed <= phi_v*Vn). Itera el catalog AISC v16
(SteelProfile en SI) como espacio de soluciones discreto. Backward compatible
con services existentes.

Unidades del catalog (SI): A en m^2, Ix en m^4, weight_per_m en kg/m,
d/bf en m. Por defecto calcula capacidad a flexion con Sx = Ix / (d/2) y
phi = 0.9; si ``use_plastic_modulus=True`` utiliza Zx (o factor de forma 1.12
para perfiles doble T). Si ``L_b_m > 0`` reduce por pandeo lateral-torsional.
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Optional

log = logging.getLogger("paretosteel.beam_optimizer")


@dataclass(frozen=True)
class BeamOptimizationInput:
    """Entrada del optimizador de viga.

    Atributos:
        L_m: luz en metros.
        M_Ed_kNm: momento solicitante (kN.m).
        V_Ed_kN: cortante solicitante (kN).
        Fy_MPa: tension de fluencia (default 345 = A992 Gr 50).
        E_MPa: modulo elastico (default 200000).
        deflection_limit: divisor de L (default 360 -> L/360).
        w_service_kN_m: carga uniforme de servicio (kN/m) para deflexion.
        section_family: 'W' | 'HSS' | 'M' | 'S' | 'C' | 'HP' | 'IPE' | 'HEB'.
        max_weight_kg_m: filtro maximo de peso.
        use_plastic_modulus: si True, usa Zx (o 1.12*Sx) para secciones compactas.
        L_b_m: longitud no arriostrada lateralmente (m); 0.0 = totalmente arriostrada.
    """
    L_m: float
    M_Ed_kNm: float
    V_Ed_kN: float = 0.0
    Fy_MPa: float = 345.0
    E_MPa: float = 200000.0
    deflection_limit: float = 360.0
    w_service_kN_m: float = 10.0
    section_family: str = "W"
    max_weight_kg_m: float = 200.0
    use_plastic_modulus: bool = False
    L_b_m: float = 0.0


@dataclass(frozen=True)
class BeamOptimizationResult:
    """Resultado del optimizador."""
    best_section: str
    weight_kg_m: float
    M_capacity_kNm: float
    utilization_M: float
    deflection_mm: float
    deflection_limit_mm: float
    deflection_OK: bool
    is_feasible: bool
    n_candidates_evaluated: int
    notes: list[str] = field(default_factory=list)


def _load_family_profiles(family: str) -> list:
    """Carga profiles del catalog filtrados por familia.

    Intenta AISC v16 completo primero; si falla cae al subset ``catalogs.py``.
    Devuelve list[SteelProfile] (puede estar vacia).
    """
    family_up = family.upper()
    try:
        from ..catalogs_aisc_full import (
            AISC_W_FULL, AISC_HSS_FULL, AISC_M_FULL,
            AISC_S_FULL, AISC_C_FULL, AISC_HP_FULL,
        )
        full_map = {
            "W": AISC_W_FULL, "HSS": AISC_HSS_FULL, "M": AISC_M_FULL,
            "S": AISC_S_FULL, "C": AISC_C_FULL, "HP": AISC_HP_FULL,
        }
        if family_up in full_map and full_map[family_up]:
            return list(full_map[family_up].values())
    except Exception as exc:  # pragma: no cover - defensive
        log.warning("AISC v16 no disponible: %s", exc)

    # Fallback al subset
    try:
        from ..catalogs import ALL_CATALOGS
        if family_up in ALL_CATALOGS:
            return list(ALL_CATALOGS[family_up].values())
    except Exception as exc:  # pragma: no cover
        log.warning("catalogs.ALL_CATALOGS falla: %s", exc)

    return []


def _ltb_reduction_factor_aisc(p, Fy_MPa: float, E_MPa: float, L_b_m: float) -> float:
    """Factor de reduccion por LTB según AISC 360-22 §F2.2."""
    if L_b_m <= 0.0:
        return 1.0
    Iy = getattr(p, "Iy", 0.0)
    A = getattr(p, "A", 0.0)
    if Iy <= 0.0 or A <= 0.0:
        return 1.0
    ry = math.sqrt(Iy / A)
    Lp = 1.76 * ry * math.sqrt(E_MPa / Fy_MPa)
    Lr = 4.50 * ry * math.sqrt(E_MPa / (0.7 * Fy_MPa))
    if L_b_m <= Lp:
        return 1.0
    if L_b_m <= Lr:
        return max(0.3, 1.0 - 0.3 * (L_b_m - Lp) / max(Lr - Lp, 1e-6))
    return max(0.1, 0.7 * (Lr / L_b_m) ** 2)


def optimize_beam(inp: BeamOptimizationInput) -> BeamOptimizationResult:
    """Selecciona el perfil mas liviano del catalog que cumple M, V y deflexion."""
    if inp.L_m <= 0:
        raise ValueError("L_m debe ser positivo")
    if inp.M_Ed_kNm < 0 or inp.V_Ed_kN < 0:
        raise ValueError("M_Ed y V_Ed no negativos")

    profiles = _load_family_profiles(inp.section_family)
    if not profiles:
        raise ValueError(
            f"catalog vacio para familia '{inp.section_family}'"
        )

    # Filtrar por peso maximo y ordenar ascendente
    profiles = [p for p in profiles if p.weight_per_m <= inp.max_weight_kg_m]
    profiles.sort(key=lambda p: p.weight_per_m)

    deflection_limit_mm = (inp.L_m * 1000.0) / inp.deflection_limit
    n_evaluated = 0
    best: Optional[dict] = None

    Fy_Pa = inp.Fy_MPa * 1e6
    E_Pa = inp.E_MPa * 1e6
    w_N_m = inp.w_service_kN_m * 1000.0
    L_m = inp.L_m

    for p in profiles:
        n_evaluated += 1
        if p.d <= 0 or p.Ix <= 0:
            continue
        Sx_m3 = p.Ix / (p.d / 2.0)
        if inp.use_plastic_modulus:
            Zx_m3 = getattr(p, "Zx", None)
            if not Zx_m3 or Zx_m3 <= 0:
                Zx_m3 = 1.12 * Sx_m3
            W_eff_m3 = Zx_m3
        else:
            W_eff_m3 = Sx_m3

        chi_lt = _ltb_reduction_factor_aisc(p, inp.Fy_MPa, inp.E_MPa, inp.L_b_m)
        Mn_kNm = 0.9 * chi_lt * (Fy_Pa * W_eff_m3) / 1000.0  # phi*Mn en kN.m
        if Mn_kNm < inp.M_Ed_kNm:
            continue

        # Verificacion de cortante cuando V_Ed_kN > 0
        if inp.V_Ed_kN > 0.0:
            tw_m = getattr(p, "tw", 0.0)
            Aw_m2 = p.d * tw_m if tw_m > 0 else 0.35 * p.A
            phi_Vn_kN = 0.9 * 0.6 * (Fy_Pa * Aw_m2) / 1000.0
            if phi_Vn_kN < inp.V_Ed_kN:
                continue

        # Deflexion uniforme apoyada-apoyada: delta = 5*w*L^4 / (384*E*I)
        delta_m = (5.0 * w_N_m * (L_m ** 4)) / (384.0 * E_Pa * p.Ix)
        delta_mm = delta_m * 1000.0
        if delta_mm > deflection_limit_mm:
            continue

        util = inp.M_Ed_kNm / Mn_kNm if Mn_kNm > 0 else float("inf")
        best = {
            "name": p.designation,
            "weight": p.weight_per_m,
            "Mn": Mn_kNm,
            "util": util,
            "delta": delta_mm,
        }
        break

    if best is None:
        return BeamOptimizationResult(
            best_section="<NONE_FEASIBLE>",
            weight_kg_m=0.0,
            M_capacity_kNm=0.0,
            utilization_M=float("inf"),
            deflection_mm=0.0,
            deflection_limit_mm=deflection_limit_mm,
            deflection_OK=False,
            is_feasible=False,
            n_candidates_evaluated=n_evaluated,
            notes=[
                f"Ningun perfil de familia {inp.section_family} cumple "
                f"(max_weight={inp.max_weight_kg_m} kg/m, "
                f"M_Ed={inp.M_Ed_kNm} kN.m, L={inp.L_m} m)"
            ],
        )

    return BeamOptimizationResult(
        best_section=best["name"],
        weight_kg_m=best["weight"],
        M_capacity_kNm=best["Mn"],
        utilization_M=best["util"],
        deflection_mm=best["delta"],
        deflection_limit_mm=deflection_limit_mm,
        deflection_OK=True,
        is_feasible=True,
        n_candidates_evaluated=n_evaluated,
        notes=[
            f"Perfil seleccionado: {best['name']} ({best['weight']:.1f} kg/m)",
            f"M_Ed/phi*Mn = {best['util']*100:.1f}%",
            f"Deflexion = {best['delta']:.2f} mm "
            f"(limite {deflection_limit_mm:.2f} mm)",
            f"Evaluados {n_evaluated} perfiles del catalog",
        ],
    )


__all__ = [
    "BeamOptimizationInput",
    "BeamOptimizationResult",
    "optimize_beam",
]
