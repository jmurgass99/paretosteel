# paretosteel

**Español** · [English](README.en.md)

Selección y optimización de perfiles de acero sobre catálogos comerciales.

[![CI](https://github.com/jmurgass99/paretosteel/actions/workflows/ci.yml/badge.svg)](https://github.com/jmurgass99/paretosteel/actions/workflows/ci.yml)
[![Licencia: MIT](https://img.shields.io/badge/licencia-MIT-green)](LICENSE)

## Qué hace

- Elige el perfil más ligero que cumple, sobre la base AISC v16 (2299 perfiles) y un catálogo unificado W + IPE/HEA/HEB.
- Métodos: enumeración con clasificación no dominada, algoritmo genético por grupos de barras, NSGA-II con kernels Numba y evolución diferencial de SciPy.
- Comprobaciones simplificadas de AISC 360 y EN 1993-1-1 (flexión, compresión, interacción, pandeo lateral-torsional, torsión en tubos).
- Arriostramientos con diseño por capacidad de AISC 341 y vigas mixtas (AISC 360 y EN 1994-1-1).
- Mediciones con coste y CO₂ por país, sensibilidad al precio y reutilización de perfiles.

## Instalación

```bash
pip install git+https://github.com/jmurgass99/paretosteel.git
```

Extras opcionales: `perf` (Numba), `api`, `memos`.

## Ejemplo

Perfil más ligero que resiste M = 250 kN·m y V = 120 kN (acero de 345 MPa):

```python
from paretosteel.beam_selector import BeamDemand, optimize_beam

r = optimize_beam(BeamDemand(M_kNm=250.0, V_kN=120.0))
print(r.selected.name, round(r.selected.flexural_ratio, 2))   # W18X35 0.74
```

Más casos en [`examples/`](examples).

## Qué no hace

- El cálculo de proyecto: no hay análisis estructural, las demandas las pone quien llama, y el pandeo lateral de los selectores es aproximado.
- Un compromiso coste–CO₂: `pareto_lca` y `pareto_weight_cost` siempre devuelven un único punto.
- Vigas alveolares: el módulo `castellated` es experimental y usa un factor fijo de 0,85.
- AS 4100: la rama `AU` de `design_codes` usa la curva de AISC.

El detalle está en [docs/LIMITACIONES.md](docs/LIMITACIONES.md).

## Pruebas

```bash
pip install -e ".[test]"
pytest -q
```

## Licencia

MIT. Ver [LICENSE](LICENSE). Autor: [Jesús Murgas](https://github.com/jmurgass99).
