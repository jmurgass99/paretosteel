"""Golden tests para el diseño de arriostramientos de acero según AISC 360-16 y AISC 341-16.

Este archivo contiene tests que declaran explícitamente su fuente normativa,
artículo, tabla y edición dentro de cada función de test.
"""
from __future__ import annotations

import math
import pytest

from paretosteel.bracing import (
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


def test_golden_chevron_unbalanced_beam_demand_f2_3():
    """GOLDEN. Demanda vertical por carga desequilibrada en vigas de arriostramiento Chevron según AISC 341-16 §F2.3.

    Fuente Normativa:
      - AISC 341-16: "Seismic Provisions for Structural Steel Buildings".
      - Sección F2.3: Required Strength of Beams in Chevron Braced Frames (SCBF).
        * T_exp = Ry · Fy · Ag.
        * P_post = 0.30 · P_exp (resistencia residual en compresión tras pandeo cíclico).
        * Carga vertical desequilibrada: P_desequilibrio = (T_exp - 0.30 · P_exp) · sen(θ).
        * Momento flector en el centro del vano de la viga: M = P_desequilibrio · L_beam / 4.

    Derivación Analítica a Mano:
      Diagonal: Ag = 4000 mm², Fy = 345 MPa, Ry = 1.10 -> Ry*Fy = 379.5 MPa.
      T_exp = 1.10 * 345 * 4000 / 1000 = 1518.0 kN.
      Supongamos P_exp = 1000.0 kN (calculado con curva inelástica AISC E3 con Ry*Fy).
      P_post = 0.30 * 1000.0 = 300.0 kN.
      Ángulo con la horizontal: θ = 45.0° -> sen(45°) = 0.707107, cos(45°) = 0.707107.

      P_desequilibrio_v = (1518.0 - 300.0) * sen(45°) = 1218.0 * 0.707107 = 861.256 kN.
      Viga de luz L_beam = 6.0 m:
      M_beam = 861.256 * 6.0 / 4 = 1291.884 kN·m.

    Invariante Crítico:
      En el análisis elástico lateral puro, la fuerza vertical en el centro de la viga es prácticamente nula
      (ej. 20.0 kN por asimetrías elásticas menores).
      La demanda sísmica por capacidad con desequilibrio post-pandeo (861.3 kN) es MASIVA (>40 veces mayor).
    """
    from paretosteel.bracing import (
        calculate_chevron_beam_unbalanced_demand,
    )

    sec = SteelBraceSection(
        A_mm2=4000.0,
        rx_mm=75.0,
        ry_mm=45.0,
        length_mm=5000.0,
        Fy_MPa=345.0,
        Ry=1.10,
    )
    dem = BracingSystemDemand(
        Pu_tension_kN=500.0,
        Pu_compression_kN=500.0,
        theta_deg=45.0,
    )
    brace_res = design_steel_brace(sec, dem, configuration="CHEVRON_V")

    # Demanda elástica de referencia en el análisis de fuerzas laterales (pequeña o nula)
    elastic_v = 15.0  # kN

    unbalanced = calculate_chevron_beam_unbalanced_demand(
        brace_result=brace_res,
        theta_deg=45.0,
        beam_span_mm=6000.0,
        elastic_vertical_demand_kN=elastic_v,
    )

    # 1. T_exp y P_post-buckling
    T_exp_expected = 1.10 * 345.0 * 4000.0 / 1000.0  # 1518.0 kN
    assert unbalanced.T_exp_kN == pytest.approx(T_exp_expected, rel=1e-5)
    assert unbalanced.P_post_buckling_kN == pytest.approx(0.30 * brace_res.expected_compression_capacity_kN, rel=1e-5)

    # 2. Carga vertical desequilibrada exacta
    sin45 = math.sin(math.radians(45.0))
    expected_P_v = (T_exp_expected - 0.30 * brace_res.expected_compression_capacity_kN) * sin45
    assert unbalanced.P_unbalanced_vertical_kN == pytest.approx(expected_P_v, rel=1e-5)

    # 3. Momento en la viga biapoyada
    expected_M = expected_P_v * 6.0 / 4.0
    assert unbalanced.M_beam_midspan_kNm == pytest.approx(expected_M, rel=1e-5)

    # 4. Invariante discriminante: Demanda desequilibrada >> Análisis elástico
    assert unbalanced.P_unbalanced_vertical_kN > 30.0 * elastic_v
    assert unbalanced.amplification_over_elastic > 30.0


def test_golden_shear_lag_factor_table_d3_1():
    """GOLDEN. Factor de retraso de cortante U y área neta efectiva Ae según AISC 360-16 Tabla D3.1.

    Fuente Normativa:
      - AISC 360-16: "Specification for Structural Steel Buildings".
      - Capítulo D: Design of Members for Tension.
        * §D2: Tensile Rupture in Net Section: Pn = Fu · Ae.
        * §D3: Effective Net Area: Ae = An · U.
        * Tabla D3.1 (Shear Lag Factors for Connections to Tension Members):
          - Caso 1: Todos los elementos conectados directamente -> U = 1.0.
          - Caso 2: Conexión atornillada/soldada con transmisión por algunos elementos: U = 1 - x_bar / L.
          - Caso 7: Perfiles W conectados por las alas:
              * bf >= (2/3)·d -> U = 0.90
              * bf < (2/3)·d  -> U = 0.85

    Derivación a Mano:
      Angular L 150x100x12 conectado solo por el ala larga (150 mm) a chapa de nudo:
        x_bar = 25.0 mm (distancia del plano de conexión al centroide del angular).
        Longitud de la hilera de pernos: L_conn = 200.0 mm.
        U_caso2 = 1.0 - 25.0 / 200.0 = 1.0 - 0.125 = 0.875.
        Área bruta Ag = 2860 mm², agujeros de 2 pernos d=22+2=24 mm en ala de 12 mm:
        An = 2860 - 24 * 12 = 2572 mm².
        Ae = 2572 * 0.875 = 2250.5 mm².
        Si se omitiera U (asumiendo U=1.0), se sobreestimaría la capacidad en +14.3% del lado INSEGURO.
    """
    from paretosteel.bracing import (
        calc_net_effective_area,
        calc_shear_lag_factor_U,
    )

    # Caso 1: Conexión total directa
    assert calc_shear_lag_factor_U(case=1) == 1.0

    # Caso 2: Conexión excéntrica
    U2 = calc_shear_lag_factor_U(case=2, x_bar_mm=25.0, L_conn_mm=200.0)
    assert U2 == pytest.approx(0.875, rel=1e-6)

    Ag = 2860.0
    An = 2572.0
    Ae, ratio = calc_net_effective_area(Ag, An, U2)
    assert Ae == pytest.approx(2572.0 * 0.875, rel=1e-5)
    assert ratio == pytest.approx(2250.5 / 2860.0, rel=1e-4)

    # Caso 7: Perfil W
    # W14x90: d = 356 mm, bf = 368 mm -> bf >= (2/3)*d (368 >= 237.3 mm) -> U = 0.90
    assert calc_shear_lag_factor_U(case=7, bf_mm=368.0, d_mm=356.0) == 0.90
    # W18x35: d = 450 mm, bf = 152 mm -> bf < (2/3)*d (152 < 300 mm) -> U = 0.85
    assert calc_shear_lag_factor_U(case=7, bf_mm=152.0, d_mm=450.0) == 0.85


def test_golden_gusset_plate_whitmore_and_2t_clearance():
    """GOLDEN. Verificación de sección de Whitmore (AISC 360 §J4) y franja libre de 2t en SCBF (AISC 341 §F2.6c.2).

    Fuente Normativa:
      - AISC 360-16:
        * §J4.1: Strength of Elements in Tension - Whitmore Section:
          b_w = w_conn + 2 · L_conn · tan(30°).
          Pn = Fy · b_w · t_gusset  (con phi = 0.90).
      - AISC 341-16:
        * §F2.6c.2: Special Concentric Braced Frames - Brace Connections:
          La placa de nudo debe proveer una zona libre de articulación plástica de al menos 2·t_gusset
          perpendicular al eje del arriostramiento para permitir la rotación fuera del plano por pandeo cíclico.

    Derivación a Mano:
      Placa de nudo: t_gusset = 16.0 mm, Fy = 250.0 MPa (A36).
      Conexión de arriostramiento: ancho w_conn = 200.0 mm, largo de soldadura L_conn = 300.0 mm.
      tan(30°) = 0.577350.
      b_w = 200.0 + 2 * 300.0 * 0.577350 = 200.0 + 346.410 = 546.410 mm.
      Aw = 546.410 * 16.0 = 8742.56 mm².
      Pn = 250.0 * 8742.56 / 1000 = 2185.64 kN.
      phi·Pn = 0.90 * 2185.64 = 1967.08 kN.

      Franja libre requerida: 2 · t_gusset = 2 * 16.0 = 32.0 mm.
      Si se provee 40.0 mm -> CUMPLE (40.0 >= 32.0).
      Si se provee 20.0 mm -> FALLA por riesgo de fractura frágil bajo rotación cíclica.
    """
    from paretosteel.bracing import check_gusset_plate

    # Caso 1: Cumple Whitmore y cumple franja de 2t
    res_ok = check_gusset_plate(
        t_gusset_mm=16.0,
        Fy_gusset_MPa=250.0,
        w_conn_mm=200.0,
        L_conn_mm=300.0,
        clearance_provided_mm=40.0,
        Pu_tension_kN=1500.0,
    )
    tan30 = math.tan(math.radians(30.0))
    expected_bw = 200.0 + 2.0 * 300.0 * tan30
    assert res_ok.whitmore_width_mm == pytest.approx(expected_bw, rel=1e-5)
    expected_Aw = expected_bw * 16.0
    assert res_ok.whitmore_area_mm2 == pytest.approx(expected_Aw, rel=1e-5)
    expected_phi_Pn = 0.90 * 250.0 * expected_Aw / 1000.0
    assert res_ok.phi_Pn_whitmore_kN == pytest.approx(expected_phi_Pn, rel=1e-5)
    assert res_ok.clearance_2t_required_mm == 32.0
    assert res_ok.is_2t_clearance_ok is True
    assert res_ok.status == "OK"

    # Caso 2: Falla franja de 2t (clearance = 25 mm < 32 mm)
    res_fail_clearance = check_gusset_plate(
        t_gusset_mm=16.0,
        Fy_gusset_MPa=250.0,
        w_conn_mm=200.0,
        L_conn_mm=300.0,
        clearance_provided_mm=25.0,  # Menor que 2 * 16.0 = 32.0 mm
        Pu_tension_kN=1500.0,
    )
    assert res_fail_clearance.is_2t_clearance_ok is False
    assert res_fail_clearance.status == "FAIL"

