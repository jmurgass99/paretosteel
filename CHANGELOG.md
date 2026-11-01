# Changelog

## 1.1.0 — 2026-11-01

### Corregido
- `memos.profile_justification.memo_from_beam_candidate`: pasaba la capacidad de DISEÑO del selector (φMn, φVn) como si fuera la nominal y `render_profile_memo` volvía a aplicar φ. El W18X35 que `beam_selector` da por bueno con M_u = 320 kN·m (ratio 0,946) salía «NO CUMPLE» (1,051, ×1/0,9). Ahora divide por el φ del selector y los ratios coinciden. Sin carga de servicio (`w_kN_m = 0`) la flecha se daba por «OK» con δ = 0; ahora queda «NO VERIFICADA» y la memoria no firma CUMPLE.
- `memos.justificacion_perfil.justificar`: una capacidad axial ausente (`Pn_kN <= 0`) daba P/φPn = 0 y la barra «cumplía» a axil; ahora el ratio es infinito si hay demanda (y 0 si tampoco hay axil). Lo mismo para M y V (antes 99).
- `genetic.optimize(custom_profiles=...)`: los candidatos de cada grupo se sacaban del catálogo global y el GA elegía perfiles que no estaban en `custom_profiles` (`KeyError` en cuanto el subcatálogo no contenía la familia entera). Ahora salen del catálogo de la optimización.
- `catalogs.all_profiles` (y con él `filter_profiles`, el GA, la evolución diferencial y el BoQ): los nueve W tecleados a mano en `CATALOG_AISC_W` aparecían dos veces, con valores distintos de la base AISC v16 (W8X31: Ix 4240 frente a 4579 cm⁴, −7,4 %; W8X24: Iy 707 frente a 762 cm⁴). Ahora hay una entrada por designación y manda la base AISC v16; `boq` también la prefiere.
- `catalog_unified`: W12X26 Iy 740 → 720 cm⁴ y Zx 615 → 610 cm³; W14X30 Ix 12000 → 12110, Iy 820 → 816 y Zx 750 → 775 cm³ (47,3 in³, +3,3 %); W18X35 Ix 21000 → 21230 e Iy 670 → 637 cm⁴ (−4,9 %). Los doce W se contrastan ahora en los tests con la base AISC v16 empaquetada (A, Ix, Iy ≤ 0,5 %).
- `section_bridge.apply_proposed_sections`: importaba `fastsap` aunque `validate_against_catalog=False`, así que el puente fallaba siempre sin ese paquete (que no es dependencia de paretosteel). Ahora solo lo importa para validar.
- `diff_evolution.optimize_column_de`: con momento, la interacción AISC H1 solo estaba en la penalización; el resultado declaraba `feasible` mirando el axil. Ahora publica `interaction_ratio` y la factibilidad la decide la interacción (W8X31, 3 m, P = 0,5·φPn, M = 0,7·φMn: H1 = 1,122 → no factible; antes «factible»).
- `_composite.industrial_composite_beams` (rama AISC, usada por `composite_optimizer`): pasaba el canto TOTAL de la losa como hormigón POR ENCIMA de la chapa y el motor sumaba la chapa al brazo: la chapa contaba dos veces (brazo +50 mm, bloque comprimido y I_tr inflados). IPE270, 8 m, losa 120 sobre chapa 50: φMn 411,0 → 339,7 kN·m (−17 %); flechas de uso 7,7 → 10,7 mm y total 16,0 → 22,1 mm. Ahora se valida que la chapa sea menor que la losa.
- Misma rama: la estimación del número de pernos calculaba Ec con el coeficiente SI 0,043 aplicado a wc en pcf y f'c en psi (Ec un 30 % alto); con losa maciza, donde manda el hormigón, salían menos pernos de los necesarios para conexión completa (HEA200: 30 → 32). Usa ahora `aisc_concrete_modulus`.
- Misma función, rama EC4: la inercia homogeneizada era Ia + (Ac/n)·d², sin desplazar el eje neutro (como si el acero tuviera área infinita): IPE270, b_eff 2 m, hc 70 mm: I_tr 551 → 215·10⁶ mm⁴ y flecha de uso 4,74 → 12,14 mm. En el forjado de ejemplo la viga EC4 pasa a estar gobernada por la flecha total (DCR 0,751).
- `pyproject.toml`: la base AISC v16 (`paretosteel/data/aisc_v16.csv`) no entraba en la rueda; con `pip install git+...` no editable el catálogo AISC (W_FULL, HSS_FULL…) quedaba vacío y solo se registraba un aviso. Añadido `[tool.setuptools.package-data]` y comprobado construyendo la rueda.
- Versión única 1.1.0 en `pyproject.toml`, `paretosteel.__version__` y la API (`FastAPI(version=__version__)`; antes 1.0.0 fijo en el código). La insignia del README decía Python 3.10+ y el paquete exige 3.11.
- Descripciones: el paquete se presentaba como «optimizador heurístico»; el GA decía penalizar «DCR > 1» (penaliza déficit de Ix y A); `aisc_e3_critical_stress` afirmaba que las dos ramas de §E3 «coinciden idénticamente» (difieren un 0,04 %: 0,658^2,25 = 0,38995 frente a 0,877/2,25 = 0,38978).
- `tests/test_beam_selector.py`: el oráculo de φMn del W12X26 usaba el Zx mal transcrito (615); ahora 610 cm³.

