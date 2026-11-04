# paretosteel

[Español](README.md) · **English**

Steel section selection and optimization over commercial catalogs.

[![CI](https://github.com/jmurgass99/paretosteel/actions/workflows/ci.yml/badge.svg)](https://github.com/jmurgass99/paretosteel/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

## What it does

- Picks the lightest section that passes, from the AISC v16 database (2299 sections) and a unified W + IPE/HEA/HEB catalog.
- Methods: enumeration with non-dominated sorting, a genetic algorithm by member groups, NSGA-II with Numba kernels, and SciPy differential evolution.
- Simplified AISC 360 and EN 1993-1-1 checks (flexure, compression, interaction, lateral-torsional buckling, torsion in tubes).
- Braces with AISC 341 capacity design, and composite beams (AISC 360 and EN 1994-1-1).
- Take-offs with cost and CO₂ by country, price sensitivity and section reuse.

## Install

```bash
pip install git+https://github.com/jmurgass99/paretosteel.git
```

Optional extras: `perf` (Numba), `api`, `memos`.

## Example

Lightest section that resists M = 250 kN·m and V = 120 kN (345 MPa steel):

```python
from paretosteel.beam_selector import BeamDemand, optimize_beam

r = optimize_beam(BeamDemand(M_kNm=250.0, V_kN=120.0))
print(r.selected.name, round(r.selected.flexural_ratio, 2))   # W18X35 0.74
```

More cases in [`examples/`](examples).

## What it does not do

- Project design: there is no structural analysis, demands come from the caller, and the lateral buckling in the selectors is approximate.
- A cost–CO₂ trade-off: `pareto_lca` and `pareto_weight_cost` always return a single point.
- Castellated beams: the `castellated` module is experimental and uses a fixed 0.85 factor.
- AS 4100: the `AU` branch of `design_codes` uses the AISC curve.

Details are in [docs/LIMITACIONES.md](docs/LIMITACIONES.md) (in Spanish).

## Tests

```bash
pip install -e ".[test]"
pytest -q
```

## License

MIT. See [LICENSE](LICENSE). Author: [Jesús Murgas](https://github.com/jmurgass99).
