"""Algoritmo Genético para optimización de peso de pórticos de acero.

Cada gen es un perfil de acero asignado a un grupo de elementos.
El cromosoma representa la asignación grupo → perfil.
Fitness = peso total + penalización proporcional al déficit relativo de inercia
(min_Ix) y de área (min_A) de cada grupo. No hay comprobación normativa dentro del
GA: los mínimos de Ix y A los fija quien llama (de un análisis o predimensionado).
"""
from __future__ import annotations
import logging
import random
from dataclasses import dataclass, field

from .catalogs import SteelProfile, all_profiles, filter_profiles

log = logging.getLogger("paretosteel")


@dataclass
class ElementGroup:
    """Grupo de elementos (columnas piso 1, vigas eje X, etc.) a optimizar
    en conjunto: todos reciben el mismo perfil.

    Atributos:
        name: identificador del grupo
        length_total: longitud total de elementos en este grupo (m)
        min_Ix: inercia eje fuerte mínima requerida (m⁴, de análisis previo)
        min_A: área mínima requerida (m², de chequeo axial)
        family_filter: limitar a una familia (W/IPE/HEB) o None
    """
    name: str
    length_total: float
    min_Ix: float = 0.0
    min_A: float = 0.0
    family_filter: str | None = None


@dataclass(frozen=True)
class Individual:
    """Solución candidata: una asignación grupo → perfil."""
    assignment: tuple[tuple[str, str], ...]  # ((group_name, profile_designation), ...)
    weight: float
    penalty: float

    @property
    def fitness(self) -> float:
        """Menor es mejor (peso + penalización)."""
        return self.weight + self.penalty


@dataclass
class GAConfig:
    population_size: int = 40
    n_generations: int = 50
    crossover_rate: float = 0.7
    mutation_rate: float = 0.15
    elitism: int = 2
    penalty_factor: float = 1e6  # multiplicador para violaciones
    random_seed: int | None = None


@dataclass
class GAResult:
    best: Individual
    history: list[float] = field(default_factory=list)  # best fitness por gen


def _evaluate(assignment: tuple[tuple[str, str], ...],
               groups: dict[str, ElementGroup],
               profile_lookup: dict[str, SteelProfile],
               penalty_factor: float) -> Individual:
    weight = 0.0
    penalty = 0.0
    for group_name, prof_des in assignment:
        g = groups[group_name]
        p = profile_lookup[prof_des]
        weight += p.weight_per_m * g.length_total
        if p.Ix < g.min_Ix:
            penalty += penalty_factor * (g.min_Ix - p.Ix) / max(g.min_Ix, 1e-9)
        if p.A < g.min_A:
            penalty += penalty_factor * (g.min_A - p.A) / max(g.min_A, 1e-9)
    return Individual(assignment=assignment, weight=weight, penalty=penalty)


def _candidates_for_group(g: ElementGroup,
                            profile_lookup: dict[str, SteelProfile]) -> list[str]:
    """Perfiles candidatos de un grupo: los del catálogo de ESTA optimización
    (``profile_lookup``, que respeta ``custom_profiles``) filtrados por familia.

    Las restricciones min_Ix/min_A no filtran: se imponen por penalización en
    ``_evaluate``. Antes se leía el catálogo global, y con ``custom_profiles``
    el GA elegía perfiles que no estaban en ``profile_lookup`` (KeyError).
    """
    fam = g.family_filter.upper() if g.family_filter else None
    cands = [p.designation for p in profile_lookup.values()
             if fam is None or p.family == fam]
    if not cands:
        raise ValueError(
            f"El grupo '{g.name}' no tiene perfiles de la familia "
            f"'{g.family_filter}' en el catálogo de la optimización")
    return cands


def _random_individual(groups: dict[str, ElementGroup],
                         profile_lookup: dict[str, SteelProfile],
                         rng: random.Random) -> tuple[tuple[str, str], ...]:
    return tuple(
        (name, rng.choice(_candidates_for_group(g, profile_lookup)))
        for name, g in groups.items()
    )


def _crossover(a: tuple[tuple[str, str], ...],
                b: tuple[tuple[str, str], ...],
                rng: random.Random) -> tuple[tuple[str, str], ...]:
    """Uniform crossover por grupo."""
    return tuple(
        a[i] if rng.random() < 0.5 else b[i]
        for i in range(len(a))
    )


def _mutate(ind: tuple[tuple[str, str], ...],
             groups: dict[str, ElementGroup],
             profile_lookup: dict[str, SteelProfile],
             mutation_rate: float,
             rng: random.Random) -> tuple[tuple[str, str], ...]:
    out = list(ind)
    for i, (gname, _) in enumerate(out):
        if rng.random() < mutation_rate:
            g = groups[gname]
            out[i] = (gname, rng.choice(_candidates_for_group(g, profile_lookup)))
    return tuple(out)


def optimize(groups: list[ElementGroup], *,
              config: GAConfig | None = None,
              custom_profiles: list[SteelProfile] | None = None) -> GAResult:
    """Optimiza la asignación de perfiles a grupos usando GA.

    Args:
        groups: lista de grupos a optimizar.
        config: parámetros del GA.
        custom_profiles: catálogo de perfiles disponibles (si None usa todos).

    Returns:
        GAResult con la mejor solución y el historial de fitness.
    """
    cfg = config or GAConfig()
    rng = random.Random(cfg.random_seed)
    group_map = {g.name: g for g in groups}
    profiles = custom_profiles if custom_profiles is not None else all_profiles()
    profile_lookup = {p.designation: p for p in profiles}

    # Población inicial
    population = [
        _evaluate(_random_individual(group_map, profile_lookup, rng),
                   group_map, profile_lookup, cfg.penalty_factor)
        for _ in range(cfg.population_size)
    ]
    population.sort(key=lambda i: i.fitness)
    history = [population[0].fitness]

    for gen in range(cfg.n_generations):
        # Elitismo
        new_pop = list(population[: cfg.elitism])
        # Selección por torneo + crossover + mutación
        while len(new_pop) < cfg.population_size:
            p1 = min(rng.sample(population, 3), key=lambda i: i.fitness)
            p2 = min(rng.sample(population, 3), key=lambda i: i.fitness)
            if rng.random() < cfg.crossover_rate:
                child_asgn = _crossover(p1.assignment, p2.assignment, rng)
            else:
                child_asgn = p1.assignment
            child_asgn = _mutate(child_asgn, group_map, profile_lookup,
                                  cfg.mutation_rate, rng)
            new_pop.append(_evaluate(child_asgn, group_map, profile_lookup,
                                       cfg.penalty_factor))
        population = sorted(new_pop, key=lambda i: i.fitness)
        history.append(population[0].fitness)
        log.debug(f"GA gen {gen}: best fitness = {population[0].fitness:.2f}")

    log.info(
        f"GA done: {cfg.n_generations} generations, "
        f"best weight = {population[0].weight:.1f} kg, "
        f"penalty = {population[0].penalty:.1f}"
    )
    return GAResult(best=population[0], history=history)
