"""Catálogo unificado ASTM + EN: los W contrastados con la base AISC v16 y los EN con invariantes de forma.

`catalog_unified` es el catálogo (mm, cm², cm⁴, cm³) que usan `beam_selector` y `composite_optimizer`.
Sus doce W se comparan aquí con la base AISC v16 empaquetada (A, d, bf, Ix, Iy). La 1.1.0 corrigió
tres perfiles: W12X26 (Iy 740 → 720 cm⁴, Zx 615 → 610 cm³), W14X30 (Ix 12000 → 12110, Iy 820 → 816,
Zx 750 → 775 cm³ = 47,3 in³) y W18X35 (Ix 21000 → 21230, Iy 670 → 637). Para los IPE/HEA/HEB no hay
una base independiente en el paquete: se comprueba que Zx/Sx (factor de forma) cae en el rango de
un perfil I laminado y que Ix ≈ A·h²/4·k con k razonable.

Referencias: AISC Shapes Database v16.0; EN 10365:2017 (dimensiones de perfiles europeos).

Ejecutar:  python examples/unified_catalog_w_sections_cross_checked_against_aisc_v16_and_en_section_moduli_sanity.py
"""
import csv
from pathlib import Path

import paretosteel
from paretosteel.catalog_unified import all_sections

IN = 25.4


def main() -> None:
    rows = {r["AISC_Manual_Label"]: r for r in csv.DictReader(
        (Path(paretosteel.__file__).parent / "data" / "aisc_v16.csv").open(encoding="utf-8"))}
    print("W del catálogo unificado frente a la base AISC v16 (diferencia relativa)")
    print(f"  {'perfil':<7} {'A':>7} {'d':>7} {'bf':>7} {'Ix':>7} {'Iy':>7}")
    worst = ("", 0.0)
    for s in all_sections():
        if s.standard != "ASTM":
            continue
        r = rows[s.name]
        ref = {"A": float(r["A"]) * IN ** 2 / 100, "d": float(r["d"]) * IN, "bf": float(r["bf"]) * IN,
               "Ix": float(r["Ix"]) * IN ** 4 / 1e4, "Iy": float(r["Iy"]) * IN ** 4 / 1e4}
        val = {"A": s.A_cm2, "d": s.h_mm, "bf": s.bf_mm, "Ix": s.Ix_cm4, "Iy": s.Iy_cm4}
        d = {k: val[k] / ref[k] - 1 for k in ref}
        m = max(d.values(), key=abs)
        if abs(m) > abs(worst[1]):
            worst = (s.name, m)
        print(f"  {s.name:<7} " + " ".join(f"{d[k]:+7.2%}" for k in ("A", "d", "bf", "Ix", "Iy")))
    print(f"  Peor discrepancia en las cinco magnitudes: {worst[0]} {worst[1]:+.2%} "
          f"(tests/test_correcciones_1_1_0.py exige ≤ 0,5 % en A, Ix e Iy).")

    print("\nPerfiles EN: factor de forma Zx/Sx y Ix/(A·h²/4)")
    print(f"  {'perfil':<7} {'Zx/Sx':>6} {'Ix/(A·h²/4)':>12}")
    ratios = []
    for s in all_sections():
        if s.standard != "EN":
            continue
        Sx = s.Ix_cm4 / (s.h_mm / 20.0)
        f = s.Zx_cm3 / Sx
        k = s.Ix_cm4 / (s.A_cm2 * (s.h_mm / 10.0) ** 2 / 4.0)
        ratios.append(f)
        print(f"  {s.name:<7} {f:6.3f} {k:12.3f}")
    ok = 1.05 < min(ratios) and max(ratios) < 1.20
    print(f"  Zx/Sx entre {min(ratios):.3f} y {max(ratios):.3f}: "
          + ("ninguno fuera de [1,05; 1,20], el rango de un I o H laminado en flexión fuerte." if ok
             else "hay valores fuera de [1,05; 1,20]: revisar la transcripción."))
    n_en = sum(1 for s in all_sections() if s.standard == "EN")
    n_w = sum(1 for s in all_sections() if s.standard == "ASTM")
    print(f"\nEl catálogo unificado tiene {n_w} W y {n_en} perfiles EN; no hay UC/UB ni perfiles soldados.")


if __name__ == "__main__":
    main()
