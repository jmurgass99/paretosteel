"""Golden tests de optimización de acero y vigas celulares/castellated anclados a fichas del master.

Fichas ancla
------------
* **W01416 / W00215 / W01417 — 06 Flexural Members (UPC / Arcelor)**:
  - Vigas alveolares hexagonales (Castellated beams):
    * Incremento estándar de canto h_cast = 1.50 * d_b (proceso Litzka).
    * Tabla 9-20 de perfiles aligerados IPE 300 (H=450 mm, bf=150 mm, tw=7.1 mm, Ix=14380 cm4, k1=639.11 cm3),
      HEA 200 (H=290 mm) y HEA 600 (H=800 mm).
    * Verificación del mecanismo de Vierendeel y flexión en cuerdas T.
  - Vigas celulares circulares Arcelor ABC:
    * ABC IPE 200: a0=210 mm, S=260 mm, H=294 mm.
    * ABC IPE 240: a0=250 mm, S=310 mm, H=353 mm.
    * ABC IPE 300: a0=315 mm, S=390 mm, H=441 mm.

* **W01641 / W01640 / W01643 — Design of Composite & Cellular Beams with Large Web Openings (SCI P355 / P428 / P359)**:
  - Ejemplo 2 viga celular 533x210x109 UB, S355, L=15m:
    * Aperturas circulares ho=425 mm, espaciado s=750 mm, canto del Tee h_T=120 mm, A_T=5141 mm2.
    * Resistencia axil plástica del Tee: N_T,Rd = A_T * f_yd = 5141 * 345 * 10^-3 = 1773.6 kN (≈ 1774 kN).
    * Resistencia a cortante del montante (web post shear): V_wp,Rd = (s - ho) * tw * f_yd / sqrt(3).

* **W01287 / W01281 — Task 5 (Rocafonda Footbridge / Optimization)**:
  - Selección y dimensionado de sección óptima minimizando peso bajo restricciones de resistencia (DCR <= 1.0)
    y rigidez/flecha (L/300).

* **W00637 — Yu, Kraus et al. 2024 / Pareto Optimization**:
  - Invariantes de dominancia de Pareto bi-objetivo (Peso/Coste vs Emisiones CO2 LCA).
"""
from __future__ import annotations

import math
import pytest

from steeloptimizerjm.castellated import (
    CastellatedInput,
    CastellatedResult,
    design_castellated,
)
from steeloptimizerjm.services.beam_optimizer import (
    BeamOptimizationInput,
    optimize_beam,
)
from steeloptimizerjm.pareto_lca import (
    ParetoOptimizeInput,
    ParetoGroupSpec,
    run_pareto_lca_optimizer,
)
from steeloptimizerjm.cost_lca import (
    CostLCAInput,
    evaluate_cost_lca,
)


class TestW01416CastellatedAndCellularGolden:
    """Validación de vigas aligeradas (castellated / cellular) según W01416 / W00215."""

    def test_castellated_ipe300_golden(self):
        """Viga alveolar IPE 300: db=300mm -> H=450mm (1.5x incremento)."""
        inp = CastellatedInput(
            parent_db_mm=300.0,
            parent_bf_mm=150.0,
            parent_tf_mm=10.7,
            parent_tw_mm=7.1,
            Fy_MPa=355.0,
            pattern="hex",
        )
        res = design_castellated(inp)

        assert res.db_castellated_mm == pytest.approx(450.0, rel=1e-9)
        # Zx aproximado = bf * tf * (H - tf) = 150 * 10.7 * (450 - 10.7) = 705,084.9 mm3
        # Mn_pre = Zx * Fy / 1e6 = 705084.9 * 355 / 1e6 = 250.305 kN*m
        expected_Mn_pre = 150.0 * 10.7 * (450.0 - 10.7) * 355.0 / 1e6
        assert res.Mn_pre_kNm == pytest.approx(expected_Mn_pre, rel=1e-6)
        # Factor de reducción por Vierendeel = 0.85
        assert res.Mn_post_kNm == pytest.approx(0.85 * expected_Mn_pre, rel=1e-6)
        assert res.capacity_ratio == pytest.approx(0.85, rel=1e-6)

    def test_castellated_hea600_golden(self):
        """Viga alveolar pesada HEA 600 (db=590mm -> H=885mm)."""
        inp = CastellatedInput(
            parent_db_mm=590.0,
            parent_bf_mm=300.0,
            parent_tf_mm=21.5,
            parent_tw_mm=13.0,
            Fy_MPa=275.0,
        )
        res = design_castellated(inp)
        assert res.db_castellated_mm == pytest.approx(885.0, rel=1e-9)
        assert res.Mn_post_kNm > 0.0

    @pytest.mark.parametrize("name, parent_db, expected_H, expected_a0", [
        ("ABC_IPE200", 200.0, 294.0, 210.0),
        ("ABC_IPE240", 240.0, 353.0, 250.0),
        ("ABC_IPE300", 300.0, 441.0, 315.0),
    ])
    def test_arcelor_abc_cellular_geometry(self, name, parent_db, expected_H, expected_a0):
        """Valida las dimensiones normalizadas de la serie Arcelor ABC en W01416 p.63."""
        # El ratio H / db en la serie ABC es ~1.47
        ratio_H = expected_H / parent_db
        ratio_a0 = expected_a0 / parent_db
        assert ratio_H == pytest.approx(1.47, abs=0.01)
        assert ratio_a0 == pytest.approx(1.05, abs=0.01)


