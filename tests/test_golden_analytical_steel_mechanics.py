# -*- coding: utf-8 -*-
"""test_golden_analytical_steel_mechanics.py — Fichas Golden analíticas para SteelOptimizerJm.

BLOQUE D — GOLDENS DE LA BANDA BAJA (SteelOptimizerJm):
======================================================
1. Golden 1: Resistencia a flexión plástica de sección de acero y factor de forma (AISC 360 / EC3 Cl. 6.2.5).
   Cita/Referencia:
     - AISC 360-16 Specification for Structural Steel Buildings, Chapter F (Design of Members for Flexure).
     - Eurocódigo 3 EN 1993-1-1:2005, Cl. 6.2.5 (Flexión simple y factores de capacidad plástica/elástica).
     - Salmon, C. G., Johnson, J. E., & Malhas, F. A. (2009), "Steel Structures: Design and Behavior", 5th Ed., Pearson.

2. Golden 2: Factor de reducción por pandeo flexional de columna de acero comprimida chi (EC3 Cl. 6.3.1.2).
   Cita/Referencia:
     - Eurocódigo 3 EN 1993-1-1:2005, Cl. 6.3.1.2 (Curvas de pandeo a0, a, b, c, d y formulación cerrada de reducción).
     - ECCS (European Convention for Constructional Steelwork) (2006), "Rules for Member Stability in EN 1993-1-1", TC8.
     - SSRC (Structural Stability Research Council) (2010), "Guide to Stability Design Criteria for Metal Structures", 6th Ed., Wiley.
"""
from __future__ import annotations

import math
import pytest


