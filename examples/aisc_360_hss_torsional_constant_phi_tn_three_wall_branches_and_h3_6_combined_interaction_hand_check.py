"""Torsión en perfiles tubulares (HSS) según AISC 360 §H3: constante C, φTn y la interacción H3-6.

Tubos A500 de Fy = 345 MPa con espesor de diseño t = 0,93·t_nominal (§B4.2):
  · C (rectangular) = 2(B − t)(H − t)t − 4,5(4 − π)t³;  C (circular) = π(D − t)²t/2
  · φTn = 0,90·Fcr·C con h = lado mayor − 3t y tres ramas: h/t ≤ 2,45√(E/Fy) → Fcr = 0,6Fy;
    hasta 3,07√(E/Fy) → 0,6Fy·2,45√(E/Fy)/(h/t); por encima → 0,458π²E/(h/t)²
  · H3-6: (Pr/Pc + Mrx/Mcx + Mry/Mcy) + (Vr/Vc + Tr/Tc)² ≤ 1
Se eligen tres tubos cuadrados que caen en las tres ramas y se recalcula todo a mano. El módulo solo
da φTn para tubos rectangulares; para el circular solo calcula C. La interacción se aplica siempre:
AISC permite ignorar la torsión cuando Tr ≤ 0,2·Tc, y el módulo no hace esa distinción.

Ejecutar:  python examples/aisc_360_hss_torsional_constant_phi_tn_three_wall_branches_and_h3_6_combined_interaction_hand_check.py
"""
import math

from paretosteel.aisc360_22_hss import (Aisc360HssH36Input, compute_hss_torsional_constant_c,
                                         compute_rect_hss_design_torsion_strength, verify_aisc360_22_hss_h3_6)

FY, E, IN = 345.0, 200000.0, 25.4


def main() -> None:
    lim1, lim2 = 2.45 * math.sqrt(E / FY), 3.07 * math.sqrt(E / FY)
    print(f"Límites de h/t: 2,45√(E/Fy) = {lim1:.1f}; 3,07√(E/Fy) = {lim2:.1f}")
    print(f"  {'tubo':<15} {'t [mm]':>6} {'h/t':>6} {'rama':<10} {'C [cm³]':>8} {'a mano':>8} {'φTn':>7} {'a mano':>7}")
    tubes = [("HSS8X8X3/8", 8, 3 / 8), ("HSS12X12X3/16", 12, 3 / 16), ("HSS16X16X3/16", 16, 3 / 16)]
    tc = {}
    for name, B_in, t_in in tubes:
        B, t = B_in * IN, 0.93 * t_in * IN
        C = compute_hss_torsional_constant_c("rectangular", B, B, t)
        C_hand = 2 * (B - t) * (B - t) * t - 4.5 * (4 - math.pi) * t ** 3
        ht = (B - 3 * t) / t
        if ht <= lim1:
            Fcr, rama = 0.6 * FY, "fluencia"
        elif ht <= lim2:
            Fcr, rama = 0.6 * FY * lim1 / ht, "inelástica"
        else:
            Fcr, rama = 0.458 * math.pi ** 2 * E / ht ** 2, "elástica"
        phiTn = compute_rect_hss_design_torsion_strength(B, B, t, FY)
        tc[name] = phiTn
        print(f"  {name:<15} {t:6.2f} {ht:6.1f} {rama:<10} {C / 1e3:8.1f} {C_hand / 1e3:8.1f} {phiTn:7.2f} "
              f"{0.9 * Fcr * C_hand / 1e6:7.2f}")
    D, t = 8.625 * IN, 0.93 * 0.322 * IN
    Cr = compute_hss_torsional_constant_c("round", D, t_des=t)
    print(f"  Circular HSS8.625X0.322: C = π(D − t)²t/2 = {math.pi * (D - t) ** 2 * t / 2 / 1e3:.1f} cm³ "
          f"(función {Cr / 1e3:.1f}); el módulo no calcula φTn de tubos circulares (como cota, 0,9·0,6·Fy·C = "
          f"{0.9 * 0.6 * FY * Cr / 1e6:.2f} kN·m)")

    print("\nH3-6 en el HSS8X8X3/8 (capacidades de diseño supuestas de cálculos previos):")
    Tc = tc["HSS8X8X3/8"]
    for Tr in (0.0, 0.15 * Tc, 0.5 * Tc):
        inp = Aisc360HssH36Input(p_r=600.0, p_c=1650.0, m_rx=60.0, m_cx=210.0, m_ry=0.0, m_cy=210.0,
                                 v_r=120.0, v_c=520.0, t_r=Tr, t_c=Tc)
        r = verify_aisc360_22_hss_h3_6(inp)
        hand = 600 / 1650 + 60 / 210 + (120 / 520 + Tr / Tc) ** 2
        print(f"  Tr = {Tr:5.2f} kN·m ({Tr / Tc:4.0%} de Tc): normal {r.normal_stress_term:.4f} + "
              f"(V + T)² {r.shear_torsion_term_squared:.4f} = {r.interaction_h3_6:.4f} (a mano {hand:.4f}) → "
              f"{'cumple' if r.passes else 'NO cumple'}")
    print("  Con Tr = 15 % de Tc AISC permitiría ignorar la torsión (umbral 20 %); el módulo la suma igualmente "
          "(del lado seguro).")


if __name__ == "__main__":
    main()
