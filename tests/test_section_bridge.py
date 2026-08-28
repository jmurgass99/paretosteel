"""Tests for the SteelOptimizerJm <-> fastsap / jmstructural-common section bridge."""
from __future__ import annotations
import pytest

from steeloptimizerjm.section_bridge import (
    read_assigned_sections,
    apply_proposed_sections,
)
from jmstructural_common.model import (
    Model,
    Node,
    Element,
    SectionRef,
    Material,
)


class TestSectionOptimizerBridge:
    def test_read_assigned_sections_from_canonical_model(self) -> None:
        """Bridge accurately reads element-to-section mapping from a Model."""
        nodes = (
            Node("N1", 0.0, 0.0, 0.0),
            Node("N2", 6.0, 0.0, 0.0),
            Node("N3", 0.0, 0.0, 3.5),
            Node("N4", 6.0, 0.0, 3.5),
        )
        sec_col = SectionRef(name="HEB240", family="I")
        sec_beam = SectionRef(name="IPE300", family="I")
        elements = (
            Element("C1", "N1", "N3", section=sec_col, material="S355"),
            Element("C2", "N2", "N4", section=sec_col, material="S355"),
            Element("B1", "N3", "N4", section=sec_beam, material="S355"),
        )
        model = Model(
            nodes=nodes,
            elements=elements,
            materials=(Material("S355", E_MPa=210000.0, nu=0.3, fy_MPa=355.0, rho_kg_m3=7850.0),),
            sections=(sec_col, sec_beam),
        )

        assigned = read_assigned_sections(model)
        assert len(assigned) == 3
        assert assigned["C1"].name == "HEB240"
        assert assigned["C2"].name == "HEB240"
        assert assigned["B1"].name == "IPE300"

    def test_apply_proposed_sections_with_catalog_validation(self) -> None:
        """Proposed sections update the Model and are validated against catalog."""
        nodes = (
            Node("N1", 0.0, 0.0, 0.0),
            Node("N2", 0.0, 0.0, 3.0),
        )
        model = Model(
            nodes=nodes,
            elements=(Element("C1", "N1", "N2", section=SectionRef("IPE200", "I"), material="S355"),),
            materials=(Material("S355", E_MPa=210000.0, nu=0.3, fy_MPa=355.0, rho_kg_m3=7850.0),),
            sections=(SectionRef("IPE200", "I"),),
        )

        # Propose IPE300
        updated = apply_proposed_sections(
            model=model,
            proposed_sections={"C1": "IPE300"},
            validate_against_catalog=True,
        )
        assert updated.elements[0].section.name == "IPE300"
        assert any(s.name == "IPE300" for s in updated.sections)

    def test_apply_uncataloged_section_rejected_by_bridge(self) -> None:
        """Proposing an uncataloged section raises ValueError when catalog validation is active."""
        nodes = (
            Node("N1", 0.0, 0.0, 0.0),
            Node("N2", 0.0, 0.0, 3.0),
        )
        model = Model(
            nodes=nodes,
            elements=(Element("C1", "N1", "N2", section=SectionRef("IPE200", "I"), material="S355"),),
            materials=(Material("S355", E_MPa=210000.0, nu=0.3, fy_MPa=355.0, rho_kg_m3=7850.0),),
            sections=(SectionRef("IPE200", "I"),),
        )

        with pytest.raises(ValueError, match="no existe en el catálogo"):
            apply_proposed_sections(
                model=model,
                proposed_sections={"C1": "NON_EXISTENT_PROFILE_999"},
                validate_against_catalog=True,
            )
