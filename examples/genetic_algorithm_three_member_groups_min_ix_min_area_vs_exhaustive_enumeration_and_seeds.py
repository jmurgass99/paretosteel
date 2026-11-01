"""Algoritmo genético por grupos de barras frente a la enumeración exhaustiva del catálogo.

Nave con tres grupos que reciben un perfil cada uno (requisitos de un predimensionado previo):
  · vigas IPE, 120 m en total, Ix ≥ 2,5e-4 m⁴
  · pilares HEB, 60 m, Ix ≥ 1,0e-4 m⁴ y A ≥ 80 cm²
  · arriostramientos HSS (base AISC v16), 80 m, A ≥ 20 cm²
`genetic.optimize` minimiza peso + penalización por déficit de Ix o A. Como los grupos son
independientes, el óptimo global es el perfil más ligero que cumple en cada grupo: se obtiene por
enumeración y sirve de oráculo. Se corre el GA con cinco semillas y se mide la distancia al óptimo.

El GA no comprueba ninguna norma: los mínimos de Ix y A los pone quien llama.

Ejecutar:  python examples/genetic_algorithm_three_member_groups_min_ix_min_area_vs_exhaustive_enumeration_and_seeds.py
"""
from paretosteel import ElementGroup, GAConfig, filter_profiles, optimize


def main() -> None:
    groups = [
        ElementGroup(name="vigas", length_total=120.0, min_Ix=2.5e-4, min_A=0.0, family_filter="IPE"),
        ElementGroup(name="pilares", length_total=60.0, min_Ix=1.0e-4, min_A=8.0e-3, family_filter="HEB"),
        ElementGroup(name="arriostramientos", length_total=80.0, min_Ix=0.0, min_A=2.0e-3, family_filter="HSS"),
    ]
    print("Óptimo por enumeración exhaustiva (perfil más ligero que cumple en cada grupo):")
    exact = {}
    w_exact = 0.0
    for g in groups:
        fam = filter_profiles(family=g.family_filter)
        ok = [p for p in fam if p.Ix >= g.min_Ix and p.A >= g.min_A]
        best = min(ok, key=lambda p: p.weight_per_m)
        exact[g.name] = best.designation
        w_exact += best.weight_per_m * g.length_total
        print(f"  {g.name:<17} {len(fam):4d} candidatos, {len(ok):4d} cumplen → {best.designation:<14} "
              f"{best.weight_per_m:6.1f} kg/m × {g.length_total:5.0f} m = {best.weight_per_m * g.length_total:7.0f} kg")
    print(f"  Peso mínimo: {w_exact:.0f} kg")

    print("\nGA (población 40, 40 generaciones) con cinco semillas:")
    print(f"  {'semilla':>7} {'peso [kg]':>10} {'vs óptimo':>10} {'penal.':>7}  asignación")
    hits = 0
    gaps = []
    per_group = {g.name: 0 for g in groups}
    for seed in (1, 2, 3, 4, 5):
        res = optimize(groups, config=GAConfig(population_size=40, n_generations=40, random_seed=seed))
        a = dict(res.best.assignment)
        gap = res.best.weight / w_exact - 1.0
        gaps.append(gap)
        hits += a == exact
        for k in per_group:
            per_group[k] += a[k] == exact[k]
        print(f"  {seed:7d} {res.best.weight:10.0f} {gap:+10.2%} {res.best.penalty:7.0f}  "
              + ", ".join(f"{k}={v}" for k, v in a.items()))
        hist = res.history
        assert all(hist[i + 1] <= hist[i] + 1e-9 for i in range(len(hist) - 1)), "el elitismo debería impedir empeorar"
    print(f"\nSemillas que dan el óptimo exacto: {hits} de 5; la peor queda a {max(gaps):+.2%}.")
    print("Aciertos por grupo: " + ", ".join(f"{k} {v}/5" for k, v in per_group.items())
          + f" (tamaño del catálogo: " + ", ".join(f"{g.family_filter} {len(filter_profiles(family=g.family_filter))}"
                                                   for g in groups) + ").")
    print("Para grupos independientes la enumeración es exacta y más barata; el GA solo compensa cuando el "
          "coste de un grupo depende de lo que se elige en los demás.")


if __name__ == "__main__":
    main()
