"""Envoltorios por código de `design_codes`: flexión de sección compacta y compresión, US / EU / AU.

  · `design_beam_compact`: US/CO φ·Z·Fy con φ = 0,90 (AISC 360 §F2.1); EU/SG W_pl·fy/γ_M0 con γ_M0 = 1,0
    (EN 1993-1-1 §6.2.5); AU φ·Z·fy con φ = 0,90, que solo vale para AS 4100 si se le pasa el módulo
    efectivo Ze (el código no lo calcula).
  · `design_column` con la esbeltez adimensional λc = (KL/r)·√(Fy/(π²E)):
    US: Fcr = 0,658^(λc²)·Fy si λc ≤ 1,5, 0,877/λc²·Fy si no (= AISC E3);
    EU: curva c fija (α = 0,49), γ_M1 = 1,0;
    AU: la MISMA curva de AISC, no la de AS 4100 §6.3.3 (αb, kf, λn); el resultado de 'AU' es AISC con φ = 0,9.
Se comparan los tres para un HEB300 de S355 en compresión con longitudes de 2 a 12 m, se comprueba a
mano un punto por código y se mide el salto de la curva AISC en el cambio de rama
(KL/r = 4,71√(E/Fy) ⇔ λc = 1,5): las dos ramas no coinciden exactamente (0,658^2,25 ≠ 0,877/2,25).

Ejecutar:  python examples/code_wrappers_beam_and_column_strength_us_eu_au_and_aisc_e3_transition_continuity.py
"""
import math

from paretosteel.bracing import aisc_e3_critical_stress
from paretosteel.design_codes import SteelBeamInput, SteelColumnInput, design_beam_compact, design_column

FY, E = 355.0, 210000.0
A, IZ, WPL = 14910.0, 85.63e6, 1869e3  # HEB300, EN 10365


def lam_c(L_mm):
    r = math.sqrt(IZ / A)
    return (L_mm / r) * math.sqrt(FY / (math.pi ** 2 * E))


def main() -> None:
    print("Flexión de sección compacta HEB300, W_pl = 1869 cm³, fy = 355 MPa:")
    for code in ("US", "EU", "AU"):
        r = design_beam_compact(SteelBeamInput(plastic_modulus_mm3=WPL, Fy_MPa=FY, code=code))
        print(f"  {code}: Mn = {r.Mn_kNm:.1f} kN·m, factor {r.factor:.2f} → M_d = {r.M_design_kNm:.1f} kN·m")

    print("\nCompresión HEB300 (eje débil, iz = √(Iz/A) = {:.1f} mm):".format(math.sqrt(IZ / A)))
    print(f"  {'L [m]':>5} {'λc':>5} {'US φPn':>7} {'EU Nb,Rd':>8} {'AU φNc':>7} {'EU/US':>6}")
    for L in (2.0, 4.0, 6.0, 8.0, 10.0, 12.0):
        lc = lam_c(L * 1000)
        res = {c: design_column(SteelColumnInput(A_mm2=A, Fy_MPa=FY, lambda_slenderness=lc, code=c))["P_design_kN"]
               for c in ("US", "EU", "AU")}
        print(f"  {L:5.1f} {lc:5.2f} {res['US']:7.0f} {res['EU']:8.0f} {res['AU']:7.0f} {res['EU'] / res['US']:6.3f}")
    lc = lam_c(6000)
    us_hand = 0.9 * 0.658 ** (lc ** 2) * FY * A / 1e3
    phi = 0.5 * (1 + 0.49 * (lc - 0.2) + lc ** 2)
    chi = 1 / (phi + math.sqrt(phi ** 2 - lc ** 2))
    print(f"  A mano en 6 m (λc = {lc:.3f}): US 0,9·0,658^λc²·Fy·A = {us_hand:.0f} kN; "
          f"EU Φ = {phi:.3f}, χ = {chi:.4f} → {chi * FY * A / 1e3:.0f} kN")
    same_au = all(abs(design_column(SteelColumnInput(A, FY, l, "AU"))["P_design_kN"]
                      - design_column(SteelColumnInput(A, FY, l, "US"))["P_design_kN"]) < 1e-9
                  for l in (0.3, 1.0, 1.6, 2.5))
    print(f"  'AU' idéntico a 'US' en todas las esbelteces probadas: {'sí' if same_au else 'no'} "
          "→ no es AS 4100.")

    klr_t = 4.71 * math.sqrt(200000.0 / 345.0)
    lo = aisc_e3_critical_stress(klr_t * (1 - 1e-9), 345.0, 200000.0)
    hi = aisc_e3_critical_stress(klr_t * (1 + 1e-9), 345.0, 200000.0)
    print(f"\nAISC E3 en el cambio de rama KL/r = 4,71·√(E/Fy) = {klr_t:.2f}: Fcr = {lo[0]:.4f} MPa ({lo[2]}) y "
          f"{hi[0]:.4f} MPa ({hi[2]}), salto relativo {abs(hi[0] / lo[0] - 1):.1e}, propio de la norma: "
          f"0,658^2,25 = {0.658 ** 2.25:.5f} frente a 0,877/2,25 = {0.877 / 2.25:.5f}.")


if __name__ == "__main__":
    main()
