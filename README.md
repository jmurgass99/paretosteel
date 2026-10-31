# paretosteel

Optimización multiobjetivo de estructuras de acero: NSGA-II (con aceleración Numba) y algoritmo genético sobre catálogos comerciales unificados (AISC completo, IPE, HEB, HEA, HSS), objetivos de peso, coste por país y huella de carbono (LCA), selectores de viga y pilar con comprobación LRFD, arriostramientos, vigas alveolares y mixtas, auditoría de pandeo lateral-torsional (AISC 360-22, EN 1993-1-1), sensibilidad de precios, reutilización de perfiles y mediciones (BoQ).

[![CI](https://github.com/jmurgass99/paretosteel/actions/workflows/ci.yml/badge.svg)](https://github.com/jmurgass99/paretosteel/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

Paquete independiente. Dependencias: `numpy`, `scipy`, `numba`, `pydantic`. Las rutinas de viga mixta van incluidas en `paretosteel/_composite`.

## Instalación

```bash
pip install git+https://github.com/jmurgass99/paretosteel.git
```

Extras: `api` (REST), `memos` (handcalcs), `test`.

## Inicio rápido

### Perfil de mínimo peso para una viga

```python
from paretosteel.beam_selector import BeamDemand, optimize_beam

res = optimize_beam(BeamDemand(M_kNm=320.0, V_kN=180.0, Fy_MPa=345.0, code="US"))
feasible = sorted((c for c in res.candidates if c.feasible), key=lambda c: c.weight_kg_m)
print(feasible[0].name, feasible[0].weight_kg_m)     # W18X35, 52.2 kg/m
```

### Asignación de perfiles por grupos con algoritmo genético

```python
from paretosteel import ElementGroup, GAConfig, optimize

groups = [
    ElementGroup(name="vigas", length_total=120.0, min_Ix=2.5e-4, family_filter="IPE"),
    ElementGroup(name="pilares", length_total=60.0, min_Ix=1.0e-4, min_A=8.0e-3, family_filter="HEB"),
    ElementGroup(name="arriostramientos", length_total=80.0, min_A=2.0e-3, family_filter="HSS"),
]
ga = optimize(groups, config=GAConfig(population_size=40, n_generations=40, random_seed=1))
print(ga.best.assignment, round(ga.best.weight))     # (('vigas','IPE450'), ('pilares','HEB240'), ...), 15680 kg
```

### Frente de Pareto peso-coste-carbono (NSGA-II)

```python
from paretosteel.nsga2 import nsga2_run                       # motor NSGA-II genérico
from paretosteel.pareto_lca import ParetoOptimizeInput, run_pareto_lca_optimizer
help(run_pareto_lca_optimizer)                               # frente peso-coste-CO2 sobre catálogo
```

`examples/01_beam_selection_and_ga_groups.py` ejecuta los dos primeros flujos con tablas.

## Módulos

| Módulo | Contenido |
|---|---|
| `catalogs`, `catalogs_aisc_full`, `catalog_unified`, `section_bridge` | Catálogos y sección unificada |
| `genetic`, `nsga2`, `nsga2_jit`, `_nsga2_fast`, `diff_evolution`, `optimizer`, `pareto`, `pareto_lca` | Motores de optimización |
| `beam_selector`, `column_optimizer`, `bracing`, `castellated`, `composite_optimizer` | Selectores y elementos especiales |
| `design_codes`, `aisc360_22_hss`, `ec3_2022_2g`, `deflection` | Comprobaciones normativas |
| `cost_by_country`, `cost_lca`, `price_sensitivity`, `price_sensitivity_v2`, `reuse`, `boq` | Coste, LCA, sensibilidad, reutilización y mediciones |
| `surrogate` | Metamodelo sustituto |
| `api/`, `memos/` | REST y memorias |

## Validación

Tests golden de interacción H1 de AISC, pandeo lateral-torsional EN 1993-1-1, frente de Pareto con LCA, mediciones y arriostramientos AISC; tests de propiedades con hypothesis.

## Licencia

MIT. Consulta [LICENSE](LICENSE).

---

Parte del toolkit estructural de código abierto **Loadpath**, de [Jesús Murgas](https://github.com/jmurgass99).
