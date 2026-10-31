"""Memoria handcalcs - Justificacion del perfil seleccionado.

Genera markdown documentando: solicitaciones, capacidad, ratios y verificacion final.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class JustificacionInput:
    perfil_nombre: str
    Mu_kNm: float
    Vu_kN: float
    Pu_kN: float
    Mn_kNm: float
    Vn_kN: float
    Pn_kN: float
    fy_MPa: float = 345.0
    code: str = "US"


@dataclass(frozen=True)
class JustificacionResult:
    ratio_M: float
    ratio_V: float
    ratio_P: float
    ratio_combinado: float
    cumple: bool
    markdown: str


def justificar(inp: JustificacionInput) -> JustificacionResult:
    phi_b = 0.9
    phi_v = 0.9
    phi_c = 0.9
    rM = abs(inp.Mu_kNm) / (phi_b * inp.Mn_kNm) if inp.Mn_kNm > 0 else 99
    rV = abs(inp.Vu_kN) / (phi_v * inp.Vn_kN) if inp.Vn_kN > 0 else 99
    rP = abs(inp.Pu_kN) / (phi_c * inp.Pn_kN) if inp.Pn_kN > 0 else 0
    # AISC H1
    if rP >= 0.2:
        ic = rP + 8.0 / 9.0 * rM
    else:
        ic = rP / 2.0 + rM
    md = (
        f"# Justificacion - {inp.perfil_nombre}\n\n"
        f"## Solicitaciones\n- Mu = {inp.Mu_kNm} kNm\n- Vu = {inp.Vu_kN} kN\n- Pu = {inp.Pu_kN} kN\n\n"
        f"## Capacidades\n- phi*Mn = {phi_b*inp.Mn_kNm:.2f}\n- phi*Vn = {phi_v*inp.Vn_kN:.2f}\n- phi*Pn = {phi_c*inp.Pn_kN:.2f}\n\n"
        f"## Ratios\n- M: {rM:.3f}\n- V: {rV:.3f}\n- P: {rP:.3f}\n- Combinado (AISC H1): {ic:.3f}\n\n"
        f"## Veredicto: {'CUMPLE' if ic <= 1.0 and rV <= 1.0 else 'NO CUMPLE'}\n"
    )
    return JustificacionResult(rM, rV, rP, ic, ic <= 1.0 and rV <= 1.0, md)


__all__ = ["JustificacionInput", "JustificacionResult", "justificar"]
