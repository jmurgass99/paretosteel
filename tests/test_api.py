"""Tests del endpoint REST."""
from __future__ import annotations
import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient
from steeloptimizerjm.api.app import create_app


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(create_app())


def test_catalog_endpoint_all(client: TestClient) -> None:
    r = client.get("/api/optimizer/catalog")
    assert r.status_code == 200
    body = r.json()
    assert "profiles" in body
    assert len(body["profiles"]) >= 20


def test_catalog_endpoint_filter(client: TestClient) -> None:
    r = client.get("/api/optimizer/catalog", params={"family": "IPE"})
    assert r.status_code == 200
    profs = r.json()["profiles"]
    assert all(p["family"] == "IPE" for p in profs)


def test_ga_endpoint(client: TestClient) -> None:
    payload = {
        "groups": [{"name": "cols", "length_total": 100.0,
                     "min_Ix": 2.0e-4, "min_A": 1.0e-2,
                     "family_filter": "HEB"}],
        "population_size": 20, "n_generations": 20, "random_seed": 42,
    }
    r = client.post("/api/optimizer/ga", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body["feasible"] is True
    assert "cols" in body["assignment"]


def test_ga_endpoint_bad_config(client: TestClient) -> None:
    payload = {"groups": [], "population_size": 10, "n_generations": 5}
    r = client.post("/api/optimizer/ga", json=payload)
    assert r.status_code == 400


def test_health_endpoint(client: TestClient) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_optimize_beam_endpoint_ok(client: TestClient) -> None:
    r = client.post("/optimize/beam", json={
        "L_m": 6.0, "M_Ed_kNm": 200.0, "V_Ed_kN": 50.0,
        "Fy_MPa": 345.0, "w_service_kN_m": 10.0,
        "section_family": "W", "max_weight_kg_m": 200.0,
    })
    assert r.status_code == 200, r.text
    data = r.json()
    assert "best_section" in data
    assert "is_feasible" in data
    assert data["is_feasible"] is True


def test_optimize_beam_endpoint_validation_error(client: TestClient) -> None:
    r = client.post("/optimize/beam", json={
        "L_m": -1, "M_Ed_kNm": 100,
    })
    # Pydantic gt=0 -> 422; ValueError interna -> 400
    assert r.status_code in (400, 422)


def test_optimize_beam_endpoint_infeasible(client: TestClient) -> None:
    r = client.post("/optimize/beam", json={
        "L_m": 10.0, "M_Ed_kNm": 10000.0, "w_service_kN_m": 50.0,
        "section_family": "W", "max_weight_kg_m": 50.0,
    })
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["is_feasible"] is False


def test_optimize_column_endpoint_ok(client: TestClient) -> None:
    r = client.post("/optimize/column", json={
        "L_m": 4.0, "P_Ed_kN": 1200.0, "K": 1.0,
        "Fy_MPa": 345.0, "section_family": "W", "max_weight_kg_m": 150.0,
    })
    assert r.status_code == 200, r.text
    data = r.json()
    assert "best_section" in data
    assert "is_feasible" in data
    assert data["is_feasible"] is True
    assert data["P_capacity_kN"] >= 1200.0
    assert data["slenderness"] <= 200.0


def test_optimize_column_endpoint_validation_error(client: TestClient) -> None:
    r = client.post("/optimize/column", json={
        "L_m": -1, "P_Ed_kN": 500,
    })
    assert r.status_code in (400, 422)


def test_optimize_column_endpoint_infeasible(client: TestClient) -> None:
    r = client.post("/optimize/column", json={
        "L_m": 6.0, "P_Ed_kN": 90000.0,
        "section_family": "W", "max_weight_kg_m": 40.0,
    })
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["is_feasible"] is False

