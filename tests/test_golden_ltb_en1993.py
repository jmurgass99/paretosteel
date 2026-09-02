"""Golden test para pandeo lateral-torsional (LTB) según EN 1993-1-1 §6.3.2.

Fuente:
1. EN 1993-1-1:2005 / Eurocódigo 3: Proyecto de estructuras de acero — Parte 1-1: Reglas generales y reglas para edificios, §6.3.2 (Pandeo lateral-torsional de barras flexionadas).
2. SN001a-EN-EU: "Access Steel — Critical moment for lateral-torsional buckling", ECCS / CTICM (Fuente de valores de C1 para distintos diagramas de momentos).

Derivación analítica cerrada a mano:
------------------------------------
Perfil: IPE 300 en acero S275 (fy = 275.0 MPa, E = 210000 MPa, G = 81000 MPa).
Propiedades geométricas tabuladas EN 10365:
    Iz = 6.038 · 10⁶ mm⁴ (603.8 cm⁴)
    Iw = 1.259 · 10¹¹ mm⁶ (125900 cm⁶)
    It = 2.012 · 10⁵ mm⁴ (20.12 cm⁴)
    Wpl,y = 6.284 · 10⁵ mm³ (628.4 cm³)
    h/b = 300/150 = 2.0 <= 2.0 (caso general EN 1993-1-1 Tabla 6.4: perfil laminado h/b <= 2.0 -> curva a, alpha_LT = 0.21;
    para método alternativo §6.3.2.3 o factor conservador de proyecto se evalúa alpha_LT = 0.34).

Luz libre entre arriostramientos laterales: L = 5000 mm (5.00 m).
Condición de carga: momento uniforme en todo el vano ⇒ C1 = 1.000 (Access Steel SN001a).
Condición de apoyo: horquilla en extremos (torsión impedida, alabeo libre: k = 1.0, kw = 1.0).

1. Momento crítico elástico Mcr:
    π² · E · Iz / L² = (π² · 210000 · 6038000) / 5000² = 500583.5991 N
    Iw / Iz = 1.259e11 / 6.038e6 = 20851.275257 mm²
    (L² · G · It) / (π² · E · Iz) = (5000² · 81000 · 201200) / (π² · 210000 · 6038000) = 32556.398048 mm²
    √(20851.275257 + 32556.398048) = √53407.673305 = 231.101002 mm
    Mcr = 1.0 · 500583.5991 · 231.101002 · 10⁻⁶ = 115.685369 kN·m.

2. Momento plástico de la sección (gamma_M1 = 1.00):
    Mpl,Rd = Wpl,y · fy / gamma_M1 = 628400 · 275 · 10⁻⁶ = 172.810 kN·m.

3. Esbeltez relativa λ_LT:
    λ_LT = √(Mpl,Rd / Mcr) = √(172.810 / 115.685369) = √1.493793 = 1.222208.

4. Coeficiente de reducción χ_LT (con alpha_LT = 0.34):
    Φ_LT = 0.5 · [1 + 0.34 · (1.222208 - 0.2) + 1.222208²] = 1.420672
    χ_LT = 1 / [1.420672 + √(1.420672² - 1.222208²)] = 1 / [1.420672 + 0.724235] = 0.466221.

5. Resistencia de diseño a pandeo lateral-torsional:
    Mb,Rd = χ_LT · Mpl,Rd = 0.466221 · 172.810 = 80.5676 kN·m.
"""
from __future__ import annotations

import math
import pytest
from steeloptimizerjm.design_codes import (
    LtbEc3Input,
    lateral_torsional_buckling_ec3,
)


def test_golden_lateral_torsional_buckling_ipe300_en1993_1_1():
    """GOLDEN. Validación cerrada de Mcr y Mb,Rd según EN 1993-1-1 §6.3.2 y Access Steel SN001a.

    Fuente Normativa:
      - EN 1993-1-1:2005: "Eurocode 3: Design of steel structures - Part 1-1".
      - §6.3.2: Lateral-torsional buckling of members subject to bending.
      - Access Steel SN001a: Critical moment Mcr para momento uniforme (C1 = 1.0).
    """
    inp = LtbEc3Input(
        L_unrestrained_mm=5000.0,
        Iz_mm4=6.038e6,
        Iw_mm6=1.259e11,
        It_mm4=2.012e5,
        Wpl_y_mm3=6.284e5,
        fy_MPa=275.0,
        E_MPa=210000.0,
        G_MPa=81000.0,
        C1=1.0,
        alpha_LT=0.34,
        gamma_M1=1.00,
    )
    res = lateral_torsional_buckling_ec3(inp)

    assert res.Mcr_kNm == pytest.approx(115.685369, rel=1e-5)
    assert res.lambda_bar_LT == pytest.approx(1.222208, rel=1e-5)
    assert res.phi_LT == pytest.approx(1.420672, rel=1e-5)
    assert res.chi_LT == pytest.approx(0.466221, rel=1e-5)
    assert res.Mpl_Rd_kNm == pytest.approx(172.810, rel=1e-5)
    assert res.Mb_Rd_kNm == pytest.approx(80.5676, rel=1e-4)


