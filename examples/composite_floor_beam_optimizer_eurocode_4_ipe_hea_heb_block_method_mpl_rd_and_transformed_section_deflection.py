"""Optimizador de vigas mixtas con Eurocódigo 4 (EN 1994-1-1): perfiles IPE/HEA/HEB, S355, losa sobre chapa.

Mismo forjado que el ejemplo AISC (8 m, vigas cada 2,8 m, losa total 120 mm sobre chapa de 50 mm,
cargas 1,2 + 3,5 kPa) con perfiles EN de S355 y hormigón fck = 28 MPa:
  · combinaciones 1,35·G + 1,50·Q (construcción con 1,0 kPa de uso)
  · b_eff = 2·mín(Le/8, b_i) (§5.4.1.2); M_pl,Rd por bloques (§6.2.1.2) con fcd = fck/1,5, 0,85·fcd, fyd = fy;
    conexión completa con pernos Ø19 de losa maciza (P_Rd de §6.6.3.1, sin la reducción k_t por chapa)
  · flecha con la sección homogeneizada Ia + Ac/n·hc²/12 + Aa·(Ac/n)/(Aa + Ac/n)·d². En 1.0.0 se usaba
    Ia + (Ac/n)·d², que ignora el desplazamiento del eje neutro e infla la inercia ~2,5 veces.
El ejemplo rehace a mano M_pl,Rd del perfil elegido (modelo de chapas, sin radios de acuerdo) y su flecha.
El módulo de deformación del hormigón que usa el código, 9500·((fck + 8)/10)^(1/3) MPa, no es el Ecm de
EN 1992-1-1 (22 000·(fcm/10)^0,3): queda como límite documentado; el ejemplo muestra los dos n.

Ejecutar:  python examples/composite_floor_beam_optimizer_eurocode_4_ipe_hea_heb_block_method_mpl_rd_and_transformed_section_deflection.py
"""
from paretosteel.catalog_unified import all_sections
from paretosteel.composite_optimizer import CompositeOptimizationDemand, optimize_composite_beam


def main() -> None:
    d = CompositeOptimizationDemand(span_m=8.0, spacing_m=2.8, dead_load_superimposed_kpa=1.2, live_load_kpa=3.5,
                                    slab_thickness_mm=120.0, deck_height_mm=50.0, concrete_fc_MPa=28.0,
                                    standard="EUROCODE_4", steel_grade_Fy_MPa=355.0, catalog_filter_standard="EN")
    res = optimize_composite_beam(d)
    print(f"{res.n_evaluated} perfiles EN evaluados, {res.n_feasible} factibles")
    print(f"  {'perfil':<8} {'kg/m':>6} {'DCR':>6} {'modo':<20} {'M_Rd':>6} {'M_Ed':>6} {'δ uso':>6} {'δ tot':>6}")
    for c in sorted((c for c in res.all_evaluated if c.is_feasible), key=lambda c: c.weight_kg_m)[:5]:
        print(f"  {c.section_name:<8} {c.weight_kg_m:6.1f} {c.governing_dcr:6.3f} {c.governing_mode:<20} "
              f"{c.moment_capacity_kNm:6.1f} {c.applied_moment_kNm:6.1f} {c.deflection_live_mm:6.1f} {c.deflection_total_mm:6.1f}")
    sel = res.selected
    s = next(x for x in all_sections() if x.name == sel.section_name)
    print(f"Elegido: {sel.section_name} ({sel.weight_kg_m:.1f} kg/m), gobierna «{sel.governing_mode}» con DCR {sel.governing_dcr:.3f}")

    fy, fck, hc, hp, L = 355.0, 28.0, 70.0, 50.0, 8000.0
    fcd = fck / 1.5
    beff = 2 * min(L / 8, 2800 / 2)
    Aa = 2 * s.bf_mm * s.tf_mm + (s.h_mm - 2 * s.tf_mm) * s.tw_mm
    Npl = Aa * fy
    Ncf = 0.85 * fcd * beff * hc
    print(f"\nA mano ({s.name}): b_eff = {beff:.0f} mm; A_a (chapas) = {Aa:.0f} mm²; N_pl,a = {Npl / 1e3:.0f} kN; "
          f"N_c,f = 0,85·{fcd:.2f}·{beff:.0f}·{hc:.0f} = {Ncf / 1e3:.0f} kN")
    if Npl <= Ncf:
        x = Npl / (0.85 * fcd * beff)
        Mpl = Npl * (hc + hp + s.h_mm / 2 - x / 2) / 1e6
        print(f"  Eje neutro en la losa: x = {x:.1f} mm; M_pl,Rd = N_pl,a·({hc:.0f} + {hp:.0f} + {s.h_mm / 2:.0f} − {x / 2:.1f}) "
              f"= {Mpl:.1f} kN·m (función {sel.moment_capacity_kNm:.1f})")
    n_code = 200000 / (9500 * ((fck + 8) / 10) ** (1 / 3))
    n_ec2 = 200000 / (22000 * ((fck + 8) / 10) ** 0.3)
    Ac = beff * hc / n_code
    dd = s.h_mm / 2 + hp + hc / 2
    A_tab = s.A_cm2 * 100
    Itr = s.Ix_cm4 * 1e4 + Ac * hc ** 2 / 12 + A_tab * Ac / (A_tab + Ac) * dd ** 2
    I_old = s.Ix_cm4 * 1e4 + Ac * dd ** 2
    wq = 3.5 * 2.8
    dl = 5 * wq * L ** 4 / (384 * 200000 * Itr)
    print(f"  n del código = {n_code:.2f} (con Ecm de EN 1992-1-1 sería n0 = {n_ec2:.2f}); Ac/n = {Ac:.0f} mm²; d = {dd:.0f} mm")
    print(f"  I_tr = {Itr / 1e6:.1f}·10⁶ mm⁴ (fórmula de 1.0.0: {I_old / 1e6:.1f}·10⁶, ×{I_old / Itr:.2f}); "
          f"δ_uso = 5·{wq:.1f}·8000⁴/(384·200000·I_tr) = {dl:.2f} mm (función {sel.deflection_live_mm:.2f}) "
          f"frente a L/360 = {L / 360:.1f} mm")


if __name__ == "__main__":
    main()
