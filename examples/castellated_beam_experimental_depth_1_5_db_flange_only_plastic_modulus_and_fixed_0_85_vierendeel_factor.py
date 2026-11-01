"""Viga alveolar (castellated) — módulo EXPERIMENTAL: qué calcula y qué no.

`castellated.design_castellated` toma una viga madre y devuelve:
  · canto alveolado d_g = 1,5·d_b (expansión fija del 50 %);
  · un módulo plástico aproximado con SOLO las alas: Z ≈ b_f·t_f·(d_g − t_f);
  · M_post = 0,85·M_pre, un factor fijo que el código atribuye a «AISC DG31 §3.4» (no contrastado:
    la Guía de Diseño 31 comprueba la sección en T en los huecos, el efecto Vierendeel y el pandeo del
    montante, no aplica un coeficiente único).
Para tres vigas madre (IPE300, W14X30, HEB300) el ejemplo compara ese Z con el módulo plástico de la
sección neta en el centro del hueco (dos T, con hueco de altura h_o = d_b para una expansión del 50 %:
d_g = d_b + h_o/2), calculado a mano, y señala la nota de «T delgada»: el código toma la altura de la T
como (d_g − 0,5·d_b)/2 = 0,5·d_b, mientras que con h_o = d_b la T mide (d_g − h_o)/2 = 0,25·d_b.
Ningún resultado de este módulo sirve para dimensionar.

Ejecutar:  python examples/castellated_beam_experimental_depth_1_5_db_flange_only_plastic_modulus_and_fixed_0_85_vierendeel_factor.py
"""
from paretosteel.castellated import CastellatedInput, design_castellated


def net_section_Z(db, bf, tf, tw, dg, ho):
    """Módulo plástico de la sección neta (dos T simétricas) respecto al eje de la viga alveolada."""
    dt = (dg - ho) / 2  # canto de cada T
    stem = dt - tf
    z_flange = bf * tf * (dg - tf)  # dos alas, brazo d_g − t_f entre centroides
    z_stem = 2 * tw * stem * (dg / 2 - tf - stem / 2)
    return z_flange + z_stem, dt


def main() -> None:
    beams = [("IPE300", 300, 150, 10.7, 7.1), ("W14X30", 351, 171, 9.8, 6.9), ("HEB300", 300, 300, 19.0, 11.0)]
    print(f"  {'madre':<7} {'d_g':>5} {'Z código':>9} {'Z neta':>8} {'código/neta':>11} {'T código':>8} {'T real':>6} {'M_pre':>6} {'M_post':>6}")
    below = []
    for name, db, bf, tf, tw in beams:
        r = design_castellated(CastellatedInput(parent_db_mm=db, parent_bf_mm=bf, parent_tf_mm=tf, parent_tw_mm=tw, Fy_MPa=355))
        dg = r.db_castellated_mm
        Zc = bf * tf * (dg - tf)
        Zn, dt = net_section_Z(db, bf, tf, tw, dg, ho=db)
        t_code = (dg - 0.5 * db) / 2
        print(f"  {name:<7} {dg:5.0f} {Zc / 1e3:9.0f} {Zn / 1e3:8.0f} {Zc / Zn:11.3f} {t_code:8.0f} {dt:6.0f} "
              f"{r.Mn_pre_kNm:6.0f} {r.Mn_post_kNm:6.0f}")
        assert abs(r.Mn_pre_kNm - Zc * 355 / 1e6) < 1e-9 and abs(r.capacity_ratio - 0.85) < 1e-12
        if r.notes:
            print(f"          notas del módulo: {'; '.join(r.notes)}")
        below.append(Zc < Zn)
    print("\nZ del código (solo alas) frente al de la sección neta: "
          + ("menor en los tres casos, del lado seguro en flexión pura" if all(below)
             else "MAYOR en algún caso, del lado inseguro")
          + "; pero el 0,85 fijo no sustituye las comprobaciones de la T, del Vierendeel ni del montante. "
          f"Estado declarado por el módulo: {r.validation_level}.")


if __name__ == "__main__":
    main()
