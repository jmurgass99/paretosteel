"""Diagonal HSS en cruz de San Andrés y en V invertida: AISC 360 (resistencias) y AISC 341 (capacidad).

Pórtico de 6 m de vano y 3,5 m de altura, diagonales HSS6X6X3/8 de A500 grado C (Fy = 345 MPa,
Fu = 427 MPa; Ry = 1,3 según AISC 341-16 Tabla A3.1, valor que recoge el AISC Engineering Journal).
Propiedades de la base AISC v16: A = 7,58 in², Ix = Iy = 39,5 in⁴.
  · Cruz: L = √(6² + 3,5²); fuera del plano K·L = 0,5·L (la diagonal traccionada arriostra el cruce),
    en el plano 1,0·L. Compresión §E3, tracción §D2 (φ = 0,90 fluencia; φ = 0,75 rotura con Ae).
  · Área neta efectiva: chapa de nudo de 16 mm en una ranura de 18 mm por cara, soldadura de 300 mm;
    U = 1 − x̄/l con x̄ = (B² + 2BH)/(4(B + H)) = 3B/8 para tubo cuadrado (Tabla D3.1, caso 6).
  · Esperadas (§F2.3): T = Ry·Fy·Ag; C = min(Ry·Fy, 1,14·Fcre)·Ag con Fcre de §E3 usando Ry·Fy.
  · V invertida: diagonales de esquina a centro de viga (3 m × 3,5 m), K = 1. Carga desequilibrada
    sobre la viga tras el pandeo: (T − 0,3·C)·sen θ y momento P·L/4 en la viga de 6 m.
Se comprueba todo a mano y se muestra el efecto de dejar el Ry por defecto del módulo (1,10, que es
el de perfiles W en A992 y no el de un tubo A500).

Ejecutar:  python examples/hss_brace_x_and_chevron_aisc_360_compression_tension_aisc_341_expected_strengths_and_unbalanced_beam_load.py
"""
import math

from paretosteel.bracing import (BracingSystemDemand, SteelBraceSection, calc_net_effective_area,
                                 calc_shear_lag_factor_U, calculate_chevron_beam_unbalanced_demand,
                                 design_steel_brace)
from paretosteel.catalogs_aisc_full import AISC_HSS_FULL

FY, FU, E, RY = 345.0, 427.0, 200000.0, 1.3


def fcr(klr, fy):
    Fe = math.pi ** 2 * E / klr ** 2
    return 0.658 ** (fy / Fe) * fy if klr <= 4.71 * math.sqrt(E / fy) else 0.877 * Fe


