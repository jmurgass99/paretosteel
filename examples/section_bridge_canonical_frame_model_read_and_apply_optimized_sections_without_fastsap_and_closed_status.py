"""Puente de secciones con el modelo canónico: leer, optimizar y escribir perfiles sin fastsap.

Pórtico de dos plantas y un vano (6 m × 2 × 3,5 m) en el modelo canónico vendorizado
(`_common.model.Model`, inmutable). El flujo:
  1. `section_bridge.read_assigned_sections` lee {barra: sección} del modelo;
  2. `beam_selector` elige perfil para vigas y `services.optimize_column` para pilares con demandas de un
     análisis previo (supuestas aquí);
  3. `apply_proposed_sections(..., validate_against_catalog=False)` devuelve un modelo NUEVO con los
     perfiles propuestos. Validar contra catálogo (`True`) necesita el paquete `fastsap`, que no es
     dependencia de paretosteel; en 1.0.0 fastsap se importaba siempre y el puente fallaba sin él.
  4. El veredicto de cada barra se expresa con `_common.audit_status.resolve_status`, cerrado por
     defecto: sin declarar las seis evidencias, una utilización de 0,8 NO es «cumple».

Ejecutar:  python examples/section_bridge_canonical_frame_model_read_and_apply_optimized_sections_without_fastsap_and_closed_status.py
"""
import importlib.util

from paretosteel._common.audit_status import CalculationStatus, aggregate_calculation_statuses, resolve_status
from paretosteel._common.model import Element, Material, Model, Node, SectionRef
from paretosteel.beam_selector import BeamDemand, optimize_beam
from paretosteel.section_bridge import apply_proposed_sections, read_assigned_sections
from paretosteel.services import ColumnOptimizationInput, optimize_column


def main() -> None:
    nodes = tuple(Node(f"N{i}{j}", x, 0.0, z) for i, z in enumerate((0.0, 3.5, 7.0)) for j, x in enumerate((0.0, 6.0)))
    pre = SectionRef("HEB300", "I"), SectionRef("IPE500", "I")
    elems = (
        Element("P1", "N00", "N10", pre[0], "S355"), Element("P2", "N01", "N11", pre[0], "S355"),
        Element("P3", "N10", "N20", pre[0], "S355"), Element("P4", "N11", "N21", pre[0], "S355"),
        Element("V1", "N10", "N11", pre[1], "S355"), Element("V2", "N20", "N21", pre[1], "S355"),
    )
    model = Model(nodes=nodes, elements=elems, sections=pre,
                  materials=(Material("S355", E_MPa=210000.0, fy_MPa=355.0, rho_kg_m3=7850.0),))
    before = read_assigned_sections(model)
    print("Antes: " + ", ".join(f"{k}={v.name}" for k, v in before.items()))

    demands = {"V1": (210.0, 140.0), "V2": (150.0, 110.0)}  # M_Ed [kN·m], V_Ed [kN] por viga
    cols = {"P1": 820.0, "P2": 820.0, "P3": 380.0, "P4": 380.0}  # N_Ed [kN] por pilar
    proposed, ratios = {}, {}
    for v, (M, V) in demands.items():
        s = optimize_beam(BeamDemand(M_kNm=M, V_kN=V, Fy_MPa=355.0, code="EU"), standard="EN").selected
        proposed[v], ratios[v] = s.name, max(s.flexural_ratio, s.shear_ratio)
    for p, N in cols.items():
        r = optimize_column(ColumnOptimizationInput(L_m=3.5, P_Ed_kN=N, Fy_MPa=355.0, section_family="HEB"))
        proposed[p], ratios[p] = r.best_section, r.utilization_P
    new = apply_proposed_sections(model, proposed, validate_against_catalog=False)
    after = read_assigned_sections(new)
    print("Después: " + ", ".join(f"{k}={v.name}" for k, v in after.items()))
    print(f"  El modelo original no cambia (inmutable): P1 sigue con {read_assigned_sections(model)['P1'].name}; "
          f"secciones del modelo nuevo: {sorted(s.name for s in new.sections)}")
    have_fastsap = importlib.util.find_spec("fastsap") is not None
    print(f"  fastsap instalado: {'sí' if have_fastsap else 'no'} → la validación contra catálogo "
          + ("se puede pedir con validate_against_catalog=True." if have_fastsap
             else "no se ha hecho (validate_against_catalog=True lanzaría ImportError)."))

    print("\nEstado por barra (resolve_status, cerrado por defecto):")
    statuses = []
    for k, u in ratios.items():
        bare = resolve_status(u)
        full = resolve_status(u, demand_present=True, capacity_present=True, analysis_executed=False,
                              geometry_present=True, material_present=True, reinforcement_present=True)
        statuses.append(full)
        print(f"  {k}: {proposed[k]:<7} utilización {u:.3f} → sin evidencias {bare.value}; "
              f"con el análisis sin ejecutar {full.value}")
    ok = resolve_status(0.8, demand_present=True, capacity_present=True, analysis_executed=True,
                        geometry_present=True, material_present=True, reinforcement_present=True)
    print(f"  Solo con las seis evidencias declaradas True una utilización de 0,8 es {ok.value}.")
    print(f"Agregado del pórtico: {aggregate_calculation_statuses(statuses).value}; lista vacía → "
          f"{aggregate_calculation_statuses([]).value}. Las demandas de este ejemplo son supuestas, no de un análisis: "
          f"por eso se declara analysis_executed=False y nada sale {CalculationStatus.CALCULADO_CUMPLE.value}.")


if __name__ == "__main__":
    main()
