"""AISC 360-22 Chapter H (Eq. H3-6) — Combined Torsion, Shear, Flexure, and Axial Force in HSS.

Implements the updated AISC 360-22 §H3.1 and §H3.2 provisions for rectangular and round
Hollow Structural Sections (HSS) subject to combined torsion, shear, biaxial bending,
and axial force:
  1. Torsional constant ``C`` for rectangular and circular HSS (§H3.1).
  2. Torsional buckling critical stress ``F_cr`` and design torsional strength ``phi_T * T_n``.
  3. Combined interaction Equation H3-6 (AISC 360-22 §H3.2):
     ``(P_r / P_c + M_rx / M_cx + M_ry / M_cy) + (V_r / V_c + T_r / T_c)^2 <= 1.0``

All public dataclasses declare ``units`` explicitly and avoid unit-suffixed field names.
"""
from __future__ import annotations

from dataclasses import dataclass
import math


def compute_hss_torsional_constant_c(
    shape: str,
    b_or_d: float,
    h: float = 0.0,
    t_des: float = 0.0,
) -> float:
    """Compute the HSS torsional shear constant ``C`` [mm3] per AISC 360-22 §H3.1 User Note.

    Parameters
    ----------
    shape : str
        ``"rectangular"`` (or ``"box"``) or ``"round"`` (or ``"circular"`` / ``"chs"``).
    b_or_d : float
        Outer width ``B`` (for rectangular HSS) or outer diameter ``D`` (for round HSS) [mm].
    h : float
        Outer depth ``H`` for rectangular HSS [mm].
    t_des : float
        Design wall thickness ``t`` [mm] (0.93 * nominal wall thickness for ERW HSS).
    """
    if b_or_d <= 0.0 or t_des <= 0.0:
        raise ValueError("Outer dimension and design wall thickness must be positive.")

    kind = shape.strip().lower()
    if kind in ("round", "circular", "chs", "pipe"):
        if b_or_d <= 2.0 * t_des:
            raise ValueError("Outer diameter must exceed 2 * t_des.")
        return math.pi * ((b_or_d - t_des) ** 2) * t_des / 2.0

    if kind in ("rectangular", "box", "rhs", "shs"):
        depth = h if h > 0.0 else b_or_d
        if b_or_d <= 2.0 * t_des or depth <= 2.0 * t_des:
            raise ValueError("Outer dimensions B and H must exceed 2 * t_des.")
        # AISC 360-22 §H3.1 User Note Eq. for inside corner radius r_i = t:
        # C = 2*(B - t)*(H - t)*t - 4.5*(4 - pi)*t^3
        return 2.0 * (b_or_d - t_des) * (depth - t_des) * t_des - 4.5 * (4.0 - math.pi) * (t_des**3)

    raise ValueError(f"Unsupported HSS shape '{shape}'. Expected 'rectangular' or 'round'.")


@dataclass(frozen=True)
class Aisc360HssH36Input:
    """Input for AISC 360-22 §H3.2 Equation H3-6 combined HSS interaction check.

    Units: forces in kN, moments/torques in kNm, lengths in mm, stresses in MPa.
    """

    p_r: float
    p_c: float
    m_rx: float
    m_cx: float
    m_ry: float
    m_cy: float
    v_r: float
    v_c: float
    t_r: float
    t_c: float
    units: str = "SI_kN_kNm"


@dataclass(frozen=True)
class Aisc360HssH36Result:
    """Result of AISC 360-22 Equation H3-6 combined interaction verification."""

    normal_stress_term: float
    shear_torsion_term_squared: float
    interaction_h3_6: float
    passes: bool
    status: str = "CALCULADO"
    clause: str = "AISC 360-22 §H3.2 Eq. (H3-6)"
    units: str = "SI_kN_kNm"


def verify_aisc360_22_hss_h3_6(inp: Aisc360HssH36Input) -> Aisc360HssH36Result:
    """Evaluate AISC 360-22 §H3.2 Equation H3-6 for HSS under combined forces and torsion.

    Equation H3-6:
        (P_r / P_c + M_rx / M_cx + M_ry / M_cy) + (V_r / V_c + T_r / T_c)^2 <= 1.0
    """
    if inp.p_c <= 0.0 or inp.m_cx <= 0.0 or inp.m_cy <= 0.0 or inp.v_c <= 0.0 or inp.t_c <= 0.0:
        raise ValueError("All design capacities (P_c, M_cx, M_cy, V_c, T_c) must be strictly positive.")

    normal_term = (
        abs(inp.p_r) / inp.p_c
        + abs(inp.m_rx) / inp.m_cx
        + abs(inp.m_ry) / inp.m_cy
    )
    shear_torsion_sq = ((abs(inp.v_r) / inp.v_c) + (abs(inp.t_r) / inp.t_c)) ** 2
    total = normal_term + shear_torsion_sq

    return Aisc360HssH36Result(
        normal_stress_term=round(normal_term, 4),
        shear_torsion_term_squared=round(shear_torsion_sq, 4),
        interaction_h3_6=round(total, 4),
        passes=total <= 1.0,
        status="CALCULADO",
        clause="AISC 360-22 §H3.2 Eq. (H3-6)",
        units=inp.units,
    )


def compute_rect_hss_design_torsion_strength(
    b: float,
    h: float,
    t_des: float,
    fy: float,
    elastic_modulus: float = 200_000.0,
    phi_t: float = 0.90,
) -> float:
    """Compute LRFD design torsional capacity ``phi_T * T_n`` [kNm] for rectangular HSS per AISC 360-22 §H3.1.

    Handles torsional yielding (``h/t <= 2.45*sqrt(E/Fy)``), inelastic buckling, and elastic buckling.
    """
    c_const = compute_hss_torsional_constant_c("rectangular", b_or_d=b, h=h, t_des=t_des)
    h_flat = max(b, h) - 3.0 * t_des
    slend = h_flat / t_des
    root_e_fy = math.sqrt(elastic_modulus / fy)

    limit_yield = 2.45 * root_e_fy
    limit_inel = 3.07 * root_e_fy

    if slend <= limit_yield:
        f_cr = 0.60 * fy
    elif slend <= limit_inel:
        f_cr = 0.60 * fy * (limit_yield / slend)
    else:
        f_cr = 0.458 * (math.pi**2) * elastic_modulus / (slend**2)

    t_n = (f_cr * c_const) / 1.0e6  # N*mm -> kN*m
    return round(phi_t * t_n, 4)


__all__ = [
    "Aisc360HssH36Input",
    "Aisc360HssH36Result",
    "compute_hss_torsional_constant_c",
    "compute_rect_hss_design_torsion_strength",
    "verify_aisc360_22_hss_h3_6",
]
