# -*- coding: utf-8 -*-
"""
Loadpath Core - NSGA-II Pareto Engine Acelerado con Numba JIT
"""
from __future__ import annotations
import numpy as np
from numba import jit

@jit(nopython=True, cache=True)
def fast_dominates(fit_a: np.ndarray, fit_b: np.ndarray) -> bool:
    """Evalúa la dominancia de Pareto para minimización.
    
    True si 'a' domina a 'b' (es mejor o igual en todos los objetivos
    y estrictamente mejor en al menos uno).
    """
    better_any = False
    for i in range(fit_a.shape[0]):
        if fit_a[i] > fit_b[i]:
            return False
        if fit_a[i] < fit_b[i]:
            better_any = True
    return better_any

@jit(nopython=True, cache=True)
def non_dominated_sort_jit(fitness_matrix: np.ndarray) -> np.ndarray:
    """
    Clasificación no dominada ultra veloz compilada con Numba.
    
    Args:
        fitness_matrix: Array 2D (Float64) de dimensiones (N_poblacion, M_objetivos)
    Returns:
        ranks: Array 1D (Int32) con el rango del frente de cada individuo (0 = Pareto, 1 = segundo frente...)
    """
    n_pop = fitness_matrix.shape[0]
    ranks = np.zeros(n_pop, dtype=np.int32)
    n = np.zeros(n_pop, dtype=np.int32)
    
    # Matriz binaria para maximizar el rendimiento en Numba sin listas dinámicas complejas
    dominados_por = np.zeros((n_pop, n_pop), dtype=np.bool_)
    
    for p in range(n_pop):
        fit_p = fitness_matrix[p]
        for q in range(n_pop):
            if p == q:
                continue
            fit_q = fitness_matrix[q]
            
            if fast_dominates(fit_p, fit_q):
                dominados_por[p, q] = True
            elif fast_dominates(fit_q, fit_p):
                n[p] += 1
                
    # Inicializar el primer frente
    # Usamos una lista para inicializar el frente en Numba, lo cual es compatible en Python 3/Numba
    current_front = []
    for p in range(n_pop):
        if n[p] == 0:
            ranks[p] = 0
            current_front.append(p)
            
    rank = 0
    while len(current_front) > 0:
        next_front = []
        for p in current_front:
            for q in range(n_pop):
                if dominados_por[p, q]:
                    n[q] -= 1
                    if n[q] == 0:
                        ranks[q] = rank + 1
                        next_front.append(q)
        rank += 1
        current_front = next_front
        
    return ranks

@jit(nopython=True, cache=True)
def calculate_crowding_distance_jit(fitness_matrix: np.ndarray, ranks: np.ndarray) -> np.ndarray:
    """
    Calcula la distancia de apiñamiento (Crowding Distance) por frente de Pareto en microsegundos.
    Garantiza la diversidad de soluciones a lo largo del frente.
    """
    n_pop = fitness_matrix.shape[0]
    n_obj = fitness_matrix.shape[1]
    crowding_distances = np.zeros(n_pop, dtype=np.float64)
    
    max_rank = np.max(ranks)
    for r in range(max_rank + 1):
        # Encontrar los índices del frente actual
        indices_list = []
        for i in range(n_pop):
            if ranks[i] == r:
                indices_list.append(i)
        
        n_indices = len(indices_list)
        if n_indices == 0:
            continue
            
        if n_indices <= 2:
            for idx in indices_list:
                crowding_distances[idx] = 1e9  # Prioridad máxima para desempates en frentes pequeños
            continue
            
        # Convertir a array de NumPy para manipulación segura en Numba
        indices = np.array(indices_list, dtype=np.int32)
        
        # Calcular distancias por cada objetivo
        for m in range(n_obj):
            # Ordenamiento por burbuja compilado sobre el array local de índices
            sorted_indices = indices.copy()
            for i in range(n_indices):
                for j in range(0, n_indices - i - 1):
                    val_j = fitness_matrix[sorted_indices[j], m]
                    val_j1 = fitness_matrix[sorted_indices[j+1], m]
                    if val_j > val_j1:
                        tmp = sorted_indices[j]
                        sorted_indices[j] = sorted_indices[j+1]
                        sorted_indices[j+1] = tmp
            
            # Los extremos de la frontera tienen prioridad infinita para mantener el rango de búsqueda
            crowding_distances[sorted_indices[0]] = 1e9
            crowding_distances[sorted_indices[-1]] = 1e9
            
            f_min = fitness_matrix[sorted_indices[0], m]
            f_max = fitness_matrix[sorted_indices[-1], m]
            norm_factor = f_max - f_min
            if norm_factor < 1e-12:
                norm_factor = 1.0
            
            for i in range(1, n_indices - 1):
                idx_prev = sorted_indices[i - 1]
                idx_next = sorted_indices[i + 1]
                idx_curr = sorted_indices[i]
                diff = fitness_matrix[idx_next, m] - fitness_matrix[idx_prev, m]
                crowding_distances[idx_curr] += diff / norm_factor
                
    return crowding_distances
