"""Servicio de optimización de pilares a compresión centrada (AISC 360 §E3) para tres familias.

Pilar biarticulado de 4,0 m (K = 1) con P_u = 1500 kN, acero de 345 MPa. `services.optimize_column`
recorre cada familia de la base AISC v16 por peso creciente y devuelve el primer perfil con
KL/r_min ≤ 200 y φ·Fcr·Ag ≥ P_u, con
  Fe = π²E/(KL/r)²;  Fcr = 0,658^(Fy/Fe)·Fy si KL/r ≤ 4,71√(E/Fy), y 0,877·Fe en otro caso; φ = 0,90.
El ejemplo recalcula el perfil elegido a mano para W, HP y HSS, compara el peso de las tres
soluciones y repite con 9 m para ver el cambio de rama inelástica a elástica.

No comprueba pandeo local (secciones esbeltas, §E7) ni pandeo por torsión o flexotorsión (§E4). El
ejemplo calcula la esbeltez de pared de los HSS elegidos (t_diseño = 0,93·t_nominal) y la compara con
los límites de la Tabla B4.1a: b/t ≤ 1,40·√(E/Fy) en HSS rectangulares (con b = lado − 3t, §B4.1b) y
D/t ≤ 0,11·E/Fy en circulares (este último, sin contrastar en esta revisión).

Ejecutar:  python examples/aisc_e3_column_optimizer_w_hp_hss_families_4_m_1500_kn_fcr_hand_check_and_slenderness.py
"""
import math
from fractions import Fraction

from paretosteel.catalogs_aisc_full import load_aisc_v16
from paretosteel.services import ColumnOptimizationInput, optimize_column


def hand(p, L, Fy=345e6, E=200e9):
    r = math.sqrt(min(p.Ix, p.Iy) / p.A)
    klr = L / r
    Fe = math.pi ** 2 * E / klr ** 2
    lim = 4.71 * math.sqrt(E / Fy)
    Fcr = 0.658 ** (Fy / Fe) * Fy if klr <= lim else 0.877 * Fe
    return klr, Fe / 1e6, Fcr / 1e6, 0.9 * Fcr * p.A / 1e3, "inelástico" if klr <= lim else "elástico"


def hss_wall_slenderness(name, Fy=345.0, E=200000.0):
    """(λ, λr, tipo) de la pared de un HSS AISC a partir de su designación (in)."""
    parts = name[3:].split("X")
    to_in = lambda s: float(sum(Fraction(x) for x in s.split("-")))  # noqa: E731  "2-1/2" → 2,5
    t = 0.93 * to_in(parts[-1])
    if len(parts) == 3:  # rectangular B×H×t: pared mayor, b = H − 3t (§B4.1b(d))
        b = max(to_in(parts[0]), to_in(parts[1])) - 3.0 * t
        return b / t, 1.40 * math.sqrt(E / Fy), "b/t"
    return to_in(parts[0]) / t, 0.11 * E / Fy, "D/t"


def main() -> None:
    cat = load_aisc_v16()
    print(f"Límite inelástico/elástico 4,71·√(E/Fy) = {4.71 * math.sqrt(200000 / 345):.1f}")
    totals = {}
    slender = False
    for L, P in ((4.0, 1500.0), (9.0, 1500.0)):
        print(f"\nL = {L} m, P_u = {P} kN")
        print(f"  {'familia':<7} {'perfil':<16} {'kg/m':>6} {'KL/r':>6} {'Fe':>7} {'Fcr':>6} {'φPn':>7} {'a mano':>7} {'rama':<10}")
        sols = []
        for fam in ("W", "HP", "HSS"):
            r = optimize_column(ColumnOptimizationInput(L_m=L, P_Ed_kN=P, section_family=fam, max_weight_kg_m=400.0))
            if not r.is_feasible:
                print(f"  {fam:<7} ninguno ≤ 400 kg/m")
                continue
            p = cat[r.best_section]
            klr, Fe, Fcr, phiPn, rama = hand(p, L)
            sols.append((r.weight_kg_m, fam, r.best_section))
            print(f"  {fam:<7} {r.best_section:<16} {r.weight_kg_m:6.1f} {klr:6.1f} {Fe:7.1f} {Fcr:6.1f} "
                  f"{r.P_capacity_kN:7.1f} {phiPn:7.1f} {rama:<10}")
        best = min(sols)
        w_w = next(s[0] for s in sols if s[1] == "W")
        print(f"  Más ligero: {best[2]} ({best[1]}, {best[0]:.1f} kg/m); el W elegido pesa "
              f"{w_w / best[0] - 1:+.0%} respecto a él.")
        hss = next((s[2] for s in sols if s[1] == "HSS"), None)
        if hss:
            lam, lam_r, kind = hss_wall_slenderness(hss)
            verdict = ("pared ESBELTA: §E7 reduciría φPn y el servicio no lo comprueba" if lam > lam_r
                       else "pared no esbelta")
            note = " (límite D/t sin contrastar)" if kind == "D/t" else ""
            print(f"  {hss}: {kind} = {lam:.1f} frente a λr = {lam_r:.1f}{note} → {verdict}")
            slender = slender or lam > lam_r
        totals[L] = {s[1]: s[0] for s in sols}
    heavier = all(totals[9.0][f] > totals[4.0][f] for f in totals[4.0])
    print("\nA 9 m " + ("todas las familias necesitan un perfil más pesado que a 4 m" if heavier
                        else "alguna familia mantiene el peso") + ". El HSS tiene el mismo radio de giro en los "
          "dos ejes y por eso gana en compresión centrada"
          + (", pero los HSS elegidos por peso son de pared esbelta: sin la comprobación de §E7 esa ventaja "
             "no está demostrada." if slender else "."))


if __name__ == "__main__":
    main()
