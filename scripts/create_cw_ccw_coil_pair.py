"""
KiCad pcbnew: series-connected, opposite-polarity PCB spiral pair.

Paste into KiCad's PCB Editor Python console:
    exec(open(r"/path/to/create_cw_ccw_coil_pair.py", encoding="utf-8").read())

IMPORTANT:
* Configure the PCB's copper layer count to NUM_LAYERS BEFORE running.
* Only even NUM_LAYERS = 4, 6 or 8 are supported by this outer-to-outer
  inter-coil jumper topology.
* The original 6 turns at R_OUT = 2.12 mm would leave only R_IN = 0.56 mm,
  which cannot accommodate separate conventional through-vias for 8 layers.
  This safer through-via layout instead uses 4 turns per layer, R_IN=1.08 mm.
* Generated coils share NET_NAME, consistent with your previous scripts.
* This script ADDS geometry; undo or delete it before running again.
* Run PCB DRC and review your fabricator's via/trace clearance rules.
"""

import math
import pcbnew

# ============================================================================
# USER PARAMETERS
# ============================================================================
NUM_LAYERS = 6                  # Allowed: 4, 6, 8
NET_NAME = "/COIL+"     # Existing PCB net, as in your original scripts

LEFT_CX = 90.0                  # mm; left coil = CW (current, viewed from F.Cu)
CY = 100.0
CENTER_DISTANCE = 6.0          # mm; RIGHT_CX = LEFT_CX + CENTER_DISTANCE

TRACE = 0.16                   # mm
GAP = 0.10                     # mm
PITCH = TRACE + GAP            # mm/turn = 0.26
R_OUT = 2.12                   # mm, spiral trace centerline
TURNS_PER_LAYER = 4.0         # Four full turns -> R_IN = 1.08 mm

VIA_DIAMETER = 0.50            # mm through-hole pad diameter
VIA_DRILL = 0.25               # mm drill diameter
INNER_VIA_RADIUS = 0.60       # mm, center-to-inner-transition via
OUTER_VIA_RADIUS = 3.05       # mm, center-to-outer-transition via
ESCAPE_RADIUS = 2.50          # mm, exterior routing arc radius
TERMINAL_RADIUS = 3.65        # mm, external two-terminal endpoints

STEP_DEG = 2.0                # angular polyline approximation for spirals
ARC_STEP_DEG = 3.0            # angular polyline approximation for escape arcs

ADD_CENTER_CROSSES = True
CROSS_SIZE = 0.60
CROSS_WIDTH = 0.12

# Angles use conventional top-view coordinates: 90=up, -90=down.
# One unique THROUGH-via inside each pair of layers, all at radius 0.60.
INNER_ANGLES = (-135.0, -45.0, 45.0, 135.0)
# Outboard positions leave room for the second coil (6 mm separation).
LEFT_OUTER_ANGLES = (165.0, 180.0, 195.0)
RIGHT_OUTER_ANGLES = (15.0, 0.0, -15.0)

# ============================================================================
# VALIDATION AND SETUP
# ============================================================================
board = pcbnew.GetBoard()
if board is None:
    raise RuntimeError("Open a PCB in the KiCad PCB Editor first.")
if NUM_LAYERS not in (4, 6, 8):
    raise ValueError("NUM_LAYERS must be 4, 6 or 8 for this series routing.")
if board.GetCopperLayerCount() != NUM_LAYERS:
    raise RuntimeError(
        "PCB has %d copper layers, but NUM_LAYERS=%d. "
        "Configure Board Setup > Stackup > Physical Stackup first."
        % (board.GetCopperLayerCount(), NUM_LAYERS)
    )

coil_net = board.FindNet(NET_NAME)
if coil_net is None:
    raise RuntimeError("Net %r not found; make it in the PCB first." % NET_NAME)

R_IN = R_OUT - PITCH * TURNS_PER_LAYER
if not math.isclose(TURNS_PER_LAYER, round(TURNS_PER_LAYER), abs_tol=1e-9):
    raise ValueError("This route generator requires an integer number of turns.")
if VIA_DRILL >= VIA_DIAMETER:
    raise ValueError("The through-via drill must be smaller than its diameter.")

# Conservative radial keepout for nonconnected through-vias vs spiral traces.
min_inner_clearance = R_IN - INNER_VIA_RADIUS - (VIA_DIAMETER + TRACE) / 2
min_arc_clearance = OUTER_VIA_RADIUS - ESCAPE_RADIUS - (VIA_DIAMETER + TRACE) / 2
min_spiral_arc_clearance = ESCAPE_RADIUS - R_OUT - TRACE
if min_inner_clearance < GAP or min_arc_clearance < GAP or min_spiral_arc_clearance < GAP:
    raise ValueError(
        "Clearances insufficient: inner %.3f, outer-via/arc %.3f, "
        "spiral/arc %.3f mm; required %.3f mm."
        % (min_inner_clearance, min_arc_clearance, min_spiral_arc_clearance, GAP)
    )
if CENTER_DISTANCE <= 2 * (R_OUT + TRACE / 2 + GAP):
    raise ValueError("Coil centers too close for the spiral copper clearance.")

