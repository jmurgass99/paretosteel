"""Pandeo lateral-torsional de una IPE300 S355 (EN 1993-1-1 §6.3.2) con longitudes libres de 2 a 10 m.

Propiedades EN 10365 de la IPE300: Iz = 604 cm⁴, It = 20,12 cm⁴, Iw = 125,9·10³ cm⁶, Wpl,y = 628 cm³,
h/b = 300/150 = 2,0. Apoyos en horquilla (k = kw = 1), carga en el centro de cortante, C1 = 1,0
(momento uniforme) y C1 = 1,127 (carga repartida, valor habitual de la literatura ECCS; no se cita aquí
una tabla concreta):
  Mcr = C1·π²·E·Iz/L²·√(Iw/Iz + L²·G·It/(π²·E·Iz))
  λ̄_LT = √(Wpl,y·fy/Mcr);  Φ = 0,5·[1 + α_LT·(λ̄_LT − 0,2) + λ̄_LT²];  χ_LT = 1/(Φ + √(Φ² − λ̄_LT²))
`get_ec3_ltb_curve` elige la curva: caso general (Tabla 6.4) h/b ≤ 2 → curva a (α = 0,21); método de
perfiles laminados (Tabla 6.5) h/b ≤ 2 → curva b (α = 0,34). `lateral_torsional_buckling_ec3`
aplica la fórmula del caso general; el método de §6.3.2.3 (λ̄_LT,0 = 0,4, β = 0,75, χ ≤ 1/λ̄²) está
en `_composite.composite_beam.chi_lt` y se usa aquí para comparar. Valores recomendados sin anejo nacional.

Ejecutar:  python examples/ec3_lateral_torsional_buckling_ipe300_s355_mcr_chi_lt_general_vs_rolled_method_spans_2_to_10_m.py
"""
import math

from paretosteel._composite.composite_beam import chi_lt
from paretosteel.design_codes import LtbEc3Input, get_ec3_ltb_curve, lateral_torsional_buckling_ec3

E, G, FY = 210000.0, 81000.0, 355.0
IZ, IT, IW, WPL = 604e4, 20.12e4, 125.9e9, 628e3


def mcr_hand(L, C1):
    return C1 * math.pi ** 2 * E * IZ / L ** 2 * math.sqrt(IW / IZ + L ** 2 * G * IT / (math.pi ** 2 * E * IZ)) / 1e6


def main() -> None:
    cg, ag = get_ec3_ltb_curve(300, 150, method="general")
    cr, ar = get_ec3_ltb_curve(300, 150, method="rolled")
    print(f"IPE300, h/b = 2,0: caso general → curva {cg} (α = {ag}); método laminados → curva {cr} (α = {ar})")
    Mpl = WPL * FY / 1e6
    print(f"M_pl,Rd = Wpl·fy/γ_M1 = {Mpl:.1f} kN·m (γ_M1 = 1,0)\n")
    print(f"  {'L [m]':>5} {'C1':>5} {'Mcr':>7} {'a mano':>7} {'λ̄_LT':>6} {'χ gen.':>6} {'Mb,Rd':>6} {'χ lam.':>6} {'Mb,Rd':>6}")
    worst = 0.0
    for C1 in (1.0, 1.127):
        for L in (2.0, 4.0, 6.0, 8.0, 10.0):
            r = lateral_torsional_buckling_ec3(LtbEc3Input(L_unrestrained_mm=L * 1000, Iz_mm4=IZ, Iw_mm6=IW, It_mm4=IT,
                                                           Wpl_y_mm3=WPL, fy_MPa=FY, C1=C1, alpha_LT=ag))
            hand = mcr_hand(L * 1000, C1)
            worst = max(worst, abs(r.Mcr_kNm / hand - 1))
            chi_r = chi_lt(r.lambda_bar_LT, curve=cr, method="rolled")
            assert abs(chi_lt(r.lambda_bar_LT, curve=cg, method="general") - r.chi_LT) < 1e-12
            print(f"  {L:5.1f} {C1:5.3f} {r.Mcr_kNm:7.1f} {hand:7.1f} {r.lambda_bar_LT:6.3f} {r.chi_LT:6.3f} "
                  f"{r.Mb_Rd_kNm:6.1f} {chi_r:6.3f} {chi_r * Mpl:6.1f}")
    print(f"\nMcr de la función frente a la fórmula a mano: diferencia máxima {worst:.1e}; χ_LT del caso general "
          "coincide con chi_lt(method='general') de la librería de vigas mixtas.")
    r6 = lateral_torsional_buckling_ec3(LtbEc3Input(6000, IZ, IW, IT, WPL, FY, C1=1.0, alpha_LT=ag))
    chi6 = chi_lt(r6.lambda_bar_LT, curve=cr, method="rolled")
    print(f"En 6 m con C1 = 1: Mb,Rd = {r6.Mb_Rd_kNm:.1f} kN·m por el caso general (curva {cg}) y {chi6 * Mpl:.1f} kN·m "
          f"por el método de laminados (curva {cr}); sin arriostramiento lateral en 6 m la resistencia baja al "
          f"{r6.Mb_Rd_kNm / Mpl:.0%} de M_pl,Rd por el caso general.")


if __name__ == "__main__":
    main()
