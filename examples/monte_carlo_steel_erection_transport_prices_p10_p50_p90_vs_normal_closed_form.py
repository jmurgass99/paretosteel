"""Monte Carlo de precio unitario (acero + montaje + transporte) para 120 t: P10, P50, P90 frente a la forma cerrada.

`price_sensitivity_v2.monte_carlo` muestrea tres precios por tonelada con variación normal relativa
independiente (σ = 15 %, 10 % y 25 %) y devuelve P10, P50, P90 y la media del coste total. Como la suma
de normales independientes es normal, el resultado exacto es
  μ = T·(s + e + t);  σ = T·√((0,15·s)² + (0,10·e)² + (0,25·t)²);  P10/P90 = μ ∓ 1,2816·σ.
El ejemplo compara ambos con 1 000 y 20 000 muestras y con varias semillas.

Base: 120 t, acero 1100 USD/t, montaje 900 USD/t, transporte 120 USD/t (valores ilustrativos).

Ejecutar:  python examples/monte_carlo_steel_erection_transport_prices_p10_p50_p90_vs_normal_closed_form.py
"""
import math
from statistics import NormalDist

from paretosteel.price_sensitivity_v2 import PriceSensitivityV2Input, monte_carlo


def main() -> None:
    T, s, e, t = 120.0, 1100.0, 900.0, 120.0
    mu = T * (s + e + t)
    sig = T * math.sqrt((0.15 * s) ** 2 + (0.10 * e) ** 2 + (0.25 * t) ** 2)
    z = NormalDist().inv_cdf(0.90)
    print(f"Forma cerrada: μ = {mu:,.0f} USD, σ = {sig:,.0f} USD ({sig / mu:.1%}), z90 = {z:.4f}")
    print(f"  P10 = {mu - z * sig:,.0f}   P50 = {mu:,.0f}   P90 = {mu + z * sig:,.0f}")
    print(f"\n  {'n':>6} {'semilla':>7} {'P10':>10} {'P50':>10} {'P90':>10} {'media':>10} {'err P90':>8}")
    errs = {}
    for n in (1000, 20000):
        for seed in (42, 7, 2026):
            r = monte_carlo(PriceSensitivityV2Input(T, s, e, t, n_samples=n, seed=seed))
            err = r.P90_usd / (mu + z * sig) - 1
            errs.setdefault(n, []).append(abs(err))
            print(f"  {n:6d} {seed:7d} {r.P10_usd:10,.0f} {r.P50_usd:10,.0f} {r.P90_usd:10,.0f} {r.mean_usd:10,.0f} {err:+8.2%}")
    var = {"acero": (0.15 * s) ** 2, "montaje": (0.10 * e) ** 2, "transporte": (0.25 * t) ** 2}
    top = max(var, key=var.get)
    share = var[top] / sum(var.values())
    print(f"\nError máximo en P90: {max(errs[1000]):.2%} con 1 000 muestras y {max(errs[20000]):.2%} con 20 000. "
          f"De la dispersión (P90 − P10 = {2 * z * sig:,.0f} USD) el {top} aporta el {share:.0%} de la varianza.")
    print("El modelo no limita los precios a valores positivos ni correlaciona acero y montaje; con σ grandes "
          "conviene una distribución acotada.")


if __name__ == "__main__":
    main()
