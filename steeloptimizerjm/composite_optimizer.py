"""
SteelOptimizerJm — Composite Steel-Concrete Beam Optimizer
=========================================================
Pareto multi-objective discrete optimization for composite floor beams.

Combines the unified steel profile catalog (catalog_unified) with the rigorous
composite beam mechanics engine (AISC 360-16 / EN 1994-1-1) to select the
most economical profile (minimum steel weight) that strictly satisfies:
1. Construction stage flexure and shear on bare steel (unpropped).
2. Composite stage flexure and shear with shear studs.
3. Minimum degree of composite action (AISC >= 25%, Eurocode >= eta_min).
4. SLS live and total deflection limits under composite inertia I_eff.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import List, Literal, Optional, Sequence

import numpy as np

from .catalog_unified import UnifiedSection, all_sections
from .nsga2_jit import non_dominated_sort_jit

from compositejm.aisc_composite_beam import (
    AISCBeamSection,
    AISCSlabSpec,
    AISCStudSpec,
    verify_aisc_composite_beam,
)
from industrialjm.composite_beams import (
    SteelBeamProfile,
    StudConnectorSpec,
    IndustrialMezzanineDemand,
    design_industrial_composite_beam,
)


@dataclass(frozen=True)
class CompositeOptimizationDemand:
    """Design requirements and loadings for composite beam optimization."""
    span_m: float
    spacing_m: float
    dead_load_superimposed_kpa: float  # [kPa]
    live_load_kpa: float               # [kPa]
    slab_thickness_mm: float = 120.0
    deck_height_mm: float = 50.0
    concrete_fc_MPa: float = 28.0
    concrete_density_kg_m3: float = 2400.0
    shored_construction: bool = False
    standard: Literal["AISC_360_16", "EUROCODE_4"] = "AISC_360_16"
    steel_grade_Fy_MPa: float = 345.0
    stud_diameter_mm: float = 19.0
    stud_fu_MPa: float = 450.0
    live_deflection_limit_ratio: float = 360.0
    total_deflection_limit_ratio: float = 240.0
    catalog_filter_standard: Optional[Literal["ASTM", "EN"]] = None


@dataclass(frozen=True)
class CompositeCandidate:
    """Evaluated steel profile candidate in composite action."""
    section_name: str
    standard: str
    weight_kg_m: float
    total_steel_weight_kg: float
    is_feasible: bool
    governing_dcr: float
    governing_mode: str
    dcr_flexure_composite: float
    dcr_shear_composite: float
    dcr_flexure_construction: float
    dcr_deflection_live: float
    dcr_deflection_total: float
    deflection_live_mm: float
    deflection_total_mm: float
    moment_capacity_kNm: float
    applied_moment_kNm: float
    num_studs_total: int
    units: dict[str, str] = field(default_factory=lambda: {"moment": "kNm", "weight": "kg", "length": "mm"})
    diagnostics: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class CompositeOptimizationResult:
    """Optimal solution and Pareto set of composite beam candidates."""
    selected: Optional[CompositeCandidate]
    pareto_front: List[CompositeCandidate]
    all_evaluated: List[CompositeCandidate]
    n_evaluated: int
    n_feasible: int
    demand: CompositeOptimizationDemand

    def explanation_memo(self) -> str:
        """Generates an engineering rationale memo explaining the selection."""
        code_str = "AISC 360-16" if self.demand.standard == "AISC_360_16" else "Eurocódigo 4 (EN 1994-1-1)"
        lines = [
            f"# Memorando de Optimización de Viga Compuesta ({code_str})",
            f"- **Geometría**: Vano L = {self.demand.span_m:.2f} m, Separación S = {self.demand.spacing_m:.2f} m",
            f"- **Losa**: Espesor total = {self.demand.slab_thickness_mm:.0f} mm (chapa grecada h_deck = {self.demand.deck_height_mm:.0f} mm), f'c = {self.demand.concrete_fc_MPa:.1f} MPa",

            f"- **Cargas**: Sobrecarga = {self.demand.live_load_kpa:.2f} kPa, Carga permanente añadida = {self.demand.dead_load_superimposed_kpa:.2f} kPa",
            f"- **Perfiles evaluados**: {self.n_evaluated} ({self.n_feasible} factibles)",
            "",
        ]
        if self.selected is not None:
            sel = self.selected
            lines.extend([
                f"## Perfil Óptimo Seleccionado: **{sel.section_name}** ({sel.standard})",
                f"- **Peso Lineal**: {sel.weight_kg_m:.1f} kg/m (Peso total viga = {sel.total_steel_weight_kg:.1f} kg)",
                f"- **DCR Gobernante**: {sel.governing_dcr:.2f} (Gobernado por: {sel.governing_mode})",
                f"- **Momento Último**: Capacidad = {sel.moment_capacity_kNm:.1f} kN·m vs Solicitación = {sel.applied_moment_kNm:.1f} kN·m (DCR = {sel.dcr_flexure_composite:.2f})",
                f"- **Conectores**: {sel.num_studs_total} pernos tipo stud Ø{self.demand.stud_diameter_mm:.0f} mm",
                f"- **Flechas ELS**: Sobrecarga = {sel.deflection_live_mm:.1f} mm (DCR = {sel.dcr_deflection_live:.2f}), Total = {sel.deflection_total_mm:.1f} mm (DCR = {sel.dcr_deflection_total:.2f})",
                "",
                "### Justificación Estructural:",
                f"El perfil {sel.section_name} proporciona el menor consumo de acero garantizando la resistencia en fase constructiva sin apeos y la rigidez necesaria en servicio gracias a la colaboración de la losa.",
            ])
        else:
            lines.extend([
                "## ❌ Ningún perfil del catálogo resultó factible",
                "Todos los perfiles evaluados incumplieron al menos uno de los estados límite (resistencia constructiva, flexión compuesta o flecha).",
                "Considere aumentar el canto del perfil, utilizar apuntalamiento provisional (shored construction) o reducir la separación entre vigas.",
            ])

        # Pareto summary
        if self.pareto_front:
            lines.extend([
                "",
                "### Alternativas en la Frontera de Pareto:",
                "| Perfil | Estándar | Peso (kg/m) | DCR Gobernante | Modo Crítico | Pernos |",
                "| :--- | :---: | :---: | :---: | :---: | :---: |",
            ])
            for p in self.pareto_front:
                lines.append(f"| {p.section_name} | {p.standard} | {p.weight_kg_m:.1f} | {p.governing_dcr:.2f} | {p.governing_mode} | {p.num_studs_total} |")

        return "\n".join(lines)


def _evaluate_candidate(
    sec: UnifiedSection,
    demand: CompositeOptimizationDemand,
) -> CompositeCandidate:
    """Evaluates a single catalog profile against composite demand."""
    # Convert UnifiedSection to SteelBeamProfile
    # Note: sec.A_cm2 -> mm2 (* 100), Ix_cm4 -> mm4 (* 10000), Zx_cm3 -> mm3 (* 1000)
    profile = SteelBeamProfile(
        name=sec.name,
        d_mm=float(sec.h_mm),
        bf_mm=float(sec.bf_mm),
        tf_mm=float(sec.tf_mm),
        tw_mm=float(sec.tw_mm),
        A_mm2=float(sec.A_cm2 * 100.0),
        Ix_mm4=float(sec.Ix_cm4 * 10000.0),
        Zx_mm3=float(sec.Zx_cm3 * 1000.0),
        Fy_MPa=demand.steel_grade_Fy_MPa,
    )

    stud_spec = StudConnectorSpec(
        diameter_mm=demand.stud_diameter_mm,
        fu_MPa=demand.stud_fu_MPa,
        height_mm=demand.deck_height_mm + 45.0,  # stud emerges 45 mm into concrete slab
        Rg=1.0,
        Rp=0.75 if demand.deck_height_mm > 0 else 1.0,
    )

    ind_demand = IndustrialMezzanineDemand(
        span_m=demand.span_m,
        spacing_m=demand.spacing_m,
        dead_load_superimposed_kpa=demand.dead_load_superimposed_kpa,
        live_load_kpa=demand.live_load_kpa,
        slab_thickness_mm=demand.slab_thickness_mm,
        deck_height_mm=demand.deck_height_mm,
        concrete_f_c_MPa=demand.concrete_fc_MPa,
        concrete_density_kg_m3=demand.concrete_density_kg_m3,
        shored_construction=demand.shored_construction,
        standard=demand.standard,
        live_deflection_limit_ratio=demand.live_deflection_limit_ratio,
        total_deflection_limit_ratio=demand.total_deflection_limit_ratio,
    )

    res = design_industrial_composite_beam(ind_demand, profile, stud_spec=stud_spec)

    weight_kg_m = round(sec.A_cm2 * 0.785, 2)  # steel mass kg/m
    total_steel_weight = round(weight_kg_m * demand.span_m, 1)

    return CompositeCandidate(
        section_name=sec.name,
        standard=sec.standard,
        weight_kg_m=weight_kg_m,
        total_steel_weight_kg=total_steel_weight,
        is_feasible=res.is_viable,
        governing_dcr=res.governing_dcr,
        governing_mode=res.governing_mode,
        dcr_flexure_composite=res.dcr_flexure_composite,
        dcr_shear_composite=res.dcr_shear_composite,
        dcr_flexure_construction=res.dcr_flexure_construction,
        dcr_deflection_live=res.dcr_deflection_live,
        dcr_deflection_total=res.dcr_deflection_total,
        deflection_live_mm=res.deflection_live_mm,
        deflection_total_mm=res.deflection_total_mm,
        moment_capacity_kNm=res.moment_capacity_kNm,
        applied_moment_kNm=res.applied_moment_kNm,
        num_studs_total=res.num_studs_total,
        diagnostics=res.diagnostics,
    )


def optimize_composite_beam(
    demand: CompositeOptimizationDemand,
    sections: Optional[Sequence[UnifiedSection]] = None,
) -> CompositeOptimizationResult:
    """Finds the Pareto frontier and minimum-weight profile for composite floor beams."""
    if sections is None:
        sections = all_sections()

    # Filter catalog if requested
    if demand.catalog_filter_standard is not None:
        sections = [s for s in sections if s.standard == demand.catalog_filter_standard]

    if not sections:
        raise ValueError("No se encontraron perfiles en el catálogo para los criterios solicitados.")

    # Evaluate all candidates
    evaluated: list[CompositeCandidate] = []
    for s in sections:
        cand = _evaluate_candidate(s, demand)
        evaluated.append(cand)

    feasible = [c for c in evaluated if c.is_feasible]

    if not feasible:
        return CompositeOptimizationResult(
            selected=None,
            pareto_front=[],
            all_evaluated=evaluated,
            n_evaluated=len(evaluated),
            n_feasible=0,
            demand=demand,
        )

    # Multi-objective Pareto optimization on feasible candidates:
    # Objective 1: Weight (kg/m) [minimize]
    # Objective 2: Governing DCR (utilization) [minimize]
    objs = np.array([[c.weight_kg_m, c.governing_dcr] for c in feasible], dtype=np.float64)
    ranks = non_dominated_sort_jit(objs)

    # Rank 0 is the non-dominated Pareto frontier
    pareto_candidates = [feasible[i] for i in range(len(feasible)) if ranks[i] == 0]
    # Sort Pareto front by weight ascending
    pareto_candidates.sort(key=lambda c: c.weight_kg_m)

    # Optimal selected is the minimum weight solution from the Pareto frontier
    selected = pareto_candidates[0]

    return CompositeOptimizationResult(
        selected=selected,
        pareto_front=pareto_candidates,
        all_evaluated=evaluated,
        n_evaluated=len(evaluated),
        n_feasible=len(feasible),
        demand=demand,
    )