def main() -> None:
    p = AISC_HSS_FULL["HSS6X6X3/8"]
    Ag = p.A * 1e6
    r = math.sqrt(p.Ix / p.A) * 1000
    B, t = 6 * 25.4, 0.93 * 0.375 * 25.4
    l_w, slot = 300.0, 18.0
    U = calc_shear_lag_factor_U(case=2, x_bar_mm=3 * B / 8, L_conn_mm=l_w)
    An = Ag - 2 * t * slot
    Ae, ratio = calc_net_effective_area(Ag, An, U)
    print(f"HSS6X6X3/8: Ag = {Ag:.0f} mm², r = {r:.1f} mm, t_diseño = {t:.2f} mm")
    print(f"  U = 1 − (3·{B:.1f}/8)/{l_w:.0f} = {U:.3f}; An = Ag − 2·t·{slot:.0f} = {An:.0f} mm²; "
          f"Ae = {Ae:.0f} mm² (Ae/Ag = {ratio:.3f})")

    Lx = math.hypot(6000, 3500)
    sec = SteelBraceSection(A_mm2=Ag, rx_mm=r, ry_mm=r, length_mm=Lx, Fy_MPa=FY, Fu_MPa=FU, Ry=RY, Ae_ratio=ratio)
    x = design_steel_brace(sec, BracingSystemDemand(Pu_tension_kN=700, Pu_compression_kN=700), "X_BRACE")
    klr = Lx / r
    print(f"\nCruz, L = {Lx:.0f} mm: KL/r en el plano {x.KL_over_r_x:.1f}, fuera {x.KL_over_r_y:.1f} → gobierna {x.KL_over_r_governing:.1f}")
    print(f"  Fcr = {x.Fcr_MPa:.1f} MPa ({x.buckling_regime}; a mano {fcr(klr, FY):.1f}); φPn = {x.phi_Pn_compression_kN:.0f} kN, "
          f"DCR {x.dcr_compression:.3f}")
    print(f"  Tracción: φ·Fy·Ag = {0.9 * FY * Ag / 1e3:.0f}, φ·Fu·Ae = {0.75 * FU * Ae / 1e3:.0f} → φPn = {x.phi_Pn_tension_kN:.0f} kN, "
          f"DCR {x.dcr_tension:.3f}; estado {x.status}")
    alt = 0.9 * fcr(0.5 * Lx / r, FY) * Ag / 1e3
    print(f"  El módulo toma 1,0·L en el plano para la cruz (hipótesis conservadora); con la unión del cruce "
          f"contando también en el plano (0,5·L en los dos ejes) sería φPn = {alt:.0f} kN y DCR {700 / alt:.3f}.")
    Fcre = fcr(klr, RY * FY)
    print(f"  Esperadas: T = Ry·Fy·Ag = {RY * FY * Ag / 1e3:.0f} kN (función {x.expected_tension_capacity_kN:.0f}); "
          f"C = min(Ry·Fy, 1,14·Fcre)·Ag = {min(RY * FY, 1.14 * Fcre) * Ag / 1e3:.0f} kN (función {x.expected_compression_capacity_kN:.0f}); "
          f"esbeltez sísmica {x.slenderness_seismic_status}")

    Lc = math.hypot(3000, 3500)
    theta = math.degrees(math.atan2(3500, 3000))
    for ry, tag in ((RY, "Ry = 1,3 (A500 gr. C)"), (1.10, "Ry por defecto 1,10")):
        s2 = SteelBraceSection(A_mm2=Ag, rx_mm=r, ry_mm=r, length_mm=Lc, Fy_MPa=FY, Fu_MPa=FU, Ry=ry, Ae_ratio=ratio)
        v = design_steel_brace(s2, BracingSystemDemand(), "CHEVRON_INVERTED_V")
        ch = calculate_chevron_beam_unbalanced_demand(v, theta_deg=theta, beam_span_mm=6000.0, elastic_vertical_demand_kN=60.0)
        Pv = (v.expected_tension_capacity_kN - 0.3 * v.expected_compression_capacity_kN) * math.sin(math.radians(theta))
        print(f"\nV invertida, {tag}: L = {Lc:.0f} mm, θ = {theta:.1f}°, KL/r = {v.KL_over_r_governing:.1f}")
        print(f"  T = {v.expected_tension_capacity_kN:.0f} kN, C = {v.expected_compression_capacity_kN:.0f} kN, "
              f"0,3·C = {ch.P_post_buckling_kN:.0f} kN → P_v = (T − 0,3C)·sen θ = {Pv:.0f} kN (función {ch.P_unbalanced_vertical_kN:.0f})")
        print(f"  Momento en la viga de 6 m: P_v·L/4 = {ch.M_beam_midspan_kNm:.0f} kN·m, {ch.amplification_over_elastic:.1f} veces "
              f"la carga vertical del análisis elástico (60 kN)")
        if ry == RY:
            m_real = ch.M_beam_midspan_kNm
        else:
            low = ch.M_beam_midspan_kNm < m_real
            print(f"  Con el Ry por defecto el momento de diseño de la viga sale {ch.M_beam_midspan_kNm / m_real - 1:+.0%}"
                  + (": del lado inseguro. Pasa el Ry del material." if low else "."))


if __name__ == "__main__":
    main()
