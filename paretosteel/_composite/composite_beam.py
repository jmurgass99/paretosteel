"""Composite beam design per EN 1994-1-1.

Conventions (SI mm/N): forces in N, lengths in mm, stresses in MPa (N/mm^2),
moments in N*mm. Functions return moments in kN*m where indicated.
"""
from __future__ import annotations

import math
from typing import Literal


def plastic_moment_full_interaction(
    b_eff: float,
    h_c: float,
    A_s: float,
    fy: float,
    fc: float,
) -> float:
    """[LEGACY / SIMPLIFIED] Plastic moment resistance Mpl,Rd of a composite
    beam with full shear interaction, simply-supported sagging region
    (EN 1994-1-1 §6.2.1.2), using a SLAB-ONLY lever arm.

    .. deprecated::
        This function UNDER-estimates Mpl,Rd because its lever arm
        ``z = h_c - x/2`` measures only within the slab and OMITS the depth of
        the steel section (the steel tension acts at the steel centroid, well
        below the slab). It is retained for backward compatibility and for the
        slab-only textbook bound it reproduces. For a correct result that
        includes the real steel geometry use :func:`mpl_rd_block_method`
        (the genuine block method of §6.2.1.2, with all three PNA subcases).

    Assumes the plastic neutral axis (PNA) lies within the concrete slab
    (the most common case for typical office floor beams).

    Parameters
    ----------
    b_eff : float
        Effective width of the concrete flange [mm].
    h_c : float
        Overall slab depth above the steel top flange [mm].
    A_s : float
        Cross-sectional area of the structural steel section [mm^2].
    fy : float
        Yield strength of structural steel [N/mm^2].
    fc : float
        Design (cylinder) compressive strength of concrete fcd = 0.85*fck/gamma_c
        already factored, or characteristic fck if a partial-factor-free
        estimate is desired. Pass the design block stress directly.

    Returns
    -------
    Mpl_Rd : float
        Plastic moment resistance in kN*m.

    Notes
    -----
    Tension force in steel  Ns = A_s * fy
    Compression force in concrete block Nc = b_eff * x * fc
    Equilibrium -> x = Ns / (b_eff * fc).
    Lever arm z = d_s + h_c - x/2, where d_s is the distance from the
    steel centroid to the top of the steel section (taken as half the
    steel depth is not enough; here we use the slab thickness only for the
    lever arm contribution and assume the steel centroid is at the
    underside of the slab — the function uses a simplified lever-arm
    consistent with §6.2.1.2 when PNA is in the slab). Users requiring
    the full geometric lever arm should call with the explicit
    steel-centroid distance baked into h_c.
    """
    if min(b_eff, h_c, A_s, fy, fc) <= 0:
        raise ValueError("All inputs must be positive.")
    Ns = A_s * fy  # N
    x = Ns / (b_eff * fc)  # mm, depth of concrete stress block
    if x > h_c:
        # PNA falls in the steel section — return a conservative bound using
        # the full concrete block; user should treat result with caution.
        x = h_c
    # Lever arm between centroid of concrete block and centroid of steel.
    # Take the steel centroid one half-depth below the top of steel.
    # Without explicit steel depth, the safe conventional lever arm used
    # in textbook benchmarks is z = h_c - x/2 plus the steel half-depth,
    # which the caller can incorporate into h_c. Here we return the
    # contribution Mpl = Ns * (h_c - x/2) which equals the slab portion.
    z = h_c - x / 2.0  # mm
    Mpl = Ns * z  # N*mm
    return Mpl / 1.0e6  # kN*m


def mpl_rd_block_method(
    b_f: float,
    t_f: float,
    t_w: float,
    h_a: float,
    b_eff: float,
    h_c: float,
    fyd: float,
    fcd: float,
    h_p: float = 0.0,
) -> float:
    """Plastic moment resistance Mpl,Rd by the rectangular-stress-BLOCK method
    for a sagging composite beam with FULL shear interaction
    (EN 1994-1-1 §6.2.1.2).

    Unlike the simplified :func:`plastic_moment_full_interaction` (slab-only
    lever arm, which under-estimates), this resolves the plastic neutral axis
    (PNA) position and returns the CORRECT lever arm including the depth of the
    structural steel. The §6.2.1.2 plastic assumptions are: full interaction;
    structural steel at the design yield fyd in tension/compression over the
    whole section; concrete in compression at the rectangular block stress
    0.85*fcd; concrete in tension neglected (EN 1994-1-1 §6.2.1.2(1)(a)-(d)).

    Three PNA subcases are covered, selected automatically (W01635/W01636):

    * **Case 1 — PNA in the concrete slab** (N_pl,a <= N_c,f). The slab carries
      compression over a depth ``x = N_pl,a/(0.85*fcd*b_eff)``; all steel is in
      tension at its centroid.
    * **Case 2 — PNA in the steel top flange**
      (0 < N_pl,a - N_c,f <= 2*b_f*t_f*fyd). The whole slab is in compression;
      a depth of the top flange flips to compression.
    * **Case 3 — PNA in the steel web** (N_pl,a - N_c,f > 2*b_f*t_f*fyd). Closed
      form ``Mpl,a,Rd + N_c,f*(h_a/2 + h_p + h_c/2) - N_c,f^2/(4*t_w*fyd)``.

    The section is taken doubly-symmetric (equal flanges). For S420/S460 a
    further reduction beta may apply when x_pl/h > 0.15 (see
    :func:`beta_flexural_reduction`); it is NOT applied here (caller-gated).

    Parameters
    ----------
    b_f, t_f, t_w, h_a : float
        Steel I-section geometry [mm]: flange width, flange thickness, web
        thickness and OVERALL section depth (root radii ignored — plate model).
    b_eff : float
        Effective width of the concrete flange [mm] (see :func:`b_effective`).
    h_c : float
        Depth of concrete ABOVE the profiled-sheeting ribs (the part available
        for the compression block) [mm].
    fyd : float
        Design yield strength of structural steel [N/mm^2] (= fyk/gamma_M0,
        gamma_M0 = 1.0 in EC4 so fyd = fyk).
    fcd : float
        Design CYLINDER compressive strength of concrete [N/mm^2]
        (= fck/gamma_c). NOTE: unlike the legacy
        :func:`plastic_moment_full_interaction` (which expects the
        already-factored block stress), this function applies the 0.85 factor
        of §6.2.1.2(1)(d) INTERNALLY. Pass fcd, e.g. 16.67 for C25/30.
    h_p : float, optional
        Depth of the profiled steel sheeting ribs between the slab soffit and
        the top of the steel flange [mm], default 0.0 (solid slab). Concrete
        within h_p is conservatively ignored in compression.

    Returns
    -------
    Mpl_Rd : float
        Plastic moment resistance in kN*m.

    Raises
    ------
    ValueError
        If any dimension/strength is non-positive, if the flanges do not fit in
        the section depth (2*t_f >= h_a), or if x in Case 1 exceeds h_c (an
        internal-consistency check on the case selection).
    """
    if min(b_f, t_f, t_w, h_a, b_eff, h_c, fyd, fcd) <= 0.0:
        raise ValueError(
            "All geometry and strengths must be positive "
            "(b_f, t_f, t_w, h_a, b_eff, h_c, fyd, fcd)."
        )
    if h_p < 0.0:
        raise ValueError("h_p (sheeting rib depth) must be non-negative.")
    if 2.0 * t_f >= h_a:
        raise ValueError(
            "Flanges do not fit in the section depth: need 2*t_f < h_a."
        )

    A_a = 2.0 * b_f * t_f + (h_a - 2.0 * t_f) * t_w  # steel area [mm^2]
    N_pl_a = A_a * fyd  # full steel yield force [N]
    fc_block = 0.85 * fcd  # rectangular block stress, §6.2.1.2(1)(d)
    N_cf = fc_block * b_eff * h_c  # full slab compression force [N]
    N_flange = b_f * t_f * fyd  # one full flange yield force [N]

    top_steel = h_c + h_p  # depth of top of steel below top of slab [mm]
    z_s = top_steel + h_a / 2.0  # steel centroid below top of slab [mm]
    # Bare-steel plastic moment Mpl,a,Rd (doubly-symmetric I), used for Case 3.
    W_pl = b_f * t_f * (h_a - t_f) + t_w * (h_a - 2.0 * t_f) ** 2 / 4.0  # mm^3
    Mpl_a = W_pl * fyd  # N*mm

    if N_pl_a <= N_cf:
        # Case 1 — PNA in the slab. EN 1994-1-1 §6.2.1.2.
        x = N_pl_a / (fc_block * b_eff)  # compression block depth [mm]
        if x > h_c:  # pragma: no cover - guarded by the N_pl_a <= N_cf branch
            raise ValueError(
                "Inconsistent Case-1 selection: x > h_c. Check inputs."
            )
        Mpl = N_pl_a * (z_s - x / 2.0)  # N*mm
    elif (N_pl_a - N_cf) <= 2.0 * N_flange:
        # Case 2 — PNA in the steel top flange. Whole slab in compression; a
        # depth a of the top flange flips to compression. Net steel compression
        # Nc = (N_pl,a - N_c,f)/2 (the flipped strip is double-counted).
        Nc = (N_pl_a - N_cf) / 2.0  # N
        a = Nc / (b_f * fyd)  # flange compression depth [mm]
        Mpl = (
            N_pl_a * z_s
            - N_cf * (h_c / 2.0)
            - 2.0 * Nc * (top_steel + a / 2.0)
        )  # N*mm
    else:
        # Case 3 — PNA in the web. Clean closed form (taking the bare-steel
        # plastic couple plus the slab contribution minus the web "hole").
        Mpl = (
            Mpl_a
            + N_cf * (h_a / 2.0 + h_p + h_c / 2.0)
            - N_cf ** 2 / (4.0 * t_w * fyd)
        )  # N*mm
    return Mpl / 1.0e6  # kN*m


