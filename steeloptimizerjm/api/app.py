from __future__ import annotations

"""FastAPI app para SteelOptimizerJm.

Instalar con::

    pip install steeloptimizerjm[api]
"""
try:
    from pydantic import BaseModel, Field
except ImportError as exc:  # pragma: no cover
    from ..exceptions import DependencyError
    raise DependencyError(
        "FastAPI no está instalado. Instale: pip install steeloptimizerjm[api]"
    ) from exc

from ..exceptions import DependencyError


class GroupBody(BaseModel):
    name: str
    length_total: float = Field(..., gt=0)
    min_Ix: float = 0.0
    min_A: float = 0.0
    family_filter: str | None = None


class GABody(BaseModel):
    groups: list[GroupBody]
    population_size: int = 40
    n_generations: int = 50
    crossover_rate: float = 0.7
    mutation_rate: float = 0.15
    elitism: int = 2
    penalty_factor: float = 1e6
    random_seed: int | None = None


class BeamOptimizeBody(BaseModel):
    L_m: float = Field(..., gt=0, description="Luz (m)")
    M_Ed_kNm: float = Field(..., ge=0)
    V_Ed_kN: float = Field(default=0.0, ge=0)
    Fy_MPa: float = 345.0
    E_MPa: float = 200000.0
    deflection_limit: float = 360.0
    w_service_kN_m: float = 10.0
    section_family: str = "W"
    max_weight_kg_m: float = 200.0


class ColumnOptimizeBody(BaseModel):
    L_m: float = Field(..., gt=0, description="Longitud/Altura (m)")
    P_Ed_kN: float = Field(..., ge=0, description="Carga axial de diseño (kN)")
    K: float = 1.0
    Fy_MPa: float = 345.0
    E_MPa: float = 200000.0
    section_family: str = "W"
    max_weight_kg_m: float = 200.0



def create_router():
    """Devuelve el APIRouter con los endpoints del optimizador.

    Raises:
        DependencyError: si FastAPI no está instalado.
    """
    try:
        from fastapi import APIRouter, HTTPException, Query
    except ImportError as exc:  # pragma: no cover
        raise DependencyError(
            "FastAPI no está instalado. Instale: pip install steeloptimizerjm[api]"
        ) from exc

    from ..exceptions import ConfigurationError
    from ..services.optimizer import (
        GroupSpec, OptimizerInput, run_ga_optimizer, list_catalog,
    )
    from ..services import (
        BeamOptimizationInput, optimize_beam,
        ColumnOptimizationInput, optimize_column,
    )

    router = APIRouter()

    @router.post("/api/optimizer/ga")
    def post_ga(body: GABody) -> dict:
        try:
            inp = OptimizerInput(
                groups=[GroupSpec(**g.model_dump()) for g in body.groups],
                population_size=body.population_size,
                n_generations=body.n_generations,
                crossover_rate=body.crossover_rate,
                mutation_rate=body.mutation_rate,
                elitism=body.elitism,
                penalty_factor=body.penalty_factor,
                random_seed=body.random_seed,
            )
            res = run_ga_optimizer(inp)
        except ConfigurationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {
            "assignment": res.assignment,
            "weight": res.weight,
            "penalty": res.penalty,
            "fitness": res.fitness,
            "feasible": res.feasible,
            "n_generations": len(res.history),
        }

    @router.get("/api/optimizer/catalog")
    def get_catalog(family: str | None = Query(default=None)) -> dict:
        return {"profiles": list_catalog(family=family)}

    @router.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @router.post("/optimize/beam")
    def post_optimize_beam(body: BeamOptimizeBody) -> dict:
        try:
            res = optimize_beam(BeamOptimizationInput(
                L_m=body.L_m, M_Ed_kNm=body.M_Ed_kNm, V_Ed_kN=body.V_Ed_kN,
                Fy_MPa=body.Fy_MPa, E_MPa=body.E_MPa,
                deflection_limit=body.deflection_limit,
                w_service_kN_m=body.w_service_kN_m,
                section_family=body.section_family,
                max_weight_kg_m=body.max_weight_kg_m,
            ))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {
            "best_section": res.best_section,
            "weight_kg_m": res.weight_kg_m,
            "M_capacity_kNm": res.M_capacity_kNm,
            "utilization_M": res.utilization_M,
            "deflection_mm": res.deflection_mm,
            "deflection_limit_mm": res.deflection_limit_mm,
            "deflection_OK": res.deflection_OK,
            "is_feasible": res.is_feasible,
            "n_candidates_evaluated": res.n_candidates_evaluated,
            "notes": list(res.notes),
        }

    @router.post("/optimize/column")
    def post_optimize_column(body: ColumnOptimizeBody) -> dict:
        try:
            res = optimize_column(ColumnOptimizationInput(
                L_m=body.L_m, P_Ed_kN=body.P_Ed_kN, K=body.K,
                Fy_MPa=body.Fy_MPa, E_MPa=body.E_MPa,
                section_family=body.section_family,
                max_weight_kg_m=body.max_weight_kg_m,
            ))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {
            "best_section": res.best_section,
            "weight_kg_m": res.weight_kg_m,
            "P_capacity_kN": res.P_capacity_kN,
            "utilization_P": res.utilization_P,
            "slenderness": res.slenderness,
            "is_feasible": res.is_feasible,
            "n_candidates_evaluated": res.n_candidates_evaluated,
            "notes": list(res.notes),
        }

    return router


def create_app():
    """Crea la app FastAPI standalone.

    Raises:
        DependencyError: si FastAPI no está instalado.
    """
    try:
        from fastapi import FastAPI
    except ImportError as exc:  # pragma: no cover
        raise DependencyError(
            "FastAPI no está instalado. Instale: pip install steeloptimizerjm[api]"
        ) from exc

    app = FastAPI(title="SteelOptimizerJm API", version="1.0.0")
    app.include_router(create_router())
    return app


__all__ = ["create_app", "create_router"]

