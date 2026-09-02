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


@dataclass(frozen=True)
class LtbEc3Input:
    """Parámetros para comprobación de pandeo lateral-torsional según EN 1993-1-1 §6.3.2.
    
    Hipótesis de cálculo:
      - Condiciones de apoyo en extremos tipo horquilla (simplemente apoyada, torsión impedida,
        alabeo libre: k = 1.0, kw = 1.0).
      - Coeficiente de momento C1 según Access Steel SN001a / ECCS.
      - Factor de imperfección alpha_LT según EN 1993-1-1 §6.3.2.2 Tabla 6.4:
        * Perfiles I laminados con h/b <= 2.0 -> Curva a (alpha_LT = 0.21)
        * Perfiles I laminados con h/b > 2.0 -> Curva b (alpha_LT = 0.34)
        * Perfiles I soldados con h/b <= 2.0 -> Curva c (alpha_LT = 0.49)
        * Perfiles I soldados con h/b > 2.0 -> Curva d (alpha_LT = 0.76)
    """
    L_unrestrained_mm: float
    Iz_mm4: float
    Iw_mm6: float
    It_mm4: float
    Wpl_y_mm3: float
    fy_MPa: float
    E_MPa: float = 210000.0
    G_MPa: float = 81000.0
    C1: float = 1.0  # C1 = 1.0 (momento uniforme), 1.132 (carga repartida), 1.35 (puntual al centro)
    alpha_LT: float = 0.34  # Factor imperfección
    gamma_M1: float = 1.00


@dataclass(frozen=True)
class LtbEc3Result:
    Mcr_kNm: float
    lambda_bar_LT: float
    phi_LT: float
    chi_LT: float
    Mb_Rd_kNm: float
    Mpl_Rd_kNm: float


def lateral_torsional_buckling_ec3(inp: LtbEc3Input) -> LtbEc3Result:
    """Calcula momento crítico elástico Mcr y resistencia de diseño Mb,Rd según EN 1993-1-1 §6.3.2."""
    import math

    L = inp.L_unrestrained_mm
    pi = math.pi
    Iz = inp.Iz_mm4
    Iw = inp.Iw_mm6
    It = inp.It_mm4
    E = inp.E_MPa
    G = inp.G_MPa

    # Fórmula clásica de Mcr para sección doblemente simétrica con C1 (Access Steel SN001a)
    pi2_E_Iz_over_L2 = (pi ** 2 * E * Iz) / (L ** 2)
    term1 = Iw / Iz
    term2 = (L ** 2 * G * It) / (pi ** 2 * E * Iz)
    Mcr_Nmm = inp.C1 * pi2_E_Iz_over_L2 * math.sqrt(term1 + term2)
    Mcr_kNm = Mcr_Nmm * 1e-6

    # Momento plástico de la sección
    Mpl_Rd_kNm = (inp.Wpl_y_mm3 * inp.fy_MPa / inp.gamma_M1) * 1e-6

    # Esbeltez adimensional para pandeo lateral-torsional
    lambda_bar_LT = math.sqrt((inp.Wpl_y_mm3 * inp.fy_MPa) / Mcr_Nmm)

    # Factor de reducción chi_LT (EN 1993-1-1 §6.3.2.2 caso general)
    phi_LT = 0.5 * (1.0 + inp.alpha_LT * (lambda_bar_LT - 0.2) + (lambda_bar_LT ** 2))
    disc = max(0.0, (phi_LT ** 2) - (lambda_bar_LT ** 2))
    chi_LT = 1.0 / (phi_LT + math.sqrt(disc))
    chi_LT = min(1.0, chi_LT)

    Mb_Rd_kNm = chi_LT * Mpl_Rd_kNm

    return LtbEc3Result(
        Mcr_kNm=Mcr_kNm,
        lambda_bar_LT=lambda_bar_LT,
        phi_LT=phi_LT,
        chi_LT=chi_LT,
        Mb_Rd_kNm=Mb_Rd_kNm,
        Mpl_Rd_kNm=Mpl_Rd_kNm,
    )


__all__ = [
    "SteelBeamInput", "SteelBeamResult", "design_beam_compact",
    "SteelColumnInput", "design_column",
    "LtbEc3Input", "LtbEc3Result", "lateral_torsional_buckling_ec3",
]

