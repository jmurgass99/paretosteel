# -*- coding: utf-8 -*-
"""Verificacion de servicio por deflexion (AISC / IBC Tabla 1604.3).

Complementa la seleccion por resistencia (beam_selector) con el estado limite de
SERVICIO: una viga puede cumplir resistencia y aun asi fallar el limite de
deflexion (L/360 carga viva, L/240 total son los tipicos).

Deflexiones de viga simplemente apoyada:
  - Carga distribuida w:  delta = 5·w·L^4 / (384·E·I)
  - Carga puntual P centrada: delta = P·L^3 / (48·E·I)
Unidades SI: N, mm, MPa (=N/mm^2), mm^4  ->  delta en mm.
"""
from __future__ import annotations

from dataclasses import dataclass

_E_STEEL = 200000.0  # MPa


@dataclass(frozen=True)
class DeflectionCheck:
    delta_mm: float
    limit_mm: float
    ratio: float          # delta / limit ; <= 1.0 = OK
    ok: bool


def deflection_udl(w_N_mm: float, L_mm: float, I_mm4: float, E_MPa: float = _E_STEEL) -> float:
    """Deflexion maxima de viga simple bajo carga distribuida (mm)."""
    return 5.0 * w_N_mm * L_mm ** 4 / (384.0 * E_MPa * I_mm4)


def deflection_point_center(P_N: float, L_mm: float, I_mm4: float, E_MPa: float = _E_STEEL) -> float:
    """Deflexion maxima de viga simple bajo carga puntual centrada (mm)."""
    return P_N * L_mm ** 3 / (48.0 * E_MPa * I_mm4)


def check_deflection(delta_mm: float, L_mm: float, limit_ratio: float = 360.0) -> DeflectionCheck:
    """Compara la deflexion contra L/limit_ratio (p.ej. 360 viva, 240 total)."""
    limit = L_mm / limit_ratio
    return DeflectionCheck(delta_mm=delta_mm, limit_mm=limit,
                           ratio=delta_mm / limit if limit > 0 else float("inf"),
                           ok=delta_mm <= limit + 1e-9)


def required_I_udl(w_N_mm: float, L_mm: float, limit_ratio: float = 360.0,
                   E_MPa: float = _E_STEEL) -> float:
    """Inercia minima I (mm^4) para cumplir L/limit_ratio bajo carga distribuida."""
    limit = L_mm / limit_ratio
    return 5.0 * w_N_mm * L_mm ** 4 / (384.0 * E_MPa * limit)


__all__ = [
    "DeflectionCheck", "deflection_udl", "deflection_point_center",
    "check_deflection", "required_I_udl",
]
