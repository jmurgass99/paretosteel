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


def get_ec3_ltb_curve(
    h_mm: float,
    b_mm: float,
    is_welded: bool = False,
    method: str = "general",
) -> tuple[str, float]:
    """Determina la curva de pandeo lateral-torsional y factor de imperfección alpha_LT según EN 1993-1-1.

    Fuente Normativa:
      - EN 1993-1-1:2005: "Eurocode 3: Design of steel structures - Part 1-1".
      - Sección 6.3.2.2, Tabla 6.4 (Recomendación para la curva de pandeo lateral-torsional en caso general):
        * Perfiles laminados en I y H:
            - h/b <= 2.0 -> Curva a (alpha_LT = 0.21) [NOTA: Para IPE 300 con h/b = 2.0 corresponde Curva a]
            - h/b > 2.0  -> Curva b (alpha_LT = 0.34)
        * Perfiles soldados en I y H:
            - h/b <= 2.0 -> Curva c (alpha_LT = 0.49)
            - h/b > 2.0  -> Curva d (alpha_LT = 0.76)
      - Sección 6.3.2.3, Tabla 6.5 (Método específico para perfiles laminados o secciones equivalentes):
        * Perfiles laminados en I y H:
            - h/b <= 2.0 -> Curva b (alpha_LT = 0.34)
            - h/b > 2.0  -> Curva c (alpha_LT = 0.49)
    """
    ratio = h_mm / max(b_mm, 1e-3)
    m = method.lower()
    if m == "general":
        if not is_welded:
            if ratio <= 2.0:
                return "a", 0.21
            else:
                return "b", 0.34
        else:
            if ratio <= 2.0:
                return "c", 0.49
            else:
                return "d", 0.76
    elif m in ("rolled", "specific", "alternativo"):
        if ratio <= 2.0:
            return "b", 0.34
        else:
            return "c", 0.49
    else:
        raise ValueError(f"Método de pandeo lateral desconocido: '{method}'. Usar 'general' o 'rolled'.")


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


# ===========================================================================
# AISC 360-16 Chapter H §H1 and Appendix 8 §8.2 (Beam-Column Interaction)
# ===========================================================================

@dataclass(frozen=True)
class AiscBeamColumnInput:
    """Inputs para interacción compresión-flexión biaxial según AISC 360-16 Capítulo H.

    Citas normativas:
      - Interacción P-M-M: AISC 360-16 Capítulo H §H1.1 (Eq. H1-1a / H1-1b)
      - Amplificación de momentos de 2º orden: AISC 360-16 Apéndice 8 §8.2 (Eq. A-8-3, A-8-5)
    """
    Pu_kN: float
    Pn_kN: float                 # Resistencia axial nominal a compresión Pn (AISC §E)
    Mux_kNm: float               # Momento de 1er orden en eje mayor (kN·m)
    Mnx_kNm: float               # Resistencia nominal a flexión eje mayor (kN·m)
    Muy_kNm: float = 0.0         # Momento de 1er orden en eje menor (kN·m)
    Mny_kNm: float = 1.0         # Resistencia nominal a flexión eje menor (kN·m)
    L_x_mm: float = 3000.0       # Longitud no arriostrada para pandeo en X (mm)
    L_y_mm: float = 3000.0       # Longitud no arriostrada para pandeo en Y (mm)
    Ix_mm4: float = 1.0e8        # Momento de inercia eje mayor (mm⁴)
    Iy_mm4: float = 2.0e7        # Momento de inercia eje menor (mm⁴)
    E_MPa: float = 200000.0      # Módulo de elasticidad (MPa)
    K1_x: float = 1.0            # Factor de longitud efectiva no traslacional X
    K1_y: float = 1.0            # Factor de longitud efectiva no traslacional Y
    Cm_x: float = 1.0            # Factor de gradiente de momentos X (AISC Apéndice 8 Eq. A-8-4)
    Cm_y: float = 1.0            # Factor de gradiente de momentos Y (AISC Apéndice 8 Eq. A-8-4)
    phi_c: float = 0.90          # Factor de resistencia a compresión (AISC §E1)
    phi_b: float = 0.90          # Factor de resistencia a flexión (AISC §F1)


@dataclass(frozen=True)
class AiscBeamColumnResult:
    """Resultado de la verificación de interacción AISC 360-16 Capítulo H."""
    Pe1_x_kN: float              # Carga crítica de Euler en X (Apéndice 8 Eq. A-8-5)
    Pe1_y_kN: float              # Carga crítica de Euler en Y (Apéndice 8 Eq. A-8-5)
    B1_x: float                  # Amplificador de momento B1 en X (Apéndice 8 Eq. A-8-3)
    B1_y: float                  # Amplificador de momento B1 en Y (Apéndice 8 Eq. A-8-3)
    Mrx_kNm: float               # Momento amplificado de 2º orden en X (kN·m)
    Mry_kNm: float               # Momento amplificado de 2º orden en Y (kN·m)
    axial_ratio: float           # Pu / (phi_c * Pn)
    governing_equation: str      # 'H1-1a' (ratio >= 0.20) o 'H1-1b' (ratio < 0.20)
    dcr: float                   # Ratio demanda / capacidad
    is_ok: bool


