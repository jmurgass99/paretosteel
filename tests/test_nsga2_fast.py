"""Equivalencia exacta entre el non-dominated sort puro y el acelerado (Numba).

El kernel JIT debe producir frentes y ranks BYTE-idénticos a la versión pura;
y `nsga2_run(fast=True)` debe dar el mismo resultado que `fast=False`.
"""
import random

import pytest

from paretosteel.nsga2 import (
    Individual,
    non_dominated_sort,
    nsga2_run,
)
from paretosteel._nsga2_fast import NUMBA_AVAILABLE, non_dominated_sort_fast


def _pop(fitnesses):
    return [Individual(genes=[0.0], fitness=tuple(f)) for f in fitnesses]


def _ranks(pop):
    return [ind.rank for ind in pop]


class TestEquivalenciaFrentes:
    def test_caso_a_mano(self):
        fits = [(1.0, 4.0), (2.0, 3.0), (3.0, 2.0), (4.0, 1.0),  # frente 0 (no dominados)
                (2.0, 5.0), (5.0, 5.0)]                          # dominados
        pa, pb = _pop(fits), _pop(fits)
        fa = non_dominated_sort(pa)
        fb = non_dominated_sort_fast(pb)
        assert fa == fb
        assert _ranks(pa) == _ranks(pb)

    def test_todos_no_dominados(self):
        fits = [(1.0, 3.0), (2.0, 2.0), (3.0, 1.0)]
        pa, pb = _pop(fits), _pop(fits)
        assert non_dominated_sort(pa) == non_dominated_sort_fast(pb)
        assert _ranks(pa) == _ranks(pb) == [0, 0, 0]

    def test_cadena_dominancia(self):
        fits = [(1.0, 1.0), (2.0, 2.0), (3.0, 3.0), (4.0, 4.0)]
        pa, pb = _pop(fits), _pop(fits)
        assert non_dominated_sort(pa) == non_dominated_sort_fast(pb)
        assert _ranks(pa) == _ranks(pb) == [0, 1, 2, 3]

    def test_poblacion_vacia(self):
        assert non_dominated_sort_fast([]) == []

    @pytest.mark.parametrize("seed", [0, 1, 7, 42, 123])
    def test_random_equivalente(self, seed):
        rng = random.Random(seed)
        fits = [(rng.random(), rng.random(), rng.random()) for _ in range(60)]
        pa, pb = _pop(fits), _pop(fits)
        assert non_dominated_sort(pa) == non_dominated_sort_fast(pb)
        assert _ranks(pa) == _ranks(pb)

    def test_escala_grande(self):
        rng = random.Random(99)
        fits = [(rng.random(), rng.random()) for _ in range(200)]
        pa, pb = _pop(fits), _pop(fits)
        assert non_dominated_sort(pa) == non_dominated_sort_fast(pb)
        assert _ranks(pa) == _ranks(pb)


class TestNsga2RunIdentico:
    def _obj(self, g):
        # dos objetivos en conflicto
        return (g[0] ** 2 + g[1] ** 2, (g[0] - 1) ** 2 + (g[1] - 1) ** 2)

    def test_fast_igual_que_puro(self):
        kw = dict(objective_fn=self._obj, n_genes=2,
                  bounds=[(-2.0, 2.0), (-2.0, 2.0)], pop_size=30, n_gen=15, seed=5)
        slow = nsga2_run(**kw, fast=False)
        fast = nsga2_run(**kw, fast=True)
        assert [i.genes for i in slow] == [i.genes for i in fast]
        assert [i.fitness for i in slow] == [i.fitness for i in fast]


class TestNumba:
    def test_numba_disponible(self):
        # En este entorno numba está instalado; el kernel debe ir por la ruta JIT.
        assert NUMBA_AVAILABLE is True
