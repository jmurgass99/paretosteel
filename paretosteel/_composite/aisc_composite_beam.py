"""AISC 360-16 Chapter I — Design of Composite Steel-Concrete Beams.

Conventions (SI mm/N):
- Dimensions in mm (lengths, thicknesses, widths).
- Forces in N.
- Stresses / strengths in MPa (N/mm^2).
- Bending moments returned in kN*m.
- Factor of safety / resistance factors:
  - LRFD: phi_b = 0.90 for flexure, phi_v = 0.90 for shear.
  - ASD: Omega_b = 1.67 for flexure, Omega_v = 1.67 for shear.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Any, Literal


@dataclass(frozen=True)
class AISCBeamSection:
    """Steel I-shaped beam geometry and material properties."""
    d_mm: float          # Overall section depth
    bf_mm: float         # Flange width
    tf_mm: float         # Flange thickness
    tw_mm: float         # Web thickness
    A_mm2: float         # Steel cross-sectional area
    Ix_mm4: float        # Moment of inertia about major axis
    Zx_mm3: float        # Plastic section modulus about major axis
    Fy_MPa: float        # Yield stress (e.g. 345 MPa for ASTM A992 / Gr. 50)
    Es_MPa: float = 200_000.0  # Modulus of elasticity of steel


@dataclass(frozen=True)
class AISCSlabSpec:
    """Concrete slab and decking specification."""
    t_slab_mm: float     # Total concrete thickness above decking/flange [mm]
    fc_MPa: float        # Concrete cylinder compressive strength [MPa]
    wc_kg_m3: float = 2350.0  # Unit weight of concrete [kg/m^3]
    h_deck_mm: float = 0.0    # Rib depth of metal deck (0 for solid slab) [mm]
    wr_mm: float = 0.0        # Average rib width (if metal deck) [mm]


@dataclass(frozen=True)
class AISCStudSpec:
    """Headed shear stud connector specification."""
    d_stud_mm: float     # Stud diameter [mm] (e.g. 19 mm = 3/4 in)
    Fu_stud_MPa: float = 450.0  # Minimum tensile strength of stud [MPa] (65 ksi ~ 450 MPa)
    Rg: float = 1.0      # AISC 360 Table I8.1 factor (1.0 for solid slab or 1 stud/rib)
    Rp: float = 1.0      # AISC 360 Table I8.1 factor (1.0 for solid slab or deck with emedment >= 2 in)


@dataclass(frozen=True)
class AISCCompositeFlexureResult:
    """Detailed flexural capacity result per AISC 360-16 §I3.2."""
    Mn_kNm: float              # Nominal flexural strength [kN*m]
    phi_Mn_kNm: float          # Design flexural strength (LRFD, phi=0.90) [kN*m]
    Mn_over_Omega_kNm: float   # Allowable flexural strength (ASD, Omega=1.67) [kN*m]
    V_prime_N: float           # Governing compressive force transferred by shear connection [N]
    V_prime_full_N: float      # Force required for full composite action [N]
    composite_ratio: float     # Degree of composite action: V' / V'_full (0.25 to 1.0)
    pna_case: Literal["CASE_1_SLAB", "CASE_2_FLANGE", "CASE_3_WEB"]
    y_pna_from_top_slab_mm: float  # PNA depth from top of concrete slab [mm]
    a_conc_block_mm: float     # Depth of concrete compression block [mm]
    is_fully_composite: bool
    is_compact_web: bool       # True if web satisfies h/tw <= 3.76 * sqrt(E/Fy)
    units: dict[str, str] = field(default_factory=lambda: {"moment": "kNm", "force": "N", "length": "mm"})


@dataclass(frozen=True)
class AISCCompositeVerificationResult:
    """Complete ULS and SLS verification of composite beam per AISC 360-16."""
    passed: bool
    status: str
    dcr_flexure_composite: float
    dcr_shear_composite: float
    dcr_flexure_construction: float
    dcr_shear_construction: float
    deflection_live_mm: float
    deflection_total_mm: float
    dcr_deflection_live: float
    dcr_deflection_total: float
    flexure_result: AISCCompositeFlexureResult
    Vn_shear_kN: float
    phi_Vn_shear_kN: float
    stud_Qn_kN: float
    num_studs_half_span_required: int
    num_studs_half_span_provided: int
    I_eff_mm4: float
    diagnostics: list[str]
    units: dict[str, str] = field(default_factory=lambda: {"force": "kN", "moment": "kNm", "length": "mm", "inertia": "mm4"})


def aisc_b_effective(
    L_span_mm: float,
    beam_spacing_mm: float,
    dist_to_edge_left_mm: float | None = None,
    dist_to_edge_right_mm: float | None = None,
) -> float:
    """Calculates the effective width of the concrete slab b_eff per AISC 360-16 §I1.1.

    The effective width of the concrete slab on each side of the beam centerline
    shall not exceed:
    (1) 1/8 of the beam span, center-to-center of supports (L / 8)
    (2) 1/2 the distance to the centerline of the adjacent beam (S / 2)
    (3) The distance to the edge of the slab.

    For a typical interior beam with symmetric spacing S:
    b_eff = min(L/4, S).
    """
    if L_span_mm <= 0.0:
        raise ValueError("L_span_mm must be strictly positive.")
    if beam_spacing_mm <= 0.0:
        raise ValueError("beam_spacing_mm must be strictly positive.")

    # Left half-width
    max_left = min(L_span_mm / 8.0, beam_spacing_mm / 2.0)
    if dist_to_edge_left_mm is not None:
        if dist_to_edge_left_mm < 0.0:
            raise ValueError("dist_to_edge_left_mm cannot be negative.")
        max_left = min(max_left, dist_to_edge_left_mm)

    # Right half-width
    max_right = min(L_span_mm / 8.0, beam_spacing_mm / 2.0)
    if dist_to_edge_right_mm is not None:
        if dist_to_edge_right_mm < 0.0:
            raise ValueError("dist_to_edge_right_mm cannot be negative.")
        max_right = min(max_right, dist_to_edge_right_mm)

    return max_left + max_right


def aisc_concrete_modulus(fc_MPa: float, wc_kg_m3: float = 2350.0) -> float:
    """Calculates concrete modulus of elasticity Ec in MPa per AISC 360-16 §I1.5.

    Ec = 0.043 * wc^1.5 * sqrt(fc) in SI units (wc in kg/m^3, fc in MPa).
    For normal weight concrete (wc ~ 2350 kg/m^3), Ec ~ 4900 * sqrt(fc).
    """
    if fc_MPa <= 0.0:
        raise ValueError("fc_MPa must be positive.")
    if wc_kg_m3 <= 0.0:
        raise ValueError("wc_kg_m3 must be positive.")
    return 0.043 * (wc_kg_m3 ** 1.5) * math.sqrt(fc_MPa)


def aisc_stud_shear_strength(
    d_stud_mm: float,
    fc_MPa: float,
    Ec_MPa: float,
    Fu_stud_MPa: float = 450.0,
    Rg: float = 1.0,
    Rp: float = 1.0,
) -> float:
    """Calculates the nominal shear strength Qn of one headed stud anchor per AISC 360-16 Eq. I8-1.

    Qn = 0.5 * A_sa * sqrt(fc * Ec) <= Rg * Rp * A_sa * Fu

    Parameters
    ----------
    d_stud_mm : float
        Stud shank diameter [mm].
    fc_MPa : float
        Concrete compressive strength [MPa].
    Ec_MPa : float
        Concrete modulus of elasticity [MPa].
    Fu_stud_MPa : float
        Minimum tensile strength of stud [MPa] (default 450 MPa ~ 65 ksi).
    Rg, Rp : float
        AISC Table I8.1 factors for deck configuration (1.0 for solid slab).

    Returns
    -------
    Qn : float
        Nominal shear strength in Newtons [N].
    """
    if min(d_stud_mm, fc_MPa, Ec_MPa, Fu_stud_MPa, Rg, Rp) <= 0.0:
        raise ValueError("All stud parameters and factors must be positive.")

    A_sa = math.pi * (d_stud_mm ** 2) / 4.0  # mm^2
    concrete_term = 0.5 * A_sa * math.sqrt(fc_MPa * Ec_MPa)
    steel_term = Rg * Rp * A_sa * Fu_stud_MPa
    return min(concrete_term, steel_term)


def aisc_composite_positive_moment(
    section: AISCBeamSection,
    slab: AISCSlabSpec,
    b_eff_mm: float,
    sum_Qn_N: float | None = None,
) -> AISCCompositeFlexureResult:
    """Calculates nominal and design positive flexural strength per AISC 360-16 §I3.2.

    Uses the plastic stress distribution method for compact web I-sections in
    positive bending. Covers both full and partial composite interaction.

    Parameters
    ----------
    section : AISCBeamSection
        Steel beam section properties.
    slab : AISCSlabSpec
        Concrete slab and deck properties.
    b_eff_mm : float
        Effective width of concrete slab [mm].
    sum_Qn_N : float, optional
        Total nominal shear connector force between point of zero moment and
        point of maximum moment [N]. If None, full composite action is assumed.
    """
    # 1. Validation of AISC limits
    if section.Fy_MPa > 525.0:
        raise ValueError(
            f"AISC 360-16 §I1.2: Fy ({section.Fy_MPa:.1f} MPa) exceeds maximum permitted 525 MPa (75 ksi)."
        )
    if slab.fc_MPa < 21.0 or slab.fc_MPa > 70.0:
        # Note: Normal weight concrete limit 21 to 70 MPa (3 to 10 ksi)
        if slab.fc_MPa < 17.0:
            raise ValueError(
                f"AISC 360-16 §I1.2: fc ({slab.fc_MPa:.1f} MPa) is below minimum structural limit 17 MPa."
            )

    # 2. Compact web check per §I3.2a: h/tw <= 3.76 * sqrt(E/Fy)
    h_clear = section.d_mm - 2.0 * section.tf_mm
    h_over_tw = h_clear / section.tw_mm
    compact_limit = 3.76 * math.sqrt(section.Es_MPa / section.Fy_MPa)
    is_compact_web = h_over_tw <= compact_limit

    # 3. Maximum forces
    T_max = section.A_mm2 * section.Fy_MPa  # [N] Full steel tension
    # Concrete compression above deck ribs
    C_max = 0.85 * slab.fc_MPa * b_eff_mm * slab.t_slab_mm  # [N]

    V_prime_full = min(T_max, C_max)

    if sum_Qn_N is None or sum_Qn_N >= V_prime_full:
        V_prime = V_prime_full
        is_fully_composite = True
    else:
        # Partial composite action
        # AISC 360-16 §I3.2d: minimum 25% composite action
        min_connection = 0.25 * V_prime_full
        if sum_Qn_N < min_connection:
            raise ValueError(
                f"AISC 360-16 §I3.2d violation: sum(Qn) = {sum_Qn_N/1e3:.1f} kN is less than "
                f"25% of V'_full ({min_connection/1e3:.1f} kN). Composite action is not permitted."
            )
        V_prime = sum_Qn_N
        is_fully_composite = False

    composite_ratio = V_prime / V_prime_full

    # 4. Determine PNA location
    # Distance from top of steel flange to top of slab
    d_top_steel_to_top_slab = slab.t_slab_mm + slab.h_deck_mm

    # Case 1: PNA in the concrete slab (V' = T_max <= C_max, or compression is fully within slab)
    # The depth of concrete compression block is a = V' / (0.85 * fc * b_eff)
    a_conc = V_prime / (0.85 * slab.fc_MPa * b_eff_mm)

    if a_conc <= slab.t_slab_mm and V_prime == T_max:
        # PNA is in the concrete slab!
        pna_case: Literal["CASE_1_SLAB", "CASE_2_FLANGE", "CASE_3_WEB"] = "CASE_1_SLAB"
        y_pna = a_conc  # from top of slab
        # Steel is entirely in tension at its centroid (d/2 below top of steel)
        arm_steel_from_top_slab = d_top_steel_to_top_slab + section.d_mm / 2.0
        arm_concrete_from_top_slab = a_conc / 2.0
        lever_arm = arm_steel_from_top_slab - arm_concrete_from_top_slab
        Mn_Nmm = V_prime * lever_arm

    else:
        # PNA is in the steel section!
        # Entire slab concrete is in compression: C_conc = min(C_max, V')
        # Concrete block depth is full t_slab
        a_conc = slab.t_slab_mm
        C_conc = min(C_max, V_prime)

        # Force in steel that must flip to compression:
        # T_steel - C_steel_comp = C_conc => (As*Fy - C_steel_comp) - C_steel_comp = C_conc
        # => 2 * C_steel_comp = As*Fy - C_conc => C_steel_comp = (As*Fy - C_conc) / 2
        C_steel_comp = (T_max - C_conc) / 2.0
        flange_force = section.bf_mm * section.tf_mm * section.Fy_MPa

        if C_steel_comp <= flange_force:
            # Case 2: PNA in the top flange of the steel section
            pna_case = "CASE_2_FLANGE"
            y_in_flange = C_steel_comp / (section.bf_mm * section.Fy_MPa)
            y_pna = d_top_steel_to_top_slab + y_in_flange

            # Moments about PNA:
            # 1. Concrete slab block: force C_conc, lever arm = (y_pna - slab.t_slab_mm / 2.0)
            M_conc = C_conc * (y_pna - slab.t_slab_mm / 2.0)
            # 2. Steel top flange in compression: (0 to y_in_flange)
            M_flange_comp = (section.bf_mm * y_in_flange * section.Fy_MPa) * (y_in_flange / 2.0)
            # 3. Steel top flange in tension: (y_in_flange to tf)
            t_flange_tens = section.tf_mm - y_in_flange
            M_flange_tens = (section.bf_mm * t_flange_tens * section.Fy_MPa) * (t_flange_tens / 2.0)
            # 4. Steel web in tension: force Aw*Fy, lever from PNA
            h_web = section.d_mm - 2.0 * section.tf_mm
            arm_web_centroid = (section.tf_mm - y_in_flange) + h_web / 2.0
            M_web_tens = (h_web * section.tw_mm * section.Fy_MPa) * arm_web_centroid
            # 5. Steel bottom flange in tension: force Af*Fy
            arm_bot_flange = (section.tf_mm - y_in_flange) + h_web + section.tf_mm / 2.0
            M_bot_flange = flange_force * arm_bot_flange

            Mn_Nmm = M_conc + M_flange_comp + M_flange_tens + M_web_tens + M_bot_flange

        else:
            # Case 3: PNA in the web of the steel section
            pna_case = "CASE_3_WEB"
            web_comp = C_steel_comp - flange_force
            y_in_web = web_comp / (section.tw_mm * section.Fy_MPa)
            y_pna = d_top_steel_to_top_slab + section.tf_mm + y_in_web

            # Equivalent plastic formulation: bare steel Mpl + slab couple - lost web couple
            Mpl_steel = section.Zx_mm3 * section.Fy_MPa  # N*mm
            # Couple of slab compression to steel centroid:
            arm_slab_to_centroid = (section.d_mm / 2.0 + slab.h_deck_mm + slab.t_slab_mm / 2.0)
            M_slab_couple = C_conc * arm_slab_to_centroid
            # Deduction for compressive force shift in web:
            M_web_deduction = (C_conc ** 2) / (4.0 * section.tw_mm * section.Fy_MPa)
            Mn_Nmm = Mpl_steel + M_slab_couple - M_web_deduction

    Mn_kNm = Mn_Nmm / 1.0e6
    phi_Mn_kNm = 0.90 * Mn_kNm
    Mn_over_Omega_kNm = Mn_kNm / 1.67

    return AISCCompositeFlexureResult(
        Mn_kNm=Mn_kNm,
        phi_Mn_kNm=phi_Mn_kNm,
        Mn_over_Omega_kNm=Mn_over_Omega_kNm,
        V_prime_N=V_prime,
        V_prime_full_N=V_prime_full,
        composite_ratio=composite_ratio,
        pna_case=pna_case,
        y_pna_from_top_slab_mm=y_pna,
        a_conc_block_mm=a_conc,
        is_fully_composite=is_fully_composite,
        is_compact_web=is_compact_web,
    )


def aisc_effective_inertia(
    section: AISCBeamSection,
    slab: AISCSlabSpec,
    b_eff_mm: float,
    V_prime_N: float,
    V_prime_full_N: float,
) -> float:
    """Calculates effective moment of inertia I_eff per AISC 360-16 Commentary §I3.2.

    I_eff = I_s + sqrt(V' / V'_full) * (I_tr - I_s)
    where:
    - I_s is the bare steel major-axis moment of inertia.
    - I_tr is the transformed elastic moment of inertia of the fully composite section.
    """
    if V_prime_full_N <= 0.0 or V_prime_N <= 0.0:
        return section.Ix_mm4

    ratio = min(1.0, max(0.0, V_prime_N / V_prime_full_N))

    # Modular ratio n = Es / Ec
    Ec = aisc_concrete_modulus(slab.fc_MPa, slab.wc_kg_m3)
    n = max(1.0, section.Es_MPa / Ec)

    # Transformed slab width and area
    b_tr = b_eff_mm / n
    A_conc_tr = b_tr * slab.t_slab_mm
    A_total = section.A_mm2 + A_conc_tr

    # Elastic neutral axis y_bar from bottom of steel beam
    y_steel = section.d_mm / 2.0
    y_conc = section.d_mm + slab.h_deck_mm + slab.t_slab_mm / 2.0
    y_bar = (section.A_mm2 * y_steel + A_conc_tr * y_conc) / A_total

    # Transformed inertia about y_bar
    I_conc = (b_tr * (slab.t_slab_mm ** 3)) / 12.0
    d_conc = y_conc - y_bar
    d_steel = y_bar - y_steel
    I_tr = (
        section.Ix_mm4
        + section.A_mm2 * (d_steel ** 2)
        + I_conc
        + A_conc_tr * (d_conc ** 2)
    )

    I_eff = section.Ix_mm4 + math.sqrt(ratio) * (I_tr - section.Ix_mm4)
    return I_eff


def aisc_beam_shear_strength(
    section: AISCBeamSection,
) -> tuple[float, float]:
    """Calculates nominal and design vertical shear strength per AISC 360-16 §G2.1.

    Vn = 0.6 * Fy * Aw * Cv1
    Aw = d * tw
    Returns (Vn_kN, phi_Vn_kN).
    """
    Aw = section.d_mm * section.tw_mm
    h_clear = section.d_mm - 2.0 * section.tf_mm
    h_over_tw = h_clear / section.tw_mm

    # Cv1 per AISC 360-16 §G2.1(a)
    lim1 = 2.24 * math.sqrt(section.Es_MPa / section.Fy_MPa)
    if h_over_tw <= lim1:
        Cv1 = 1.0
        phi_v = 1.00  # §G2.1a allows phi=1.00 for compact webs
    else:
        Cv1 = min(1.0, lim1 / h_over_tw)
        phi_v = 0.90

    Vn_N = 0.6 * section.Fy_MPa * Aw * Cv1
    Vn_kN = Vn_N / 1000.0
    phi_Vn_kN = phi_v * Vn_kN
    return Vn_kN, phi_Vn_kN


def verify_aisc_composite_beam(
    section: AISCBeamSection,
    slab: AISCSlabSpec,
    stud: AISCStudSpec,
    L_span_mm: float,
    beam_spacing_mm: float,
    num_studs_total: int,
    M_construction_kNm: float,
    V_construction_kN: float,
    M_composite_kNm: float,
    V_composite_kN: float,
    w_live_N_per_mm: float = 0.0,
    w_total_N_per_mm: float = 0.0,
    live_deflection_limit_ratio: float = 360.0,  # L / 360
    total_deflection_limit_ratio: float = 240.0, # L / 240
    units: dict[str, str] | None = None,
) -> AISCCompositeVerificationResult:
    """Full engineering verification of a composite beam per AISC 360-16 (LRFD).

    Checks:
    1. Effective slab width b_eff (§I1.1)
    2. Construction phase flexure & shear on bare steel (§I3.1)
    3. Stud shear strength Qn and provided shear connection force sum(Qn) (§I8.1)
    4. Minimum degree of shear connection >= 25% (§I3.2d)
    5. Composite positive flexural strength phi_Mn (§I3.2)
    6. Vertical shear strength phi_Vn (§I4.1 / §G2.1)
    7. SLS Live and total load deflections using I_eff (Commentary §I3.2)
    """
    diagnostics: list[str] = []

    # 1. Effective width
    b_eff = aisc_b_effective(L_span_mm, beam_spacing_mm)

    # 2. Construction stage (bare steel)
    # Steel flexural capacity: phi * Fy * Zx
    phi_Mn_const = 0.90 * (section.Zx_mm3 * section.Fy_MPa) / 1.0e6  # kN*m
    Vn_const, phi_Vn_const = aisc_beam_shear_strength(section)

    if phi_Mn_const > 0:
        dcr_flex_const = M_construction_kNm / phi_Mn_const
    else:
        dcr_flex_const = float("inf")

    if phi_Vn_const > 0:
        dcr_shear_const = V_construction_kN / phi_Vn_const
    else:
        dcr_shear_const = float("inf")

    if dcr_flex_const > 1.0:
        diagnostics.append(f"Falla flexión constructiva: DCR={dcr_flex_const:.2f} > 1.0 (Mu={M_construction_kNm:.1f} kN*m, phiMn={phi_Mn_const:.1f} kN*m)")
    if dcr_shear_const > 1.0:
        diagnostics.append(f"Falla cortante constructivo: DCR={dcr_shear_const:.2f} > 1.0")

    # 3. Stud connection
    Ec = aisc_concrete_modulus(slab.fc_MPa, slab.wc_kg_m3)
    Qn_N = aisc_stud_shear_strength(stud.d_stud_mm, slab.fc_MPa, Ec, stud.Fu_stud_MPa, stud.Rg, stud.Rp)
    Qn_kN = Qn_N / 1000.0

    # Number of studs between zero and max moment (half span for simply supported)
    num_studs_half = num_studs_total // 2
    sum_Qn_N = num_studs_half * Qn_N

    # 4. Composite flexure
    try:
        flex_res = aisc_composite_positive_moment(section, slab, b_eff, sum_Qn_N=sum_Qn_N)
    except ValueError as exc:
        diagnostics.append(f"Error en dimensionamiento compuesto: {exc}")
        # Return fallback result
        return AISCCompositeVerificationResult(
            passed=False,
            status="RECHAZADO",
            dcr_flexure_composite=999.0,
            dcr_shear_composite=999.0,
            dcr_flexure_construction=dcr_flex_const,
            dcr_shear_construction=dcr_shear_const,
            deflection_live_mm=0.0,
            deflection_total_mm=0.0,
            dcr_deflection_live=0.0,
            dcr_deflection_total=0.0,
            flexure_result=AISCCompositeFlexureResult(
                Mn_kNm=0.0, phi_Mn_kNm=0.0, Mn_over_Omega_kNm=0.0,
                V_prime_N=0.0, V_prime_full_N=0.0, composite_ratio=0.0,
                pna_case="CASE_1_SLAB", y_pna_from_top_slab_mm=0.0, a_conc_block_mm=0.0,
                is_fully_composite=False, is_compact_web=False,
            ),
            Vn_shear_kN=Vn_const,
            phi_Vn_shear_kN=phi_Vn_const,
            stud_Qn_kN=Qn_kN,
            num_studs_half_span_required=math.ceil(Qn_N / 1.0),
            num_studs_half_span_provided=num_studs_half,
            I_eff_mm4=section.Ix_mm4,
            diagnostics=diagnostics,
        )

    if flex_res.phi_Mn_kNm > 0:
        dcr_flex_comp = M_composite_kNm / flex_res.phi_Mn_kNm
    else:
        dcr_flex_comp = float("inf")

    if phi_Vn_const > 0:
        dcr_shear_comp = V_composite_kN / phi_Vn_const
    else:
        dcr_shear_comp = float("inf")

    if dcr_flex_comp > 1.0:
        diagnostics.append(f"Falla flexión compuesta: DCR={dcr_flex_comp:.2f} > 1.0 (Mu={M_composite_kNm:.1f} kN*m, phiMn={flex_res.phi_Mn_kNm:.1f} kN*m)")
    if dcr_shear_comp > 1.0:
        diagnostics.append(f"Falla cortante compuesto: DCR={dcr_shear_comp:.2f} > 1.0")

    # Studs required for full interaction
    studs_half_req = math.ceil(flex_res.V_prime_full_N / Qn_N) if Qn_N > 0 else 999

    # 5. Deflections
    I_eff = aisc_effective_inertia(section, slab, b_eff, flex_res.V_prime_N, flex_res.V_prime_full_N)

    # delta = 5 * w * L^4 / (384 * E * I)
    # w in N/mm, L in mm, E in MPa (N/mm^2), I in mm^4 -> delta in mm
    delta_live = 0.0
    dcr_delta_live = 0.0
    if w_live_N_per_mm > 0.0:
        delta_live = (5.0 * w_live_N_per_mm * (L_span_mm ** 4)) / (384.0 * section.Es_MPa * I_eff)
        delta_live_limit = L_span_mm / live_deflection_limit_ratio
        dcr_delta_live = delta_live / delta_live_limit
        if dcr_delta_live > 1.0:
            diagnostics.append(f"Falla flecha de sobrecarga viva: {delta_live:.1f} mm > {delta_live_limit:.1f} mm (L/{live_deflection_limit_ratio:.0f})")

    delta_total = 0.0
    dcr_delta_total = 0.0
    if w_total_N_per_mm > 0.0:
        delta_total = (5.0 * w_total_N_per_mm * (L_span_mm ** 4)) / (384.0 * section.Es_MPa * I_eff)
        delta_total_limit = L_span_mm / total_deflection_limit_ratio
        dcr_delta_total = delta_total / delta_total_limit
        if dcr_delta_total > 1.0:
            diagnostics.append(f"Falla flecha total: {delta_total:.1f} mm > {delta_total_limit:.1f} mm (L/{total_deflection_limit_ratio:.0f})")

    passed = (
        dcr_flex_const <= 1.0
        and dcr_shear_const <= 1.0
        and dcr_flex_comp <= 1.0
        and dcr_shear_comp <= 1.0
        and dcr_delta_live <= 1.0
        and dcr_delta_total <= 1.0
    )

    status = "APROBADO" if passed else "RECHAZADO"

    return AISCCompositeVerificationResult(
        passed=passed,
        status=status,
        dcr_flexure_composite=dcr_flex_comp,
        dcr_shear_composite=dcr_shear_comp,
        dcr_flexure_construction=dcr_flex_const,
        dcr_shear_construction=dcr_shear_const,
        deflection_live_mm=delta_live,
        deflection_total_mm=delta_total,
        dcr_deflection_live=dcr_delta_live,
        dcr_deflection_total=dcr_delta_total,
        flexure_result=flex_res,
        Vn_shear_kN=Vn_const,
        phi_Vn_shear_kN=phi_Vn_const,
        stud_Qn_kN=Qn_kN,
        num_studs_half_span_required=studs_half_req,
        num_studs_half_span_provided=num_studs_half,
        I_eff_mm4=I_eff,
        diagnostics=diagnostics,
    )
