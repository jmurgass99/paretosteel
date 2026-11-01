"""Sección armada en I de S460 de clase 3: módulo elastoplástico W_ep (EC3 de segunda generación) frente a W_el.

Viga armada 300×15 + 600×8 (alas y alma), soldaduras de garganta a = 5 mm, S460 (ε = √(235/460)).
`ec3_2022_2g.verify_member_ec3_2022` clasifica con los límites c/t de la Tabla 5.2 (ala: 9/10/14·ε,
alma: 72/83/124·ε) y, en clase 3, interpola linealmente W entre W_pl (límite de clase 2) y W_el (límite
de clase 3) según la esbeltez más desfavorable, en lugar de saltar a W_el como EN 1993-1-1:2005.
La interpolación es la del paquete; su correspondencia con la cláusula exacta de EN 1993-1-1:2022 queda
sin contrastar. W_pl, W_el, c/t y la interpolación se recalculan a mano.

También compara χ con la curva por defecto «a0» (la más favorable) y con la curva c que la Tabla 6.2
de EN 1993-1-1 asigna a una sección en I soldada con tf ≤ 40 mm pandeando alrededor de z–z, para un
axil de 1500 kN y 5 m de longitud de pandeo en el eje débil. La utilización que da el módulo es la
suma lineal M/M_Rd + N/N_b,Rd, no las fórmulas de interacción de §6.3.3.

Ejecutar:  python examples/ec3_2022_semi_compact_welded_i_section_s460_w_ep_interpolation_vs_w_el_and_buckling_curve_choice.py
"""
import math

from paretosteel.ec3_2022_2g import Ec3SemiCompactInput, compute_epsilon_ec3_2022, verify_member_ec3_2022


def main() -> None:
    b, tf, hw, tw, a, fy = 300.0, 15.0, 600.0, 8.0, 5.0, 460.0
    h = hw + 2 * tf
    A = 2 * b * tf + hw * tw
    I = 2 * (b * tf ** 3 / 12 + b * tf * ((h - tf) / 2) ** 2) + tw * hw ** 3 / 12
    Wel = I / (h / 2)
    Wpl = 2 * b * tf * (h - tf) / 2 + tw * hw ** 2 / 4
    c_f = (b - tw) / 2 - math.sqrt(2) * a
    c_w = hw - 2 * math.sqrt(2) * a
    eps = compute_epsilon_ec3_2022(fy)
    print(f"Sección {b:.0f}×{tf:.0f} + {hw:.0f}×{tw:.0f}, S460: ε = {eps:.4f}; A = {A:.0f} mm², "
          f"W_el = {Wel / 1e3:.1f}·10³ mm³, W_pl = {Wpl / 1e3:.1f}·10³ mm³ (W_pl/W_el = {Wpl / Wel:.3f})")
    print(f"  ala: c/t = {c_f:.1f}/{tf:.0f} = {c_f / tf:.2f} → {c_f / tf / eps:.2f}·ε (clase 2 ≤ 10, clase 3 ≤ 14)")
    print(f"  alma: c/t = {c_w:.1f}/{tw:.0f} = {c_w / tw:.2f} → {c_w / tw / eps:.2f}·ε (clase 2 ≤ 83, clase 3 ≤ 124)")
    xi = min(max((c_f / tf / eps - 10) / 4, (c_w / tw / eps - 83) / 41, 0.0), 1.0)
    W_ep = Wpl - xi * (Wpl - Wel)
    print(f"  ξ = max({(c_f / tf / eps - 10) / 4:.3f}, {(c_w / tw / eps - 83) / 41:.3f}) = {xi:.3f} → "
          f"W_ep = W_pl − ξ·(W_pl − W_el) = {W_ep / 1e3:.1f}·10³ mm³")

    Iz = 2 * tf * b ** 3 / 12 + hw * tw ** 3 / 12
    Lcr, N = 5000.0, 1500.0
    Ncr = math.pi ** 2 * 210000 * Iz / Lcr ** 2 / 1e3
    base = dict(c_flange=c_f, t_flange=tf, c_web=c_w, t_web=tw, w_pl=Wpl, w_el=Wel, area=A, fy=fy,
                m_ed=900.0, n_ed=N, n_cr=Ncr)
    print(f"\nN_cr,z = π²·E·Iz/L² = {Ncr:.0f} kN con Iz = {Iz / 1e6:.2f}·10⁶ mm⁴; N_Ed = {N:.0f} kN, M_Ed = 900 kN·m")
    print(f"  {'curva':<6} {'clase':>5} {'M_Rd 2022':>9} {'M_Rd 2005':>9} {'ganancia':>8} {'χ':>6} {'N_b,Rd':>7} {'utiliz.':>7}")
    res = {}
    for curve in ("a0", "c"):
        r = verify_member_ec3_2022(Ec3SemiCompactInput(**base, buckling_curve=curve))
        res[curve] = r
        print(f"  {curve:<6} {r.section_class:5d} {r.m_rd_2022:9.1f} {r.m_rd_2005_legacy:9.1f} {r.capacity_gain_pct:7.2f}% "
              f"{r.chi_buckling:6.3f} {r.n_b_rd:7.0f} {r.utilization:7.3f}")
    print(f"  M_Rd a mano: W_ep·fy = {W_ep * fy / 1e6:.1f} kN·m (función {res['a0'].m_rd_2022:.1f}); "
          f"W_el·fy = {Wel * fy / 1e6:.1f} kN·m")
    ra, rc = res["a0"], res["c"]
    print(f"\nLa curva por defecto a0 da χ = {ra.chi_buckling:.3f}; la curva c de una I soldada en z–z da "
          f"χ = {rc.chi_buckling:.3f} ({rc.chi_buckling / ra.chi_buckling - 1:+.0%}). Con a0 la barra "
          f"{'cumple' if ra.passes else 'no cumple'} (utilización {ra.utilization:.3f}); con la curva c "
          f"{'cumple' if rc.passes else 'no cumple'} ({rc.utilization:.3f}). La curva hay que pasarla siempre.")


if __name__ == "__main__":
    main()
