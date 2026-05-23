"""Bridge SteelOptimizerJm -> FastSAP: usa SAP como evaluador real del optimizer.

Cada llamada al evaluator() corre un analisis (real o mock) y devuelve solicitaciones.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class FastSAPEvaluator:
    client: Any = None
    dry_run: bool = False

    def evaluate(self, perfil_genes: list[float]) -> dict:
        """Evalua un perfil candidato. genes = [h_mm, bf_mm, tw_mm, tf_mm]."""
        if self.dry_run or self.client is None:
            h, bf, tw, tf = perfil_genes[:4]
            A = h * tw + 2 * bf * tf
            I = (bf * h ** 3 - (bf - tw) * (h - 2 * tf) ** 3) / 12.0
            # estimacion ficticia: Mu = q*L^2/8 con L=6m, q=20kN/m
            Mu = 20.0 * 6.0 ** 2 / 8.0
            Vu = 20.0 * 6.0 / 2.0
            return {"Mu_kNm": Mu, "Vu_kN": Vu, "Pu_kN": 0.0,
                    "A_mm2": A, "Ix_mm4": I, "dry_run": True}
        # caso con client real
        try:
            self.client.Analyze.RunAnalysis()
            Mu = float(self.client.Results.FrameForce("BEAM1")[3])
            Vu = float(self.client.Results.FrameForce("BEAM1")[2])
            return {"Mu_kNm": Mu, "Vu_kN": Vu, "Pu_kN": 0.0,
                    "A_mm2": 0, "Ix_mm4": 0, "dry_run": False}
        except Exception as e:  # pragma: no cover
            return {"error": str(e)}


__all__ = ["FastSAPEvaluator"]
