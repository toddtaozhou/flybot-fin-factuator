"""Generate a dense, electrically SERIES-connected CW/CCW spiral pair in KiCad.

In KiCad PCB Editor's Python console:
    exec(open(r"C:\\path\\create_cw_ccw_coil_pair_dense.py", encoding="utf-8").read())

LEFT coil:  CW current (top view).       RIGHT coil: CCW current (top view).
Current path: LEFT L1->L2->...->LN, bridge on LN, RIGHT LN->...->L2->L1.
All winding segments advance in the desired angular direction. Layer-change
leads are RADIAL tracks (no backward-going circular escape arcs).

VIA_MODE = "HDI":    ~7 full turns/layer. Very small layer-pair microvias
                     share XY, but NOT copper layers. Needs advanced fab.
VIA_MODE = "THROUGH": ~5.25-5.375 turns/layer with 0.25/0.12 mm plated
                     through vias; staggered phases and radial traces.
                     Conventional through-via construction, albeit fine vias.

IMPORTANT:
* Configure the actual board copper layer count to NUM_LAYERS (4, 6, or 8).
* NET_NAME must already exist on the PCB; both terminal ends use that net.
* This ADDS tracks and vias, does not replace or delete existing geometry.
* No same-layer copper bridge should be mistaken for a coil turn; the only
  nonspiral copper is straight radial transition/terminal leads and the
  single straight inter-coil bridge on the bottom copper layer.
* Run KiCad DRC. Check clearances to existing board items and assembly pads.
* HDI is a SPECULATIVE manufacturing topology until your fabricator approves
  the microvia sizes, internal laser vias, and shared-XY layer-pair locations.
"""

import math
import pcbnew

# ============================================================================
# USER PARAMETERS
# ============================================================================
NUM_LAYERS = 8                  # 4, 6, or 8; PCB stack must match
VIA_MODE = "HDI"               # "HDI" for MAX turns, or "THROUGH" for PTH
NET_NAME = "/COIL+"     # Use an existing PCB net

LEFT_CX = 90.0                  # Center coordinates, mm
CY = 100.0
CENTER_DISTANCE = 6.0          # Left-to-right distance, mm

TRACE = 0.16                   # mm; existing coil trace width
GAP = 0.10                     # mm; existing coil gap
R_OUT = 2.5                   # mm; outer TRACE CENTERLINE radius
STEP_DEG = 2.0                 # degrees; straight segment approximation

# Clearance margin above the target GAP (copper-to-copper, via-to-track)
EXTRA_CLEARANCE = 0.015        # mm; raise when fabrication requires it

# HDI: independent adjacent-layer microvias (each spans exactly TWO layers).
HDI_VIA_DIAMETER = 0.24        # mm; requires fabricator approval
HDI_VIA_DRILL = 0.15           # mm; laser microvia
HDI_OUTER_VIA_RADIUS = 2.86   # mm; radial via position outside each spiral

# THROUGH: independent conventional through-vias, distributed in empty core.
PTH_VIA_DIAMETER = 0.25        # mm; check finished hole + aspect ratio
PTH_VIA_DRILL = 0.12           # mm; potentially challenging for thick stackups
PTH_INNER_RING_RADIUS = 0.33  # mm; distinct via centers arranged in ring
PTH_OUTER_VIA_RADIUS = 2.8   # mm; distinct transitions around outer rim

# Radial, non-via terminal lead ends, on F.Cu. Add footprint pads separately.
TERMINAL_RADIUS = 2.8         # mm; bridge on bottom remains r=R_OUT

ADD_CENTER_CROSSES = False     # False avoids silk-over-via warnings
CROSS_SIZE = 0.20              # mm
CROSS_WIDTH = 0.10             # mm

# ============================================================================
# PREFLIGHT -- NO BOARD MODIFICATION BEFORE THESE CHECKS
# ============================================================================
board = pcbnew.GetBoard()
if board is None:
    raise RuntimeError("Open a KiCad PCB before running this script.")
if NUM_LAYERS not in (4, 6, 8):
    raise ValueError("NUM_LAYERS must be 4, 6, or 8.")
if VIA_MODE not in ("HDI", "THROUGH"):
    raise ValueError('VIA_MODE must be "HDI" or "THROUGH".')
if board.GetCopperLayerCount() != NUM_LAYERS:
    raise RuntimeError(
        "Board is configured for %d copper layers; set it to %d first."
        % (board.GetCopperLayerCount(), NUM_LAYERS)
    )
coil_net = board.FindNet(NET_NAME)
if coil_net is None:
    raise RuntimeError("Existing KiCad PCB net %r not found." % NET_NAME)