def mpl_rd_hogging(
    b_f: float,
    t_f: float,
    t_w: float,
    h_a: float,
    A_sr: float,
    fsd: float,
    d_s: float,
    fyd: float,
) -> float:
    """Hogging (negative) plastic moment resistance Mpl,Rd,neg of a composite
    beam (EN 1994-1-1 §6.2.1.2, negative-bending case).

    In a hogging region the concrete slab is in tension and CRACKED, so it is
    excluded; the resistance comes from the structural steel section plus the
    longitudinal slab REINFORCEMENT in tension (W01635 §4, W01636, W01642
    §6.2.1.2). With the reinforcement near the top in tension, the steel
    plastic neutral axis shifts UP into the WEB by ``delta`` so that a web strip
    flips from tension to compression and balances the rebar force
    ``N_s = A_sr*fsd``:

        delta = N_s / (2*t_w*fyd)
        Mpl,Rd,neg = Mpl,a,Rd + N_s*(h_a/2 + d_s) - N_s^2/(4*t_w*fyd)

    where Mpl,a,Rd is the bare-steel plastic moment and the last term is the
    plastic-couple lost by the flipped web strip. The doubly-symmetric I steel
    is assumed Class 1/2 in hogging (the compressed bottom flange governs the
    classification — verify separately).

    Parameters
    ----------
    b_f, t_f, t_w, h_a : float
        Steel I-section geometry [mm] (see :func:`mpl_rd_block_method`).
    A_sr : float
        Area of longitudinal slab reinforcement within b_eff [mm^2].
    fsd : float
        Design yield strength of the reinforcement [N/mm^2] (= fsk/gamma_s,
        e.g. 500/1.15 = 434.78 for B500).
    d_s : float
        Distance from the TOP of the steel flange UP to the reinforcement
        layer [mm] (so the rebar lever to the steel centroid is h_a/2 + d_s).
    fyd : float
        Design yield strength of structural steel [N/mm^2].

    Returns
    -------
    Mpl_Rd_neg : float
        Hogging plastic moment resistance in kN*m.

    Raises
    ------
    ValueError
        If any input is non-positive (d_s may be >= 0), or if the rebar force
        is so large that the steel PNA would leave the web
        (N_s > fyd*t_w*(h_a - 2*t_f)); that regime needs the PNA-in-flange
        treatment and is not covered by this closed form.
    """
    if min(b_f, t_f, t_w, h_a, fsd, fyd) <= 0.0 or A_sr <= 0.0:
        raise ValueError(
            "Geometry, A_sr, fsd and fyd must be positive."
        )
    if d_s < 0.0:
        raise ValueError("d_s (rebar height above steel top) must be >= 0.")
    if 2.0 * t_f >= h_a:
        raise ValueError("Flanges do not fit in the section depth: need 2*t_f < h_a.")

    N_s = A_sr * fsd  # rebar tension force [N]
    N_pl_web = fyd * t_w * (h_a - 2.0 * t_f)  # web yield capacity (both halves) [N]
    if N_s > N_pl_web:
        raise ValueError(
            "Reinforcement too heavy: the steel PNA would leave the web "
            f"(N_s = {N_s/1e3:.1f} kN > N_pl,web = {N_pl_web/1e3:.1f} kN). "
            "This closed form covers the PNA-in-web regime only; use a "
            "PNA-in-flange treatment (EN 1994-1-1 §6.2.1.2)."
        )
    W_pl = b_f * t_f * (h_a - t_f) + t_w * (h_a - 2.0 * t_f) ** 2 / 4.0  # mm^3
    Mpl_a = W_pl * fyd  # N*mm
    Mpl = Mpl_a + N_s * (h_a / 2.0 + d_s) - N_s ** 2 / (4.0 * t_w * fyd)  # N*mm
    return Mpl / 1.0e6  # kN*m


def b_effective(L_span: float, b0: float, b1: float, b2: float) -> float:
    """Effective flange width beff at mid-span of a simply-supported
    composite beam per EN 1994-1-1 §5.4.1.2.

    beff = b0 + sum(bei),  bei = min(Le/8, bi)

    where Le is the approximate distance between points of zero bending
    moment; for a simply-supported beam Le = L_span.

    Parameters
    ----------
    L_span : float
        Span length (point-to-point of zero moment) [mm].
    b0 : float
        Distance between the centres of the outstand shear connectors [mm].
    b1, b2 : float
        Geometric distances from the connector to the mid-distance of the
        adjacent beam (each side) [mm].

    Returns
    -------
    beff : float
        Effective width [mm].
    """
    if L_span <= 0 or b0 < 0 or b1 < 0 or b2 < 0:
        raise ValueError("Inputs must be non-negative; L_span positive.")
    Le = L_span
    be1 = min(Le / 8.0, b1)
    be2 = min(Le / 8.0, b2)
    return b0 + be1 + be2


