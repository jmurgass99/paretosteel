"""Interacción flexocompresión biaxial AISC 360-16 §H1.1 con amplificación B1 (Apéndice 8) en un W12X65.

Pilar W12X65, Fy = 345 MPa, KL = 4,5 m en los dos ejes, P_u = 1100 kN, M_ux = 180 kN·m, M_uy = 30 kN·m.
Propiedades (AISC, en SI): A = 12 300 mm², Ix = 222·10⁶ mm⁴, Iy = 72,4·10⁶ mm⁴, Zx = 1590·10³ mm³,
Zy = 723·10³ mm³, Sy = 477·10³ mm³, ry = 76,7 mm.
  Pn: §E3 con KL/r_y (función `bracing.aisc_e3_critical_stress`, independiente del módulo H1)
  Mnx = Zx·Fy (sección compacta, Lb ≤ Lp supuesto); Mny = min(Zy·Fy, 1,6·Sy·Fy) (§F6)
  Pe1 = π²EI/(K1L)²;  B1 = Cm/(1 − Pu/Pe1) ≥ 1;  Cm,x = 0,6 (M1/M2 = 0), Cm,y = 1,0
  H1-1a si Pu/φPn ≥ 0,2: Pu/φPn + 8/9·(Mrx/φMnx + Mry/φMny) ≤ 1;  H1-1b en otro caso.
El ejemplo rehace todo a mano, prueba también un axil bajo (H1-1b) y muestra lo que pasa si no se
pasan Ix, Iy y las longitudes: el módulo usa valores por defecto (1·10⁸ y 2·10⁷ mm⁴, 3 m) y calcula
un B1 con ellos sin avisar. Está marcado como experimental.

Ejecutar:  python examples/aisc_h1_beam_column_biaxial_interaction_b1_amplification_w12x65_hand_check_and_default_inputs.py
"""
import math

from paretosteel.bracing import aisc_e3_critical_stress
from paretosteel.design_codes import AiscBeamColumnInput, aisc_beam_column_interaction

FY, E = 345.0, 200000.0
A, IX, IY, ZX, ZY, SY, RY = 12300.0, 222e6, 72.4e6, 1590e3, 723e3, 477e3, 76.7
L = 4500.0


def main() -> None:
    Fcr, Fe, regime, _ = aisc_e3_critical_stress(L / RY, FY, E)
    Pn = Fcr * A / 1e3
    Mnx = ZX * FY / 1e6
    Mny = min(ZY * FY, 1.6 * SY * FY) / 1e6
    print(f"KL/r_y = {L / RY:.1f} → Fe = {Fe:.1f} MPa, Fcr = {Fcr:.1f} MPa ({regime}) → Pn = {Pn:.0f} kN")
    print(f"Mnx = Zx·Fy = {Mnx:.1f} kN·m; Mny = min(Zy·Fy, 1,6·Sy·Fy) = min({ZY * FY / 1e6:.1f}, {1.6 * SY * FY / 1e6:.1f}) = {Mny:.1f} kN·m")
    for Pu, Mux, Muy in ((1100.0, 180.0, 30.0), (150.0, 180.0, 30.0)):
        inp = AiscBeamColumnInput(Pu_kN=Pu, Pn_kN=Pn, Mux_kNm=Mux, Mnx_kNm=Mnx, Muy_kNm=Muy, Mny_kNm=Mny,
                                  L_x_mm=L, L_y_mm=L, Ix_mm4=IX, Iy_mm4=IY, E_MPa=E, Cm_x=0.6, Cm_y=1.0)
        r = aisc_beam_column_interaction(inp)
        Pe1x = math.pi ** 2 * E * IX / L ** 2 / 1e3
        Pe1y = math.pi ** 2 * E * IY / L ** 2 / 1e3
        B1x, B1y = max(1.0, 0.6 / (1 - Pu / Pe1x)), max(1.0, 1.0 / (1 - Pu / Pe1y))
        pr = Pu / (0.9 * Pn)
        ms = B1x * Mux / (0.9 * Mnx) + B1y * Muy / (0.9 * Mny)
        dcr = pr + 8 / 9 * ms if pr >= 0.2 else pr / 2 + ms
        print(f"\nP_u = {Pu:.0f} kN, M_ux = {Mux:.0f}, M_uy = {Muy:.0f} kN·m")
        print(f"  Pe1x = {Pe1x:.0f} kN, Pe1y = {Pe1y:.0f} kN (función {r.Pe1_x_kN:.0f}, {r.Pe1_y_kN:.0f})")
        print(f"  B1x = {B1x:.3f}, B1y = {B1y:.3f} (función {r.B1_x:.3f}, {r.B1_y:.3f}); Mry = {r.Mry_kNm:.1f} kN·m")
        print(f"  Pu/φPn = {pr:.3f} → {r.governing_equation}; DCR a mano {dcr:.4f}, función {r.dcr:.4f} → "
              f"{'cumple' if r.is_ok else 'NO cumple'}")
    d = aisc_beam_column_interaction(AiscBeamColumnInput(Pu_kN=1100.0, Pn_kN=Pn, Mux_kNm=180.0, Mnx_kNm=Mnx,
                                                         Muy_kNm=30.0, Mny_kNm=Mny, Cm_x=0.6))
    real = aisc_beam_column_interaction(AiscBeamColumnInput(Pu_kN=1100.0, Pn_kN=Pn, Mux_kNm=180.0, Mnx_kNm=Mnx,
                                                            Muy_kNm=30.0, Mny_kNm=Mny, L_x_mm=L, L_y_mm=L,
                                                            Ix_mm4=IX, Iy_mm4=IY, Cm_x=0.6))
    print(f"\nSin pasar Ix, Iy ni longitudes (valores por defecto): B1y = {d.B1_y:.3f} y DCR = {d.dcr:.4f}, frente a "
          f"B1y = {real.B1_y:.3f} y DCR = {real.dcr:.4f} con los datos reales ({d.dcr / real.dcr - 1:+.1%}). "
          "Los valores por defecto no son del perfil: pásalos siempre.")


if __name__ == "__main__":
    main()
