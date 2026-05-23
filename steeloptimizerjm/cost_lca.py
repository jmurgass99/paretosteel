"""
Costos por país + huella de carbono (LCA simplificado) — ingreso a la
optimización multi-objetivo con dimensión costo y emisiones.

Datos típicos 2024-2025:
    Acero estructural: 1.85 tCO2/t (EPD industria global, EuroLifeCycle 2023)
    Reciclado: 0.6 tCO2/t  (proceso EAF)
"""
from __future__ import annotations

from dataclasses import dataclass


# Costos USD/ton (acero perfil A992/S355) por país — orientativo Q2-2025
COST_USD_PER_TON: dict[str, float] = {
    "CL": 1450.0,    # Chile
    "PE": 1350.0,
    "CO": 1500.0,
    "AR": 1400.0,
    "MX": 1300.0,
    "US": 1100.0,
    "ES": 1100.0,
    "DE": 1050.0,
    "CN": 850.0,
    "DEFAULT": 1300.0,
}


# Emisiones tCO2 / t acero
EMBODIED_CO2_TON_PER_TON: dict[str, float] = {
    "primary_BF":   2.20,    # alto horno tradicional
    "secondary_EAF": 0.60,   # arco eléctrico (chatarra)
    "average_global": 1.85,
    "low_carbon":   0.40,    # acero "verde" hidrógeno
}


@dataclass(frozen=True)
class CostLCAInput:
    weight_kg: float
    country: str = "DEFAULT"
    steel_grade: str = "average_global"


def evaluate_cost_lca(inp: CostLCAInput) -> dict[str, float]:
    weight_t = inp.weight_kg / 1000.0
    cost_per_ton = COST_USD_PER_TON.get(inp.country.upper(),
                                          COST_USD_PER_TON["DEFAULT"])
    co2_per_ton = EMBODIED_CO2_TON_PER_TON.get(inp.steel_grade,
                                                 EMBODIED_CO2_TON_PER_TON["average_global"])
    return {
        "weight_kg": inp.weight_kg,
        "cost_USD": weight_t * cost_per_ton,
        "co2_emissions_tCO2": weight_t * co2_per_ton,
        "cost_per_ton_USD": cost_per_ton,
        "co2_per_ton": co2_per_ton,
    }


__all__ = ["CostLCAInput", "COST_USD_PER_TON",
           "EMBODIED_CO2_TON_PER_TON", "evaluate_cost_lca"]
