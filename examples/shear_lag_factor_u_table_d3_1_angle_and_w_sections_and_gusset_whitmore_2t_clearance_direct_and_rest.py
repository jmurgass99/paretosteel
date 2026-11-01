"""Retraso de cortante (AISC 360 Tabla D3.1) y chapa de nudo: sección de Whitmore y franja libre 2t.

1. `calc_shear_lag_factor_U`:
   · caso 2: angular L4X4X1/2 atornillado por un ala con 3 tornillos a 75 mm (l = 150 mm), x̄ = 1,18 in;
     U = 1 − x̄/l. La Tabla D3.1 también tiene, para angulares, el caso 8 (U = 0,60 con 3 tornillos
     por línea; valor y regla de «el mayor de los dos» sin contrastar en esta revisión), que el módulo no
     implementa.
   · caso 7: W unidos por las alas con ≥ 3 tornillos por línea: U = 0,90 si bf ≥ 2/3·d, 0,85 si no
     (W10X33 y W12X26, d y bf de la base AISC v16).
2. `check_gusset_plate` para la diagonal HSS6X6X3/8 con P_u = 700 kN: chapa de 16 mm, Fy = 345 MPa,
   anchura de unión 152,4 mm, soldadura de 300 mm, franja libre de 40 mm:
   b_w = w + 2·l·tan 30°; φPn = 0,90·Fy·b_w·t (§J4.1); franja libre ≥ 2t (requisito de AISC 341 para
   pórticos arriostrados especiales; el número de cláusula que cita el módulo queda sin contrastar).
   La misma comprobación por la API REST (`/api/steel-opt/gusset-plate`) y un cuerpo inválido (422).

Ejecutar:  python examples/shear_lag_factor_u_table_d3_1_angle_and_w_sections_and_gusset_whitmore_2t_clearance_direct_and_rest.py
"""
import math
import warnings

from paretosteel.bracing import calc_net_effective_area, calc_shear_lag_factor_U, check_gusset_plate
from paretosteel.catalogs_aisc_full import AISC_W_FULL


def main() -> None:
    xbar, l = 1.18 * 25.4, 150.0
    U = calc_shear_lag_factor_U(case=2, x_bar_mm=xbar, L_conn_mm=l)
    Ag = 3.75 * 645.16  # L4X4X1/2: A = 3,75 in²
    An = Ag - (22 + 2) * 12.7  # un agujero de 22 mm (+2 mm) en el ala de 12,7 mm
    Ae, r = calc_net_effective_area(Ag, An, U)
    print(f"Angular L4X4X1/2, 3 tornillos: U = 1 − {xbar:.1f}/{l:.0f} = {U:.3f} (caso 2); "
          f"An = {An:.0f} mm², Ae = {Ae:.0f} mm² ({r:.3f}·Ag)")
    print(f"  Con el caso 8 (U = 0,60, sin contrastar) Ae sería {An * 0.60:.0f} mm²: "
          f"{'el caso 2 da más' if U > 0.60 else 'el caso 8 da más'}.")
    for name in ("W10X33", "W12X26"):
        p = AISC_W_FULL[name]
        U7 = calc_shear_lag_factor_U(case=7, bf_mm=p.bf * 1000, d_mm=p.d * 1000)
        print(f"  {name}: bf/d = {p.bf / p.d:.3f} {'≥' if p.bf >= 2 / 3 * p.d else '<'} 2/3 → U = {U7:.2f} (caso 7)")

    g = check_gusset_plate(t_gusset_mm=16.0, Fy_gusset_MPa=345.0, w_conn_mm=152.4, L_conn_mm=300.0,
                           clearance_provided_mm=40.0, Pu_tension_kN=700.0)
    bw = 152.4 + 2 * 300 * math.tan(math.radians(30))
    print(f"\nChapa de nudo: b_w = 152,4 + 2·300·tan 30° = {bw:.1f} mm (función {g.whitmore_width_mm:.1f}); "
          f"φPn = 0,9·345·{bw:.1f}·16/1e3 = {0.9 * 345 * bw * 16 / 1e3:.0f} kN (función {g.phi_Pn_whitmore_kN:.0f})")
    print(f"  DCR Whitmore {g.dcr_whitmore:.3f}; franja libre {g.clearance_provided_mm:.0f} mm frente a 2t = "
          f"{g.clearance_2t_required_mm:.0f} mm → {g.status}")
    g2 = check_gusset_plate(16.0, 345.0, 152.4, 300.0, 25.0, 700.0)
    print(f"  Con 25 mm de franja libre: {g2.status} (2t = 32 mm), aunque Whitmore siga en {g2.dcr_whitmore:.3f}")

    try:
        # Aviso de Starlette sobre httpx (deprecación de la librería, ajena al cálculo).
        warnings.filterwarnings("ignore", message=".*httpx.*")
        from fastapi.testclient import TestClient
        from paretosteel.api.app import create_app
    except ImportError:
        print("\n(La API necesita el extra 'api': pip install paretosteel[api])")
        return
    c = TestClient(create_app())
    body = {"t_gusset_mm": 16.0, "Fy_gusset_MPa": 345.0, "w_conn_mm": 152.4, "L_conn_mm": 300.0,
            "clearance_provided_mm": 40.0, "Pu_tension_kN": 700.0}
    rr = c.post("/api/steel-opt/gusset-plate", json=body)
    j = rr.json()
    print(f"\nPOST /api/steel-opt/gusset-plate → {rr.status_code}: φPn = {j['phi_Pn_whitmore_kN']:.0f} kN, "
          f"DCR = {j['dcr_whitmore']:.3f}, {j['status']}; igual que la llamada directa: "
          f"{'sí' if abs(j['phi_Pn_whitmore_kN'] - g.phi_Pn_whitmore_kN) < 1e-9 else 'no'}")
    bad = c.post("/api/steel-opt/gusset-plate", json=dict(body, t_gusset_mm=-5.0))
    print(f"  Con t = −5 mm → {bad.status_code} ({bad.json()['detail'][0]['msg']})")


if __name__ == "__main__":
    main()
