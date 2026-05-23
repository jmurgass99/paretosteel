"""Costos USD/ton de acero estructural por pais (estimacion 2025-2026)."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CountryCost:
    country: str
    code: str
    USD_per_ton_raw: float
    USD_per_ton_fab: float       # fabricado pintado
    USD_per_ton_erected: float   # montado


_COSTS: dict[str, CountryCost] = {
    "CL": CountryCost("Chile",      "AU", 1400, 2200, 2800),
    "CO": CountryCost("Colombia",   "CO", 1300, 2100, 2700),
    "US": CountryCost("USA",        "US", 1600, 2700, 3500),
    "DE": CountryCost("Germany",    "EU", 1700, 2900, 3800),
    "SG": CountryCost("Singapore",  "SG", 1500, 2500, 3300),
    "AU": CountryCost("Australia",  "AU", 1650, 2800, 3700),
    "PE": CountryCost("Peru",       "CO", 1350, 2150, 2750),
}


def get_cost(country_iso: str) -> CountryCost:
    if country_iso not in _COSTS:
        raise KeyError(f"pais desconocido: {country_iso}; disponibles: {list(_COSTS)}")
    return _COSTS[country_iso]


def estimate_cost(country_iso: str, tons: float, stage: str = "erected") -> float:
    c = get_cost(country_iso)
    rate = {
        "raw": c.USD_per_ton_raw,
        "fab": c.USD_per_ton_fab,
        "erected": c.USD_per_ton_erected,
    }.get(stage)
    if rate is None:
        raise ValueError(f"stage desconocido: {stage}")
    return rate * tons


def list_countries() -> list[str]:
    return list(_COSTS.keys())


__all__ = ["CountryCost", "get_cost", "estimate_cost", "list_countries"]