if TRACE <= 0 or GAP <= 0 or R_OUT <= 0 or STEP_DEG <= 0:
    raise ValueError("TRACE, GAP, R_OUT, and STEP_DEG must be positive.")
if STEP_DEG > 5.0:
    raise ValueError("STEP_DEG > 5 degrees reduces width/gap precision.")
if CENTER_DISTANCE < 2.0 * R_OUT + TRACE + GAP:
    raise ValueError("Coil copper disks too close to each other.")
if TERMINAL_RADIUS < R_OUT:
    raise ValueError("TERMINAL_RADIUS must be outside R_OUT.")

layers = ([pcbnew.F_Cu] +
          [getattr(pcbnew, "In%d_Cu" % i) for i in range(1, NUM_LAYERS - 1)] +
          [pcbnew.B_Cu])
PITCH = TRACE + GAP
m = NUM_LAYERS // 2

# The boundary angles for each two-layer pair rotate around the perimeter.
# In THROUGH mode this puts EVERY layer near its maximum possible turns,
# without using any circumferential escape routing. In HDI all boundary
# angles may be constant because each via is restricted to its layer pair.
if VIA_MODE == "HDI":
    via_d, via_drill = HDI_VIA_DIAMETER, HDI_VIA_DRILL
    via_radius = 0.0
    outer_via_radius = HDI_OUTER_VIA_RADIUS
    fraction = 0.0
    max_n = (R_OUT - (via_d / 2 + TRACE / 2 + GAP + EXTRA_CLEARANCE)) / PITCH
    turns = float(math.floor(max_n + 1e-10))
else:
    via_d, via_drill = PTH_VIA_DIAMETER, PTH_VIA_DRILL
    via_radius = PTH_INNER_RING_RADIUS
    outer_via_radius = PTH_OUTER_VIA_RADIUS
    # Two layers together must rotate their outer ends by 360/m. Each layer
    # therefore advances (k + (m-1)/(2m)) turns of CONSTANT angular sign.
    fraction = (m - 1) / (2.0 * m)
    min_inner_r = via_radius + via_d / 2 + TRACE / 2 + GAP + EXTRA_CLEARANCE
    max_n = (R_OUT - min_inner_r) / PITCH
    turns = float(math.floor(max_n - fraction + 1e-10) + fraction)

R_IN = R_OUT - PITCH * turns
if turns < 1.0:
    raise ValueError("Insufficient radial space for at least one spiral turn.")
if via_d <= via_drill or via_drill <= 0:
    raise ValueError("Via pad diameter must exceed drill diameter > 0.")
min_gap_inner = R_IN - via_radius - via_d / 2 - TRACE / 2
if min_gap_inner < GAP + EXTRA_CLEARANCE - 1e-8:
    raise ValueError("Inner via too close to inner winding: %.3f mm." % min_gap_inner)
min_gap_outer = outer_via_radius - R_OUT - via_d / 2 - TRACE / 2
if min_gap_outer < GAP + EXTRA_CLEARANCE - 1e-8:
    raise ValueError("Outer via too close to nonattached spiral: %.3f mm." % min_gap_outer)
# Check two terminal stubs are not so close that connecting pads can't be added.
terminal_distance = CENTER_DISTANCE - 2 * TERMINAL_RADIUS
if terminal_distance < TRACE + GAP + 2 * EXTRA_CLEARANCE:
    raise ValueError("Opposing front-layer terminal leads too close.")
# HDI outer via pair (one per coil) must not contact across the 6mm gap.
if CENTER_DISTANCE - 2 * outer_via_radius < via_d + GAP + EXTRA_CLEARANCE:
    raise ValueError("Opposing outer vias too close in central gap.")
# Any two THROUGH core vias must be separated with respect to pads and copper.
if VIA_MODE == "THROUGH":
    nearest_core_spacing = 2 * via_radius * math.sin(math.pi / m)
    if nearest_core_spacing < via_d + GAP + EXTRA_CLEARANCE:
        raise ValueError("Inner THROUGH vias too close; raise INNER_RING_RADIUS.")

# ============================================================================
# HELPERS
# ============================================================================
def xy(cx, radius, degrees):
    angle = math.radians(degrees)
    return (cx + radius * math.cos(angle), CY - radius * math.sin(angle))


def p2i(point):
    return pcbnew.VECTOR2I(pcbnew.FromMM(point[0]),
                            pcbnew.FromMM(point[1]))


