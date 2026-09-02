"""Módulo de diseño y verificación de arriostramientos de acero según AISC 360-16 y AISC 341-16.

Implementa:
  - Modelado de longitudes efectivas según configuración (diagonal simple, X, chevron/V).
  - Pandeo en compresión AISC 360-16 Capítulo E §E3 (inelástico vs elástico con transición continua).
  - Resistencia a tracción AISC 360-16 Capítulo D §D2.
  - Asimetría tracción / compresión en sistemas de arriostramiento.
  - Parámetros sísmicos de diseño por capacidad AISC 341-16 (SCBF / OCBF).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal, Optional


BracingType = Literal["SINGLE_DIAGONAL", "X_BRACE", "CHEVRON_V", "CHEVRON_INVERTED_V"]


@dataclass(frozen=True)
class SteelBraceSection:
    """Propiedades geométricas y mecánicas del perfil del arriostramiento."""
    A_mm2: float                # Área bruta Ag (mm²)
    rx_mm: float                # Radio de giro eje fuerte (mm)
    ry_mm: float                # Radio de giro eje débil (mm)
    length_mm: float            # Longitud nudo a nudo del arriostramiento (L en mm)
    Fy_MPa: float = 345.0       # Tensión de fluencia especificada (ej. 345 MPa para A992/A572 Gr 50)
    Fu_MPa: float = 450.0       # Tensión de rotura especificada
    E_MPa: float = 200000.0     # Módulo de elasticidad (200,000 MPa)
    Ry: float = 1.10            # Factor de sobre-resistencia sísmica esperada (AISC 341-16 Tabla A3.1)
    Ae_ratio: float = 0.85      # Relación Ae/Ag de área neta efectiva a tracción


@dataclass(frozen=True)
class BracingSystemDemand:
    """Solicitaciones actuantes en el arriostramiento o en el sistema."""
    Pu_tension_kN: float = 0.0     # Tracción mayorada actuante (kN)
    Pu_compression_kN: float = 0.0 # Compresión mayorada actuante (kN, positiva)
    story_shear_kN: float = 0.0    # Cortante de piso transferido al sistema (kN)
    theta_deg: float = 45.0        # Ángulo de inclinación del arriostramiento respecto a la horizontal


@dataclass(frozen=True)
class SteelBraceResult:
    """Resultados de capacidad y verificación de arriostramiento."""
    # Longitudes efectivas adoptadas
    configuration: str
    KL_over_r_x: float
    KL_over_r_y: float
    KL_over_r_governing: float
    lambda_c_transition: float     # 4.71 * sqrt(E/Fy)
    buckling_regime: str           # "INELASTIC" o "ELASTIC"
    Fe_MPa: float                  # Tensión elástica de Euler (MPa)
    Fcr_MPa: float                 # Tensión crítica de pandeo (MPa)

    # Compresión
    Pn_compression_kN: float       # Resistencia nominal a compresión Fcr * Ag
    phi_Pn_compression_kN: float   # phi * Pn_c (phi = 0.90)
    dcr_compression: float         # Pu_c / phi_Pn_c

    # Tracción
    Pn_tension_yield_kN: float     # Fy * Ag
    Pn_tension_rupture_kN: float   # Fu * Ae
    Pn_tension_kN: float           # min(yield, rupture)
    phi_Pn_tension_kN: float       # phi * Pn_t
    dcr_tension: float             # Pu_t / phi_Pn_t

    # Asimetría y verificación global
    tension_to_compression_ratio: float # Pn_tension / Pn_compression
    max_dcr: float
    status: str

    # Parámetros sísmicos por capacidad AISC 341-16
    expected_tension_capacity_kN: float     # Ry * Fy * Ag
    expected_compression_capacity_kN: float   # min(Ry*Fy, 1.14*Fcre) * Ag
    slenderness_seismic_status: str          # "OK" si KL/r <= 200 (SCBF AISC 341-16 §F2.5b)


def calculate_effective_lengths(
    length_mm: float,
    configuration: BracingType,
) -> tuple[float, float, str]:
    """Calcula las longitudes efectivas en el plano (KL_x) y fuera del plano (KL_y).

    Justificación Física y Criterio de Diseño:
      - SINGLE_DIAGONAL: Sin puntos intermedios -> Kx*Lx = 1.0*L, Ky*Ly = 1.0*L.
      - X_BRACE (Cruz de San Andrés):
        * Fuera del plano (y): La diagonal en tracción arriostra el punto medio de la diagonal
          en compresión, restringiendo el desplazamiento transversal fuera del plano -> Ky*Ly = 0.50*L.
        * En el plano (x): El cruce central no está fijado a diafragma ni viga, pudiendo desplazarse
          libremente en el plano del pórtico -> Kx*Lx = 1.0*L.
      - CHEVRON_V / CHEVRON_INVERTED_V: La diagonal va de esquina a centro de viga -> Kx*Lx = 1.0*L, Ky*Ly = 1.0*L.
    """
    cfg = configuration.upper()
    if cfg == "X_BRACE":
        KL_x = 1.0 * length_mm
        KL_y = 0.5 * length_mm
        notes = "X-Brace: Kx*Lx = 1.0*L (en plano libre), Ky*Ly = 0.5*L (arriostrado fuera de plano por tracción)"
    elif cfg in ("CHEVRON_V", "CHEVRON_INVERTED_V"):
        KL_x = 1.0 * length_mm
        KL_y = 1.0 * length_mm
        notes = "Chevron V: Kx*Lx = 1.0*L, Ky*Ly = 1.0*L (nudo a viga sin arriostramiento intermedio)"
    elif cfg == "SINGLE_DIAGONAL":
        KL_x = 1.0 * length_mm
        KL_y = 1.0 * length_mm
        notes = "Single Diagonal: Kx*Lx = 1.0*L, Ky*Ly = 1.0*L"
    else:
        raise ValueError(f"Configuración de arriostramiento no reconocida: '{configuration}'")

    return KL_x, KL_y, notes


def aisc_e3_critical_stress(
    KL_over_r: float,
    Fy: float,
    E: float = 200000.0,
) -> tuple[float, float, str, float]:
    """Calcula la tensión crítica de compresión Fcr según AISC 360-16 Sección E3.

    Ecuaciones:
      - Tensión de Euler: Fe = pi² * E / (KL/r)²
      - Límite de transición: lambda_c = 4.71 * sqrt(E / Fy)
      - Pandeo inelástico (KL/r <= lambda_c):
          Fcr = [0.658^(Fy / Fe)] * Fy
      - Pandeo elástico (KL/r > lambda_c):
          Fcr = 0.877 * Fe

    Invariante: En el punto exacto KL/r = 4.71 * sqrt(E/Fy), ambas ramas coinciden idénticamente.
    """
    if KL_over_r <= 0.0:
        return Fy, float("inf"), "INELASTIC", 4.71 * math.sqrt(E / Fy)

    lambda_c = 4.71 * math.sqrt(E / Fy)
    Fe = (math.pi ** 2) * E / (KL_over_r ** 2)

    if KL_over_r <= lambda_c:
        regime = "INELASTIC"
        exponent = Fy / Fe
        Fcr = (0.658 ** exponent) * Fy
    else:
        regime = "ELASTIC"
        Fcr = 0.877 * Fe

    return Fcr, Fe, regime, lambda_c


def design_steel_brace(
    section: SteelBraceSection,
    demand: BracingSystemDemand,
    configuration: BracingType = "X_BRACE",
) -> SteelBraceResult:
    """Diseña y verifica un arriostramiento de acero según AISC 360-16 y AISC 341-16."""
    KL_x, KL_y, _ = calculate_effective_lengths(section.length_mm, configuration)

    KLr_x = KL_x / max(section.rx_mm, 1e-3)
    KLr_y = KL_y / max(section.ry_mm, 1e-3)
    KLr_gov = max(KLr_x, KLr_y)

    # 1. Compresión axial AISC 360-16 §E3
    Fcr, Fe, regime, lambda_c = aisc_e3_critical_stress(
        KL_over_r=KLr_gov,
        Fy=section.Fy_MPa,
        E=section.E_MPa,
    )
    Pn_c = Fcr * section.A_mm2 / 1000.0  # kN
    phi_c = 0.90
    phi_Pn_c = phi_c * Pn_c

    # 2. Tracción axial AISC 360-16 Capítulo D
    # Fluencia en sección bruta (phi = 0.90)
    Pn_t_yield = section.Fy_MPa * section.A_mm2 / 1000.0
    phi_t_yield = 0.90 * Pn_t_yield

    # Rotura en sección neta (phi = 0.75)
    Ae = section.Ae_ratio * section.A_mm2
    Pn_t_rupture = section.Fu_MPa * Ae / 1000.0
    phi_t_rupture = 0.75 * Pn_t_rupture

    # Resistencia de diseño gobernante a tracción
    phi_Pn_t = min(phi_t_yield, phi_t_rupture)
    Pn_t = min(Pn_t_yield, Pn_t_rupture)

    # 3. Ratios de demanda / capacidad
    if phi_Pn_c > 0:
        dcr_c = demand.Pu_compression_kN / phi_Pn_c
    else:
        dcr_c = float("inf") if demand.Pu_compression_kN > 0 else 0.0

    if phi_Pn_t > 0:
        dcr_t = demand.Pu_tension_kN / phi_Pn_t
    else:
        dcr_t = float("inf") if demand.Pu_tension_kN > 0 else 0.0

    max_dcr = max(dcr_c, dcr_t)
    status = "OK" if max_dcr <= 1.0 else "FAIL"

    # Asimetría tracción / compresión
    tension_to_comp_ratio = Pn_t / max(Pn_c, 1e-6)

    # 4. Diseño sísmico por capacidad AISC 341-16 (SCBF / OCBF)
    # Resistencia esperada a tracción: T_exp = Ry * Fy * Ag
    expected_tension_kN = section.Ry * section.Fy_MPa * section.A_mm2 / 1000.0

    # Resistencia esperada a compresión: P_exp = min(Ry * Fy, 1.14 * Fcre) * Ag
    # Fcre calculada con Ry * Fy
    Fcre, _, _, _ = aisc_e3_critical_stress(
        KL_over_r=KLr_gov,
        Fy=section.Ry * section.Fy_MPa,
        E=section.E_MPa,
    )
    expected_compression_kN = min(section.Ry * section.Fy_MPa, 1.14 * Fcre) * section.A_mm2 / 1000.0

    # Límite de esbeltez sísmica SCBF (AISC 341-16 §F2.5b): KL/r <= 200
    seismic_slenderness_ok = bool(KLr_gov <= 200.0)
    seismic_status = "OK" if seismic_slenderness_ok else "FAIL_SLENDERNESS_EXCEEDS_200"

    return SteelBraceResult(
        configuration=configuration,
        KL_over_r_x=KLr_x,
        KL_over_r_y=KLr_y,
        KL_over_r_governing=KLr_gov,
        lambda_c_transition=lambda_c,
        buckling_regime=regime,
        Fe_MPa=Fe,
        Fcr_MPa=Fcr,
        Pn_compression_kN=Pn_c,
        phi_Pn_compression_kN=phi_Pn_c,
        dcr_compression=dcr_c,
        Pn_tension_yield_kN=Pn_t_yield,
        Pn_tension_rupture_kN=Pn_t_rupture,
        Pn_tension_kN=Pn_t,
        phi_Pn_tension_kN=phi_Pn_t,
        dcr_tension=dcr_t,
        tension_to_compression_ratio=tension_to_comp_ratio,
        max_dcr=max_dcr,
        status=status,
        expected_tension_capacity_kN=expected_tension_kN,
        expected_compression_capacity_kN=expected_compression_kN,
        slenderness_seismic_status=seismic_status,
    )


# ---------------------------------------------------------------------------
# AISC 341-16 §F2.3 — Carga desequilibrada en vigas de arriostramiento Chevron
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ChevronBeamDemand:
    """Demanda sobre la viga debida a la carga desequilibrada de arriostramientos en V o V invertida (Chevron).

    Fuente Normativa:
      - AISC 341-16: Seismic Provisions for Structural Steel Buildings.
      - Section F2.3: Analysis - Required Strength of Beams in Chevron Braced Frames.
        Cuando la diagonal comprimida pandea, su capacidad cae a la resistencia residual post-pandeo:
          P_post_buckling = 0.30 · P_exp
        mientras la diagonal traccionada alcanza su capacidad esperada T_exp = Ry · Fy · Ag.
        La fuerza vertical desequilibrada en el punto medio de la viga es:
          P_desequilibrio = (T_exp - 0.30 · P_exp) · sen(θ)
    """
    T_exp_kN: float
    P_exp_kN: float
    P_post_buckling_kN: float       # 0.30 * P_exp
    theta_deg: float
    P_unbalanced_vertical_kN: float # (T_exp - 0.30 * P_exp) * sin(theta)
    P_unbalanced_horizontal_kN: float # (T_exp + 0.30 * P_exp) * cos(theta)
    M_beam_midspan_kNm: float       # P_unbalanced_v * L_beam / 4
    elastic_vertical_demand_kN: float
    amplification_over_elastic: float # P_unbalanced_v / max(elastic_v, 1e-6)


def calculate_chevron_beam_unbalanced_demand(
    brace_result: SteelBraceResult,
    theta_deg: float,
    beam_span_mm: float,
    elastic_vertical_demand_kN: float = 0.0,
) -> ChevronBeamDemand:
    """Calcula la demanda vertical desequilibrada sobre la viga según AISC 341-16 §F2.3."""
    theta_rad = math.radians(theta_deg)
    sin_theta = math.sin(theta_rad)
    cos_theta = math.cos(theta_rad)

    T_exp = brace_result.expected_tension_capacity_kN
    P_exp = brace_result.expected_compression_capacity_kN
    P_post = 0.30 * P_exp  # AISC 341-16 §F2.3 post-buckling compressive strength

    # Componente vertical de la fuerza desequilibrada
    P_unbalanced_v = (T_exp - P_post) * sin_theta
    # Componente horizontal neta transmitida a la viga
    P_unbalanced_h = (T_exp + P_post) * cos_theta

    # Momento flector en el centro del vano de la viga biapoyada: P * L / 4
    M_beam_midspan = (P_unbalanced_v * (beam_span_mm / 1000.0)) / 4.0

    amp = P_unbalanced_v / max(elastic_vertical_demand_kN, 1e-3) if elastic_vertical_demand_kN > 0 else float("inf")

    return ChevronBeamDemand(
        T_exp_kN=T_exp,
        P_exp_kN=P_exp,
        P_post_buckling_kN=P_post,
        theta_deg=theta_deg,
        P_unbalanced_vertical_kN=P_unbalanced_v,
        P_unbalanced_horizontal_kN=P_unbalanced_h,
        M_beam_midspan_kNm=M_beam_midspan,
        elastic_vertical_demand_kN=elastic_vertical_demand_kN,
        amplification_over_elastic=amp,
    )


# ---------------------------------------------------------------------------
# AISC 360-16 Capítulo D — Retraso de cortante (Shear Lag) Ae = An · U
# ---------------------------------------------------------------------------

def calc_shear_lag_factor_U(
    case: int = 2,
    x_bar_mm: float = 0.0,
    L_conn_mm: float = 100.0,
    bf_mm: float = 0.0,
    d_mm: float = 0.0,
) -> float:
    """Calcula el factor de retraso de cortante U según AISC 360-16 Tabla D3.1.

    Casos implementados:
      - Caso 1: Todos los elementos conectados directamente -> U = 1.0.
      - Caso 2: Conexión atornillada o soldada con elementos no conectados directamente:
          U = 1.0 - x_bar / L_conn (con cota inferior 0.0 y superior 1.0).
      - Caso 7: Perfiles W / I con alas conectadas:
          * bf >= (2/3)·d -> U = 0.90
          * bf < (2/3)·d  -> U = 0.85
    """
    if case == 1:
        return 1.0
    elif case == 2:
        if L_conn_mm <= 0:
            raise ValueError("Longitud de conexión L_conn_mm debe ser > 0.")
        u = 1.0 - (x_bar_mm / L_conn_mm)
        return max(0.0, min(1.0, u))
    elif case == 7:
        if d_mm <= 0:
            raise ValueError("Peralte d_mm debe ser > 0 para Caso 7.")
        if bf_mm >= (2.0 / 3.0) * d_mm:
            return 0.90
        else:
            return 0.85
    else:
        raise ValueError(f"Caso de retraso de cortante AISC Tabla D3.1 no soportado: {case}")


def calc_net_effective_area(
    Ag_mm2: float,
    An_mm2: float,
    U: float,
) -> tuple[float, float]:
    """Calcula el área neta efectiva Ae = An * U y la relación Ae/Ag."""
    if An_mm2 > Ag_mm2:
        raise ValueError(f"Área neta An ({An_mm2}) no puede ser mayor que área bruta Ag ({Ag_mm2}).")
    Ae = An_mm2 * U
    ratio = Ae / max(Ag_mm2, 1e-6)
    return Ae, ratio


# ---------------------------------------------------------------------------
# Chapa de nudo (Gusset Plate): Sección de Whitmore y Franja libre de 2t
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class GussetPlateResult:
    """Verificación de chapa de nudo (Gusset Plate) según AISC 360-16 y AISC 341-16."""
    t_gusset_mm: float
    whitmore_width_mm: float
    whitmore_area_mm2: float
    Pn_whitmore_yield_kN: float
    phi_Pn_whitmore_kN: float        # phi = 0.90
    dcr_whitmore: float
    clearance_2t_required_mm: float  # 2 * t_gusset
    clearance_provided_mm: float
    is_2t_clearance_ok: bool
    status: str


def check_gusset_plate(
    t_gusset_mm: float,
    Fy_gusset_MPa: float,
    w_conn_mm: float,
    L_conn_mm: float,
    clearance_provided_mm: float,
    Pu_tension_kN: float,
) -> GussetPlateResult:
    """Verifica la chapa de nudo (sección de Whitmore a tracción y franja libre de 2t en SCBF).

    Fuente Normativa:
      - AISC 360-16 §J4: Sección de Whitmore con ángulo de dispersión de 30°:
          b_w = w_conn + 2 · L_conn · tan(30°)
          Pn = Fy · b_w · t_gusset  (phi = 0.90)
      - AISC 341-16 §F2.6c.2: Zona de articulación libre de 2t:
          clearance >= 2.0 · t_gusset (permite rotación fuera del plano sin agrietamiento).
    """
    if t_gusset_mm <= 0:
        raise ValueError("Espesor de gusset debe ser > 0.")

    # Ancho de Whitmore: w_conn + 2 * L_conn * tan(30°)
    tan30 = math.tan(math.radians(30.0))
    bw = w_conn_mm + 2.0 * L_conn_mm * tan30
    Aw = bw * t_gusset_mm

    # Resistencia de fluencia en la sección de Whitmore (AISC 360-16 §J4.1)
    Pn_w_yield = Fy_gusset_MPa * Aw / 1000.0  # kN
    phi = 0.90
    phi_Pn = phi * Pn_w_yield
    dcr_w = Pu_tension_kN / max(phi_Pn, 1e-6)

    # Franja libre de 2t para articulación plástica fuera del plano (AISC 341-16 §F2.6c.2)
    req_clearance = 2.0 * t_gusset_mm
    clearance_ok = bool(clearance_provided_mm >= req_clearance)

    status = "OK" if (dcr_w <= 1.0 and clearance_ok) else "FAIL"

    return GussetPlateResult(
        t_gusset_mm=t_gusset_mm,
        whitmore_width_mm=bw,
        whitmore_area_mm2=Aw,
        Pn_whitmore_yield_kN=Pn_w_yield,
        phi_Pn_whitmore_kN=phi_Pn,
        dcr_whitmore=dcr_w,
        clearance_2t_required_mm=req_clearance,
        clearance_provided_mm=clearance_provided_mm,
        is_2t_clearance_ok=clearance_ok,
        status=status,
    )


__all__ = [
    "BracingType",
    "SteelBraceSection",
    "BracingSystemDemand",
    "SteelBraceResult",
    "ChevronBeamDemand",
    "GussetPlateResult",
    "calculate_effective_lengths",
    "aisc_e3_critical_stress",
    "design_steel_brace",
    "calculate_chevron_beam_unbalanced_demand",
    "calc_shear_lag_factor_U",
    "calc_net_effective_area",
    "check_gusset_plate",
]