def n_cf_concrete(
    fcd: float,
    b_eff: float,
    h_c: float,
    alpha_c: float = 0.85,
) -> float:
    """Concrete-flange compression capacity N_c,f (concrete term) of a composite
    beam for FULL shear connection (EN 1994-1-1 §6.2.1.2(1)(d) / §6.6.1.2):

        N_c,f = alpha_c * fcd * b_eff * h_c        (alpha_c = 0.85)

    The force required for FULL shear connection is
    ``N_c,f = min(A_a*fyd, alpha_c*fcd*b_eff*h_c)``; this helper returns the
    CONCRETE term (the second argument of that min), i.e. the crushing capacity
    of the effective slab compression zone. Compare it with the steel yield
    force ``A_a*fyd`` to obtain the governing N_c,f and the number of connectors
    for full interaction (N_c,f / P_Rd).

    Parameters
    ----------
    fcd : float
        Design cylinder compressive strength ``fcd = fck/gamma_c`` [N/mm^2]
        (e.g. 20.0 for C30/37 with gamma_c = 1.5).
    b_eff : float
        Effective width of the concrete flange [mm] (see :func:`b_effective`).
    h_c : float
        Depth of concrete available for compression (above the sheeting ribs)
        [mm].
    alpha_c : float, optional
        Rectangular-stress-block factor, 0.85 per §6.2.1.2(1)(d) (default 0.85).

    Returns
    -------
    N_c_f : float
        Concrete compression force [N].

    Raises
    ------
    ValueError
        If any input is non-positive.

    Notes
    -----
    Worked example (ficha W01640, SCI P359 Example 1): C30/37 (fcd = 20),
    b_eff = 3000 mm, h_c = 70 mm gives
    N_c,f = 0.85*20*3000*70 = 3 570 000 N = 3570 kN.
    """
    if min(fcd, b_eff, h_c, alpha_c) <= 0.0:
        raise ValueError("fcd, b_eff, h_c and alpha_c must be positive.")
    return alpha_c * fcd * b_eff * h_c


def shear_connector_resistance(
    d: float,
    fu_stud: float,
    fck: float,
    h_sc: float,
    Ecm: float | None = None,
    gamma_v: float = 1.25,
) -> float:
    """Design shear resistance PRd of a single headed-stud connector welded
    to a solid concrete slab per EN 1994-1-1 §6.6.3.1.

    PRd = min(P_Rd_a, P_Rd_b)
        P_Rd_a = 0.8 * fu * pi*d^2/4 / gamma_v        (stud-shank failure)
        P_Rd_b = 0.29 * alpha * d^2 * sqrt(fck * Ecm) / gamma_v (concrete)
        alpha = 0.2 * (h_sc/d + 1) for 3 <= h_sc/d <= 4
        alpha = 1.0                 for h_sc/d > 4

    Parameters
    ----------
    d : float
        Shank diameter of the stud [mm], 16 <= d <= 25 typically.
    fu_stud : float
        Ultimate tensile strength of stud material [N/mm^2] (<=500 typical).
    fck : float
        Characteristic cylinder strength of concrete [N/mm^2].
    h_sc : float
        Overall nominal height of the stud [mm].
    Ecm : float, optional
        Secant modulus of concrete [N/mm^2]. If None, estimated from
        Ecm = 22000 * (fcm/10)^0.3 with fcm = fck + 8 (EN 1992-1-1 Table 3.1).
    gamma_v : float
        Partial factor for shear connection (recommended 1.25).

    Returns
    -------
    PRd : float
        Design shear resistance of one stud [N].
    """
    if min(d, fu_stud, fck, h_sc) <= 0 or gamma_v <= 0:
        raise ValueError("All inputs must be positive.")
    if Ecm is None:
        fcm = fck + 8.0
        Ecm = 22000.0 * (fcm / 10.0) ** 0.3

    ratio = h_sc / d
    if ratio < 3.0:
        # Below validity; treat as not allowed but clamp alpha for robustness.
        alpha = 0.2 * (ratio + 1.0)
    elif ratio <= 4.0:
        alpha = 0.2 * (ratio + 1.0)
    else:
        alpha = 1.0

    P_a = 0.8 * fu_stud * math.pi * d ** 2 / 4.0 / gamma_v
    P_b = 0.29 * alpha * d ** 2 * math.sqrt(fck * Ecm) / gamma_v
    return min(P_a, P_b)


# ===========================================================================
# Shear connectors in PROFILED STEEL SHEETING (EN 1994-1-1 §6.6.4)
# ---------------------------------------------------------------------------
# When the stud is welded through (or beside) a trapezoidal steel deck, only a
# reduced portion of the solid-slab resistance P_Rd,solid (§6.6.3.1) is
# mobilised. EC4 gives two reduction factors by rib orientation:
#   * ribs TRANSVERSE  to the beam -> k_t  (§6.6.4.2, Eq. 6.23), capped by k_t,max
#     (Table 6.2, a function of n_r, sheet thickness and stud-weld detail);
#   * ribs PARALLEL    to the beam -> k_l  (§6.6.4.1, Eq. 6.22), capped at 1.0.
# Both reductions multiply P_Rd,solid; the design value is k * P_Rd,solid.
# ===========================================================================

# EN 1994-1-1 Table 6.2 — upper limit k_t,max for the §6.6.4.2 reduction.
# Keyed by (n_r_row, welded_through, thin_sheet):
#   n_r_row       : 1 for one stud per rib, 2 for two or more (n_r >= 2);
#   welded_through: True  -> studs welded through the profiled sheeting,
#                   False -> studs NOT welded through (e.g. through pre-punched
#                            holes / shot-fired), the more onerous columns;
#   thin_sheet    : True  -> nominal sheet thickness t <= 1.0 mm,
#                   False -> t > 1.0 mm.
# PROVENANCE: only the welded-through & t<=1.0 mm column (n_r=1 -> 0.85,
# n_r>=2 -> 0.70) is corroborated by the source fichas (W01628 and W01640).
# The remaining cells reproduce EN 1994-1-1 Table 6.2 as published in the
# standard but were NOT in the extracted corpus; they are tested by RELATIONS
# (monotonicity) rather than cited goldens, and a caller holding the table may
# override the cap via ``kt_max`` (see :func:`kt_profiled_transverse`).
_KT_MAX_TABLE_6_2 = {
    # (n_r_row, welded_through, thin_sheet): k_t,max
    (1, True, True): 0.85,   # ✓ W01628 / W01640
    (1, True, False): 1.00,
    (1, False, True): 0.75,
    (1, False, False): 0.75,
    (2, True, True): 0.70,   # ✓ W01628 (n_r=2 transverse)
    (2, True, False): 0.80,
    (2, False, True): 0.60,
    (2, False, False): 0.60,
}


