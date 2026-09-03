"""Tests de integración y golden para verificación de chapa de nudo (Gusset Plate).

Normas: AISC 360-16 §J4.1 (Sección de Whitmore) y AISC 341-16 §F2.6c.2 (Franja de articulación 2t).
"""
import math
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from steeloptimizerjm.api.app import create_router
from steeloptimizerjm.bracing import check_gusset_plate


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(create_router())
    return TestClient(app)


def test_gusset_plate_whitmore_golden_hand_calc():
    """Golden analítico exacto derivado a mano según AISC 360-16 / AISC 341-16.

    Chapa t = 16 mm, Fy = 250 MPa, w_conn = 150 mm, L_conn = 200 mm, clearance = 40 mm, Pu = 800 kN:
      bw = 150 + 2 * 200 * tan(30°) = 380.940 mm
      Aw = 380.940 * 16 = 6095.04 mm²
      Pn = 250 * 6095.04 / 1000 = 1523.76 kN
      phi_Pn = 0.90 * 1523.76 = 1371.385 kN
      dcr = 800 / 1371.385 = 0.5833
      req_clearance = 2 * 16 = 32 mm <= 40 mm (OK)
    """
    res = check_gusset_plate(
        t_gusset_mm=16.0,
        Fy_gusset_MPa=250.0,
        w_conn_mm=150.0,
        L_conn_mm=200.0,
        clearance_provided_mm=40.0,
        Pu_tension_kN=800.0,
    )

    assert res.whitmore_width_mm == pytest.approx(380.940, rel=1e-4)
    assert res.whitmore_area_mm2 == pytest.approx(6095.04, rel=1e-4)
    assert res.Pn_whitmore_yield_kN == pytest.approx(1523.76, rel=1e-4)
    assert res.phi_Pn_whitmore_kN == pytest.approx(1371.385, rel=1e-4)
    assert res.dcr_whitmore == pytest.approx(0.5833, rel=1e-3)
    assert res.clearance_2t_required_mm == 32.0
    assert res.is_2t_clearance_ok is True
    assert res.status == "OK"


def test_gusset_plate_api_endpoint(client):
    """Verifica endpoint HTTP /api/steel-opt/gusset-plate."""
    payload = {
        "t_gusset_mm": 16.0,
        "Fy_gusset_MPa": 250.0,
        "w_conn_mm": 150.0,
        "L_conn_mm": 200.0,
        "clearance_provided_mm": 40.0,
        "Pu_tension_kN": 800.0,
    }
    resp = client.post("/api/steel-opt/gusset-plate", json=payload)
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["whitmore_width_mm"] == pytest.approx(380.940, rel=1e-4)
    assert data["Pn_whitmore_yield_kN"] == pytest.approx(1523.76, rel=1e-4)
    assert data["phi_Pn_whitmore_kN"] == pytest.approx(1371.385, rel=1e-4)
    assert data["dcr_whitmore"] == pytest.approx(0.5833, rel=1e-3)
    assert data["clearance_2t_required_mm"] == 32.0
    assert data["is_2t_clearance_ok"] is True
    assert data["status"] == "OK"
