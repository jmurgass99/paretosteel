"""Optimización multiobjetivo Pareto de Estructuras de Acero: Costo vs Huella Ecológica (CO2).

Utiliza el algoritmo genético NSGA-II para encontrar la frontera de Pareto de perfiles
estructurales optimizando simultáneamente el costo de fabricación y la huella de carbono embebido.
"""

from __future__ import annotations

import math
import random
from typing import List, Dict, Optional, Tuple
from pydantic import BaseModel, Field

from .nsga2 import nsga2_run, Individual
from .cost_lca import COST_USD_PER_TON, EMBODIED_CO2_TON_PER_TON
from .catalogs import filter_profiles, all_profiles


# Sobreprecio relativo por ruta siderúrgica (alto horno BF = 1.00, horno de arco EAF = 1.08, verde H2 = 1.22)
ROUTE_COST_MULTIPLIER: Dict[str, float] = {
    "primary_BF": 1.00,
    "average_global": 1.03,
    "secondary_EAF": 1.08,
    "low_carbon": 1.22,
}


# ---------------------------------------------------------------------------
# Schemas de Entrada Pydantic v2
# ---------------------------------------------------------------------------

class ParetoGroupSpec(BaseModel):
    """Especificación de un grupo de miembros estructurales para optimización Pareto."""
    name: str = Field(..., description="Nombre del grupo (e.g. Columnas Externas)")
    length_total: float = Field(..., description="Longitud acumulada total del grupo en metros", gt=0.0)
    min_Ix: float = Field(0.0, description="Inercia mínima requerida Ix en cm4", ge=0.0)
    min_A: float = Field(0.0, description="Área mínima requerida A en cm2", ge=0.0)
    family_filter: Optional[str] = Field(None, description="Filtro de catálogo (W, IPE, HEB o None)")
    country: str = Field("DEFAULT", description="País origen para costos (US, CL, CN, etc.)")
    steel_grade: str = Field("average_global", description="Tipo de producción del acero para CO2 (primary_BF, secondary_EAF, low_carbon, etc.)")
    route_options: Optional[List[str]] = Field(
        None,
        description="Rutas siderúrgicas candidatas para crear compromiso real Costo vs CO2 (ej. ['primary_BF', 'secondary_EAF', 'low_carbon']).",
    )


class ParetoOptimizeInput(BaseModel):
    """Parámetros para ejecutar el optimizador multicriterio Pareto NSGA-II."""
    groups: List[ParetoGroupSpec] = Field(..., description="Grupos de acero a optimizar")
    population_size: int = Field(40, description="Tamaño de la población del GA", ge=10, le=200)
    n_generations: int = Field(30, description="Número de generaciones de optimización", ge=5, le=100)
    random_seed: int = Field(42, description="Semilla aleatoria para reproducibilidad")
    allow_route_tradeoff: bool = Field(
        False,
        description="Si True, incluye la ruta siderúrgica (BF/EAF/low_carbon) como variable de decisión para generar un frente Costo-CO2 no colineal.",
    )


# ---------------------------------------------------------------------------
# Schemas de Salida Pydantic v2
# ---------------------------------------------------------------------------

class ParetoSolution(BaseModel):
    """Representa un punto de diseño factible óptimo en la frontera de Pareto."""
    assignment: Dict[str, str] = Field(..., description="Asignación de perfiles (nombre_grupo -> designacion_perfil)")
    total_weight_kg: float
    total_cost_USD: float
    total_co2_tCO2: float
    feasible: bool
    steel_routes: Optional[Dict[str, str]] = Field(None, description="Ruta siderúrgica asignada por grupo cuando se optimiza ruta.")


class ParetoOptimizeOutput(BaseModel):
    """Resultados de la frontera de Pareto encontrada."""
    n_solutions: int
    solutions: List[ParetoSolution]


# ---------------------------------------------------------------------------
# Core de la Optimización NSGA-II Costo vs CO2
# ---------------------------------------------------------------------------

