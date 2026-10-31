"""Kernel acelerado (Numba JIT) del non-dominated sorting de NSGA-II.

El cuello de botella de NSGA-II es la clasificación no dominada: O(M·N²)
comparaciones de dominancia (N = tamaño de población, M = nº de objetivos).
En Python puro, el tipado dinámico hace ese bucle anidado caro.

Estrategia: el kernel JIT calcula SOLO la parte pesada —la matriz de dominancia
`S[p,q]` y el contador `n[p]`— compilada a código máquina. La construcción de
los frentes (BFS barato) se rehace en Python EXACTAMENTE igual que la versión
pura (`nsga2.non_dominated_sort`), recorriendo `q` en orden creciente, de modo
que el resultado es **byte-idéntico** al puro (mismos frentes, mismo orden,
mismos ranks). Esto permite usar el camino rápido como drop-in sin cambiar el
comportamiento del algoritmo.

Si Numba no está instalado, `njit` cae a un decorador no-op y el mismo código
corre en Python/NumPy (más lento, pero correcto e idéntico).
"""
from __future__ import annotations

import numpy as np

try:  # pragma: no cover - depende del entorno
    from numba import njit
    NUMBA_AVAILABLE = True
except Exception:  # pragma: no cover
    NUMBA_AVAILABLE = False

    def njit(*args, **kwargs):
        """Fallback: decorador no-op si Numba no está disponible."""
        if args and callable(args[0]):
            return args[0]

        def _deco(fn):
            return fn

        return _deco


@njit(cache=True)
def _dominates(a, b, n_obj):
    """True si `a` domina a `b` (minimización): ningún a_i > b_i y algún a_i < b_i."""
    better_any = False
    for i in range(n_obj):
        if a[i] > b[i]:
            return False
        if a[i] < b[i]:
            better_any = True
    return better_any


@njit(cache=True)
def _fast_sort(fit):
    """Clasificación no dominada COMPLETA en código máquina (dominancia + BFS).

    Replica exactamente el orden de descubrimiento de la versión pura
    (`nsga2.non_dominated_sort`): frente 0 con p creciente; luego, por cada p del
    frente, q creciente. Así los frentes salen byte-idénticos.

    Args:
        fit: array (N, M) float64 de fitness.
    Returns:
        ranks: array (N,) int64 — rank de cada individuo.
        order: array (N,) int64 — índices en el orden de descubrimiento (todos los frentes concatenados).
        front_sizes: array (N+1,) int64 — tamaño de cada frente.
        n_fronts: int — nº de frentes no vacíos.
    """
    n_ind = fit.shape[0]
    n_obj = fit.shape[1]

    # Matriz de dominancia S[p,q] (p domina q) y contador n[p] (cuántos dominan a p).
    S = np.zeros((n_ind, n_ind), dtype=np.bool_)
    n = np.zeros(n_ind, dtype=np.int64)
    for p in range(n_ind):
        for q in range(n_ind):
            if p == q:
                continue
            if _dominates(fit[p], fit[q], n_obj):
                S[p, q] = True
            elif _dominates(fit[q], fit[p], n_obj):
                n[p] += 1

    ranks = np.empty(n_ind, dtype=np.int64)
    order = np.empty(n_ind, dtype=np.int64)
    front_sizes = np.zeros(n_ind + 1, dtype=np.int64)
    pos = 0

    # Frente 0: no dominados, en orden creciente de p.
    for p in range(n_ind):
        if n[p] == 0:
            ranks[p] = 0
            order[pos] = p
            pos += 1
            front_sizes[0] += 1

    # BFS por frentes.
    i = 0
    front_start = 0
    while front_sizes[i] > 0:
        cur_size = front_sizes[i]
        for k in range(front_start, front_start + cur_size):
            p = order[k]
            for q in range(n_ind):  # q creciente → mismo orden que el puro
                if S[p, q]:
                    n[q] -= 1
                    if n[q] == 0:
                        ranks[q] = i + 1
                        order[pos] = q
                        pos += 1
                        front_sizes[i + 1] += 1
        front_start += cur_size
        i += 1

    return ranks, order, front_sizes, i


def non_dominated_sort_fast(pop) -> list[list[int]]:
    """Drop-in acelerado de `nsga2.non_dominated_sort`.

    Asigna `pop[i].rank` y devuelve los frentes como `list[list[int]]`, con el
    mismo contenido y orden que la versión pura.
    """
    if not pop:
        return []
    fit = np.array([ind.fitness for ind in pop], dtype=np.float64)
    ranks, order, front_sizes, n_fronts = _fast_sort(fit)

    for idx in range(len(pop)):
        pop[idx].rank = int(ranks[idx])

    fronts: list[list[int]] = []
    start = 0
    for i in range(n_fronts):
        size = int(front_sizes[i])
        fronts.append([int(order[k]) for k in range(start, start + size)])
        start += size
    return fronts


__all__ = ["non_dominated_sort_fast", "NUMBA_AVAILABLE"]
