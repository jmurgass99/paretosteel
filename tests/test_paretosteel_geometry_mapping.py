"""Tests para SpanStationMapping en ParetoSteel."""
from paretosteel.geometry_mapping import SemanticSpan, build_span_pareto_mesh


def test_span_station_mapping_refinement():
    spans = [
        SemanticSpan("SPAN-1", length_m=6.0, udl_kN_per_m=20.0),
        SemanticSpan("SPAN-2", length_m=8.0, udl_kN_per_m=25.0),
    ]
    st_4, map_4, sum_4 = build_span_pareto_mesh(spans=spans, stations_per_span=4)
    st_12, map_12, sum_12 = build_span_pareto_mesh(spans=spans, stations_per_span=12)

    assert len(st_4) == 8
    assert len(st_12) == 24
    assert len(map_12.span_to_stations["SPAN-1"]) == 12
    assert sum_12["total_mass_kg"] > 100.0
    assert sum_12["co2_BF_kg"] > sum_12["co2_EAF_kg"] > sum_12["co2_Green_kg"]
    assert sum_12["cost_BF_usd"] < sum_12["cost_EAF_usd"] < sum_12["cost_Green_usd"]
