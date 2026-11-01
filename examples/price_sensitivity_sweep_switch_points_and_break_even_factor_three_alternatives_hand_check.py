"""Sensibilidad de la alternativa más barata al precio del acero: puntos de cambio y precio de equilibrio.

Tres soluciones para la cubierta de una nave (pesos de un predimensionado; costes ilustrativos):
  · A: perfiles laminados, 18,0 t a 1300 USD/t, sin coste extra
  · B: vigas alveolares, 14,5 t a 1300 USD/t + 4800 USD de corte y soldadura
  · C: celosía, 12,0 t a 1300 USD/t + 8500 USD de taller y montaje adicional
`price_sensitivity.sensitivity_sweep` multiplica solo el precio del acero por un factor f ∈ [0,5; 2,0]
(el coste extra no escala) y devuelve la mejor por factor, los cambios y la elección «robusta» (la que
gana en más factores). `break_even_price` da el factor en que dos alternativas cuestan lo mismo:
  f* = (extra₂ − extra₁)/(m₁·p₁ − m₂·p₂), que el ejemplo calcula también a mano.

Ejecutar:  python examples/price_sensitivity_sweep_switch_points_and_break_even_factor_three_alternatives_hand_check.py
"""
from paretosteel.price_sensitivity import Candidate, break_even_price, evaluate_total_cost, sensitivity_sweep


def main() -> None:
    A = Candidate("A laminados", 18000.0, 1300.0, 0.0)
    B = Candidate("B alveolares", 14500.0, 1300.0, 4800.0)
    C = Candidate("C celosía", 12000.0, 1300.0, 8500.0)
    cands = [A, B, C]
    factors = [round(0.5 + 0.1 * i, 1) for i in range(16)]
    res = sensitivity_sweep(cands, factors)
    print(f"  {'f':>4} " + " ".join(f"{c.name:>13}" for c in cands) + "   más barata")
    for f, best in zip(res.price_factors, res.best_candidate_per_factor):
        print(f"  {f:4.1f} " + " ".join(f"{evaluate_total_cost(c, f):13.0f}" for c in cands) + f"   {best}")
    print(f"\nCambios de la más barata en f = {res.switch_points}; elección «robusta» (gana en más factores): "
          f"{res.robust_choice}")
    print("\nPrecios de equilibrio (factor sobre 1300 USD/t):")
    for c1, c2 in ((A, B), (B, C), (A, C)):
        f = break_even_price(c1, c2)
        hand = (c2.other_penalty - c1.other_penalty) / (c1.weight_kg / 1000 * c1.unit_cost_USD_per_ton
                                                         - c2.weight_kg / 1000 * c2.unit_cost_USD_per_ton)
        print(f"  {c1.name} = {c2.name}: f* = {f:.4f} (a mano {hand:.4f}) → {f * 1300:.0f} USD/t; "
              f"por encima gana la de menos acero")
    print("\nLa barrida es discreta (paso 0,1): los cambios se dan en el primer factor de la rejilla tras el equilibrio "
          "exacto, que es el que da break_even_price.")


if __name__ == "__main__":
    main()
