"""Memoria de justificación del perfil elegido por el selector, con flecha y sin ella.

Viga de 8 m, M_u = 320 kN·m, V_u = 180 kN, carga de servicio 20 kN/m. `memo_from_beam_candidate`
toma el candidato de `beam_selector` y genera Markdown + LaTeX (handcalcs si está instalado; si no, un
LaTeX manual equivalente). En 1.0.0 la memoria recibía φMn como si fuera Mn y volvía a aplicar φ: el
W18X35 que el selector da por bueno (ratio 0,946) salía «NO CUMPLE» (1,051). Ahora los ratios
coinciden. Sin carga de servicio la flecha queda «NO VERIFICADA» y la memoria no firma CUMPLE.

Además, `justificar` (memoria corta de barra flectocomprimida, AISC 360 §H1) con y sin capacidad axial.

Escribe las memorias en examples/out/ (o en JM_EXAMPLES_OUT_DIR).

Ejecutar:  python examples/profile_justification_memo_from_selector_same_ratios_latex_engine_and_unverified_deflection.py
"""
import os
from pathlib import Path

from paretosteel.beam_selector import BeamDemand, optimize_beam
from paretosteel.memos.justificacion_perfil import JustificacionInput, justificar
from paretosteel.memos.profile_justification import _HAS_HANDCALCS, memo_from_beam_candidate

OUT = Path(os.environ.get("JM_EXAMPLES_OUT_DIR", Path(__file__).resolve().parent / "out"))


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    sel = optimize_beam(BeamDemand(M_kNm=320.0, V_kN=180.0)).selected
    memo = memo_from_beam_candidate(sel, span_m=8.0, w_kN_m=20.0)
    print(f"Selector: {sel.name}, M/φMn = {sel.flexural_ratio:.4f}, V/φVn = {sel.shear_ratio:.4f}")
    print(f"Memoria : {memo.section_name}, flexión {memo.ratio_flexion:.4f}, cortante {memo.ratio_cortante:.4f}, "
          f"flecha {memo.ratio_deflexion:.3f} → {'CUMPLE' if memo.cumple else 'NO CUMPLE'}")
    print(f"  Ratios iguales a los del selector: "
          f"{'sí' if abs(memo.ratio_flexion - sel.flexural_ratio) < 1e-12 else 'NO'}; "
          f"motor LaTeX: {'handcalcs' if _HAS_HANDCALCS else 'LaTeX manual (handcalcs no instalado)'}")
    L, w, Ix = 8000.0, 20.0, 21230e4
    print(f"  Flecha a mano: 5·20·8000⁴/(384·200000·{Ix:.4e}) = {5 * w * L ** 4 / (384 * 200000 * Ix):.2f} mm "
          f"frente a L/360 = {L / 360:.2f} mm → ratio {5 * w * L ** 4 / (384 * 200000 * Ix) / (L / 360):.3f}")
    (OUT / "memo_W18X35.md").write_text(memo.markdown, encoding="utf-8")
    (OUT / "memo_W18X35.tex").write_text(memo.latex, encoding="utf-8")
    print(f"  Escritas {OUT.name}/memo_W18X35.md ({len(memo.markdown.splitlines())} líneas) y .tex "
          f"({len(memo.latex)} caracteres)")

    if memo.cumple_flexion and memo.cumple_cortante and not memo.cumple_deflexion:
        print("  La memoria dice NO CUMPLE por flecha: beam_selector solo mira resistencia; con 20 kN/m de "
              "servicio en 8 m el W18X35 no llega a L/360 y hay que subir de perfil.")
    sin = memo_from_beam_candidate(sel, span_m=8.0, w_kN_m=0.0)
    linea = next(x for x in sin.markdown.splitlines() if "delta / delta_lim" in x)
    print(f"\nSin carga de servicio: {'CUMPLE' if sin.cumple else 'NO CUMPLE'} — «{linea.strip()}»")

    print("\njustificar (AISC H1): W12X65 con P_u = 900 kN, M_u = 160 kN·m, V_u = 60 kN; "
          "Mn = Zx·Fy = 1590e3·345, Vn = 0,6·Fy·d·tw, Pn = 3200 kN (supuesto, de un cálculo E3 previo)")
    j = justificar(JustificacionInput("W12X65", Mu_kNm=160, Vu_kN=60, Pu_kN=900,
                                      Mn_kNm=0.345 * 1590, Vn_kN=0.6 * 345 * 308 * 9.9 / 1e3, Pn_kN=3200))
    rp, rm = 900 / (0.9 * 3200), 160 / (0.9 * 0.345 * 1590)
    print(f"  P/φPn = {j.ratio_P:.3f}, M/φMn = {j.ratio_M:.3f}; H1-1a a mano {rp:.3f} + 8/9·{rm:.3f} = "
          f"{rp + 8 / 9 * rm:.3f} (función {j.ratio_combinado:.3f}) → {'CUMPLE' if j.cumple else 'NO CUMPLE'}")
    k = justificar(JustificacionInput("W12X65", Mu_kNm=160, Vu_kN=60, Pu_kN=900,
                                      Mn_kNm=0.345 * 1590, Vn_kN=500, Pn_kN=0.0))
    print(f"  Mismo caso sin Pn (capacidad axial ausente): P/φPn = {k.ratio_P}, {'CUMPLE' if k.cumple else 'NO CUMPLE'} "
          "(en 1.0.0 un Pn ausente daba P/φPn = 0 y la barra «cumplía» a axil).")


if __name__ == "__main__":
    main()
