"""Golden test para cómputo de mediciones y presupuesto (BoQ) de acero con áreas tabuladas EN 10365 y costes por país.

Requisitos:
1. Verificación de suma exacta de tonelaje y coste total = ∑(partidas).
2. Uso de área seccional tabulada oficial EN 10365 (no IShape simplificado sin radios de acuerdo).
3. Test de regresión: demuestra que la aproximación IShape.A difiere del valor tabulado y que el BoQ usa el tabulado.
"""
from __future__ import annotations

import pytest
from steeloptimizerjm.boq import (
    SteelBoQItem,
    calculate_steel_boq,
)
from steeloptimizerjm.cost_by_country import get_cost


def test_golden_steel_boq_exact_sum_and_country_cost():
    """GOLDEN. Suma exacta de tonelaje y coste para combinación de perfiles con tarifa de Alemania."""
    items = [
        SteelBoQItem(profile_name="IPE 300", total_length_m=100.0),
        SteelBoQItem(profile_name="HEB 300", total_length_m=50.0),
    ]

    # Tarifa Alemania ('DE') montado ('erected') = 3800 USD/ton
    c_de = get_cost("DE")
    assert c_de.USD_per_ton_erected == 3800.0

    report = calculate_steel_boq(items=items, country_iso="DE", stage="erected")

    assert report.country_iso == "DE"
    assert report.rate_USD_per_ton == 3800.0
    assert len(report.items) == 2

    it1 = report.items[0]
    it2 = report.items[1]

    # IPE 300: A tabulada = 53.8 cm² -> masa lineal = 0.00538 m² * 7850 kg/m³ = 42.233 kg/m
    # Para 100 m: masa = 4223.3 kg = 4.2233 ton
    assert it1.tabulated_area_cm2 == pytest.approx(53.8, rel=1e-3)
    assert it1.total_tonnage == pytest.approx(100.0 * 53.8 * 1e-4 * 7850.0 / 1000.0, rel=1e-5)
    assert it1.cost_USD == pytest.approx(it1.total_tonnage * 3800.0, rel=1e-5)

    # HEB 300: A tabulada = 149.1 cm² -> masa lineal = 0.01491 m² * 7850 kg/m³ = 117.0435 kg/m
    # Para 50 m: masa = 5852.175 kg = 5.852175 ton
    assert it2.tabulated_area_cm2 == pytest.approx(149.1, rel=1e-3)
    assert it2.total_tonnage == pytest.approx(50.0 * 149.1 * 1e-4 * 7850.0 / 1000.0, rel=1e-5)
    assert it2.cost_USD == pytest.approx(it2.total_tonnage * 3800.0, rel=1e-5)

    # Suma exacta total
    expected_tot_ton = it1.total_tonnage + it2.total_tonnage
    expected_tot_cost = it1.cost_USD + it2.cost_USD
    assert report.total_tonnage == pytest.approx(expected_tot_ton, rel=1e-9)
    assert report.total_cost_USD == pytest.approx(expected_tot_cost, rel=1e-9)


def test_golden_tabulated_en10365_area_differs_from_simplified_ishape():
    """GOLDEN. Demuestra que IShape simplificado (2*bf*tf + (h-2*tf)*tw) subestima el área real por omitir los acuerdos r."""
    # Para IPE 300: h=300 mm, bf=150 mm, tf=10.7 mm, tw=7.1 mm, r=15 mm
    # Área simplificada = 2 * 150 * 10.7 + (300 - 2*10.7) * 7.1 = 3210 + 1978.06 = 5188.06 mm² = 51.88 cm²
    # Área tabulada real EN 10365 (con acuerdos r=15 mm) = 53.81 cm² (~3.7% más de acero real)
    h = 300.0
    bf = 150.0
    tf = 10.7
    tw = 7.1
    A_simplified_cm2 = (2.0 * bf * tf + (h - 2.0 * tf) * tw) / 100.0
    assert A_simplified_cm2 == pytest.approx(51.8806, rel=1e-3)

    report = calculate_steel_boq([SteelBoQItem(profile_name="IPE 300", total_length_m=10.0)], country_iso="DE")
    # Aserción obligatoria: el BoQ usa el área tabulada real de 53.8 cm², NO los 51.88 cm² simplificados
    assert report.items[0].tabulated_area_cm2 > A_simplified_cm2
    assert report.items[0].tabulated_area_cm2 == pytest.approx(53.8, rel=1e-2)


def test_golden_steel_boq_spain_cost_and_embodied_co2():
    """GOLDEN. Verificación de coste regional para España ('ES') y cálculo de CO2 incorporado."""
    # Perfil HEB 200: A tabulada = 78.1 cm² -> masa lineal = 0.00781 * 7850 = 61.3085 kg/m
    # 20.0 m -> masa total = 1226.17 kg = 1.22617 ton
    items = [SteelBoQItem(profile_name="HEB 200", total_length_m=20.0)]

    c_es = get_cost("ES")
    assert c_es.country == "Spain"
    assert c_es.USD_per_ton_fab == 2850.0
    assert c_es.co2_kg_per_kg == 1.80

    report = calculate_steel_boq(items=items, country_iso="ES", stage="fab")

    assert report.country_iso == "ES"
    assert report.country_name == "Spain"
    assert report.rate_USD_per_ton == 2850.0
    assert report.co2_intensity_kg_per_kg == 1.80
    assert report.total_tonnage == pytest.approx(1.22617, rel=1e-4)

    expected_cost_usd = 1.22617 * 2850.0
    expected_co2_kg = 1226.17 * 1.80
    assert report.total_cost_USD == pytest.approx(expected_cost_usd, rel=1e-4)
    assert report.total_co2_kg == pytest.approx(expected_co2_kg, rel=1e-4)
    assert report.items[0].co2_emissions_kg == pytest.approx(expected_co2_kg, rel=1e-4)

