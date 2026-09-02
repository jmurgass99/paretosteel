"""Golden test para interacción compresión axial y flexión biaxial según AISC 360-16 Capítulo H y Apéndice 8.

Fuente Normativa:
  - AISC 360-16: Specification for Structural Steel Buildings
  - Chapter H §H1.1: Doubly and Singly Symmetric Members Subject to Flexure and Axial Compression
      * Eq. H1-1a (para Pr / Pc >= 0.20):  Pr/Pc + (8/9)·(Mrx/Mcx + Mry/Mcy) <= 1.0
      * Eq. H1-1b (para Pr / Pc < 0.20):   Pr/(2·Pc) + (Mrx/Mcx + Mry/Mcy) <= 1.0
  - Appendix 8 §8.2: Approximate Second-Order Analysis
      * Eq. A-8-3: B1 = Cm / (1 - α·Pr / Pe1) >= 1.0 (con α = 1.0 para LRFD)
      * Eq. A-8-5: Pe1 = π² · E · I / (K1 · L)²

Derivación analítica a mano:
----------------------------
Datos:
  Pn = 2000.0 kN, φc = 0.90 -> Pc = φc·Pn = 1800.0 kN
  Mnx = 400.0 kNm, φb = 0.90 -> Mcx = φb·Mnx = 360.0 kNm
  Mny = 150.0 kNm, φb = 0.90 -> Mcy = φb·Mny = 135.0 kNm
  L = 4000.0 mm, K1 = 1.0, E = 200,000 MPa
  Ix = 2.0e8 mm⁴ -> Pe1_x = π² · 200000 · 2.0e8 / (4000² · 1000) = 24,674.0110027 kN
  Iy = 5.0e7 mm⁴ -> Pe1_y = π² · 200000 · 5.0e7 / (4000² · 1000) = 6,168.5027507 kN

Caso 1: Punto frontera exacto Pu / Pc = 0.20 (Pu = 360.0 kN)
  p = 360.0 / 1800.0 = 0.2000000
  Cm = 1.0
  B1_x = 1.0 / (1 - 360.0 / 24674.0110027) = 1.014806037
  B1_y = 1.0 / (1 - 360.0 / 6168.5027507) = 1.061978873
  Mux = 162.0 kNm -> Mrx = 1.014806037 · 162.0 = 164.3985781 kNm
  Muy = 60.75 kNm -> Mry = 1.061978873 · 60.75 = 64.5152165 kNm
  Σ = 164.3985781 / 360.0 + 64.5152165 / 135.0 = 0.456662717 + 0.477890493 = 0.934553210
  Eq. H1-1a: DCR = 0.20 + (8/9) · 0.934553210 = 1.030713964

Punto de coincidencia teórica H1-1a == H1-1b:
  Cuando p = 0.20 y Σ = 0.90:
    H1-1a: 0.20 + (8/9) · 0.90 = 0.20 + 0.80 = 1.0000000
    H1-1b: 0.20 / 2 + 0.90 = 0.10 + 0.90 = 1.0000000
"""
from __future__ import annotations

import math
import pytest

from steeloptimizerjm.design_codes import (
    AiscBeamColumnInput,
    AiscBeamColumnResult,
    calc_B1,
    aisc_beam_column_interaction,
)


def test_golden_aisc_h1_crossing_boundary_at_p_0_20():
    """GOLDEN. Comprueba la frontera de cruce p = 0.20 y la igualdad exacta cuando Σ = 0.90.

    Fuente Normativa:
      - AISC 360-16: Specification for Structural Steel Buildings.
      - Chapter H §H1.1: Doubly and Singly Symmetric Members Subject to Flexure and Axial Compression.
        * Eq. (H1-1a): Pr/Pc + (8/9)·(Mrx/Mcx + Mry/Mcy) <= 1.0 (para Pr/Pc >= 0.20).
      - Appendix 8 §8.2: Approximate Second-Order Analysis.
        * Eq. (A-8-3): B1 = Cm / (1 - α·Pr / Pe1) >= 1.0 (con α = 1.0 para LRFD).
        * Eq. (A-8-5): Pe1 = π² · E · I / (K1 · L)².
    """
    pi = math.pi
    Pe1_x_expected = (pi ** 2 * 200000.0 * 2.0e8) / (4000.0 ** 2 * 1000.0)
    Pe1_y_expected = (pi ** 2 * 200000.0 * 5.0e7) / (4000.0 ** 2 * 1000.0)

    inp = AiscBeamColumnInput(
        Pu_kN=360.0,
        Pn_kN=2000.0,
        Mux_kNm=162.0,
        Mnx_kNm=400.0,
        Muy_kNm=60.75,
        Mny_kNm=150.0,
        L_x_mm=4000.0,
        L_y_mm=4000.0,
        Ix_mm4=2.0e8,
        Iy_mm4=5.0e7,
        E_MPa=200000.0,
        Cm_x=1.0,
        Cm_y=1.0,
        phi_c=0.90,
        phi_b=0.90,
    )

    res = aisc_beam_column_interaction(inp)

    assert res.Pe1_x_kN == pytest.approx(Pe1_x_expected, rel=1e-12)
    assert res.Pe1_y_kN == pytest.approx(Pe1_y_expected, rel=1e-12)
    assert res.axial_ratio == pytest.approx(0.2000000, rel=1e-12)
    assert res.governing_equation == "H1-1a"

    # Amplificadores B1
    B1_x_exp = 1.0 / (1.0 - 360.0 / Pe1_x_expected)
    B1_y_exp = 1.0 / (1.0 - 360.0 / Pe1_y_expected)
    assert res.B1_x == pytest.approx(B1_x_exp, rel=1e-12)
    assert res.B1_y == pytest.approx(B1_y_exp, rel=1e-12)

    # Momentos amplificados
    assert res.Mrx_kNm == pytest.approx(B1_x_exp * 162.0, rel=1e-12)
    assert res.Mry_kNm == pytest.approx(B1_y_exp * 60.75, rel=1e-12)

    # DCR exacto derivado en docstring
    sigma = (B1_x_exp * 162.0) / 360.0 + (B1_y_exp * 60.75) / 135.0
    expected_dcr = 0.20 + (8.0 / 9.0) * sigma
    assert res.dcr == pytest.approx(expected_dcr, rel=1e-12)
    assert res.is_ok is False