def kt_max_table_6_2(
    n_r: int,
    welded_through: bool = True,
    t_sheet: float = 1.0,
) -> float:
    """Upper limit k_t,max for the transverse-rib reduction factor, from
    EN 1994-1-1 Table 6.2.

    The limit depends on the number of studs per rib ``n_r`` (the table has a
    row for n_r = 1 and a row for n_r >= 2), whether the studs are welded
    through the profiled sheeting, and the nominal sheet thickness ``t_sheet``
    (the threshold is 1.0 mm). For ``n_r > 2`` the n_r >= 2 row applies.

    .. note::
        Only the welded-through, ``t <= 1.0 mm`` column (0.85 for n_r = 1, 0.70
        for n_r >= 2) is corroborated by the source documents (W01628 ComFlor 60
        guide; W01640 SCI P359/P405). The other columns reproduce EN 1994-1-1
        Table 6.2 as published but were not present in the extracted corpus —
        verify them against a copy of the code, or pass an explicit cap to
        :func:`kt_profiled_transverse` via its ``kt_max`` argument.

    Parameters
    ----------
    n_r : int
        Number of stud connectors in one rib at a beam intersection (>= 1). In
        EN 1994-1-1 §6.6.4.2(2) ``n_r`` is also limited to <= 2 inside Eq. 6.23
        — that clamp is applied by :func:`kt_profiled_transverse`, not here;
        this lookup only selects the n_r = 1 vs n_r >= 2 ROW.
    welded_through : bool
        True if the studs are welded through the profiled sheeting (default),
        False otherwise (the more onerous columns).
    t_sheet : float
        Nominal thickness of the profiled steel sheeting [mm] (default 1.0).
        ``t_sheet <= 1.0`` selects the thin-sheet column.

    Returns
    -------
    k_t_max : float
        The Table 6.2 upper limit for k_t.

    Raises
    ------
    ValueError
        If ``n_r < 1`` or ``t_sheet <= 0``.
    """
    if n_r < 1:
        raise ValueError("n_r must be >= 1.")
    if t_sheet <= 0.0:
        raise ValueError("t_sheet must be positive.")
    n_r_row = 1 if n_r == 1 else 2
    thin_sheet = t_sheet <= 1.0
    return _KT_MAX_TABLE_6_2[(n_r_row, bool(welded_through), thin_sheet)]


def kt_profiled_transverse(
    b0: float,
    hp: float,
    hsc: float,
    n_r: int,
    welded_through: bool = True,
    t_sheet: float = 1.0,
    kt_max: float | None = None,
) -> float:
    """Reduction factor k_t for headed studs in profiled sheeting with the ribs
    running TRANSVERSE (perpendicular) to the supporting beam
    (EN 1994-1-1 §6.6.4.2, Eq. 6.23):

        k_t = (0.7 / sqrt(n_r)) * (b0 / hp) * (h_sc / hp - 1) <= k_t,max

    where ``b0`` is the mean (for trapezoidal ribs) width of the concrete rib,
    ``hp`` the depth of the profiled sheeting, ``h_sc`` the overall stud height
    and ``n_r`` the number of studs in one rib at the beam crossing. Two
    §6.6.4.2(2) provisos are applied:

    * ``n_r`` is taken as not greater than 2 in the (0.7/sqrt(n_r)) term even if
      more studs are present; and
    * ``h_sc`` is taken as not greater than ``hp + 75 mm`` in the (h_sc/hp - 1)
      term.

    The result is capped at ``k_t,max`` from :func:`kt_max_table_6_2`
    (EN 1994-1-1 Table 6.2), or at an explicit ``kt_max`` if supplied.

    Parameters
    ----------
    b0 : float
        Width of the concrete rib [mm] (mean width for a trapezoidal rib;
        the width at the top for a re-entrant rib). For ComFlor 60, b0 = 100 mm.
    hp : float
        Depth of the profiled steel sheeting (rib height) [mm].
    hsc : float
        Overall nominal height of the stud connector [mm]. Must exceed ``hp``
        (the stud has to project above the rib). Capped at ``hp + 75`` internally.
    n_r : int
        Number of stud connectors in one rib at the beam crossing (>= 1).
        Clamped to 2 inside Eq. 6.23 per §6.6.4.2(2).
    welded_through : bool
        Studs welded through the sheeting (default True) — selects the Table 6.2
        column for k_t,max. Ignored if ``kt_max`` is given.
    t_sheet : float
        Nominal sheet thickness [mm] (default 1.0) — selects the Table 6.2
        column for k_t,max. Ignored if ``kt_max`` is given.
    kt_max : float, optional
        Explicit upper limit, bypassing the Table 6.2 lookup. Provide this when
        you read the cap straight from a copy of the standard (recommended for
        the columns not corroborated by the source documents). Appended LAST so
        existing positional calls stay valid.

    Returns
    -------
    k_t : float
        Reduction factor (> 0), already capped at k_t,max.

    Raises
    ------
    ValueError
        If any of ``b0, hp, hsc`` is non-positive, if ``hsc <= hp`` (stud does
        not project above the rib, Eq. 6.23 would be <= 0), if ``n_r < 1`` or if
        ``kt_max <= 0``.
    """
    if min(b0, hp, hsc) <= 0.0:
        raise ValueError("b0, hp and hsc must be positive.")
    if n_r < 1:
        raise ValueError("n_r must be >= 1.")
    if hsc <= hp:
        raise ValueError(
            "hsc must exceed hp (the stud must project above the rib for "
            "Eq. 6.23 to be positive)."
        )
    if kt_max is not None and kt_max <= 0.0:
        raise ValueError("kt_max must be positive when supplied.")

    n_r_eff = min(n_r, 2)  # §6.6.4.2(2): n_r limited to 2 in Eq. 6.23
    hsc_eff = min(hsc, hp + 75.0)  # §6.6.4.2(2): h_sc limited to hp + 75 mm
    k_t = (0.7 / math.sqrt(n_r_eff)) * (b0 / hp) * (hsc_eff / hp - 1.0)

    cap = kt_max if kt_max is not None else kt_max_table_6_2(
        n_r, welded_through=welded_through, t_sheet=t_sheet
    )
    return min(k_t, cap)


def kl_profiled_parallel(b0: float, hp: float, hsc: float) -> float:
    """Reduction factor k_l for headed studs in profiled sheeting with the ribs
    running PARALLEL to the supporting beam (EN 1994-1-1 §6.6.4.1, Eq. 6.22):

        k_l = 0.6 * (b0 / hp) * (h_sc / hp - 1) <= 1.0

    Unlike the transverse factor k_t, the parallel factor has a fixed upper
    limit of 1.0 (no Table 6.2 dependence) and no n_r term. The §6.6.4.2(2) cap
    ``h_sc <= hp + 75 mm`` is applied in the (h_sc/hp - 1) term.

    Parameters
    ----------
    b0 : float
        Width of the concrete rib [mm] (mean width for a trapezoidal rib).
    hp : float
        Depth of the profiled steel sheeting (rib height) [mm].
    hsc : float
        Overall nominal height of the stud [mm]; must exceed ``hp``. Capped at
        ``hp + 75`` internally.

    Returns
    -------
    k_l : float
        Reduction factor in (0, 1.0].

    Raises
    ------
    ValueError
        If any of ``b0, hp, hsc`` is non-positive or if ``hsc <= hp``.
    """
    if min(b0, hp, hsc) <= 0.0:
        raise ValueError("b0, hp and hsc must be positive.")
    if hsc <= hp:
        raise ValueError(
            "hsc must exceed hp (the stud must project above the rib for "
            "Eq. 6.22 to be positive)."
        )
    hsc_eff = min(hsc, hp + 75.0)
    k_l = 0.6 * (b0 / hp) * (hsc_eff / hp - 1.0)
    return min(k_l, 1.0)


