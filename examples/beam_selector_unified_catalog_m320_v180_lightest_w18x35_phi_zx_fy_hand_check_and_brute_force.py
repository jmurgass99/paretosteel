"""Selector de vigas por enumeración y clasificación no dominada: M_u = 320 kN·m, V_u = 180 kN.

`beam_selector.optimize_beam` recorre el catálogo unificado (12 W + 18 EN), calcula para cada perfil
φMn = φ·Zx·Fy (AISC 360 §F2.1, sección compacta y arriostrada: Lb ≤ Lp) y φVn = 0,90·0,6·Fy·d·tw
(§G2.1 con Cv = 1), clasifica los factibles por (peso, ratio de flexión) con el kernel NSGA-II y se
queda con el más ligero del frente. El ejemplo recalcula a mano el perfil elegido y comprueba por
fuerza bruta que es el más ligero que cumple. También repite la selección solo con perfiles EN
(code="EU": M_pl,Rd = Wpl·fy/γ_M0 con γ_M0 = 1,0, EN 1993-1-1 §6.2.5).

No incluye pandeo lateral-torsional: si la viga no está arriostrada, compruébalo aparte
(ejemplo ec3_lateral_torsional_buckling_*).

Ejecutar:  python examples/beam_selector_unified_catalog_m320_v180_lightest_w18x35_phi_zx_fy_hand_check_and_brute_force.py
"""
from paretosteel.beam_selector import BeamDemand, optimize_beam
from paretosteel.catalog_unified import all_sections


def main() -> None:
    d = BeamDemand(M_kNm=320.0, V_kN=180.0, Fy_MPa=345.0, code="US")
    res = optimize_beam(d)
    print(f"Demanda M_u = {d.M_kNm} kN·m, V_u = {d.V_kN} kN, Fy = {d.Fy_MPa} MPa, LRFD")
    print(f"  {res.n_evaluated} perfiles evaluados, {res.n_feasible} factibles; frente de Pareto (peso, ratio M): "
          + ", ".join(res.pareto_front))
    feas = sorted((c for c in res.candidates if c.feasible), key=lambda c: c.weight_kg_m)
    print(f"  {'perfil':<8} {'kg/m':>6} {'φMn':>7} {'M/φMn':>6} {'φVn':>6} {'V/φVn':>6}")
    for c in feas[:6]:
        print(f"  {c.name:<8} {c.weight_kg_m:6.1f} {c.Mn_design_kNm:7.1f} {c.flexural_ratio:6.3f} "
              f"{c.Vn_design_kN:6.1f} {c.shear_ratio:6.3f}")
    sel = res.selected
    s = next(x for x in all_sections() if x.name == sel.name)
    phiMn = 0.9 * s.Zx_cm3 * 1e3 * d.Fy_MPa / 1e6
    phiVn = 0.9 * 0.6 * d.Fy_MPa * s.h_mm * s.tw_mm / 1e3
    print(f"\nSeleccionado {sel.name}: a mano φMn = 0,9·{s.Zx_cm3:.0f}e3·{d.Fy_MPa:.0f}/1e6 = {phiMn:.1f} kN·m "
          f"(función {sel.Mn_design_kNm:.1f}), ratio {d.M_kNm / phiMn:.4f}")
    print(f"  φVn = 0,9·0,6·{d.Fy_MPa:.0f}·{s.h_mm:.0f}·{s.tw_mm} /1e3 = {phiVn:.1f} kN (función {sel.Vn_design_kN:.1f}); "
          f"masa = {s.A_cm2}e-4·7850 = {s.A_cm2 * 0.785:.1f} kg/m")
    brute = min((x for x in all_sections()
                 if 0.9 * x.Zx_cm3 * d.Fy_MPa / 1e3 >= d.M_kNm
                 and 0.9 * 0.6 * d.Fy_MPa * x.h_mm * x.tw_mm / 1e3 >= d.V_kN), key=lambda x: x.A_cm2)
    print(f"  Fuerza bruta (mínima área con φMn ≥ M_u y φVn ≥ V_u): {brute.name} → "
          f"{'coincide' if brute.name == sel.name else 'NO coincide'} con el selector.")

    eu = optimize_beam(BeamDemand(M_kNm=320.0, V_kN=180.0, Fy_MPa=355.0, code="EU"), standard="EN")
    e = eu.selected
    es = next(x for x in all_sections() if x.name == e.name)
    print(f"\nSolo EN, S355, code='EU': {e.name} ({e.weight_kg_m:.1f} kg/m), M_pl,Rd = {es.Zx_cm3:.0f}e3·355/1e6 = "
          f"{es.Zx_cm3 * 0.355:.1f} kN·m (función {e.Mn_design_kNm:.1f}), ratio {e.flexural_ratio:.3f}")
    print(f"  El W elegido pesa {sel.weight_kg_m:.1f} kg/m frente a {e.weight_kg_m:.1f} kg/m del EN "
          f"({e.weight_kg_m / sel.weight_kg_m - 1:+.0%}); el cortante usa φv = 0,90 también en 'EU' (simplificación).")


if __name__ == "__main__":
    main()