# Standard complete PCB stack, ending at B.Cu (unlike the original files,
# which named In3.Cu as layer 4).
layers = ([pcbnew.F_Cu] +
          [getattr(pcbnew, "In%d_Cu" % i) for i in range(1, NUM_LAYERS - 1)] +
          [pcbnew.B_Cu])

RIGHT_CX = LEFT_CX + CENTER_DISTANCE
centers = {"L": (LEFT_CX, CY), "R": (RIGHT_CX, CY)}

# ============================================================================
# GEOMETRY HELPERS
# ============================================================================
def mmpt(x, y):
    return pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y))


def polar(cx, cy, radius, degrees):
    a = math.radians(degrees)
    return (cx + radius * math.cos(a), cy - radius * math.sin(a))


def put_track(a, b, layer):
    if math.hypot(b[0] - a[0], b[1] - a[1]) < 1e-7:
        return
    obj = pcbnew.PCB_TRACK(board)
    obj.SetStart(mmpt(*a))
    obj.SetEnd(mmpt(*b))
    obj.SetWidth(pcbnew.FromMM(TRACE))
    obj.SetLayer(layer)
    obj.SetNet(coil_net)
    board.Add(obj)


def put_path(points, layer):
    for a, b in zip(points, points[1:]):
        put_track(a, b, layer)


def put_through_via(point):
    via = pcbnew.PCB_VIA(board)
    via.SetPosition(mmpt(*point))
    via.SetViaType(pcbnew.VIATYPE_THROUGH)
    via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    via.SetWidth(pcbnew.FromMM(VIA_DIAMETER))
    via.SetDrill(pcbnew.FromMM(VIA_DRILL))
    via.SetNet(coil_net)
    board.Add(via)
    return via


def spiral(cx, cy, layer, direction, from_outside, phase):
    """Follow copper in actual series-current order.

    direction=-1 => current CW viewed from TOP; +1 => CCW.
    from_outside indicates OUT->IN, else IN->OUT. Returns endpoint pairs.
    Integer turns guarantee that both endpoints lie at the same angle.
    """
    n = int(round(TURNS_PER_LAYER * 360.0 / STEP_DEG))
    result = []
    for i in range(n + 1):
        turns_completed = TURNS_PER_LAYER * i / n
        rad = (R_OUT - PITCH * turns_completed if from_outside
               else R_IN + PITCH * turns_completed)
        angle = phase + direction * 360.0 * turns_completed
        result.append(polar(cx, cy, rad, angle))
    put_path(result, layer)
    return {"inner": (result[-1] if from_outside else result[0]),
            "outer": (result[0] if from_outside else result[-1]),
            "start": result[0], "end": result[-1],
            "from_outside": from_outside}


def shortest_sweep(a, b):
    return (b - a + 180.0) % 360.0 - 180.0


def route_outside(cx, cy, starting_angle, ending_angle,
                  destination_radius=OUTER_VIA_RADIUS):
    """Copper route from R_OUT to a point outside the spiral.

    All arcs sit at ESCAPE_RADIUS. Other through-vias are far enough away
    that unrelated layer transitions do NOT connect to these arcs.
    """
    points = [polar(cx, cy, R_OUT, starting_angle),
              polar(cx, cy, ESCAPE_RADIUS, starting_angle)]
    sweep = shortest_sweep(starting_angle, ending_angle)
    steps = max(1, int(math.ceil(abs(sweep) / ARC_STEP_DEG)))
    for i in range(1, steps + 1):
        points.append(polar(cx, cy, ESCAPE_RADIUS,
                            starting_angle + sweep * i / steps))
    points.append(polar(cx, cy, destination_radius, ending_angle))
    return points


def add_cross(cx, cy):
    for a, b in [((cx - CROSS_SIZE / 2, cy), (cx + CROSS_SIZE / 2, cy)),
                 ((cx, cy - CROSS_SIZE / 2), (cx, cy + CROSS_SIZE / 2))]:
        obj = pcbnew.PCB_SHAPE(board)
        obj.SetShape(pcbnew.SHAPE_T_SEGMENT)
        obj.SetStart(mmpt(*a))
        obj.SetEnd(mmpt(*b))
        obj.SetWidth(pcbnew.FromMM(CROSS_WIDTH))
        obj.SetLayer(pcbnew.F_SilkS)
        board.Add(obj)