def calc_B1(Pu_kN: float, Pe1_kN: float, Cm: float = 1.0) -> float:
    """Calcula el amplificador de momento B1 según AISC 360-16 Apéndice 8 Eq. A-8-3.

    B1 = Cm / (1 - Pu / Pe1) >= 1.0
    """
    if Pe1_kN <= 0.0:
        raise ValueError("La carga crítica de Euler Pe1 debe ser positiva.")
    if Pu_kN >= Pe1_kN:
        raise ValueError(
            f"La carga axial Pu ({Pu_kN:.2f} kN) alcanza o supera la carga de Euler Pe1 ({Pe1_kN:.2f} kN), "
            "provocando inestabilidad elástica por divergencia (AISC 360-16 Apéndice 8)."
        )
    denom = 1.0 - (Pu_kN / Pe1_kN)
    b1 = Cm / denom
    return max(1.0, b1)


def aisc_beam_column_interaction(inp: AiscBeamColumnInput) -> AiscBeamColumnResult:
    """Comprueba la interacción compresión axial y flexión biaxial según AISC 360-16 §H1.1 y Apéndice 8 §8.2.

    Ecuaciones:
      - Para Pu / (φc·Pn) >= 0.20 (Eq. H1-1a):
            Pu / (φc·Pn) + (8/9) · (Mrx / (φb·Mnx) + Mry / (φb·Mny)) <= 1.0
      - Para Pu / (φc·Pn) < 0.20 (Eq. H1-1b):
            Pu / (2·φc·Pn) + (Mrx / (φb·Mnx) + Mry / (φb·Mny)) <= 1.0
    """
    import math

    pi = math.pi
    # Cargas críticas de Euler (Apéndice 8 Eq. A-8-5): Pe1 = (π² · E · I) / (K1 · L)²
    Pe1_x_kN = (pi ** 2 * inp.E_MPa * inp.Ix_mm4) / ((inp.K1_x * inp.L_x_mm) ** 2 * 1000.0)
    Pe1_y_kN = (pi ** 2 * inp.E_MPa * inp.Iy_mm4) / ((inp.K1_y * inp.L_y_mm) ** 2 * 1000.0)

    # Factores de amplificación de segundo orden B1 (Apéndice 8 Eq. A-8-3)
    B1_x = calc_B1(inp.Pu_kN, Pe1_x_kN, inp.Cm_x)
    B1_y = calc_B1(inp.Pu_kN, Pe1_y_kN, inp.Cm_y)

    Mrx_kNm = B1_x * inp.Mux_kNm
    Mry_kNm = B1_y * inp.Muy_kNm

    phi_Pn = inp.phi_c * inp.Pn_kN
    phi_Mnx = inp.phi_b * inp.Mnx_kNm
    phi_Mny = inp.phi_b * inp.Mny_kNm

    if phi_Pn <= 0.0:
        p_ratio = float("inf") if inp.Pu_kN > 0 else 0.0
    else:
        p_ratio = inp.Pu_kN / phi_Pn

    moment_sum = 0.0
    if phi_Mnx > 0.0:
        moment_sum += Mrx_kNm / phi_Mnx
    elif Mrx_kNm > 0.0:
        moment_sum += float("inf")

    if phi_Mny > 0.0:
        moment_sum += Mry_kNm / phi_Mny
    elif Mry_kNm > 0.0:
        moment_sum += float("inf")

    if p_ratio >= 0.20:
        gov_eq = "H1-1a"
        dcr = p_ratio + (8.0 / 9.0) * moment_sum
    else:
        gov_eq = "H1-1b"
        dcr = (p_ratio / 2.0) + moment_sum

    return AiscBeamColumnResult(
        Pe1_x_kN=Pe1_x_kN,
        Pe1_y_kN=Pe1_y_kN,
        B1_x=B1_x,
        B1_y=B1_y,
        Mrx_kNm=Mrx_kNm,
        Mry_kNm=Mry_kNm,
        axial_ratio=p_ratio,
        governing_equation=gov_eq,
        dcr=dcr,
        is_ok=dcr <= 1.0,
    )


__all__ = [
    "SteelBeamInput", "SteelBeamResult", "design_beam_compact",
    "SteelColumnInput", "design_column",
    "LtbEc3Input", "LtbEc3Result", "lateral_torsional_buckling_ec3",
]

