"""«Frente de Pareto» coste–CO₂ de `pareto_lca` con NSGA-II: por qué sale un único punto.

Dos grupos: vigas IPE (120 m, Ix ≥ 25 000 cm⁴) compradas en Chile con acero de alto horno, y pilares
HEB (60 m, Ix ≥ 10 000 cm⁴, A ≥ 80 cm²) comprados en China con acero de horno eléctrico.
`run_pareto_lca_optimizer` busca con NSGA-II el frente entre coste total y CO₂ total.

La variable de decisión es solo el perfil de cada grupo; el país y la ruta de fabricación son datos.
Entonces coste = Σ m_i·p_i y CO₂ = Σ m_i·e_i con p_i, e_i > 0 fijos: los dos objetivos crecen con la
masa de cada grupo y el perfil más ligero que cumple en cada grupo minimiza los dos a la vez. El frente
es un punto. El ejemplo lo comprueba enumerando las 35 combinaciones posibles.

Atención a las unidades: aquí min_Ix y min_A van en cm⁴ y cm² (en `genetic.ElementGroup`, en m⁴ y m²).

Ejecutar:  python examples/pareto_cost_vs_co2_nsga2_two_groups_collapses_to_minimum_weight_brute_force_proof.py
"""
from itertools import product

from paretosteel.catalogs import filter_profiles
from paretosteel.cost_lca import COST_USD_PER_TON, EMBODIED_CO2_TON_PER_TON
from paretosteel.pareto_lca import ParetoGroupSpec, ParetoOptimizeInput, run_pareto_lca_optimizer


def main() -> None:
    groups = [
        ParetoGroupSpec(name="vigas", length_total=120.0, min_Ix=25000.0, family_filter="IPE",
                        country="CL", steel_grade="primary_BF"),
        ParetoGroupSpec(name="pilares", length_total=60.0, min_Ix=10000.0, min_A=80.0, family_filter="HEB",
                        country="CN", steel_grade="secondary_EAF"),
    ]
    out = run_pareto_lca_optimizer(ParetoOptimizeInput(groups=groups, population_size=40, n_generations=30,
                                                       random_seed=42))
    print(f"NSGA-II (40 × 30): {out.n_solutions} solución(es) en el frente")
    for s in out.solutions:
        print(f"  {s.assignment}  {s.total_weight_kg:7.0f} kg  {s.total_cost_USD:8.0f} USD  "
              f"{s.total_co2_tCO2:6.2f} t CO₂  factible={s.feasible}")

    fams = [sorted(filter_profiles(family=g.family_filter), key=lambda p: p.weight_per_m) for g in groups]
    rows = []
    for combo in product(*fams):
        cost = co2 = mass = 0.0
        ok = True
        for g, p in zip(groups, combo):
            m = p.weight_per_m * g.length_total / 1000.0
            mass += m
            cost += m * COST_USD_PER_TON[g.country]
            co2 += m * EMBODIED_CO2_TON_PER_TON[g.steel_grade]
            ok &= p.Ix * 1e8 >= g.min_Ix and p.A * 1e4 >= g.min_A
        rows.append((cost, co2, mass, ok, tuple(p.designation for p in combo)))
    feas = [r for r in rows if r[3]]
    front = [r for r in feas if not any(o[0] <= r[0] and o[1] <= r[1] and (o[0] < r[0] or o[1] < r[1]) for o in feas)]
    print(f"\nEnumeración: {len(rows)} combinaciones, {len(feas)} factibles, {len(front)} no dominada(s):")
    for r in front:
        print(f"  {r[4]}  {r[2] * 1000:7.0f} kg  {r[0]:8.0f} USD  {r[1]:6.2f} t CO₂")
    lightest = min(feas, key=lambda r: r[2])
    same = len(front) == 1 and front[0][4] == lightest[4] == tuple(out.solutions[0].assignment.values())
    print(f"  La combinación más ligera factible es {lightest[4]}; NSGA-II, enumeración y mínimo peso "
          f"{'coinciden' if same else 'NO coinciden'}.")
    alt = sorted(feas, key=lambda r: r[2])[1]
    both = alt[0] > lightest[0] and alt[1] > lightest[1]
    print(f"  La siguiente más ligera {alt[4]} cuesta {alt[0] - lightest[0]:+.0f} USD y emite {alt[1] - lightest[1]:+.2f} t CO₂"
          + (": empeora las dos cosas a la vez." if both else "."))
    print("\nPara que haya compromiso coste–CO₂ la decisión tiene que incluir la procedencia o la ruta de "
          "fabricación de cada grupo (p. ej. EAF más caro pero con menos CO₂); `pareto_lca` no la incluye.")


if __name__ == "__main__":
    main()