# ============================================================================
# BUILD ALL SPIRALS
# ============================================================================
coils = {}
for side, (cx, cy) in centers.items():
    coil_winding_direction = (-1 if side == "L" else +1)
    for li, layer in enumerate(layers):
        phase = INNER_ANGLES[li // 2]
        if side == "L":
            # Left series path is L1 -> L2 -> ... -> LN.
            from_outside = (li % 2 == 0)
        else:
            # Right path is LN -> ... -> L2 -> L1 (reverse layer order).
            from_outside = ((NUM_LAYERS - 1 - li) % 2 == 0)
        coils[(side, li)] = spiral(cx, cy, layer,
                                   coil_winding_direction, from_outside, phase)
    if ADD_CENTER_CROSSES:
        add_cross(cx, cy)

# ============================================================================
# INNER TRANSITIONS: L1-L2, L3-L4, L5-L6, L7-L8
# ONE dedicated through-via per interface, each at a DIFFERENT XY location.
# ============================================================================
for side, (cx, cy) in centers.items():
    for pair in range(NUM_LAYERS // 2):
        a = 2 * pair
        b = a + 1
        v = polar(cx, cy, INNER_VIA_RADIUS, INNER_ANGLES[pair])
        put_through_via(v)
        put_track(coils[(side, a)]["inner"], v, layers[a])
        put_track(coils[(side, b)]["inner"], v, layers[b])

# ============================================================================
# OUTER TRANSITIONS: L2-L3, L4-L5, L6-L7
# OUTBOARD vias are distinct, and pass harmlessly through other layers.
# ============================================================================
for side, (cx, cy) in centers.items():
    outer_angles = (LEFT_OUTER_ANGLES if side == "L" else RIGHT_OUTER_ANGLES)
    for pair in range(NUM_LAYERS // 2 - 1):
        a = 2 * pair + 1   # Layer L2/L4/L6
        b = a + 1          # Layer L3/L5/L7
        phase_a = INNER_ANGLES[a // 2]
        phase_b = INNER_ANGLES[b // 2]
        via_angle = outer_angles[pair]
        v = polar(cx, cy, OUTER_VIA_RADIUS, via_angle)
        put_through_via(v)
        put_path(route_outside(cx, cy, phase_a, via_angle), layers[a])
        put_path(route_outside(cx, cy, phase_b, via_angle), layers[b])

# ============================================================================
# INTER-COIL SERIES LINK: on LN, left outer -> right outer.
# Paths go outside both spirals via the BOTTOM (Y positive) and are joined.
# ============================================================================
last_idx = NUM_LAYERS - 1
last_phase = INNER_ANGLES[last_idx // 2]
left_bottom = polar(LEFT_CX, CY, TERMINAL_RADIUS, -90.0)
right_bottom = polar(RIGHT_CX, CY, TERMINAL_RADIUS, -90.0)
bridge_from_left = route_outside(LEFT_CX, CY, last_phase, -90.0,
                                 TERMINAL_RADIUS)
bridge_to_right = route_outside(RIGHT_CX, CY, last_phase, -90.0,
                                TERMINAL_RADIUS)
put_path(bridge_from_left, layers[last_idx])
put_track(left_bottom, right_bottom, layers[last_idx])
put_path(bridge_to_right, layers[last_idx])

# ============================================================================
# TWO EXTERNAL TERMINALS on F.Cu: top of left and right coils.
# Left L1 starts at left terminal; right L1 ends at right terminal.
# ============================================================================
first_phase = INNER_ANGLES[0]
left_terminal = polar(LEFT_CX, CY, TERMINAL_RADIUS, 90.0)
right_terminal = polar(RIGHT_CX, CY, TERMINAL_RADIUS, 90.0)
put_path(route_outside(LEFT_CX, CY, first_phase, 90.0,
                       TERMINAL_RADIUS), layers[0])
put_path(route_outside(RIGHT_CX, CY, first_phase, 90.0,
                       TERMINAL_RADIUS), layers[0])
# The terminal locations are convenient PTH contact vias. When solder pads
# are needed, place footprints/pads separately to meet mask/fab rules.
put_through_via(left_terminal)
put_through_via(right_terminal)

pcbnew.Refresh()

print("\n" + "=" * 65)
print("CONNECTED CW/CCW PCB COIL PAIR CREATED")
print("=" * 65)
print("Copper layers           :", NUM_LAYERS)
print("Actual layer sequence   :", " -> ".join(board.GetLayerName(l) for l in layers))
print("Pair centers            : (%.3f, %.3f), (%.3f, %.3f) mm" %
      (LEFT_CX, CY, RIGHT_CX, CY))
print("Center-to-center        : %.2f mm" % CENTER_DISTANCE)
print("Trace / Gap / Pitch     : %.2f / %.2f / %.2f mm" % (TRACE, GAP, PITCH))
print("Outer / Inner radius    : %.2f / %.2f mm" % (R_OUT, R_IN))
print("Turns per layer         : %.1f" % TURNS_PER_LAYER)
print("Left coil               : CW viewed from F.Cu")
print("Right coil              : CCW viewed from F.Cu")
print("Series current order    : left L1 -> ... -> L%d -> right L%d -> ... -> L1" %
      (NUM_LAYERS, NUM_LAYERS))
print("Bridge layer            :", board.GetLayerName(layers[-1]))
print("INPUT  F.Cu terminal    : (%.3f, %.3f) mm" % left_terminal)
print("OUTPUT F.Cu terminal    : (%.3f, %.3f) mm" % right_terminal)
print("Connection net          :", NET_NAME)
print("Via diameter / drill    : %.2f / %.2f mm" % (VIA_DIAMETER, VIA_DRILL))
print("All layer transitions   : placed with distinct THROUGH vias")
print("IMPORTANT: Run KiCad DRC and review manufacturability.")
print("=" * 65)
