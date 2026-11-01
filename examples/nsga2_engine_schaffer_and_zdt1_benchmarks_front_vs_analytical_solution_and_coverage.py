"""Motor NSGA-II genérico (`nsga2.nsga2_run`) contra dos problemas de prueba con frente analítico.

  · Schaffer N.1: f1 = x², f2 = (x − 2)², x ∈ [−5, 5]. Conjunto de Pareto x ∈ [0, 2];
    frente f2 = (√f1 − 2)².
  · ZDT1 (Zitzler, Deb y Thiele, 2000) con 4 variables en [0, 1]: f1 = x1, g = 1 + 9·Σx_i/(n−1),
    f2 = g·(1 − √(f1/g)). Frente de Pareto (g = 1): f2 = 1 − √f1 con f1 ∈ [0, 1].
Se mide la distancia media al frente analítico (convergencia) y el tramo de f1 que cubre la población
final (diversidad), con el kernel puro y con el kernel Numba (`fast=True`), que deben dar lo mismo.

`nsga2_run` es una versión compacta: padres al azar (sin torneo), cruce por combinación convexa y
mutación gaussiana del 1 % del rango. Converge bien, pero pierde diversidad en problemas como ZDT1.

Ejecutar:  python examples/nsga2_engine_schaffer_and_zdt1_benchmarks_front_vs_analytical_solution_and_coverage.py
"""
import math
import time

from paretosteel.nsga2 import nsga2_run


def schaffer(x):
    return (x[0] ** 2, (x[0] - 2.0) ** 2)


def zdt1(x):
    n = len(x)
    g = 1.0 + 9.0 * sum(x[1:]) / (n - 1)
    return (x[0], g * (1.0 - math.sqrt(x[0] / g)))


def main() -> None:
    pop = nsga2_run(schaffer, 1, [(-5.0, 5.0)], pop_size=40, n_gen=60, seed=1)
    xs = [i.genes[0] for i in pop]
    err = max(abs(i.fitness[1] - (math.sqrt(i.fitness[0]) - 2.0) ** 2) for i in pop)
    inside = sum(1 for x in xs if -1e-9 <= x <= 2.0 + 1e-9)
    print("Schaffer N.1 (población 40, 60 generaciones)")
    print(f"  {inside}/40 individuos en el conjunto de Pareto x ∈ [0, 2]; x de {min(xs):.4f} a {max(xs):.4f}")
    print(f"  máximo |f2 − (√f1 − 2)²| = {err:.2e}  → la población final está sobre el frente analítico")

    print("\nZDT1, 4 variables (población 80, 300 generaciones)")
    print(f"  {'semilla':>7} {'kernel':>6} {'t [s]':>6} {'frente':>6} {'dist. media':>11} {'f1 cubierto':>16}")
    covers = []
    gds = []
    for seed in (1, 2, 3):
        res = {}
        for fast in ((False, True) if seed == 1 else (True,)):
            t0 = time.perf_counter()
            p = nsga2_run(zdt1, 4, [(0.0, 1.0)] * 4, pop_size=80, n_gen=300, seed=seed, fast=fast)
            dt = time.perf_counter() - t0
            front = [i for i in p if i.rank == 0]
            gd = sum(abs(i.fitness[1] - (1.0 - math.sqrt(i.fitness[0]))) for i in front) / len(front)
            f1 = [i.fitness[0] for i in front]
            res[fast] = [tuple(i.genes) for i in p]
            print(f"  {seed:7d} {'numba' if fast else 'puro':>6} {dt:6.2f} {len(front):6d} {gd:11.4f} "
                  f"{min(f1):7.3f} – {max(f1):5.3f}")
            if fast:
                covers.append(max(f1) - min(f1))
                gds.append(gd)
        if False in res:
            same = res[False] == res[True]
            print(f"  {'':7} los dos kernels dan la misma población final: {'sí' if same else 'NO'}")
    print(f"\nEn ZDT1 la población converge al frente (distancia media ≤ {max(gds):.4f}) pero solo cubre entre el "
          f"{min(covers):.0%} y el {max(covers):.0%} del tramo f1 ∈ [0, 1]: el cruce convexo no extrapola y la "
          "mutación del 1 % no recupera los extremos. Para frentes de catálogo, que son discretos y pequeños, el "
          "paquete enumera (beam_selector, composite_optimizer) en vez de evolucionar.")


if __name__ == "__main__":
    main()
