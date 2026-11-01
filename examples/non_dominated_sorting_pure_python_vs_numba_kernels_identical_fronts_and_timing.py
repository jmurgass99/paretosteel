"""Clasificación no dominada de NSGA-II: Python puro frente a los dos kernels Numba del paquete.

Tres implementaciones de la misma operación (Deb et al., 2002, «fast non-dominated sorting»):
  · `nsga2.non_dominated_sort` (Python puro, lista de frentes)
  · `_nsga2_fast.non_dominated_sort_fast` (Numba, devuelve los frentes en el mismo orden que el puro)
  · `nsga2_jit.non_dominated_sort_jit` (Numba, devuelve el rango de cada individuo)
Sobre poblaciones aleatorias de 2 y 3 objetivos se comprueba que las tres dan los mismos rangos, que
el frente 0 no contiene ningún par dominado (comprobación por fuerza bruta escrita aquí) y se mide el
tiempo. La primera llamada a un kernel Numba incluye la compilación y no se cronometra.

Ejecutar:  python examples/non_dominated_sorting_pure_python_vs_numba_kernels_identical_fronts_and_timing.py
"""
import random
import time

import numpy as np

from paretosteel._nsga2_fast import non_dominated_sort_fast
from paretosteel.nsga2 import Individual, dominates, non_dominated_sort
from paretosteel.nsga2_jit import calculate_crowding_distance_jit, non_dominated_sort_jit


def population(n, m, seed):
    rng = random.Random(seed)
    return [Individual(genes=[], fitness=tuple(rng.random() for _ in range(m))) for _ in range(n)]


def main() -> None:
    warm = population(20, 2, 0)
    non_dominated_sort_fast(warm)
    non_dominated_sort_jit(np.array([i.fitness for i in warm]))

    print(f"  {'N':>5} {'M':>2} {'frentes':>7} {'|F0|':>5} {'puro [ms]':>10} {'fast [ms]':>10} {'jit [ms]':>9} {'iguales':>8}")
    all_equal = True
    speedups = []
    for n, m in ((200, 2), (400, 2), (400, 3), (800, 3)):
        p1, p2 = population(n, m, n + m), population(n, m, n + m)
        t0 = time.perf_counter(); fr_pure = non_dominated_sort(p1); t_pure = time.perf_counter() - t0
        t0 = time.perf_counter(); fr_fast = non_dominated_sort_fast(p2); t_fast = time.perf_counter() - t0
        fit = np.array([i.fitness for i in p1], dtype=np.float64)
        t0 = time.perf_counter(); ranks_jit = non_dominated_sort_jit(fit); t_jit = time.perf_counter() - t0
        ranks_pure = [i.rank for i in p1]
        eq = fr_pure == fr_fast and ranks_pure == [i.rank for i in p2] and ranks_pure == list(ranks_jit)
        all_equal &= eq
        speedups.append(t_pure / t_fast)
        # Fuerza bruta: nadie del frente 0 está dominado por nadie de la población.
        f0 = fr_pure[0]
        assert not any(dominates(p1[q].fitness, p1[i].fitness) for i in f0 for q in range(n))
        print(f"  {n:5d} {m:2d} {len(fr_pure):7d} {len(f0):5d} {t_pure * 1e3:10.1f} {t_fast * 1e3:10.2f} "
              f"{t_jit * 1e3:9.2f} {'sí' if eq else 'NO':>8}")
    print(f"\nRangos idénticos en las tres implementaciones: {'sí' if all_equal else 'NO'}; "
          f"el kernel `fast` es entre {min(speedups):.0f} y {max(speedups):.0f} veces más rápido que el puro.")

    pts = np.array([[1.0, 5.0], [2.0, 3.0], [3.0, 2.0], [5.0, 1.0], [4.0, 4.0]])
    r = non_dominated_sort_jit(pts)
    cd = calculate_crowding_distance_jit(pts, r)
    # Frente 0 = los cuatro primeros. Extremos (1,5) y (5,1) → 1e9. Interiores, a mano:
    #   (2,3): (3−1)/(5−1) + (5−2)/(5−1) = 0,5 + 0,75 = 1,25;  (3,2): (5−2)/4 + (3−1)/4 = 0,75 + 0,5 = 1,25
    print(f"Distancia de apiñamiento de un frente de cuatro puntos: {[round(float(c), 3) for c in cd[:4]]} "
          f"(a mano: extremos 1e9, interiores 1,25 y 1,25); el punto (4,4) tiene rango {int(r[4])}.")


if __name__ == "__main__":
    main()
