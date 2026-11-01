"""Barrido de pesos α de `diff_evolution.pareto_weight_cost`: once ejecuciones de DE, un único punto.

Viga biapoyada de 8 m con w = 20 kN/m, familias IPE y W. `pareto_weight_cost` minimiza
α·peso_normalizado + (1 − α)·coste_normalizado con DE para α = 0, 0,1, …, 1 y filtra los no dominados.
Pero el coste es peso × tarifa del país (`cost_lca.COST_USD_PER_TON`), así que los dos objetivos
normalizados son la misma función y todas las α dan el mismo perfil, el que la DE encuentra al
minimizar el peso.
El ejemplo lo comprueba contra la búsqueda exhaustiva y contra `optimize_beam_de`, y de paso muestra
que la evolución diferencial sobre el índice del catálogo no garantiza el óptimo: ordenados por peso,
los perfiles no tienen capacidad monótona y la búsqueda puede quedarse en uno más pesado.

Ejecutar:  python examples/pareto_weight_cost_de_alpha_sweep_single_point_front_because_cost_is_weight_times_rate.py
"""
from paretosteel.catalogs import filter_profiles
from paretosteel.cost_lca import COST_USD_PER_TON
from paretosteel.diff_evolution import optimize_beam_de, pareto_weight_cost

FY, E = 345e6, 200e9


def feasible(p, L, w):
    Sx = p.Ix / (p.d / 2.0)
    d = 5.0 * w * 1e3 * L ** 4 / (384.0 * E * p.Ix) * 1e3
    return (0.9 * FY * Sx / 1e3 >= w * L ** 2 / 8 and 0.9 * 0.6 * FY * p.A * 0.5 / 1e3 >= w * L / 2
            and d <= L * 1e3 / 360.0)


def main() -> None:
    L, w = 8.0, 20.0
    for fam, country in (("IPE", "ES"), ("W", "US")):
        pr = pareto_weight_cost(span_m=L, w_kN_m=w, family=fam, country=country, n_alphas=11, seed=42)
        rate = COST_USD_PER_TON[country]
        ex = min((p for p in filter_profiles(family=fam) if p.d > 0 and p.Ix > 0 and feasible(p, L, w)),
                 key=lambda p: p.weight_per_m)
        de = optimize_beam_de(span_m=L, w_kN_m=w, family=fam, seed=42)
        print(f"{fam} en {country} ({rate:.0f} USD/t): {len(pr.all_solutions)} solución(es) distinta(s) en 11 valores de α; "
              f"frente = " + ", ".join(f"{c.label} ({c.weight_kg:.0f} kg, {c.cost_USD:.0f} USD)" for c in pr.front))
        for c in pr.front:
            print(f"  coste/peso = {c.cost_USD / c.weight_kg * 1000:.0f} USD/t, la tarifa del país ({rate:.0f}): "
                  "el coste no aporta información nueva")
        agree = pr.front[0].label == ex.designation == de.section
        print(f"  Exhaustiva: {ex.designation} ({ex.weight_per_m:.1f} kg/m); optimize_beam_de: {de.section} "
              f"({de.weight_kg_m:.1f} kg/m) → " + ("los tres coinciden." if agree else
              f"la DE se queda {de.weight_kg_m / ex.weight_per_m - 1:+.1%} por encima del óptimo exhaustivo."))
    print("\nUn frente peso–coste solo tiene sentido si el coste por kg cambia entre alternativas (grado, "
          "fabricación, conexiones), como en el ejemplo pareto_front_weight_vs_cost_*.")


if __name__ == "__main__":
    main()
