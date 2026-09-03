"""
test_experimental_markers_ag38.py
==================================
Campaña AG38 — Bloque C: Verificación de marcadores de estado EXPERIMENTAL
en las funciones señaladas en la tabla de 40 huérfanas:
  - #1: StickModelsJm :: modal_analysis_shear_building
  - #6: SteelOptimizerJm :: design_castellated
  - #9: SteelOptimizerJm :: aisc_beam_column_interaction
  - #13: SlopeStabilityJm :: evaluate_bray_travasarou
  - #15: ScaffoldLoadsJm :: design_load
  - #17: IndustrialJm :: evaluate_chimney
  - #20: GrasshopperBridgeJm :: compute_exchange_id
  - #29: DynamicsJm :: evaluate_fps
  - #37: ClashDetectionJm :: check_footing_rebar_vs_anchor_bolts
"""
from __future__ import annotations

import stickmodelsjm.core as stick_mod
import steeloptimizerjm.castellated as cast_mod
import steeloptimizerjm.design_codes as codes_mod
import slopestabilityjm.bray_travasarou as bray_mod
import scaffoldloadsjm.core as scaf_mod
import industrialjm.chimneys as chim_mod
import grasshopperbridgejm.core as gh_mod
import dynamicsjm.systems.fps_isolator as fps_mod
import clashdetectionjm.core as clash_mod


def test_all_8_experimental_modules_expose_experimental_level():
    """Módulos puramente experimentales exponen VALIDATION_LEVEL = 'experimental'."""
    modules = [
        stick_mod,
        cast_mod,
        bray_mod,
        scaf_mod,
        chim_mod,
        gh_mod,
        fps_mod,
        clash_mod,
    ]
    for m in modules:
        assert hasattr(m, "VALIDATION_LEVEL"), f"Módulo {m.__name__} no expone VALIDATION_LEVEL"
        assert m.VALIDATION_LEVEL == "experimental", f"Módulo {m.__name__} no declara 'experimental'"


def test_aisc_beam_column_interaction_function_has_experimental_level():
    """La función aisc_beam_column_interaction dentro de design_codes expone validation_level = 'experimental'."""
    assert hasattr(codes_mod.aisc_beam_column_interaction, "validation_level")
    assert codes_mod.aisc_beam_column_interaction.validation_level == "experimental"


def test_all_9_experimental_functions_have_experimental_docstring():
    """Las funciones de la tabla de experimentales declaran [ESTADO: EXPERIMENTAL] en su docstring."""
    funcs = [
        stick_mod.modal_analysis_shear_building,
        cast_mod.design_castellated,
        codes_mod.aisc_beam_column_interaction,
        bray_mod.evaluate_bray_travasarou,
        scaf_mod.design_load,
        chim_mod.evaluate_chimney,
        gh_mod.compute_exchange_id,
        fps_mod.evaluate_fps,
        clash_mod.check_footing_rebar_vs_anchor_bolts,
    ]
    for f in funcs:
        assert f.__doc__ is not None, f"Función {f.__name__} no tiene docstring"
        assert "[ESTADO: EXPERIMENTAL]" in f.__doc__, (
            f"Función {f.__name__} no advierte [ESTADO: EXPERIMENTAL] en docstring: {f.__doc__}"
        )
