"""Correcciones de la 1.1.0, cada una con su oráculo calculado a mano o por un método independiente.

Unidades SI salvo que se diga lo contrario. Los valores del perfil W8X31 se leen de la base
AISC v16 empaquetada (data/aisc_v16.csv): A = 9,13 in², d = 8,0 in, Ix = 110 in⁴, Iy = 37,1 in⁴.
"""
from __future__ import annotations

import csv
import math
import sys
from pathlib import Path

import pytest

import paretosteel
from paretosteel import ElementGroup, GAConfig, optimize
from paretosteel.beam_selector import BeamDemand, optimize_beam
from paretosteel.boq import SteelBoQItem, calculate_steel_boq
from paretosteel.catalog_unified import all_sections
from paretosteel.catalogs import CATALOG_EURO_IPE, all_profiles
from paretosteel.diff_evolution import optimize_column_de
from paretosteel.memos.justificacion_perfil import JustificacionInput, justificar
from paretosteel.memos.profile_justification import memo_from_beam_candidate
from paretosteel._composite.industrial_composite_beams import (
    IndustrialMezzanineDemand,
    SteelBeamProfile,
    StudConnectorSpec,
    design_industrial_composite_beam,
)

_CSV = Path(paretosteel.__file__).parent / "data" / "aisc_v16.csv"
_AISC = {r["AISC_Manual_Label"]: r for r in csv.DictReader(_CSV.open(encoding="utf-8"))}


def _unified(name: str):
    return next(s for s in all_sections() if s.name == name)


def _profile_from_unified(name: str) -> SteelBeamProfile:
    s = _unified(name)
    return SteelBeamProfile(name=s.name, d_mm=s.h_mm, bf_mm=s.bf_mm, tf_mm=s.tf_mm, tw_mm=s.tw_mm,
                            A_mm2=s.A_cm2 * 100.0, Ix_mm4=s.Ix_cm4 * 1e4, Zx_mm3=s.Zx_cm3 * 1e3,
                            Fy_MPa=345.0)


# --- 1. Memoria: φ aplicado dos veces ------------------------------------------------------

def test_memoria_reproduce_el_ratio_del_selector_sin_doble_phi():
    # W18X35: Zx = 1090 cm³ → φMn = 0,9·1090e3·345/1e6 = 338,445 kN·m; 320/338,445 = 0,94551.
    # Antes la memoria aplicaba φ otra vez: 320/(0,9·338,445) = 1,0506 → «NO CUMPLE».
    res = optimize_beam(BeamDemand(M_kNm=320.0, V_kN=180.0, Fy_MPa=345.0, code="US"))
    c = res.selected
    assert c.name == "W18X35"
    memo = memo_from_beam_candidate(c, span_m=8.0, w_kN_m=20.0)
    assert memo.ratio_flexion == pytest.approx(320.0 / (0.9 * 1090e3 * 345.0 / 1e6), rel=1e-9)
    assert memo.ratio_flexion == pytest.approx(c.flexural_ratio, rel=1e-12)
    assert memo.ratio_cortante == pytest.approx(c.shear_ratio, rel=1e-12)
    assert memo.cumple_flexion


def test_memoria_sin_carga_de_servicio_no_firma_la_flecha():
    res = optimize_beam(BeamDemand(M_kNm=320.0, V_kN=180.0))
    memo = memo_from_beam_candidate(res.selected, span_m=8.0, w_kN_m=0.0)
    assert not memo.cumple_deflexion
    assert not memo.cumple
    assert "NO VERIFICADA" in memo.markdown


# --- 2. justificar: capacidad axial ausente ---------------------------------------------------

def test_justificar_capacidad_axial_ausente_no_cumple():
    sin_pn = justificar(JustificacionInput("X", Mu_kNm=10, Vu_kN=5, Pu_kN=100,
                                           Mn_kNm=300, Vn_kN=400, Pn_kN=0.0))
    assert math.isinf(sin_pn.ratio_P)
    assert not sin_pn.cumple
    # Sin axil y sin capacidad axial (viga): rP = 0 → H1-1b = 10/(0,9·300) = 0,0370.
    viga = justificar(JustificacionInput("X", Mu_kNm=10, Vu_kN=5, Pu_kN=0.0,
                                         Mn_kNm=300, Vn_kN=400, Pn_kN=0.0))
    assert viga.ratio_P == 0.0
    assert viga.ratio_combinado == pytest.approx(10 / 270, rel=1e-12)
    assert viga.cumple


# --- 3. GA con catálogo propio ----------------------------------------------------------------

