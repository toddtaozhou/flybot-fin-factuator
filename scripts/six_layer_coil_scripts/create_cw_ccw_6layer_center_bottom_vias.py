"""KiCad pcbnew: 6-layer, 6.0-mm center-spacing CW/CCW series coil pair.

Routing change: keep both *upper* outer transition vias outboard, but move
both *lower* outer transition vias into the free center-bottom region.
Each coil remains 50 turns total, and the current keeps a single angular
sense on every layer. Different layer-pairs use different fractional turns.

Run inside the KiCad PCB editor Python console:
    exec(open(r"C:/path/create_cw_ccw_6layer_center_bottom_vias.py", encoding="utf-8").read())

IMPORTANT:
- Six copper layers must be configured in Board Setup.
- Net /COIL+ must exist (adjust NET_NAME).
- This ADDS copper. Remove old generated coils/vias first, or use a clean PCB.
- F.Cu terminals are short, unpadded stubs; connect them to real pads.
- The program has no access to your *actual* Edge.Cuts and existing footprint
  geometries for collision preflight. Check all via-to-edge distances and full
  KiCad DRC before fabrication.
- Via 0.32/0.15 mm through 6 layers needs explicit fabricator approval.
"""
import math
import pcbnew

# -----------------------------------------------------------------------------
# Geometric and manufacturing parameters (mm)
# -----------------------------------------------------------------------------
NUM_LAYERS = 6
NET_NAME = "/COIL+"
LEFT_CX = 90.0
CY = 100.0
CENTER_DISTANCE = 6.0
TRACE = 0.16
GAP = 0.10
PITCH_ALLOWANCE = 0.001
PITCH = TRACE + GAP + PITCH_ALLOWANCE
R_OUT = 2.84              # outer spiral TRACE CENTERLINE
STEP_DEG = 2.0
VIA_DIAMETER = 0.32
VIA_DRILL = 0.15
CORE_VIA_RADIUS = 0.27
OUTER_VIA_RADIUS = 3.24
TERMINAL_RADIUS = 2.857  # short F.Cu lead, avoids terminal-to-terminal short
EXTRA_CLEARANCE = 0.015

# OUTER BOUNDARIES for the left coil in traversal order (degrees).
# Original: [0, 120, 240, 360], which puts lower vias on the outside.
# Changed:  [0, 120, 315, 360], which places the lower transition vias
# at +/-45 degrees towards the center-bottom wedge.
# The right coil is the mirror of the left and traverses its layers backwards.
LEFT_BOUNDARIES_DEG = [0.0, 120.0, 315.0, 360.0]

# -----------------------------------------------------------------------------
# Utility
# -----------------------------------------------------------------------------
def point(cx, radius, angle):
    theta = math.radians(angle)
    return (cx + radius * math.cos(theta), CY - radius * math.sin(theta))


