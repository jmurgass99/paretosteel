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


class ParetoOptimizeInput(BaseModel):
    """Parámetros para ejecutar el optimizador multicriterio Pareto NSGA-II."""
    groups: List[ParetoGroupSpec] = Field(..., description="Grupos de acero a optimizar")
    population_size: int = Field(40, description="Tamaño de la población del GA", ge=10, le=200)
    n_generations: int = Field(30, description="Número de generaciones de optimización", ge=5, le=100)
    random_seed: int = Field(42, description="Semilla aleatoria para reproducibilidad")


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
        
    # 1. Preparar catálogos filtrados para cada grupo
    group_catalogs = []
    for g in inp.groups:
        profs = filter_profiles(family=g.family_filter) if g.family_filter else all_profiles()
        # Ordenar por peso por metro para consistencia
        profs = sorted(profs, key=lambda p: p.weight_per_m)
        if not profs:
            raise ValueError(f"No hay perfiles disponibles en el catálogo para el filtro '{g.family_filter}' en el grupo {g.name}")
        group_catalogs.append(profs)
        
    n_genes = len(inp.groups)
    
    # Límites de búsqueda para los genes (índices continuos dentro de los catálogos correspondientes)
    bounds = [(0.0, float(len(group_catalogs[i]) - 1)) for i in range(n_genes)]
    
    # 2. Definir función de evaluación multiobjetivo
    def evaluate_objectives(genes: list[float]) -> tuple[float, float]:
        """Calcula el costo y CO2 totales. Penaliza fuertemente si no cumple Ix o A."""
        total_weight = 0.0
        total_cost = 0.0
        total_co2 = 0.0
        penalty = 0.0
        
        for i, gene_val in enumerate(genes):
            g_spec = inp.groups[i]
            catalog = group_catalogs[i]
            
            # Mapear gen continuo a índice entero
            idx = int(round(gene_val))
            idx = max(0, min(idx, len(catalog) - 1))
            profile = catalog[idx]
            
            # Verificación de restricciones
            # Ix en catalogs está en cm4. A en cm2.
            if profile.Ix < g_spec.min_Ix:
                penalty += (g_spec.min_Ix - profile.Ix) * 10.0
            if profile.A < g_spec.min_A:
                penalty += (g_spec.min_A - profile.A) * 100.0
                
            # Volumetría y peso
            w_total = profile.weight_per_m * g_spec.length_total
            total_weight += w_total
            
            # Costos por país
            cost_per_ton = COST_USD_PER_TON.get(g_spec.country.upper(), COST_USD_PER_TON["DEFAULT"])
            # CO2 por grado
            co2_per_ton = EMBODIED_CO2_TON_PER_TON.get(g_spec.steel_grade, EMBODIED_CO2_TON_PER_TON["average_global"])
            
            weight_t = w_total / 1000.0
            total_cost += weight_t * cost_per_ton
            total_co2 += weight_t * co2_per_ton
            
        # Penalización si no cumple las inercias o áreas
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
        seed=inp.random_seed
    )
    
    # 4. Extraer y filtrar solo las soluciones dominantes únicas y factibles
    solutions_dict = {}
    
    for ind in final_population:
        # Reconstruir la asignación de perfiles
        assignment = {}
        total_weight = 0.0
        feasible = True
        
        for i, gene_val in enumerate(ind.genes):
            g_spec = inp.groups[i]
            catalog = group_catalogs[i]
            idx = int(round(gene_val))
            idx = max(0, min(idx, len(catalog) - 1))
            profile = catalog[idx]
            
            assignment[g_spec.name] = profile.designation
            total_weight += profile.weight_per_m * g_spec.length_total
            
            if profile.Ix < g_spec.min_Ix or profile.A < g_spec.min_A:
                feasible = True  # La factibilidad se verifica a nivel macro de penalización, pero lo re-verificamos estricto
                # Si no cumple, lo marcamos infactible
                if profile.Ix < g_spec.min_Ix or profile.A < g_spec.min_A:
                    feasible = False
                    
        # Re-calcular costos reales limpios sin penalización
        real_cost = 0.0
        real_co2 = 0.0
        for i, gene_val in enumerate(ind.genes):
            g_spec = inp.groups[i]
            catalog = group_catalogs[i]
            idx = int(round(gene_val))
            idx = max(0, min(idx, len(catalog) - 1))
            profile = catalog[idx]
            
            weight_t = (profile.weight_per_m * g_spec.length_total) / 1000.0
            real_cost += weight_t * COST_USD_PER_TON.get(g_spec.country.upper(), COST_USD_PER_TON["DEFAULT"])
            real_co2 += weight_t * EMBODIED_CO2_TON_PER_TON.get(g_spec.steel_grade, EMBODIED_CO2_TON_PER_TON["average_global"])
            
        # Agrupar por designación única para evitar duplicados en la frontera de Pareto expuesta al usuario
        key = tuple(assignment.values())
        if key not in solutions_dict:
            solutions_dict[key] = ParetoSolution(
                assignment=assignment,
                total_weight_kg=total_weight,
                total_cost_USD=real_cost,
                total_co2_tCO2=real_co2,
                feasible=feasible
            )
            
    # Filtrar solo factibles si las hay, ordenar por costo ascendente
    all_sols = list(solutions_dict.values())
    feasible_sols = [s for s in all_sols if s.feasible]
    
    output_sols = feasible_sols if feasible_sols else all_sols
    output_sols = sorted(output_sols, key=lambda s: s.total_cost_USD)
    
    return ParetoOptimizeOutput(
        n_solutions=len(output_sols),
        solutions=output_sols
    )
