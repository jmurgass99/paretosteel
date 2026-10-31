"""Memoria handcalcs - Justificacion del perfil de acero seleccionado.

Genera un documento Markdown/LaTeX con:
    - Datos de entrada: luz, cargas, condiciones de apoyo
    - Seccion seleccionada: propiedades (A, Ix, Sx, Zx, rx, ry)
    - Verificaciones: flexion (Mn/Mu), cortante (Vn/Vu), deflexion (delta/delta_lim)
    - Veredicto: CUMPLE / NO CUMPLE con ratios

Usa handcalcs si disponible; caso contrario genera Markdown manual.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Optional

try:
    from handcalcs.decorator import handcalc
    _HAS_HANDCALCS = True
except ImportError:
    _HAS_HANDCALCS = False

    def handcalc(*args, **kwargs):
        def deco(f):
            return f
        return deco


# ---------------------------------------------------------------------------
# Datos de entrada
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ProfileMemoInput:
    """Datos de entrada para la memoria de justificacion.

    Atributos:
        section_name: nombre del perfil (e.g. 'W14X30').
        span_m: luz de la viga (m) o altura de columna.
        support_condition: condicion de apoyo ('simple', 'empotrado', 'voladizo').
        load_type: tipo de carga ('distribuida', 'puntual', 'axial').
        w_kN_m: carga distribuida (kN/m), si aplica.
        P_kN: carga puntual o axial (kN), si aplica.
        A_cm2: area de la seccion (cm2).
        Ix_cm4: inercia eje fuerte (cm4).
        Sx_cm3: modulo de seccion elastico (cm3).
        Zx_cm3: modulo de seccion plastico (cm3).
        rx_cm: radio de giro eje fuerte (cm).
        ry_cm: radio de giro eje debil (cm).
        Mu_kNm: momento ultimo solicitante (kN.m).
        Vu_kN: cortante ultimo solicitante (kN).
        Mn_kNm: momento nominal resistente (kN.m).
        Vn_kN: cortante nominal resistente (kN).
        delta_mm: deflexion calculada (mm).
        delta_limit_mm: deflexion limite (mm).
        Fy_MPa: tension de fluencia (MPa).
        code: codigo de diseno ('US', 'CO', 'EU').
    """
    section_name: str
    span_m: float
    support_condition: str = "simple"
    load_type: str = "distribuida"
    w_kN_m: float = 0.0
    P_kN: float = 0.0
    A_cm2: float = 0.0
    Ix_cm4: float = 0.0
    Sx_cm3: float = 0.0
    Zx_cm3: float = 0.0
    rx_cm: float = 0.0
    ry_cm: float = 0.0
    Mu_kNm: float = 0.0
    Vu_kN: float = 0.0
    Mn_kNm: float = 0.0
    Vn_kN: float = 0.0
    delta_mm: float = 0.0
    delta_limit_mm: float = 0.0
    Fy_MPa: float = 345.0
    code: str = "US"


@dataclass(frozen=True)
class ProfileMemoResult:
    """Resultado de la generacion de la memoria."""
    section_name: str
    ratio_flexion: float
    ratio_cortante: float
    ratio_deflexion: float
    cumple_flexion: bool
    cumple_cortante: bool
    cumple_deflexion: bool
    cumple: bool
    markdown: str
    latex: str


# ---------------------------------------------------------------------------
# Funciones handcalcs (con fallback)
# ---------------------------------------------------------------------------

if _HAS_HANDCALCS:
    @handcalc(override="long", precision=3)
    def _calc_flexion(Mu_kNm, phi_b, Mn_kNm):
        """Verificacion a flexion AISC 360 F2."""
        phi_Mn = phi_b * Mn_kNm
        ratio_M = Mu_kNm / phi_Mn
        return phi_Mn, ratio_M

    @handcalc(override="long", precision=3)
    def _calc_cortante(Vu_kN, phi_v, Vn_kN):
        """Verificacion a cortante AISC 360 G2."""
        phi_Vn = phi_v * Vn_kN
        ratio_V = Vu_kN / phi_Vn
        return phi_Vn, ratio_V

    @handcalc(override="long", precision=3)
    def _calc_deflexion(delta_mm, delta_limit_mm):
        """Verificacion de servicio por deflexion."""
        ratio_delta = delta_mm / delta_limit_mm
        return ratio_delta

    def _calc_flexion_safe(Mu_kNm, phi_b, Mn_kNm):
        return _calc_flexion(Mu_kNm, phi_b, Mn_kNm)

    def _calc_cortante_safe(Vu_kN, phi_v, Vn_kN):
        return _calc_cortante(Vu_kN, phi_v, Vn_kN)

    def _calc_deflexion_safe(delta_mm, delta_limit_mm):
        return _calc_deflexion(delta_mm, delta_limit_mm)

else:
    def _calc_flexion_safe(Mu_kNm, phi_b, Mn_kNm):
        phi_Mn = phi_b * Mn_kNm
        ratio_M = Mu_kNm / phi_Mn if phi_Mn > 0 else float("inf")
        latex = (
            f"\\phi_b \\cdot M_n = {phi_b:.2f} \\times {Mn_kNm:.2f}"
            f" = {phi_Mn:.2f} \\, \\text{{kN.m}}\n\n"
            f"\\frac{{M_u}}{{\\phi M_n}} = \\frac{{{Mu_kNm:.2f}}}"
            f"{{{phi_Mn:.2f}}} = {ratio_M:.3f}"
        )
        return latex, (phi_Mn, ratio_M)

    def _calc_cortante_safe(Vu_kN, phi_v, Vn_kN):
        phi_Vn = phi_v * Vn_kN
        ratio_V = Vu_kN / phi_Vn if phi_Vn > 0 else float("inf")
        latex = (
            f"\\phi_v \\cdot V_n = {phi_v:.2f} \\times {Vn_kN:.2f}"
            f" = {phi_Vn:.2f} \\, \\text{{kN}}\n\n"
            f"\\frac{{V_u}}{{\\phi V_n}} = \\frac{{{Vu_kN:.2f}}}"
            f"{{{phi_Vn:.2f}}} = {ratio_V:.3f}"
        )
        return latex, (phi_Vn, ratio_V)

    def _calc_deflexion_safe(delta_mm, delta_limit_mm):
        ratio_delta = (delta_mm / delta_limit_mm
                       if delta_limit_mm > 0 else float("inf"))
        latex = (
            f"\\frac{{\\delta}}{{\\delta_{{\\text{{lim}}}}}} "
            f"= \\frac{{{delta_mm:.2f}}}{{{delta_limit_mm:.2f}}} "
            f"= {ratio_delta:.3f}"
        )
        return latex, (ratio_delta,)


# ---------------------------------------------------------------------------
# Funcion principal
# ---------------------------------------------------------------------------

def render_profile_memo(inp: ProfileMemoInput) -> ProfileMemoResult:
    """Genera la memoria de justificacion del perfil seleccionado.

    Args:
        inp: ProfileMemoInput con todos los datos.

    Returns:
        ProfileMemoResult con markdown, latex y ratios.
    """
    # Factores LRFD
    code = inp.code.upper()
    if code in ("US", "CO"):
        phi_b = 0.90
        phi_v = 0.90
    elif code in ("EU", "SG"):
        phi_b = 1.00  # gamma_M0 = 1.0
        phi_v = 1.00
    else:
        phi_b = 0.90
        phi_v = 0.90

    # Calculos
    phi_Mn = phi_b * inp.Mn_kNm
    phi_Vn = phi_v * inp.Vn_kN

    ratio_M = inp.Mu_kNm / phi_Mn if phi_Mn > 0 else float("inf")
    ratio_V = inp.Vu_kN / phi_Vn if phi_Vn > 0 else float("inf")
    ratio_delta = (inp.delta_mm / inp.delta_limit_mm
                   if inp.delta_limit_mm > 0 else float("inf"))

    cumple_M = ratio_M <= 1.0 + 1e-9
    cumple_V = ratio_V <= 1.0 + 1e-9
    cumple_delta = ratio_delta <= 1.0 + 1e-9
    cumple = cumple_M and cumple_V and cumple_delta

    # Generar LaTeX con handcalcs o fallback
    latex_parts: list[str] = []

    latex_flex, _ = _calc_flexion_safe(inp.Mu_kNm, phi_b, inp.Mn_kNm)
    latex_parts.append(f"% Flexion\n{latex_flex}")

    latex_cort, _ = _calc_cortante_safe(inp.Vu_kN, phi_v, inp.Vn_kN)
    latex_parts.append(f"% Cortante\n{latex_cort}")

    if inp.delta_limit_mm > 0:
        latex_defl, _ = _calc_deflexion_safe(inp.delta_mm, inp.delta_limit_mm)
        latex_parts.append(f"% Deflexion\n{latex_defl}")

    latex = "\n\n".join(latex_parts)

    # Markdown
    veredicto = "CUMPLE" if cumple else "NO CUMPLE"
    veredicto_M = "OK" if cumple_M else "FALLA"
    veredicto_V = "OK" if cumple_V else "FALLA"
    veredicto_D = "OK" if cumple_delta else "FALLA"

    md_lines = [
        f"# Justificacion del Perfil Seleccionado: {inp.section_name}",
        "",
        "## 1. Datos de Entrada",
        "",
        f"- **Luz / Altura:** {inp.span_m:.2f} m",
        f"- **Condicion de apoyo:** {inp.support_condition}",
        f"- **Tipo de carga:** {inp.load_type}",
    ]

    if inp.w_kN_m > 0:
        md_lines.append(f"- **Carga distribuida:** {inp.w_kN_m:.2f} kN/m")
    if inp.P_kN > 0:
        md_lines.append(f"- **Carga puntual/axial:** {inp.P_kN:.2f} kN")
    md_lines.append(f"- **Fy:** {inp.Fy_MPa:.1f} MPa")
    md_lines.append(f"- **Codigo:** {inp.code}")

    md_lines.extend([
        "",
        f"## 2. Seccion Seleccionada: {inp.section_name}",
        "",
        "| Propiedad | Valor | Unidad |",
        "|-----------|------:|--------|",
        f"| A  | {inp.A_cm2:.2f} | cm2 |",
        f"| Ix | {inp.Ix_cm4:.2f} | cm4 |",
        f"| Sx | {inp.Sx_cm3:.2f} | cm3 |",
        f"| Zx | {inp.Zx_cm3:.2f} | cm3 |",
        f"| rx | {inp.rx_cm:.2f} | cm |",
        f"| ry | {inp.ry_cm:.2f} | cm |",
    ])

    md_lines.extend([
        "",
        "## 3. Verificaciones",
        "",
        "### 3.1 Flexion (AISC 360 F2)",
        "",
        f"- Mu = {inp.Mu_kNm:.2f} kN.m",
        f"- phi*Mn = {phi_Mn:.2f} kN.m",
        f"- **Mu / phi*Mn = {ratio_M:.3f}** -- {veredicto_M}",
        "",
        "### 3.2 Cortante (AISC 360 G2)",
        "",
        f"- Vu = {inp.Vu_kN:.2f} kN",
        f"- phi*Vn = {phi_Vn:.2f} kN",
        f"- **Vu / phi*Vn = {ratio_V:.3f}** -- {veredicto_V}",
        "",
        "### 3.3 Deflexion",
        "",
        f"- delta = {inp.delta_mm:.2f} mm",
        f"- delta_lim = {inp.delta_limit_mm:.2f} mm",
        f"- **delta / delta_lim = {ratio_delta:.3f}** -- {veredicto_D}",
    ])

    md_lines.extend([
        "",
        "## 4. Veredicto",
        "",
        f"### **{veredicto}**",
        "",
        "| Verificacion | Ratio | Limite | Estado |",
        "|-------------|------:|-------:|--------|",
        f"| Flexion    | {ratio_M:.3f} | 1.000 | {veredicto_M} |",
        f"| Cortante   | {ratio_V:.3f} | 1.000 | {veredicto_V} |",
        f"| Deflexion  | {ratio_delta:.3f} | 1.000 | {veredicto_D} |",
        "",
    ])

    markdown = "\n".join(md_lines)

    return ProfileMemoResult(
        section_name=inp.section_name,
        ratio_flexion=ratio_M,
        ratio_cortante=ratio_V,
        ratio_deflexion=ratio_delta,
        cumple_flexion=cumple_M,
        cumple_cortante=cumple_V,
        cumple_deflexion=cumple_delta,
        cumple=cumple,
        markdown=markdown,
        latex=latex,
    )


# ---------------------------------------------------------------------------
# Convenience function para usar con resultados de beam_selector
# ---------------------------------------------------------------------------

def memo_from_beam_candidate(
    candidate,
    span_m: float,
    w_kN_m: float = 0.0,
    deflection_limit: float = 360.0,
    Fy_MPa: float = 345.0,
    code: str = "US",
) -> ProfileMemoResult:
    """Genera memo desde un BeamCandidate del beam_selector.

    Args:
        candidate: BeamCandidate con name, Mn_design_kNm, Vn_design_kN, etc.
        span_m: luz de la viga.
        w_kN_m: carga distribuida de servicio.
        deflection_limit: L/N para deflexion.
        Fy_MPa: fluencia.
        code: codigo de diseno.

    Returns:
        ProfileMemoResult.
    """
    from ..catalog_unified import all_sections
    from ..deflection import deflection_udl

    # Buscar seccion en catalogo unificado
    sec = None
    for s in all_sections():
        if s.name == candidate.name:
            sec = s
            break

    if sec is None:
        # Fallback: datos minimos
        return render_profile_memo(ProfileMemoInput(
            section_name=candidate.name,
            span_m=span_m,
            w_kN_m=w_kN_m,
            Mu_kNm=candidate.flexural_ratio * candidate.Mn_design_kNm,
            Vu_kN=candidate.shear_ratio * candidate.Vn_design_kN,
            Mn_kNm=candidate.Mn_design_kNm,
            Vn_kN=candidate.Vn_design_kN,
            Fy_MPa=Fy_MPa,
            code=code,
        ))

    # Con datos completos del catalogo
    A_cm2 = sec.A_cm2
    Ix_cm4 = sec.Ix_cm4
    Zx_cm3 = sec.Zx_cm3
    Sx_cm3 = Ix_cm4 / (sec.h_mm / 20.0) if sec.h_mm > 0 else 0.0  # Ix/c
    rx_cm = math.sqrt(Ix_cm4 / A_cm2) if A_cm2 > 0 else 0.0
    ry_cm = math.sqrt(sec.Iy_cm4 / A_cm2) if A_cm2 > 0 else 0.0

    Mu = candidate.flexural_ratio * candidate.Mn_design_kNm
    Vu = candidate.shear_ratio * candidate.Vn_design_kN

    # Deflexion
    delta_mm = 0.0
    delta_limit_mm = span_m * 1000.0 / deflection_limit
    if w_kN_m > 0 and Ix_cm4 > 0:
        w_N_mm = w_kN_m * 1000.0 / 1000.0  # kN/m -> N/mm
        L_mm = span_m * 1000.0
        I_mm4 = Ix_cm4 * 1e4  # cm4 -> mm4
        delta_mm = deflection_udl(w_N_mm, L_mm, I_mm4)

    return render_profile_memo(ProfileMemoInput(
        section_name=candidate.name,
        span_m=span_m,
        support_condition="simple",
        load_type="distribuida",
        w_kN_m=w_kN_m,
        A_cm2=A_cm2,
        Ix_cm4=Ix_cm4,
        Sx_cm3=Sx_cm3,
        Zx_cm3=Zx_cm3,
        rx_cm=rx_cm,
        ry_cm=ry_cm,
        Mu_kNm=Mu,
        Vu_kN=Vu,
        Mn_kNm=candidate.Mn_design_kNm,
        Vn_kN=candidate.Vn_design_kN,
        delta_mm=delta_mm,
        delta_limit_mm=delta_limit_mm,
        Fy_MPa=Fy_MPa,
        code=code,
    ))


__all__ = [
    "ProfileMemoInput",
    "ProfileMemoResult",
    "render_profile_memo",
    "memo_from_beam_candidate",
]
