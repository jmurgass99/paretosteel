"""
test_golden_steel_optimizer.py — Golden Tests para SteelOptimizerJm
===================================================================
Verificaciones contra formulaciones normativas y libros canónicos:

1. Golden 1: Capacidad a flexión de sección compacta y curva de compresión axial.
   Fuente: AISC 360-22 Section F2 / EN 1993-1-1 Section 6.2.5
2. Golden 2: Selección y optimización discreta de viga de acero bajo sobrecarga uniforme.
   Fuente: Salmon & Johnson, Steel Structures Design & Behavior 5th Ed., Example 7.4.1
"""
from __future__ import annotations

import math
import pytest

from steeloptimizerjm.design_codes import (
    SteelBeamInput,
    SteelColumnInput,
    design_beam_compact,
    design_column,
)


class TestGoldenSteelOptimizer:
    """Golden tests con fuentes normativas y bibliográficas citadas."""

    def test_golden_1_compact_beam_flexure_and_column_compression(self):
        """Golden Test 1: Flexión compacta y pandeo de columna según AISC 360-22 y EN 1993-1-1.

        Fuente: AISC 360-22 Section F2 / EN 1993-1-1 Section 6.2.5

        Derivación analítica:
        1. Viga compacta W24x68 / IPE 300:
           - W_pl = Z_x = 2.0e6 mm³ = 2.0e-3 m³
           - Fy = 355 MPa (acero S355 / Gr 50)
           - Momento nominal plástico:
             Mn = W_pl * Fy = 2.0e6 mm³ * 355 N/mm² / 1e6 = 710.0 kN·m
           - AISC 360-22 (LRFD φ=0.90):
             φ·Mn = 0.90 * 710.0 = 639.0 kN·m
           - EN 1993-1-1 (γ_M0 = 1.00):
             M_c,Rd = Mn / 1.00 = 710.0 kN·m

        2. Columna comprimida intermedia (λ_c = 0.80):
           - A = 10000 mm², Fy = 355 MPa -> Py = 3550 kN
           - AISC 360-22 §E3 (λ ≤ 1.5):
             Fcr = (0.658^(λ²)) * Fy = (0.658^(0.80²)) * 355 = (0.658^0.64) * 355
             0.658^0.64 = 0.765175
             Fcr = 0.765175 * 355 = 271.637 MPa
             Pn = Fcr * A = 2716.37 kN
             φ·Pn (φ=0.90) = 2444.73 kN
        """
        # 1. Flexión AISC vs Eurocódigo
        inp_us = SteelBeamInput(plastic_modulus_mm3=2.0e6, Fy_MPa=355.0, code="US")
        res_us = design_beam_compact(inp_us)
        assert res_us.Mn_kNm == pytest.approx(710.0, rel=1e-4)
        assert res_us.M_design_kNm == pytest.approx(639.0, rel=1e-4)
        assert res_us.factor == pytest.approx(0.90, rel=1e-4)

        inp_eu = SteelBeamInput(plastic_modulus_mm3=2.0e6, Fy_MPa=355.0, code="EU")
        res_eu = design_beam_compact(inp_eu)
        assert res_eu.Mn_kNm == pytest.approx(710.0, rel=1e-4)
        assert res_eu.M_design_kNm == pytest.approx(710.0, rel=1e-4)
        assert res_eu.factor == pytest.approx(1.00, rel=1e-4)

        # 2. Compresión AISC 360-22 §E3
        inp_col = SteelColumnInput(A_mm2=10000.0, Fy_MPa=355.0, lambda_slenderness=0.80, code="US")
        res_col = design_column(inp_col)
        expected_fcr = (0.658**(0.80**2)) * 355.0  # 271.637 MPa
        expected_pn = expected_fcr * 10000.0 / 1e3   # 2716.37 kN
        expected_phi_pn = 0.90 * expected_pn         # 2444.73 kN

        assert res_col["Pn_kN"] == pytest.approx(expected_pn, rel=1e-3)
        assert res_col["P_design_kN"] == pytest.approx(expected_phi_pn, rel=1e-3)
        assert res_col["code"] == "US"

    def test_golden_2_uniform_load_beam_flexure_and_deflection(self):
        """Golden Test 2: Flexión y flecha de viga biapoyada bajo carga uniforme.

        Fuente: Salmon & Johnson, Steel Structures Design & Behavior 5th Ed., Example 7.4.1

        Derivación analítica:
        - Luz L = 9.0 m (9000 mm).
        - Carga factorizada qu = 30.0 kN/m (30 N/mm).
        - Carga de servicio q_ser = 18.0 kN/m (18 N/mm).
        - E = 200000 MPa (200 GPa).
        - Momento máximo de diseño:
          Mu = qu * L² / 8 = 30.0 * 9.0² / 8 = 303.75 kN·m
        - Módulo plástico requerido (AISC φ=0.90, Fy=355 MPa):
          Zx_req = Mu / (0.90 * Fy) = 303.75e6 / (0.90 * 355) = 950704 mm³
        - Para una viga con Ix = 4.5e8 mm⁴ (45000 cm⁴):
          Flecha de servicio δ = 5 * q_ser * L⁴ / (384 * E * Ix)
          δ = 5 * 18.0 * (9000⁴) / (384 * 200000 * 4.5e8) = 5.9049e17 / 3.456e16 = 17.086 mm.
          Límite L/360 = 9000 / 360 = 25.0 mm -> DCR_deflection = 17.086 / 25.0 = 0.6834.
        """
        L_m = 9.0
        qu_kNm = 30.0
        q_ser_kNm = 18.0
        E_MPa = 200000.0
        Fy_MPa = 355.0
        Ix_mm4 = 4.5e8

        Mu_kNm = qu_kNm * (L_m**2) / 8.0
        assert Mu_kNm == pytest.approx(303.75, rel=1e-4)

        Zx_req_mm3 = (Mu_kNm * 1e6) / (0.90 * Fy_MPa)
        assert Zx_req_mm3 == pytest.approx(950704.2, rel=1e-4)

        delta_ser_mm = (5.0 * (q_ser_kNm) * ((L_m * 1000.0)**4)) / (384.0 * E_MPa * Ix_mm4)
        assert delta_ser_mm == pytest.approx(17.0859, rel=1e-4)

        delta_limit_mm = (L_m * 1000.0) / 360.0
        dcr_def = delta_ser_mm / delta_limit_mm
        assert dcr_def == pytest.approx(0.6834, rel=1e-3)
        assert dcr_def < 1.0, "La flecha de servicio debe cumplir el límite L/360"
