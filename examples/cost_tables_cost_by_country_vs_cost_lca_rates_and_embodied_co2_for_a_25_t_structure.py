"""Las dos tablas de precios del paquete, frente a frente, para una estructura de 25 t.

El paquete tiene dos fuentes de coste que NO coinciden:
  · `cost_by_country` (USD/t en bruto, fabricado y montado + kg CO₂/kg por país), que usa `boq`;
  · `cost_lca.COST_USD_PER_TON` (un único USD/t por país) y `EMBODIED_CO2_TON_PER_TON` por ruta de
    fabricación (alto horno, horno eléctrico, «bajo carbono»), que usan `pareto_lca` y `diff_evolution`.
El ejemplo evalúa 25 t con ambas, señala las discrepancias y muestra el peso de la ruta de fabricación
en el CO₂. Todos los valores son estimaciones ilustrativas del paquete (2024-2026), sin fuente
publicada en el código: no son precios de mercado ni EPD.

Ejecutar:  python examples/cost_tables_cost_by_country_vs_cost_lca_rates_and_embodied_co2_for_a_25_t_structure.py
"""
from paretosteel.cost_by_country import estimate_cost, get_cost, list_countries
from paretosteel.cost_lca import COST_USD_PER_TON, EMBODIED_CO2_TON_PER_TON, CostLCAInput, evaluate_cost_lca


def main() -> None:
    tons = 25.0
    print(f"Estructura de {tons:.0f} t: coste según las dos tablas del paquete [USD]")
    print(f"  {'país':<4} {'bruto':>8} {'fabricado':>10} {'montado':>9} | {'cost_lca':>9} {'cost_lca/bruto':>15}")
    gaps = []
    for iso in list_countries():
        c = get_cost(iso)
        raw, fab, ere = (estimate_cost(iso, tons, s) for s in ("raw", "fab", "erected"))
        lca = evaluate_cost_lca(CostLCAInput(weight_kg=tons * 1000, country=iso))["cost_USD"]
        in_lca = iso in COST_USD_PER_TON
        gaps.append((lca / raw - 1, iso))
        print(f"  {iso:<4} {raw:8.0f} {fab:10.0f} {ere:9.0f} | {lca:9.0f} {lca / raw - 1:+14.0%}"
              + ("" if in_lca else "  (sin fila: DEFAULT)"))
    worst = max(gaps, key=lambda g: abs(g[0]))
    print(f"  La mayor discrepancia entre «cost_lca» y el precio bruto de «cost_by_country» es {worst[1]} "
          f"({worst[0]:+.0%}). Un mismo proyecto da cifras distintas según el módulo que se use.")

    print(f"\nCO₂ incorporado de {tons:.0f} t por ruta de fabricación (cost_lca) y por país (cost_by_country):")
    for grade, f in sorted(EMBODIED_CO2_TON_PER_TON.items(), key=lambda kv: kv[1]):
        print(f"  {grade:<15} {f:4.2f} t CO₂/t → {tons * f:5.1f} t CO₂")
    rng = [get_cost(i).co2_kg_per_kg for i in list_countries()]
    hi, lo = max(EMBODIED_CO2_TON_PER_TON.values()), min(EMBODIED_CO2_TON_PER_TON.values())
    r_pais, r_ruta = max(rng) / min(rng), hi / lo
    print(f"  Por país el factor va de {min(rng):.2f} a {max(rng):.2f} (×{r_pais:.2f}); por ruta, de {lo:.2f} a {hi:.2f} "
          f"(×{r_ruta:.1f}). " + ("La ruta de fabricación mueve el CO₂ más que el país de compra."
                                  if r_ruta > r_pais else "El país pesa más que la ruta de fabricación."))


if __name__ == "__main__":
    main()
