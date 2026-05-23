"""Tests para la memoria de justificacion del perfil (SO-003).

Cubre:
    - render_profile_memo genera output
    - Output contiene nombre de la seccion
    - Ratios correctos
    - Veredicto CUMPLE / NO CUMPLE
    - LaTeX generado (con o sin handcalcs)
    - memo_from_beam_candidate integracion con beam_selector
"""
from __future__ import annotations

import math
import pytest

from steeloptimizerjm.memos.profile_justification import (
    ProfileMemoInput,
    ProfileMemoResult,
    render_profile_memo,
    memo_from_beam_candidate,
)


def _make_input(**overrides) -> ProfileMemoInput:
    """Helper para crear inputs con valores por defecto razonables."""
    defaults = dict(
        section_name="W14X30",
        span_m=8.0,
        support_condition="simple",
        load_type="distribuida",
        w_kN_m=30.0,
        A_cm2=57.0,
        Ix_cm4=12000.0,
        Sx_cm3=684.0,
        Zx_cm3=750.0,
        rx_cm=14.5,
        ry_cm=3.8,
        Mu_kNm=200.0,
        Vu_kN=100.0,
        Mn_kNm=300.0,
        Vn_kN=400.0,
        delta_mm=15.0,
        delta_limit_mm=22.2,
        Fy_MPa=345.0,
        code="US",
    )
    defaults.update(overrides)
    return ProfileMemoInput(**defaults)


# -----------------------------------------------------------------------
# Tests de render_profile_memo
# -----------------------------------------------------------------------

class TestRenderProfileMemo:

    def test_generates_output(self):
        res = render_profile_memo(_make_input())
        assert isinstance(res, ProfileMemoResult)
        assert len(res.markdown) > 0
        assert len(res.latex) > 0

    def test_contains_section_name(self):
        res = render_profile_memo(_make_input(section_name="W21X44"))
        assert "W21X44" in res.markdown

    def test_contains_section_name_in_title(self):
        res = render_profile_memo(_make_input(section_name="IPE300"))
        assert "IPE300" in res.section_name
        assert "IPE300" in res.markdown

    def test_cumple_flexion(self):
        res = render_profile_memo(_make_input(Mu_kNm=200.0, Mn_kNm=300.0))
        phi_Mn = 0.9 * 300.0
        expected_ratio = 200.0 / phi_Mn
        assert res.ratio_flexion == pytest.approx(expected_ratio, rel=1e-6)
        assert res.cumple_flexion

    def test_no_cumple_flexion(self):
        res = render_profile_memo(_make_input(Mu_kNm=500.0, Mn_kNm=300.0))
        assert not res.cumple_flexion
        assert res.ratio_flexion > 1.0

    def test_cumple_cortante(self):
        res = render_profile_memo(_make_input(Vu_kN=100.0, Vn_kN=400.0))
        phi_Vn = 0.9 * 400.0
        expected = 100.0 / phi_Vn
        assert res.ratio_cortante == pytest.approx(expected, rel=1e-6)
        assert res.cumple_cortante

    def test_no_cumple_cortante(self):
        res = render_profile_memo(_make_input(Vu_kN=500.0, Vn_kN=100.0))
        assert not res.cumple_cortante

    def test_cumple_deflexion(self):
        res = render_profile_memo(_make_input(delta_mm=15.0, delta_limit_mm=22.2))
        assert res.ratio_deflexion == pytest.approx(15.0 / 22.2, rel=1e-6)
        assert res.cumple_deflexion

    def test_no_cumple_deflexion(self):
        res = render_profile_memo(_make_input(delta_mm=30.0, delta_limit_mm=22.2))
        assert not res.cumple_deflexion

    def test_cumple_global(self):
        res = render_profile_memo(_make_input(
            Mu_kNm=100.0, Mn_kNm=300.0,
            Vu_kN=50.0, Vn_kN=400.0,
            delta_mm=10.0, delta_limit_mm=22.2,
        ))
        assert res.cumple

    def test_no_cumple_global_por_flexion(self):
        res = render_profile_memo(_make_input(Mu_kNm=500.0, Mn_kNm=300.0))
        assert not res.cumple

    def test_veredicto_cumple_en_markdown(self):
        res = render_profile_memo(_make_input(
            Mu_kNm=100.0, Mn_kNm=300.0,
            Vu_kN=50.0, Vn_kN=400.0,
            delta_mm=10.0, delta_limit_mm=22.2,
        ))
        assert "CUMPLE" in res.markdown

    def test_veredicto_no_cumple_en_markdown(self):
        res = render_profile_memo(_make_input(Mu_kNm=500.0, Mn_kNm=300.0))
        assert "NO CUMPLE" in res.markdown


