# -*- coding: utf-8 -*-
"""Estado limite de servicio por deflexion (AISC / IBC)."""
import pytest

from paretosteel.deflection import (
    check_deflection,
    deflection_point_center,
    deflection_udl,
    required_I_udl,
)


class TestDeflectionFormulas:
    def test_udl_formula(self):
        # 5wL^4/384EI
        w, L, I, E = 10.0, 6000.0, 1.0e8, 200000.0
        assert deflection_udl(w, L, I, E) == pytest.approx(5 * w * L ** 4 / (384 * E * I), rel=1e-12)

    def test_puntual_formula(self):
        P, L, I, E = 20000.0, 6000.0, 1.0e8, 200000.0
        assert deflection_point_center(P, L, I, E) == pytest.approx(P * L ** 3 / (48 * E * I), rel=1e-12)

    def test_inercia_mayor_menos_deflexion(self):
        d1 = deflection_udl(10.0, 6000.0, 1.0e8)
        d2 = deflection_udl(10.0, 6000.0, 2.0e8)
        assert d2 == pytest.approx(d1 / 2.0, rel=1e-12)


class TestCheck:
    def test_cumple_L360(self):
        L = 6000.0
        c = check_deflection(L / 400.0, L, 360.0)  # menor que L/360
        assert c.ok and c.ratio < 1.0

    def test_no_cumple(self):
        L = 6000.0
        c = check_deflection(L / 300.0, L, 360.0)  # mayor que L/360
        assert not c.ok and c.ratio > 1.0

    def test_limite_correcto(self):
        c = check_deflection(10.0, 7200.0, 240.0)
        assert c.limit_mm == pytest.approx(7200.0 / 240.0)


class TestRequiredI:
    def test_inercia_requerida_satisface_limite(self):
        w, L = 12.0, 6000.0
        I_req = required_I_udl(w, L, 360.0)
        # Con esa I, la deflexion debe ser exactamente L/360.
        d = deflection_udl(w, L, I_req)
        assert d == pytest.approx(L / 360.0, rel=1e-9)
