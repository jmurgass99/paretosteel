"""AISC v16.0 catalog completo (~2,299 perfiles, 289 W shapes).

Lee el dataset empaquetado ``data/aisc_v16.csv`` (derivado del Excel oficial
``aisc-shapes-database-v16.0.xlsx`` de AISC, redistribuido vía
Engineering-Fundamentals de Flocode, licencia MIT).

Convierte unidades imperiales a SI:
    in  -> m         (x 0.0254)
    in² -> m²        (x 6.4516e-4)
    in⁴ -> m⁴        (x 4.1623e-7)
    lb/ft -> kg/m    (x 1.488)

Fuentes:
    - https://www.aisc.org/publications/steel-construction-manual-resources/
    - https://github.com/flocode/Engineering-Fundamentals (MIT)
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from .catalogs import SteelProfile

_LOG = logging.getLogger("paretosteel.catalogs_aisc_full")

# Factores de conversión imperial -> SI
_IN_TO_M = 0.0254
_IN2_TO_M2 = 6.4516e-4
_IN4_TO_M4 = 4.1623e-7
_LBFT_TO_KGM = 1.488

# Mapeo Type -> family normalizada
_FAMILY_MAP = {
    "W": "W",
    "M": "M",
    "S": "S",
    "HP": "HP",
    "C": "C",
    "MC": "MC",
    "HSS": "HSS",
    "PIPE": "PIPE",
    "L": "L",
    "WT": "WT",
    "MT": "MT",
    "ST": "ST",
    "2L": "2L",
}

# Path por defecto al CSV empaquetado
_DEFAULT_CSV = Path(__file__).parent / "data" / "aisc_v16.csv"


def _to_float(value: object) -> Optional[float]:
    """Convierte celdas (que pueden venir como '-' o NaN) a float o None."""
    try:
        if value is None:
            return None
        s = str(value).strip()
        if s in ("", "-", "nan", "NaN", "None"):
            return None
        return float(s)
    except (TypeError, ValueError):
        return None


def _row_to_profile(row: dict) -> Optional[SteelProfile]:
    """Convierte una fila del CSV a SteelProfile en SI. None si datos inválidos."""
    type_raw = str(row.get("Type", "")).strip()
    family = _FAMILY_MAP.get(type_raw)
    if family is None:
        return None

    designation = str(row.get("AISC_Manual_Label", "")).strip()
    if not designation:
        return None

    w = _to_float(row.get("W"))
    a = _to_float(row.get("A"))
    d = _to_float(row.get("d"))
    bf = _to_float(row.get("bf"))
    ix = _to_float(row.get("Ix"))
    iy = _to_float(row.get("Iy"))

    # Requerimos al menos peso, área, Ix
    if w is None or a is None or ix is None:
        return None

    return SteelProfile(
        designation=designation,
        family=family,
        weight_per_m=w * _LBFT_TO_KGM,
        A=a * _IN2_TO_M2,
        Ix=ix * _IN4_TO_M4,
        Iy=(iy if iy is not None else 0.0) * _IN4_TO_M4,
        d=(d if d is not None else 0.0) * _IN_TO_M,
        bf=(bf if bf is not None else 0.0) * _IN_TO_M,
    )


def load_aisc_v16(path: Optional[Path] = None) -> dict[str, SteelProfile]:
    """Carga el catálogo AISC v16.0 completo.

    Args:
        path: ruta al CSV. Si es None usa el dataset empaquetado.

    Returns:
        dict {designation: SteelProfile} con todos los perfiles válidos en SI.
    """
    import csv

    csv_path = Path(path) if path is not None else _DEFAULT_CSV
    if not csv_path.exists():
        raise FileNotFoundError(
            f"AISC v16 CSV no encontrado en {csv_path}. "
            "Verifica que el package data se instaló correctamente."
        )

    profiles: dict[str, SteelProfile] = {}
    with csv_path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            prof = _row_to_profile(row)
            if prof is None:
                continue
            profiles[prof.designation] = prof

    _LOG.info("AISC v16 loaded: %d profiles", len(profiles))
    return profiles


def _filter_by_family(catalog: dict[str, SteelProfile],
                       family: str) -> dict[str, SteelProfile]:
    return {k: v for k, v in catalog.items() if v.family == family}


# Carga eager al importar (constantes módulo)
try:
    _ALL = load_aisc_v16()
    AISC_W_FULL: dict[str, SteelProfile] = _filter_by_family(_ALL, "W")
    AISC_HSS_FULL: dict[str, SteelProfile] = _filter_by_family(_ALL, "HSS")
    AISC_M_FULL: dict[str, SteelProfile] = _filter_by_family(_ALL, "M")
    AISC_S_FULL: dict[str, SteelProfile] = _filter_by_family(_ALL, "S")
    AISC_C_FULL: dict[str, SteelProfile] = _filter_by_family(_ALL, "C")
    AISC_HP_FULL: dict[str, SteelProfile] = _filter_by_family(_ALL, "HP")
except Exception as exc:  # pragma: no cover - defensive
    _LOG.warning("No se pudo precargar AISC v16: %s", exc)
    AISC_W_FULL = {}
    AISC_HSS_FULL = {}
    AISC_M_FULL = {}
    AISC_S_FULL = {}
    AISC_C_FULL = {}
    AISC_HP_FULL = {}


__all__ = [
    "AISC_W_FULL",
    "AISC_HSS_FULL",
    "AISC_M_FULL",
    "AISC_S_FULL",
    "AISC_C_FULL",
    "AISC_HP_FULL",
    "load_aisc_v16",
]
