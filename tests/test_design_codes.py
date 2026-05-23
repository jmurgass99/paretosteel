"""Tests design beam/column multi-código."""
import pytest

from steeloptimizerjm.design_codes import (
    SteelBeamInput, SteelColumnInput, design_beam_compact, design_column,
)


class TestBeam:
    def test_5_codigos(self):
        for c in ("US", "CO", "EU", "SG", "AU"):
            r = design_beam_compact(SteelBeamInput(
                plastic_modulus_mm3=2.5e6, Fy_MPa=345, code=c,
            ))
            assert r.M_design_kNm > 0

    def test_eu_no_reduce(self):
        r = design_beam_compact(SteelBeamInput(
            plastic_modulus_mm3=1e6, Fy_MPa=355, code="EU",
        ))
        assert r.M_design_kNm == r.Mn_kNm

    def test_invalido(self):
        with pytest.raises(ValueError):
            design_beam_compact(SteelBeamInput(
                plastic_modulus_mm3=1e6, Fy_MPa=355, code="XX",
            ))


class TestColumn:
    def test_5_codigos(self):
        for c in ("US", "CO", "EU", "SG", "AU"):
            r = design_column(SteelColumnInput(
                A_mm2=5000, Fy_MPa=345, lambda_slenderness=1.0, code=c,
            ))
            assert r["P_design_kN"] > 0

    def test_slender_reduces(self):
        a = design_column(SteelColumnInput(A_mm2=5000, Fy_MPa=345,
                                              lambda_slenderness=0.5, code="US"))
        b = design_column(SteelColumnInput(A_mm2=5000, Fy_MPa=345,
                                              lambda_slenderness=2.0, code="US"))
        assert b["P_design_kN"] < a["P_design_kN"]
