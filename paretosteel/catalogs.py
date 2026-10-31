"""Catálogos de perfiles de acero estructural.

Datos en SI (m, m², m⁴, kg/m). Subset de los perfiles más comunes
disponibles en mercado global (AISC + EN 10025).
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class SteelProfile:
    """Perfil estándar de acero.

    Atributos:
        designation: nombre comercial (W14x90, IPE300, HEB300...)
        family: W, HSS, IPE, HEB, HEA
        weight_per_m: kg/m
        A: área m²
        Ix: inercia eje fuerte m⁴
        Iy: inercia eje débil m⁴
        d: peralte m
        bf: ancho de ala m
    """
    designation: str
    family: str
    weight_per_m: float
    A: float
    Ix: float
    Iy: float
    d: float
    bf: float


# Subset funcional (~30 perfiles cubre 80% de uso)
CATALOG_AISC_W: dict[str, SteelProfile] = {
    "W14X90":  SteelProfile("W14X90",  "W", 134.0, 0.01702, 4.16e-4, 1.50e-4, 0.356, 0.369),
    "W14X74":  SteelProfile("W14X74",  "W", 110.0, 0.01405, 3.34e-4, 5.66e-5, 0.360, 0.257),
    "W14X61":  SteelProfile("W14X61",  "W",  90.7, 0.01161, 2.66e-4, 4.50e-5, 0.353, 0.254),
    "W12X65":  SteelProfile("W12X65",  "W",  96.7, 0.01232, 2.21e-4, 7.16e-5, 0.308, 0.305),
    "W12X53":  SteelProfile("W12X53",  "W",  78.9, 0.01006, 1.75e-4, 3.91e-5, 0.305, 0.254),
    "W10X45":  SteelProfile("W10X45",  "W",  67.0, 0.00855, 1.04e-4, 2.16e-5, 0.257, 0.204),
    "W10X33":  SteelProfile("W10X33",  "W",  49.1, 0.00626, 7.08e-5, 1.52e-5, 0.247, 0.202),
    "W8X31":   SteelProfile("W8X31",   "W",  46.1, 0.00587, 4.24e-5, 1.54e-5, 0.203, 0.203),
    "W8X24":   SteelProfile("W8X24",   "W",  35.7, 0.00455, 3.41e-5, 7.07e-6, 0.201, 0.165),
}

CATALOG_EURO_IPE: dict[str, SteelProfile] = {
    "IPE200": SteelProfile("IPE200", "IPE", 22.4, 0.002850, 1.94e-5, 1.42e-6, 0.200, 0.100),
    "IPE240": SteelProfile("IPE240", "IPE", 30.7, 0.003912, 3.89e-5, 2.83e-6, 0.240, 0.120),
    "IPE300": SteelProfile("IPE300", "IPE", 42.2, 0.005381, 8.36e-5, 6.04e-6, 0.300, 0.150),
    "IPE360": SteelProfile("IPE360", "IPE", 57.1, 0.007273, 1.63e-4, 1.04e-5, 0.360, 0.170),
    "IPE400": SteelProfile("IPE400", "IPE", 66.3, 0.008446, 2.31e-4, 1.32e-5, 0.400, 0.180),
    "IPE450": SteelProfile("IPE450", "IPE", 77.6, 0.009882, 3.37e-4, 1.68e-5, 0.450, 0.190),
    "IPE500": SteelProfile("IPE500", "IPE", 90.7, 0.01155, 4.82e-4, 2.14e-5, 0.500, 0.200),
}

CATALOG_EURO_HEB: dict[str, SteelProfile] = {
    "HEB200": SteelProfile("HEB200", "HEB", 61.3, 0.007808, 5.70e-5, 2.00e-5, 0.200, 0.200),
    "HEB240": SteelProfile("HEB240", "HEB", 83.2, 0.01060, 1.13e-4, 3.92e-5, 0.240, 0.240),
    "HEB300": SteelProfile("HEB300", "HEB", 117.0, 0.01491, 2.52e-4, 8.56e-5, 0.300, 0.300),
    "HEB360": SteelProfile("HEB360", "HEB", 142.0, 0.01810, 4.32e-4, 1.04e-4, 0.360, 0.300),
    "HEB400": SteelProfile("HEB400", "HEB", 155.0, 0.01978, 5.77e-4, 1.08e-4, 0.400, 0.300),
}

ALL_CATALOGS: dict[str, dict[str, SteelProfile]] = {
    "W": CATALOG_AISC_W,
    "IPE": CATALOG_EURO_IPE,
    "HEB": CATALOG_EURO_HEB,
}

# Intenta cargar el AISC v16 completo (~289 perfiles W + HSS/M/S/C/HP).
# Si falla (data no instalada), seguimos con los catálogos manuales.
try:
    from .catalogs_aisc_full import (  # noqa: E402
        AISC_W_FULL,
        AISC_HSS_FULL,
        AISC_M_FULL,
        AISC_S_FULL,
        AISC_C_FULL,
        AISC_HP_FULL,
        load_aisc_v16,
    )
    if AISC_W_FULL:
        ALL_CATALOGS["W_FULL"] = AISC_W_FULL
    if AISC_HSS_FULL:
        ALL_CATALOGS["HSS_FULL"] = AISC_HSS_FULL
    if AISC_M_FULL:
        ALL_CATALOGS["M_FULL"] = AISC_M_FULL
    if AISC_S_FULL:
        ALL_CATALOGS["S_FULL"] = AISC_S_FULL
    if AISC_C_FULL:
        ALL_CATALOGS["C_FULL"] = AISC_C_FULL
    if AISC_HP_FULL:
        ALL_CATALOGS["HP_FULL"] = AISC_HP_FULL
except Exception as _exc:  # pragma: no cover - defensive
    import logging as _logging
    _logging.getLogger("paretosteel").warning(
        "AISC full catalog no disponible: %s", _exc)


def all_profiles() -> list[SteelProfile]:
    """Lista plana de todos los perfiles disponibles."""
    out: list[SteelProfile] = []
    for cat in ALL_CATALOGS.values():
        out.extend(cat.values())
    return out


def filter_profiles(*, family: str | None = None,
                     min_Ix: float = 0.0,
                     min_A: float = 0.0) -> list[SteelProfile]:
    """Filtra perfiles del catálogo global."""
    profiles = all_profiles()
    if family:
        profiles = [p for p in profiles if p.family == family.upper()]
    return [p for p in profiles if p.Ix >= min_Ix and p.A >= min_A]