def euclidean(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def p2i(q):
    return pcbnew.VECTOR2I(pcbnew.FromMM(q[0]), pcbnew.FromMM(q[1]))


def angular_close(a, b, tolerance=1e-7):
    return abs((a - b + 180.0) % 360.0 - 180.0) < tolerance


# -----------------------------------------------------------------------------
# Geometry computations and PRE-FLIGHT checks (no board modification)
# -----------------------------------------------------------------------------
board = pcbnew.GetBoard()
if board is None:
    raise RuntimeError("Open a PCB first.")
if board.GetCopperLayerCount() != NUM_LAYERS:
    raise RuntimeError("Board must be 6 copper layers, currently %d." % board.GetCopperLayerCount())
net = board.FindNet(NET_NAME)
if net is None:
    raise RuntimeError("Create PCB net %r first." % NET_NAME)
if not (0 < VIA_DRILL < VIA_DIAMETER and 0 < TRACE and 0 < GAP and 0 < STEP_DEG <= 5):
    raise ValueError("Invalid trace, gap, step, or via sizes")
if len(LEFT_BOUNDARIES_DEG) != 4 or LEFT_BOUNDARIES_DEG[0] != 0 or LEFT_BOUNDARIES_DEG[-1] != 360:
    raise ValueError("LEFT_BOUNDARIES_DEG must have 4 entries starting at 0, ending at 360")
if not all(a < b for a,b in zip(LEFT_BOUNDARIES_DEG,LEFT_BOUNDARIES_DEG[1:])):
    raise ValueError("Outer boundary angles must increase strictly")
if TERMINAL_RADIUS < R_OUT:
    raise ValueError("Terminal tip radius cannot be inside the coil")
min_required_gap = GAP + EXTRA_CLEARANCE
# all same-layer spiral copper disks remain separated
coil_disk_copper_gap = CENTER_DISTANCE - 2 * R_OUT - TRACE
if coil_disk_copper_gap < min_required_gap:
    raise ValueError("Two coils too close: minimum conservative spiral gap %.3f mm" % coil_disk_copper_gap)
terminal_copper_gap = CENTER_DISTANCE - 2 * TERMINAL_RADIUS - TRACE
if terminal_copper_gap < min_required_gap:
    raise ValueError("Top terminal tips too close: %.3f mm" % terminal_copper_gap)
if OUTER_VIA_RADIUS - R_OUT - (VIA_DIAMETER + TRACE)/2 < min_required_gap:
    raise ValueError("Outer via radius gives insufficient clearance to adjacent spiral turns")

# Pair turns. Both layers in a pair receive the same turns, but pairs may
# have different fractional turn counts. In each pair, two same-direction
# spirals connect successive boundary angles with one core through-via.
# The choice of the smallest turn count >=8 consistent with each phase
# preserves >=8 turns/layer and gives 50.000 turns per coil in total.
PAIR_TURNS = []
for outer_a, outer_b in zip(LEFT_BOUNDARIES_DEG, LEFT_BOUNDARIES_DEG[1:]):
    delta = outer_b - outer_a
    # B[k+1] = B[k] - 720*T mod 360, with T = 8 + frac and delta 0..360.
    PAIR_TURNS.append(8.0 + (360.0 - delta)/720.0)
# Choose how many turns are allocated before and after each core via.
# Equal splits place the pair-0 core via too close to pair-2's through-via.
# A 37.5-degree phase offset in pair 0 keeps core via phases exactly
# 120 degrees apart while preserving each pair's TOTAL turns.
PAIR_FIRST_TURNS = [8.0 + 82.5/360.0, PAIR_TURNS[1], PAIR_TURNS[2]]
PAIR_SECOND_TURNS = [2.0*PAIR_TURNS[0]-PAIR_FIRST_TURNS[0],
                     PAIR_TURNS[1], PAIR_TURNS[2]]
PAIR_LAYER_TURNS = [(a,b) for a,b in zip(PAIR_FIRST_TURNS,PAIR_SECOND_TURNS)]
PAIR_INNER_R = [(R_OUT - PITCH*a, R_OUT - PITCH*b) for a,b in PAIR_LAYER_TURNS]
TOTAL_TURNS_PER_COIL = sum(a+b for a,b in PAIR_LAYER_TURNS)
if abs(TOTAL_TURNS_PER_COIL - 50.0) > 1e-8:
    raise ValueError("Phase selection does not produce 50 turns/coil")
if min(PAIR_TURNS) < 1:
    raise ValueError("Insufficient coil turns")
for k, inner_pair_r in enumerate(PAIR_INNER_R):
    for inner_r in inner_pair_r:
        clearance = inner_r - CORE_VIA_RADIUS - (VIA_DIAMETER + TRACE)/2
        if clearance + 1e-9 < min_required_gap:
            raise ValueError("Inner via too near spiral on pair %d (%.4f mm)" % (k, clearance))

layers = [pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu,
          pcbnew.In3_Cu, pcbnew.In4_Cu, pcbnew.B_Cu]
centers = {"L": LEFT_CX, "R": LEFT_CX + CENTER_DISTANCE}


def boundary(side,j):
    phase = LEFT_BOUNDARIES_DEG[j]
    return phase if side == "L" else 180.0 - phase


def index_of_pair(side,k):
    return k if side == "L" else 2-k


def inner_phase(side,k):
    j = index_of_pair(side,k)
    if side == "L":
        return boundary(side,j) - 360.0*PAIR_FIRST_TURNS[j]
    return boundary(side,j) + 360.0*PAIR_FIRST_TURNS[j]


def layer_turns(side,li):
    k=li//2
    j=index_of_pair(side,k)
    # Left: even->odd current flow; right: odd->even current flow.
    first = (li%2==0) if side=="L" else (li%2==1)
    return PAIR_LAYER_TURNS[j][0 if first else 1]


def layer_inner_radius(side,li):
    return R_OUT - PITCH*layer_turns(side,li)

# All via locations, including each through-via spanning all 6 layers.
via_locations = []
for side,cx in centers.items():
    for k in range(3):
        via_locations.append((side,"inner",k,point(cx,CORE_VIA_RADIUS,inner_phase(side,k))))
    for k in (1,2):
        bidx = k if side == "L" else 3-k
        via_locations.append((side,"outer",k,point(cx,OUTER_VIA_RADIUS,boundary(side,bidx))))

# Avoid unintentional pad overlaps, including different coil via nets (even
# when KiCad sees one net /COIL+, shorts could bypass the winding turns).
min_via_center_spacing = VIA_DIAMETER + min_required_gap
for i,a in enumerate(via_locations):
    for b in via_locations[i+1:]:
        d = euclidean(a[-1],b[-1])
        if d < min_via_center_spacing - 1e-8:
            raise ValueError("Through vias overlap: %s, %s (%.3f mm)" % (a[:3],b[:3],d))

# Confirm lower vias lie inside the pair's horizontal center gap (not outside).
lower_left = point(LEFT_CX,OUTER_VIA_RADIUS,LEFT_BOUNDARIES_DEG[2])
lower_right = point(LEFT_CX+CENTER_DISTANCE,OUTER_VIA_RADIUS,180-LEFT_BOUNDARIES_DEG[2])
if not (LEFT_CX < lower_left[0] < lower_right[0] < LEFT_CX + CENTER_DISTANCE):
    raise ValueError("Lower transition vias not in the center gap")
if not (lower_left[1] > CY and lower_right[1] > CY):
    raise ValueError("Lower transition vias not below the centers")

# -----------------------------------------------------------------------------
# Copper generation
# -----------------------------------------------------------------------------
def track(start,end,layer):
    if euclidean(start,end) < 1e-9:
        return
    t = pcbnew.PCB_TRACK(board)
    t.SetStart(p2i(start))
    t.SetEnd(p2i(end))
    t.SetWidth(pcbnew.FromMM(TRACE))
    t.SetLayer(layer)
    t.SetNet(net)
    board.Add(t)


def plated_via(where):
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(p2i(where))
    v.SetViaType(pcbnew.VIATYPE_THROUGH)
    v.SetLayerPair(pcbnew.F_Cu,pcbnew.B_Cu)
    v.SetWidth(pcbnew.FromMM(VIA_DIAMETER))
    v.SetDrill(pcbnew.FromMM(VIA_DRILL))
    v.SetNet(net)
    board.Add(v)


def spiral(cx,layer,sign,from_outside,outer_angle,inner_angle,turn_count,inner_r):
    n_steps = math.ceil(360.0*turn_count/STEP_DEG)
    pts=[]
    start_angle = outer_angle if from_outside else inner_angle
    for j in range(n_steps+1):
        t=turn_count*j/n_steps
        radius = R_OUT-PITCH*t if from_outside else inner_r+PITCH*t
        pts.append(point(cx,radius,start_angle+sign*360*t))
    for a,b in zip(pts,pts[1:]):
        track(a,b,layer)
    inner=pts[-1] if from_outside else pts[0]
    outer=pts[0] if from_outside else pts[-1]
    if euclidean(inner,point(cx,inner_r,inner_angle))>1e-6 or euclidean(outer,point(cx,R_OUT,outer_angle))>1e-6:
        raise RuntimeError("Unexpected spiral phase mismatch")
    return {"inner":inner,"outer":outer}


coil_endpoints={}
for side,cx in centers.items():
    sign=-1 if side=="L" else 1
    for li,layer in enumerate(layers):
        k=li//2
        from_outside=(li%2==0) if side=="L" else (li%2==1)
        if side=="L":
            bidx=k if li%2==0 else k+1
        else:
            bidx=(2-k) if li%2==1 else (3-k)
        outer_angle=boundary(side,bidx)
        coil_endpoints[(side,li)]=spiral(
            cx,layer,sign,from_outside,outer_angle,inner_phase(side,k),
            layer_turns(side,li),layer_inner_radius(side,li)
        )

# Layer pairs join at inner vias.
for side,cx in centers.items():
    for k in range(3):
        a,b=2*k,2*k+1
        pv=point(cx,CORE_VIA_RADIUS,inner_phase(side,k))
        plated_via(pv)
        track(coil_endpoints[side,a]["inner"],pv,layers[a])
        track(coil_endpoints[side,b]["inner"],pv,layers[b])

# Pair-to-pair transitions. These use the upper or central lower outer via.
for side,cx in centers.items():
    for k in (1,2):
        a,b=2*k-1,2*k
        j=k if side=="L" else 3-k
        pv=point(cx,OUTER_VIA_RADIUS,boundary(side,j))
        plated_via(pv)
        track(coil_endpoints[side,a]["outer"],pv,layers[a])
        track(coil_endpoints[side,b]["outer"],pv,layers[b])

# One B.Cu series bridge, from left to right (never both F.Cu terminals).
bridge_l=coil_endpoints["L",5]["outer"]
bridge_r=coil_endpoints["R",5]["outer"]
if abs(bridge_l[1]-bridge_r[1])>1e-7:
    raise RuntimeError("Bottom bridge endpoints not level")
track(bridge_l,bridge_r,pcbnew.B_Cu)

# F.Cu terminals must be connected to real PCB pads by the designer.
input_tip=point(LEFT_CX,TERMINAL_RADIUS,boundary("L",0))
output_tip=point(LEFT_CX+CENTER_DISTANCE,TERMINAL_RADIUS,boundary("R",3))
track(coil_endpoints["L",0]["outer"],input_tip,pcbnew.F_Cu)
track(coil_endpoints["R",0]["outer"],output_tip,pcbnew.F_Cu)

pcbnew.Refresh()
print("\n"+"="*64)
print("6-LAYER CW/CCW COILS: LOWER OUTER VIAS MOVED INTO MIDDLE GAP")
print("Center distance: %.3f mm; turns per coil: %.3f"%(CENTER_DISTANCE,TOTAL_TURNS_PER_COIL))
print("Turns/layer, left F.Cu to B.Cu:", [round(layer_turns("L",i),6) for i in range(6)])
print("Turns/layer, right F.Cu to B.Cu:", [round(layer_turns("R",i),6) for i in range(6)])
print("Inner radii (left layer pairs):", [[round(v,4) for v in pair] for pair in PAIR_INNER_R])
print("Lower LEFT outer via:  (%.4f, %.4f) mm"%lower_left)
print("Lower RIGHT outer via: (%.4f, %.4f) mm"%lower_right)
print("Lower vias center-center spacing: %.4f mm"%euclidean(lower_left,lower_right))
print("Coil disk conservative copper gap: %.4f mm"%coil_disk_copper_gap)
print("F.Cu terminal conservative copper gap: %.4f mm"%terminal_copper_gap)
print("Left CW -> bottom series bridge -> right CCW")
print("NOTICE: old copper is NOT removed; check actual board Edge.Cuts and full DRC")
print("="*64)
