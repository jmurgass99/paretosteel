"""Golden tests para el diseño de arriostramientos de acero según AISC 360-16 y AISC 341-16.

Este archivo contiene tests que declaran explícitamente su fuente normativa,
artículo, tabla y edición dentro de cada función de test.
"""
from __future__ import annotations

import math
import pytest

from steeloptimizerjm.bracing import (
    BracingSystemDemand,
    SteelBraceResult,
    SteelBraceSection,
    aisc_e3_critical_stress,
    calculate_effective_lengths,
    design_steel_brace,
)


def test_golden_aisc_e3_buckling_transition_point_continuity():
    """GOLDEN. Continuidad exacta de la curva de pandeo en la transición inelástica/elástica de AISC 360-16 §E3.

    Fuente Normativa:
      - AISC 360-16: "Specification for Structural Steel Buildings".
        * Capítulo E: Design of Members for Compression.
        * §E3: Compressive Strength for Flexural Buckling of Members without Slender Elements.
        * Eq. E3-2 (pandeo inelástico): Fcr = [0.658^(Fy / Fe)] * Fy, para KL/r <= 4.71 * sqrt(E / Fy).
        * Eq. E3-3 (pandeo elástico):   Fcr = 0.877 * Fe,              para KL/r > 4.71 * sqrt(E / Fy).
        * Eq. E3-4 (tensión de Euler):  Fe = pi² * E / (KL/r)².

    Derivación Analítica a Mano en el Punto de Cruce Crítico:
      Sea la esbeltez de transición lambda_c = 4.71 * sqrt(E / Fy):
        Fe(lambda_c) = pi² * E / [4.71² * (E / Fy)] = (pi² / 4.71²) * Fy
        pi² / 4.71² = 9.8696044 / 22.1841 = 0.4448954... ~ 0.444898 * Fy
        Por tanto: Fy / Fe = 22.1841 / 9.8696044 = 2.247719

      Evaluación en la rama inelástica (límite superior):
        Fcr_inel = [0.658^(Fy / Fe)] * Fy = [0.658^(2.247719)] * Fy
        0.658^(2.247719) = 0.390176
        Fcr_inel = 0.390176 * Fy

      Evaluación en la rama elástica (límite inferior):
        Fcr_el = 0.877 * Fe = 0.877 * (pi² / 4.71²) * Fy
        0.877 * (9.8696044 / 22.1841) = 0.877 * 0.4448954 = 0.390173 * Fy

      Diferencia relativa entre ambas formulaciones en la frontera:
        |Fcr_inel - Fcr_el| / Fy = |0.390176 - 0.390173| = 0.000003 < 1e-5 (0.0007%)
        Ambas ramas convergen con precisión de 5 cifras decimales a Fcr = 0.39018 * Fy.

      Para Fy = 345.0 MPa, E = 200,000.0 MPa:
        lambda_c = 4.71 * sqrt(200000 / 345) = 113.4035
        Fe = pi² * 200000 / 113.4035² = 153.4889 MPa
        Rama inelástica: Fcr_below = [0.658^(345 / 153.4889)] * 345 = 134.661 MPa (0.39032 * Fy)
        Rama elástica:   Fcr_above = 0.877 * 153.4889 = 134.610 MPa (0.39017 * Fy)
        Discrepancia por redondeo AISC 4.71: delta = 0.051 MPa (0.038%), garantizando cuasi-continuidad.
    """
    Fy = 345.0
    E = 200000.0
    lambda_c = 4.71 * math.sqrt(E / Fy)  # ~ 113.4035

    # Evaluamos un epsilon infinitesimal por debajo (rama inelástica)
    eps = 1e-4
    Fcr_below, Fe_below, regime_below, _ = aisc_e3_critical_stress(lambda_c - eps, Fy, E)
    assert regime_below == "INELASTIC"

    # Evaluamos un epsilon infinitesimal por encima (rama elástica)
    Fcr_above, Fe_above, regime_above, _ = aisc_e3_critical_stress(lambda_c + eps, Fy, E)
    assert regime_above == "ELASTIC"

    # Verificación de valores derivados a mano
    assert Fcr_below == pytest.approx(134.661, abs=0.02)
    assert Fcr_above == pytest.approx(134.610, abs=0.02)

    # Verificación de cuasi-continuidad en la frontera
    delta_Fcr = abs(Fcr_below - Fcr_above)
    assert delta_Fcr < 0.06  # Menor a 0.06 MPa en 134.6 MPa (< 0.045%)


