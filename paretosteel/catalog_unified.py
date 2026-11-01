"""Catalogo unificado ASTM + EN (perfiles W, IPE, HEA, HEB).

Unidades: mm, cm², cm⁴, cm³. Los W se contrastan en los tests contra la base AISC v16
empaquetada (`data/aisc_v16.csv`: A, d, bf, Ix, Iy); 1.1.0 corrigió Ix, Iy o Zx de W12X26,
W14X30 y W18X35 (W14X30: Zx 750 → 775 cm³ = 47,3 in³). No hay perfiles UC/UB.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UnifiedSection:
    name: str
    standard: str       # 'ASTM' o 'EN'
    h_mm: float
    bf_mm: float
    tw_mm: float
    tf_mm: float
    A_cm2: float
    Ix_cm4: float
    Iy_cm4: float
    Zx_cm3: float


_CATALOG: list[UnifiedSection] = [
    UnifiedSection("W12X26",  "ASTM", 310, 165, 5.8, 9.6, 49.3, 8500, 720, 610),
    UnifiedSection("W14X30",  "ASTM", 351, 171, 6.9, 9.8, 57.0, 12110, 816, 775),
    UnifiedSection("W16X40",  "ASTM", 407, 178, 7.7, 12.8, 76.1, 21560, 1200, 1196),
    UnifiedSection("W18X35",  "ASTM", 449, 152, 7.6, 10.8, 66.5, 21230, 637, 1090),
    UnifiedSection("W21X44",  "ASTM", 525, 165, 8.9, 11.4, 83.9, 35080, 860, 1560),
    UnifiedSection("W24X55",  "ASTM", 599, 178, 10.0, 12.8, 104.5, 56190, 1210, 2196),
    UnifiedSection("IPE200",  "EN",   200, 100, 5.6, 8.5, 28.5, 1943, 142, 220),
    UnifiedSection("IPE300",  "EN",   300, 150, 7.1, 10.7, 53.8, 8356, 604, 628),
    UnifiedSection("IPE400",  "EN",   400, 180, 8.6, 13.5, 84.5, 23130, 1318, 1307),
    UnifiedSection("HEA200",  "EN",   190, 200, 6.5, 10.0, 53.8, 3692, 1336, 429),
    UnifiedSection("HEA300",  "EN",   290, 300, 8.5, 14.0, 112.5, 18260, 6310, 1383),
    UnifiedSection("HEB300",  "EN",   300, 300, 11.0, 19.0, 149.1, 25166, 8563, 1869),
    # --- Catálogo Expandido Fase 9 ---
    UnifiedSection("W12X35",  "ASTM", 318, 167, 7.6, 13.2, 66.5, 11870, 1020, 839),
    UnifiedSection("W14X68",  "ASTM", 356, 255, 10.5, 18.3, 129.0, 30060, 5036, 1885),
    UnifiedSection("W16X45",  "ASTM", 410, 179, 8.8, 14.4, 85.8, 24390, 1365, 1349),
    UnifiedSection("W18X50",  "ASTM", 457, 190, 9.0, 14.5, 94.8, 33300, 1669, 1655),
    UnifiedSection("W21X62",  "ASTM", 533, 209, 10.2, 15.6, 118.0, 55370, 2393, 2360),
    UnifiedSection("W24X76",  "ASTM", 607, 228, 11.2, 17.3, 144.5, 87420, 3434, 3277),
    UnifiedSection("IPE270",  "EN",   270, 135, 6.6, 10.2, 45.9, 5790, 420, 484),
    UnifiedSection("IPE330",  "EN",   330, 160, 7.5, 11.5, 62.6, 11770, 788, 804),
    UnifiedSection("IPE360",  "EN",   360, 170, 8.0, 12.7, 72.7, 16270, 1043, 1019),
    UnifiedSection("IPE450",  "EN",   450, 190, 9.4, 14.6, 98.8, 33740, 1676, 1702),
    UnifiedSection("HEB200",  "EN",   200, 200, 9.0, 15.0, 78.1, 5696, 2003, 642),
    UnifiedSection("HEB260",  "EN",   260, 260, 10.0, 17.5, 118.4, 14920, 5135, 1283),
    UnifiedSection("HEB360",  "EN",   360, 300, 12.5, 22.5, 180.6, 43190, 10140, 2683),
    UnifiedSection("HEB400",  "EN",   400, 300, 13.5, 24.0, 197.8, 57680, 10820, 3232),
    UnifiedSection("HEA240",  "EN",   230, 240, 7.5, 12.0, 76.8, 7763, 2769, 745),
    UnifiedSection("HEA360",  "EN",   350, 300, 10.0, 17.5, 142.8, 33090, 7887, 2088),
    UnifiedSection("HEA450",  "EN",   440, 300, 11.5, 21.0, 178.0, 63720, 9465, 3216),
    UnifiedSection("HEA500",  "EN",   490, 300, 12.0, 23.0, 197.5, 86970, 10370, 3949),
]


def all_sections() -> list[UnifiedSection]:
    return list(_CATALOG)


def filter_by(standard: str | None = None, min_Zx: float = 0,
              max_A: float | None = None) -> list[UnifiedSection]:
    out = _CATALOG
    if standard is not None:
        out = [s for s in out if s.standard == standard]
    out = [s for s in out if s.Zx_cm3 >= min_Zx]
    if max_A is not None:
        out = [s for s in out if s.A_cm2 <= max_A]
    return out


def find_lightest(min_Zx: float, standard: str | None = None) -> UnifiedSection | None:
    cands = filter_by(standard=standard, min_Zx=min_Zx)
    if not cands:
        return None
    return min(cands, key=lambda s: s.A_cm2)


__all__ = ["UnifiedSection", "all_sections", "filter_by", "find_lightest"]
