"""Reutilización de perfiles recuperados: emparejamiento voraz demanda–inventario y CO₂ evitado.

Una ampliación necesita seis vigas, cada una con un módulo plástico mínimo Wpl (cm³) de su
predimensionado. Un desguace ofrece siete perfiles usados con su Wpl (EN 10365) y el CO₂ que se
evita al reutilizarlos en lugar de comprar acero nuevo (masa × 1,85 t CO₂/t, media mundial de
`cost_lca`, ilustrativa). `reuse.match_reuse` recorre la demanda en orden y asigna a cada una el
perfil disponible con la MENOR capacidad suficiente (mejor ajuste), sin repetir.

El ejemplo comprueba el resultado con un emparejamiento exhaustivo (todas las permutaciones) que
maximiza el número de demandas cubiertas: el voraz en orden de llegada no es óptimo en general.

Ejecutar:  python examples/circular_steel_reuse_greedy_best_fit_matching_inventory_reuse_ratio_and_carbon_saved.py
"""
from itertools import permutations

from paretosteel.reuse import DemandItem, InventoryItem, match_reuse


def main() -> None:
    inv_data = [("IPE300-usado", 628, 42.2, 6.0), ("IPE330-usado", 804, 49.1, 7.5), ("IPE400-usado", 1307, 66.3, 8.0),
                ("HEB240-usado", 1053, 83.2, 6.0), ("IPE270-usado", 484, 36.1, 5.0), ("HEA300-usado", 1383, 88.3, 7.0),
                ("IPE240-usado", 367, 30.7, 6.0)]
    inventory = [InventoryItem(n, wpl, embodied_carbon_saved=m * L / 1000 * 1.85) for n, wpl, m, L in inv_data]
    demands = [DemandItem("V1", 600), DemandItem("V2", 450), DemandItem("V3", 1250),
               DemandItem("V4", 800), DemandItem("V5", 1000), DemandItem("V6", 1500)]
    res = match_reuse(demands, inventory)
    print(f"  {'demanda':<7} {'Wpl req.':>8} → {'perfil':<14} {'Wpl':>6} {'holgura':>8} {'t CO₂':>6}")
    for a in res.assignments:
        if a.matched:
            print(f"  {a.demand_id:<7} {a.required:8.0f} → {a.inventory_id:<14} {a.capacity:6.0f} "
                  f"{a.capacity / a.required - 1:+8.0%} {a.embodied_carbon_saved:6.2f}")
        else:
            print(f"  {a.demand_id:<7} {a.required:8.0f} → sin perfil adecuado")
    print(f"\nCubiertas {res.matched_demands}/{len(demands)}; ratio de reutilización (por Wpl requerido) "
          f"{res.reuse_ratio:.1%}; CO₂ evitado {res.total_embodied_carbon_saved:.2f} t")

    best = 0
    for perm in permutations(range(len(inventory)), len(demands)):
        best = max(best, sum(inventory[j].capacity >= d.required for d, j in zip(demands, perm)))
    print(f"Exhaustivo: como máximo se pueden cubrir {best} demandas; el voraz cubre {res.matched_demands} "
          + ("(óptimo en este caso)." if best == res.matched_demands else "(subóptimo: el orden de la demanda importa)."))
    print("Wpl suficiente no basta para reutilizar: hay que comprobar longitud, estado, grado del acero y "
          "uniones; el módulo solo empareja una capacidad escalar.")


if __name__ == "__main__":
    main()
