"""Tests castellated beams."""
from paretosteel.castellated import CastellatedInput, design_castellated


def test_db_aumenta():
    r = design_castellated(CastellatedInput(
        parent_db_mm=400, parent_bf_mm=200, parent_tf_mm=15, parent_tw_mm=10,
    ))
    assert r.db_castellated_mm == 600  # 1.5·400


def test_vierendeel_reduce():
    r = design_castellated(CastellatedInput(
        parent_db_mm=400, parent_bf_mm=200, parent_tf_mm=15, parent_tw_mm=10,
    ))
    assert r.Mn_post_kNm < r.Mn_pre_kNm
    assert 0.7 < r.capacity_ratio < 1.0


def test_alma_delgada_warning():
    r = design_castellated(CastellatedInput(
        parent_db_mm=400, parent_bf_mm=200, parent_tf_mm=15, parent_tw_mm=4,
    ))
    assert any("Vierendeel" in n for n in r.notes)
