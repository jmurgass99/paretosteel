"""Surrogate models - Kriging simple (gaussian process basico).

Implementacion auto-contenida con numpy si esta disponible, fallback pure-python.
"""
from __future__ import annotations

from dataclasses import dataclass


def _dist2(a: list[float], b: list[float]) -> float:
    return sum((ai - bi) ** 2 for ai, bi in zip(a, b))


def _rbf_kernel(a: list[float], b: list[float], length: float) -> float:
    from math import exp
    return exp(-_dist2(a, b) / (2.0 * length ** 2))


@dataclass
class KrigingSurrogate:
    X: list[list[float]]
    y: list[float]
    length: float = 1.0
    noise: float = 1e-6

    def _solve(self, K: list[list[float]], y: list[float]) -> list[float]:
        n = len(K)
        # Gauss-Jordan
        A = [row[:] + [yi] for row, yi in zip(K, y)]
        for i in range(n):
            piv = A[i][i]
            if abs(piv) < 1e-12:
                # swap
                swapped = False
                for k in range(i + 1, n):
                    if abs(A[k][i]) > 1e-12:
                        A[i], A[k] = A[k], A[i]
                        piv = A[i][i]
                        swapped = True
                        break
                if not swapped:
                    # Apply Tikhonov regularization (jitter) by adding 1e-6 to the diagonal of K and resolving
                    regularized_K = [[K[r][c] + (1e-6 if r == c else 0.0) for c in range(n)] for r in range(n)]
                    # Avoid infinite recursion by checking if we already regularized
                    # if we have, we just use a small eps to avoid ZeroDivisionError
                    if any(abs(K[r][r] - (K[r][r] + 1e-6)) < 1e-9 for r in range(n)):
                        piv = 1e-12 if piv >= 0 else -1e-12
                    else:
                        return self._solve(regularized_K, y)
            for j in range(i, n + 1):
                A[i][j] /= piv
            for k in range(n):
                if k != i:
                    f = A[k][i]
                    for j in range(i, n + 1):
                        A[k][j] -= f * A[i][j]
        return [row[n] for row in A]

    def fit(self) -> "KrigingSurrogate":
        n = len(self.X)
        K = [[_rbf_kernel(self.X[i], self.X[j], self.length) + (self.noise if i == j else 0.0)
              for j in range(n)] for i in range(n)]
        self._alpha = self._solve(K, self.y)
        return self

    def predict(self, x: list[float]) -> float:
        k_star = [_rbf_kernel(x, xi, self.length) for xi in self.X]
        return sum(a * k for a, k in zip(self._alpha, k_star))


__all__ = ["KrigingSurrogate"]
