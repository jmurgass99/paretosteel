# -*- coding: utf-8 -*-
"""test_section_bridge_units.py — Pruebas de unidades dimensionales para el puente SteelOptimizerJm.

Verifica rigurosamente la consistencia dimensional de secciones de acero:
    dimensiones h, b, tw, tf [mm] -> [m] en modelo CSI/SAP
    área A [cm^2] = 10^-4 m^2 -> [m^2]
    inercias I [cm^4] = 10^-8 m^4 -> [m^4]

Cálculo a mano independiente (Derivación analítica de fastsap.section_catalog):
  - IPE 300:
    h = 300 mm = 0.300 m, b = 150 mm = 0.150 m
    tw = 7.1 mm = 0.0071 m, tf = 10.7 mm = 0.0107 m
    Fórmula geométrica exacta de placas del catálogo:
      A = 2 * b * tf + (h - 2 * tf) * tw
        = 2 * 0.150 * 0.0107 + (0.300 - 2 * 0.0107) * 0.0071
        = 0.00321 + 0.2786 * 0.0071 = 0.00518806 m^2 (51.88 cm^2)
      Iz = 2 * (tf * b^3 / 12) + (h - 2 * tf) * tw^3 / 12 = 6.02706e-6 m^4
      Iy = (b * h^3 - (b - tw) * (h - 2*tf)^3) / 12 = 7.99899e-5 m^4
"""
from __future__ import annotations

import math
import pytest

from fastsap.section_catalog import get_section
from jmstructural_common.model import (
    Element,
    Material,
    Model,
    Node,
    Restraint,
    SectionRef,
)
from steeloptimizerjm.section_bridge import (
    apply_proposed_sections,
    read_assigned_sections,
)


class TestSectionBridgeDimensionalUnits:
    def test_catalog_profile_unit_conversions_hand_calculation(self) -> None:
        """Verifica las conversiones de unidades geométricas del catálogo (mm -> m, cm2 -> m2, cm4 -> m4)."""
        prop_ipe300 = get_section("IPE 300")

        # Derivaciones analíticas contra catálogo estándar europeo EN 10365 y fórmulas de placas de fastsap:
        # Altura h = 300 mm -> 0.300 m
        assert pytest.approx(prop_ipe300.h, rel=1e-6) == 0.300
        # Ancho b = 150 mm -> 0.150 m
        assert pytest.approx(prop_ipe300.b, rel=1e-6) == 0.150
        # Espesor alma tw = 7.1 mm -> 0.0071 m
        assert pytest.approx(prop_ipe300.tw, rel=1e-6) == 0.0071
        # Espesor ala tf = 10.7 mm -> 0.0107 m
        assert pytest.approx(prop_ipe300.tf, rel=1e-6) == 0.0107

        # Área analítica de placas: A = 2*b*tf + (h-2*tf)*tw = 0.00518806 m^2
        expected_A = 2.0 * 0.150 * 0.0107 + (0.300 - 2.0 * 0.0107) * 0.0071
        assert pytest.approx(prop_ipe300.A, rel=1e-5) == expected_A

        # Inercia débil Iz = 6.027e-6 m^4
        assert pytest.approx(prop_ipe300.Iz, rel=1e-3) == 6.027e-6

    def test_apply_proposed_sections_updates_model_cleanly(self) -> None:
        """Verifica la asignación y reemplazo de perfiles en un modelo canónico."""
        n1 = Node("N1", 0.0, 0.0, 0.0)
        n2 = Node("N2", 6.0, 0.0, 0.0)
        mat = Material("S275", 210000.0, 0.3, 275.0, 7850.0)
        sec_old = SectionRef("IPE 200", "I")
        el = Element("COL_1", "N1", "N2", sec_old, "S275")
        
        model = Model(
            nodes=(n1, n2),
            materials=(mat,),
            sections=(sec_old,),
            elements=(el,),
        )

        assigned_before = read_assigned_sections(model)
        assert assigned_before["COL_1"].name == "IPE 200"

        # Optimización propone IPE 300
        updated_model = apply_proposed_sections(
            model=model,
            proposed_sections={"COL_1": "IPE 300"},
            validate_against_catalog=True,
        )

        assigned_after = read_assigned_sections(updated_model)
        assert assigned_after["COL_1"].name == "IPE 300"
        assert any(s.name == "IPE 300" for s in updated_model.sections)

    def test_invalid_profile_name_raises_defensive_value_error(self) -> None:
        """Una sección inexistente en el catálogo debe ser rechazada inmediatamente."""
        n1 = Node("N1", 0.0, 0.0, 0.0)
        n2 = Node("N2", 6.0, 0.0, 0.0)
        sec = SectionRef("IPE 200", "I")
        el = Element("B1", "N1", "N2", sec, "A36")
        model = Model(nodes=(n1, n2), sections=(sec,), elements=(el,))

        with pytest.raises(ValueError, match="no existe en el catálogo"):
            apply_proposed_sections(
                model=model,
                proposed_sections={"B1": "PERFIL_INVENTADO_9999"},
                validate_against_catalog=True,
            )
