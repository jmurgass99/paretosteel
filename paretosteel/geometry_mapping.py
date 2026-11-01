"""Separación Semántica -> Malla de Estaciones de Viga y Rutas Pareto (SpanStationMapping) para ParetoSteel.

Mapea vanos continuos semánticos (`span_to_stations`) y rutas siderúrgicas (`route_to_pareto`:
BF-BOF, EAF reciclado, Low-Carbon H2) a una malla discreta de estaciones de cálculo,
preservando la masa estructural, el costo total y la huella de carbono embebido (CO2e)
al refinar las estaciones por vano.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple


@dataclass(frozen=True)
class SemanticSpan:
    id: str
    length_m: float
    udl_kN_per_m: float
    point_load_kN: float = 0.0


@dataclass
class SpanStationMapping:
    """Mapeo Vano Semántico -> Estaciones Discretas y Rutas Pareto."""
    span_to_stations: Dict[str, List[int]] = field(default_factory=dict)
    station_to_span: Dict[int, str] = field(default_factory=dict)
    route_to_pareto: Dict[str, List[int]] = field(default_factory=dict)


@dataclass
class DiscretizedStation:
    index: int
    span_id: str
    x_m: float
    dx_m: float
    moment_kNm: float
    shear_kN: float
    min_Wpl_cm3: float


def build_span_pareto_mesh(
    spans: List[SemanticSpan] | None = None,
    stations_per_span: int = 8,
    fy_MPa: float = 355.0,
) -> Tuple[List[DiscretizedStation], SpanStationMapping, Dict[str, float]]:
    """Genera la malla de estaciones por vano y evalúa la frontera de Pareto Costo vs CO2e."""
    if spans is None:
        spans = [
            SemanticSpan("SPAN-1", length_m=7.5, udl_kN_per_m=28.0),
            SemanticSpan("SPAN-2", length_m=6.0, udl_kN_per_m=24.0),
        ]

    div = max(2, int(stations_per_span))
    mapping = SpanStationMapping()
    stations: List[DiscretizedStation] = []

    total_len = sum(s.length_m for s in spans)
    x_cursor = 0.0

    for s in spans:
        dx = s.length_m / div
        mapping.span_to_stations[s.id] = []
        for i in range(div):
            idx = len(stations)
            x_loc = (i + 0.5) * dx
            # Momento flector parabólico simplemente apoyado equivalente por tramo
            m_val = 0.5 * s.udl_kN_per_m * x_loc * (s.length_m - x_loc)
            v_val = s.udl_kN_per_m * (0.5 * s.length_m - x_loc)
            # Wpl requerido = M / fy en cm3
            wpl_req = (m_val * 1e6) / (fy_MPa * 1e3) if m_val > 0 else 10.0

            stations.append(
                DiscretizedStation(
                    index=idx,
                    span_id=s.id,
                    x_m=x_cursor + x_loc,
                    dx_m=dx,
                    moment_kNm=m_val,
                    shear_kN=v_val,
                    min_Wpl_cm3=wpl_req,
                )
            )
            mapping.span_to_stations[s.id].append(idx)
            mapping.station_to_span[idx] = s.id
        x_cursor += s.length_m

    max_wpl = max((st.min_Wpl_cm3 for st in stations), default=100.0)
    # Estimación de área y masa de perfil de acero según correlación IPE/HEB
    # A_cm2 ≈ 0.32 * Wpl^0.67
    area_cm2 = 0.35 * (max_wpl ** 0.68)
    mass_per_m = area_cm2 * 0.785
    total_mass_kg = mass_per_m * total_len

    # Rutas siderúrgicas Pareto: BF-BOF (2.2 kgCO2/kg, 1.8 $/kg), EAF (0.75 kgCO2/kg, 2.0 $/kg), Low-Carbon (0.28 kgCO2/kg, 2.4 $/kg)
    mapping.route_to_pareto["PRIMARY_BF_BOF"] = list(range(len(stations)))
    mapping.route_to_pareto["SECONDARY_EAF"] = list(range(len(stations)))
    mapping.route_to_pareto["LOW_CARBON_H2"] = list(range(len(stations)))

    summary = {
        "total_length_m": total_len,
        "max_moment_kNm": max((st.moment_kNm for st in stations), default=0.0),
        "total_mass_kg": total_mass_kg,
        "co2_BF_kg": total_mass_kg * 2.20,
        "cost_BF_usd": total_mass_kg * 1.80,
        "co2_EAF_kg": total_mass_kg * 0.75,
        "cost_EAF_usd": total_mass_kg * 2.05,
        "co2_Green_kg": total_mass_kg * 0.28,
        "cost_Green_usd": total_mass_kg * 2.45,
    }
    return stations, mapping, summary
