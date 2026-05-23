"""NSGA-II - Non-dominated Sorting Genetic Algorithm II (pure Python).

Implementacion compacta para optimizacion multi-objetivo (Pareto).
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Callable


@dataclass
class Individual:
    genes: list[float]
    fitness: tuple[float, ...] = ()
    rank: int = 0
    crowding: float = 0.0


def dominates(a: tuple[float, ...], b: tuple[float, ...]) -> bool:
    better_any = False
    for ai, bi in zip(a, b):
        if ai > bi:
            return False
        if ai < bi:
            better_any = True
    return better_any


def non_dominated_sort(pop: list[Individual]) -> list[list[int]]:
    S = [[] for _ in pop]
    n = [0] * len(pop)
    fronts: list[list[int]] = [[]]
    for p in range(len(pop)):
        for q in range(len(pop)):
            if p == q:
                continue
            if dominates(pop[p].fitness, pop[q].fitness):
                S[p].append(q)
            elif dominates(pop[q].fitness, pop[p].fitness):
                n[p] += 1
        if n[p] == 0:
            pop[p].rank = 0
            fronts[0].append(p)
    i = 0
    while fronts[i]:
        nxt = []
        for p in fronts[i]:
            for q in S[p]:
                n[q] -= 1
                if n[q] == 0:
                    pop[q].rank = i + 1
                    nxt.append(q)
        i += 1
        fronts.append(nxt)
    return fronts[:-1]


def crowding_distance(front: list[int], pop: list[Individual]) -> None:
    if not front:
        return
    k = len(pop[front[0]].fitness)
    for idx in front:
        pop[idx].crowding = 0.0
    for m in range(k):
        front_sorted = sorted(front, key=lambda i: pop[i].fitness[m])
        pop[front_sorted[0]].crowding = float("inf")
        pop[front_sorted[-1]].crowding = float("inf")
        fmin = pop[front_sorted[0]].fitness[m]
        fmax = pop[front_sorted[-1]].fitness[m]
        if fmax - fmin < 1e-12:
            continue
        for i in range(1, len(front_sorted) - 1):
            pop[front_sorted[i]].crowding += (
                pop[front_sorted[i + 1]].fitness[m] - pop[front_sorted[i - 1]].fitness[m]
            ) / (fmax - fmin)


def nsga2_run(
    objective_fn: Callable[[list[float]], tuple[float, ...]],
    n_genes: int,
    bounds: list[tuple[float, float]],
    pop_size: int = 40,
    n_gen: int = 30,
    seed: int = 0,
    fast: bool = False,
) -> list[Individual]:
    # `fast=True` usa el kernel Numba para la clasificación no dominada
    # (idéntica a la pura, solo más rápida). Default False = comportamiento previo.
    if fast:
        from ._nsga2_fast import non_dominated_sort_fast as _sort
    else:
        _sort = non_dominated_sort
    rng = random.Random(seed)
    pop = [
        Individual(genes=[rng.uniform(*bounds[i]) for i in range(n_genes)])
        for _ in range(pop_size)
    ]
    for ind in pop:
        ind.fitness = objective_fn(ind.genes)
    for _ in range(n_gen):
        # crossover + mutation
        children: list[Individual] = []
        while len(children) < pop_size:
            p1, p2 = rng.sample(pop, 2)
            alpha = rng.random()
            ch_genes = [
                max(min(alpha * a + (1 - alpha) * b + rng.gauss(0, 0.01 * (bounds[i][1] - bounds[i][0])), bounds[i][1]), bounds[i][0])
                for i, (a, b) in enumerate(zip(p1.genes, p2.genes))
            ]
            ch = Individual(genes=ch_genes)
            ch.fitness = objective_fn(ch.genes)
            children.append(ch)
        all_ind = pop + children
        fronts = _sort(all_ind)
        new_pop: list[Individual] = []
        for f in fronts:
            crowding_distance(f, all_ind)
            f_sorted = sorted(f, key=lambda i: (all_ind[i].rank, -all_ind[i].crowding))
            for idx in f_sorted:
                if len(new_pop) < pop_size:
                    new_pop.append(all_ind[idx])
            if len(new_pop) >= pop_size:
                break
        pop = new_pop
    return pop


__all__ = ["Individual", "dominates", "non_dominated_sort",
           "crowding_distance", "nsga2_run"]
