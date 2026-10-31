# -*- coding: utf-8 -*-
"""Tests del selector óptimo de vigas de acero (Pareto NSGA-II JIT).

Valida la lógica de optimización: factibilidad, selección del más ligero,
no-dominancia de la frontera de Pareto y coherencia de las capacidades
calculadas (φMn = φ·Zx·Fy, φVn = φ·0.6·Fy·Aw).
"""
import pytest

from paretosteel.beam_selector import (
    BeamDemand,
    BeamOptimizationResult,
    optimize_beam,
)


def _dominates(a, b) -> bool:
    """a domina a b si es <= en ambos objetivos (peso, ratio) y < en alguno."""
    le = a.weight_kg_m <= b.weight_kg_m and a.flexural_ratio <= b.flexural_ratio
    lt = a.weight_kg_m < b.weight_kg_m or a.flexural_ratio < b.flexural_ratio
    return le and lt


class TestSeleccion:
    def test_selecciona_factible_mas_ligero(self):
        res = optimize_beam(BeamDemand(M_kNm=120.0, V_kN=50.0))
        assert res.selected is not None
        assert res.selected.flexural_ratio <= 1.0
        assert res.selected.shear_ratio <= 1.0
        # Es el más ligero de TODOS los factibles (no solo del frente).
        feas = [c for c in res.candidates if c.feasible]
        assert res.selected.weight_kg_m == pytest.approx(min(c.weight_kg_m for c in feas))

    def test_momento_mayor_exige_perfil_mas_pesado(self):
        light = optimize_beam(BeamDemand(M_kNm=120.0, V_kN=50.0)).selected
        heavy = optimize_beam(BeamDemand(M_kNm=250.0, V_kN=50.0)).selected
        assert light is not None and heavy is not None
        assert heavy.weight_kg_m >= light.weight_kg_m

    def test_filtro_por_norma_EN(self):
        res = optimize_beam(BeamDemand(M_kNm=80.0, V_kN=30.0), standard="EN")
        assert res.selected is not None
        assert res.selected.standard == "EN"
        assert all(c.standard == "EN" for c in res.candidates)


class TestParetoFront:
    def test_frente_es_subconjunto(self):
        res = optimize_beam(BeamDemand(M_kNm=100.0, V_kN=40.0))
        nombres = {c.name for c in res.candidates}
        assert set(res.pareto_front).issubset(nombres)
        assert len(res.pareto_front) >= 1

    def test_frente_no_dominado(self):
        res = optimize_beam(BeamDemand(M_kNm=100.0, V_kN=40.0))
        front = [c for c in res.candidates if c.name in res.pareto_front]
        for a in front:
            for b in front:
                if a is b:
                    continue
                assert not _dominates(a, b), f"{a.name} domina a {b.name} en el frente"

    def test_seleccionado_esta_en_el_frente(self):
        res = optimize_beam(BeamDemand(M_kNm=150.0, V_kN=60.0))
        assert res.selected.name in res.pareto_front


class TestFactibilidad:
    def test_infactible_cuando_demanda_excesiva(self):
        res = optimize_beam(BeamDemand(M_kNm=100000.0, V_kN=10.0))
        assert res.selected is None
        assert res.n_feasible == 0
        assert res.pareto_front == []
        assert res.n_evaluated > 0

    def test_cortante_excesivo_descarta(self):
        # Momento moderado pero cortante enorme -> infactible por cortante.
        res = optimize_beam(BeamDemand(M_kNm=50.0, V_kN=100000.0))
        assert res.selected is None
        assert res.n_feasible == 0


class TestCapacidadCoherente:
    def test_flexion_phi_Zx_Fy(self):
        # W12X26: Zx = 615 cm³, Fy = 345 MPa, φ = 0.90 (LRFD US).
        res = optimize_beam(BeamDemand(M_kNm=50.0, V_kN=20.0), standard="ASTM")
        w12 = next(c for c in res.candidates if c.name == "W12X26")
        esperado = 0.90 * 615.0e3 * 345.0 / 1.0e6  # kN·m
        assert w12.Mn_design_kNm == pytest.approx(esperado, rel=1e-9)

    def test_cortante_phi_0p6_Fy_Aw(self):
        # W12X26: h = 310, tw = 5.8 -> Aw = 1798 mm²; Vn = 0.6·345·Aw/1e3·φ.
        res = optimize_beam(BeamDemand(M_kNm=50.0, V_kN=20.0), standard="ASTM")
        w12 = next(c for c in res.candidates if c.name == "W12X26")
        esperado = 0.90 * 0.6 * 345.0 * (310.0 * 5.8) / 1.0e3  # kN
        assert w12.Vn_design_kN == pytest.approx(esperado, rel=1e-9)

    def test_peso_desde_area(self):
        # W12X26: A = 49.3 cm² -> 49.3e-4 m² × 7850 = 38.7 kg/m aprox.
        res = optimize_beam(BeamDemand(M_kNm=50.0, V_kN=20.0), standard="ASTM")
        w12 = next(c for c in res.candidates if c.name == "W12X26")
        assert w12.weight_kg_m == pytest.approx(49.3e-4 * 7850.0, rel=1e-9)


class TestTipoResultado:
    def test_estructura_resultado(self):
        res = optimize_beam(BeamDemand(M_kNm=120.0, V_kN=50.0))
        assert isinstance(res, BeamOptimizationResult)
        assert res.n_evaluated == len(res.candidates)
        assert res.n_feasible == sum(1 for c in res.candidates if c.feasible)
        assert res.selected.profile_type in ("steel_w_shape", "steel_ipe")
