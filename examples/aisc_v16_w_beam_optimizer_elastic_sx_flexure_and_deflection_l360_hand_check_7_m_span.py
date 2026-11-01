"""Servicio de optimización de vigas sobre los 289 W de la base AISC v16: flexión elástica y flecha L/360.

Viga biapoyada de 7 m con M_Ed = 250 kN·m y una carga de servicio de 18 kN/m. `services.optimize_beam`
ordena la familia por peso y devuelve el primer perfil con
  φ·Fy·Sx ≥ M_Ed      (Sx = Ix/(d/2), φ = 0,9; momento ELÁSTICO, sin Zx ni pandeo lateral)
  5·w·L⁴/(384·E·Ix) ≤ L/360.
El ejemplo recalcula a mano el elegido y el anterior en peso, muestra cuándo pasa a gobernar la
flecha y deja a la vista dos rasgos del servicio: V_Ed se acepta pero no se comprueba, y si no se da
`w_service_kN_m` la flecha se evalúa con 10 kN/m por defecto.

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
    dflt = optimize_beam(BeamOptimizationInput(L_m=L, M_Ed_kNm=M, V_Ed_kN=5000.0, section_family="W"))
    print(f"Con V_Ed = 5000 kN y sin w_service: {dflt.best_section} — el cortante no se comprueba y la flecha "
          f"se evalúa con la carga por defecto de 10 kN/m (δ = {dflt.deflection_mm:.2f} mm). Pasa siempre esos datos.")


if __name__ == "__main__":
    main()