### Añadido
- 33 casos de uso ejecutables en `examples/` (seis grupos) con su salida en `examples/output/`, y `tests/test_examples.py`, que los ejecuta en CI.
- `tests/test_correcciones_1_1_0.py`: un test por corrección con su oráculo a mano o independiente.
- README reescrito con las salidas reales, los límites y las referencias.

### Límites documentados (sin cambio de código)
- `pareto_lca.run_pareto_lca_optimizer` y `diff_evolution.pareto_weight_cost` no tienen compromiso que explorar: coste y CO₂ son masa × factores fijos por grupo, así que el «frente» es siempre un punto (el más ligero factible). Comprobado por enumeración en los ejemplos.
- `optimize_beam_de` no garantiza el óptimo: W, 8 m, 20 kN/m da W21X44 cuando la enumeración da W18X40 (+10 %). El GA por grupos acierta en IPE/HEB y en HSS (714 perfiles) queda hasta un 0,65 % por encima con 4 de 5 semillas.
- `nsga2.nsga2_run`: padres al azar, cruce convexo y mutación del 1 %; converge en ZDT1 pero cubre solo el 22–41 % del frente.
- `beam_selector`: sin pandeo lateral (Lb ≤ Lp supuesto) ni flecha; φv = 0,90 siempre (AISC 360 §G2.1(a) permite 1,00 en almas de perfiles laminados con h/tw ≤ 2,24·√(E/Fy)).
- `services.optimize_beam`: φ·Fy·Sx (elástico), sin pandeo lateral; `V_Ed_kN` no se comprueba y la flecha usa 10 kN/m si no se pasa `w_service_kN_m`.
- `services.optimize_column` y `optimize_column_de`: sin pandeo local (§E7) ni por torsión o flexotorsión; el HSS más ligero que eligen suele ser de pared esbelta (HSS12X12X3/16: b/t = 65,8 > 33,7).
- `diff_evolution` (viga): alma = A/2, Sx elástico y la misma w para resistencia y flecha.
- `design_codes.design_column`: «EU» usa siempre la curva c; «AU» es la curva de AISC, no AS 4100 §6.3.3.
- `design_codes.aisc_beam_column_interaction` (experimental): si no se pasan Ix, Iy y longitudes usa valores por defecto (W12X65 de ejemplo: B1y 1,335 frente a 1,185).
- `ec3_2022_2g`: la curva por defecto «a0» es la más favorable (una I soldada en z–z es curva c: χ −25 %); la utilización es la suma lineal M/M_Rd + N/N_b,Rd, no §6.3.3 ni el método de interacción global que cita la cabecera; clase 4 aproximada; numeración de cláusulas de la edición 2022 sin contrastar.
- `aisc360_22_hss`: φTn solo para tubos rectangulares; H3-6 se aplica también por debajo del 20 % de Tc.
- `bracing`: en la cruz toma 1,0·L en el plano (conservador); Ry por defecto 1,10 (W en A992): con un tubo A500 grado C (1,3) la carga desequilibrada de una V invertida sale un 17 % baja si no se pasa.
- `castellated` (experimental): Z solo de alas, factor fijo 0,85 y altura de T 0,5·d_b (con expansión del 50 % y hueco h_o = d_b sería 0,25·d_b; geometría sin contrastar con una guía de diseño).
- Vigas mixtas: sin pandeo lateral en construcción; la rama EC4 no reduce los pernos por la chapa (k_t); su módulo del hormigón 9500·((fck + 8)/10)^(1/3) MPa no es el Ecm de EN 1992-1-1 (n = 13,7 frente a n0 = 6,2 con fck = 28) y no distingue cargas de corta y larga duración.
- Tablas de coste: `cost_by_country` y `cost_lca` dan precios distintos para el mismo país (Alemania −38 %), son ilustrativas y el campo `CountryCost.code` es incoherente (Chile «AU»).
- `price_sensitivity_v2`: normales independientes sin truncar. `surrogate`: media nula y longitud fija, extrapola hacia 0. `reuse`: voraz en el orden de la demanda con una capacidad escalar. `optimizer.SteelSectionOptimizer`: heurística con cifras fijas (31,2 % de ahorro HEB200 → IPE300).
- Unidades: `pareto_lca` pide min_Ix y min_A en cm⁴ y cm²; `genetic.ElementGroup`, en m⁴ y m².
- El extra `perf` es nominal: numba es dependencia obligatoria.
