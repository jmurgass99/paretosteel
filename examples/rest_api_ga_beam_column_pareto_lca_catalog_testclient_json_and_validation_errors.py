"""API REST de ParetoSteel sin servidor: TestClient de FastAPI contra los endpoints del optimizador.

`api.app.create_app()` monta: GET /api/optimizer/health y /api/optimizer/catalog; POST /api/optimizer/ga,
/optimize/beam, /optimize/column, /api/steel-opt/pareto-lca y /api/steel-opt/gusset-plate. El ejemplo
llama a cada uno con datos de un pórtico pequeño, comprueba que el JSON coincide con la llamada directa a
la función de Python y prueba la validación: 422 si el cuerpo no cumple el esquema (pydantic) y 400 si
la configuración es incoherente (élite ≥ población). La versión de la API es la del paquete.

Necesita el extra `api` (FastAPI, httpx). Sin él, el ejemplo lo dice y termina.

Ejecutar:  python examples/rest_api_ga_beam_column_pareto_lca_catalog_testclient_json_and_validation_errors.py
"""
import warnings

import paretosteel


def main() -> None:
    try:
        warnings.filterwarnings("ignore", message=".*httpx.*")  # aviso de Starlette ajeno al cálculo
        from fastapi.testclient import TestClient
        from paretosteel.api.app import create_app
    except ImportError:
        print("La API necesita el extra 'api': pip install paretosteel[api]")
        return
    from paretosteel.services import BeamOptimizationInput, ColumnOptimizationInput, optimize_beam, optimize_column

    app = create_app()
    c = TestClient(app)
    print(f"ParetoSteel API {app.version} (paquete {paretosteel.__version__}); health → {c.get('/api/optimizer/health').json()}")
    cat = c.get("/api/optimizer/catalog", params={"family": "HEB"}).json()["profiles"]
    print(f"GET /api/optimizer/catalog?family=HEB → {len(cat)} perfiles: " + ", ".join(p["designation"] for p in cat))

    ga = c.post("/api/optimizer/ga", json={"groups": [
        {"name": "vigas", "length_total": 48.0, "min_Ix": 8.0e-5, "family_filter": "IPE"},
        {"name": "pilares", "length_total": 28.0, "min_Ix": 5.0e-5, "min_A": 7.0e-3, "family_filter": "HEB"}],
        "population_size": 30, "n_generations": 30, "random_seed": 7}).json()
    print(f"POST /api/optimizer/ga → {ga['assignment']}, {ga['weight']:.0f} kg, factible {ga['feasible']}, "
          f"{ga['n_generations']} valores de historial")

    body = {"L_m": 6.0, "M_Ed_kNm": 180.0, "V_Ed_kN": 90.0, "w_service_kN_m": 15.0, "section_family": "W"}
    b = c.post("/optimize/beam", json=body).json()
    direct = optimize_beam(BeamOptimizationInput(**body))
    print(f"POST /optimize/beam → {b['best_section']}, φMn {b['M_capacity_kNm']:.1f} kN·m, δ {b['deflection_mm']:.2f} mm; "
          f"igual que la función: {'sí' if b['best_section'] == direct.best_section and b['M_capacity_kNm'] == direct.M_capacity_kNm else 'no'}")
    col = {"L_m": 3.5, "P_Ed_kN": 1200.0, "section_family": "HP"}
    k = c.post("/optimize/column", json=col).json()
    kd = optimize_column(ColumnOptimizationInput(**col))
    print(f"POST /optimize/column → {k['best_section']}, φPn {k['P_capacity_kN']:.0f} kN, KL/r {k['slenderness']:.1f}; "
          f"igual que la función: {'sí' if k['best_section'] == kd.best_section else 'no'}")
    lca = c.post("/api/steel-opt/pareto-lca", json={"groups": [
        {"name": "vigas", "length_total": 48.0, "min_Ix": 8000.0, "family_filter": "IPE", "country": "ES",
         "steel_grade": "secondary_EAF"}], "population_size": 20, "n_generations": 10}).json()
    s0 = lca["solutions"][0]
    print(f"POST /api/steel-opt/pareto-lca → {lca['n_solutions']} solución: {s0['assignment']}, "
          f"{s0['total_cost_USD']:.0f} USD, {s0['total_co2_tCO2']:.2f} t CO₂ (min_Ix en cm⁴ en este endpoint)")

    bad = c.post("/optimize/beam", json=dict(body, L_m=-1.0))
    print(f"\nL_m = −1 → {bad.status_code}: {bad.json()['detail'][0]['msg']}")
    bad2 = c.post("/api/optimizer/ga", json={"groups": [{"name": "v", "length_total": 10.0}], "population_size": 10,
                                            "elitism": 10})
    print(f"élite = población → {bad2.status_code}: {bad2.json()['detail']}")
    bad3 = c.post("/api/optimizer/ga", json={"groups": [{"name": "v", "length_total": 0.0}]})
    print(f"length_total = 0 → {bad3.status_code}: {bad3.json()['detail'][0]['msg']}")


if __name__ == "__main__":
    main()
