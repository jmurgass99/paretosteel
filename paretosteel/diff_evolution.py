"""GA hibrido con scipy.differential_evolution para optimizacion de secciones de acero.

Wrapper sobre ``scipy.optimize.differential_evolution`` que opera sobre el
espacio *continuo* de indices del catalogo de perfiles. El gen es un indice
real en [0, len(catalog)-1]; se redondea al entero mas cercano para evaluar
el perfil correspondiente.

Funciones principales:
    - ``optimize_beam_de``:  viga simplemente apoyada, minimiza peso total
      sujeto a restricciones AISC (flexion phi*Mn >= Mu, cortante phi*Vn >= Vu,
      deflexion <= L/360).
    - ``optimize_column_de``:  columna a compresion, minimiza peso total
      sujeto a restriccion AISC E3 (phi*Pn >= Pu, KL/r <= 200).
    - ``pareto_weight_cost``:  genera frontera Pareto peso-costo mediante
      barrido de pesos alpha*peso + (1-alpha)*costo.

Unidades del catalogo (SI): A m^2, Ix m^4, weight_per_m kg/m, d/bf m.
Modulo de seccion elastico Sx = Ix/(d/2).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional, Sequence

from scipy.optimize import differential_evolution

from .catalogs import SteelProfile, all_profiles, filter_profiles
from .cost_lca import COST_USD_PER_TON
from .pareto import Candidate, pareto_front


# ---------------------------------------------------------------------------
# Datos resultado
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DEBeamResult:
    """Resultado de la optimizacion DE para viga."""
    section: str
    weight_kg_m: float
    total_weight_kg: float
    Mn_kNm: float
    utilization_M: float
    Vn_kN: float
    utilization_V: float
    deflection_mm: float
    deflection_limit_mm: float
    deflection_ok: bool
    feasible: bool


@dataclass(frozen=True)
class DEColumnResult:
    """Resultado de la optimizacion DE para columna."""
    section: str
    weight_kg_m: float
    total_weight_kg: float
    Pn_kN: float
    utilization_P: float
    slenderness: float
    feasible: bool
    #: Interacción AISC H1-1a/H1-1b con φMn = φ·Fy·Sx; None si no hay momento.
    interaction_ratio: Optional[float] = None


@dataclass(frozen=True)
class ParetoResult:
    """Resultado de la generacion de frontera Pareto peso-costo."""
    front: list[Candidate]
    all_solutions: list[Candidate]


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

_PHI_FLEX = 0.9
_PHI_SHEAR = 0.9
_PHI_COMP = 0.9
_E_PA = 200_000e6       # 200 GPa en Pa
_E_MPA = 200_000.0
_PENALTY = 1e12


def _catalog_for_beam(family: str | None = None,
                      custom: list[SteelProfile] | None = None,
                      ) -> list[SteelProfile]:
    if custom is not None:
        return list(custom)
    profiles = filter_profiles(family=family, min_Ix=0.0, min_A=0.0)
    # Filtrar perfiles con dimensiones validas
    return [p for p in profiles if p.d > 0 and p.Ix > 0]


def _beam_capacity(p: SteelProfile, Fy_MPa: float = 345.0):
    """Retorna (Mn_kNm, Vn_kN) para un perfil dado."""
    Fy_Pa = Fy_MPa * 1e6
    Sx_m3 = p.Ix / (p.d / 2.0)
    Mn_kNm = _PHI_FLEX * Fy_Pa * Sx_m3 / 1000.0

    # Cortante: Aw = d * tw aproximado. SteelProfile no tiene tw,
    # pero podemos estimarlo: A_web ~ A - 2*bf*tf.
    # Aproximacion: tw ~ (A - 2*bf*tf_approx) / (d - 2*tf_approx)
    # Como no tenemos tf, usamos Aw = A - 2*bf* (bf * 0.03) como proxy.
    # Simplificacion: usar Vn basado en area bruta escalada.
    # AISC G2: Vn = 0.6*Fy*Aw*Cv con Cv=1 para perfiles compactos.
    # Aw ~ d * tw; sin tw usamos Aw = A/2 (aprox alma es ~50% del area).
    Aw_m2 = p.A * 0.5
    Vn_kN = _PHI_SHEAR * 0.6 * Fy_Pa * Aw_m2 / 1000.0
    return Mn_kNm, Vn_kN


def _deflection_mm(w_kN_m: float, L_m: float, Ix_m4: float) -> float:
    """Deflexion maxima viga simple bajo carga distribuida uniforme (mm)."""
    w_N_m = w_kN_m * 1000.0
    delta_m = 5.0 * w_N_m * L_m ** 4 / (384.0 * _E_PA * Ix_m4)
    return delta_m * 1000.0


# ---------------------------------------------------------------------------
# optimize_beam_de
# ---------------------------------------------------------------------------

def optimize_beam_de(
    span_m: float,
    w_kN_m: float,
    catalog: list[SteelProfile] | None = None,
    family: str | None = None,
    Fy_MPa: float = 345.0,
    deflection_limit: float = 360.0,
    seed: int = 42,
    maxiter: int = 100,
    tol: float = 1e-6,
) -> DEBeamResult:
    """Optimiza la seccion de una viga simplemente apoyada via DE.

    Funcion objetivo: peso total = weight_per_m * span_m.
    Restricciones (penalty): Mu <= phi*Mn, Vu <= phi*Vn, delta <= L/limit.

    Args:
        span_m: luz de la viga en metros.
        w_kN_m: carga distribuida uniforme (kN/m).
        catalog: lista de perfiles a considerar (None = todos).
        family: filtrar por familia ('W', 'IPE', 'HEB'...).
        Fy_MPa: tension de fluencia.
        deflection_limit: divisor (360 -> L/360).
        seed: semilla para reproducibilidad.
        maxiter: iteraciones maximas de DE.
        tol: tolerancia de convergencia.

    Returns:
        DEBeamResult con la seccion optima.
    """
    if span_m <= 0:
        raise ValueError("span_m debe ser positivo")
    if w_kN_m <= 0:
        raise ValueError("w_kN_m debe ser positivo")

    profiles = _catalog_for_beam(family, catalog)
    if not profiles:
        raise ValueError("catalogo vacio para los filtros dados")

    # Ordenar por peso para que el espacio sea mas suave
    profiles.sort(key=lambda p: p.weight_per_m)
    n = len(profiles)

    # Solicitaciones
    Mu_kNm = w_kN_m * span_m ** 2 / 8.0   # viga simple
    Vu_kN = w_kN_m * span_m / 2.0
    delta_limit_mm = span_m * 1000.0 / deflection_limit

    def objective(x):
        idx = int(round(x[0]))
        idx = max(0, min(idx, n - 1))
        p = profiles[idx]

        total_weight = p.weight_per_m * span_m
        Mn, Vn = _beam_capacity(p, Fy_MPa)
        delta = _deflection_mm(w_kN_m, span_m, p.Ix)

        penalty = 0.0
        if Mu_kNm > Mn:
            penalty += _PENALTY * (Mu_kNm / max(Mn, 1e-9) - 1.0)
        if Vu_kN > Vn:
            penalty += _PENALTY * (Vu_kN / max(Vn, 1e-9) - 1.0)
        if delta > delta_limit_mm:
            penalty += _PENALTY * (delta / max(delta_limit_mm, 1e-9) - 1.0)

        return total_weight + penalty

    result = differential_evolution(
        objective,
        bounds=[(0, n - 1)],
        seed=seed,
        maxiter=maxiter,
        tol=tol,
        polish=False,
        integrality=[True],
    )

    best_idx = int(round(result.x[0]))
    best_idx = max(0, min(best_idx, n - 1))
    p = profiles[best_idx]
    Mn, Vn = _beam_capacity(p, Fy_MPa)
    delta = _deflection_mm(w_kN_m, span_m, p.Ix)

    util_M = Mu_kNm / Mn if Mn > 0 else float("inf")
    util_V = Vu_kN / Vn if Vn > 0 else float("inf")
    deflection_ok = delta <= delta_limit_mm + 1e-9
    feasible = util_M <= 1.0 + 1e-9 and util_V <= 1.0 + 1e-9 and deflection_ok

    return DEBeamResult(
        section=p.designation,
        weight_kg_m=p.weight_per_m,
        total_weight_kg=p.weight_per_m * span_m,
        Mn_kNm=Mn,
        utilization_M=util_M,
        Vn_kN=Vn,
        utilization_V=util_V,
        deflection_mm=delta,
        deflection_limit_mm=delta_limit_mm,
        deflection_ok=deflection_ok,
        feasible=feasible,
    )


# ---------------------------------------------------------------------------
# optimize_column_de
# ---------------------------------------------------------------------------

def optimize_column_de(
    height_m: float,
    axial_kN: float,
    moment_kNm: float = 0.0,
    catalog: list[SteelProfile] | None = None,
    family: str | None = None,
    K: float = 1.0,
    Fy_MPa: float = 345.0,
    seed: int = 42,
    maxiter: int = 100,
    tol: float = 1e-6,
) -> DEColumnResult:
    """Optimiza la seccion de una columna via DE.

    Funcion objetivo: peso total = weight_per_m * height_m.
    Restricciones (penalty): Pu <= phi*Pn (AISC E3), KL/r <= 200.
    Si hay momento, se aplica interaccion AISC H1.

    Args:
        height_m: altura de la columna en metros.
        axial_kN: carga axial de compresion (kN).
        moment_kNm: momento flector (kN.m), default 0.
        catalog: lista de perfiles a considerar.
        family: filtrar por familia.
        K: factor de longitud efectiva.
        Fy_MPa: tension de fluencia.
        seed: semilla.
        maxiter: iteraciones maximas.
        tol: tolerancia.

    Returns:
        DEColumnResult con la seccion optima.
    """
    if height_m <= 0:
        raise ValueError("height_m debe ser positivo")
    if axial_kN < 0:
        raise ValueError("axial_kN no puede ser negativo")

    profiles = _catalog_for_beam(family, catalog)
    # Filtrar perfiles con Iy > 0 para columnas
    profiles = [p for p in profiles if p.Iy > 0 and p.A > 0]
    if not profiles:
        raise ValueError("catalogo vacio para los filtros dados")

    profiles.sort(key=lambda p: p.weight_per_m)
    n = len(profiles)

    Fy_Pa = Fy_MPa * 1e6
    E_Pa = _E_PA

    def _column_capacity(p: SteelProfile):
        rx = math.sqrt(p.Ix / p.A)
        ry = math.sqrt(p.Iy / p.A)
        r_min = min(rx, ry)
        kl_over_r = (K * height_m) / r_min

        if kl_over_r > 200.0:
            return 0.0, kl_over_r

        Fe = (math.pi ** 2 * E_Pa) / (kl_over_r ** 2)
        if kl_over_r <= 4.71 * math.sqrt(E_Pa / Fy_Pa):
            Fcr = (0.658 ** (Fy_Pa / Fe)) * Fy_Pa
        else:
            Fcr = 0.877 * Fe

        Pn_kN = _PHI_COMP * Fcr * p.A / 1000.0
        return Pn_kN, kl_over_r

    def _interaction(p: SteelProfile, Pn: float) -> Optional[float]:
        """AISC H1-1a/b con φPn (ya minorado) y φMn = φ·Fy·Sx; None sin momento."""
        if not (moment_kNm > 0 and p.d > 0):
            return None
        if Pn <= 0:
            return float("inf")
        Sx_m3 = p.Ix / (p.d / 2.0)
        Mn_kNm = _PHI_FLEX * Fy_Pa * Sx_m3 / 1000.0
        ratio_P = axial_kN / Pn
        ratio_M = moment_kNm / Mn_kNm if Mn_kNm > 0 else float("inf")
        if ratio_P >= 0.2:
            return ratio_P + 8.0 / 9.0 * ratio_M
        return ratio_P / 2.0 + ratio_M

    def objective(x):
        idx = int(round(x[0]))
        idx = max(0, min(idx, n - 1))
        p = profiles[idx]

        total_weight = p.weight_per_m * height_m
        Pn, kl_r = _column_capacity(p)

        penalty = 0.0
        if kl_r > 200.0:
            penalty += _PENALTY * (kl_r / 200.0 - 1.0)

        # Interaccion axial
        if Pn <= 0:
            penalty += _PENALTY
        else:
            # Si hay momento, verificar interaccion AISC H1
            ic = _interaction(p, Pn)
            if ic is not None:
                if ic > 1.0:
                    penalty += _PENALTY * min(ic - 1.0, 1e3)
            else:
                if axial_kN > Pn:
                    penalty += _PENALTY * (axial_kN / max(Pn, 1e-9) - 1.0)

        return total_weight + penalty

    result = differential_evolution(
        objective,
        bounds=[(0, n - 1)],
        seed=seed,
        maxiter=maxiter,
        tol=tol,
        polish=False,
        integrality=[True],
    )

    best_idx = int(round(result.x[0]))
    best_idx = max(0, min(best_idx, n - 1))
    p = profiles[best_idx]
    Pn, kl_r = _column_capacity(p)

    util_P = axial_kN / Pn if Pn > 0 else float("inf")
    # Con momento, la factibilidad la decide la interacción H1 que se optimizó;
    # antes el resultado solo miraba el axil y podía declarar factible un perfil
    # con interacción > 1.
    ic = _interaction(p, Pn)
    feasible = util_P <= 1.0 + 1e-9 and kl_r <= 200.0
    if ic is not None:
        feasible = feasible and ic <= 1.0 + 1e-9

    return DEColumnResult(
        section=p.designation,
        weight_kg_m=p.weight_per_m,
        total_weight_kg=p.weight_per_m * height_m,
        Pn_kN=Pn,
        utilization_P=util_P,
        slenderness=kl_r,
        feasible=feasible,
        interaction_ratio=ic,
    )


# ---------------------------------------------------------------------------
# pareto_weight_cost  (multi-objetivo via barrido alpha)
# ---------------------------------------------------------------------------

def pareto_weight_cost(
    span_m: float,
    w_kN_m: float,
    catalog: list[SteelProfile] | None = None,
    family: str | None = None,
    Fy_MPa: float = 345.0,
    deflection_limit: float = 360.0,
    country: str = "DEFAULT",
    n_alphas: int = 11,
    seed: int = 42,
    maxiter: int = 80,
) -> ParetoResult:
    """Genera frontera Pareto peso-costo via barrido de alpha.

    Para cada alpha en linspace(0, 1, n_alphas):
        f = alpha * peso_normalizado + (1 - alpha) * costo_normalizado
    Ejecuta DE con esa funcion objetivo y recolecta las soluciones.
    Luego aplica filtro de dominancia (pareto.pareto_front).

    Args:
        span_m: luz de la viga (m).
        w_kN_m: carga uniforme (kN/m).
        catalog: perfiles a considerar.
        family: filtrar por familia.
        Fy_MPa: fluencia.
        deflection_limit: L/N.
        country: pais para costo.
        n_alphas: numero de valores de alpha a barrer.
        seed: semilla.
        maxiter: iteraciones DE por alpha.

    Returns:
        ParetoResult con la frontera y todas las soluciones.
    """
    profiles = _catalog_for_beam(family, catalog)
    if not profiles:
        raise ValueError("catalogo vacio para los filtros dados")

    profiles.sort(key=lambda p: p.weight_per_m)
    n = len(profiles)

    cost_per_ton = COST_USD_PER_TON.get(country.upper(),
                                         COST_USD_PER_TON["DEFAULT"])

    Mu_kNm = w_kN_m * span_m ** 2 / 8.0
    Vu_kN = w_kN_m * span_m / 2.0
    delta_limit_mm = span_m * 1000.0 / deflection_limit

    # Rangos para normalizacion
    weights = [p.weight_per_m * span_m for p in profiles]
    costs = [p.weight_per_m * span_m / 1000.0 * cost_per_ton for p in profiles]
    w_min, w_max = min(weights), max(weights)
    c_min, c_max = min(costs), max(costs)
    w_range = max(w_max - w_min, 1e-9)
    c_range = max(c_max - c_min, 1e-9)

    all_solutions: list[Candidate] = []
    seen: set[str] = set()

    alphas = [i / max(n_alphas - 1, 1) for i in range(n_alphas)]

    for alpha in alphas:
        def make_objective(a):
            def objective(x):
                idx = int(round(x[0]))
                idx = max(0, min(idx, n - 1))
                p = profiles[idx]

                w_total = p.weight_per_m * span_m
                c_total = w_total / 1000.0 * cost_per_ton

                Mn, Vn = _beam_capacity(p, Fy_MPa)
                delta = _deflection_mm(w_kN_m, span_m, p.Ix)

                penalty = 0.0
                if Mu_kNm > Mn:
                    penalty += _PENALTY * (Mu_kNm / max(Mn, 1e-9) - 1.0)
                if Vu_kN > Vn:
                    penalty += _PENALTY * (Vu_kN / max(Vn, 1e-9) - 1.0)
                if delta > delta_limit_mm:
                    penalty += _PENALTY * (delta / max(delta_limit_mm, 1e-9) - 1.0)

                w_norm = (w_total - w_min) / w_range
                c_norm = (c_total - c_min) / c_range

                return a * w_norm + (1 - a) * c_norm + penalty
            return objective

        result = differential_evolution(
            make_objective(alpha),
            bounds=[(0, n - 1)],
            seed=seed,
            maxiter=maxiter,
            tol=1e-6,
            polish=False,
            integrality=[True],
        )

        best_idx = int(round(result.x[0]))
        best_idx = max(0, min(best_idx, n - 1))
        p = profiles[best_idx]

        # Verificar factibilidad
        Mn, Vn = _beam_capacity(p, Fy_MPa)
        delta = _deflection_mm(w_kN_m, span_m, p.Ix)
        feasible = (Mu_kNm <= Mn + 1e-9
                     and Vu_kN <= Vn + 1e-9
                     and delta <= delta_limit_mm + 1e-9)

        if feasible and p.designation not in seen:
            seen.add(p.designation)
            w_total = p.weight_per_m * span_m
            c_total = w_total / 1000.0 * cost_per_ton
            all_solutions.append(
                Candidate(label=p.designation,
                          weight_kg=w_total,
                          cost_USD=c_total)
            )

    front = pareto_front(all_solutions) if all_solutions else []

    return ParetoResult(front=front, all_solutions=all_solutions)


__all__ = [
    "DEBeamResult",
    "DEColumnResult",
    "ParetoResult",
    "optimize_beam_de",
    "optimize_column_de",
    "pareto_weight_cost",
]