def test_golden_aisc_h1_exact_crossing_point_dcr_unity():
    """GOLDEN. En p = 0.20 y suma de momentos Σ = 0.90, H1-1a y H1-1b dan exactamente 1.000000.

    Fuente Normativa:
      - AISC 360-16: Specification for Structural Steel Buildings.
      - Chapter H §H1.1: Doubly and Singly Symmetric Members Subject to Flexure and Axial Compression.
        * Eq. (H1-1a): 0.20 + (8/9)·0.90 = 1.000000.
        * Eq. (H1-1b): 0.20/2 + 0.90 = 1.000000.
    """
    # Determinamos Mux tal que Mrx / (phi_b * Mnx) = 0.90 exactamente
    inp_exact = AiscBeamColumnInput(
        Pu_kN=360.0,
        Pn_kN=2000.0,
        Mux_kNm=0.90 * 360.0,
        Mnx_kNm=400.0,
        Muy_kNm=0.0,
        Mny_kNm=150.0,
        L_x_mm=4000.0,
        L_y_mm=4000.0,
        Ix_mm4=2.0e8,
        Iy_mm4=5.0e7,
    )
    # Ajustamos Mux para que Mrx / (phi_b * Mnx) sea exactamente 0.90
    B1_x = calc_B1(inp_exact.Pu_kN, (math.pi ** 2 * 200000.0 * 2.0e8) / (4000.0 ** 2 * 1000.0))
    inp_exact_calibrated = AiscBeamColumnInput(
        Pu_kN=360.0,
        Pn_kN=2000.0,
        Mux_kNm=(0.90 * 360.0) / B1_x,
        Mnx_kNm=400.0,
        Muy_kNm=0.0,
        Mny_kNm=150.0,
        L_x_mm=4000.0,
        L_y_mm=4000.0,
        Ix_mm4=2.0e8,
        Iy_mm4=5.0e7,
    )
    res = aisc_beam_column_interaction(inp_exact_calibrated)
    assert res.axial_ratio == pytest.approx(0.20, rel=1e-12)
    assert res.dcr == pytest.approx(1.0000000, rel=1e-12)
    assert res.is_ok is True


def test_golden_aisc_h1_low_axial_ratio_h1_1b():
    """GOLDEN. Para p < 0.20 (Pu = 180 kN -> p = 0.10) rige la ecuación H1-1b.

    Fuente Normativa:
      - AISC 360-16: Specification for Structural Steel Buildings.
      - Chapter H §H1.1: Doubly and Singly Symmetric Members Subject to Flexure and Axial Compression.
        * Eq. (H1-1b): Pr/(2·Pc) + (Mrx/Mcx + Mry/Mcy) <= 1.0 (para Pr/Pc < 0.20).
    """
    inp_low = AiscBeamColumnInput(
        Pu_kN=180.0,
        Pn_kN=2000.0,
        Mux_kNm=162.0,
        Mnx_kNm=400.0,
        Muy_kNm=60.75,
        Mny_kNm=150.0,
        L_x_mm=4000.0,
        L_y_mm=4000.0,
        Ix_mm4=2.0e8,
        Iy_mm4=5.0e7,
    )
    res_low = aisc_beam_column_interaction(inp_low)
    assert res_low.axial_ratio == pytest.approx(0.10, rel=1e-12)
    assert res_low.governing_equation == "H1-1b"

    B1_x_exp = 1.0 / (1.0 - 180.0 / res_low.Pe1_x_kN)
    B1_y_exp = 1.0 / (1.0 - 180.0 / res_low.Pe1_y_kN)
    sigma = (B1_x_exp * 162.0) / 360.0 + (B1_y_exp * 60.75) / 135.0
    expected_dcr = (0.10 / 2.0) + sigma
    assert res_low.dcr == pytest.approx(expected_dcr, rel=1e-12)


def test_golden_b1_lower_bound_and_instability_limit():
    """GOLDEN. B1 >= 1.0 (cota inferior activa cuando Cm < 1.0) y excepción ante Pu >= Pe1.

    Fuente Normativa:
      - AISC 360-16: Specification for Structural Steel Buildings.
      - Appendix 8 §8.2, Eq. (A-8-3): B1 = Cm / (1 - α·Pr / Pe1) >= 1.0.
    """
    # 1. Cota B1 >= 1.0
    b1_capped = calc_B1(Pu_kN=50.0, Pe1_kN=20000.0, Cm=0.60)
    assert b1_capped == 1.0  # 0.60 / (1 - 50/20000) = 0.6015 < 1.0 -> 1.0

    # 2. Inestabilidad de columna por divergencia elástica Pu >= Pe1
    with pytest.raises(ValueError, match="alcanza o supera la carga de Euler Pe1"):
        calc_B1(Pu_kN=25000.0, Pe1_kN=24674.0)