def test_golden_lateral_torsional_buckling_gamma_m1_non_unity():
    """GOLDEN. Validación de coeficiente parcial de seguridad gamma_M1 != 1.0 (Anexo Nacional EN 1993).

    Fuente Normativa:
      - EN 1993-1-1:2005 §6.3.2 & Cl. 6.1: Resistencia con gamma_M1 = 1.10.
    """
    inp = LtbEc3Input(
        L_unrestrained_mm=5000.0,
        Iz_mm4=6.038e6,
        Iw_mm6=1.259e11,
        It_mm4=2.012e5,
        Wpl_y_mm3=6.284e5,
        fy_MPa=275.0,
        E_MPa=210000.0,
        G_MPa=81000.0,
        C1=1.0,
        alpha_LT=0.34,
        gamma_M1=1.10,
    )
    res = lateral_torsional_buckling_ec3(inp)
    assert res.Mpl_Rd_kNm == pytest.approx(157.100, rel=1e-5)
    assert res.Mb_Rd_kNm == pytest.approx(73.2433, rel=1e-4)


def test_golden_en1993_table_6_4_and_6_5_ltb_curves_resolution():
    """GOLDEN. Selección normativa exacta de curva LTB y alpha_LT según EN 1993-1-1 Tablas 6.4 y 6.5.

    Fuente Normativa:
      - EN 1993-1-1:2005: "Eurocode 3: Design of steel structures - Part 1-1".
      - Sección 6.3.2.2, Tabla 6.4 (Curva LTB para caso general):
        * Perfil IPE 300 (h=300 mm, b=150 mm): h/b = 2.0 <= 2.0 laminado -> Curva a (alpha_LT = 0.21).
        * Perfil laminado esbelto (h/b = 350/150 = 2.33 > 2.0) -> Curva b (alpha_LT = 0.34).
        * Perfil soldado compacto (h/b = 300/150 = 2.0 <= 2.0) -> Curva c (alpha_LT = 0.49).
        * Perfil soldado esbelto (h/b = 350/150 = 2.33 > 2.0) -> Curva d (alpha_LT = 0.76).
      - Sección 6.3.2.3, Tabla 6.5 (Método específico para perfiles laminados):
        * Perfil IPE 300 (h/b = 2.0 <= 2.0) -> Curva b (alpha_LT = 0.34).
        * Perfil laminado (h/b = 2.33 > 2.0) -> Curva c (alpha_LT = 0.49).

    Resolución de Hallazgo de Auditoría:
      El falso umbral "h/b > 1.2" pertenecía a la Tabla 6.2 (pandeo por compresión axial pura).
      Para pandeo lateral-torsional en la Tabla 6.4 el umbral normativo es exactamente h/b = 2.0.
    """
    from steeloptimizerjm.design_codes import get_ec3_ltb_curve

    # 1. Caso General (§6.3.2.2 Tabla 6.4)
    # IPE 300 laminado: h/b = 2.0 -> Curva a (alpha_LT = 0.21)
    curve, alpha = get_ec3_ltb_curve(h_mm=300.0, b_mm=150.0, is_welded=False, method="general")
    assert curve == "a"
    assert alpha == pytest.approx(0.21)

    # Perfil laminado con h/b > 2.0 -> Curva b (alpha_LT = 0.34)
    curve_b, alpha_b = get_ec3_ltb_curve(h_mm=350.0, b_mm=150.0, is_welded=False, method="general")
    assert curve_b == "b"
    assert alpha_b == pytest.approx(0.34)

    # Perfil soldado con h/b <= 2.0 -> Curva c (alpha_LT = 0.49)
    curve_c, alpha_c = get_ec3_ltb_curve(h_mm=300.0, b_mm=150.0, is_welded=True, method="general")
    assert curve_c == "c"
    assert alpha_c == pytest.approx(0.49)

    # Perfil soldado con h/b > 2.0 -> Curva d (alpha_LT = 0.76)
    curve_d, alpha_d = get_ec3_ltb_curve(h_mm=350.0, b_mm=150.0, is_welded=True, method="general")
    assert curve_d == "d"
    assert alpha_d == pytest.approx(0.76)

    # 2. Método Específico para Laminados (§6.3.2.3 Tabla 6.5)
    # IPE 300 laminado: h/b <= 2.0 -> Curva b (alpha_LT = 0.34)
    curve_sp_b, alpha_sp_b = get_ec3_ltb_curve(h_mm=300.0, b_mm=150.0, is_welded=False, method="rolled")
    assert curve_sp_b == "b"
    assert alpha_sp_b == pytest.approx(0.34)

    # Laminado con h/b > 2.0 -> Curva c (alpha_LT = 0.49)
    curve_sp_c, alpha_sp_c = get_ec3_ltb_curve(h_mm=350.0, b_mm=150.0, is_welded=False, method="rolled")
    assert curve_sp_c == "c"
    assert alpha_sp_c == pytest.approx(0.49)
