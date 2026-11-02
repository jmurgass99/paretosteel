# paretosteel — scelta e ottimizzazione di profili in acciaio su cataloghi commerciali in Python

[Español](README.md) · [English](README.en.md) · [Português](README.pt.md) · **Italiano**

Scelta del profilo più leggero che verifica sulla base AISC v16 (2299 profili) e su un catalogo unificato W + IPE/HEA/HEB, per enumerazione con ordinamento non dominato, algoritmo genetico per gruppi di aste, NSGA-II con kernel Numba o evoluzione differenziale di SciPy; verifiche semplificate secondo AISC 360 ed EN 1993-1-1 (flessione compatta, compressione §E3, interazione H1, instabilità flesso-torsionale, torsione nei tubi), controventi con progettazione in capacità secondo AISC 341, travi composte AISC 360 ed EN 1994-1-1, computi con costo e CO₂ per paese, sensibilità al prezzo, riuso di profili e una API REST. Dipendenze: `numpy`, `scipy`, `numba`, `pydantic`.

[![CI](https://github.com/jmurgass99/paretosteel/actions/workflows/ci.yml/badge.svg)](https://github.com/jmurgass99/paretosteel/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

## Quale problema risolve

Nel predimensionamento di una struttura in acciaio quasi tutte le decisioni sono di catalogo: quale profilo è il più leggero che resiste a un momento, quale serie conviene per una colonna, quanto pesa e costa la struttura, quanto cambia se l'acciaio aumenta del 20 %. Gli strumenti di «ottimizzazione» di solito nascondono due cose: che con un catalogo di alcune centinaia di profili l'enumerazione è esatta e più economica di un algoritmo evolutivo, e che un fronte di Pareto peso–costo non esiste se il costo è il peso per una tariffa. `paretosteel` risponde a queste domande con il metodo in vista e ogni esempio confronta il risultato dell'ottimizzatore con una ricerca esaustiva o con un calcolo a mano.

**Usalo quando**

- ti serve il profilo più leggero di un catalogo (W AISC, IPE, HEA, HEB, HSS, HP) che verifichi flessione, taglio, freccia o compressione centrata con le formule di AISC 360 o EN 1993-1-1;
- vuoi assegnare profili a gruppi di aste con minimi di inerzia e area, o esplorare un fronte di Pareto quando il costo al kg cambia tra le alternative;
- devi verificare a mano un'interazione H1 con B1, un'instabilità flesso-torsionale secondo EN 1993-1-1, la torsione di un tubo o un controvento a V rovescia con il carico sbilanciato della AISC 341;
- predimensioni una trave composta di solaio su lamiera grecata con AISC 360 o con EN 1994-1-1;
- vuoi computare la struttura (tonnellate, costo, CO₂) e vedere la sensibilità al prezzo dell'acciaio o abbinare profili recuperati.

**Non usarlo per**

- il calcolo di progetto: non c'è analisi strutturale, le domande le fornisce chi chiama, l'instabilità flesso-torsionale dei selettori è approssimata ed entra solo se si dà `L_b_m`, e non verificano l'instabilità locale delle sezioni snelle (§E7) né la flesso-torsione;
- ottenere un compromesso costo–CO₂: `pareto_lca` e `pareto_weight_cost` restituiscono sempre un unico punto (vedi gli esempi);
- travi alveolari: il modulo `castellated` è sperimentale e usa un fattore fisso di 0,85;
- AS 4100: il ramo «AU» di `design_codes` è la curva AISC;
- prezzi o fattori di CO₂ reali: le tabelle del pacchetto sono illustrative e non coincidono tra loro.

## Installazione

```bash
pip install git+https://github.com/jmurgass99/paretosteel.git
```

Extra: `api` (FastAPI, uvicorn, httpx), `memos` (handcalcs; senza di esso la relazione esce con un LaTeX manuale equivalente), `test`; `perf` è nominale perché numba è già obbligatoria. Per lo sviluppo: `git clone`, `pip install -e ".[test,api]"`, `pytest -q` (42 file di test; `tests/test_examples.py` esegue i 33 esempi come sottoprocessi). Su Windows, se la console non è UTF-8, esegui gli esempi con `python -X utf8 examples/<nome>.py`. Gli esempi che scrivono file (relazioni) lo fanno in `examples/out/`, che non è versionata; il loro output di console è in `examples/output/`.

## Capacità

| Capacità | Moduli | Norma o riferimento | Casi d'uso |
|---|---|---|---|
| Cataloghi, computi e costo: base AISC v16 inclusa con conversione in SI, catalogo unificato W + EN confrontato con essa, filtri per famiglia, inerzia e modulo plastico, computo con tonnellate, costo per paese e CO₂, due tabelle di prezzi | `catalogs`, `catalogs_aisc_full`, `catalog_unified`, `boq`, `cost_by_country`, `cost_lca`, `deflection` | AISC Shapes Database v16.0; EN 10365 | [5 casi](#1-cataloghi-computi-e-costo) |
| Motori di ottimizzazione: algoritmo genetico per gruppi, NSGA-II generico, ordinamento non dominato puro e Numba, fronte di Pareto e distanza di affollamento, Kriging | `genetic`, `nsga2`, `nsga2_jit`, `_nsga2_fast`, `pareto`, `surrogate` | Deb et al. (2002) | [5 casi](#2-motori-di-ottimizzazione) |
| Selettori di travi e colonne: enumerazione con fronte (peso, rapporto), servizi sulla base AISC v16, evoluzione differenziale con interazione H1, relazione di giustificazione | `beam_selector`, `services`, `diff_evolution`, `memos` | AISC 360-16 §E3, §F2.1, §G2.1, §H1.1; EN 1993-1-1 §6.2.5 | [5 casi](#3-selettori-di-travi-e-colonne-e-relazioni) |
| Costo, carbonio, sensibilità e riuso: «Pareto» costo–CO₂ con NSGA-II, scansione α peso–costo, punti di scambio e prezzo di pareggio, Monte Carlo P10/P50/P90, abbinamento di profili recuperati | `pareto_lca`, `diff_evolution`, `price_sensitivity`, `price_sensitivity_v2`, `reuse` | — | [5 casi](#4-costo-carbonio-sensibilità-e-riuso) |
| Verifiche di aste e controventi: instabilità flesso-torsionale, interazione biassiale con B1, sezione semicompatta dell'EC3 di seconda generazione, torsione negli HSS, involucri per norma, diagonali a croce e a V con resistenze attese, shear lag e fazzoletto | `design_codes`, `ec3_2022_2g`, `aisc360_22_hss`, `bracing` | EN 1993-1-1 §6.3.1, §6.3.2; AISC 360-16 §D3, §E3, §H1, §H3, App. 8; AISC 341-16 §F2 | [7 casi](#5-verifiche-di-aste-e-controventi) |
| Travi composte, alveolari e integrazione: ottimizzatore di travi composte AISC ed EC4, pioli e connessione parziale della EN 1994-1-1, trave alveolare sperimentale, API REST, ponte con il modello canonico e stato di calcolo chiuso per impostazione predefinita | `composite_optimizer`, `_composite`, `castellated`, `api`, `section_bridge`, `_common` | AISC 360-16 cap. I; EN 1994-1-1 §5.4.1.2, §6.2.1, §6.6 | [6 casi](#6-travi-composte-alveolari-e-integrazione) |

I 33 script di `examples/` sono stati eseguiti in un ambiente pulito prima della pubblicazione; il loro output è in `examples/output/` ed è quello riprodotto qui. Quasi tutti confrontano il risultato del pacchetto con un calcolo a mano o con una ricerca esaustiva scritta all'interno dell'esempio stesso.

## Casi d'uso

Gli output sono riportati esattamente come li stampano gli script, in spagnolo.

### 1. Cataloghi, computi e costo

#### Base AISC v16: conteggio per famiglia, conversione in SI del W14X90 a mano e un profilo per designazione

<details><summary>Output reale di <code>python examples/aisc_v16_catalog_load_unit_conversion_w14x90_hand_check_and_family_counts.py</code></summary>

```text
AISC v16 empaquetado: 2299 perfiles con peso, área e Ix
  HSS 714, 2L 639, W 289, WT 289, L 137, PIPE 51, MC 40, C 32, S 28, ST 28, HP 22, M 16, MT 14

W14X90 en el CSV: W = 90.0 lb/ft, A = 26.5 in², d = 14 in, Ix = 999.0 in⁴, Iy = 362.0 in⁴
  magnitud         a mano    paquete     dif.
  masa [kg/m]      133.93     133.92 -0.0110%
  A [cm²]          170.97     170.97 +0.0000%
  d [mm]           355.60     355.60 +0.0000%
  Ix [cm⁴]       41581.52   41581.38 -0.0003%
  Iy [cm⁴]       15067.58   15067.53 -0.0003%
  Máxima diferencia 0.0110%: el paquete usa 1,488 kg/m por lb/ft y 4,1623e-7 m⁴ por in⁴ (exactos: 1.48816 y 4.1623143e-07).

all_profiles(): 1113 perfiles, designaciones repetidas: 0
  Copia manual de catalogs.CATALOG_AISC_W frente a la base AISC v16 (la que queda en all_profiles):
  W14X90  Ix  41600 →  41581 cm⁴ (-0.0%)   Iy  15000 →  15068 cm⁴ (+0.5%)
  W14X74  Ix  33400 →  33090 cm⁴ (-0.9%)   Iy   5660 →   5577 cm⁴ (-1.5%)
  W14X61  Ix  26600 →  26639 cm⁴ (+0.1%)   Iy   4500 →   4454 cm⁴ (-1.0%)
  W12X65  Ix  22100 →  22185 cm⁴ (+0.4%)   Iy   7160 →   7242 cm⁴ (+1.2%)
  W12X53  Ix  17500 →  17690 cm⁴ (+1.1%)   Iy   3910 →   3987 cm⁴ (+2.0%)
  W10X45  Ix  10400 →  10323 cm⁴ (-0.7%)   Iy   2160 →   2223 cm⁴ (+2.9%)
  W10X33  Ix   7080 →   7118 cm⁴ (+0.5%)   Iy   1520 →   1523 cm⁴ (+0.2%)
  W8X31   Ix   4240 →   4579 cm⁴ (+8.0%)   Iy   1540 →   1544 cm⁴ (+0.3%)
  W8X24   Ix   3410 →   3442 cm⁴ (+0.9%)   Iy    707 →    762 cm⁴ (+7.7%)
  La mayor discrepancia en Ix es la de W8X31 (+8.0%); los optimizadores usan ya el valor de la base AISC.
```

</details>

#### Catalogo unificato: i dodici W rispetto alla base AISC v16 e fattore di forma dei profili EN

<details><summary>Output reale di <code>python examples/unified_catalog_w_sections_cross_checked_against_aisc_v16_and_en_section_moduli_sanity.py</code></summary>

```text
W del catálogo unificado frente a la base AISC v16 (diferencia relativa)
  perfil        A       d      bf      Ix      Iy
  W12X26   -0.11%  +0.04%  +0.09%  +0.10%  -0.01%
  W14X30   -0.17%  +0.14%  +0.03%  -0.02%  +0.02%
  W16X40   -0.04%  +0.15%  +0.11%  -0.00%  -0.24%
  W18X35   +0.07%  -0.13%  -0.26%  +0.01%  +0.03%
  W21X44   +0.03%  -0.15%  -0.06%  -0.02%  -0.19%
  W24X55   -0.02%  -0.07%  -0.03%  -0.00%  -0.10%
  W12X35   +0.07%  +0.16%  +0.23%  +0.06%  +0.02%
  W14X68   -0.02%  +0.11%  +0.39%  +0.03%  -0.01%
  W16X45   -0.01%  +0.26%  +0.10%  -0.00%  -0.02%
  W18X50   -0.04%  -0.04%  -0.26%  +0.00%  -0.01%
  W21X62   -0.05%  -0.07%  -0.14%  +0.02%  -0.01%
  W24X76   -0.01%  -0.01%  -0.15%  +0.01%  +0.00%
  Peor discrepancia en las cinco magnitudes: W14X68 +0.39% (tests/test_correcciones_1_1_0.py exige ≤ 0,5 % en A, Ix e Iy).

Perfiles EN: factor de forma Zx/Sx y Ix/(A·h²/4)
  perfil   Zx/Sx  Ix/(A·h²/4)
  IPE200   1.132        0.682
  IPE300   1.127        0.690
  IPE400   1.130        0.684
  HEA200   1.104        0.760
  HEA300   1.098        0.772
  HEB300   1.114        0.750
  IPE270   1.128        0.692
  IPE330   1.127        0.691
  IPE360   1.127        0.691
  IPE450   1.135        0.675
  HEB200   1.127        0.729
  HEB260   1.118        0.746
  HEB360   1.118        0.738
  HEB400   1.121        0.729
  HEA240   1.104        0.764
  HEA360   1.104        0.757
  HEA450   1.110        0.740
  HEA500   1.112        0.734
  Zx/Sx entre 1.098 y 1.135: ninguno fuera de [1,05; 1,20], el rango de un I o H laminado en flexión fuerte.

El catálogo unificado tiene 12 W y 18 perfiles EN; no hay UC/UB ni perfiles soldados.
```

</details>

#### Profilo più leggero per uno Zx e un'inerzia richiesti, rispetto alla ricerca esaustiva

<details><summary>Output reale di <code>python examples/catalog_filters_lightest_section_for_required_zx_and_min_ix_by_family_brute_force.py</code></summary>

```text
Viga de 7.5 m: M_Ed = 42.0·7.5²/8 = 295.3 kN·m → Zx ≥ 832 cm³; flecha L/300 con q_k = 30.0 kN/m → I ≥ 23542 cm⁴

Perfil más ligero que cumple Zx y además I (catálogo unificado):
  EN     solo resistencia: IPE360  (A   72.7 cm², Zx  1019, Ix  16270)  | resistencia + flecha: IPE450  (Ix  33740)
  ASTM   solo resistencia: W18X35  (A   66.5 cm², Zx  1090, Ix  21230)  | resistencia + flecha: W21X44  (Ix  35080)
  ambos  solo resistencia: W18X35  (A   66.5 cm², Zx  1090, Ix  21230)  | resistencia + flecha: W21X44  (Ix  35080)
  find_lightest coincide con la búsqueda exhaustiva en los tres casos.

filter_profiles por familia con I ≥ I_req (catálogo global SteelProfile, m⁴):
  IPE     2 candidatos; el más ligero IPE450     77.6 kg/m, Ix   33700 cm⁴
  HEB     3 candidatos; el más ligero HEB300    117.0 kg/m, Ix   25200 cm⁴
  W     224 candidatos; el más ligero W18X40     59.5 kg/m, Ix   25473 cm⁴

Ojo: filter_profiles solo mira Ix y A; la resistencia (Zx) y el pandeo lateral no entran en ese filtro.
```

</details>

#### Computo di un telaio a due piani: tonnellate a mano, costo e CO₂ in quattro paesi

<details><summary>Output reale di <code>python examples/steel_boq_two_storey_frame_ipe_heb_w_tonnage_cost_and_co2_by_country_hand_check.py</code></summary>

```text
Medición — Spain, fase 'erected', tarifa 3750 USD/t, 1.8 kg CO₂/kg
  perfil     L [m]  A [cm²]    kg/m       t       USD   t CO₂
  HEB240     56.00   106.00   83.20   4.659     17472    8.39
  IPE360     72.00    72.70   57.07   4.109     15409    7.40
  IPE 240    40.00    39.12   30.70   1.228      4605    2.21
  W8X31      27.78    58.90   46.13   1.282      4806    2.31
  TOTAL     195.78                   11.278     42292   20.30

A mano: Σ L·A·7850 (EN) + Σ L·masa AISC (W) = 11.2779 t; función: 11.2779 t (+0.00e+00)

Misma medición en cuatro países (fase montado):
  ES Spain       3750 USD/t →     42292 USD,  20.30 t CO₂
  DE Germany     3800 USD/t →     42856 USD,  18.61 t CO₂
  US USA         3500 USD/t →     39473 USD,  19.74 t CO₂
  CL Chile       2800 USD/t →     31578 USD,  20.86 t CO₂
  Las toneladas no cambian (11.278 t); el coste va de 31578 (CL) a 42856 USD (DE), +36%, solo por la tarifa.
  España por fase: materia prima 18608, fabricado 32142, montado 42292 USD.
```

</details>

#### Le due tabelle di prezzi del pacchetto a confronto e il peso del processo produttivo sulla CO₂

<details><summary>Output reale di <code>python examples/cost_tables_cost_by_country_vs_cost_lca_rates_and_embodied_co2_for_a_25_t_structure.py</code></summary>

```text
Estructura de 25 t: coste según las dos tablas del paquete [USD]
  país    bruto  fabricado   montado |  cost_lca  cost_lca/bruto
  CL      35000      55000     70000 |     36250            +4%
  CO      32500      52500     67500 |     37500           +15%
  US      40000      67500     87500 |     27500           -31%
  DE      42500      72500     95000 |     26250           -38%
  ES      41250      71250     93750 |     27500           -33%
  SG      37500      62500     82500 |     32500           -13%  (sin fila: DEFAULT)
  AU      41250      70000     92500 |     32500           -21%  (sin fila: DEFAULT)
  PE      33750      53750     68750 |     33750            +0%
  CN      21250      36250     48750 |     21250            +0%
  MX      32500      52500     67500 |     32500            +0%
  La mayor discrepancia entre «cost_lca» y el precio bruto de «cost_by_country» es DE (-38%). Un mismo proyecto da cifras distintas según el módulo que se use.

CO₂ incorporado de 25 t por ruta de fabricación (cost_lca) y por país (cost_by_country):
  low_carbon      0.40 t CO₂/t →  10.0 t CO₂
  secondary_EAF   0.60 t CO₂/t →  15.0 t CO₂
  average_global  1.85 t CO₂/t →  46.2 t CO₂
  primary_BF      2.20 t CO₂/t →  55.0 t CO₂
  Por país el factor va de 1.65 a 2.10 (×1.27); por ruta, de 0.40 a 2.20 (×5.5). La ruta de fabricación mueve el CO₂ más que el país de compra.
```

</details>

### 2. Motori di ottimizzazione

#### Algoritmo genetico per gruppi rispetto all'enumerazione esaustiva, con cinque semi

<details><summary>Output reale di <code>python examples/genetic_algorithm_three_member_groups_min_ix_min_area_vs_exhaustive_enumeration_and_seeds.py</code></summary>

```text
Óptimo por enumeración exhaustiva (perfil más ligero que cumple en cada grupo):
  vigas                7 candidatos,    2 cumplen → IPE450           77.6 kg/m ×   120 m =    9312 kg
  pilares              5 candidatos,    4 cumplen → HEB240           83.2 kg/m ×    60 m =    4992 kg
  arriostramientos   714 candidatos,  568 cumplen → HSS5X2-1/2X1/4   16.9 kg/m ×    80 m =    1352 kg
  Peso mínimo: 15656 kg

GA (población 40, 40 generaciones) con cinco semillas:
  semilla  peso [kg]  vs óptimo  penal.  asignación
        1      15680     +0.15%       0  vigas=IPE450, pilares=HEB240, arriostramientos=HSS10X4X1/8
        2      15680     +0.15%       0  vigas=IPE450, pilares=HEB240, arriostramientos=HSS7X7X1/8
        3      15757     +0.65%       0  vigas=IPE450, pilares=HEB240, arriostramientos=HSS6X2X1/4
        4      15656     +0.00%       0  vigas=IPE450, pilares=HEB240, arriostramientos=HSS5X2-1/2X1/4
        5      15729     +0.46%       0  vigas=IPE450, pilares=HEB240, arriostramientos=HSS6X4X3/16

Semillas que dan el óptimo exacto: 1 de 5; la peor queda a +0.65%.
Aciertos por grupo: vigas 5/5, pilares 5/5, arriostramientos 1/5 (tamaño del catálogo: IPE 7, HEB 5, HSS 714).
Para grupos independientes la enumeración es exacta y más barata; el GA solo compensa cuando el coste de un grupo depende de lo que se elige en los demás.
```

</details>

#### NSGA-II su Schaffer e ZDT1: convergenza al fronte analitico e tratto coperto

<details><summary>Output reale di <code>python examples/nsga2_engine_schaffer_and_zdt1_benchmarks_front_vs_analytical_solution_and_coverage.py</code></summary>

```text
Schaffer N.1 (población 40, 60 generaciones)
  40/40 individuos en el conjunto de Pareto x ∈ [0, 2]; x de 0.0018 a 1.9981
  máximo |f2 − (√f1 − 2)²| = 0.00e+00  → la población final está sobre el frente analítico

ZDT1, 4 variables (población 80, 300 generaciones)
  semilla kernel  t [s] frente dist. media      f1 cubierto
        1   puro   4.56     80      0.0006   0.000 – 0.216
        1  numba   0.50     80      0.0006   0.000 – 0.216
          los dos kernels dan la misma población final: sí
        2  numba   0.31     80      0.0014   0.000 – 0.403
        3  numba   0.30     80      0.0014   0.000 – 0.412

En ZDT1 la población converge al frente (distancia media ≤ 0.0014) pero solo cubre entre el 22% y el 41% del tramo f1 ∈ [0, 1]: el cruce convexo no extrapola y la mutación del 1 % no recupera los extremos. Para frentes de catálogo, que son discretos y pequeños, el paquete enumera (beam_selector, composite_optimizer) en vez de evolucionar.
```

</details>

#### Ordinamento non dominato: Python puro e i due kernel Numba danno gli stessi ranghi

<details><summary>Output reale di <code>python examples/non_dominated_sorting_pure_python_vs_numba_kernels_identical_fronts_and_timing.py</code></summary>

```text
      N  M frentes  |F0|  puro [ms]  fast [ms]  jit [ms]  iguales
    200  2      22     7       16.7       0.41      0.31       sí
    400  2      38     4       83.6       1.33      1.13       sí
    400  3      13    22       81.9       1.43      1.55       sí
    800  3      20    26      335.5       5.72      5.88       sí

Rangos idénticos en las tres implementaciones: sí; el kernel `fast` es entre 41 y 63 veces más rápido que el puro.
Distancia de apiñamiento de un frente de cuatro puntos: [1000000000.0, 1.25, 1.25, 1000000000.0] (a mano: extremos 1e9, interiores 1,25 y 1,25); el punto (4,4) tiene rango 1.
```

</details>

#### Fronte peso–costo di sei travi il cui costo al kg cambia, e distanza di affollamento a mano

<details><summary>Output reale di <code>python examples/pareto_front_weight_vs_cost_six_floor_beam_alternatives_and_crowding_distance_hand_check.py</code></summary>

```text
Alternativas para una viga de 9 m:
  IPE450 S275               698.4 kg     768 USD  (1.10 USD/kg)
  IPE400 S355               596.7 kg     704 USD  (1.18 USD/kg)
  IPE360 S460               513.9 kg     719 USD  (1.40 USD/kg)
  HEA360 S275              1008.0 kg    1109 USD  (1.10 USD/kg)
  armada 500x200 S355       549.0 kg     950 USD  (1.73 USD/kg)
  alveolar ex-IPE300 S355   379.8 kg     733 USD  (1.93 USD/kg)

Frente de Pareto (3 de 6, coincide con la fuerza bruta), ordenado por peso:
  alveolar ex-IPE300 S355   379.8 kg     733 USD
  IPE360 S460               513.9 kg     719 USD
  IPE400 S355               596.7 kg     704 USD
Dominadas: IPE450 S275 (por alveolar ex-IPE300 S355); HEA360 S275 (por alveolar ex-IPE300 S355); armada 500x200 S355 (por alveolar ex-IPE300 S355)

Distancia de apiñamiento del frente: alveolar ∞, IPE360 2.000, IPE400 ∞
  A mano para IPE360 S460: Δpeso/rango + Δcoste/rango = 2.000 (función 2.000); los extremos llevan ∞ para que el frente conserve su amplitud.

La más ligera (alveolar ex-IPE300 S355, 380 kg) cuesta +4% más que la más barata (IPE400 S355, 597 kg): esa es la decisión que el frente deja al proyectista.
```

</details>

#### Kriging adattato alla curva di instabilità AISC: interpolazione e perché non estrapolare

<details><summary>Output reale di <code>python examples/kriging_surrogate_fit_of_aisc_e3_column_curve_vs_exact_and_extrapolation_warning.py</code></summary>

```text
longitud 0.10: error máximo 0.0607 (en KL/r = 27), medio 0.0087 sobre Fcr/Fy
longitud 0.25: error máximo 0.0019 (en KL/r = 173), medio 0.0004 sobre Fcr/Fy
longitud 0.50: error máximo 0.0016 (en KL/r = 124), medio 0.0007 sobre Fcr/Fy

Longitud 0,25 — predicción frente a la curva exacta:
   KL/r  exacto  Kriging
   25.0  0.9553   0.9553
   60.0  0.7685   0.7684
  100.0  0.4812   0.4811
  113.4  0.3903   0.3890
  140.0  0.2560   0.2560
  175.0  0.1638   0.1622
  Fuera del rango muestreado:
    0.0  1.0000   0.9836
  200.0  0.1254   0.1559
  260.0  0.0742   0.1058

En KL/r = 400 el Kriging predice 0.0000 (exacto 0.0314): con media nula la predicción decae hacia 0 al alejarse de los datos. Úsalo solo para interpolar dentro del muestreo.
```

</details>

### 3. Selettori di travi e colonne e relazioni

#### M_u = 320 kN·m e V_u = 180 kN: W18X35 verificato a mano e con forza bruta, e l'alternativa EN

<details><summary>Output reale di <code>python examples/beam_selector_unified_catalog_m320_v180_lightest_w18x35_phi_zx_fy_hand_check_and_brute_force.py</code></summary>

```text
Demanda M_u = 320.0 kN·m, V_u = 180.0 kN, Fy = 345.0 MPa, LRFD
  30 perfiles evaluados, 19 factibles; frente de Pareto (peso, ratio M): W16X40, W18X35, W21X44, W24X55, W18X50, W21X62, W24X76, IPE450, HEA500
  perfil     kg/m     φMn  M/φMn    φVn  V/φVn
  W18X35     52.2   338.4  0.946  635.7  0.283
  W16X40     59.7   371.4  0.862  583.8  0.308
  W21X44     65.9   484.4  0.661  870.5  0.207
  IPE400     66.3   405.8  0.789  640.9  0.281
  W16X45     67.4   418.9  0.764  672.2  0.268
  W18X50     74.4   513.9  0.623  766.3  0.235

Seleccionado W18X35: a mano φMn = 0,9·1090e3·345/1e6 = 338.4 kN·m (función 338.4), ratio 0.9455
  φVn = 0,9·0,6·345·449·7.6 /1e3 = 635.7 kN (función 635.7); masa = 66.5e-4·7850 = 52.2 kg/m
  Fuerza bruta (mínima área con φMn ≥ M_u y φVn ≥ V_u): W18X35 → coincide con el selector.

Solo EN, S355, code='EU': IPE360 (57.1 kg/m), M_pl,Rd = 1019e3·355/1e6 = 361.7 kN·m (función 361.7), ratio 0.885
  El W elegido pesa 52.2 kg/m frente a 57.1 kg/m del EN (+9%); el cortante usa φv = 0,90 también en 'EU' (simplificación).
```

</details>

#### Trave di 7 m sui 289 W AISC: flessione elastica, freccia L/360 e i dati che il servizio non verifica

<details><summary>Output reale di <code>python examples/aisc_v16_w_beam_optimizer_elastic_sx_flexure_and_deflection_l360_hand_check_7_m_span.py</code></summary>

```text
L = 7.0 m, M_Ed = 250.0 kN·m, w_servicio = 18.0 kN/m, límite L/360 = 19.44 mm
  → W18X35: 52.1 kg/m, φMn = 293.2 kN·m (85.3%), δ = 13.25 mm; 39 perfiles probados

A mano para W18X35: Sx = Ix/(d/2) = 2.1228e-04/0.2248 = 944 cm³; φMn = 0,9·345·Sx = 293.2 kN·m
  δ = 5·18.0·7000⁴/(384·200000·2.1228e+08) = 13.25 mm
  Los 38 W más ligeros fallan por: flexión 1, flecha 0, las dos 37

Sin flecha relevante el perfil sería el mismo (W18X35): gobierna la flexión.
Con V_Ed = 150 kN: W18X35 — el mismo perfil: el cortante no gobierna.
Con V_Ed = 5000 kN: <NONE_FEASIBLE> — ningún W de la base resiste ese cortante (φVn = 0,9·0,6·Fy·d·tw).
Sin w_service: W18X35 — la flecha se evalúa con la carga por defecto de 10 kN/m (δ = 7.36 mm), no con la carga de servicio real.
```

</details>

#### Colonna da 1500 kN in W, HP e HSS a 4 e 9 m, e la snellezza di parete del tubo scelto

<details><summary>Output reale di <code>python examples/aisc_e3_column_optimizer_w_hp_hss_families_4_m_1500_kn_fcr_hand_check_and_slenderness.py</code></summary>

```text
Límite inelástico/elástico 4,71·√(E/Fy) = 113.4

L = 4.0 m, P_u = 1500.0 kN
  familia perfil             kg/m   KL/r      Fe    Fcr     φPn  a mano rama      
  W       W8X40              59.5   76.9   334.0  223.9  1521.1  1521.1 inelástico
  HP      HP10X42            62.5   65.5   460.2  252.1  1815.0  1815.0 inelástico
  HSS     HSS12X12X3/16      44.4   32.7  1845.8  319.0  1509.8  1509.8 inelástico
  Más ligero: HSS12X12X3/16 (HSS, 44.4 kg/m); el W elegido pesa +34% respecto a él.
  HSS12X12X3/16: b/t = 65.8 frente a λr = 33.7 → pared ESBELTA: §E7 reduciría φPn y el servicio no lo comprueba

L = 9.0 m, P_u = 1500.0 kN
  familia perfil             kg/m   KL/r      Fe    Fcr     φPn  a mano rama      
  W       W12X72            107.1  116.6   145.3  127.4  1561.2  1561.2 elástico  
  HP      HP14X73           108.6  101.5   191.8  162.5  2018.8  2018.8 inelástico
  HSS     HSS16.000X0.250    62.6   63.4   490.8  257.1  1716.5  1716.5 inelástico
  Más ligero: HSS16.000X0.250 (HSS, 62.6 kg/m); el W elegido pesa +71% respecto a él.
  HSS16.000X0.250: D/t = 68.8 frente a λr = 63.8 (límite D/t sin contrastar) → pared ESBELTA: §E7 reduciría φPn y el servicio no lo comprueba

A 9 m todas las familias necesitan un perfil más pesado que a 4 m. El HSS tiene el mismo radio de giro en los dos ejes y por eso gana en compresión centrada, pero los HSS elegidos por peso son de pared esbelta: sin la comprobación de §E7 esa ventaja no está demostrada.
```

</details>

#### Evoluzione differenziale per trave e colonna con momento rispetto alla ricerca esaustiva

<details><summary>Output reale di <code>python examples/differential_evolution_beam_and_column_with_moment_vs_exhaustive_catalog_search_h1_interaction.py</code></summary>

```text
Viga biapoyada (familias IPE y W), L = 8 m, w = 25 kN/m
  IPE DE: IPE450     77.6 kg/m  M 0.430  V 0.109  δ  19.8/22.2 mm | exhaustiva: IPE450   = DE (7 perfiles)
  W   DE: W21X44     65.5 kg/m  M 0.483  V 0.128  δ  19.0/22.2 mm | exhaustiva: W21X44   = DE (289 perfiles)

Pilar W, H = 4 m, K = 1, P = 900 kN
  M =   0.0 kN·m  DE: W8X31      46.1 kg/m  P/φPn 0.769  H1     —  factible True | exhaustiva: W8X31    = DE (H1 a mano 0.769)
  M =  60.0 kN·m  DE: W10X39     58.0 kg/m  P/φPn 0.621  H1 0.870  factible True | exhaustiva: W10X39   = DE (H1 a mano 0.870)
  M = 150.0 kN·m  DE: W21X48     71.4 kg/m  P/φPn 0.617  H1 0.899  factible True | exhaustiva: W21X48   = DE (H1 a mano 0.899)

Peso del pilar con M = 0, 60 y 150 kN·m: 46.1, 58.0 y 71.4 kg/m (crece con el momento: gobierna la interacción H1). φMn usa Sx (elástico) y no considera pandeo lateral: resultado de predimensionado.
```

</details>

#### Relazione di giustificazione con gli stessi rapporti del selettore, e una freccia che il selettore non guarda

<details><summary>Output reale di <code>python examples/profile_justification_memo_from_selector_same_ratios_latex_engine_and_unverified_deflection.py</code></summary>

```text
Selector: W18X35, M/φMn = 0.9455, V/φVn = 0.2831
Memoria : W18X35, flexión 0.9455, cortante 0.2831, flecha 1.130 → NO CUMPLE
  Ratios iguales a los del selector: sí; motor LaTeX: handcalcs
  Flecha a mano: 5·20·8000⁴/(384·200000·2.1230e+08) = 25.12 mm frente a L/360 = 22.22 mm → ratio 1.130
  Escritas out/memo_W18X35.md (51 líneas) y .tex (642 caracteres)
  La memoria dice NO CUMPLE por flecha: beam_selector solo mira resistencia; con 20 kN/m de servicio en 8 m el W18X35 no llega a L/360 y hay que subir de perfil.

Sin carga de servicio: NO CUMPLE — «- **delta / delta_lim = inf** -- NO VERIFICADA (sin carga de servicio)»

justificar (AISC H1): W12X65 con P_u = 900 kN, M_u = 160 kN·m, V_u = 60 kN; Mn = Zx·Fy = 1590e3·345, Vn = 0,6·Fy·d·tw, Pn = 3200 kN (supuesto, de un cálculo E3 previo)
  P/φPn = 0.312, M/φMn = 0.324; H1-1a a mano 0.312 + 8/9·0.324 = 0.601 (función 0.601) → CUMPLE
  Mismo caso sin Pn (capacidad axial ausente): P/φPn = inf, NO CUMPLE (en 1.0.0 un Pn ausente daba P/φPn = 0 y la barra «cumplía» a axil).
```

</details>

### 4. Costo, carbonio, sensibilità e riuso

#### «Fronte» costo–CO₂ con NSGA-II: un unico punto, dimostrato enumerando le 35 combinazioni

<details><summary>Output reale di <code>python examples/pareto_cost_vs_co2_nsga2_two_groups_collapses_to_minimum_weight_brute_force_proof.py</code></summary>

```text
NSGA-II (40 × 30): 1 solución(es) en el frente
  {'vigas': 'IPE450', 'pilares': 'HEB240'}    14304 kg     17746 USD   23.48 t CO₂  factible=True

Enumeración: 35 combinaciones, 8 factibles, 1 no dominada(s):
  ('IPE450', 'HEB240')    14304 kg     17746 USD   23.48 t CO₂
  La combinación más ligera factible es ('IPE450', 'HEB240'); NSGA-II, enumeración y mínimo peso coinciden.
  La siguiente más ligera ('IPE500', 'HEB240') cuesta +2279 USD y emite +3.46 t CO₂: empeora las dos cosas a la vez.

Para que haya compromiso coste–CO₂ la decisión tiene que incluir la procedencia o la ruta de fabricación de cada grupo (p. ej. EAF más caro pero con menos CO₂); `pareto_lca` no la incluye.
```

</details>

#### Scansione α peso–costo con evoluzione differenziale: il costo è il peso per la tariffa

<details><summary>Output reale di <code>python examples/pareto_weight_cost_de_alpha_sweep_single_point_front_because_cost_is_weight_times_rate.py</code></summary>

```text
IPE en ES (1100 USD/t): 1 solución(es) distinta(s) en 11 valores de α; frente = IPE450 (621 kg, 683 USD)
  coste/peso = 1100 USD/t, la tarifa del país (1100): el coste no aporta información nueva
  Exhaustiva: IPE450 (77.6 kg/m); optimize_beam_de: IPE450 (77.6 kg/m) → los tres coinciden.
W en US (1100 USD/t): 1 solución(es) distinta(s) en 11 valores de α; frente = W21X44 (524 kg, 576 USD)
  coste/peso = 1100 USD/t, la tarifa del país (1100): el coste no aporta información nueva
  Exhaustiva: W18X40 (59.5 kg/m); optimize_beam_de: W21X44 (65.5 kg/m) → la DE se queda +10.0% por encima del óptimo exhaustivo.

Un frente peso–coste solo tiene sentido si el coste por kg cambia entre alternativas (grado, fabricación, conexiones), como en el ejemplo pareto_front_weight_vs_cost_*.
```

</details>

#### Tre soluzioni di copertura: quale è la più economica secondo il prezzo dell'acciaio e i prezzi di pareggio

<details><summary>Output reale di <code>python examples/price_sensitivity_sweep_switch_points_and_break_even_factor_three_alternatives_hand_check.py</code></summary>

```text
     f   A laminados  B alveolares     C celosía   más barata
   0.5         11700         14225         16300   A laminados
   0.6         14040         16110         17860   A laminados
   0.7         16380         17995         19420   A laminados
   0.8         18720         19880         20980   A laminados
   0.9         21060         21765         22540   A laminados
   1.0         23400         23650         24100   A laminados
   1.1         25740         25535         25660   B alveolares
   1.2         28080         27420         27220   C celosía
   1.3         30420         29305         28780   C celosía
   1.4         32760         31190         30340   C celosía
   1.5         35100         33075         31900   C celosía
   1.6         37440         34960         33460   C celosía
   1.7         39780         36845         35020   C celosía
   1.8         42120         38730         36580   C celosía
   1.9         44460         40615         38140   C celosía
   2.0         46800         42500         39700   C celosía

Cambios de la más barata en f = [1.1, 1.2]; elección «robusta» (gana en más factores): C celosía

Precios de equilibrio (factor sobre 1300 USD/t):
  A laminados = B alveolares: f* = 1.0549 (a mano 1.0549) → 1371 USD/t; por encima gana la de menos acero
  B alveolares = C celosía: f* = 1.1385 (a mano 1.1385) → 1480 USD/t; por encima gana la de menos acero
  A laminados = C celosía: f* = 1.0897 (a mano 1.0897) → 1417 USD/t; por encima gana la de menos acero

La barrida es discreta (paso 0,1): los cambios se dan en el primer factor de la rejilla tras el equilibrio exacto, que es el que da break_even_price.
```

</details>

#### Monte Carlo di acciaio, montaggio e trasporto rispetto alla forma chiusa della somma di normali

<details><summary>Output reale di <code>python examples/monte_carlo_steel_erection_transport_prices_p10_p50_p90_vs_normal_closed_form.py</code></summary>

```text
Forma cerrada: μ = 254,400 USD, σ = 22,839 USD (9.0%), z90 = 1.2816
  P10 = 225,130   P50 = 254,400   P90 = 283,670

       n semilla        P10        P50        P90      media  err P90
    1000      42    224,117    255,128    284,210    254,499   +0.19%
    1000       7    224,177    254,875    283,663    254,394   -0.00%
    1000    2026    225,145    255,761    283,625    254,941   -0.02%
   20000      42    225,405    254,340    283,594    254,359   -0.03%
   20000       7    225,167    254,336    283,518    254,355   -0.05%
   20000    2026    225,424    254,300    283,759    254,446   +0.03%

Error máximo en P90: 0.19% con 1 000 muestras y 0.05% con 20 000. De la dispersión (P90 − P10 = 58,540 USD) el acero aporta el 75% de la varianza.
El modelo no limita los precios a valores positivos ni correlaciona acero y montaje; con σ grandes conviene una distribución acotada.
```

</details>

#### Riuso di profili recuperati: miglior adattamento per Wpl e CO₂ evitata

<details><summary>Output reale di <code>python examples/circular_steel_reuse_greedy_best_fit_matching_inventory_reuse_ratio_and_carbon_saved.py</code></summary>

```text
  demanda Wpl req. → perfil            Wpl  holgura  t CO₂
  V1           600 → IPE300-usado      628      +5%   0.47
  V2           450 → IPE270-usado      484      +8%   0.33
  V3          1250 → IPE400-usado     1307      +5%   0.98
  V4           800 → IPE330-usado      804      +0%   0.68
  V5          1000 → HEB240-usado     1053      +5%   0.92
  V6          1500 → sin perfil adecuado

Cubiertas 5/6; ratio de reutilización (por Wpl requerido) 73.2%; CO₂ evitado 3.39 t
Exhaustivo: como máximo se pueden cubrir 5 demandas; el voraz cubre 5 (óptimo en este caso).
Wpl suficiente no basta para reutilizar: hay que comprobar longitud, estado, grado del acero y uniones; el módulo solo empareja una capacidad escalar.
```

</details>

### 5. Verifiche di aste e controventi

#### Instabilità flesso-torsionale di una IPE300 S355 da 2 a 10 m: Mcr a mano, caso generale e metodo dei laminati

<details><summary>Output reale di <code>python examples/ec3_lateral_torsional_buckling_ipe300_s355_mcr_chi_lt_general_vs_rolled_method_spans_2_to_10_m.py</code></summary>

```text
IPE300, h/b = 2,0: caso general → curva a (α = 0.21); método laminados → curva b (α = 0.34)
M_pl,Rd = Wpl·fy/γ_M1 = 222.9 kN·m (γ_M1 = 1,0)

  L [m]    C1     Mcr  a mano  λ̄_LT χ gen.  Mb,Rd χ lam.  Mb,Rd
    2.0 1.000   505.1   505.1  0.664  0.864  192.6  0.887  197.8
    4.0 1.000   159.7   159.7  1.181  0.542  120.8  0.590  131.5
    6.0 1.000    90.5    90.5  1.570  0.345   76.8  0.399   88.9
    8.0 1.000    63.1    63.1  1.879  0.250   55.7  0.283   63.1
   10.0 1.000    48.7    48.7  2.141  0.196   43.8  0.218   48.7
    2.0 1.127   569.3   569.3  0.626  0.880  196.2  0.905  201.8
    4.0 1.127   180.0   180.0  1.113  0.587  130.9  0.631  140.6
    6.0 1.127   102.0   102.0  1.479  0.382   85.1  0.437   97.3
    8.0 1.127    71.1    71.1  1.770  0.279   62.1  0.319   71.1
   10.0 1.127    54.8    54.8  2.016  0.220   48.9  0.246   54.8

Mcr de la función frente a la fórmula a mano: diferencia máxima 3.3e-16; χ_LT del caso general coincide con chi_lt(method='general') de la librería de vigas mixtas.
En 6 m con C1 = 1: Mb,Rd = 76.8 kN·m por el caso general (curva a) y 88.9 kN·m por el método de laminados (curva b); sin arriostramiento lateral en 6 m la resistencia baja al 34% de M_pl,Rd por el caso general.
```

</details>

#### Interazione biassiale H1 con B1 su un W12X65, a mano, e cosa fanno i valori predefiniti

<details><summary>Output reale di <code>python examples/aisc_h1_beam_column_biaxial_interaction_b1_amplification_w12x65_hand_check_and_default_inputs.py</code></summary>

```text
KL/r_y = 58.7 → Fe = 573.4 MPa, Fcr = 268.2 MPa (INELASTIC) → Pn = 3299 kN
Mnx = Zx·Fy = 548.5 kN·m; Mny = min(Zy·Fy, 1,6·Sy·Fy) = min(249.4, 263.3) = 249.4 kN·m

P_u = 1100 kN, M_ux = 180, M_uy = 30 kN·m
  Pe1x = 21640 kN, Pe1y = 7057 kN (función 21640, 7057)
  B1x = 1.000, B1y = 1.185 (función 1.000, 1.185); Mry = 35.5 kN·m
  Pu/φPn = 0.370 → H1-1a; DCR a mano 0.8353, función 0.8353 → cumple

P_u = 150 kN, M_ux = 180, M_uy = 30 kN·m
  Pe1x = 21640 kN, Pe1y = 7057 kN (función 21640, 7057)
  B1x = 1.000, B1y = 1.022 (función 1.000, 1.022); Mry = 30.7 kN·m
  Pu/φPn = 0.051 → H1-1b; DCR a mano 0.5264, función 0.5264 → cumple

Sin pasar Ix, Iy ni longitudes (valores por defecto): B1y = 1.335 y DCR = 0.8531, frente a B1y = 1.185 y DCR = 0.8353 con los datos reales (+2.1%). Los valores por defecto no son del perfil: pásalos siempre.
```

</details>

#### Sezione saldata S460 di classe 3: W_ep rispetto a W_el e la scelta della curva di instabilità

<details><summary>Output reale di <code>python examples/ec3_2022_semi_compact_welded_i_section_s460_w_ep_interpolation_vs_w_el_and_buckling_curve_choice.py</code></summary>

```text
Sección 300×15 + 600×8, S460: ε = 0.7148; A = 13800 mm², W_el = 3159.3·10³ mm³, W_pl = 3487.5·10³ mm³ (W_pl/W_el = 1.104)
  ala: c/t = 138.9/15 = 9.26 → 12.96·ε (clase 2 ≤ 10, clase 3 ≤ 14)
  alma: c/t = 585.9/8 = 73.23 → 102.46·ε (clase 2 ≤ 83, clase 3 ≤ 124)
  ξ = max(0.740, 0.475) = 0.740 → W_ep = W_pl − ξ·(W_pl − W_el) = 3244.8·10³ mm³

N_cr,z = π²·E·Iz/L² = 5598 kN con Iz = 67.53·10⁶ mm⁴; N_Ed = 1500 kN, M_Ed = 900 kN·m
  curva  clase M_Rd 2022 M_Rd 2005 ganancia      χ  N_b,Rd utiliz.
  a0         3    1492.6    1453.3    2.71%  0.675    4288   0.953
  c          3    1492.6    1453.3    2.71%  0.503    3195   1.073
  M_Rd a mano: W_ep·fy = 1492.6 kN·m (función 1492.6); W_el·fy = 1453.3 kN·m

La curva por defecto a0 da χ = 0.675; la curva c de una I soldada en z–z da χ = 0.503 (-25%). Con a0 la barra cumple (utilización 0.953); con la curva c no cumple (1.073). La curva hay que pasarla siempre.
```

</details>

#### Torsione nei tubi: costante C, φTn nei tre rami e l'interazione H3-6

<details><summary>Output reale di <code>python examples/aisc_360_hss_torsional_constant_phi_tn_three_wall_branches_and_h3_6_combined_interaction_hand_check.py</code></summary>

```text
Límites de h/t: 2,45√(E/Fy) = 59.0; 3,07√(E/Fy) = 73.9
  tubo            t [mm]    h/t rama        C [cm³]   a mano     φTn  a mano
  HSS8X8X3/8        8.86   19.9 fluencia      666.4    666.4  124.16  124.16
  HSS12X12X3/16     4.43   65.8 inelástica    798.9    798.9  133.39  133.39
  HSS16X16X3/16     4.43   88.8 elástica     1431.0   1431.0  147.80  147.80
  Circular HSS8.625X0.322: C = π(D − t)²t/2 = 534.3 cm³ (función 534.3); el módulo no calcula φTn de tubos circulares (como cota, 0,9·0,6·Fy·C = 99.54 kN·m)

H3-6 en el HSS8X8X3/8 (capacidades de diseño supuestas de cálculos previos):
  Tr =  0.00 kN·m (  0% de Tc): normal 0.6494 + (V + T)² 0.0533 = 0.7026 (a mano 0.7026) → cumple
  Tr = 18.62 kN·m ( 15% de Tc): normal 0.6494 + (V + T)² 0.1450 = 0.7943 (a mano 0.7943) → cumple
  Tr = 62.08 kN·m ( 50% de Tc): normal 0.6494 + (V + T)² 0.5340 = 1.1834 (a mano 1.1834) → NO cumple
  Con Tr = 15 % de Tc AISC permitiría ignorar la torsión (umbral 20 %); el módulo la suma igualmente (del lado seguro).
```

</details>

#### Involucri per norma US/EU/AU per flessione e compressione, e il salto della curva AISC al cambio di ramo

<details><summary>Output reale di <code>python examples/code_wrappers_beam_and_column_strength_us_eu_au_and_aisc_e3_transition_continuity.py</code></summary>

```text
Flexión de sección compacta HEB300, W_pl = 1869 cm³, fy = 355 MPa:
  US: Mn = 663.5 kN·m, factor 0.90 → M_d = 597.1 kN·m
  EU: Mn = 663.5 kN·m, factor 1.00 → M_d = 663.5 kN·m
  AU: Mn = 663.5 kN·m, factor 0.90 → M_d = 597.1 kN·m

Compresión HEB300 (eje débil, iz = √(Iz/A) = 75.8 mm):
  L [m]    λc  US φPn EU Nb,Rd  AU φNc  EU/US
    2.0  0.35    4532     4901    4532  1.081
    4.0  0.69    3901     3866    3901  0.991
    6.0  1.04    3039     2748    3039  0.904
    8.0  1.38    2143     1885    2143  0.880
   10.0  1.73    1401     1329    1401  0.949
   12.0  2.07     973      977     973  1.004
  A mano en 6 m (λc = 1.036): US 0,9·0,658^λc²·Fy·A = 3039 kN; EU Φ = 1.242, χ = 0.5192 → 2748 kN
  'AU' idéntico a 'US' en todas las esbelteces probadas: sí → no es AS 4100.

AISC E3 en el cambio de rama KL/r = 4,71·√(E/Fy) = 113.40: Fcr = 134.6610 MPa (INELASTIC) y 134.6098 MPa (ELASTIC), salto relativo 3.8e-04, propio de la norma: 0,658^2,25 = 0.38995 frente a 0,877/2,25 = 0.38978.
```

</details>

#### Diagonale HSS a croce e a V rovescia: resistenze, capacità attese e carico sbilanciato sulla trave

<details><summary>Output reale di <code>python examples/hss_brace_x_and_chevron_aisc_360_compression_tension_aisc_341_expected_strengths_and_unbalanced_beam_load.py</code></summary>

```text
HSS6X6X3/8: Ag = 4890 mm², r = 58.0 mm, t_diseño = 8.86 mm
  U = 1 − (3·152.4/8)/300 = 0.809; An = Ag − 2·t·18 = 4571 mm²; Ae = 3701 mm² (Ae/Ag = 0.757)

Cruz, L = 6946 mm: KL/r en el plano 119.8, fuera 59.9 → gobierna 119.8
  Fcr = 120.6 MPa (ELASTIC; a mano 120.6); φPn = 531 kN, DCR 1.319
  Tracción: φ·Fy·Ag = 1518, φ·Fu·Ae = 1185 → φPn = 1185 kN, DCR 0.591; estado FAIL
  El módulo toma 1,0·L en el plano para la cruz (hipótesis conservadora); con la unión del cruce contando también en el plano (0,5·L en los dos ejes) sería φPn = 1168 kN y DCR 0.599.
  Esperadas: T = Ry·Fy·Ag = 2193 kN (función 2193); C = min(Ry·Fy, 1,14·Fcre)·Ag = 672 kN (función 672); esbeltez sísmica OK

V invertida, Ry = 1,3 (A500 gr. C): L = 4610 mm, θ = 49.4°, KL/r = 79.5
  T = 2193 kN, C = 1371 kN, 0,3·C = 411 kN → P_v = (T − 0,3C)·sen θ = 1353 kN (función 1353)
  Momento en la viga de 6 m: P_v·L/4 = 2030 kN·m, 22.6 veces la carga vertical del análisis elástico (60 kN)

V invertida, Ry por defecto 1,10: L = 4610 mm, θ = 49.4°, KL/r = 79.5
  T = 1856 kN, C = 1272 kN, 0,3·C = 382 kN → P_v = (T − 0,3C)·sen θ = 1119 kN (función 1119)
  Momento en la viga de 6 m: P_v·L/4 = 1679 kN·m, 18.7 veces la carga vertical del análisis elástico (60 kN)
  Con el Ry por defecto el momento de diseño de la viga sale -17%: del lado inseguro. Pasa el Ry del material.
```

</details>

#### Shear lag in angolari e W, e fazzoletto (Whitmore e fascia 2t) diretto e tramite la API

<details><summary>Output reale di <code>python examples/shear_lag_factor_u_table_d3_1_angle_and_w_sections_and_gusset_whitmore_2t_clearance_direct_and_rest.py</code></summary>

```text
Angular L4X4X1/2, 3 tornillos: U = 1 − 30.0/150 = 0.800 (caso 2); An = 2115 mm², Ae = 1692 mm² (0.699·Ag)
  Con el caso 8 (U = 0,60, sin contrastar) Ae sería 1269 mm²: el caso 2 da más.
  W10X33: bf/d = 0.818 ≥ 2/3 → U = 0.90 (caso 7)
  W12X26: bf/d = 0.532 < 2/3 → U = 0.85 (caso 7)

Chapa de nudo: b_w = 152,4 + 2·300·tan 30° = 498.8 mm (función 498.8); φPn = 0,9·345·498.8·16/1e3 = 2478 kN (función 2478)
  DCR Whitmore 0.282; franja libre 40 mm frente a 2t = 32 mm → OK
  Con 25 mm de franja libre: FAIL (2t = 32 mm), aunque Whitmore siga en 0.282

POST /api/steel-opt/gusset-plate → 200: φPn = 2478 kN, DCR = 0.282, OK; igual que la llamada directa: sí
  Con t = −5 mm → 422 (Input should be greater than 0)
```

</details>

### 6. Travi composte, alveolari e integrazione

#### Solaio di 8 m con AISC 360: carichi e φMn del profilo scelto a mano

<details><summary>Output reale di <code>python examples/composite_floor_beam_optimizer_aisc_360_8_m_span_deck_slab_selected_profile_loads_and_phi_mn_hand_check.py</code></summary>

```text
30 perfiles evaluados, 29 factibles
  perfil     kg/m    DCR modo                    φMn     Mu  δ uso  δ tot pernos
  IPE270     36.0  0.688 Flexión Constructiva  339.7  225.2   10.7   22.1     34
  W12X26     38.7  0.573 Flexión Compuesta     393.6  225.5    8.2   17.0     36
  IPE300     42.2  0.540 Flexión Compuesta     418.5  225.8    8.1   16.8     40
  HEA200     42.2  0.900 Flecha Total          326.6  225.8   14.5   30.0     40
  W14X30     44.8  0.465 Flexión Compuesta     486.4  226.0    6.1   12.7     42
  IPE330     49.1  0.444 Flexión Compuesta     509.9  226.5    6.2   12.9     46
Elegido: IPE270 — frente de Pareto: IPE270, W12X26, IPE300, W14X30, IPE330, W18X35, W16X40, W21X44, W18X50, W24X55, W24X76, HEA500

A mano (IPE270): D = 0.353 (perfil) + 6.261 (losa con nervios al 50 %) + 0.42 (chapa) = 7.034 kN/m
  construcción q = máx(1,4·D, 1,2·D + 1,6·2,8) = 12.92 kN/m → M = 103.4 kN·m frente a φMp = 0,9·Zx·Fy = 150.3 → DCR 0.688 (función 0.688)
  mixta q = 1,2·(D + 1,2·2,8) + 1,6·3,5·2,8 = 28.15 kN/m → Mu = 225.2 kN·m (función 225.2)
  b_eff = 2000 mm; T = As·Fy = 1584 kN; a = 33.3 mm < 70 mm; φMn = 0,9·T·(135 + 50 + 70 − 16.6) = 339.7 kN·m (función 339.7)
  Con la chapa contada dos veces (1.0.0) habría salido 411.0 kN·m (+21%).

Gobierna «Flexión Constructiva» (DCR 0.688): sin apuntalar, el perfil lo fija el hormigón fresco, no la sección mixta.
```

</details>

#### Lo stesso solaio con EN 1994-1-1: M_pl,Rd per blocchi e freccia con la sezione omogeneizzata

<details><summary>Output reale di <code>python examples/composite_floor_beam_optimizer_eurocode_4_ipe_hea_heb_block_method_mpl_rd_and_transformed_section_deflection.py</code></summary>

```text
18 perfiles EN evaluados, 16 factibles
  perfil     kg/m    DCR modo                   M_Rd   M_Ed  δ uso  δ tot
  IPE270     36.0  0.751 Flecha Total          360.0  229.9   12.1   25.0
  IPE300     42.2  0.574 Flecha Total          443.8  230.5    9.3   19.1
  IPE330     49.1  0.446 Flecha Total          534.2  231.2    7.2   14.9
  IPE360     57.1  0.365 Flexión Compuesta     635.5  232.1    5.6   11.7
  HEA240     60.3  0.636 Flecha Total          486.6  232.4   10.2   21.2
Elegido: IPE270 (36.0 kg/m), gobierna «Flecha Total» con DCR 0.751

A mano (IPE270): b_eff = 2000 mm; A_a (chapas) = 4401 mm²; N_pl,a = 1562 kN; N_c,f = 0,85·18.67·2000·70 = 2221 kN
  Eje neutro en la losa: x = 49.2 mm; M_pl,Rd = N_pl,a·(70 + 50 + 135 − 24.6) = 360.0 kN·m (función 360.0)
  n del código = 13.74 (con Ecm de EN 1992-1-1 sería n0 = 6.19); Ac/n = 10192 mm²; d = 220 mm
  I_tr = 215.2·10⁶ mm⁴ (fórmula de 1.0.0: 551.2·10⁶, ×2.56); δ_uso = 5·9.8·8000⁴/(384·200000·I_tr) = 12.14 mm (función 12.14) frente a L/360 = 22.2 mm
```

</details>

#### Pioli in soletta piena e su lamiera, grado minimo di connessione, connessione parziale e momento negativo

<details><summary>Output reale di <code>python examples/ec4_headed_stud_resistance_profiled_sheeting_kt_partial_connection_eta_min_and_hogging_moment.py</code></summary>

```text
1. Ecm = 32837 MPa; P_Rd = mín(81.7; 83.1) = 81.7 kN (función 81.7 kN) — manda el fuste
2. Chapa transversal hp = 60, b0 = 100, h_sc = 100 mm:
   n_r = 1: k_t = 0,7/√1·1.667·0.667 = 0.778 → con tope 0.85: 0.778 (función 0.778); P_Rd = 63.5 kN por perno
   n_r = 2: k_t = 0,7/√2·1.667·0.667 = 0.550 → con tope 0.7: 0.550 (función 0.550); P_Rd = 44.9 kN por perno
3. Grado mínimo de conexión (alas iguales):
   S275: Le  6.0 m → 0.400; Le 10.0 m → 0.419; Le 16.0 m → 0.651; Le 25.0 m → 1.000
   S355: Le  6.0 m → 0.430; Le 10.0 m → 0.550; Le 16.0 m → 0.730; Le 25.0 m → 1.000
   S460: Le  6.0 m → 0.560; Le 10.0 m → 0.653; Le 16.0 m → 0.792; Le 25.0 m → 1.000
   IPE360 S355, b_eff 2 m, hc 70 + hp 50, C30/37: η = 0.4 → M_Rd = 361.7 + 0.4·(649.2 − 361.7) = 476.7 kN·m
   IPE360 S355, b_eff 2 m, hc 70 + hp 50, C30/37: η = 0.7 → M_Rd = 361.7 + 0.7·(649.2 − 361.7) = 563.0 kN·m
   IPE360 S355, b_eff 2 m, hc 70 + hp 50, C30/37: η = 1.0 → M_Rd = 361.7 + 1.0·(649.2 − 361.7) = 649.2 kN·m
4. Momento negativo IPE360 (modelo de chapas) + 1200 mm² de B500 a 90 mm del ala: N_s = 522 kN, M_pl,a = 345.7 kN·m → M_pl,Rd,neg = 462.6 kN·m (función 462.6), +34% sobre el acero solo
```

</details>

#### Trave alveolare: cosa calcola il modulo sperimentale rispetto alla sezione netta al foro

<details><summary>Output reale di <code>python examples/castellated_beam_experimental_depth_1_5_db_flange_only_plastic_modulus_and_fixed_0_85_vierendeel_factor.py</code></summary>

```text
  madre     d_g  Z código   Z neta código/neta T código T real  M_pre M_post
  IPE300    450       705      871       0.809      150     75    250    213
  W14X30    526       866     1097       0.790      176     88    307    261
  HEB300    450      2457     2676       0.918      150     75    872    741

Z del código (solo alas) frente al de la sección neta: menor en los tres casos, del lado seguro en flexión pura; pero el 0,85 fijo no sustituye las comprobaciones de la T, del Vierendeel ni del montante. Estado declarado por el módulo: experimental.
```

</details>

#### API REST senza server: GA, trave, colonna, costo–CO₂, catalogo ed errori di validazione

<details><summary>Output reale di <code>python examples/rest_api_ga_beam_column_pareto_lca_catalog_testclient_json_and_validation_errors.py</code></summary>

```text
ParetoSteel API 1.1.0 (paquete 1.1.0); health → {'status': 'ok'}
GET /api/optimizer/catalog?family=HEB → 5 perfiles: HEB200, HEB240, HEB300, HEB360, HEB400
POST /api/optimizer/ga → {'vigas': 'IPE300', 'pilares': 'HEB200'}, 3742 kg, factible True, 31 valores de historial
POST /optimize/beam → W16X26, φMn 195.1 kN·m, δ 10.10 mm; igual que la función: sí
POST /optimize/column → HP8X36, φPn 1474 kN, KL/r 70.7; igual que la función: sí
POST /api/steel-opt/pareto-lca → 1 solución: {'vigas': 'IPE300'}, 2228 USD, 1.22 t CO₂ (min_Ix en cm⁴ en este endpoint)

L_m = −1 → 422: Input should be greater than 0
élite = población → 400: elitism debe estar en [0, population_size)
length_total = 0 → 422: Input should be greater than 0
```

</details>

#### Ponte con il modello canonico senza fastsap e stato di calcolo chiuso per impostazione predefinita

<details><summary>Output reale di <code>python examples/section_bridge_canonical_frame_model_read_and_apply_optimized_sections_without_fastsap_and_closed_status.py</code></summary>

```text
Antes: P1=HEB300, P2=HEB300, P3=HEB300, P4=HEB300, V1=IPE500, V2=IPE500
Después: P1=HEB200, P2=HEB200, P3=HEB200, P4=HEB200, V1=IPE300, V2=IPE270
  El modelo original no cambia (inmutable): P1 sigue con HEB300; secciones del modelo nuevo: ['HEB200', 'HEB300', 'IPE270', 'IPE300', 'IPE500']
  fastsap instalado: no → la validación contra catálogo no se ha hecho (validate_against_catalog=True lanzaría ImportError).

Estado por barra (resolve_status, cerrado por defecto):
  V1: IPE300  utilización 0.942 → sin evidencias NO_CALCULADO; con el análisis sin ejecutar NO_CALCULADO
  V2: IPE270  utilización 0.873 → sin evidencias NO_CALCULADO; con el análisis sin ejecutar NO_CALCULADO
  P1: HEB200  utilización 0.471 → sin evidencias NO_CALCULADO; con el análisis sin ejecutar NO_CALCULADO
  P2: HEB200  utilización 0.471 → sin evidencias NO_CALCULADO; con el análisis sin ejecutar NO_CALCULADO
  P3: HEB200  utilización 0.218 → sin evidencias NO_CALCULADO; con el análisis sin ejecutar NO_CALCULADO
  P4: HEB200  utilización 0.218 → sin evidencias NO_CALCULADO; con el análisis sin ejecutar NO_CALCULADO
  Solo con las seis evidencias declaradas True una utilización de 0,8 es CALCULADO_CUMPLE.
Agregado del pórtico: NO_CALCULADO; lista vacía → NO_CALCULADO. Las demandas de este ejemplo son supuestas, no de un análisis: por eso se declara analysis_executed=False y nada sale CALCULADO_CUMPLE.
```

</details>

## Verifica

- Correzioni della 1.1.0, una per test con il suo oracolo (`test_correcciones_1_1_0.py`): la relazione riproduce il rapporto del selettore (W18X35, 320/338,4 = 0,9455); GA con catalogo proprio rispetto all'enumerazione (IPE300, 422 kg); nessuna designazione duplicata e W8X31 con la Ix della base AISC; i dodici W del catalogo unificato rispetto alla base AISC v16 (A, Ix, Iy ≤ 0,5 %) e Zx del W14X30 = 775 cm³; ponte delle sezioni senza fastsap; interazione H1 della colonna per evoluzione differenziale a mano (1,1222); φMn composto AISC della IPE270 a mano (339,7 kN·m); 32 pioli con l'Ec in SI; freccia EC4 con l'inerzia omogeneizzata a mano (12,14 mm); versione unica.
- Interazione H1 e B1 della AISC 360-16 con derivazione a mano (`test_golden_aisc_h1_interaction.py`); instabilità flesso-torsionale di una IPE300 S275 secondo EN 1993-1-1 §6.3.2 con proprietà EN 10365 e scelta della curva con le Tabelle 6.4 e 6.5 (`test_golden_ltb_en1993.py`); flessione plastica e riduzione χ del §6.3.1.2 (`test_golden_analytical_steel_mechanics.py`).
- Controventi AISC 360/341: transizione del §E3, lunghezze efficaci, trazione e rottura, resistenze attese, chevron, shear lag e fazzoletto (`test_golden_steel_bracing_aisc.py`, `test_gusset_plate_api.py`).
- Computi con le aree della EN 10365 (IPE300 53,8 cm², HEB300 149,1 cm²) e somma esatta di tonnellate e costo (`test_golden_steel_boq.py`); fronte costo–CO₂ ammissibile e senza dominanze interne (`test_golden_nsga2_pareto_lca.py`).
- Kernel di ordinamento non dominato identici al Python puro, anche dentro `nsga2_run` (`test_nsga2_fast.py`, `test_nsga2_jit.py`).
- `tests/test_examples.py` esegue i 33 esempi come sottoprocessi su ubuntu e windows × Python 3.11–3.13. Senza `fastsap` (client privato di SAP2000) e `stickmodelsjm` si saltano quattro moduli di test che li importano.

## Limitazioni

- Non c'è analisi strutturale: le sollecitazioni sono dati. I selettori (`beam_selector`, `services`, `diff_evolution`) non verificano l'instabilità locale delle sezioni snelle (§E7) né la flesso-torsione; l'HSS più leggero che scelgono a compressione è spesso a parete snella. L'instabilità flesso-torsionale entra solo se si dà `L_b_m`: `beam_selector` applica il χ_LT della EN 1993-1-1 §6.3.2 (It e Iw stimati dalla geometria) al φ·Zx·Fy AISC, un misto di norme; `services.optimize_beam` usa una riduzione lineare propria tra Lp e Lr che non è quella della AISC 360 §F2.2; `diff_evolution` non la verifica. `beam_selector` verifica la freccia solo se si danno `L_span_m` e `w_service_kN_m`, e usa sempre φv = 0,90 (la AISC ammette 1,00 per anime di laminati compatti). `services.optimize_beam` usa Sx elastico salvo con `use_plastic_modulus=True`, verifica `V_Ed_kN` con 0,9·0,6·Fy·d·tw e, se non si passa il carico di esercizio, valuta la freccia con 10 kN/m. La trave di `diff_evolution` approssima l'anima con A/2 e usa lo stesso carico per resistenza e freccia.
- Gli ottimizzatori evolutivi non garantiscono l'ottimo di catalogo: l'evoluzione differenziale ha dato W21X44 dove l'enumerazione dà W18X40 (+10 %); il GA su HSS è rimasto fino allo 0,65 % sopra. `nsga2_run` (genitori a caso, crossover convesso, mutazione dell'1 %) copre solo una parte del fronte di ZDT1.
- `pareto_lca` e `pareto_weight_cost` non hanno un compromesso da esplorare: costo e CO₂ sono massa × fattori fissi e il fronte è un punto. Le tabelle di `cost_by_country` e `cost_lca` sono illustrative e non coincidono (Germania −38 % tra l'una e l'altra); `CountryCost.code` è incoerente (Cile «AU»). `pareto_lca` chiede min_Ix in cm⁴ e `genetic` in m⁴.
- `design_codes`: «EU» usa sempre la curva c e «AU» è la curva AISC, non la AS 4100; `aisc_beam_column_interaction` (sperimentale) completa Ix, Iy e lunghezze con valori predefiniti se non vengono passati. `ec3_2022_2g`: curva predefinita a0 (la più favorevole), somma lineare M + N invece del §6.3.3, classe 4 approssimata e numerazione delle clausole dell'edizione 2022 non confrontata. `aisc360_22_hss`: φTn solo per tubi rettangolari e H3-6 senza la soglia del 20 % di Tc.
- `bracing`: la croce prende 1,0·L nel piano (conservativo) e l'Ry predefinito è 1,10 (W in A992): per tubi A500 bisogna passare il loro oppure il carico sbilanciato della V risulta basso. Il numero di clausola citato dalla fascia 2t del fazzoletto resta non confrontato.
- Travi composte: nessuna instabilità flesso-torsionale in fase di costruzione (ala superiore supposta ritenuta dalla lamiera); il ramo EC4 non riduce i pioli per la lamiera (k_t), usa un modulo del calcestruzzo che non è l'Ecm della EN 1992-1-1 (n = 13,7 rispetto a n0 = 6,2 con fck = 28) e un unico n per tutti i carichi; l'inerzia efficace I_s + √η·(I_tr − I_s) è quella del commentario AISC, anche nel ramo EC4. `castellated` è sperimentale (Z solo dalle ali, fattore fisso 0,85).
- `price_sensitivity_v2` usa normali indipendenti non troncate; `surrogate` è un Kriging a media nulla e lunghezza fissa che tende a 0 fuori dai dati; `reuse` abbina in modo greedy una capacità scalare; `optimizer.SteelSectionOptimizer` è un'euristica con valori fissi. Validare le sezioni rispetto al catalogo in `section_bridge` richiede `fastsap`, che non è una dipendenza pubblica.

## Norme e riferimenti

Confrontato in questa revisione con fonti secondarie (AISC Engineering Journal e Modern Steel Construction, documentazione di programmi di calcolo, schede dei profili): φv = 1,00 della AISC 360 §G2.1(a), la soglia del 20 % del §H3.2, il limite 1,40·√(E/Fy) della Tabella B4.1a con t = 0,93·t_nominale, Ry = 1,3 dell'A500 grado C, l'Ecm della EN 1992-1-1, la curva c della Tabella 6.2 della EN 1993-1-1 per I saldate in z–z e le proprietà dei W corretti. Gli altri numeri di clausola provengono dal codice del pacchetto e restano non confrontati.

- AISC 360-16, *Specification for Structural Steel Buildings*: §D2 e Tabella D3.1, §E3, §F2.1, §G2.1, §H1.1, §H3 (costante C, φTn ed equazione H3-6, mantenuta dall'edizione 2022), Appendice 8 (B1) e cap. I (travi composte: larghezza efficace, Ec = 0,043·wc^1,5·√f'c, pioli, momento plastico).
- AISC 341-16, *Seismic Provisions for Structural Steel Buildings*: §F2.3 (resistenze attese e 0,3 della diagonale instabilizzata), §F2.5b (KL/r ≤ 200) e Tabella A3.1 (Ry = 1,3 per A500 grado C, secondo l'AISC Engineering Journal).
- AISC Shapes Database v16.0 (Steel Construction Manual, 16ª ed., Tabella 1-1).
- EN 1993-1-1:2005: Tabella 5.2 (classi), §6.2.5, §6.3.1 (Tabella 6.2), §6.3.2 (Tabelle 6.4 e 6.5). EN 1993-1-1:2022 per l'idea di W_ep in classe 3 (interpolazione del pacchetto, non confrontata con la clausola).
- EN 1994-1-1:2004: §5.4.1.2, §6.2.1.2, §6.2.1.3, §6.6.1.2, §6.6.3.1, §6.6.4 e Tabella 6.2. EN 1992-1-1:2004, Tabella 3.1 (Ecm). EN 10365:2017 (dimensioni dei profili europei).
- K. Deb, A. Pratap, S. Agarwal e T. Meyarivan, «A fast and elitist multiobjective genetic algorithm: NSGA-II», IEEE Trans. Evol. Comput. 6(2) (2002). R. Storn e K. Price, «Differential evolution», J. Global Optim. 11 (1997), tramite `scipy.optimize.differential_evolution`. I problemi di prova ZDT1 e Schaffer N.1 dell'esempio NSGA-II sono citati nella sua intestazione.

## Licenza

MIT. Vedi [LICENSE](LICENSE).

---

Parte di **Loadpath**, la raccolta di librerie strutturali open source di [Jesús Murgas](https://github.com/jmurgass99).
