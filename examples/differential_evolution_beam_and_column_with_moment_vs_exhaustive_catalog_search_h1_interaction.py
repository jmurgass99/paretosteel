"""Evolución diferencial (SciPy) sobre el índice del catálogo frente a la búsqueda exhaustiva.

`diff_evolution.optimize_beam_de` y `optimize_column_de` usan `scipy.optimize.differential_evolution`
con una variable entera (posición en el catálogo ordenado por peso) y penalizan las restricciones:
  · viga biapoyada: M = wL²/8 ≤ φ·Fy·Sx, V = wL/2 ≤ φ·0,6·Fy·(A/2), δ = 5wL⁴/384EI ≤ L/360
    (la misma w para resistencia y flecha; el alma se aproxima por A/2 porque SteelProfile no tiene tw)
  · pilar: AISC E3 con r_min y KL/r ≤ 200; con momento, interacción H1-1a/H1-1b con φMn = φ·Fy·Sx.
El ejemplo repite esas comprobaciones en una búsqueda exhaustiva escrita aquí (oráculo) y compara.
En la 1.1.0 el resultado del pilar publica `interaction_ratio` y la factibilidad la decide la
interacción (antes solo el axil).

Ejecutar:  python examples/differential_evolution_beam_and_column_with_moment_vs_exhaustive_catalog_search_h1_interaction.py
"""
import math

from paretosteel.catalogs import filter_profiles
from paretosteel.diff_evolution import optimize_beam_de, optimize_column_de

FY, E = 345e6, 200e9


def beam_ok(p, L, w):
    Sx = p.Ix / (p.d / 2.0)
    M, V = w * L ** 2 / 8.0, w * L / 2.0
    d = 5.0 * w * 1e3 * L ** 4 / (384.0 * E * p.Ix) * 1e3
    return 0.9 * FY * Sx / 1e3 >= M and 0.9 * 0.6 * FY * p.A * 0.5 / 1e3 >= V and d <= L * 1e3 / 360.0


def column_ratio(p, H, P, M):
    r = math.sqrt(min(p.Ix, p.Iy) / p.A)
    klr = H / r
    if klr > 200:
        return float("inf")
    Fe = math.pi ** 2 * E / klr ** 2
    Fcr = 0.658 ** (FY / Fe) * FY if klr <= 4.71 * math.sqrt(E / FY) else 0.877 * Fe
    phiPn = 0.9 * Fcr * p.A / 1e3
    phiMn = 0.9 * FY * p.Ix / (p.d / 2.0) / 1e3
    rp, rm = P / phiPn, M / phiMn
    return rp + 8.0 / 9.0 * rm if rp >= 0.2 else rp / 2.0 + rm


def main() -> None:
    print("Viga biapoyada (familias IPE y W), L = 8 m, w = 25 kN/m")
    for fam in ("IPE", "W"):
        de = optimize_beam_de(span_m=8.0, w_kN_m=25.0, family=fam, seed=42)
        cands = [p for p in filter_profiles(family=fam) if p.d > 0 and p.Ix > 0]
        ex = min((p for p in cands if beam_ok(p, 8.0, 25.0)), key=lambda p: p.weight_per_m)
        print(f"  {fam:<3} DE: {de.section:<8} {de.weight_kg_m:6.1f} kg/m  M {de.utilization_M:.3f}  V {de.utilization_V:.3f}  "
              f"δ {de.deflection_mm:5.1f}/{de.deflection_limit_mm:.1f} mm | exhaustiva: {ex.designation:<8} "
              f"{'= DE' if ex.designation == de.section else 'DISTINTO'} ({len(cands)} perfiles)")

    print("\nPilar W, H = 4 m, K = 1, P = 900 kN")
    pesos = []
    for M in (0.0, 60.0, 150.0):
        de = optimize_column_de(height_m=4.0, axial_kN=900.0, moment_kNm=M, family="W", seed=42)
        cands = [p for p in filter_profiles(family="W") if p.Iy > 0 and p.A > 0 and p.d > 0]
        ok = [p for p in cands if column_ratio(p, 4.0, 900.0, M) <= 1.0]
        ex = min(ok, key=lambda p: p.weight_per_m)
        ic = "—" if de.interaction_ratio is None else f"{de.interaction_ratio:.3f}"
        pesos.append(de.weight_kg_m)
        print(f"  M = {M:5.1f} kN·m  DE: {de.section:<8} {de.weight_kg_m:6.1f} kg/m  P/φPn {de.utilization_P:.3f}  "
              f"H1 {ic:>5}  factible {de.feasible} | exhaustiva: {ex.designation:<8} "
              f"{'= DE' if ex.designation == de.section else 'DISTINTO'} (H1 a mano {column_ratio(ex, 4.0, 900.0, M):.3f})")
    sube = all(pesos[i + 1] > pesos[i] for i in range(len(pesos) - 1))
    print(f"\nPeso del pilar con M = 0, 60 y 150 kN·m: {pesos[0]:.1f}, {pesos[1]:.1f} y {pesos[2]:.1f} kg/m"
          + (" (crece con el momento: gobierna la interacción H1)." if sube else ".")
          + " φMn usa Sx (elástico) y no considera pandeo lateral: resultado de predimensionado.")


if __name__ == "__main__":
    main()