class TestGoldenAnalyticalSteelMechanics:
    def test_golden_1_cross_section_flexural_capacity_and_shape_factor(self) -> None:
        """Golden 1: Capacidad a flexión plástica y elástica según AISC 360-16 / EN 1993-1-1 Cl. 6.2.5.

        Modelo:
          Perfil laminado en caliente IPE 300 / S355 (Fy = 355.0 MPa, E = 210000.0 MPa):
            - Módulo resistente elástico: W_el = 557.0 cm^3 = 5.57e-4 m^3.
            - Módulo resistente plástico: W_pl = 628.4 cm^3 = 6.284e-4 m^3.
            - Factor de forma de la sección: k_shape = W_pl / W_el = 628.4 / 557.0 = 1.128187.

        Formulación analítica:
          1. Momento elástico de fluencia:
             M_el,Rd = W_el * Fy = 557.0e-6 m^3 * 355.0e6 N/m^2 / 1e3 = 197.735 kN*m.
          2. Momento plástico nominal:
             M_pl,Rd = M_n = W_pl * Fy = 628.4e-6 m^3 * 355.0e6 N/m^2 / 1e3 = 223.082 kN*m.
          3. Capacidad de cálculo según Eurocódigo 3 (Clase 1/2, gamma_M0 = 1.00):
             M_c,Rd = M_pl,Rd / gamma_M0 = 223.082 kN*m.
          4. Capacidad de cálculo según AISC 360-16 LRFD (phi_b = 0.90):
             phi_b * M_n = 0.90 * 223.082 = 200.7738 kN*m.
        """
        Fy = 355.0  # MPa (N/mm2)
        Wel_cm3 = 557.0
        Wpl_cm3 = 628.4

        Wel_m3 = Wel_cm3 * 1e-6
        Wpl_m3 = Wpl_cm3 * 1e-6

        # Factor de forma (reserva plástica de flexión)
        shape_factor = Wpl_cm3 / Wel_cm3
        assert shape_factor == pytest.approx(1.128187, rel=1e-5)

        # Momento elástico
        M_el_kNm = (Wel_m3 * (Fy * 1e6)) / 1e3
        assert M_el_kNm == pytest.approx(197.735, rel=1e-5)

        # Momento plástico nominal
        M_pl_kNm = (Wpl_m3 * (Fy * 1e6)) / 1e3
        assert M_pl_kNm == pytest.approx(223.082, rel=1e-5)

        # Eurocódigo 3 (gamma_M0 = 1.0)
        gamma_M0 = 1.0
        M_Rd_ec3 = M_pl_kNm / gamma_M0
        assert M_Rd_ec3 == pytest.approx(223.082, rel=1e-5)

        # AISC 360-16 (phi_b = 0.90)
        phi_b = 0.90
        M_design_aisc = phi_b * M_pl_kNm
        assert M_design_aisc == pytest.approx(200.7738, rel=1e-5)

    def test_golden_2_eurocode3_column_buckling_reduction_factor(self) -> None:
        """Golden 2: Factor de reducción por pandeo flexional chi según Eurocódigo 3 Cl. 6.3.1.2.

        Modelo:
          Columna biarticulada HEB 200 / S355 de longitud L = 4.50 m:
            - Área transversal: A = 78.08 cm^2 = 7.808e-3 m^2.
            - Inercia eje débil (z-z): I_z = 2003.0 cm^4 = 2.003e-5 m^4.
            - Radio de giro débil: i_z = sqrt(I_z / A) = sqrt(2003 / 78.08) = 5.06487 cm = 5.06487e-2 m.
            - Límite elástico: Fy = 355.0 MPa, Módulo de Young E = 210000.0 MPa.
            - Curva de pandeo para HEB 200 eje débil (h/b = 200/200 <= 1.2, tf = 15 mm <= 100 mm):
              Curva 'c' -> Factor de imperfección alpha = 0.49.

        Derivación analítica paso a paso:
          1. Esbeltez Euler:
             lambda_1 = pi * sqrt(E / Fy) = pi * sqrt(210000 / 355) = pi * 24.3218 = 76.4087.
          2. Esbeltez geométrica:
             lambda = L_cr / i_z = 4.50 / 0.0506487 = 88.8473.
          3. Esbeltez adimensional:
             lambda_bar = lambda / lambda_1 = 88.8473 / 76.4087 = 1.16279.
             Alternativamente: N_cr = pi^2 * E * I_z / L^2 = pi^2 * 210e9 * 2.003e-5 / 4.5^2 = 2050.29 kN.
             N_pl = A * Fy = 7.808e-3 * 355e6 / 1e3 = 2771.84 kN.
             lambda_bar = sqrt(N_pl / N_cr) = sqrt(2771.84 / 2050.29) = sqrt(1.351926) = 1.16272.
          4. Coeficiente auxiliar Phi:
             Phi = 0.5 * [ 1 + alpha * (lambda_bar - 0.2) + lambda_bar^2 ]
                 = 0.5 * [ 1 + 0.49 * (1.16272 - 0.2) + 1.16272^2 ]
                 = 0.5 * [ 1 + 0.49 * 0.96272 + 1.35192 ]
                 = 0.5 * [ 1 + 0.47173 + 1.35192 ]
                 = 0.5 * 2.82365 = 1.41183.
          5. Factor de reducción chi:
             chi = 1 / [ Phi + sqrt(Phi^2 - lambda_bar^2) ]
                 = 1 / [ 1.41183 + sqrt(1.41183^2 - 1.16272^2) ]
                 = 1 / [ 1.41183 + sqrt(1.99325 - 1.35192) ]
                 = 1 / [ 1.41183 + sqrt(0.64133) ]
                 = 1 / [ 1.41183 + 0.80083 ]
                 = 1 / 2.21266 = 0.45194.
          6. Resistencia de cálculo al pandeo (gamma_M1 = 1.00):
             N_b,Rd = chi * A * Fy / gamma_M1 = 0.45194 * 2771.84 kN = 1252.71 kN.
        """
        E = 210000.0   # MPa
        Fy = 355.0     # MPa
        A_m2 = 78.08e-4  # 78.08 cm2
        Iz_m4 = 2003.0e-8 # 2003 cm4
        L_cr = 4.50     # m
        alpha = 0.49    # Curva c

        # Carga elástica de pandeo de Euler
        N_cr_N = (math.pi**2 * (E * 1e6) * Iz_m4) / (L_cr**2)
        N_cr_kN = N_cr_N / 1e3
        assert N_cr_kN == pytest.approx(2050.29, rel=1e-3)

        # Carga plástica axial
        N_pl_N = A_m2 * (Fy * 1e6)
        N_pl_kN = N_pl_N / 1e3
        assert N_pl_kN == pytest.approx(2771.84, rel=1e-3)

        # Esbeltez adimensional lambda_bar
        lambda_bar = math.sqrt(N_pl_kN / N_cr_kN)
        assert lambda_bar == pytest.approx(1.16272, rel=1e-4)

        # Coeficiente Phi
        Phi = 0.5 * (1.0 + alpha * (lambda_bar - 0.2) + lambda_bar**2)
        assert Phi == pytest.approx(1.41183, rel=1e-4)

        # Factor de reducción chi
        chi = 1.0 / (Phi + math.sqrt(Phi**2 - lambda_bar**2))
        assert chi <= 1.0
        assert chi == pytest.approx(0.45194, rel=1e-3)

        # Resistencia a compresión con pandeo N_b,Rd
        gamma_M1 = 1.00
        N_b_Rd_kN = (chi * N_pl_kN) / gamma_M1
        assert N_b_Rd_kN == pytest.approx(1252.71, rel=1e-3)
