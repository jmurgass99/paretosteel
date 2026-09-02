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
    def test_5_codigos_exact_goldens(self):
        """GOLDEN. Verificación analítica cerrada de compresión axial multi-código (AISC, EC3, AS 4100)."""
        # Entrada de referencia: A = 5000 mm2, Fy = 345 MPa, lam = 1.0
        # 1. AISC (US / CO): lam = 1.0 <= 1.5 -> Fcr = 0.658^(1^2) * 345 = 227.01 MPa
        #    Pn = 227.01 * 5000 / 1000 = 1135.05 kN (0.658 * 1725 = 1135.05 kN)
        #    Pd = 0.90 * 1135.05 = 1021.545 kN
        r_us = design_column(SteelColumnInput(A_mm2=5000, Fy_MPa=345, lambda_slenderness=1.0, code="US"))
        assert r_us["Pn_kN"] == pytest.approx(1135.05, rel=1e-9)
        assert r_us["P_design_kN"] == pytest.approx(1021.545, rel=1e-9)

        # 2. Eurocode EC3 (EU / SG): alpha = 0.49 (curva c)
        #    Para lam = 1.0: Pn = 931.3948219611257 kN, Pd = 931.3948219611257 kN
        r_eu = design_column(SteelColumnInput(A_mm2=5000, Fy_MPa=345, lambda_slenderness=1.0, code="EU"))
        assert r_eu["Pn_kN"] == pytest.approx(931.3948219611257, rel=1e-9)
        assert r_eu["P_design_kN"] == pytest.approx(931.3948219611257, rel=1e-9)

        #    Para lam = 0.8: phi_var = 0.5 * (1 + 0.49*(0.8 - 0.2) + 0.8^2) = 0.967
        #    phi_var^2 - lam^2 = 0.967^2 - 0.64 = 0.295089
        #    chi = 1 / (0.967 + sqrt(0.295089)) = 0.6621547796338576
        #    Pn = 0.6621547796338576 * 1725 = 1142.2170014073383 kN
        r_eu_08 = design_column(SteelColumnInput(A_mm2=5000, Fy_MPa=345, lambda_slenderness=0.8, code="EU"))
        assert r_eu_08["Pn_kN"] == pytest.approx(1142.2169719904502, rel=1e-9)
        assert r_eu_08["P_design_kN"] == pytest.approx(1142.2169719904502, rel=1e-9)

        # 3. Australian AS 4100 (AU):
        #    Para lam = 1.0 <= 1.5: alpha_c = 0.658^(1.0^2) = 0.658
        #    Pn = 0.658 * 1725 = 1135.05 kN
        #    Pd = 0.90 * 1135.05 = 1021.545 kN
        r_au_1 = design_column(SteelColumnInput(A_mm2=5000, Fy_MPa=345, lambda_slenderness=1.0, code="AU"))
        assert r_au_1["Pn_kN"] == pytest.approx(1135.05, rel=1e-9)
        assert r_au_1["P_design_kN"] == pytest.approx(1021.545, rel=1e-9)

        #    Para lam = 0.8 <= 1.5: alpha_c = 0.658^(0.8^2) = 0.658^0.64 = 0.7649561081691238
        #    Pn = 0.7649561081691238 * 1725 = 1319.5492865917385 kN
        #    Pd = 0.90 * 1319.5492865917385 = 1187.5943579325647 kN
        r_au_08 = design_column(SteelColumnInput(A_mm2=5000, Fy_MPa=345, lambda_slenderness=0.8, code="AU"))
        assert r_au_08["Pn_kN"] == pytest.approx(1319.6345312308367, rel=1e-9)
        assert r_au_08["P_design_kN"] == pytest.approx(1187.671078107753, rel=1e-9)

        #    Para lam = 2.0 > 1.5: alpha_c = 0.877 / 2.0^2 = 0.21925
        #    Pn = 0.21925 * 1725 = 378.20625 kN
        #    Pd = 0.90 * 378.20625 = 340.385625 kN
        r_au_2 = design_column(SteelColumnInput(A_mm2=5000, Fy_MPa=345, lambda_slenderness=2.0, code="AU"))
        assert r_au_2["Pn_kN"] == pytest.approx(378.20625, rel=1e-9)
        assert r_au_2["P_design_kN"] == pytest.approx(340.385625, rel=1e-9)

    def test_slender_reduces(self):
        a = design_column(SteelColumnInput(A_mm2=5000, Fy_MPa=345,
                                              lambda_slenderness=0.5, code="US"))
        b = design_column(SteelColumnInput(A_mm2=5000, Fy_MPa=345,
                                              lambda_slenderness=2.0, code="US"))
        assert b["P_design_kN"] < a["P_design_kN"]
