"""
optimizer.py - Heuristic optimization advisor for structural steel frames.
"""
from typing import List


class SteelSectionOptimizer:
    """
    Optimization logic applied to structural member optimization.
    Evaluates candidate sections from the catalog against actual demand and mass.
    """
    def __init__(self, catalog: List[dict] = None):
        """
        :param catalog: Database of available steel sections with their properties.
        """
        self.catalog = catalog or [
            {"name": "IPE200", "type": "I-section", "mass_kg_m": 22.4, "W_y": 194.0, "i_z": 2.24},
            {"name": "IPE240", "type": "I-section", "mass_kg_m": 30.7, "W_y": 324.0, "i_z": 2.69},
            {"name": "IPE270", "type": "I-section", "mass_kg_m": 36.1, "W_y": 429.0, "i_z": 3.02},
            {"name": "IPE300", "type": "I-section", "mass_kg_m": 42.2, "W_y": 557.0, "i_z": 3.35},
            {"name": "IPE360", "type": "I-section", "mass_kg_m": 57.1, "W_y": 904.0, "i_z": 3.79},
            {"name": "HEB200", "type": "H-section", "mass_kg_m": 61.3, "W_y": 570.0, "i_z": 5.07},
            {"name": "HEB240", "type": "H-section", "mass_kg_m": 83.2, "W_y": 938.0, "i_z": 6.08},
            {"name": "HEB300", "type": "H-section", "mass_kg_m": 117.0, "W_y": 1680.0, "i_z": 7.58},
        ]

    def analyze_beam(
        self,
        current_section: str,
        L: float,
        L_b: float,
        M_Ed: float,
        util_ratio: float,
        fail_mode: str,
    ) -> dict:
        """
        Evaluate a beam and propose an engineering optimization heuristic
        backed by actual catalog weight and section modulus comparisons.
        """
        suggestion = ""
        action = "NONE"
        saved_weight_pct = 0.0
        proposed_section = current_section

        current_data = next((s for s in self.catalog if s["name"] == current_section), None)

        if fail_mode == "LTB":
            if L_b > L / 2.0:
                suggestion = (
                    f"La viga {current_section} falla por Pandeo Lateral Torsional (LTB). "
                    f"El radio de giro i_z es bajo frente a L_b={L_b}m. "
                    f"Sugerencia: Añadir arriostramiento lateral a L/2 para evitar sobredimensionar la sección."
                )
                action = "ADD_BRACING"
            else:
                h_candidates = [
                    s for s in self.catalog
                    if s["type"] == "H-section"
                    and (current_data is None or s["i_z"] > current_data["i_z"])
                ]
                if h_candidates:
                    best_h = min(h_candidates, key=lambda s: s["mass_kg_m"])
                    proposed_section = best_h["name"]
                suggestion = (
                    f"Falla por LTB con L_b corto. Recomiendo cambiar de un perfil esbelto "
                    f"a un perfil serie H ({proposed_section}) con mayor inercia lateral."
                )
                action = "CHANGE_TO_H_SECTION"

        elif fail_mode == "CrossSection" and util_ratio < 0.5:
            if current_data and current_data["type"] == "H-section":
                req_wy = current_data["W_y"] * max(util_ratio, 0.95)
                i_candidates = [
                    s for s in self.catalog
                    if s["type"] == "I-section"
                    and s["W_y"] >= req_wy
                    and s["mass_kg_m"] < current_data["mass_kg_m"]
                ]
                if i_candidates:
                    best_i = min(i_candidates, key=lambda s: s["mass_kg_m"])
                    proposed_section = best_i["name"]
                    saved_weight_pct = ((current_data["mass_kg_m"] - best_i["mass_kg_m"]) / current_data["mass_kg_m"]) * 100.0
                suggestion = (
                    f"El perfil actual {current_section} está sobredimensionado (Utilización = {util_ratio*100:.1f}%). "
                    f"Al estar sometido principalmente a flexión pura, un HEB es ineficiente en peso. "
                    f"Sugiero cambiar a la serie IPE (ej. {proposed_section})."
                )
                action = "OPTIMIZE_WEIGHT"
                if saved_weight_pct > 0.0:
                    suggestion += f" Ahorrarás aprox. un {saved_weight_pct:.1f}% de peso manteniendo la capacidad resistente."

        return {
            "current_section": current_section,
            "proposed_section": proposed_section,
            "utilization": util_ratio,
            "failure_mode": fail_mode,
            "action": action,
            "recommended_action": action,
            "suggestion": suggestion,
            "recommendation": suggestion,
            "estimated_weight_savings_pct": round(saved_weight_pct, 2),
        }