def test_ga_respeta_custom_profiles():
    # Subcatálogo IPE200/240/300 y min_Ix = 5e-5 m⁴. Fuerza bruta: IPE200 (1,94e-5) e IPE240
    # (3,89e-5) no llegan; IPE300 (8,36e-5) sí → óptimo IPE300, 42,2 kg/m × 10 m = 422 kg.
    sub = [CATALOG_EURO_IPE[k] for k in ("IPE200", "IPE240", "IPE300")]
    res = optimize([ElementGroup("viga", 10.0, min_Ix=5e-5, family_filter="IPE")],
                   config=GAConfig(population_size=10, n_generations=10, random_seed=3),
                   custom_profiles=sub)
    assert dict(res.best.assignment)["viga"] == "IPE300"
    assert res.best.weight == pytest.approx(422.0)
    assert res.best.penalty == 0.0


# --- 4. Catálogo sin duplicados ---------------------------------------------------------------

def test_catalogo_sin_designaciones_duplicadas_y_W_de_la_base_aisc():
    names = [p.designation for p in all_profiles()]
    assert len(names) == len(set(names))
    w8 = next(p for p in all_profiles() if p.designation == "W8X31")
    # 110 in⁴ × 4,1623e-7 = 4,5785e-5 m⁴ (la copia manual decía 4,24e-5, −7,4 %).
    assert w8.Ix == pytest.approx(110.0 * 4.1623e-7, rel=1e-12)


def test_boq_usa_el_area_de_la_base_aisc():
    # W8X31: A = 9,13 in² × 6,4516 = 58,903 cm² (la copia manual decía 58,7).
    rep = calculate_steel_boq([SteelBoQItem("W8X31", 10.0)], country_iso="US")
    assert rep.items[0].tabulated_area_cm2 == pytest.approx(9.13 * 6.4516, rel=1e-9)


@pytest.mark.parametrize("s", [s for s in all_sections() if s.standard == "ASTM"], ids=lambda s: s.name)
def test_catalogo_unificado_W_contra_base_aisc_v16(s):
    r = _AISC[s.name]
    assert s.A_cm2 == pytest.approx(float(r["A"]) * 6.4516, rel=0.005)
    assert s.Ix_cm4 == pytest.approx(float(r["Ix"]) * 41.6231, rel=0.005)
    assert s.Iy_cm4 == pytest.approx(float(r["Iy"]) * 41.6231, rel=0.005)
    assert s.h_mm == pytest.approx(float(r["d"]) * 25.4, abs=1.5)


def test_W14X30_Zx_corregido():
    # AISC: Zx = 47,3 in³ = 775 cm³ (antes 750, −3,2 %).
    assert _unified("W14X30").Zx_cm3 == pytest.approx(775.0)


# --- 5. Puente de secciones sin fastsap ------------------------------------------------------

def test_section_bridge_sin_validar_no_importa_fastsap(monkeypatch):
    from paretosteel._common.model import Element, Material, Model, Node, SectionRef
    from paretosteel.section_bridge import apply_proposed_sections

    monkeypatch.setitem(sys.modules, "fastsap", None)  # import fastsap → ImportError
    model = Model(
        nodes=(Node("N1", 0.0, 0.0, 0.0), Node("N2", 0.0, 0.0, 3.0)),
        elements=(Element("C1", "N1", "N2", section=SectionRef("IPE200", "I"), material="S355"),),
        materials=(Material("S355", E_MPa=210000.0, fy_MPa=355.0),),
        sections=(SectionRef("IPE200", "I"),),
    )
    new = apply_proposed_sections(model, {"C1": "HEB240"}, validate_against_catalog=False)
    assert new.elements[0].section.name == "HEB240"
    with pytest.raises(ImportError):
        apply_proposed_sections(model, {"C1": "HEB240"}, validate_against_catalog=True)


# --- 6. Pilar por evolución diferencial: interacción H1 en el resultado ----------------------

def test_pilar_de_con_momento_reporta_la_interaccion_h1():
    # W8X31, H = 3 m, K = 1, Fy = 345, E = 200 GPa (base AISC v16):
    #   ry = √(Iy/A) = √(1,5442e-5/5,8903e-3) = 0,051202 m; KL/r = 58,592 < 4,71√(E/Fy) = 113,4
    #   Fe = π²E/(KL/r)² = 574,98 MPa; Fcr = 0,658^(345/574,98)·345 = 268,38 MPa
    #   φPn = 0,9·268,38·5890,3/1e3 = 1422,76 kN
    #   Sx = Ix/(d/2) = 4,5785e-5/0,1016 = 4,5064e-4 m³; φMn = 0,9·345e3·4,5064e-4 = 139,92 kN·m
    # P = 0,5·φPn y M = 0,7·φMn → H1-1a: 0,5 + 8/9·0,7 = 1,1222 > 1 aunque el axil (0,5) cumpla.
    w8 = next(p for p in all_profiles() if p.designation == "W8X31")
    phiPn, phiMn = 1422.762646, 139.924563
    res = optimize_column_de(height_m=3.0, axial_kN=0.5 * phiPn, moment_kNm=0.7 * phiMn,
                             catalog=[w8], maxiter=5)
    assert res.utilization_P == pytest.approx(0.5, rel=1e-6)
    assert res.interaction_ratio == pytest.approx(0.5 + 8.0 / 9.0 * 0.7, rel=1e-6)
    assert res.feasible is False
    assert optimize_column_de(height_m=3.0, axial_kN=500.0, catalog=[w8], maxiter=5).interaction_ratio is None