def prd_profiled_transverse(
    d: float,
    fu_stud: float,
    fck: float,
    hsc: float,
    b0: float,
    hp: float,
    n_r: int,
    Ecm: float | None = None,
    gamma_v: float = 1.25,
    welded_through: bool = True,
    t_sheet: float = 1.0,
    kt_max: float | None = None,
) -> float:
    """Design shear resistance of a headed stud in profiled sheeting with ribs
    TRANSVERSE to the beam (EN 1994-1-1 §6.6.4.2):

        P_Rd,profiled = k_t * P_Rd,solid

    where ``P_Rd,solid`` is the solid-slab resistance of §6.6.3.1
    (:func:`shear_connector_resistance`) and ``k_t`` is the transverse-rib
    reduction of :func:`kt_profiled_transverse` (Eq. 6.23, capped by Table 6.2).
    Because ``0 < k_t <= k_t,max <= 1``, the result is always below the
    solid-slab value.

    Parameters
    ----------
    d, fu_stud, fck, Ecm, gamma_v : float
        Stud and concrete parameters for the solid-slab resistance — see
        :func:`shear_connector_resistance`. ``Ecm`` defaults to the EN 1992-1-1
        estimate when None.
    hsc : float
        Overall stud height [mm] (used by BOTH the solid-slab resistance and
        Eq. 6.23).
    b0, hp, n_r, welded_through, t_sheet, kt_max :
        Rib geometry and Table 6.2 selectors for k_t — see
        :func:`kt_profiled_transverse`.

    Returns
    -------
    P_Rd,profiled : float
        Design shear resistance of one stud in the deck rib [N].
    """
    P_solid = shear_connector_resistance(
        d=d, fu_stud=fu_stud, fck=fck, h_sc=hsc, Ecm=Ecm, gamma_v=gamma_v
    )
    k_t = kt_profiled_transverse(
        b0=b0, hp=hp, hsc=hsc, n_r=n_r,
        welded_through=welded_through, t_sheet=t_sheet, kt_max=kt_max,
    )
    return k_t * P_solid


def partial_interaction(
    N_connectors: int,
    N_full: int,
    Le: float | None = None,
    check_eta_min: bool = True,
    fy: float = 355.0,
) -> dict:
    """Degree of shear connection eta = N / Nf (EN 1994-1-1 §6.6.1.2).

    The minimum allowable eta_min for ductile connectors in a beam with
    equal-flange steel sections is

        eta_min = 1 - (355/fy) * (0.75 - 0.03*Le)     with Le in m, Le <= 25 m
        eta_min >= 0.4

    where fy is the nominal yield strength of the steel section [N/mm^2]
    (Eq. 6.12, equal-flange sections; for unequal flanges the more severe
    Eq. 6.13 with 0.30 - 0.015*Le applies — not implemented here). A higher
    steel grade gives a smaller (355/fy) factor and therefore a more
    demanding (larger) eta_min.

    Parameters
    ----------
    N_connectors : int
        Provided number of shear connectors in the critical length.
    N_full : int
        Connectors required for full interaction.
    Le : float, optional
        Critical length in meters (typically the span of a simply-supported
        beam). Only used when check_eta_min=True.
    check_eta_min : bool
        If True, evaluates the §6.6.1.2 minimum and reports a pass/fail.
    fy : float
        Nominal yield strength of the structural steel [N/mm^2] (default 355,
        i.e. S355, which reproduces the legacy behaviour). Appended LAST on
        purpose: hardening an exported function must add parameters, never
        insert them, so existing positional calls stay valid.

    Returns
    -------
    dict with keys: 'eta', 'eta_min', 'ok'.
    """
    if N_full <= 0 or N_connectors < 0:
        raise ValueError("N_full must be positive, N_connectors non-negative.")
    if fy <= 0:
        raise ValueError("fy must be positive.")
    eta = N_connectors / N_full
    eta_min = None
    ok = None
    if check_eta_min and Le is not None:
        Le_m = min(Le, 25.0)
        eta_min = max(0.4, 1.0 - (355.0 / fy) * (0.75 - 0.03 * Le_m))
        ok = eta >= eta_min
    return {"eta": eta, "eta_min": eta_min, "ok": ok}


def m_rd_partial_interaction(
    eta: float,
    M_pl_a_Rd: float,
    M_pl_Rd: float,
) -> float:
    """Design bending resistance with PARTIAL shear connection — simplified
    linear ("line AC") method per EN 1994-1-1 §6.2.1.3:

        M_Rd = M_pl,a,Rd + eta * (M_pl,Rd - M_pl,a,Rd)

    where eta = Nc/Nc,f is the degree of shear connection. The expression
    interpolates linearly between the bare-steel plastic moment M_pl,a,Rd
    (eta -> 0) and the full-interaction composite moment M_pl,Rd (eta = 1);
    it is conservative relative to the true convex M_Rd-eta curve
    (EN 1994-1-1 Fig. 6.5).

    Parameters
    ----------
    eta : float
        Degree of shear connection Nc/Nc,f in [0, 1]. Practical designs must
        also satisfy eta >= eta_min (see :func:`partial_interaction`).
    M_pl_a_Rd : float
        Plastic moment resistance of the structural steel section alone
        [kN*m].
    M_pl_Rd : float
        Plastic moment resistance with full shear connection [kN*m]; must be
        >= M_pl_a_Rd.

    Returns
    -------
    M_Rd : float
        Design moment resistance for the given degree of shear connection,
        same units as the inputs [kN*m].
    """
    if not (0.0 <= eta <= 1.0):
        raise ValueError("eta (degree of shear connection) must be in [0, 1].")
    if M_pl_a_Rd < 0.0 or M_pl_Rd < 0.0:
        raise ValueError("Moment resistances must be non-negative.")
    if M_pl_Rd < M_pl_a_Rd:
        raise ValueError(
            "M_pl_Rd (full interaction) must be >= M_pl_a_Rd (bare steel)."
        )
    return M_pl_a_Rd + eta * (M_pl_Rd - M_pl_a_Rd)


def beta_flexural_reduction(x_pl_over_h: float) -> float:
    """Reduction factor beta applied to M_pl,Rd for high-grade steel
    (S420 and S460) per EN 1994-1-1 §6.2.1.2(2).

    When the plastic neutral axis is deep (large x_pl/h) the high strain
    demanded of S420/S460 steel may not be reached before the concrete
    crushes, so M_pl,Rd is reduced:

        beta = 1.0                                            x_pl/h <= 0.15
        beta = 1.0 - (x_pl/h - 0.15)/(0.40 - 0.15)*(1 - 0.85) 0.15 < x_pl/h <= 0.40
        x_pl/h > 0.40 : method NOT applicable -> §6.2.1.4 or §6.2.1.5

    This factor applies ONLY to S420/S460. For S235..S355 use beta = 1.0
    (do not call this function).

    Parameters
    ----------
    x_pl_over_h : float
        Ratio of plastic-neutral-axis depth to overall section depth, x_pl/h.

    Returns
    -------
    beta : float
        Reduction factor in [0.85, 1.0].

    Raises
    ------
    ValueError
        If x_pl/h > 0.40 (the linear-reduction method does not apply; check
        the section with EN 1994-1-1 §6.2.1.4 or §6.2.1.5), or if x_pl/h < 0.
    """
    if x_pl_over_h < 0.0:
        raise ValueError("x_pl/h must be non-negative.")
    if x_pl_over_h <= 0.15:
        return 1.0
    if x_pl_over_h <= 0.40:
        return 1.0 - (x_pl_over_h - 0.15) / (0.40 - 0.15) * (1.0 - 0.85)
    raise ValueError(
        "x_pl/h > 0.40: the beta-reduction method of EN 1994-1-1 §6.2.1.2(2) "
        "does not apply; check the section with §6.2.1.4 or §6.2.1.5."
    )


