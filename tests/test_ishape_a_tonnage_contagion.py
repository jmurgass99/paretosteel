# -*- coding: utf-8 -*-
"""test_ishape_a_tonnage_contagion.py — Caracterización del contagio de IShape.A fuera de fastsap.

DOCUMENTACIÓN DE CONTAGIO (AG29 - A1):
======================================
fastsap.section_catalog.IShape calcula el área transversal mediante la fórmula de placas:
    A_plates = 2 * b * tf + (h - 2 * tf) * tw
omitiendo los acuerdos de raíz (fillets r):
    A_fillets = (4 - pi) * r^2

Para un perfil IPE 300 (h=300 mm, b=150 mm, tw=7.1 mm, tf=10.7 mm, r=15 mm):
    A_plates   = 2 * 150 * 10.7 + (300 - 2 * 10.7) * 7.1
               = 3210 + 278.6 * 7.1 = 3210 + 1978.06 = 5188.06 mm^2 = 51.8806 cm^2
    A_fillets  = (4 - pi) * 15^2 = (4 - 3.14159265...) * 225 = 0.858407 * 225 = 193.14 mm^2 = 1.9314 cm^2
    A_tabulado = 53.81 cm^2 (EN 10365:2020 / ArcelorMittal Sales Programme 2023)

SUBESTIMACIÓN:
    Error = (51.8806 - 53.81) / 53.81 = -3.5856 % (~3.6 % de subestimación).

ALCANCE EN ParetoSteel:
----------------------------
ParetoSteel consume `fastsap.section_catalog.get_section()` a través de
`paretosteel.section_bridge`. Toda estimación de masa (M = rho * A * L) o
coste de estructura que utilice esta propiedad subestima el tonelaje en un 3.6%
para perfiles IPE 300 y proporciones similares en perfiles laminados en caliente.

Este test NO arregla fastsap (prohibido modificar fastsap en AG29); fija el
comportamiento observado y documenta cuantitativamente el error transmitido.
"""
from __future__ import annotations
import pytest as _pytest_skip
_pytest_skip.importorskip("fastsap")  # dependencia externa opcional: sin ella estos tests se omiten

import pytest
from fastsap.section_catalog import get_section


class TestIShapeAContagionSteelOptimizer:
    @pytest.mark.characterization
    def test_ishape_a_ipe300_underestimates_en10365_tonnage(self) -> None:
        """Caracterización: fija que get_section('IPE 300').A subestima un 3.59% frente a EN 10365."""
        sec = get_section("IPE 300")
        A_m2 = sec.A
        A_cm2 = A_m2 * 1e4

        # Valor devuelto por fastsap (solo placas): 51.8806 cm2
        assert pytest.approx(A_cm2, rel=1e-4) == 51.8806

        # Valor tabulado normativo EN 10365: 53.81 cm2
        A_en10365_cm2 = 53.81
        delta_pct = ((A_cm2 - A_en10365_cm2) / A_en10365_cm2) * 100.0

        # Subestimación exacta del 3.5856% en tonelaje
        assert pytest.approx(delta_pct, rel=1e-2) == -3.59
        assert delta_pct < -3.5  # Subestima más del 3.5%

        # Impacto en masa de una viga de L = 6.0 m (acero rho = 7850 kg/m3)
        rho_steel = 7850.0  # kg/m3
        length = 6.0  # m
        mass_calculated_kg = A_m2 * length * rho_steel
        mass_real_en10365_kg = (A_en10365_cm2 * 1e-4) * length * rho_steel

        # Masa calculada: 244.36 kg vs real 253.44 kg -> pérdida de 9.09 kg por viga
        assert pytest.approx(mass_calculated_kg, rel=1e-3) == 244.357
        assert pytest.approx(mass_real_en10365_kg, rel=1e-3) == 253.445
        assert (mass_real_en10365_kg - mass_calculated_kg) > 9.0
