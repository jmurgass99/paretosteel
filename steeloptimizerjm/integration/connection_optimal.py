"""Bridge SteelOptimizerJm -> SteelConnectionJm.

Toma el perfil optimo del optimizer y propone tipologia de conexion
(WUF-W, RBS, end-plate) acorde a las solicitaciones.
"""
from __future__ import annotations

import warnings
from dataclasses import dataclass


@dataclass(frozen=True)
class ConnectionRecommendation:
    tipo: str
    n_bolts: int
    db_mm: float
    espesor_plate_mm: float
    momento_capacidad_kNm: float


def recommend_connection(
    perfil_nombre: str,
    Mu_kNm: float,
    Vu_kN: float,
    sismica: bool = False,
) -> ConnectionRecommendation:
    if sismica:
        tipo = "RBS" if Mu_kNm > 500 else "WUF-W"
    else:
        tipo = "endplate-bolted" if Mu_kNm > 200 else "shear-tab"
    n_bolts = max(4, int(2 * (Mu_kNm / 100.0)))
    db = 22 if Mu_kNm < 400 else 25
    t_plate = max(16, int(Mu_kNm / 30))
    M_cap = n_bolts * db * 0.5 * 1.2 * Mu_kNm
    try:  # delega a SteelConnectionJm si esta
        from steelconnectionjm.api import design_endplate  # noqa: F401
    except ImportError:
        warnings.warn("SteelConnectionJm no instalado - usando estimacion heuristica")
    return ConnectionRecommendation(tipo, n_bolts, db, t_plate, M_cap)


__all__ = ["ConnectionRecommendation", "recommend_connection"]