def segment(a, b, copper_layer):
    if math.hypot(b[0] - a[0], b[1] - a[1]) < 1e-9:
        return
    track = pcbnew.PCB_TRACK(board)
    track.SetStart(p2i(a))
    track.SetEnd(p2i(b))
    track.SetWidth(pcbnew.FromMM(TRACE))
    track.SetLayer(copper_layer)
    track.SetNet(coil_net)
    board.Add(track)


def polyline(pts, copper_layer):
    for a, b in zip(pts, pts[1:]):
        segment(a, b, copper_layer)


def place_via(point, lower_index, upper_index):
    """Connect exact layer INDEX endpoints, not arbitrary whole stack."""
    via = pcbnew.PCB_VIA(board)
    via.SetPosition(p2i(point))
    if VIA_MODE == "HDI":
        # Each microvia spans adjacent Cu layers only; even repeated XY
        # locations are NOT electrically connected if layer pairs differ.
        via.SetViaType(pcbnew.VIATYPE_MICROVIA)
        via.SetLayerPair(layers[lower_index], layers[upper_index])
    else:
        via.SetViaType(pcbnew.VIATYPE_THROUGH)
        via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    via.SetWidth(pcbnew.FromMM(via_d))
    via.SetDrill(pcbnew.FromMM(via_drill))
    via.SetNet(coil_net)
    board.Add(via)


def coil_spiral(cx, copper_layer, direction, from_outside,
                phase_outer, phase_inner):
    """Emit a spiral in CURRENT direction, without any backward arc.

    direction: -1 for top-view CW, +1 for top-view CCW.
    On each layer the angle changes monotonically with given sign.
    """
    start_angle = phase_outer if from_outside else phase_inner
    n_steps = max(1, int(math.ceil(360.0 * turns / STEP_DEG)))
    pts = []
    for j in range(n_steps + 1):
        t = turns * j / n_steps
        r = R_OUT - PITCH * t if from_outside else R_IN + PITCH * t
        angle = start_angle + direction * 360.0 * t
        pts.append(xy(cx, r, angle))
    polyline(pts, copper_layer)
    inner = pts[-1] if from_outside else pts[0]
    outer = pts[0] if from_outside else pts[-1]
    expected_inner = xy(cx, R_IN, phase_inner)
    expected_outer = xy(cx, R_OUT, phase_outer)
    if math.dist(inner, expected_inner) > 1e-6 or math.dist(outer, expected_outer) > 1e-6:
        raise RuntimeError("Spiral phase calculation mismatch on layer %s." %
                           board.GetLayerName(copper_layer))
    return {"inner": inner, "outer": outer,
            "outer_angle": phase_outer, "inner_angle": phase_inner}


def cross(cx):
    for a, b in [((cx - CROSS_SIZE / 2, CY), (cx + CROSS_SIZE / 2, CY)),
                 ((cx, CY - CROSS_SIZE / 2), (cx, CY + CROSS_SIZE / 2))]:
        shape = pcbnew.PCB_SHAPE(board)
        shape.SetShape(pcbnew.SHAPE_T_SEGMENT)
        shape.SetStart(p2i(a))
        shape.SetEnd(p2i(b))
        shape.SetWidth(pcbnew.FromMM(CROSS_WIDTH))
        shape.SetLayer(pcbnew.F_SilkS)
        board.Add(shape)


def boundary_angle(side, j):
    if VIA_MODE == "HDI":
        return 0.0 if side == "L" else 180.0
    # Outer endpoint phase in each side's CURRENT traversal order.
    # LEFT traverses layer pairs k=0...m-1 (CW); RIGHT k=m-1...0 (CCW).
    return (360.0 * j / m if side == "L" else 180.0 - 360.0 * j / m)


def inner_phase(side, pair_index):
    if VIA_MODE == "HDI":
        return 0.0 if side == "L" else 180.0
    j = pair_index if side == "L" else m - 1 - pair_index
    return boundary_angle(side, j) + (-1 if side == "L" else +1) * 360.0 * fraction


# ============================================================================
# BUILD COMPLETE SINGLE-SERIES CURRENT PATH: F.Cu L IN -> B.Cu BRIDGE
# -> F.Cu R OUT. Only same-sense spiral trajectories, plus radial leads.
# ============================================================================
centers = {"L": LEFT_CX, "R": LEFT_CX + CENTER_DISTANCE}
coils = {}
for side, cx in centers.items():
    clockwise_sign = -1 if side == "L" else +1
    for li, layer in enumerate(layers):
        k = li // 2
        phase_in = inner_phase(side, k)
        if side == "L":
            # L1 OUT->IN, L2 IN->OUT, ..., LN IN->OUT.
            from_outside = (li % 2 == 0)
            outer_boundary_index = k if li % 2 == 0 else k + 1
        else:
            # Actual right-hand CURRENT reverses the physical layer order:
            # LN OUT->IN, L(N-1) IN->OUT ... L1 IN->OUT.
            from_outside = (li % 2 == 1)
            outer_boundary_index = (m - 1 - k if li % 2 == 1
                                    else m - k)
        phase_out = boundary_angle(side, outer_boundary_index)
        coils[(side, li)] = coil_spiral(
            cx, layer, clockwise_sign, from_outside, phase_out, phase_in
        )
    if ADD_CENTER_CROSSES:
        cross(cx)