# ===========================================================================
# Lateral-torsional buckling of a continuous composite beam (EN 1994-1-1 §6.4)
# ---------------------------------------------------------------------------
# In hogging regions of a continuous composite beam the BOTTOM steel flange is
# in compression while the slab restrains the top flange; the member can buckle
# laterally in the "inverted U-frame" mode (EN 1994-1-1 §6.4.2). The check is
#   M_b,Rd = chi_LT * M_Rd                                     [expr. 6.6]
#   lambda_LT = sqrt(M_Rk / M_cr)                              [expr. 6.7]
# with M_cr from the inverted-U-frame model and chi_LT from the EN 1993-1-1
# §6.3.2 buckling curves. NB the LTB reduction chi_LT is NOT the column
# reduction chi_buckling of §6.3.1.2 (see :func:`chi_lt`).
# ===========================================================================

# Imperfection factor alpha_LT for the four LTB buckling curves
# (EN 1993-1-1 §6.3.2.2 Table 6.3 / §6.3.2.3 Table 6.5). LTB uses curves a-d
# (curve 'd', alpha_LT = 0.76, is additional w.r.t. the a-c set of chi_buckling).
_ALPHA_LT = {"a": 0.21, "b": 0.34, "c": 0.49, "d": 0.76}


def chi_lt(
    lambda_lt: float,
    curve: Literal["a", "b", "c", "d"] = "b",
    method: Literal["rolled", "general"] = "rolled",
) -> float:
    """Reduction factor chi_LT for lateral-torsional buckling
    (EN 1993-1-1 §6.3.2), used by EN 1994-1-1 §6.4.2 expr. (6.6).

    Two methods are provided; they are NOT numerically equal:

    * ``method="general"`` — the GENERAL case of EN 1993-1-1 §6.3.2.2 expr.
      (6.56). Identical algebra to the column reduction of §6.3.1.2
      (``lambda_LT,0 = 0.2``, ``beta = 1.0``), capped only at ``chi_LT <= 1``::

          Phi_LT = 0.5 * [1 + alpha_LT*(lambda_LT - 0.2) + lambda_LT^2]
          chi_LT = 1 / (Phi_LT + sqrt(Phi_LT^2 - lambda_LT^2)) <= 1.0

    * ``method="rolled"`` (DEFAULT) — the method for ROLLED sections and
      equivalent welded sections of EN 1993-1-1 §6.3.2.3 expr. (6.57), with the
      recommended ``lambda_LT,0 = 0.4`` and ``beta = 0.75``, and the ADDITIONAL
      cap ``chi_LT <= 1/lambda_LT^2``::

          Phi_LT = 0.5 * [1 + alpha_LT*(lambda_LT - 0.4) + 0.75*lambda_LT^2]
          chi_LT = 1 / (Phi_LT + sqrt(Phi_LT^2 - 0.75*lambda_LT^2))
          chi_LT = min(chi_LT, 1.0, 1/lambda_LT^2)

    HOW chi_LT DIFFERS FROM :func:`compositejm.composite_column.chi_buckling`:
    (i) the rolled method has ``beta = 0.75`` (so ``beta`` multiplies
    ``lambda_LT^2`` INSIDE the square root) and ``lambda_LT,0 = 0.4`` (a longer
    plateau: chi_LT = 1 for lambda_LT <= 0.4, vs <= 0.2 for columns); and
    (ii) the rolled method adds the cap ``chi_LT <= 1/lambda_LT^2``. The general
    case is algebraically the same as ``chi_buckling`` but is a distinct,
    correctly-cited entry point for LTB (and supports curve 'd').

    Parameters
    ----------
    lambda_lt : float
        Non-dimensional LTB slenderness ``lambda_LT = sqrt(M_Rk/M_cr)``
        (>= 0), see :func:`m_cr_uframe` for M_cr.
    curve : {'a', 'b', 'c', 'd'}
        LTB buckling curve. For rolled doubly-symmetric I-sections the
        general-case selection is curve 'a' (h/b <= 2) or 'b' (h/b > 2);
        the rolled-method selection is one curve more severe (Table 6.5).
    method : {'rolled', 'general'}
        Reduction formula, as above. Default ``"rolled"`` (§6.3.2.3).

    Returns
    -------
    chi_LT : float
        Reduction factor in (0, 1].

    Raises
    ------
    ValueError
        If ``lambda_lt < 0``, ``curve`` is not a-d, or ``method`` is unknown.
    """
    if lambda_lt < 0.0:
        raise ValueError("lambda_lt must be non-negative.")
    if curve not in _ALPHA_LT:
        raise ValueError("curve must be one of 'a', 'b', 'c', 'd'.")
    if method not in ("rolled", "general"):
        raise ValueError("method must be 'rolled' or 'general'.")
    alpha = _ALPHA_LT[curve]
    lam0, beta = (0.4, 0.75) if method == "rolled" else (0.2, 1.0)
    if lambda_lt <= lam0:
        return 1.0
    Phi = 0.5 * (1.0 + alpha * (lambda_lt - lam0) + beta * lambda_lt ** 2)
    chi = 1.0 / (Phi + math.sqrt(Phi ** 2 - beta * lambda_lt ** 2))
    chi = min(chi, 1.0)
    if method == "rolled":
        chi = min(chi, 1.0 / lambda_lt ** 2)
    return chi


def u_frame_stiffness(
    EI_2: float,
    a: float,
    t_w: float,
    h_s: float,
    E_a: float = 210000.0,
    nu_a: float = 0.3,
    alpha: float = 3.0,
) -> dict:
    """Rotational stiffness k_s of the inverted U-frame per unit length of beam
    (EN 1994-1-1 §6.4.2(6), expr. 6.8-6.10), for a beam WITHOUT web encasement.

        k_1 = alpha * (EI)_2 / a                          [expr. 6.9]
        k_2 = E_a * t_w^3 / [4*(1 - nu_a^2) * h_s]        [expr. 6.10]
        k_s = k_1 * k_2 / (k_1 + k_2)                     [expr. 6.8]

    k_1 is the flexural stiffness contributed by the cracked composite slab
    acting as the transverse member of the U-frame; k_2 is the flexural
    stiffness of the steel web; k_s combines them in series (the softer one
    governs). All three are stiffnesses PER UNIT LENGTH of the beam.

    Units (be careful — this is the classic place for a silent bug): for k_1
    and k_2 to be combined they must share units. ``k_2`` evaluates to
    ``(N/mm^2) * mm^3 / mm = N``. Therefore ``(EI)_2`` must be supplied as the
    cracked composite-slab flexural stiffness PER UNIT WIDTH of slab, i.e. in
    ``N*mm^2/mm = N*mm`` (then ``k_1 = alpha*(EI)_2/a`` is ``N*mm/mm = N``).
    Both k_1 and k_2 then come out in N and k_s likewise.

    Parameters
    ----------
    EI_2 : float
        Cracked composite-slab flexural stiffness PER UNIT WIDTH [N*mm^2/mm].
    a : float
        Spacing of the (parallel) beams / transverse span of the slab acting as
        the U-frame member [mm].
    t_w : float
        Steel web thickness [mm].
    h_s : float
        Distance between the centroids of the steel flanges [mm].
    E_a : float
        Modulus of elasticity of structural steel [N/mm^2] (default 210000).
    nu_a : float
        Poisson's ratio of steel (default 0.3, giving 1 - nu_a^2 = 0.91).
    alpha : float
        Factor in expr. (6.9): 2 for an edge beam, 3 for an interior beam,
        4 if there are >= 4 similar beams (default 3.0, interior beam).

    Returns
    -------
    dict
        ``{'k_1': k_1, 'k_2': k_2, 'k_s': k_s}`` all in N (per unit length).

    Raises
    ------
    ValueError
        If any input is non-positive.
    """
    if min(EI_2, a, t_w, h_s, E_a, alpha) <= 0.0 or not (0.0 <= nu_a < 1.0):
        raise ValueError(
            "EI_2, a, t_w, h_s, E_a, alpha must be positive and 0 <= nu_a < 1."
        )
    k_1 = alpha * EI_2 / a
    k_2 = E_a * t_w ** 3 / (4.0 * (1.0 - nu_a ** 2) * h_s)
    k_s = k_1 * k_2 / (k_1 + k_2)
    return {"k_1": k_1, "k_2": k_2, "k_s": k_s}


