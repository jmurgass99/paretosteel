"""Base de perfiles AISC v16 empaquetada: carga, recuento por familia y conversión a SI comprobada a mano.

`catalogs_aisc_full.load_aisc_v16()` lee `paretosteel/data/aisc_v16.csv` (derivado de la AISC Shapes
Database v16.0) y convierte in → m, in² → m², in⁴ → m⁴ y lb/ft → kg/m. El ejemplo cuenta los perfiles
por familia, recalcula a mano la conversión del W14X90 desde la fila del CSV y comprueba que
`all_profiles()` ya no devuelve dos copias del mismo W (la copia tecleada a mano de `catalogs.py` frente
a la base AISC; en 1.0.0 W8X31 aparecía dos veces con Ix 4240 y 4579 cm⁴).

Referencia: AISC Shapes Database v16.0 (Steel Construction Manual, 16.ª ed., Tabla 1-1).

Ejecutar:  python examples/aisc_v16_catalog_load_unit_conversion_w14x90_hand_check_and_family_counts.py
"""
import csv
from collections import Counter
from pathlib import Path

import paretosteel
from paretosteel.catalogs import CATALOG_AISC_W, all_profiles
from paretosteel.catalogs_aisc_full import load_aisc_v16

IN, IN2, IN4, LBFT = 0.0254, 0.0254 ** 2, 0.0254 ** 4, 0.45359237 / 0.3048


def main() -> None:
    full = load_aisc_v16()
    fam = Counter(p.family for p in full.values())
    print(f"AISC v16 empaquetado: {len(full)} perfiles con peso, área e Ix")
    print("  " + ", ".join(f"{k} {v}" for k, v in fam.most_common()))

    csv_path = Path(paretosteel.__file__).parent / "data" / "aisc_v16.csv"
    row = next(r for r in csv.DictReader(csv_path.open(encoding="utf-8")) if r["AISC_Manual_Label"] == "W14X90")
    p = full["W14X90"]
    print(f"\nW14X90 en el CSV: W = {row['W']} lb/ft, A = {row['A']} in², d = {row['d']} in, "
          f"Ix = {row['Ix']} in⁴, Iy = {row['Iy']} in⁴")
    checks = [
        ("masa [kg/m]", float(row["W"]) * LBFT, p.weight_per_m),
        ("A [cm²]", float(row["A"]) * IN2 * 1e4, p.A * 1e4),
        ("d [mm]", float(row["d"]) * IN * 1e3, p.d * 1e3),
        ("Ix [cm⁴]", float(row["Ix"]) * IN4 * 1e8, p.Ix * 1e8),
        ("Iy [cm⁴]", float(row["Iy"]) * IN4 * 1e8, p.Iy * 1e8),
    ]
    print(f"  {'magnitud':<12} {'a mano':>10} {'paquete':>10} {'dif.':>8}")
    worst = 0.0
    for name, hand, pkg in checks:
        d = pkg / hand - 1.0
        worst = max(worst, abs(d))
        print(f"  {name:<12} {hand:10.2f} {pkg:10.2f} {d:+8.4%}")
    print(f"  Máxima diferencia {worst:.4%}: el paquete usa 1,488 kg/m por lb/ft y 4,1623e-7 m⁴ por in⁴ "
          f"(exactos: {LBFT:.5f} y {IN4:.7e}).")

    names = [q.designation for q in all_profiles()]
    dups = [k for k, v in Counter(names).items() if v > 1]
    print(f"\nall_profiles(): {len(names)} perfiles, designaciones repetidas: {len(dups)}")
    print("  Copia manual de catalogs.CATALOG_AISC_W frente a la base AISC v16 (la que queda en all_profiles):")
    by = {q.designation: q for q in all_profiles()}
    for k, man in CATALOG_AISC_W.items():
        ref = by[k]
        print(f"  {k:<7} Ix {man.Ix * 1e8:6.0f} → {ref.Ix * 1e8:6.0f} cm⁴ ({ref.Ix / man.Ix - 1:+.1%})   "
              f"Iy {man.Iy * 1e8:6.0f} → {ref.Iy * 1e8:6.0f} cm⁴ ({ref.Iy / man.Iy - 1:+.1%})")
    big = max(CATALOG_AISC_W, key=lambda k: abs(by[k].Ix / CATALOG_AISC_W[k].Ix - 1))
    print(f"  La mayor discrepancia en Ix es la de {big} "
          f"({by[big].Ix / CATALOG_AISC_W[big].Ix - 1:+.1%}); los optimizadores usan ya el valor de la base AISC.")


if __name__ == "__main__":
    main()