# Inner transitions (L1/L2, L3/L4, ..., L(N-1)/LN).
for side, cx in centers.items():
    for k in range(m):
        a, b = 2 * k, 2 * k + 1
        phase = inner_phase(side, k)
        via_position = xy(cx, via_radius, phase)
        place_via(via_position, a, b)
        # Both are straight radial lines to the SAME via.
        segment(coils[(side, a)]["inner"], via_position, layers[a])
        segment(coils[(side, b)]["inner"], via_position, layers[b])

# Outer transitions (L2/L3, L4/L5, ..., L(N-2)/L(N-1)).
for side, cx in centers.items():
    for k in range(1, m):
        a, b = 2 * k - 1, 2 * k
        outer_boundary_index = k if side == "L" else m - k
        phase = boundary_angle(side, outer_boundary_index)
        via_position = xy(cx, outer_via_radius, phase)
        place_via(via_position, a, b)
        # Radial tracks, never circular backwards escape paths.
        segment(coils[(side, a)]["outer"], via_position, layers[a])
        segment(coils[(side, b)]["outer"], via_position, layers[b])

# Single straight bridge on last (B.Cu) layer, from L outer to R outer.
# Last-layer outer endpoints face each other at 0 degrees and 180 degrees.
bridge_l = coils[("L", NUM_LAYERS - 1)]["outer"]
bridge_r = coils[("R", NUM_LAYERS - 1)]["outer"]
if abs(bridge_l[1] - bridge_r[1]) > 1e-6:
    raise RuntimeError("Expected horizontal direct bridge; check phases.")
segment(bridge_l, bridge_r, layers[-1])

# Top-layer input / output terminal STUBS. These must be joined to actual
# surface-mount driver pads separately; using through-vias here would short
# the winding stack to the bottom bridge at the same coordinates.
input_fcu = xy(LEFT_CX, TERMINAL_RADIUS, 0.0)
output_fcu = xy(centers["R"], TERMINAL_RADIUS, 180.0)
segment(input_fcu, coils[("L", 0)]["outer"], layers[0])
segment(coils[("R", 0)]["outer"], output_fcu, layers[0])

pcbnew.Refresh()
print("\n" + "=" * 68)
print("DENSE CONNECTED CW/CCW SPIRAL PAIR GENERATED")
print("=" * 68)
print("Layers: %d (%s)" % (NUM_LAYERS, ", ".join(board.GetLayerName(x) for x in layers)))
print("Mode: %s  |  %.3f mm via pad / %.3f mm drill" %
      (VIA_MODE, via_d, via_drill))
print("Center separation: %.3f mm" % CENTER_DISTANCE)
print("Trace/gap/pitch: %.3f / %.3f / %.3f mm" % (TRACE, GAP, PITCH))
print("Turns per layer: %.3f  |  total turns per coil: %.3f" %
      (turns, NUM_LAYERS * turns))
print("Outer radius: %.3f mm  |  inner radius: %.3f mm" % (R_OUT, R_IN))
print("Minimum radial clearance to inner via pads: %.3f mm" % min_gap_inner)
print("Left coil CW; right coil CCW as CURRENT travels from input to output.")
print("Current: L1 -> ... -> L%d -> B.Cu bridge -> R%d -> ... -> R1" %
      (NUM_LAYERS, NUM_LAYERS))
print("Terminal track tips on F.Cu: IN=%r  OUT=%r" %
      (tuple(round(v, 4) for v in input_fcu),
       tuple(round(v, 4) for v in output_fcu)))
print("Transitions: center inner vias, outer radial vias; NO return arcs.")
print("WARNING: This script does not run KiCad DRC or check other PCB geometry.")
if VIA_MODE == "HDI":
    print("FAB WARNING: internal laser microvias and layer-pair stacking require")
    print("a capable HDI fabricator and matching KiCad board-design rules.")
else:
    print("FAB WARNING: check %.2f mm through drill aspect ratio for %d layers." %
          (via_drill, NUM_LAYERS))
print("=" * 68)
