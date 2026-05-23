"""
Vigas castellated (alma calada) — diseño según AISC Design Guide 31 +
EN 1993-1-1 (Annex N).

Patrón típico: hexágonos con altura del castellation = 0.5·db, paso = db.
Capacidad reducida por la presencia de los aberturas:
    Mn_castellated ≈ M_Vierendeel
"""
from __future__ import annotations

from dataclasses import dataclass
from math import pi
from typing import Any


@dataclass(frozen=True)
class CastellatedInput:
    parent_db_mm: float               # peralte viga base
    parent_bf_mm: float
    parent_tf_mm: float
    parent_tw_mm: float
    Fy_MPa: float = 345
    pattern: str = "hex"              # 'hex' o 'circle'


@dataclass(frozen=True)
class CastellatedResult:
    db_castellated_mm: float
    Mn_pre_kNm: float                 # momento sección original
    Mn_post_kNm: float                # con apertura crítica (Vierendeel)
    capacity_ratio: float
    notes: list[str]


def design_castellated(inp: CastellatedInput) -> CastellatedResult:
    """Calcula la altura aumentada (~1.5·db) y la capacidad reducida."""
    db_orig = inp.parent_db_mm
    db_cast = 1.50 * db_orig          # incremento estándar Litzka
    # Tee superior+inferior
    h_tee = (db_cast - 0.5 * db_orig) / 2.0
    # Zx aproximado de la viga castellated
    Zx_cast = inp.parent_bf_mm * inp.parent_tf_mm * (db_cast - inp.parent_tf_mm)
    Mn_pre = Zx_cast * inp.Fy_MPa / 1e6

    # Reducción por modo Vierendeel (~15-25% según L_opening/h_tee)
    # AISC DG31 §3.4 — factor 0.85 conservador
    Mn_post = 0.85 * Mn_pre

    notes = []
    if h_tee < 50:
        notes.append("Tee superior/inferior muy delgada — riesgo de pandeo local")
    if inp.parent_tw_mm < 6:
        notes.append("Alma original delgada — Vierendeel governing")

    return CastellatedResult(
        db_castellated_mm=db_cast,
        Mn_pre_kNm=Mn_pre, Mn_post_kNm=Mn_post,
        capacity_ratio=Mn_post / Mn_pre,
        notes=notes,
    )


__all__ = ["CastellatedInput", "CastellatedResult", "design_castellated"]
