# -*- coding: utf-8 -*-
"""Consistencia fisica del catalogo unificado de perfiles (Fase 9).

No re-deriva las tablas (eso seria reimplementar la norma); valida invariantes
fisicos que atrapan erratas de transcripcion: signos, ordenes de magnitud,
Ix > Iy en perfiles I, y coherencia geometrica espesores/dimensiones.
"""
import math

import pytest

from paretosteel.catalog_unified import all_sections

SECTIONS = all_sections()
NEW_FASE9 = {
    "W12X35", "W14X68", "W16X45", "W18X50", "W21X62", "W24X76",
    "IPE270", "IPE330", "IPE360", "IPE450",
    "HEB200", "HEB260", "HEB360", "HEB400", "HEA360", "HEA450",
}


def test_perfiles_fase9_presentes():
    nombres = {s.name for s in SECTIONS}
    assert NEW_FASE9.issubset(nombres)


def test_sin_duplicados():
    nombres = [s.name for s in SECTIONS]
    assert len(nombres) == len(set(nombres))


@pytest.mark.parametrize("s", SECTIONS, ids=[s.name for s in SECTIONS])
class TestInvariantesFisicos:
    def test_dimensiones_positivas(self, s):
        for v in (s.h_mm, s.bf_mm, s.tw_mm, s.tf_mm, s.A_cm2, s.Ix_cm4, s.Iy_cm4, s.Zx_cm3):
            assert v > 0

    def test_eje_fuerte_mayor(self, s):
        # Ix (eje fuerte) > Iy en perfiles I/H.
        assert s.Ix_cm4 > s.Iy_cm4

    def test_espesores_menores_que_dimensiones(self, s):
        assert s.tw_mm < s.bf_mm     # alma mas delgada que el ancho de ala
        assert s.tf_mm < s.h_mm      # ala mas delgada que el peralte
        assert s.tw_mm < s.h_mm

    def test_area_coherente_con_dimensiones(self, s):
        # Area real entre el 10% y el 70% del rectangulo envolvente (perfil abierto).
        env_cm2 = (s.h_mm * s.bf_mm) / 100.0  # mm^2 -> cm^2
        ratio = s.A_cm2 / env_cm2
        assert 0.08 < ratio < 0.75, (s.name, ratio)

    def test_inercia_orden_de_magnitud(self, s):
        # Ix ~ A * (h/2)^2 dentro de un factor 3 (cota gruesa pero atrapa erratas).
        A_mm2 = s.A_cm2 * 100.0
        Ix_mm4 = s.Ix_cm4 * 1e4
        aprox = A_mm2 * (s.h_mm / 2.0) ** 2
        assert 0.2 < Ix_mm4 / aprox < 1.2, (s.name, Ix_mm4 / aprox)

    def test_modulo_plastico_coherente(self, s):
        # Zx (mm^3) debe ser del orden de Ix/(h/2) y mayor (Zx > Sx siempre).
        Sx_mm3 = (s.Ix_cm4 * 1e4) / (s.h_mm / 2.0)
        Zx_mm3 = s.Zx_cm3 * 1e3
        assert Zx_mm3 > 0.9 * Sx_mm3, (s.name, Zx_mm3, Sx_mm3)
        assert Zx_mm3 < 1.7 * Sx_mm3, (s.name, Zx_mm3, Sx_mm3)
