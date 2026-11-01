"""Optimizador de vigas mixtas (AISC 360-16 cap. I, LRFD): forjado de oficinas de 8 m sobre chapa colaborante.

Vigas de 8 m cada 2,8 m, losa de 120 mm de canto TOTAL sobre chapa de 50 mm (70 mm de hormigón sobre
los nervios), f'c = 28 MPa, 2400 kg/m³, cargas añadidas 1,2 kPa y uso 3,5 kPa, sin apuntalar, acero
de 345 MPa, pernos Ø19 (Rp = 0,75 en chapa). `optimize_composite_beam` evalúa los 30 perfiles del
catálogo unificado (fase de construcción sobre el acero solo, flexión y cortante mixtos, flecha de uso
L/360 y total L/240 con I_eff) y elige el más ligero del frente (peso, DCR que gobierna).

El ejemplo rehace a mano las cargas y el momento resistente del perfil elegido:
  construcción: q = máx(1,4·D, 1,2·D + 1,6·1,0 kPa·S); mixta: q = 1,2·(D + SDL) + 1,6·L
  b_eff = 2·mín(L/8, S/2); con conexión completa y bloque en la losa: a = As·Fy/(0,85·f'c·b_eff),
  Mn = As·Fy·(d/2 + h_chapa + h_c − a/2), φ = 0,90.
En 1.0.0 el adaptador pasaba los 120 mm totales como hormigón SOBRE la chapa y el brazo contaba la
chapa dos veces (IPE270: φMn = 411,0 kN·m en vez de 339,7). Se supone el ala superior arriostrada por
la chapa en construcción: no hay comprobación de pandeo lateral.

Ejecutar:  python examples/composite_floor_beam_optimizer_aisc_360_8_m_span_deck_slab_selected_profile_loads_and_phi_mn_hand_check.py
"""
from paretosteel.catalog_unified import all_sections
from paretosteel.composite_optimizer import CompositeOptimizationDemand, optimize_composite_beam

G = 9.80665


def main() -> None:
    d = CompositeOptimizationDemand(span_m=8.0, spacing_m=2.8, dead_load_superimposed_kpa=1.2, live_load_kpa=3.5,
                                    slab_thickness_mm=120.0, deck_height_mm=50.0, concrete_fc_MPa=28.0)
    res = optimize_composite_beam(d)
    print(f"{res.n_evaluated} perfiles evaluados, {res.n_feasible} factibles")
    print(f"  {'perfil':<8} {'kg/m':>6} {'DCR':>6} {'modo':<20} {'φMn':>6} {'Mu':>6} {'δ uso':>6} {'δ tot':>6} {'pernos':>6}")
    for c in sorted((c for c in res.all_evaluated if c.is_feasible), key=lambda c: c.weight_kg_m)[:6]:
        print(f"  {c.section_name:<8} {c.weight_kg_m:6.1f} {c.governing_dcr:6.3f} {c.governing_mode:<20} "
              f"{c.moment_capacity_kNm:6.1f} {c.applied_moment_kNm:6.1f} {c.deflection_live_mm:6.1f} "
              f"{c.deflection_total_mm:6.1f} {c.num_studs_total:6d}")
    sel = res.selected
    s = next(x for x in all_sections() if x.name == sel.section_name)
    print(f"Elegido: {sel.section_name} — frente de Pareto: " + ", ".join(p.section_name for p in res.pareto_front))

    L, S = 8.0, 2.8
    As = s.A_cm2 * 100.0
    w_sw = As * 1e-6 * 7850 * G / 1e3
    w_slab = (120 - 0.5 * 50) / 1e3 * S * 2400 * G / 1e3
    D = w_sw + w_slab + 0.15 * S
    q_c = max(1.4 * D, 1.2 * D + 1.6 * 1.0 * S)
    q_u = 1.2 * (D + 1.2 * S) + 1.6 * 3.5 * S
    Mu = q_u * L ** 2 / 8
    phiMp = 0.9 * s.Zx_cm3 * 1e3 * 345 / 1e6
    print(f"\nA mano ({s.name}): D = {w_sw:.3f} (perfil) + {w_slab:.3f} (losa con nervios al 50 %) + {0.15 * S:.2f} (chapa) "
          f"= {D:.3f} kN/m")
    print(f"  construcción q = máx(1,4·D, 1,2·D + 1,6·2,8) = {q_c:.2f} kN/m → M = {q_c * L ** 2 / 8:.1f} kN·m frente a "
          f"φMp = 0,9·Zx·Fy = {phiMp:.1f} → DCR {q_c * L ** 2 / 8 / phiMp:.3f} (función {sel.dcr_flexure_construction:.3f})")
    beff = 2 * min(L * 1000 / 8, S * 1000 / 2)
    T = As * 345
    a = T / (0.85 * 28 * beff)
    Mn = T * (s.h_mm / 2 + 50 + 70 - a / 2) / 1e6
    print(f"  mixta q = 1,2·(D + 1,2·2,8) + 1,6·3,5·2,8 = {q_u:.2f} kN/m → Mu = {Mu:.1f} kN·m (función {sel.applied_moment_kNm:.1f})")
    print(f"  b_eff = {beff:.0f} mm; T = As·Fy = {T / 1e3:.0f} kN; a = {a:.1f} mm < 70 mm; "
          f"φMn = 0,9·T·({s.h_mm / 2:.0f} + 50 + 70 − {a / 2:.1f}) = {0.9 * Mn:.1f} kN·m (función {sel.moment_capacity_kNm:.1f})")
    old = 0.9 * T * (s.h_mm / 2 + 50 + 120 - T / (0.85 * 28 * beff * 1.0) / 2) / 1e6
    print(f"  Con la chapa contada dos veces (1.0.0) habría salido {old:.1f} kN·m ({old / (0.9 * Mn) - 1:+.0%}).")
    print(f"\nGobierna «{sel.governing_mode}» (DCR {sel.governing_dcr:.3f}): "
          + ("sin apuntalar, el perfil lo fija el hormigón fresco, no la sección mixta." if "Constructiva" in sel.governing_mode
             else "la sección mixta o la flecha deciden el perfil."))


if __name__ == "__main__":
    main()
