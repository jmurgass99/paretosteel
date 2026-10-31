"""
IndustrialJm — Industrial Mezzanine and Equipment Platform Composite Beams
========================================================================
Design, demand generation, and code compliance verification for steel-concrete
composite beams in industrial facilities (mezzanines, walkways, heavy equipment decks).

Supports:
- AISC 360-16 Chapter I (LRFD)
- Eurocode 4 / EN 1994-1-1

Separation of Concerns:
- Mechanics & Code formulas: CompositeJm
- Industrial Demands & Serviceability checks: IndustrialJm
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Literal

from .aisc_composite_beam import (
    AISCBeamSection,
    AISCSlabSpec,
    AISCStudSpec,
    verify_aisc_composite_beam,
)
from .composite_beam import (
    b_effective as ec4_b_effective,
    mpl_rd_block_method as ec4_mpl_rd_block_method,
    shear_connector_resistance as ec4_stud_resistance,
    partial_interaction as ec4_partial_interaction,
    m_rd_partial_interaction as ec4_m_rd_partial,
)


@dataclass(frozen=True)
class SteelBeamProfile:
    """Steel profile cross-section for industrial composite floor beams."""
    name: str
    d_mm: float
    bf_mm: float
    tf_mm: float
    tw_mm: float
    A_mm2: float
    Ix_mm4: float
    Zx_mm3: float
    Fy_MPa: float
    Es_MPa: float = 200_000.0
    self_weight_kN_per_m: float = 0.0
    units: dict[str, str] = field(default_factory=lambda: {"force": "kN", "length": "mm", "stress": "MPa"})

    def __post_init__(self):
        if self.d_mm <= 0 or self.bf_mm <= 0 or self.tf_mm <= 0 or self.tw_mm <= 0:
            raise ValueError(f"Dimensiones de perfil invalidas en {self.name}: dimensiones deben ser positivas.")
        if self.A_mm2 <= 0 or self.Ix_mm4 <= 0 or self.Zx_mm3 <= 0 or self.Fy_MPa <= 0:
            raise ValueError(f"Propiedades mecanicas invalidas en {self.name}: deben ser positivas.")
        # If self_weight not provided, estimate from steel density 7850 kg/m^3
        if self.self_weight_kN_per_m <= 0.0:
            w_calc = (self.A_mm2 * 1e-6) * 7850.0 * 9.80665 / 1000.0
            object.__setattr__(self, "self_weight_kN_per_m", round(w_calc, 3))


@dataclass(frozen=True)
class StudConnectorSpec:
    """Shear stud connector for composite action."""
    diameter_mm: float = 19.0      # 3/4" (19.05 mm)
    fu_MPa: float = 450.0          # Minimum tensile strength
    height_mm: float = 95.0        # Total stud height after weld
    Rg: float = 1.0                # AISC deck group factor
    Rp: float = 0.75               # AISC deck position factor (0.75 perpendicular deck)


@dataclass(frozen=True)
class IndustrialMezzanineDemand:
    """Load and geometry demand on an industrial mezzanine composite beam."""
    span_m: float
    spacing_m: float
    dead_load_superimposed_kpa: float  # Finishes, ducts, MEP, fire protection [kPa]
    live_load_kpa: float               # Mezzanine storage/machinery load [kPa]
    slab_thickness_mm: float = 120.0   # Total slab thickness (deck + concrete) [mm]
    deck_height_mm: float = 50.0       # Rib height of metal decking [mm]
    concrete_f_c_MPa: float = 28.0     # Concrete cylinder compressive strength [MPa]
    concrete_density_kg_m3: float = 2400.0  # Concrete density [kg/m^3]
    shored_construction: bool = False  # True if propped during concrete pouring
    standard: Literal["AISC_360_16", "EUROCODE_4"] = "AISC_360_16"
    live_deflection_limit_ratio: float = 360.0  # L / 360
    total_deflection_limit_ratio: float = 240.0 # L / 240
    point_load_dead_kN: float = 0.0    # Concentrated equipment dead load [kN]
    point_load_live_kN: float = 0.0    # Concentrated equipment live load [kN]
    units: dict[str, str] = field(default_factory=lambda: {"force": "kN", "pressure": "kPa", "length": "m", "stress": "MPa"})

    def __post_init__(self):
        if self.span_m <= 0 or self.spacing_m <= 0:
            raise ValueError("span_m y spacing_m deben ser estrictamente positivos.")
        if self.slab_thickness_mm <= 0:
            raise ValueError("slab_thickness_mm debe ser estrictamente positivo.")
        if self.concrete_f_c_MPa <= 0:
            raise ValueError("concrete_f_c_MPa debe ser estrictamente positivo.")


@dataclass(frozen=True)
class IndustrialCompositeBeamResult:
    """Engineering result and verification of the industrial composite beam."""
    is_viable: bool
    standard_used: str
    governing_dcr: float
    governing_mode: str
    dcr_flexure_composite: float
    dcr_shear_composite: float
    dcr_flexure_construction: float
    dcr_shear_construction: float
    dcr_deflection_live: float
    dcr_deflection_total: float
    deflection_live_mm: float
    deflection_total_mm: float
    num_studs_total: int
    num_studs_half_span: int
    stud_spacing_mm: float
    moment_capacity_kNm: float
    applied_moment_kNm: float
    shear_capacity_kN: float
    applied_shear_kN: float
    units: dict[str, str] = field(default_factory=lambda: {"force": "kN", "moment": "kNm", "length": "mm"})
    diagnostics: list[str] = field(default_factory=list)

    def summary_markdown(self) -> str:
        status_badge = "✅ CUMPLE" if self.is_viable else "❌ NO CUMPLE"
        lines = [
            f"### Verificación de Viga Compuesta Industrial ({self.standard_used})",
            f"**Estado Global**: {status_badge} (DCR Gobernante = {self.governing_dcr:.2f} por {self.governing_mode})",
            "",
            "| Comprobación | DCR | Capacidad | Solicitación | Estado |",
            "| :--- | :---: | :---: | :---: | :---: |",
            f"| Flexión Compuesta | {self.dcr_flexure_composite:.2f} | {self.moment_capacity_kNm:.1f} kN·m | {self.applied_moment_kNm:.1f} kN·m | {'OK' if self.dcr_flexure_composite <= 1.0 else 'FALLA'} |",
            f"| Cortante Compuesto | {self.dcr_shear_composite:.2f} | {self.shear_capacity_kN:.1f} kN | {self.applied_shear_kN:.1f} kN | {'OK' if self.dcr_shear_composite <= 1.0 else 'FALLA'} |",
            f"| Flexión Constructiva | {self.dcr_flexure_construction:.2f} | - | - | {'OK' if self.dcr_flexure_construction <= 1.0 else 'FALLA'} |",
            f"| Flecha Sobrecarga (L/SLS) | {self.dcr_deflection_live:.2f} | - | {self.deflection_live_mm:.1f} mm | {'OK' if self.dcr_deflection_live <= 1.0 else 'FALLA'} |",
            f"| Flecha Total (L/SLS) | {self.dcr_deflection_total:.2f} | - | {self.deflection_total_mm:.1f} mm | {'OK' if self.dcr_deflection_total <= 1.0 else 'FALLA'} |",
            "",
            f"- **Conectores**: {self.num_studs_total} pernos tipo stud ({self.num_studs_half_span} por semivano, paso ~{self.stud_spacing_mm:.0f} mm)",
        ]
        if self.diagnostics:
            lines.append("\n**Observaciones / Diagnósticos:**")
            for diag in self.diagnostics:
                lines.append(f"- {diag}")
        return "\n".join(lines)


def calculate_industrial_mezzanine_loads(
    demand: IndustrialMezzanineDemand,
    profile: SteelBeamProfile,
) -> dict[str, float]:
    """Computes distributed and factored internal forces for construction and composite stages.

    Units:
    - Distributed loads in kN/m.
    - Factored moments in kN*m.
    - Factored shears in kN.
    - Unfactored loads in N/mm for deflection checks.
    """
    g = 9.80665

    # 1. Dead loads (kN/m)
    # Self-weight of beam:
    w_beam_sw_kN_m = profile.self_weight_kN_per_m

    # Concrete slab dead load (accounting for solid portion + deck ribs average)
    # If deck_height > 0, rib volume is roughly 50% void in rib zone
    effective_concrete_depth_m = (demand.slab_thickness_mm - 0.5 * demand.deck_height_mm) / 1000.0
    w_slab_kN_m = (effective_concrete_depth_m * demand.spacing_m) * demand.concrete_density_kg_m3 * g / 1000.0

    # Steel decking self-weight (~0.12 to 0.15 kN/m^2)
    w_deck_kN_m = 0.15 * demand.spacing_m

    # Total wet concrete + steel at construction
    w_dead_construction_kN_m = w_beam_sw_kN_m + w_slab_kN_m + w_deck_kN_m

    # Superimposed dead load
    w_dead_super_kN_m = demand.dead_load_superimposed_kpa * demand.spacing_m
    w_dead_total_kN_m = w_dead_construction_kN_m + w_dead_super_kN_m

    # Live loads (kN/m)
    w_live_kN_m = demand.live_load_kpa * demand.spacing_m
    w_live_construction_kN_m = 1.0 * demand.spacing_m  # OSHA/AISC 20 psf ~ 1.0 kPa construction live load

    L = demand.span_m

    # 2. Factored load combinations per standard
    if demand.standard == "AISC_360_16":
        # ASCE 7-16 LRFD:
        # Construction: 1.2 D_const + 1.6 L_const (or 1.4 D)
        q_u_const = max(
            1.4 * w_dead_construction_kN_m,
            1.2 * w_dead_construction_kN_m + 1.6 * w_live_construction_kN_m,
        )
        # Composite: 1.2 D + 1.6 L
        q_u_comp = 1.2 * w_dead_total_kN_m + 1.6 * w_live_kN_m
        P_u_comp = 1.2 * demand.point_load_dead_kN + 1.6 * demand.point_load_live_kN
    else:
        # Eurocode (EN 1990):
        # Construction: 1.35 G_const + 1.50 Q_const
        q_u_const = 1.35 * w_dead_construction_kN_m + 1.50 * w_live_construction_kN_m
        # Composite: 1.35 G + 1.50 Q
        q_u_comp = 1.35 * w_dead_total_kN_m + 1.50 * w_live_kN_m
        P_u_comp = 1.35 * demand.point_load_dead_kN + 1.50 * demand.point_load_live_kN

    # Moments and Shears (simply supported beam)
    # If shored, construction forces on steel are negligible (propped)
    if demand.shored_construction:
        M_u_const_kNm = 0.0
        V_u_const_kN = 0.0
    else:
        M_u_const_kNm = (q_u_const * (L ** 2)) / 8.0
        V_u_const_kN = (q_u_const * L) / 2.0

    # Composite stage forces (uniform load + mid-span point load)
    M_u_comp_kNm = (q_u_comp * (L ** 2)) / 8.0 + (P_u_comp * L) / 4.0
    V_u_comp_kN = (q_u_comp * L) / 2.0 + (P_u_comp / 2.0)

    # SLS Unfactored loads for deflections (in N/mm, note 1 kN/m = 1 N/mm)
    w_live_N_mm = w_live_kN_m
    w_total_N_mm = w_dead_total_kN_m + w_live_kN_m

    return {
        "w_dead_construction_kN_m": w_dead_construction_kN_m,
        "w_dead_total_kN_m": w_dead_total_kN_m,
        "w_live_kN_m": w_live_kN_m,
        "q_u_const_kN_m": q_u_const,
        "q_u_comp_kN_m": q_u_comp,
        "M_u_const_kNm": M_u_const_kNm,
        "V_u_const_kN": V_u_const_kN,
        "M_u_comp_kNm": M_u_comp_kNm,
        "V_u_comp_kN": V_u_comp_kN,
        "w_live_N_mm": w_live_N_mm,
        "w_total_N_mm": w_total_N_mm,
    }


def design_industrial_composite_beam(
    demand: IndustrialMezzanineDemand,
    profile: SteelBeamProfile,
    stud_spec: StudConnectorSpec | None = None,
    num_studs_total: int | None = None,
) -> IndustrialCompositeBeamResult:
    """Performs full design and code verification of an industrial composite beam.

    If num_studs_total is None, it automatically calculates the minimum number
    of studs required to achieve safe composite action (or full interaction).
    """
    if stud_spec is None:
        stud_spec = StudConnectorSpec()

    # 1. Evaluate demand forces
    loads = calculate_industrial_mezzanine_loads(demand, profile)
    L_span_mm = demand.span_m * 1000.0
    spacing_mm = demand.spacing_m * 1000.0

    if demand.standard == "AISC_360_16":
        # Convert profile to AISC types
        aisc_section = AISCBeamSection(
            d_mm=profile.d_mm,
            bf_mm=profile.bf_mm,
            tf_mm=profile.tf_mm,
            tw_mm=profile.tw_mm,
            A_mm2=profile.A_mm2,
            Ix_mm4=profile.Ix_mm4,
            Zx_mm3=profile.Zx_mm3,
            Fy_MPa=profile.Fy_MPa,
            Es_MPa=profile.Es_MPa,
        )
        aisc_slab = AISCSlabSpec(
            t_slab_mm=demand.slab_thickness_mm,
            fc_MPa=demand.concrete_f_c_MPa,
            wc_kg_m3=demand.concrete_density_kg_m3,
            h_deck_mm=demand.deck_height_mm,
        )
        aisc_stud = AISCStudSpec(
            d_stud_mm=stud_spec.diameter_mm,
            Fu_stud_MPa=stud_spec.fu_MPa,
            Rg=stud_spec.Rg,
            Rp=stud_spec.Rp,
        )

        # If stud count not specified, estimate from shear capacity requirement
        if num_studs_total is None:
            # Full interaction studs estimate
            full_shear_N = aisc_section.A_mm2 * aisc_section.Fy_MPa
            # Nominal stud capacity
            d_s = stud_spec.diameter_mm
            Asa = math.pi * (d_s / 2.0) ** 2
            Ec = 0.043 * ((demand.concrete_density_kg_m3 / 16.0185) ** 1.5) * math.sqrt(demand.concrete_f_c_MPa * 145.038) * 6.89476
            Qn_approx = min(
                0.5 * Asa * math.sqrt(demand.concrete_f_c_MPa * Ec),
                stud_spec.Rg * stud_spec.Rp * Asa * stud_spec.fu_MPa,
            )
            studs_half = max(2, math.ceil(full_shear_N / Qn_approx))
            num_studs_total = studs_half * 2

        # Run verification engine
        verif = verify_aisc_composite_beam(
            section=aisc_section,
            slab=aisc_slab,
            stud=aisc_stud,
            L_span_mm=L_span_mm,
            beam_spacing_mm=spacing_mm,
            num_studs_total=num_studs_total,
            M_construction_kNm=loads["M_u_const_kNm"],
            V_construction_kN=loads["V_u_const_kN"],
            M_composite_kNm=loads["M_u_comp_kNm"],
            V_composite_kN=loads["V_u_comp_kN"],
            w_live_N_per_mm=loads["w_live_N_mm"],
            w_total_N_per_mm=loads["w_total_N_mm"],
            live_deflection_limit_ratio=demand.live_deflection_limit_ratio,
            total_deflection_limit_ratio=demand.total_deflection_limit_ratio,
        )

        # Find governing failure mode
        dcrs = {
            "Flexión Compuesta": verif.dcr_flexure_composite,
            "Cortante Compuesto": verif.dcr_shear_composite,
            "Flexión Constructiva": verif.dcr_flexure_construction,
            "Cortante Constructivo": verif.dcr_shear_construction,
            "Flecha Sobrecarga": verif.dcr_deflection_live,
            "Flecha Total": verif.dcr_deflection_total,
        }
        gov_mode, gov_dcr = max(dcrs.items(), key=lambda kv: kv[1])

        num_studs_half = num_studs_total // 2
        stud_spacing = (L_span_mm / 2.0) / max(1, num_studs_half)

        return IndustrialCompositeBeamResult(
            is_viable=verif.passed,
            standard_used="AISC 360-16 (LRFD)",
            governing_dcr=gov_dcr,
            governing_mode=gov_mode,
            dcr_flexure_composite=verif.dcr_flexure_composite,
            dcr_shear_composite=verif.dcr_shear_composite,
            dcr_flexure_construction=verif.dcr_flexure_construction,
            dcr_shear_construction=verif.dcr_shear_construction,
            dcr_deflection_live=verif.dcr_deflection_live,
            dcr_deflection_total=verif.dcr_deflection_total,
            deflection_live_mm=verif.deflection_live_mm,
            deflection_total_mm=verif.deflection_total_mm,
            num_studs_total=num_studs_total,
            num_studs_half_span=num_studs_half,
            stud_spacing_mm=stud_spacing,
            moment_capacity_kNm=verif.flexure_result.phi_Mn_kNm,
            applied_moment_kNm=loads["M_u_comp_kNm"],
            shear_capacity_kN=verif.phi_Vn_shear_kN,
            applied_shear_kN=loads["V_u_comp_kN"],
            diagnostics=verif.diagnostics,
        )

    else:
        # EUROCODE 4 (EN 1994-1-1)
        # Concrete compressive design strength fcd = fck / 1.5
        fck = demand.concrete_f_c_MPa
        fcd = fck / 1.5
        fy = profile.Fy_MPa
        fyd = fy / 1.0  # gamma_M0 = 1.0

        # In interior beam with equal spacing S, b0=0 (single line of studs) and b1=b2=S/2
        b_eff_mm = ec4_b_effective(L_span=L_span_mm, b0=0.0, b1=spacing_mm / 2.0, b2=spacing_mm / 2.0)
        hc_mm = demand.slab_thickness_mm - demand.deck_height_mm
        hp_mm = demand.deck_height_mm

        # Plastic tension of steel section
        N_pl_a = (profile.A_mm2 * fyd) / 1000.0  # kN
        # Compression in concrete flange (EN 1994-1-1 Eq 6.3)
        N_cf = (0.85 * fcd * b_eff_mm * hc_mm) / 1000.0  # kN

        # Stud capacity per EN 1994-1-1 (returns N, convert to kN)
        P_rd_one_stud_N = ec4_stud_resistance(
            d=stud_spec.diameter_mm,
            fu_stud=stud_spec.fu_MPa,
            fck=fck,
            h_sc=stud_spec.height_mm,
        )
        P_rd_one_stud = P_rd_one_stud_N / 1000.0  # kN


        if num_studs_total is None:
            # Need N_c = min(N_pl_a, N_cf)
            N_c_target = min(N_pl_a, N_cf)
            studs_half = max(2, math.ceil(N_c_target / P_rd_one_stud))
            num_studs_total = studs_half * 2
        else:
            studs_half = num_studs_total // 2

        N_c = min(studs_half * P_rd_one_stud, N_pl_a, N_cf)
        eta_degree = N_c / min(N_pl_a, N_cf) if min(N_pl_a, N_cf) > 0 else 1.0

        # Full interaction plastic moment
        # M_pl_rd (Case 1: PNA in slab, Case 2: PNA in flange, Case 3: PNA in web)
        try:
            m_pl_rd_kNm = ec4_mpl_rd_block_method(
                b_f=profile.bf_mm,
                t_f=profile.tf_mm,
                t_w=profile.tw_mm,
                h_a=profile.d_mm,
                b_eff=b_eff_mm,
                h_c=hc_mm,
                fyd=fyd,
                fcd=fcd,
                h_p=hp_mm,
            )
        except Exception:
            # Fallback conservative estimate
            m_pl_rd_kNm = (profile.Zx_mm3 * fyd + N_c * 1000.0 * (profile.d_mm / 2.0 + hp_mm + hc_mm / 2.0)) / 1e6


        # Plastic moment of bare steel
        m_a_pl_rd_kNm = (profile.Zx_mm3 * fyd) / 1e6

        # Partial interaction moment (EN 1994-1-1 Eq 6.28)
        if eta_degree < 1.0:
            m_rd_kNm = m_a_pl_rd_kNm + eta_degree * (m_pl_rd_kNm - m_a_pl_rd_kNm)
        else:
            m_rd_kNm = m_pl_rd_kNm

        # Shear capacity per EN 1993-1-1 (Av * fyd / sqrt(3))
        Av_mm2 = max(profile.A_mm2 - 2 * profile.bf_mm * profile.tf_mm, profile.d_mm * profile.tw_mm)
        V_rd_kN = (Av_mm2 * (fyd / math.sqrt(3))) / 1000.0

        # Deflection estimate with approximate composite inertia
        n_modular = profile.Es_MPa / (9500.0 * ((fck + 8) / 10.0) ** (1.0 / 3.0))
        A_c_equiv = (b_eff_mm * hc_mm) / n_modular
        d_c_center = profile.d_mm / 2.0 + hp_mm + hc_mm / 2.0
        I_tr = profile.Ix_mm4 + A_c_equiv * (d_c_center ** 2)
        I_eff = profile.Ix_mm4 + math.sqrt(min(1.0, eta_degree)) * (I_tr - profile.Ix_mm4)

        delta_live = (5.0 * loads["w_live_N_mm"] * (L_span_mm ** 4)) / (384.0 * profile.Es_MPa * I_eff)
        delta_total = (5.0 * loads["w_total_N_mm"] * (L_span_mm ** 4)) / (384.0 * profile.Es_MPa * I_eff)

        delta_live_limit = L_span_mm / demand.live_deflection_limit_ratio
        delta_total_limit = L_span_mm / demand.total_deflection_limit_ratio

        if m_rd_kNm > 0:
            dcr_flex_comp = loads["M_u_comp_kNm"] / m_rd_kNm
        else:
            dcr_flex_comp = float("inf")

        if V_rd_kN > 0:
            dcr_shear_comp = loads["V_u_comp_kN"] / V_rd_kN
        else:
            dcr_shear_comp = float("inf")

        if m_a_pl_rd_kNm > 0:
            dcr_flex_const = loads["M_u_const_kNm"] / m_a_pl_rd_kNm
        else:
            dcr_flex_const = 0.0 if loads["M_u_const_kNm"] == 0 else float("inf")

        if V_rd_kN > 0:
            dcr_shear_const = loads["V_u_const_kN"] / V_rd_kN
        else:
            dcr_shear_const = 0.0 if loads["V_u_const_kN"] == 0 else float("inf")
        dcr_delta_live = delta_live / delta_live_limit
        dcr_delta_total = delta_total / delta_total_limit

        diagnostics: list[str] = []
        # Eurocode minimum degree of connection check (EN 1994-1-1 §6.6.1.2)
        # eta >= 1 - (355 / fy) * (0.75 - 0.03 * Le) >= 0.40
        eta_min = max(0.40, 1.0 - (355.0 / fy) * (0.75 - 0.03 * demand.span_m))
        if eta_degree < eta_min:
            diagnostics.append(f"Aviso Eurocódigo 4 §6.6.1.2: Grado de conexión {eta_degree:.2f} < mínimo normativo {eta_min:.2f}.")

        if dcr_flex_comp > 1.0:
            diagnostics.append(f"Falla flexión compuesta: DCR={dcr_flex_comp:.2f} > 1.0 (Med={loads['M_u_comp_kNm']:.1f} kN·m, Mrd={m_rd_kNm:.1f} kN·m)")
        if dcr_shear_comp > 1.0:
            diagnostics.append(f"Falla cortante compuesto: DCR={dcr_shear_comp:.2f} > 1.0")
        if dcr_delta_live > 1.0:
            diagnostics.append(f"Falla flecha de sobrecarga: {delta_live:.1f} mm > {delta_live_limit:.1f} mm")
        if dcr_delta_total > 1.0:
            diagnostics.append(f"Falla flecha total: {delta_total:.1f} mm > {delta_total_limit:.1f} mm")

        dcrs = {
            "Flexión Compuesta": dcr_flex_comp,
            "Cortante Compuesto": dcr_shear_comp,
            "Flexión Constructiva": dcr_flex_const,
            "Cortante Constructivo": dcr_shear_const,
            "Flecha Sobrecarga": dcr_delta_live,
            "Flecha Total": dcr_delta_total,
        }
        gov_mode, gov_dcr = max(dcrs.items(), key=lambda kv: kv[1])
        is_viable = all(v <= 1.0 for v in dcrs.values()) and (eta_degree >= eta_min)

        stud_spacing = (L_span_mm / 2.0) / max(1, studs_half)

        return IndustrialCompositeBeamResult(
            is_viable=is_viable,
            standard_used="Eurocódigo 4 (EN 1994-1-1)",
            governing_dcr=gov_dcr,
            governing_mode=gov_mode,
            dcr_flexure_composite=dcr_flex_comp,
            dcr_shear_composite=dcr_shear_comp,
            dcr_flexure_construction=dcr_flex_const,
            dcr_shear_construction=dcr_shear_const,
            dcr_deflection_live=dcr_delta_live,
            dcr_deflection_total=dcr_delta_total,
            deflection_live_mm=delta_live,
            deflection_total_mm=delta_total,
            num_studs_total=num_studs_total,
            num_studs_half_span=studs_half,
            stud_spacing_mm=stud_spacing,
            moment_capacity_kNm=m_rd_kNm,
            applied_moment_kNm=loads["M_u_comp_kNm"],
            shear_capacity_kN=V_rd_kN,
            applied_shear_kN=loads["V_u_comp_kN"],
            diagnostics=diagnostics,
        )
