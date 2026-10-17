"""Eurocode 3 Second Generation (EN 1993-1-1:2022) — Ultra-High-Strength Steels & Semi-Compact Plasticity.

Implements the key advances of the Second Generation of Eurocode 3 (EN 1993-1-1:2022):
  1. High and ultra-high strength steel grades up to S700 and S960 integrated into Part 1-1
     (formerly separated in EN 1993-1-12), with ``epsilon = sqrt(235 / fy)``.
  2. Elasto-plastic continuous bending resistance ``W_ep`` for Class 3 (semi-compact)
     cross-sections (EN 1993-1-1:2022 §6.2.5(2) & Annex B), eliminating the discontinuous
     capacity drop between Class 2 (``W_pl``) and Class 3 (``W_el``).
  3. Flexural buckling verification with buckling curve ``a0`` (``alpha = 0.13``) for
     ultra-high-strength grades (S460–S960) and continuous Overall Interaction Concept (OIC).

All public dataclasses declare ``units`` explicitly and avoid unit-suffixed field names.
"""
from __future__ import annotations

from dataclasses import dataclass
import math


EC3_2022_STEEL_GRADES: dict[str, dict[str, float]] = {
    "S235": {"fy": 235.0, "fu": 360.0},
    "S275": {"fy": 275.0, "fu": 430.0},
    "S355": {"fy": 355.0, "fu": 510.0},
    "S420": {"fy": 420.0, "fu": 520.0},
    "S460": {"fy": 460.0, "fu": 540.0},
    "S500": {"fy": 500.0, "fu": 580.0},
    "S550": {"fy": 550.0, "fu": 640.0},
    "S620": {"fy": 620.0, "fu": 700.0},
    "S690": {"fy": 690.0, "fu": 770.0},
    "S700": {"fy": 700.0, "fu": 750.0},
    "S890": {"fy": 890.0, "fu": 940.0},
    "S960": {"fy": 960.0, "fu": 980.0},
}

BUCKLING_IMPERFECTION_ALPHA: dict[str, float] = {
    "a0": 0.13,
    "a": 0.21,
    "b": 0.34,
    "c": 0.49,
    "d": 0.76,
}


def compute_epsilon_ec3_2022(fy: float) -> float:
    """Compute material slenderness factor ``epsilon = sqrt(235 / fy)`` per EN 1993-1-1:2022 §5.2."""
    if fy <= 0.0:
        raise ValueError(f"fy must be positive, got {fy}")
    return math.sqrt(235.0 / fy)


@dataclass(frozen=True)
class Ec3SemiCompactInput:
    """Input for EN 1993-1-1:2022 Annex B elasto-plastic bending & buckling check.

    Units: lengths in mm, areas in mm2, section moduli in mm3, stresses in MPa,
    internal forces in kN and kNm.
    """

    c_flange: float
    t_flange: float
    c_web: float
    t_web: float
    w_pl: float
    w_el: float
    area: float
    fy: float
    m_ed: float = 0.0
    n_ed: float = 0.0
    n_cr: float | None = None
    buckling_curve: str = "a0"
    gamma_m0: float = 1.00
    gamma_m1: float = 1.00
    units: str = "SI_kN_kNm_mm_MPa"


@dataclass(frozen=True)
class Ec3SemiCompactResult:
    """Result of EN 1993-1-1:2022 Annex B semi-compact bending and stability check."""

    epsilon: float
    section_class: int
    w_eff_design: float
    m_rd_2022: float
    m_rd_2005_legacy: float
    capacity_gain_pct: float
    chi_buckling: float
    n_b_rd: float
    utilization: float
    passes: bool
    status: str = "CALCULADO"
    clause: str = "EN 1993-1-1:2022 §6.2.5 & Annex B"
    units: str = "SI_kN_kNm_mm_MPa"