def m_cr_uframe(
    k_s: float,
    L: float,
    EI_afz: float,
    GI_at: float,
    C_4: float,
    k_c: float = 1.0,
) -> float:
    """Elastic critical moment M_cr for lateral-torsional buckling of a
    continuous composite beam by the inverted-U-frame model
    (EN 1994-1-1 §6.4.2), as the closed form widely used in the literature
    (Roik/Hanswille; Johnson, "Composite Structures of Steel and Concrete"):

        M_cr = (k_c * C_4 / L) * sqrt( E*I_afz * ( G*I_at + k_s * L^2 / pi^2 ) )

    where the bracket under the root combines the St-Venant torsional stiffness
    of the steel section ``G*I_at`` with the U-frame lateral restraint term
    ``k_s * L^2 / pi^2`` (``k_s`` per :func:`u_frame_stiffness`), the whole
    multiplied by the minor-axis flexural stiffness ``E*I_afz`` of the bottom
    (compressed) flange. This grouping is the dimensionally-homogeneous one for
    ``k_s`` in N: ``E*I_afz`` [N*mm^2] times (``G*I_at`` [N*mm^2] + ``k_s*L^2``
    [N*mm^2]) gives N^2*mm^4 under the root -> sqrt -> N*mm^2 -> times (1/L)
    [1/mm] -> N*mm (a moment). ``C_4`` is a
    property factor that depends on the hogging bending-moment distribution and
    the beam geometry (tabulated in the source literature), and ``k_c`` is a
    property factor for the composite section.

    .. warning::
        EN 1994-1-1 §6.4.2 does NOT print this closed form in the body of the
        code (it points to specialist literature); the form above is the
        established U-frame expression but is NOT validated here against any
        resolved numeric case (no such worked example was available in the
        source fichas). ``C_4`` and ``k_c`` are therefore CALLER-SUPPLIED
        (read from the relevant table for the actual moment distribution) and
        are NOT hard-coded. Use the result as a model estimate; verify ``C_4``
        / ``k_c`` against the design reference for the load case at hand.

    Parameters
    ----------
    k_s : float
        U-frame rotational stiffness per unit length [N] (see
        :func:`u_frame_stiffness`).
    L : float
        Relevant length of the beam (length of the hogging region / distance
        between points of lateral restraint) [mm].
    EI_afz : float
        Minor-axis flexural stiffness ``E_a * I_afz`` of the bottom (compressed)
        steel flange [N*mm^2].
    GI_at : float
        St-Venant torsional stiffness ``G_a * I_at`` of the steel section
        [N*mm^2].
    C_4 : float
        Property factor for the hogging moment distribution (from the source
        table); dimensionless.
    k_c : float
        Property factor for the composite section (default 1.0); dimensionless.

    Returns
    -------
    M_cr : float
        Elastic critical moment in kN*m.

    Raises
    ------
    ValueError
        If any of ``k_s, L, EI_afz, GI_at, C_4, k_c`` is non-positive.
    """
    if min(k_s, L, EI_afz, GI_at, C_4, k_c) <= 0.0:
        raise ValueError(
            "k_s, L, EI_afz, GI_at, C_4, k_c must all be positive."
        )
    # Dimensionally-homogeneous grouping (k_s in N): E*I_afz multiplies the
    # whole bracket so both inner terms are N*mm^2 (else G*I_at would be added
    # to a far larger N^2*mm^4 term and silently vanish).
    under_root = EI_afz * (GI_at + k_s * L ** 2 / math.pi ** 2)
    M_cr = (k_c * C_4 / L) * math.sqrt(under_root)  # N*mm
    return M_cr / 1.0e6  # kN*m


def m_b_rd_ltb(
    M_Rd: float,
    lambda_lt: float,
    curve: Literal["a", "b", "c", "d"] = "b",
    method: Literal["rolled", "general"] = "rolled",
) -> float:
    """Design buckling resistance moment M_b,Rd for lateral-torsional buckling
    of a composite beam (EN 1994-1-1 §6.4.2 expr. 6.6):

        M_b,Rd = chi_LT * M_Rd

    with chi_LT from :func:`chi_lt`. Because chi_LT <= 1, M_b,Rd <= M_Rd always;
    and for a stocky beam (lambda_LT <= lambda_LT,0, i.e. 0.4 rolled / 0.2
    general) chi_LT = 1 and M_b,Rd = M_Rd (no LTB penalty).

    Parameters
    ----------
    M_Rd : float
        Design bending resistance of the cross-section [kN*m] (for a hogging
        region, the negative plastic moment :func:`mpl_rd_hogging`).
    lambda_lt : float
        LTB slenderness ``sqrt(M_Rk/M_cr)`` (>= 0).
    curve : {'a', 'b', 'c', 'd'}
        LTB buckling curve (see :func:`chi_lt`).
    method : {'rolled', 'general'}
        chi_LT formula (see :func:`chi_lt`). Default ``"rolled"``.

    Returns
    -------
    M_b_Rd : float
        Buckling resistance moment in the same units as ``M_Rd`` [kN*m].

    Raises
    ------
    ValueError
        If ``M_Rd < 0`` (or via :func:`chi_lt` for bad lambda/curve/method).
    """
    if M_Rd < 0.0:
        raise ValueError("M_Rd must be non-negative.")
    return chi_lt(lambda_lt, curve=curve, method=method) * M_Rd


# Table 6.1 of EN 1994-1-1 §6.4.3: maximum depth h (mm) of an uncased IPE/HEA
# (or similar) steel section for which the simplified verification permits
# OMITTING the LTB check, by steel grade. Values are the IPE column (the more
# common rolled I-beam). (HE sections allow larger depths; not tabulated here.)
_LTB_HMAX_IPE = {
    "S235": 600.0,
    "S275": 550.0,
    "S355": 400.0,
    "S420": 270.0,
    "S460": 270.0,
}


def ltb_simplified_hmax(grade: str) -> float:
    """Maximum IPE section depth h_max [mm] below which the LTB verification of
    a continuous composite beam may be OMITTED, per the simplified method of
    EN 1994-1-1 §6.4.3 Table 6.1 (IPE column).

        S235 -> 600 mm ; S275 -> 550 mm ; S355 -> 400 mm ;
        S420 -> 270 mm ; S460 -> 270 mm

    If the actual steel depth h <= h_max(grade) the inverted-U-frame LTB check
    (chi_LT, M_cr) need not be performed. Higher steel grades give smaller
    h_max (a slenderer flange buckles sooner). The tabulated values are for
    IPE/uncased sections; HE sections permit larger depths (not covered here).

    Parameters
    ----------
    grade : str
        Steel grade, one of ``"S235"``, ``"S275"``, ``"S355"``, ``"S420"``,
        ``"S460"`` (case-insensitive).

    Returns
    -------
    h_max : float
        Maximum section depth in mm.

    Raises
    ------
    ValueError
        If ``grade`` is not one of the tabulated grades.
    """
    key = str(grade).upper().strip()
    if key not in _LTB_HMAX_IPE:
        raise ValueError(
            "grade must be one of S235, S275, S355, S420, S460 "
            f"(got {grade!r})."
        )
    return _LTB_HMAX_IPE[key]


