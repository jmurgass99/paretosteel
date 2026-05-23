"""Tests del catálogo AISC v16.0 completo."""
from __future__ import annotations

import pytest

from steeloptimizerjm.catalogs import (
    ALL_CATALOGS,
    SteelProfile,
    filter_profiles,
)
from steeloptimizerjm.catalogs_aisc_full import (
    AISC_W_FULL,
    AISC_HSS_FULL,
    load_aisc_v16,
)


def test_catalog_loads():
    """El catálogo carga sin errores y tiene perfiles."""
    cat = load_aisc_v16()
    assert isinstance(cat, dict)
    assert len(cat) > 0


def test_w_full_count():
    """Sanity check: AISC tiene ~289 W shapes; aceptamos >= 100."""
    assert len(AISC_W_FULL) >= 100, (
        f"Esperaba >= 100 W shapes, encontré {len(AISC_W_FULL)}"
    )


def test_profiles_have_positive_properties():
    """Todos los perfiles tienen propiedades físicas válidas."""
    for designation, prof in AISC_W_FULL.items():
        assert isinstance(prof, SteelProfile), designation
        assert prof.A > 0, f"{designation}: A no positivo"
        assert prof.Ix > 0, f"{designation}: Ix no positivo"
        assert prof.weight_per_m > 0, f"{designation}: weight no positivo"


def test_w14x90_present_and_consistent_with_manual():
    """W14X90 debe estar y coincidir (±5%) con el catálogo manual SI."""
    assert "W14X90" in AISC_W_FULL
    full = AISC_W_FULL["W14X90"]
    # Valores del catálogo manual (CATALOG_AISC_W)
    expected = {
        "weight_per_m": 134.0,    # kg/m
        "A": 0.01702,             # m²
        "Ix": 4.16e-4,            # m⁴
        "d": 0.356,               # m
        "bf": 0.369,              # m
    }
    for attr, exp in expected.items():
        got = getattr(full, attr)
        rel = abs(got - exp) / exp
        assert rel < 0.05, (
            f"W14X90.{attr}: manual={exp}, AISC_v16={got} (rel diff {rel:.2%})"
        )


def test_filter_profiles_with_full_catalog():
    """filter_profiles ahora ve el catálogo completo y retorna subset positivo."""
    assert "W_FULL" in ALL_CATALOGS
    big = filter_profiles(family="W", min_Ix=4e-4)
    assert len(big) > 0
    for p in big:
        assert p.Ix >= 4e-4
        assert p.family == "W"


def test_hss_present():
    """HSS family debe tener perfiles (AISC tiene >700)."""
    assert len(AISC_HSS_FULL) > 100
