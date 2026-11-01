"""Medición (BoQ) de la estructura metálica de una nave de dos plantas: toneladas, coste y CO₂ por país.

Dos pórticos de tres vanos de 6 m y dos plantas de 3,5 m, unidos por vigas de atado:
  · pilares HEB240: 2 pórticos × 4 pilares × 7,0 m = 56 m
  · vigas de pórtico IPE360: 2 pórticos × 2 plantas × 3 vanos × 6,0 m = 72 m
  · vigas de atado IPE240: 4 líneas × 2 plantas × 5,0 m = 40 m
  · arriostramiento W8X31 (base AISC): 4 diagonales × √(6² + 3,5²) m

`calculate_steel_boq` toma el área tabulada (EN 10365 para los EN, AISC v16 para los W), masa
= A·7850 kg/m³ para los perfiles del catálogo unificado y la masa nominal AISC para los W que solo están
en la base AISC. Coste = toneladas × tarifa del país (`cost_by_country`, montado) y CO₂ con el factor
del país. El ejemplo recalcula a mano las toneladas y compara cuatro países.

Las tarifas y factores de CO₂ de `cost_by_country` son estimaciones ilustrativas del paquete, sin
fuente publicada: sirven para comparar alternativas, no para presupuestar.

Ejecutar:  python examples/steel_boq_two_storey_frame_ipe_heb_w_tonnage_cost_and_co2_by_country_hand_check.py
"""
import math

from paretosteel.boq import SteelBoQItem, calculate_steel_boq
from paretosteel.catalog_unified import all_sections
from paretosteel.catalogs import all_profiles


def main() -> None:
    diag = math.hypot(6.0, 3.5)
    items = [
        SteelBoQItem("HEB240", 2 * 4 * 7.0),
        SteelBoQItem("IPE360", 2 * 2 * 3 * 6.0),
        SteelBoQItem("IPE 240", 4 * 2 * 5.0),
        SteelBoQItem("W8X31", 4 * diag),
    ]
    rep = calculate_steel_boq(items, country_iso="ES", stage="erected")
    print(f"Medición — {rep.country_name}, fase '{rep.stage}', tarifa {rep.rate_USD_per_ton:.0f} USD/t, "
          f"{rep.co2_intensity_kg_per_kg} kg CO₂/kg")
    print(f"  {'perfil':<8} {'L [m]':>7} {'A [cm²]':>8} {'kg/m':>7} {'t':>7} {'USD':>9} {'t CO₂':>7}")
    for it in rep.items:
        print(f"  {it.profile_name:<8} {it.total_length_m:7.2f} {it.tabulated_area_cm2:8.2f} "
              f"{it.weight_per_m_kg:7.2f} {it.total_tonnage:7.3f} {it.cost_USD:9.0f} {it.co2_emissions_kg / 1000:7.2f}")
    print(f"  {'TOTAL':<8} {rep.total_length_m:7.2f} {'':>8} {'':>7} {rep.total_tonnage:7.3f} "
          f"{rep.total_cost_USD:9.0f} {rep.total_co2_kg / 1000:7.2f}")

    # Comprobación a mano de las toneladas
    unified = {s.name: s for s in all_sections()}
    aisc = {p.designation: p for p in all_profiles()}
    t_hand = 0.0
    for it in items:
        key = it.profile_name.replace(" ", "").upper()
        if key in unified:
            t_hand += it.total_length_m * unified[key].A_cm2 * 1e-4 * 7850.0 / 1000.0
        else:
            t_hand += it.total_length_m * aisc[key].weight_per_m / 1000.0
    print(f"\nA mano: Σ L·A·7850 (EN) + Σ L·masa AISC (W) = {t_hand:.4f} t; función: {rep.total_tonnage:.4f} t "
          f"({rep.total_tonnage / t_hand - 1:+.2e})")

    print("\nMisma medición en cuatro países (fase montado):")
    res = []
    for iso in ("ES", "DE", "US", "CL"):
        r = calculate_steel_boq(items, country_iso=iso)
        res.append((r.total_cost_USD, iso, r))
        print(f"  {iso} {r.country_name:<9} {r.rate_USD_per_ton:6.0f} USD/t → {r.total_cost_USD:9.0f} USD, "
              f"{r.total_co2_kg / 1000:6.2f} t CO₂")
    lo, hi = min(res), max(res)
    print(f"  Las toneladas no cambian ({rep.total_tonnage:.3f} t); el coste va de {lo[0]:.0f} ({lo[1]}) a "
          f"{hi[0]:.0f} USD ({hi[1]}), {hi[0] / lo[0] - 1:+.0%}, solo por la tarifa.")
    st = {s: calculate_steel_boq(items, "ES", stage=s).total_cost_USD for s in ("raw", "fab", "erected")}
    print(f"  España por fase: materia prima {st['raw']:.0f}, fabricado {st['fab']:.0f}, montado {st['erected']:.0f} USD.")


if __name__ == "__main__":
    main()
