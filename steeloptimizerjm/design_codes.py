"""
Diseño de vigas/columnas de acero — wrappers compactos por código.

AISC 360-22 §F2.1 (LRFD):     φ·Mn = φ·Zx·Fy            (compacta)
EN 1993-1-1 §6.2.5:           M_pl,Rd = W_pl·fy/γ_M0
AS 4100 §5.2.1:               φ·Ms = φ·S·fy
NSR-10 §F.2.5 (idéntico AISC)
SS EN 1993-1-1 (idéntico EN)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SteelBeamInput:
    plastic_modulus_mm3: float   # Zx (US/CO) o W_pl (EU/SG) o S (AU)
    Fy_MPa: float
    code: str = "US"


@dataclass(frozen=True)
class SteelBeamResult:
    Mn_kNm: float                 # nominal
    M_design_kNm: float           # con φ o /γ
    factor: float
    code: str


def design_beam_compact(inp: SteelBeamInput) -> SteelBeamResult:
    code = inp.code.upper()
    Mn = inp.plastic_modulus_mm3 * inp.Fy_MPa / 1e6  # kN·m
    if code in ("US", "CO"):
        phi = 0.90
        M_d = phi * Mn
        factor = phi
    elif code in ("EU", "SG"):
        gamma_M0 = 1.00
        M_d = Mn / gamma_M0
        factor = 1 / gamma_M0
    elif code == "AU":
        phi = 0.90
        M_d = phi * Mn
        factor = phi
    else:
        raise ValueError(f"código '{code}' no soportado")
    return SteelBeamResult(
        Mn_kNm=Mn, M_design_kNm=M_d, factor=factor, code=code,
    )


@dataclass(frozen=True)
class SteelColumnInput:
    A_mm2: float
    Fy_MPa: float
    lambda_slenderness: float    # KL/r · √(Fy/E·π²)
    code: str = "US"


def design_column(inp: SteelColumnInput) -> dict[str, Any]:
    """Resistencia a compresión axial (curva de pandeo).

    AISC: Fcr = (0.658^λ²)·Fy  si λ ≤ 1.5, else (0.877/λ²)·Fy
    EN:   chi = 1/(φ + √(φ² - λ²))  con curva de pandeo c → α=0.49
    AS:   αb factor + αc curva de imperfección
    """
    code = inp.code.upper()
    lam = inp.lambda_slenderness
    Fy = inp.Fy_MPa
    A = inp.A_mm2

    if code in ("US", "CO"):
        Fcr = (0.658 ** (lam ** 2)) * Fy if lam <= 1.5 else (0.877 / lam ** 2) * Fy
        Pn = Fcr * A / 1000.0
        phi = 0.90
        Pd = phi * Pn
    elif code in ("EU", "SG"):
        alpha = 0.49  # curva c (perfil laminado pesado)
        phi_var = 0.5 * (1 + alpha * (lam - 0.2) + lam ** 2)
        chi = 1.0 / (phi_var + (phi_var ** 2 - lam ** 2) ** 0.5)
        chi = min(chi, 1.0)
        Pn = chi * A * Fy / 1000.0
        gamma_M1 = 1.00
        Pd = Pn / gamma_M1
    elif code == "AU":
        # AS 4100 §6.3.3 — αc forma cerrada (Rotter-Hancock)
        # αc ≈ (0.658^λ²) si λ ≤ 1.5; else 0.877/λ² (equiv AISC αb=0)
        if lam <= 1.5:
            alpha_c = 0.658 ** (lam ** 2)
        else:
            alpha_c = 0.877 / (lam ** 2)
        Pn = alpha_c * A * Fy / 1000.0
        phi = 0.90
        Pd = phi * Pn
    else:
        raise ValueError(f"código '{code}' no soportado")

    return {"Pn_kN": Pn, "P_design_kN": Pd, "code": code}


__all__ = [
    "SteelBeamInput", "SteelBeamResult", "design_beam_compact",
    "SteelColumnInput", "design_column",
]