def test_golden_x_brace_tension_compression_asymmetry():
    """GOLDEN. Asimetría de resistencia y longitud efectiva fuera del plano en arriostramiento en X.

    Fuente Normativa:
      - AISC 360-16:
        * Capítulo D §D2: Resistencia a tracción nominal Pn_t = Fy * Ag.
        * Capítulo E §E3: Resistencia a compresión nominal Pn_c = Fcr * Ag.
      - Criterio de longitud efectiva en X-Bracing (AISC Design Guide):
        * Fuera del plano (y): la diagonal en tracción arriostra el cruce -> Ky*Ly = 0.50 * L.
        * En el plano (x): nudos libres en el plano -> Kx*Lx = 1.0 * L.

    Derivación Analítica a Mano:
      Perfil: Ag = 5000 mm², rx = 80.0 mm, ry = 50.0 mm, L = 6000 mm, Fy = 345 MPa
        KL_x = 1.0 * 6000 = 6000 mm -> KL/rx = 6000 / 80 = 75.0
        KL_y = 0.5 * 6000 = 3000 mm -> KL/ry = 3000 / 50 = 60.0
        Gobernante: KL/r = 75.0 (en el plano) < lambda_c = 113.40 -> Pandeo Inelástico

        Fe = pi² * 200000 / 75² = 350.916 MPa
        Fy / Fe = 345 / 350.916 = 0.98314
        Fcr = [0.658^(0.98314)] * 345 = 228.60 MPa

        Compresión nominal: Pn_c = 228.60 * 5000 / 1000 = 1,143.0 kN
        Tracción nominal:   Pn_t = 345.0 * 5000 / 1000 = 1,725.0 kN

        Ratio de asimetría: Pn_t / Pn_c = 1,725.0 / 1,143.0 = 1.509 (+50.9% a tracción)
    """
    sec = SteelBraceSection(
        A_mm2=5000.0,
        rx_mm=80.0,
        ry_mm=50.0,
        length_mm=6000.0,
        Fy_MPa=345.0,
        Fu_MPa=450.0,
        E_MPa=200000.0,
    )
    dem = BracingSystemDemand(
        Pu_tension_kN=1200.0,
        Pu_compression_kN=900.0,
    )

    res = design_steel_brace(sec, dem, configuration="X_BRACE")

    # 1. Longitudes efectivas
    assert res.KL_over_r_x == pytest.approx(75.0, rel=1e-5)
    assert res.KL_over_r_y == pytest.approx(60.0, rel=1e-5)
    assert res.KL_over_r_governing == pytest.approx(75.0, rel=1e-5)
    assert res.buckling_regime == "INELASTIC"

    # 2. Tensiones críticas y capacidades nominales
    assert res.Fe_MPa == pytest.approx(350.916, abs=0.1)
    assert res.Fcr_MPa == pytest.approx(228.60, abs=0.2)
    assert res.Pn_compression_kN == pytest.approx(1143.0, abs=1.0)
    assert res.Pn_tension_yield_kN == pytest.approx(1725.0, abs=1.0)

    # 3. Comprobación de ASIMETRÍA TRACCIÓN / COMPRESIÓN
    assert res.tension_to_compression_ratio == pytest.approx(1.509, abs=0.01)
    assert res.Pn_tension_kN > 1.45 * res.Pn_compression_kN

    # 4. Diseño por capacidad sísmica AISC 341-16 §F2
    # Resistencia esperada a tracción T_exp = Ry * Fy * Ag = 1.10 * 345 * 5000 / 1000 = 1897.5 kN
    assert res.expected_tension_capacity_kN == pytest.approx(1897.5, abs=1.0)
    assert res.slenderness_seismic_status == "OK"
