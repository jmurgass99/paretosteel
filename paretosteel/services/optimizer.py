"""Servicio de optimización GA con tipado estable.

Envuelve :func:`paretosteel.genetic.optimize` y expone acceso al
catálogo de perfiles.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..exceptions import ConfigurationError, ConvergenceError


@dataclass
class GroupSpec:
    """Especificación de un grupo de elementos a optimizar."""
    name: str
    length_total: float
    min_Ix: float = 0.0
    min_A: float = 0.0
    family_filter: str | None = None


@dataclass
class OptimizerInput:
    """Entrada tipada al GA.

    Atributos:
        groups: lista de grupos.
        population_size, n_generations, crossover_rate, mutation_rate,
        elitism, penalty_factor, random_seed: parámetros del GA.
    """
    groups: list[GroupSpec]
    population_size: int = 40
    n_generations: int = 50
    crossover_rate: float = 0.7
    mutation_rate: float = 0.15
    elitism: int = 2
    penalty_factor: float = 1e6
    random_seed: int | None = None

    def validate(self) -> None:
        if not self.groups:
            raise ConfigurationError("Debe haber al menos un grupo")
        if self.population_size < 4:
            raise ConfigurationError("population_size debe ser >= 4")
        if self.n_generations < 1:
            raise ConfigurationError("n_generations debe ser >= 1")
        if not (0.0 <= self.crossover_rate <= 1.0):
            raise ConfigurationError("crossover_rate debe estar en [0, 1]")
        if not (0.0 <= self.mutation_rate <= 1.0):
            raise ConfigurationError("mutation_rate debe estar en [0, 1]")
        if self.elitism < 0 or self.elitism >= self.population_size:
            raise ConfigurationError("elitism debe estar en [0, population_size)")
        names = [g.name for g in self.groups]
        if len(set(names)) != len(names):
            raise ConfigurationError("Los grupos deben tener nombres únicos")


@dataclass
class OptimizerResult:
    """Resultado tipado del GA."""
    assignment: dict[str, str]
    weight: float
    penalty: float
    fitness: float
    history: list[float] = field(default_factory=list)
    feasible: bool = True


def run_ga_optimizer(inp: OptimizerInput) -> OptimizerResult:
    """Ejecuta el GA con los parámetros dados.

    Args:
        inp: entrada validada.

    Returns:
        OptimizerResult serializable.

    Raises:
        ConfigurationError: entrada inválida.
        ConvergenceError: el GA terminó sin solución factible (penalty>0).
            Se lanza sólo si el caller marca ``inp.elitism > 0``; los
            casos de búsqueda exploratoria con penalty>0 NO disparan.
            (Se mantiene como excepción documentada; en esta versión
            simplemente nunca se lanza para preservar compatibilidad.)
    """
    inp.validate()
    from ..genetic import ElementGroup, GAConfig, optimize

    cfg = GAConfig(
        population_size=inp.population_size,
        n_generations=inp.n_generations,
        crossover_rate=inp.crossover_rate,
        mutation_rate=inp.mutation_rate,
        elitism=inp.elitism,
        penalty_factor=inp.penalty_factor,
        random_seed=inp.random_seed,
    )
    groups = [
        ElementGroup(
            name=g.name,
            length_total=g.length_total,
            min_Ix=g.min_Ix,
            min_A=g.min_A,
            family_filter=g.family_filter,
        )
        for g in inp.groups
    ]
    try:
        res = optimize(groups, config=cfg)
    except Exception as exc:  # pragma: no cover - defensa
        raise ConvergenceError(f"GA falló: {exc}") from exc

    return OptimizerResult(
        assignment=dict(res.best.assignment),
        weight=float(res.best.weight),
        penalty=float(res.best.penalty),
        fitness=float(res.best.fitness),
        history=[float(h) for h in res.history],
        feasible=res.best.penalty == 0,
    )


def list_catalog(family: str | None = None) -> list[dict]:
    """Devuelve el catálogo (opcionalmente filtrado por familia).

    Args:
        family: 'W', 'IPE', 'HEB', o None para todos.

    Returns:
        Lista de dicts con los datos de cada perfil.
    """
    from ..catalogs import all_profiles, filter_profiles

    profs = filter_profiles(family=family) if family else all_profiles()
    return [
        {
            "designation": p.designation,
            "family": p.family,
            "weight_per_m": p.weight_per_m,
            "A": p.A,
            "Ix": p.Ix,
            "Iy": p.Iy,
            "d": p.d,
            "bf": p.bf,
        }
        for p in profs
    ]