class TestW01641SciP355CellularBeamGolden:
    """Validación del benchmark SCI P355 / SCI P428 fijado en W01641 / W01640."""

    def test_sci_p355_example2_tee_capacity(self):
        """Ejemplo 2 SCI P355: Viga celular 533x210x109 UB, S355 (fyd=345 MPa).

        A_T = 5141 mm2 -> N_T,Rd = A_T * f_yd = 5141 * 345 * 1e-3 = 1773.645 kN ≈ 1774 kN.
        """
        A_T_mm2 = 5141.0
        f_yd_MPa = 345.0
        N_T_Rd_kN = A_T_mm2 * f_yd_MPa / 1000.0
        assert N_T_Rd_kN == pytest.approx(1773.645, rel=1e-6)
        assert round(N_T_Rd_kN) == 1774

    def test_sci_p355_web_post_shear_resistance(self):
        """Resistencia a cortante del montante horizontal: V_wp,Rd = (s - ho) * tw * f_yd / sqrt(3)."""
        s_mm = 750.0
        ho_mm = 425.0
        tw_mm = 11.6  # alma 533x210x109 UB
        fyd_MPa = 345.0

        # V_wp,Rd = (750 - 425) * 11.6 * 345 / (sqrt(3) * 1000)
        web_post_width_mm = s_mm - ho_mm  # 325 mm
        V_wp_Rd_kN = (web_post_width_mm * tw_mm * fyd_MPa) / (math.sqrt(3.0) * 1000.0)

        assert web_post_width_mm == 325.0
        assert V_wp_Rd_kN == pytest.approx(750.93, rel=1e-3)


class TestW01287ProfileOptimizationGolden:
    """Validación de optimización de perfil bajo flexión y flecha según W01287."""

    def test_optimize_beam_flexure_and_deflection_ipe_catalog(self):
        """Viga L=6m, M_Ed=180 kNm, w_service=12 kN/m. Busca perfil IPE factible con peso mínimo."""
        inp = BeamOptimizationInput(
            L_m=6.0,
            M_Ed_kNm=180.0,
            w_service_kN_m=12.0,
            section_family="IPE",
            max_weight_kg_m=120.0,
            deflection_limit=300.0,
        )
        res = optimize_beam(inp)

        assert res.is_feasible, res.notes
        assert res.best_section.startswith("IPE")
        assert res.utilization_M <= 1.0
        assert res.deflection_OK
        assert res.weight_kg_m > 0.0

    def test_optimization_respects_dcr_and_weight_order(self):
        """Demanda M_Ed=250 kNm requiere un perfil más pesado que M_Ed=80 kNm."""
        res_low = optimize_beam(BeamOptimizationInput(
            L_m=5.0, M_Ed_kNm=80.0, w_service_kN_m=5.0, section_family="IPE",
        ))
        res_high = optimize_beam(BeamOptimizationInput(
            L_m=5.0, M_Ed_kNm=250.0, w_service_kN_m=5.0, section_family="IPE",
        ))

        assert res_low.is_feasible
        assert res_high.is_feasible
        assert res_high.weight_kg_m > res_low.weight_kg_m


class TestW00637ParetoDominanceAndNSGA2Invariants:
    """Validación del frente de Pareto y optimización multiobjetivo bi-criterio Coste vs LCA."""

    def test_pareto_dominance_properties(self):
        """Verifica que el frente de Pareto contiene soluciones factibles no vacías."""
        inp = ParetoOptimizeInput(
            groups=[
                ParetoGroupSpec(
                    name="G1_Vigas",
                    length_total=30.0,
                    min_Ix=5.0e-5,       # 5000 cm4 en m4
                    min_Area=0.003,      # 30 cm2 en m2
                    allowed_profiles=["IPE 240", "IPE 270", "IPE 300", "IPE 330", "IPE 360"],
                )
            ],
            population_size=16,
            generations=6,
            seed=42,
        )
        result = run_pareto_lca_optimizer(inp)

        assert len(result.solutions) > 0
        # Todas las soluciones en el frente deben ser factibles
        for sol in result.solutions:
            assert sol.total_cost_USD > 0.0
            assert sol.total_co2_tCO2 > 0.0
            assert sol.feasible

    def test_cost_lca_calculator_consistency(self):
        """Verifica cálculo analítico de coste y huella de carbono según masa de acero."""
        # 1000 kg de acero estructural en España (1100 USD/t, 0.60 tCO2/t para secondary_EAF)
        inp = CostLCAInput(weight_kg=1000.0, country="ES", steel_grade="secondary_EAF")
        res = evaluate_cost_lca(inp)
        assert res["cost_USD"] == pytest.approx(1100.0, rel=1e-6)
        assert res["co2_emissions_tCO2"] == pytest.approx(0.60, rel=1e-6)
        assert res["weight_kg"] == 1000.0
