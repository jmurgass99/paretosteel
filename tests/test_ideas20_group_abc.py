"""Tests para IDEAS_20 grupos A/B/C en SteelOptimizerJm."""
import pytest


def test_justificacion_perfil_cumple():
    from steeloptimizerjm.memos.justificacion_perfil import (
        JustificacionInput, justificar,
    )
    res = justificar(JustificacionInput(
        perfil_nombre="W14X30", Mu_kNm=100, Vu_kN=50, Pu_kN=100,
        Mn_kNm=300, Vn_kN=400, Pn_kN=2000, code="US",
    ))
    assert res.cumple
    assert res.ratio_combinado <= 1.0


def test_justificacion_no_cumple():
    from steeloptimizerjm.memos.justificacion_perfil import (
        JustificacionInput, justificar,
    )
    res = justificar(JustificacionInput(
        perfil_nombre="X", Mu_kNm=500, Vu_kN=50, Pu_kN=100,
        Mn_kNm=300, Vn_kN=400, Pn_kN=2000, code="US",
    ))
    assert not res.cumple


def test_nsga2_dominates():
    from steeloptimizerjm.nsga2 import dominates
    assert dominates((1.0, 2.0), (2.0, 3.0))
    assert not dominates((1.0, 5.0), (2.0, 3.0))


def test_nsga2_run():
    from steeloptimizerjm.nsga2 import nsga2_run

    def obj(g):
        return (g[0] ** 2, (g[0] - 2) ** 2)
    final = nsga2_run(obj, n_genes=1, bounds=[(0.0, 4.0)], pop_size=10, n_gen=5)
    assert len(final) == 10
    assert all(hasattr(ind, "fitness") for ind in final)


def test_kriging_fits_constant():
    from steeloptimizerjm.surrogate import KrigingSurrogate
    X = [[0.0], [1.0], [2.0]]
    y = [1.0, 1.0, 1.0]
    s = KrigingSurrogate(X=X, y=y, length=1.0).fit()
    p = s.predict([1.5])
    assert abs(p - 1.0) < 0.5


def test_kriging_interpolacion():
    from steeloptimizerjm.surrogate import KrigingSurrogate
    X = [[0.0], [1.0], [2.0]]
    y = [0.0, 2.0, 4.0]
    s = KrigingSurrogate(X=X, y=y, length=2.0).fit()
    p = s.predict([1.0])
    assert abs(p - 2.0) < 1.0


def test_catalog_unified_filter():
    from steeloptimizerjm.catalog_unified import (
        all_sections, filter_by, find_lightest,
    )
    secs = all_sections()
    assert len(secs) >= 5
    en = filter_by(standard="EN")
    assert all(s.standard == "EN" for s in en)
    lit = find_lightest(min_Zx=500, standard="ASTM")
    assert lit is not None
    assert lit.Zx_cm3 >= 500


def test_cost_by_country():
    from steeloptimizerjm.cost_by_country import (
        get_cost, estimate_cost, list_countries,
    )
    assert "CL" in list_countries()
    c = get_cost("US")
    assert c.code == "US"
    cost = estimate_cost("CL", tons=10, stage="erected")
    assert cost > 0
    with pytest.raises(KeyError):
        get_cost("XX")


def test_price_sensitivity_v2():
    from steeloptimizerjm.price_sensitivity_v2 import (
        PriceSensitivityV2Input, monte_carlo,
    )
    res = monte_carlo(PriceSensitivityV2Input(
        base_tons=100, base_steel_usd_ton=1500,
        base_erection_usd_ton=500, base_transport_usd_ton=100,
        n_samples=500,
    ))
    assert res.P10_usd < res.P50_usd < res.P90_usd
    assert res.mean_usd > 0