# -----------------------------------------------------------------------
# Tests de contenido del markdown
# -----------------------------------------------------------------------

class TestMarkdownContent:

    def test_has_section_properties_table(self):
        res = render_profile_memo(_make_input(A_cm2=57.0, Ix_cm4=12000.0))
        assert "57.00" in res.markdown
        assert "12000.00" in res.markdown

    def test_has_flexion_section(self):
        res = render_profile_memo(_make_input())
        assert "Flexion" in res.markdown or "flexion" in res.markdown.lower()

    def test_has_cortante_section(self):
        res = render_profile_memo(_make_input())
        assert "Cortante" in res.markdown or "cortante" in res.markdown.lower()

    def test_has_deflexion_section(self):
        res = render_profile_memo(_make_input())
        assert "Deflexion" in res.markdown or "deflexion" in res.markdown.lower()

    def test_has_datos_entrada(self):
        res = render_profile_memo(_make_input(span_m=8.0, w_kN_m=30.0))
        assert "8.00" in res.markdown
        assert "30.00" in res.markdown

    def test_has_veredicto_section(self):
        res = render_profile_memo(_make_input())
        assert "Veredicto" in res.markdown

    def test_span_displayed(self):
        res = render_profile_memo(_make_input(span_m=12.5))
        assert "12.50" in res.markdown

    def test_fy_displayed(self):
        res = render_profile_memo(_make_input(Fy_MPa=250.0))
        assert "250.0" in res.markdown


# -----------------------------------------------------------------------
# Tests de LaTeX
# -----------------------------------------------------------------------

class TestLatexOutput:

    def test_latex_not_empty(self):
        res = render_profile_memo(_make_input())
        assert len(res.latex) > 0

    def test_latex_contains_flexion(self):
        res = render_profile_memo(_make_input())
        # Debe contener algo del calculo de flexion
        assert "Flexion" in res.latex or "M" in res.latex

    def test_latex_contains_cortante(self):
        res = render_profile_memo(_make_input())
        assert "Cortante" in res.latex or "V" in res.latex


# -----------------------------------------------------------------------
# Tests de codigo EU
# -----------------------------------------------------------------------

class TestCodigoEU:

    def test_eu_phi_1_0(self):
        """En Eurocodigo gamma_M0 = 1.0 -> factor efectivo = 1.0."""
        res = render_profile_memo(_make_input(
            Mu_kNm=200.0, Mn_kNm=300.0,
            Vu_kN=100.0, Vn_kN=400.0,
            code="EU",
        ))
        # ratio_M = 200 / (1.0 * 300) = 0.667
        assert res.ratio_flexion == pytest.approx(200.0 / 300.0, rel=1e-6)


# -----------------------------------------------------------------------
# Tests de memo_from_beam_candidate
# -----------------------------------------------------------------------

class TestMemoFromBeamCandidate:

    def test_integration_with_beam_selector(self):
        from steeloptimizerjm.beam_selector import BeamDemand, optimize_beam

        result = optimize_beam(BeamDemand(M_kNm=120.0, V_kN=50.0))
        assert result.selected is not None

        memo = memo_from_beam_candidate(
            result.selected,
            span_m=8.0,
            w_kN_m=15.0,
        )
        assert isinstance(memo, ProfileMemoResult)
        assert memo.section_name == result.selected.name
        assert result.selected.name in memo.markdown
        assert memo.cumple_flexion  # la seccion seleccionada debe cumplir

    def test_memo_contains_section_properties(self):
        from steeloptimizerjm.beam_selector import BeamDemand, optimize_beam

        result = optimize_beam(BeamDemand(M_kNm=120.0, V_kN=50.0))
        memo = memo_from_beam_candidate(
            result.selected, span_m=8.0, w_kN_m=15.0,
        )
        # Debe tener propiedades no nulas (al menos A)
        assert "A" in memo.markdown
        assert "Ix" in memo.markdown