# --- 7. Viga mixta AISC: la chapa no cuenta dos veces -----------------------------------------

def _demand(**kw):
    base = dict(span_m=8.0, spacing_m=2.8, dead_load_superimposed_kpa=1.2, live_load_kpa=3.5,
                slab_thickness_mm=120.0, deck_height_mm=50.0, concrete_f_c_MPa=28.0)
    base.update(kw)
    return IndustrialMezzanineDemand(**base)


def test_viga_mixta_aisc_canto_de_losa_sobre_la_chapa():
    # IPE270 (A = 45,9 cm²), losa total 120 mm con chapa de 50 → hormigón sobre nervios hc = 70 mm.
    # b_eff = 2·min(L/8, S/2) = 2·min(1000, 1400) = 2000 mm. Conexión completa (34 pernos):
    #   T = As·Fy = 4590·345 = 1 583 550 N;  a = T/(0,85·28·2000) = 33,268 mm < hc
    #   Mn = T·(d/2 + h_deck + hc − a/2) = 1 583 550·(135 + 50 + 70 − 16,634) = 377,46 kN·m
    #   φMn = 339,72 kN·m  (antes 411,0: brazo con +50 mm y bloque sobre 120 mm)
    res = design_industrial_composite_beam(_demand(), _profile_from_unified("IPE270"))
    assert res.num_studs_total == 34
    assert res.moment_capacity_kNm == pytest.approx(339.718, rel=1e-4)


def test_viga_mixta_rechaza_chapa_igual_o_mayor_que_la_losa():
    with pytest.raises(ValueError, match="deck_height_mm"):
        _demand(slab_thickness_mm=50.0, deck_height_mm=50.0)


def test_estimacion_de_pernos_con_Ec_en_unidades_SI():
    # Losa maciza (h_deck = 0, Rp = 1), HEA200 (A = 53,8 cm²), f'c = 28, wc = 2400, perno Ø19:
    #   Ec = 0,043·2400^1,5·√28 = 26 752 MPa; Asa = π·19²/4 = 283,53 mm²
    #   Qn = min(0,5·Asa·√(f'c·Ec), Asa·Fu) = min(122 695, 127 588) = 122 695 N (manda el hormigón)
    #   pernos por semivano = ⌈5380·345/122 695⌉ = ⌈15,13⌉ = 16 → 32 en total.
    # Con el Ec de antes (34 649 MPa, +30 %) mandaba el acero (127 588 N) y salían 15·2 = 30 pernos,
    # que con el Qn real no llegan a la conexión completa (ΣQn = 1 840 kN < 1 856 kN).
    res = design_industrial_composite_beam(
        _demand(deck_height_mm=0.0), _profile_from_unified("HEA200"),
        stud_spec=StudConnectorSpec(diameter_mm=19.0, fu_MPa=450.0, height_mm=95.0, Rg=1.0, Rp=1.0))
    assert res.num_studs_total == 32


# --- 8. Viga mixta EC4: inercia homogeneizada con su propio eje neutro ------------------------

def test_flecha_ec4_con_inercia_homogeneizada_correcta():
    # IPE270: Ia = 5790e4 mm⁴, Aa = 4590 mm²; n = 200000/(9500·3,6^(1/3)) = 13,736 (límite declarado)
    #   Ac/n = 2000·70/13,736 = 10 191,9 mm²; d = 135 + 50 + 35 = 220 mm
    #   I_tr = Ia + (Ac/n)·70²/12 + Aa·(Ac/n)/(Aa + Ac/n)·d² = 2,1524e8 mm⁴  (antes Ia + (Ac/n)·d² = 5,512e8)
    #   δ_viva = 5·(3,5·2,8)·8000⁴/(384·200000·2,1524e8) = 12,14 mm  (antes 4,74 mm)
    res = design_industrial_composite_beam(_demand(standard="EUROCODE_4"), _profile_from_unified("IPE270"))
    assert res.deflection_live_mm == pytest.approx(12.1418, rel=1e-4)


# --- 9. Versión única -------------------------------------------------------------------------

def test_version_unica():
    import tomllib
    from paretosteel.api.app import create_app

    pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
    ver = tomllib.loads(pyproject.read_text(encoding="utf-8"))["project"]["version"]
    assert paretosteel.__version__ == ver == "1.1.0"
    assert create_app().version == ver
