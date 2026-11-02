"""Servicio de optimización de vigas sobre los 289 W de la base AISC v16: flexión elástica y flecha L/360.

Viga biapoyada de 7 m con M_Ed = 250 kN·m y una carga de servicio de 18 kN/m. `services.optimize_beam`
ordena la familia por peso y devuelve el primer perfil con
  φ·Fy·Sx ≥ M_Ed      (Sx = Ix/(d/2), φ = 0,9; momento ELÁSTICO por defecto: `use_plastic_modulus`
                        usa Zx y `L_b_m > 0` reduce por pandeo lateral)
  5·w·L⁴/(384·E·Ix) ≤ L/360
  0,9·0,6·Fy·d·tw ≥ V_Ed   (si se da V_Ed).
El ejemplo recalcula a mano el elegido y el anterior en peso, muestra cuándo pasa a gobernar la
flecha, comprueba el cortante con un V_Ed realista y uno imposible, y deja a la vista que si no se
da `w_service_kN_m` la flecha se evalúa con 10 kN/m por defecto.

Ejecutar:  python examples/aisc_v16_w_beam_optimizer_elastic_sx_flexure_and_deflection_l360_hand_check_7_m_span.py
"""
from paretosteel.catalogs_aisc_full import AISC_W_FULL
from paretosteel.services import BeamOptimizationInput, optimize_beam


def check(p, M, w, L, Fy=345.0, E=200000.0):
    Sx = p.Ix / (p.d / 2.0)
    phiMn = 0.9 * Fy * 1e3 * Sx
    delta = 5.0 * w * L ** 4 / (384.0 * E * 1e3 * p.Ix) * 1000.0
    return phiMn, delta


def main() -> None:
    L, M, w = 7.0, 250.0, 18.0
    res = optimize_beam(BeamOptimizationInput(L_m=L, M_Ed_kNm=M, w_service_kN_m=w, section_family="W"))
    print(f"L = {L} m, M_Ed = {M} kN·m, w_servicio = {w} kN/m, límite L/360 = {res.deflection_limit_mm:.2f} mm")
    print(f"  → {res.best_section}: {res.weight_kg_m:.1f} kg/m, φMn = {res.M_capacity_kNm:.1f} kN·m "
          f"({res.utilization_M:.1%}), δ = {res.deflection_mm:.2f} mm; {res.n_candidates_evaluated} perfiles probados")

    ws = sorted(AISC_W_FULL.values(), key=lambda p: p.weight_per_m)
    p = AISC_W_FULL[res.best_section]
    phiMn, delta = check(p, M, w, L)
    print(f"\nA mano para {p.designation}: Sx = Ix/(d/2) = {p.Ix:.4e}/{p.d / 2:.4f} = {p.Ix / (p.d / 2) * 1e6:.0f} cm³; "
          f"φMn = 0,9·345·Sx = {phiMn:.1f} kN·m")
    print(f"  δ = 5·{w}·7000⁴/(384·200000·{p.Ix * 1e12:.4e}) = {delta:.2f} mm")
    lighter = [q for q in ws if q.weight_per_m < p.weight_per_m]
    fails = {"flexión": 0, "flecha": 0, "las dos": 0}
    for q in lighter:
        m, dd = check(q, M, w, L)
        fm, fd = m < M, dd > L * 1000 / 360
        fails["las dos" if fm and fd else "flexión" if fm else "flecha"] += 1
    print(f"  Los {len(lighter)} W más ligeros fallan por: " + ", ".join(f"{k} {v}" for k, v in fails.items()))

    only_m = optimize_beam(BeamOptimizationInput(L_m=L, M_Ed_kNm=M, w_service_kN_m=0.001, section_family="W"))
    print(f"\nSin flecha relevante (w = 0,001 kN/m) bastaría {only_m.best_section} ({only_m.weight_kg_m:.1f} kg/m): "
          f"la flecha encarece {res.weight_kg_m / only_m.weight_kg_m - 1:+.0%}." if only_m.best_section != res.best_section
          else f"\nSin flecha relevante el perfil sería el mismo ({only_m.best_section}): gobierna la flexión.")
    for V in (150.0, 5000.0):
        rv = optimize_beam(BeamOptimizationInput(L_m=L, M_Ed_kNm=M, w_service_kN_m=w, V_Ed_kN=V, section_family="W"))
        print(f"Con V_Ed = {V:.0f} kN: {rv.best_section}"
              + (" — ningún W de la base resiste ese cortante (φVn = 0,9·0,6·Fy·d·tw)." if not rv.is_feasible
                 else (" — el mismo perfil: el cortante no gobierna." if rv.best_section == res.best_section
                       else f" — el cortante obliga a subir desde {res.best_section}.")))
    dflt = optimize_beam(BeamOptimizationInput(L_m=L, M_Ed_kNm=M, section_family="W"))
    print(f"Sin w_service: {dflt.best_section} — la flecha se evalúa con la carga por defecto de 10 kN/m "
          f"(δ = {dflt.deflection_mm:.2f} mm), no con la carga de servicio real.")


if __name__ == "__main__":
    main()
