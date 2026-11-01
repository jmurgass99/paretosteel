"""Funciones de EN 1994-1-1 de `_composite.composite_beam`: pernos, chapa, conexión parcial y momento negativo.

1. Perno Ø19, h_sc = 100 mm, fu = 450 MPa en C30/37 (§6.6.3.1):
   P_Rd = mín(0,8·fu·πd²/4/γv; 0,29·α·d²·√(fck·Ecm)/γv), α = 1 si h_sc/d > 4, γv = 1,25;
   Ecm = 22 000·(fcm/10)^0,3 (EN 1992-1-1 Tabla 3.1).
2. Chapa con nervios transversales (hp = 60 mm, b0 = 100 mm), 1 y 2 pernos por nervio (§6.6.4.2):
   k_t = 0,7/√n_r·(b0/hp)·(h_sc/hp − 1) ≤ k_t,max (0,85 y 0,70 con chapa ≤ 1 mm y pernos soldados a través).
3. Grado mínimo de conexión (§6.6.1.2, alas iguales): η_min = 1 − (355/fy)·(0,75 − 0,03·Le) ≥ 0,4, y el
   momento con conexión parcial por interpolación lineal M_Rd = M_pl,a,Rd + η·(M_pl,Rd − M_pl,a,Rd).
4. Momento negativo con armadura de la losa (§6.2.1.2): M_pl,Rd,neg = M_pl,a,Rd + N_s·(h_a/2 + d_s) − N_s²/(4·t_w·fyd).
Todo se recalcula a mano dentro del ejemplo.

Ejecutar:  python examples/ec4_headed_stud_resistance_profiled_sheeting_kt_partial_connection_eta_min_and_hogging_moment.py
"""
import math

from paretosteel._composite.composite_beam import (kt_profiled_transverse, m_rd_partial_interaction, mpl_rd_block_method,
                                                    mpl_rd_hogging, partial_interaction, prd_profiled_transverse,
                                                    shear_connector_resistance)


def main() -> None:
    d, hsc, fu, fck = 19.0, 100.0, 450.0, 30.0
    Ecm = 22000 * ((fck + 8) / 10) ** 0.3
    Pa = 0.8 * fu * math.pi * d ** 2 / 4 / 1.25
    Pb = 0.29 * 1.0 * d ** 2 * math.sqrt(fck * Ecm) / 1.25
    P = shear_connector_resistance(d, fu, fck, hsc)
    print(f"1. Ecm = {Ecm:.0f} MPa; P_Rd = mín({Pa / 1e3:.1f}; {Pb / 1e3:.1f}) = {min(Pa, Pb) / 1e3:.1f} kN "
          f"(función {P / 1e3:.1f} kN) — manda {'el fuste' if Pa < Pb else 'el hormigón'}")

    hp, b0 = 60.0, 100.0
    print("2. Chapa transversal hp = 60, b0 = 100, h_sc = 100 mm:")
    for nr, cap in ((1, 0.85), (2, 0.70)):
        kt_raw = 0.7 / math.sqrt(nr) * (b0 / hp) * (hsc / hp - 1)
        kt = kt_profiled_transverse(b0, hp, hsc, nr)
        Pp = prd_profiled_transverse(d, fu, fck, hsc, b0, hp, nr)
        print(f"   n_r = {nr}: k_t = 0,7/√{nr}·{b0 / hp:.3f}·{hsc / hp - 1:.3f} = {kt_raw:.3f} → con tope {cap}: {min(kt_raw, cap):.3f} "
              f"(función {kt:.3f}); P_Rd = {Pp / 1e3:.1f} kN por perno")

    print("3. Grado mínimo de conexión (alas iguales):")
    for fy in (275.0, 355.0, 460.0):
        row = []
        for Le in (6.0, 10.0, 16.0, 25.0):
            em = partial_interaction(10, 20, Le=Le, fy=fy)["eta_min"]
            hand = max(0.4, 1 - 355 / fy * (0.75 - 0.03 * Le))
            assert abs(em - hand) < 1e-12
            row.append(f"Le {Le:4.1f} m → {em:.3f}")
        print(f"   S{fy:.0f}: " + "; ".join(row))
    Mpl_a = 0.355 * 1019  # IPE360 S355: Wpl·fy en kN·m
    Mpl = mpl_rd_block_method(170, 12.7, 8.0, 360, 2000, 70, 355, 20.0, h_p=50)
    for eta in (0.4, 0.7, 1.0):
        print(f"   IPE360 S355, b_eff 2 m, hc 70 + hp 50, C30/37: η = {eta:.1f} → M_Rd = {Mpl_a:.1f} + {eta}·({Mpl:.1f} − {Mpl_a:.1f}) = "
              f"{m_rd_partial_interaction(eta, Mpl_a, Mpl):.1f} kN·m")

    As, fsd, ds = 1200.0, 500 / 1.15, 90.0
    bf, tf, tw, ha, fyd = 170.0, 12.7, 8.0, 360.0, 355.0
    Wpl = bf * tf * (ha - tf) + tw * (ha - 2 * tf) ** 2 / 4
    Ns = As * fsd
    hand = (Wpl * fyd + Ns * (ha / 2 + ds) - Ns ** 2 / (4 * tw * fyd)) / 1e6
    neg = mpl_rd_hogging(bf, tf, tw, ha, As, fsd, ds, fyd)
    print(f"4. Momento negativo IPE360 (modelo de chapas) + 1200 mm² de B500 a 90 mm del ala: N_s = {Ns / 1e3:.0f} kN, "
          f"M_pl,a = {Wpl * fyd / 1e6:.1f} kN·m → M_pl,Rd,neg = {hand:.1f} kN·m (función {neg:.1f}), "
          f"{neg / (Wpl * fyd / 1e6) - 1:+.0%} sobre el acero solo")


if __name__ == "__main__":
    main()
