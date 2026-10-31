"""Tests for Eurocode 3 Second Generation (EN 1993-1-1:2022) semi-compact & S700/S960 check."""
from __future__ import annotations

import math
import pytest

from paretosteel.ec3_2022_2g import (
    EC3_2022_STEEL_GRADES,
    Ec3SemiCompactInput,
    compute_epsilon_ec3_2022,
    verify_member_ec3_2022,
)


def test_ec3_2022_ultra_high_strength_grades() -> None:
    assert "S700" in EC3_2022_STEEL_GRADES
    assert "S960" in EC3_2022_STEEL_GRADES
    assert compute_epsilon_ec3_2022(960.0) == pytest.approx(math.sqrt(235.0 / 960.0))


def test_semi_compact_class3_continuous_interpolation_gain() -> None:
    # Choose flange slenderness halfway between Class 2 (10*eps) and Class 3 (14*eps): 12*eps
    fy = 355.0
    eps = compute_epsilon_ec3_2022(fy)
    inp = Ec3SemiCompactInput(
        c_flange=12.0 * eps * 10.0,
        t_flange=10.0,
        c_web=60.0 * eps * 8.0,
        t_web=8.0,
        w_pl=1_150_000.0,
        w_el=1_000_000.0,
        area=8500.0,
        fy=fy,
        m_ed=360.0,
    )
    res = verify_member_ec3_2022(inp)
    assert res.section_class == 3
    # Midpoint interpolation between W_pl (1.15e6) and W_el (1.00e6) -> 1.075e6 mm3
    assert res.w_eff_design == pytest.approx(1_075_000.0, rel=1e-4)
    assert res.m_rd_2022 > res.m_rd_2005_legacy
    assert res.capacity_gain_pct == pytest.approx(7.5, rel=1e-2)
    assert res.passes is True


def test_s700_buckling_curve_a0() -> None:
    inp = Ec3SemiCompactInput(
        c_flange=70.0,
        t_flange=15.0,
        c_web=250.0,
        t_web=12.0,
        w_pl=1_400_000.0,
        w_el=1_220_000.0,
        area=11_000.0,
        fy=700.0,
        m_ed=200.0,
        n_ed=3500.0,
        n_cr=12_000.0,
        buckling_curve="a0",
    )
    res = verify_member_ec3_2022(inp)
    assert res.status == "CALCULADO"
    assert 0.5 < res.chi_buckling < 1.0
    assert res.n_b_rd > 4500.0
    assert res.passes is True
