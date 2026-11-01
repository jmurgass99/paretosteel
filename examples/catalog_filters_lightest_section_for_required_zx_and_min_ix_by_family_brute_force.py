"""Predimensionado por catálogo: perfil más ligero para un Zx requerido y para una inercia mínima por familia.

Viga biapoyada de 7,5 m con q_Ed = 42 kN/m (ELU) y q_k = 30 kN/m (servicio), acero S355:
  · M_Ed = q·L²/8 → Zx requerido = M_Ed/fy (EN 1993-1-1 §6.2.5, γ_M0 = 1,0)
  · I requerida por flecha L/300 bajo q_k: I = 5·q·L⁴/(384·E·L/300) (`deflection.required_I_udl`)
`catalog_unified.find_lightest` devuelve el perfil de menor área con Zx suficiente y
`catalogs.filter_profiles` filtra por familia e inercia. Ambos resultados se contrastan con una búsqueda
exhaustiva escrita en el propio ejemplo.

Ejecutar:  python examples/catalog_filters_lightest_section_for_required_zx_and_min_ix_by_family_brute_force.py
"""
from paretosteel.catalog_unified import all_sections, find_lightest
from paretosteel.catalogs import filter_profiles
from paretosteel.deflection import required_I_udl


def main() -> None:
    L, q_ed, q_k, fy, E = 7.5, 42.0, 30.0, 355.0, 210000.0
    M_ed = q_ed * L ** 2 / 8.0
    Zx_req = M_ed * 1e6 / fy / 1e3  # cm³
    I_req = required_I_udl(q_k, L * 1000.0, 300.0, E) / 1e4  # cm⁴ (q en N/mm = kN/m)
    print(f"Viga de {L} m: M_Ed = {q_ed}·{L}²/8 = {M_ed:.1f} kN·m → Zx ≥ {Zx_req:.0f} cm³; "
          f"flecha L/300 con q_k = {q_k} kN/m → I ≥ {I_req:.0f} cm⁴")

    print("\nPerfil más ligero que cumple Zx y además I (catálogo unificado):")
    for std in ("EN", "ASTM", None):
        s = find_lightest(Zx_req, standard=std)
        both = [x for x in all_sections() if (std is None or x.standard == std)
                and x.Zx_cm3 >= Zx_req and x.Ix_cm4 >= I_req]
        bf = min(both, key=lambda x: x.A_cm2) if both else None
        tag = std or "ambos"
        print(f"  {tag:<6} solo resistencia: {s.name:<7} (A {s.A_cm2:6.1f} cm², Zx {s.Zx_cm3:5.0f}, Ix {s.Ix_cm4:6.0f})"
              f"  | resistencia + flecha: {bf.name if bf else 'ninguno':<7}"
              + (f" (Ix {bf.Ix_cm4:6.0f})" if bf else ""))
        brute = min((x for x in all_sections() if (std is None or x.standard == std) and x.Zx_cm3 >= Zx_req),
                    key=lambda x: x.A_cm2)
        assert brute.name == s.name
    print("  find_lightest coincide con la búsqueda exhaustiva en los tres casos.")

    print("\nfilter_profiles por familia con I ≥ I_req (catálogo global SteelProfile, m⁴):")
    for fam in ("IPE", "HEB", "W"):
        cands = filter_profiles(family=fam, min_Ix=I_req * 1e-8)
        best = min(cands, key=lambda p: p.weight_per_m) if cands else None
        if best is None:
            print(f"  {fam:<4} ninguno")
            continue
        print(f"  {fam:<4} {len(cands):4d} candidatos; el más ligero {best.designation:<8} "
              f"{best.weight_per_m:6.1f} kg/m, Ix {best.Ix * 1e8:7.0f} cm⁴")
    print("\nOjo: filter_profiles solo mira Ix y A; la resistencia (Zx) y el pandeo lateral no entran en ese filtro.")


if __name__ == "__main__":
    main()
