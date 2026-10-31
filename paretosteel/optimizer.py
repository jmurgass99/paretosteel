"""
optimizer.py - Heuristic optimization agent for structural steel frames.
"""
from typing import List, Dict

class SteelSectionOptimizer:
    """
    AI Copilot logic applied to structural member optimization.
    Inspired by advanced frame optimization algorithms (OSAFE).
    """
    def __init__(self, catalog: List[dict] = None):
        """
        :param catalog: Database of available steel sections with their properties.
        """
        self.catalog = catalog or [
            {"name": "IPE200", "type": "I-section", "mass_kg_m": 22.4, "W_y": 194.0, "i_z": 2.24},
            {"name": "HEB200", "type": "H-section", "mass_kg_m": 61.3, "W_y": 570.0, "i_z": 5.07},
            {"name": "IPE300", "type": "I-section", "mass_kg_m": 42.2, "W_y": 557.0, "i_z": 3.35},
        ]

    def analyze_beam(self, current_section: str, L: float, L_b: float, M_Ed: float, util_ratio: float, fail_mode: str) -> dict:
        """
        Evaluate a beam and propose an AI-driven optimization heuristic.
        
        :param current_section: Profile name (e.g. 'HEB200')
        :param L: Total length in m
        :param L_b: Unbraced length in m
        :param M_Ed: Design bending moment
        :param util_ratio: Current utilization ratio (e.g., 1.15 means fails by 15%)
        :param fail_mode: The failure mode reported by the OAPI (e.g., 'LTB', 'CrossSection')
        """
        suggestion = ""
        action = "NONE"
        saved_weight_pct = 0.0
        
        current_data = next((s for s in self.catalog if s["name"] == current_section), None)
        
        if fail_mode == "LTB":
            if L_b > L / 2.0:
                # Copilot Suggestion: Don't increase the section, just add lateral bracing
                suggestion = f"La viga {current_section} falla por Pandeo Lateral Torsional (LTB). El radio de giro i_z es bajo frente a L_b={L_b}m. Sugerencia: Añadir arriostramiento lateral a L/2. Esto evita sobredimensionar la sección."
                action = "ADD_BRACING"
            else:
                # Need a section with higher i_z (HEB instead of IPE, or wider flanges)
                suggestion = f"Falla por LTB con L_b corto. Recomiendo cambiar de un perfil esbelto a un perfil serie H (ej. HEB o HEA) con mayor inercia lateral."
                action = "CHANGE_TO_H_SECTION"
                
        elif fail_mode == "CrossSection" and util_ratio < 0.5:
            if current_data and current_data["type"] == "H-section":
                suggestion = f"El perfil actual {current_section} está sobredimensionado (Utilización = {util_ratio*100}%). Al estar sometido principalmente a flexión pura, un HEB es ineficiente en peso. Sugiero cambiar a la serie IPE (ej. IPE300)."
                action = "OPTIMIZE_WEIGHT"
                # Mock calculation of saved weight
                # HEB200 = 61.3 kg/m. IPE300 = 42.2 kg/m. Both have W_y ~ 560 cm3.
                saved_weight_pct = ((61.3 - 42.2) / 61.3) * 100
                suggestion += f" Ahorrarás aprox. un {saved_weight_pct:.1f}% de peso manteniendo la capacidad resistente."
        
        return {
            "current_section": current_section,
            "utilization": util_ratio,
            "failure_mode": fail_mode,
            "copilot_action": action,
            "copilot_suggestion": suggestion,
            "estimated_weight_savings_pct": round(saved_weight_pct, 2)
        }
