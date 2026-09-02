"""Cómputo de mediciones y presupuesto (Bill of Quantities - BoQ) de acero estructural.

Utiliza exclusivamente las áreas seccionales tabuladas según EN 10365 / AISC (sin aproximaciones de IShape simplificado)
y aplica las tarifas internacionales de `cost_by_country`.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

from .catalog_unified import all_sections
from .catalogs import ALL_CATALOGS
from .cost_by_country import get_cost, estimate_cost


@dataclass(frozen=True)
class SteelBoQItem:
    """Partida de medición de un perfil de acero con su longitud acumulada."""
    profile_name: str
    total_length_m: float


@dataclass(frozen=True)
class ProfileBoQSummary:
    profile_name: str
    total_length_m: float
    tabulated_area_cm2: float
    weight_per_m_kg: float
    total_weight_kg: float
    total_tonnage: float
    cost_USD: float
    co2_emissions_kg: float = 0.0


@dataclass(frozen=True)
class SteelBoQReport:
    country_iso: str
    country_name: str
    stage: str
    rate_USD_per_ton: float
    items: list[ProfileBoQSummary]
    total_length_m: float
    total_tonnage: float
    total_cost_USD: float
    total_co2_kg: float = 0.0
    co2_intensity_kg_per_kg: float = 1.8

    def to_dict(self) -> dict[str, Any]:
        return {
            "country_iso": self.country_iso,
            "country_name": self.country_name,
            "stage": self.stage,
            "rate_USD_per_ton": self.rate_USD_per_ton,
            "co2_intensity_kg_per_kg": self.co2_intensity_kg_per_kg,
            "items": [
                {
                    "profile_name": it.profile_name,
                    "total_length_m": it.total_length_m,
                    "tabulated_area_cm2": it.tabulated_area_cm2,
                    "weight_per_m_kg": it.weight_per_m_kg,
                    "total_weight_kg": it.total_weight_kg,
                    "total_tonnage": it.total_tonnage,
                    "cost_USD": it.cost_USD,
                    "co2_emissions_kg": it.co2_emissions_kg,
                }
                for it in self.items
            ],
            "total_length_m": self.total_length_m,
            "total_tonnage": self.total_tonnage,
            "total_cost_USD": self.total_cost_USD,
            "total_co2_kg": self.total_co2_kg,
        }


def _get_tabulated_profile_data(name: str) -> tuple[float, float]:
    """Obtiene el área tabulada en cm² y masa lineal en kg/m para el perfil dado."""
    norm_name = name.strip().upper().replace(" ", "")
    
    # 1. Buscar en catálogo unificado
    for sec in all_sections():
        if sec.name.upper().replace(" ", "") == norm_name:
            # Masa lineal teórica a partir de área tabulada EN 10365 (densidad 7850 kg/m³)
            w_per_m = (sec.A_cm2 * 1e-4) * 7850.0
            return sec.A_cm2, w_per_m

    # 2. Buscar en catálogos AISC / Euro
    for fam, cat in ALL_CATALOGS.items():
        for pname, pobj in cat.items():
            if pname.upper().replace(" ", "") == norm_name:
                a_cm2 = pobj.A * 1e4
                return a_cm2, pobj.weight_per_m

    raise KeyError(f"Perfil '{name}' no encontrado en los catálogos tabulados EN 10365 / AISC.")


def calculate_steel_boq(
    items: Sequence[SteelBoQItem],
    country_iso: str = "DE",
    stage: str = "erected",
) -> SteelBoQReport:
    """Calcula el BoQ de acero con cubicación exacta basada en área tabulada EN 10365 y costes por país."""
    c_info = get_cost(country_iso)
    rate = {
        "raw": c_info.USD_per_ton_raw,
        "fab": c_info.USD_per_ton_fab,
        "erected": c_info.USD_per_ton_erected,
    }[stage]

    summaries: list[ProfileBoQSummary] = []
    tot_len = 0.0
    tot_ton = 0.0
    tot_cost = 0.0
    tot_co2 = 0.0

    for it in items:
        a_cm2, w_kg_m = _get_tabulated_profile_data(it.profile_name)
        total_wt_kg = it.total_length_m * w_kg_m
        tonnage = total_wt_kg / 1000.0
        cost_item = tonnage * rate
        co2_item = total_wt_kg * c_info.co2_kg_per_kg

        tot_len += it.total_length_m
        tot_ton += tonnage
        tot_cost += cost_item
        tot_co2 += co2_item

        summaries.append(
            ProfileBoQSummary(
                profile_name=it.profile_name,
                total_length_m=it.total_length_m,
                tabulated_area_cm2=a_cm2,
                weight_per_m_kg=w_kg_m,
                total_weight_kg=total_wt_kg,
                total_tonnage=tonnage,
                cost_USD=cost_item,
                co2_emissions_kg=co2_item,
            )
        )

    return SteelBoQReport(
        country_iso=country_iso,
        country_name=c_info.country,
        stage=stage,
        rate_USD_per_ton=rate,
        items=summaries,
        total_length_m=tot_len,
        total_tonnage=tot_ton,
        total_cost_USD=tot_cost,
        total_co2_kg=tot_co2,
        co2_intensity_kg_per_kg=c_info.co2_kg_per_kg,
    )


__all__ = [
    "SteelBoQItem",
    "ProfileBoQSummary",
    "SteelBoQReport",
    "calculate_steel_boq",
]
