"""Tests for AISC 360-22 Chapter H (Eq. H3-6) combined torsion-shear-flexure-axial in HSS."""
from __future__ import annotations

import math
import pytest

from paretosteel.aisc360_22_hss import (
    Aisc360HssH36Input,
    compute_hss_torsional_constant_c,
    compute_rect_hss_design_torsion_strength,
    verify_aisc360_22_hss_h3_6,
)


def test_hss_torsional_constant_rectangular_and_round() -> None:
    c_round = compute_hss_torsional_constant_c("round", b_or_d=200.0, t_des=10.0)
    expected_round = math.pi * (190.0**2) * 10.0 / 2.0
    assert c_round == pytest.approx(expected_round)

    c_rect = compute_hss_torsional_constant_c("rectangular", b_or_d=200.0, h=300.0, t_des=10.0)
    expected_rect = 2.0 * 190.0 * 290.0 * 10.0 - 4.5 * (4.0 - math.pi) * (10.0**3)
    assert c_rect == pytest.approx(expected_rect)


def test_verify_aisc360_22_hss_h3_6_interaction() -> None:
    t_c = compute_rect_hss_design_torsion_strength(b=200.0, h=300.0, t_des=10.0, fy=345.0)
    assert t_c > 150.0

    inp = Aisc360HssH36Input(
        p_r=400.0,
        p_c=2000.0,   # 0.20
        m_rx=90.0,
        m_cx=300.0,   # 0.30
        m_ry=30.0,
        m_cy=200.0,   # 0.15 -> normal_stress_term = 0.65
        v_r=100.0,
        v_c=500.0,    # 0.20
        t_r=0.30 * t_c,
        t_c=t_c,      # 0.30 -> (0.20 + 0.30)^2 = 0.25 -> total = 0.90 <= 1.0
    )
    res = verify_aisc360_22_hss_h3_6(inp)
    assert res.status == "CALCULADO"
    assert res.normal_stress_term == pytest.approx(0.65)
    assert res.shear_torsion_term_squared == pytest.approx(0.25)
    assert res.interaction_h3_6 == pytest.approx(0.90)
    assert res.passes is True
