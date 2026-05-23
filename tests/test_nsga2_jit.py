# -*- coding: utf-8 -*-
"""
Tests de unidad y rendimiento para el motor JIT de NSGA-II
"""
from __future__ import annotations
import numpy as np
import pytest
import time
from steeloptimizerjm.nsga2_jit import (
    fast_dominates,
    non_dominated_sort_jit,
    calculate_crowding_distance_jit,
)

def test_fast_dominates():
    # Minimización
    a = np.array([2.0, 3.0])
    b = np.array([3.0, 4.0])
    c = np.array([2.0, 3.0])
    d = np.array([1.0, 5.0])
    
    # 'a' domina a 'b' (es mejor en ambos)
    assert fast_dominates(a, b) is True
    # 'b' no domina a 'a'
    assert fast_dominates(b, a) is False
    # 'a' no domina a 'c' (son iguales)
    assert fast_dominates(a, c) is False
    # 'a' y 'd' no se dominan mutuamente (uno es mejor en obj1, otro en obj2)
    assert fast_dominates(a, d) is False
    assert fast_dominates(d, a) is False

def test_non_dominated_sort_jit():
    # Matriz de fitness de prueba
    # p0: (10.0, 100.0) -> muy mala
    # p1: (5.0, 50.0)   -> regular, dominada por p2 y p3
    # p2: (2.0, 80.0)   -> Pareto, no dominada
    # p3: (8.0, 20.0)   -> Pareto, no dominada
    fitness = np.array([
        [10.0, 100.0],
        [5.0, 50.0],
        [2.0, 80.0],
        [8.0, 20.0]
    ], dtype=np.float64)
    
    ranks = non_dominated_sort_jit(fitness)
    
    # El rango 0 debe corresponder a las no dominadas (p1, p2 y p3 son mutuamente no dominadas)
    assert ranks[1] == 0
    assert ranks[2] == 0
    assert ranks[3] == 0
    
    # p0 es dominada por todos (rango 1)
    assert ranks[0] == 1

def test_calculate_crowding_distance_jit():
    fitness = np.array([
        [1.0, 9.0],
        [2.0, 8.0],
        [5.0, 5.0],
        [8.0, 2.0],
        [9.0, 1.0]
    ], dtype=np.float64)
    
    # Todos pertenecen al frente de Pareto 0
    ranks = np.zeros(5, dtype=np.int32)
    
    distances = calculate_crowding_distance_jit(fitness, ranks)
    
    # Los extremos (0 y 4) deben tener distancia infinita (1e9 en JIT)
    assert distances[0] == 1e9
    assert distances[4] == 1e9
    
    # Las intermedias deben tener valores positivos y coherentes
    assert distances[1] > 0
    assert distances[2] > 0
    assert distances[3] > 0

def test_jit_performance_benchmark():
    # Generar una población grande para ver el beneficio de JIT
    rng = np.random.default_rng(42)
    pop_size = 200
    n_obj = 2
    fitness = rng.random((pop_size, n_obj)) * 100.0
    
    # Calentamiento (compilación JIT)
    _ = non_dominated_sort_jit(fitness[:5])
    _ = calculate_crowding_distance_jit(fitness[:5], np.zeros(5, dtype=np.int32))
    
    # Medir tiempo con JIT
    t_start = time.perf_counter()
    ranks_jit = non_dominated_sort_jit(fitness)
    dist_jit = calculate_crowding_distance_jit(fitness, ranks_jit)
    t_jit = time.perf_counter() - t_start
    
    assert len(ranks_jit) == pop_size
    assert len(dist_jit) == pop_size
    # Imprime el tiempo para información del desarrollador
    print(f"\n[BENCHMARK] NSGA-II JIT para N={pop_size} ejecutado en {t_jit*1000:.3f} ms")
