"""Selección de perfil mínimo y optimización por grupos con algoritmo genético.

1. Viga con M = 320 kN·m y V = 180 kN: perfil de mínimo peso que cumple
   (frente de Pareto NSGA-II sobre el catálogo unificado).
2. Pórtico con tres grupos de elementos (vigas, pilares, arriostramientos) con
   inercia y área mínimas: el GA asigna un perfil comercial a cada grupo
   minimizando el peso total.

Ejecutar:  python examples/01_beam_selection_and_ga_groups.py
"""
from dataclasses import asdict

from paretosteel import ElementGroup, GAConfig, filter_profiles, optimize
from paretosteel.beam_selector import BeamDemand, optimize_beam


def main() -> None:
    res = optimize_beam(BeamDemand(M_kNm=320.0, V_kN=180.0, Fy_MPa=345.0, code="US"))
    print("Viga M = 320 kN·m, V = 180 kN (A992, LRFD):")
    d = asdict(res)
    for k, v in d.items():
        if not isinstance(v, (list, dict)):
            print(f"  {k:<22} {v}")
    cands = [c for c in (d.get("candidates") or []) if c.get("feasible")]
    cands.sort(key=lambda c: c["weight_kg_m"])
    print(f"  {'perfil':<10} {'kg/m':>7} {'M_n·φ [kN·m]':>13} {'ratio M':>8} {'ratio V':>8}")
    for c in cands[:6]:
        print(f"  {c['name']:<10} {c['weight_kg_m']:7.1f} {c['Mn_design_kNm']:13.0f} "
              f"{c['flexural_ratio']:8.2f} {c['shear_ratio']:8.2f}")
    print(f"  → más ligero factible: {cands[0]['name'] if cands else 'ninguno'}")

    groups = [
        ElementGroup(name="vigas", length_total=120.0, min_Ix=2.5e-4, min_A=0.0, family_filter="IPE"),
        ElementGroup(name="pilares", length_total=60.0, min_Ix=1.0e-4, min_A=8.0e-3, family_filter="HEB"),
        ElementGroup(name="arriostramientos", length_total=80.0, min_Ix=0.0, min_A=2.0e-3, family_filter="HSS"),
    ]
    print(f"\nCatálogo: {len(filter_profiles())} perfiles ({len(filter_profiles(family='IPE'))} IPE, "
          f"{len(filter_profiles(family='HEB'))} HEB, {len(filter_profiles(family='HSS'))} HSS)")
    ga = optimize(groups, config=GAConfig(population_size=40, n_generations=40, random_seed=1))
    print("Asignación óptima (GA, semilla 1):")
    best = ga.best
    for k, v in asdict(best).items():
        print(f"  {k:<16} {v}")
    print(f"  fitness por generación (primeras/últimas): {ga.history[:3]} ... {ga.history[-3:]}")


if __name__ == "__main__":
    main()