# ===========================================================================
# Demountable shear connectors per SCI P428
# ---------------------------------------------------------------------------
# Guidance on Demountable Composite Construction Systems for UK Practice
# (SCI P428). Bolted shear connectors and coupler systems.
# ===========================================================================

def demountable_connector_properties(
    system: Literal["Detail A", "Detail B", "Detail C", "Coupler"]
) -> dict[str, float]:
    """Properties for demountable shear connectors per SCI P428 Table 3.2.

    Returns design shear resistance P_Rd [N], slip stiffness k_sc [N/mm],
    characteristic force fraction 0.7*P_Rk [N], and elastic slip delta_el [mm].
    """
    props = {
        "Detail A": {
            "P_Rd": 24000.0,
            "k_sc": 15000.0,
            "0.7P_Rk": 21000.0,
            "delta_el": 1.4,
        },
        "Detail B": {
            "P_Rd": 51000.0,
            "k_sc": 25000.0,
            "0.7P_Rk": 45000.0,
            "delta_el": 1.8,
        },
        "Detail C": {
            "P_Rd": 44000.0,
            "k_sc": 17000.0,
            "0.7P_Rk": 39000.0,
            "delta_el": 2.3,
        },
        "Coupler": {
            "P_Rd": 39000.0,
            "k_sc": 19000.0,
            "0.7P_Rk": 34000.0,
            "delta_el": 1.8,
        },
    }
    if system not in props:
        raise ValueError(
            f"Unknown system: {system!r}. Must be 'Detail A', 'Detail B', 'Detail C', or 'Coupler'."
        )
    return props[system]


def prd_demountable_bolt_failure(
    f_ub: float,
    A_s: float,
    gamma_M2: float = 1.25,
) -> float:
    """Design shear resistance P_Rd,bolt of a demountable bolt connector
    governed by bolt shear failure (SCI P428 Eq 3.10 / BS EN 1993-1-8 Table 3.4).

    Parameters
    ----------
    f_ub : float
        Ultimate tensile strength of the bolt material [N/mm^2] (e.g. 800 for 8.8).
    A_s : float
        Tensile stress area of the bolt [mm^2] (e.g. 245 for M20).
    gamma_M2 : float
        Partial safety factor for bolt shear (recommended 1.25).

    Returns
    -------
    P_Rd : float
        Design shear resistance [N].
    """
    if min(f_ub, A_s, gamma_M2) <= 0.0:
        raise ValueError("All inputs must be positive.")
    return 0.6 * f_ub * A_s / gamma_M2


def prd_demountable_concrete_failure(
    A_s: float,
    fu_stud: float,
    fck: float,
    h_sc: float,
    Ecm: float | None = None,
    gamma_v: float = 1.25,
) -> float:
    """Design shear resistance of a demountable connector governed by concrete
    failure (SCI P428 §3.2.2).

    It uses the solid-slab shear connector resistance formula of EN 1994-1-1
    §6.6.3.1 with effective diameter d_s = sqrt(4 * A_s / pi) and a reduction
    factor of 0.6:

        P_Rd = 0.6 * shear_connector_resistance(d_s, ...)

    Parameters
    ----------
    A_s : float
        Tensile stress area of the bolt [mm^2] (e.g. 245 for M20).
    fu_stud : float
        Ultimate tensile strength of stud material [N/mm^2].
    fck : float
        Characteristic cylinder strength of concrete [N/mm^2].
    h_sc : float
        Overall nominal height of the connector [mm].
    Ecm : float, optional
        Secant modulus of concrete [N/mm^2]. If None, estimated from fck.
    gamma_v : float
        Partial factor for shear connection (recommended 1.25).

    Returns
    -------
    P_Rd : float
        Design shear resistance [N].
    """
    if A_s <= 0.0:
        raise ValueError("A_s must be positive.")
    d_eff = math.sqrt(4.0 * A_s / math.pi)
    P_solid = shear_connector_resistance(
        d=d_eff, fu_stud=fu_stud, fck=fck, h_sc=h_sc, Ecm=Ecm, gamma_v=gamma_v
    )
    return 0.6 * P_solid


def k_flex_factor(
    distribution: Literal["uniform", "pseudo-elastic", "welded"]
) -> float:
    """Stiffness/flexibility reduction factor k_flex for demountable connectors
    (SCI P428 Eq 3.11).

    For non-ductile (bolted) connectors, the ULS shear connection resistance
    is reduced depending on the layout.

    Parameters
    ----------
    distribution : {'uniform', 'pseudo-elastic', 'welded'}
        Type of connector spacing/layout along the beam span.
        'uniform' -> 0.80
        'pseudo-elastic' -> 0.85
        'welded' -> 1.0 (standard welded studs)

    Returns
    -------
    k_flex : float
        The factor to multiply P_Rd.
    """
    factors = {
        "uniform": 0.80,
        "pseudo-elastic": 0.85,
        "welded": 1.0,
    }
    if distribution not in factors:
        raise ValueError(
            f"Unknown distribution: {distribution!r}. Must be 'uniform', 'pseudo-elastic', or 'welded'."
        )
    return factors[distribution]


def calc_slippage_sls(
    h_p: float,
    h_c: float,
    z_a: float,
    M_Ed: float,
    L: float,
    E_a: float,
    I_y_comp: float,
    k_sc: float,
    A_c: float,
    A_a: float,
    n: float,
    s_sc_eq: float,
) -> float:
    """SLS maximum end slippage s_bar of a composite beam with demountable
    shear connectors (SCI P428 Eq 5.4).

    Parameters
    ----------
    h_p : float
        Depth of the profiled steel sheeting ribs [mm].
    h_c : float
        Slab depth above the steel top flange [mm].
    z_a : float
        Distance from the top of the steel flange to the steel section centroid [mm]
        (h_a/2 for doubly-symmetric section).
    M_Ed : float
        Design bending moment at mid-span under serviceability limit state [N*mm].
    L : float
        Span length [mm].
    E_a : float
        Modulus of elasticity of structural steel [N/mm^2].
    I_y_comp : float
        Second moment of area of the composite section [mm^4].
    k_sc : float
        Rotational/slip stiffness of a single connector [N/mm].
    A_c : float
        Area of concrete slab [mm^2].
    A_a : float
        Area of steel section [mm^2].
    n : float
        Modular ratio E_a / E_cm.
    s_sc_eq : float
        Equivalent connector spacing along the beam [mm] (s_sc,eq = s_sc,1 / 0.625
        for pseudo-elastic distribution, SCI P428 Eq 4.15).

    Returns
    -------
    s_bar : float
        Maximum slip at the beam end [mm]. Must be <= 1.2 mm (SCI P428 Eq 5.6)
        to prevent permanent slip under service loads.
    """
    if min(h_c, M_Ed, L, E_a, I_y_comp, k_sc, A_c, A_a, n, s_sc_eq) <= 0.0:
        raise ValueError("Inputs must be positive.")
    if h_p < 0.0 or z_a < 0.0:
        raise ValueError("h_p and z_a must be non-negative.")

    term_num = A_c + n * A_a
    term_den = A_c * A_a * E_a * s_sc_eq
    bracket = 1.0 + k_sc * (L / math.pi) ** 2 * (term_num / term_den)
    lever_arm = h_p + 0.5 * h_c + z_a
    s_bar = (lever_arm * M_Ed * bracket) / (L * E_a * I_y_comp)
    return s_bar