def run_pareto_lca_optimizer(inp: ParetoOptimizeInput) -> ParetoOptimizeOutput:
    """Ejecuta NSGA-II para hallar la frontera de Pareto entre Costo y CO2."""
    if not inp.groups:
        raise ValueError("Debe especificar al menos un grupo de elementos.")

    # 1. Preparar catálogos y rutas candidatas para cada grupo
    group_catalogs = []
    group_routes: list[list[str]] = []
    default_routes = ["primary_BF", "average_global", "secondary_EAF", "low_carbon"]
    for g in inp.groups:
        profs = filter_profiles(family=g.family_filter) if g.family_filter else all_profiles()
        profs = sorted(profs, key=lambda p: p.weight_per_m)
        if not profs:
            raise ValueError(f"No hay perfiles disponibles en el catálogo para el filtro '{g.family_filter}' en el grupo {g.name}")
        group_catalogs.append(profs)
        if g.route_options:
            group_routes.append(list(g.route_options))
        elif inp.allow_route_tradeoff:
            group_routes.append(default_routes)
        else:
            group_routes.append([g.steel_grade])

    has_route_genes = any(len(r) > 1 for r in group_routes)
    n_groups = len(inp.groups)
    n_genes = n_groups * (2 if has_route_genes else 1)

    bounds = [(0.0, float(len(group_catalogs[i]) - 1)) for i in range(n_groups)]
    if has_route_genes:
        bounds.extend([(0.0, float(len(group_routes[i]) - 1)) for i in range(n_groups)])

    def _decode(genes: list[float], i: int):
        catalog = group_catalogs[i]
        idx = max(0, min(int(round(genes[i])), len(catalog) - 1))
        profile = catalog[idx]
        routes = group_routes[i]
        if has_route_genes and len(routes) > 1:
            r_idx = max(0, min(int(round(genes[n_groups + i])), len(routes) - 1))
            route = routes[r_idx]
        else:
            route = routes[0]
        return profile, route

    # 2. Definir función de evaluación multiobjetivo
    def evaluate_objectives(genes: list[float]) -> tuple[float, float]:
        """Calcula el costo y CO2 totales. Penaliza fuertemente si no cumple Ix o A."""
        total_cost = 0.0
        total_co2 = 0.0
        penalty = 0.0

        for i in range(n_groups):
            g_spec = inp.groups[i]
            profile, route = _decode(genes, i)

            prof_Ix_cm4 = profile.Ix * 1e8 if profile.Ix < 1.0 else profile.Ix
            prof_A_cm2 = profile.A * 1e4 if profile.A < 1.0 else profile.A

            if prof_Ix_cm4 < g_spec.min_Ix:
                penalty += (g_spec.min_Ix - prof_Ix_cm4) * 10.0
            if prof_A_cm2 < g_spec.min_A:
                penalty += (g_spec.min_A - prof_A_cm2) * 100.0

            w_total = profile.weight_per_m * g_spec.length_total
            base_cost_per_ton = COST_USD_PER_TON.get(g_spec.country.upper(), COST_USD_PER_TON["DEFAULT"])
            mult = ROUTE_COST_MULTIPLIER.get(route, 1.0) if has_route_genes else 1.0
            cost_per_ton = base_cost_per_ton * mult
            co2_per_ton = EMBODIED_CO2_TON_PER_TON.get(route, EMBODIED_CO2_TON_PER_TON["average_global"])

            weight_t = w_total / 1000.0
            total_cost += weight_t * cost_per_ton
            total_co2 += weight_t * co2_per_ton

        if penalty > 0.0:
            total_cost += 1e6 + penalty * 1e5
            total_co2 += 1e5 + penalty * 1e4

        return total_cost, total_co2

    # 3. Ejecutar NSGA-II
    final_population = nsga2_run(
        objective_fn=evaluate_objectives,
        n_genes=n_genes,
        bounds=bounds,
        pop_size=inp.population_size,
        n_gen=inp.n_generations,
        seed=inp.random_seed,
    )

    # 4. Extraer soluciones no duplicadas de la última generación
    solutions_dict = {}

    for ind in final_population:
        assignment = {}
        routes_map = {}
        total_weight = 0.0
        feasible = True
        real_cost = 0.0
        real_co2 = 0.0

        for i in range(n_groups):
            g_spec = inp.groups[i]
            profile, route = _decode(ind.genes, i)
            assignment[g_spec.name] = profile.designation
            routes_map[g_spec.name] = route
            total_weight += profile.weight_per_m * g_spec.length_total

            prof_Ix_cm4 = profile.Ix * 1e8 if profile.Ix < 1.0 else profile.Ix
            prof_A_cm2 = profile.A * 1e4 if profile.A < 1.0 else profile.A

            if prof_Ix_cm4 < g_spec.min_Ix or prof_A_cm2 < g_spec.min_A:
                feasible = False

            weight_t = (profile.weight_per_m * g_spec.length_total) / 1000.0
            base_cost_per_ton = COST_USD_PER_TON.get(g_spec.country.upper(), COST_USD_PER_TON["DEFAULT"])
            mult = ROUTE_COST_MULTIPLIER.get(route, 1.0) if has_route_genes else 1.0
            real_cost += weight_t * base_cost_per_ton * mult
            real_co2 += weight_t * EMBODIED_CO2_TON_PER_TON.get(route, EMBODIED_CO2_TON_PER_TON["average_global"])

        key = (tuple(assignment.values()), tuple(routes_map.values())) if has_route_genes else tuple(assignment.values())
        if key not in solutions_dict:
            solutions_dict[key] = ParetoSolution(
                assignment=assignment,
                total_weight_kg=total_weight,
                total_cost_USD=real_cost,
                total_co2_tCO2=real_co2,
                feasible=feasible,
                steel_routes=routes_map if has_route_genes else None,
            )

    all_sols = list(solutions_dict.values())
    feasible_sols = [s for s in all_sols if s.feasible]
    pool = feasible_sols if feasible_sols else all_sols

    # Filtro estricto de no-dominancia de Pareto (Costo vs CO2)
    pareto_front: list[ParetoSolution] = []
    for candidate in pool:
        is_dominated = False
        for other in pool:
            if other is candidate:
                continue
            c_le = other.total_cost_USD <= candidate.total_cost_USD
            co2_le = other.total_co2_tCO2 <= candidate.total_co2_tCO2
            strictly_better = (other.total_cost_USD < candidate.total_cost_USD) or (other.total_co2_tCO2 < candidate.total_co2_tCO2)
            if c_le and co2_le and strictly_better:
                is_dominated = True
                break
        if not is_dominated:
            pareto_front.append(candidate)

    output_sols = sorted(pareto_front, key=lambda s: s.total_cost_USD)

    return ParetoOptimizeOutput(
        n_solutions=len(output_sols),
        solutions=output_sols,
    )