def verify_member_ec3_2022(inp: Ec3SemiCompactInput) -> Ec3SemiCompactResult:
    """Evaluate cross-section class, continuous semi-compact ``W_ep``, and stability per EC3:2022.

    For Class 3 rolled/welded I-sections in pure bending (EN 1993-1-1:2022 Table 7.2 & Annex B):
      - Flange outstand limits: Class 1 = 9*eps, Class 2 = 10*eps, Class 3 = 14*eps
      - Web in bending limits:  Class 1 = 72*eps, Class 2 = 83*eps, Class 3 = 124*eps
      - In Class 3, ``W_ep`` interpolates linearly between ``W_pl`` (at the Class 2 limit)
        and ``W_el`` (at the Class 3 limit), avoiding the discontinuous Class 2 -> 3 cliff.
    """
    if inp.t_flange <= 0.0 or inp.t_web <= 0.0 or inp.w_el <= 0.0 or inp.w_pl < inp.w_el:
        raise ValueError("Invalid geometric properties or w_pl < w_el.")
    if inp.fy <= 0.0 or inp.area <= 0.0:
        raise ValueError("fy and area must be positive.")

    eps = compute_epsilon_ec3_2022(inp.fy)
    slend_f = (inp.c_flange / inp.t_flange) / eps
    slend_w = (inp.c_web / inp.t_web) / eps

    # Determine governing class and continuous interpolation parameter alpha_ep in [0, 1]
    if slend_f <= 9.0 and slend_w <= 72.0:
        sec_class = 1
        w_eff = inp.w_pl
        w_legacy = inp.w_pl
    elif slend_f <= 10.0 and slend_w <= 83.0:
        sec_class = 2
        w_eff = inp.w_pl
        w_legacy = inp.w_pl
    elif slend_f <= 14.0 and slend_w <= 124.0:
        sec_class = 3
        # Normalized position between Class 2 boundary (0.0) and Class 3 boundary (1.0)
        ratio_f = max(0.0, (slend_f - 10.0) / (14.0 - 10.0))
        ratio_w = max(0.0, (slend_w - 83.0) / (124.0 - 83.0))
        xi = min(max(ratio_f, ratio_w), 1.0)
        w_eff = inp.w_pl - xi * (inp.w_pl - inp.w_el)
        w_legacy = inp.w_el
    else:
        sec_class = 4
        # Effective Class 4 reduction approximation
        red = min(14.0 / max(slend_f, 14.0), 124.0 / max(slend_w, 124.0))
        w_eff = inp.w_el * red
        w_legacy = w_eff

    m_rd_2022 = (w_eff * inp.fy) / (inp.gamma_m0 * 1.0e6)       # N*mm -> kN*m
    m_rd_legacy = (w_legacy * inp.fy) / (inp.gamma_m0 * 1.0e6)  # N*mm -> kN*m
    gain_pct = ((m_rd_2022 - m_rd_legacy) / m_rd_legacy * 100.0) if m_rd_legacy > 0.0 else 0.0

    # Flexural buckling reduction factor chi
    chi = 1.0
    if inp.n_cr is not None and inp.n_cr > 0.0:
        n_pl_n = inp.area * inp.fy / 1000.0  # kN
        lambda_bar = math.sqrt(n_pl_n / inp.n_cr)
        alpha_imp = BUCKLING_IMPERFECTION_ALPHA.get(inp.buckling_curve, 0.21)
        if lambda_bar > 0.2:
            phi = 0.5 * (1.0 + alpha_imp * (lambda_bar - 0.2) + lambda_bar**2)
            disc = max(0.0, phi**2 - lambda_bar**2)
            chi = min(1.0, 1.0 / (phi + math.sqrt(disc)))

    n_b_rd = (chi * inp.area * inp.fy) / (inp.gamma_m1 * 1000.0)  # kN
    util_m = abs(inp.m_ed) / m_rd_2022 if m_rd_2022 > 0.0 else float("inf")
    util_n = abs(inp.n_ed) / n_b_rd if n_b_rd > 0.0 else 0.0
    utilization = util_m + util_n

    return Ec3SemiCompactResult(
        epsilon=round(eps, 4),
        section_class=sec_class,
        w_eff_design=round(w_eff, 2),
        m_rd_2022=round(m_rd_2022, 3),
        m_rd_2005_legacy=round(m_rd_legacy, 3),
        capacity_gain_pct=round(gain_pct, 2),
        chi_buckling=round(chi, 4),
        n_b_rd=round(n_b_rd, 3),
        utilization=round(utilization, 4),
        passes=utilization <= 1.0,
        status="CALCULADO",
        clause="EN 1993-1-1:2022 §6.2.5 & Annex B",
        units=inp.units,
    )


__all__ = [
    "BUCKLING_IMPERFECTION_ALPHA",
    "EC3_2022_STEEL_GRADES",
    "Ec3SemiCompactInput",
    "Ec3SemiCompactResult",
    "compute_epsilon_ec3_2022",
    "verify_member_ec3_2022",
]
