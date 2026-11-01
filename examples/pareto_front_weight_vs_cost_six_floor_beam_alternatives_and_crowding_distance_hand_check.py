"""Frente de Pareto peso–coste de seis alternativas de viga de forjado y distancia de apiñamiento.

Viga de 9 m. Las alternativas difieren en perfil, grado y fabricación, así que el coste NO es
proporcional al peso (si lo fuera, el frente tendría un único punto):
  coste = masa·precio del grado + fabricación (soldadura de cartelas, alveolado, etc.)
Precios supuestos para el ejemplo: S275 1,10 USD/kg, S355 1,18 USD/kg, S460 1,40 USD/kg; perfil
armado +0,55 USD/kg de taller; viga alveolar +0,75 USD/kg de corte y soldadura. Las seis se suponen
válidas para la misma solicitación: aquí no se comprueba su resistencia, solo se ordenan.

`pareto.pareto_front` extrae los no dominados (peso y coste a minimizar) y `pareto.crowding_distance`
la distancia de apiñamiento de NSGA-II. Ambos se contrastan con una comprobación por fuerza bruta y
con la distancia calculada a mano para el punto interior.

Ejecutar:  python examples/pareto_front_weight_vs_cost_six_floor_beam_alternatives_and_crowding_distance_hand_check.py
"""
from paretosteel.pareto import Candidate, crowding_distance, pareto_front


def main() -> None:
    L = 9.0
    alts = [  # etiqueta, kg/m, USD/kg de material, USD/kg de taller
        ("IPE450 S275", 77.6, 1.10, 0.00),
        ("IPE400 S355", 66.3, 1.18, 0.00),
        ("IPE360 S460", 57.1, 1.40, 0.00),
        ("HEA360 S275", 112.0, 1.10, 0.00),
        ("armada 500x200 S355", 61.0, 1.18, 0.55),
        ("alveolar ex-IPE300 S355", 42.2, 1.18, 0.75),
    ]
    cands = [Candidate(lbl, w * L, w * L * (pm + pf)) for lbl, w, pm, pf in alts]
    print(f"Alternativas para una viga de {L:.0f} m:")
    for c in cands:
        print(f"  {c.label:<24} {c.weight_kg:6.1f} kg  {c.cost_USD:6.0f} USD  ({c.cost_USD / c.weight_kg:.2f} USD/kg)")

    front = pareto_front(cands)
    brute = [c for c in cands if not any(o.weight_kg <= c.weight_kg and o.cost_USD <= c.cost_USD
                                         and (o.weight_kg < c.weight_kg or o.cost_USD < c.cost_USD)
                                         for o in cands if o is not c)]
    assert {c.label for c in front} == {c.label for c in brute}
    print(f"\nFrente de Pareto ({len(front)} de {len(cands)}, coincide con la fuerza bruta), ordenado por peso:")
    for c in front:
        print(f"  {c.label:<24} {c.weight_kg:6.1f} kg  {c.cost_USD:6.0f} USD")
    out = [c.label for c in cands if c not in front]
    print("Dominadas: " + "; ".join(
        f"{lbl} (por {next(o.label for o in front if o.weight_kg <= x.weight_kg and o.cost_USD <= x.cost_USD)})"
        for lbl in out for x in cands if x.label == lbl))

    cd = crowding_distance(front)
    print("\nDistancia de apiñamiento del frente: " + ", ".join(
        f"{c.label.split()[0]} {'∞' if d == float('inf') else f'{d:.3f}'}" for c, d in zip(front, cd)))
    if len(front) >= 3:
        i = 1
        w = [c.weight_kg for c in front]
        k = [c.cost_USD for c in front]
        by_cost = sorted(range(len(front)), key=lambda j: k[j])
        pos = by_cost.index(i)
        hand = ((w[i + 1] - w[i - 1]) / (max(w) - min(w))
                + (k[by_cost[pos + 1]] - k[by_cost[pos - 1]]) / (max(k) - min(k)))
        print(f"  A mano para {front[i].label}: Δpeso/rango + Δcoste/rango = {hand:.3f} (función {cd[i]:.3f}); "
              "los extremos llevan ∞ para que el frente conserve su amplitud.")
    cheapest = min(front, key=lambda c: c.cost_USD)
    lightest = min(front, key=lambda c: c.weight_kg)
    print(f"\nLa más ligera ({lightest.label}, {lightest.weight_kg:.0f} kg) cuesta "
          f"{lightest.cost_USD / cheapest.cost_USD - 1:+.0%} más que la más barata ({cheapest.label}, "
          f"{cheapest.weight_kg:.0f} kg): esa es la decisión que el frente deja al proyectista.")


if __name__ == "__main__":
    main()
