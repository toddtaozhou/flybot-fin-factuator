"""Generate a 6-layer, all-2-oz, series CW/CCW PCB coil pair in KiCad.

Design target: PCBWay Advanced / standard-process rules for 2 oz finished
copper *on all six layers*.  The dimensions are deliberately based on the
2-oz-specific tables, not the generic 0.10-mm minimum.  Submission to PCBWay
for stackup + dense-spiral DFM approval is still required.

KiCad PCB Editor > Tools > Scripting Console:
    exec(open(r'C:/path/pcbway_6layer_2oz_cw_ccw_final.py', encoding='utf-8').read())

Standalone geometry summary (does NOT create a board):
    python pcbway_6layer_2oz_cw_ccw_final.py

Current: left CW viewed from top -> bottom bridge -> right CCW viewed from top.
The windings are strictly one copper series path: 26 turns/coil, 52 turns/pair.
This generator ADDS copper; delete earlier coil copper first. It does not
make or alter Edge.Cuts and cannot certify board-outline/footprint clearance.
Place two real driver terminal pads and connect them yourself. Consult the
README before fabrication.

PCBWay reference: https://www.pcbway.com/capabilities.html
As of Oct 2026, its 70-um copper NORMAL trace/space: outer >=7/8 mil,
inner >=6/8 mil; via annular ring >=7 mil on 2-oz outer; 0.20-mm drills
are listed for <=1.6-mm boards. These minima are not a promise that every
concentrated spiral or 2-oz thin-board stackup will be accepted. DFM review.
"""
import math

# -----------------------------------------------------------------------------
# EDIT ONLY THIS BLOCK unless changing the layer-transition topology.
# -----------------------------------------------------------------------------
NUM_LAYERS = 6
NET_NAME = '/COIL+'       # Must already exist on your actual PCB
LEFT_CX = 90.0           # mm; same as prior generators
CY = 100.0
CENTER_DISTANCE = 6.0
TRACE_MM = 0.18          # 7.09 mil; passes PCBWay 2-oz OUTER 7 mil normal
CLEARANCE_MM = 0.21      # 8.27 mil; passes 2-oz OUTER/INNER 8 mil normal
PITCH_GUARD_MM = 0.005 # Prevent polyline approximation eroding clearance
OUTER_TRACE_RADIUS_MM = 2.80  # trace centerline, NOT board outer radius
INNER_VIA_RING_RADIUS_MM = 0.455
OUTER_VIA_RING_RADIUS_MM = 3.40
VIA_DIAMETER_MM = 0.56  # 0.18-mm annular ring with 0.20 drill
VIA_DRILL_MM = 0.20
TERMINAL_RADIUS_MM = 2.95 # F.Cu endpoints separated with no mutual short
SEGMENT_STEP_DEG = 2.0 # 2-deg approximation; validated with 0.005-mm guard
# Keep upper vias outboard and lower vias in the *central lower* web.
LEFT_BOUNDARIES_DEG = (20.0, 120.0, 318.0, 380.0)
# Deliberately space three through-hole core via angles by 120deg.
LEFT_CORE_PHASES_DEG = (-81.0, 39.0, 159.0)
# This is a *request to the fabricator*, not encoded in pcbnew track objects.
REQUIRED_FINISHED_COPPER_UM = 70
SUGGESTED_FINISHED_BOARD_THICKNESS_MM = 1.0 # request PCBWay confirmation
# When true, fail rather than putting a new coil over any existing tracks/vias
# whose centerpoints lie within one of the two winding disks.
BLOCK_IF_PRIOR_COIL_COPPER = True

PITCH_MM = TRACE_MM + CLEARANCE_MM + PITCH_GUARD_MM
PAIR_COUNT = NUM_LAYERS // 2


def point(cx, radius, deg):
    a = math.radians(deg)
    return (cx + radius * math.cos(a), CY - radius * math.sin(a))


def distance(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def shortest_phase_error(a, b):
    return abs((a - b + 180) % 360 - 180)


def build_geometry():
    """Return pure-Python segments/vias, with ALL checks before board change."""
    assert NUM_LAYERS == 6
    if not (0 < VIA_DRILL_MM < VIA_DIAMETER_MM and SEGMENT_STEP_DEG <= 2):
        raise ValueError('Invalid via or trace approximation size')
    if TRACE_MM < 0.1778 or CLEARANCE_MM < 0.2032:
        raise ValueError('Below PCBWay 2oz normal outer trace/spacing capability')
    if (VIA_DIAMETER_MM - VIA_DRILL_MM)/2 < 0.1778:
        raise ValueError('Via annular ring < 7mil on outer 2oz copper')
    if SUGGESTED_FINISHED_BOARD_THICKNESS_MM / VIA_DRILL_MM > 8:
        raise ValueError('Through drill aspect ratio too high for standard processing')
    if abs(LEFT_BOUNDARIES_DEG[-1] - LEFT_BOUNDARIES_DEG[0] - 360)>1e-8:
        raise ValueError('First/last outer boundary must differ by 360 degrees')
    if any(b <= a for a,b in zip(LEFT_BOUNDARIES_DEG,LEFT_BOUNDARIES_DEG[1:])):
        raise ValueError('Boundary phases must increase')
    if CENTER_DISTANCE - 2*OUTER_TRACE_RADIUS_MM - TRACE_MM < CLEARANCE_MM:
        raise ValueError('Opposing spiral copper too close')
    outer_via_clearance = (OUTER_VIA_RING_RADIUS_MM - OUTER_TRACE_RADIUS_MM
                           - (VIA_DIAMETER_MM + TRACE_MM)/2)
    if outer_via_clearance < CLEARANCE_MM:
        raise ValueError('Outer via too close to unrelated spiral segments')
    top_terminal_gap = (CENTER_DISTANCE - 2*TERMINAL_RADIUS_MM
                        *math.cos(math.radians(LEFT_BOUNDARIES_DEG[0])) - TRACE_MM)
    if top_terminal_gap < CLEARANCE_MM:
        raise ValueError('Top terminal leads too close')
    if TERMINAL_RADIUS_MM < OUTER_TRACE_RADIUS_MM:
        raise ValueError('Top terminals need to project outside spirals')

    # Layer pairs, in order of CURRENT across the LEFT coil.
    # By combining an OUT->IN and an IN->OUT spiral in each pair,
    # the two outer boundaries obey delta = 360 - 720 * frac.
    pair_turns = []
    for a,b in zip(LEFT_BOUNDARIES_DEG,LEFT_BOUNDARIES_DEG[1:]):
        pair_turns.append(4.0 + (360.0 - (b-a))/720.0)
    pair_first_turns = []
    pair_second_turns = []
    inner_radii = []
    for k in range(3):
        phase_diff = (LEFT_BOUNDARIES_DEG[k] - LEFT_CORE_PHASES_DEG[k])%360
        first = 4.0 + phase_diff/360.0
        second = 2.0*pair_turns[k] - first
        if second < 1 or first < 1:
            raise ValueError('Illegal signed winding count')
        pair_first_turns.append(first)
        pair_second_turns.append(second)
        inner_radii.append((OUTER_TRACE_RADIUS_MM-PITCH_MM*first,
                            OUTER_TRACE_RADIUS_MM-PITCH_MM*second))
    total_turns = sum(a+b for a,b in zip(pair_first_turns,pair_second_turns))
    if abs(total_turns-26.0)>1e-6:
        raise ValueError('Topology no longer makes 26 turns per coil')

    core_clear = min(min(p) for p in inner_radii) - INNER_VIA_RING_RADIUS_MM - (VIA_DIAMETER_MM+TRACE_MM)/2
    if core_clear < CLEARANCE_MM:
        raise ValueError('Core via/spiral gap %.4f < %.4f mm' % (core_clear, CLEARANCE_MM))

    centers={'L':LEFT_CX, 'R':LEFT_CX+CENTER_DISTANCE}
    def boundary(side,k):
        a=LEFT_BOUNDARIES_DEG[k]
        return a if side=='L' else 180.0-a
    def pair_j(side,k):
        return k if side=='L' else 2-k
    def inner_phase(side,k):
        a=LEFT_CORE_PHASES_DEG[pair_j(side,k)]
        return a if side=='L' else 180.0-a

    segments=[]   # (layer INDEX, start, end, kind, side, k)
    vias=[]       # (point, kind, side, pair index)
    endpoints={}
    layer_turns={}
    total_copper_lengths=[0.0]*NUM_LAYERS
    def seg(li,a,b,kind,side,k):
        length=distance(a,b)
        if length>1e-9:
            segments.append((li,a,b,kind,side,k))
            total_copper_lengths[li] += length

    for side,cx in centers.items():
        sign=-1 if side=='L' else +1
        for li in range(NUM_LAYERS):
            k=li//2
            j=pair_j(side,k)
            travels_from_outside = (li%2==0) if side=='L' else (li%2==1)
            travels_first=travels_from_outside
            turns=(pair_first_turns[j] if travels_first else pair_second_turns[j])
            layer_turns[side,li]=turns
            inner_radius=OUTER_TRACE_RADIUS_MM-PITCH_MM*turns
            outer_bidx=(j if travels_from_outside else j+1)
            phase_o=boundary(side,outer_bidx)
            phase_i=inner_phase(side,k)
            first_angle=phase_o if travels_from_outside else phase_i
            count=math.ceil(turns*360.0/SEGMENT_STEP_DEG)
            pts=[]
            for t in range(count+1):
                q=t/count
                r=(OUTER_TRACE_RADIUS_MM-PITCH_MM*turns*q
                   if travels_from_outside else inner_radius+PITCH_MM*turns*q)
                theta=first_angle + sign*360.0*turns*q
                pts.append(point(cx,r,theta))
            for a,b in zip(pts,pts[1:]):
                seg(li,a,b,'spiral',side,k)
            inner_pt=(pts[-1] if travels_from_outside else pts[0])
            outer_pt=(pts[0] if travels_from_outside else pts[-1])
            if distance(inner_pt,point(cx,inner_radius,phase_i))>1e-6:
                raise ValueError('Inner geometry phase mismatch (%s L%d)'%(side,li))
            if distance(outer_pt,point(cx,OUTER_TRACE_RADIUS_MM,phase_o))>1e-6:
                raise ValueError('Outer geometry phase mismatch (%s L%d)'%(side,li))
            endpoints[side,li]={'inner':inner_pt,'outer':outer_pt}

    for side,cx in centers.items():
        for k in range(3):
            li=2*k
            pv=point(cx,INNER_VIA_RING_RADIUS_MM,inner_phase(side,k))
            vias.append((pv,'inner',side,k))
            for j in (li,li+1):
                seg(j,endpoints[side,j]['inner'],pv,'inner-lead',side,k)
        for k in (1,2):
            bidx=(k if side=='L' else 3-k)
            pv=point(cx,OUTER_VIA_RING_RADIUS_MM,boundary(side,bidx))
            vias.append((pv,'outer',side,k))
            for li in (2*k-1,2*k):
                seg(li,endpoints[side,li]['outer'],pv,'outer-lead',side,k)

    # A single bottom-layer bridge connects the two coils in series.
    bl=endpoints['L',NUM_LAYERS-1]['outer']
    br=endpoints['R',NUM_LAYERS-1]['outer']
    if abs(bl[1]-br[1])>1e-6:
        raise ValueError('Bottom bridge not horizontal')
    seg(NUM_LAYERS-1,bl,br,'bridge','B',0)
    # Terminals are exposed short traces, NOT through-vias: any through-via
    # added here would shunt the bottom-layer bridge and short winding turns.
    input_pt=point(LEFT_CX,TERMINAL_RADIUS_MM,boundary('L',0))
    output_pt=point(LEFT_CX+CENTER_DISTANCE,TERMINAL_RADIUS_MM,boundary('R',3))
    seg(0,endpoints['L',0]['outer'],input_pt,'terminal','L',0)
    seg(0,endpoints['R',0]['outer'],output_pt,'terminal','R',2)

    # ANY through-vias carry metal pads on ALL six layers. Check all ten
    # pair-wise distances, regardless of their nominal layer-transition role.
    for i,va in enumerate(vias):
        for vb in vias[i+1:]:
            if distance(va[0],vb[0]) < VIA_DIAMETER_MM+CLEARANCE_MM-1e-8:
                raise ValueError('Two physical PTH pads too close %s, %s'%(va[1:],vb[1:]))
    inner_left=[v[0] for v in vias if v[1]=='inner' and v[2]=='L']
    core_pitch=min(distance(a,b) for i,a in enumerate(inner_left) for b in inner_left[i+1:])
    bottom_l=next(v[0] for v in vias if v[1]=='outer' and v[2]=='L' and v[3]==2)
    bottom_r=next(v[0] for v in vias if v[1]=='outer' and v[2]=='R' and v[3]==1)
    if not (LEFT_CX < bottom_l[0] < bottom_r[0] < LEFT_CX+CENTER_DISTANCE
            and bottom_l[1]>CY and bottom_r[1]>CY):
        raise ValueError('Lower outer vias not inside the central-bottom gap')
    return {'segments':segments, 'vias':vias, 'turns':total_turns,
            'layer_turns':layer_turns, 'total_lengths':total_copper_lengths,
            'inner_radii':inner_radii, 'core_clearance':core_clear,
            'outer_via_clearance':outer_via_clearance,
            'core_via_center_spacing':core_pitch,
            'lower_outer_center_spacing':distance(bottom_l,bottom_r),
            'input_tip':input_pt, 'output_tip':output_pt,
            'terminal_gap':top_terminal_gap,
            'spiral_disk_gap':CENTER_DISTANCE-2*OUTER_TRACE_RADIUS_MM-TRACE_MM}


def describe(g):
    print('\n=== PCBWAY 6L / 2-OZ EACH LAYER / CW-CCW COIL PAIR ===')
    print('Turns: %.3f per coil, %.3f both coils in SERIES'%(g['turns'],2*g['turns']))
    print('Turns by layer LEFT:',[round(g['layer_turns']['L',i],4) for i in range(6)])
    print('Turns by layer RIGHT:',[round(g['layer_turns']['R',i],4) for i in range(6)])
    print('Trace %.3f / nominal gap %.3f / path pitch %.3f mm'%(TRACE_MM,CLEARANCE_MM,PITCH_MM))
    print('Vias %.3f pad / %.3f drill; annulus %.3f mm'%(VIA_DIAMETER_MM,VIA_DRILL_MM,(VIA_DIAMETER_MM-VIA_DRILL_MM)/2))
    print('Min radial gaps: core %.4f; outer vias %.4f; coil disks %.4f mm'%
          (g['core_clearance'],g['outer_via_clearance'],g['spiral_disk_gap']))
    print('Via center pitch: core %.4f; lower opposing outer %.4f mm'%
          (g['core_via_center_spacing'],g['lower_outer_center_spacing']))
    print('Terminal tip copper gap %.4f mm'%g['terminal_gap'])
    lengths=g['total_lengths']
    print('Copper path length: %.1f mm per left+right pair'%(sum(lengths)))
    # 1.724e-8 Ohm*m => 0.01724 Ohm*mm2/m, L in mm => 1.724e-5 Ohm*mm2/mm
    R_est=sum(L*1.724e-5/(TRACE_MM*(REQUIRED_FINISHED_COPPER_UM/1000)) for L in lengths)
    print('Estimated 20 C DC pair R ~%.3f ohm (traces only, not vias/etch)'%R_est)
    print('Ideal P @ 0.2 / 0.3 / 0.5 A: %.0f / %.0f / %.0f mW'%
          tuple(1000*R_est*i*i for i in (0.2,0.3,0.5)))
    print('F.Cu IN %.4f,%.4f; OUT %.4f,%.4f (connect to real surface pads)'%
          (g['input_tip']+g['output_tip']))
    print('WARNING: PCBWay 2-oz six-layer stackup & concentrated-coil DFM require written acceptance.')
    print('WARNING: actual board EDGE.Cuts and existing tracks/footprints need DRC.')


def emit_kicad(g,pcbnew):
    board=pcbnew.GetBoard()
    if board is None: raise RuntimeError('Open a PCB in KiCad first')
    if board.GetCopperLayerCount()!=NUM_LAYERS:
        raise RuntimeError('Set KiCad copper stack to 6 layers before running')
    net=board.FindNet(NET_NAME)
    if net is None:
        raise RuntimeError('Net %s does not exist; edit NET_NAME first' % NET_NAME)
    if BLOCK_IF_PRIOR_COIL_COPPER:
        # Conservative: do not overwrite any current copper track/via in
        # a radius of the coil winding. Other board objects require DRC.
        for item in board.GetTracks():
            try:
                pos=item.GetPosition()
                x=pcbnew.ToMM(pos.x); y=pcbnew.ToMM(pos.y)
            except Exception:
                continue
            if min(math.hypot(x-cx,y-CY) for cx in (LEFT_CX, LEFT_CX+CENTER_DISTANCE)) < OUTER_TRACE_RADIUS_MM:
                raise RuntimeError('Copper already in coil winding area. Remove OLD coil tracks/vias first or adjust centers.')
    layers=(pcbnew.F_Cu,pcbnew.In1_Cu,pcbnew.In2_Cu,
            pcbnew.In3_Cu,pcbnew.In4_Cu,pcbnew.B_Cu)
    def pos(p):
        return pcbnew.VECTOR2I(pcbnew.FromMM(p[0]),pcbnew.FromMM(p[1]))
    # All preflight checks above finish before any board edits.
    for li,a,b,kind,side,k in g['segments']:
        t=pcbnew.PCB_TRACK(board)
        t.SetStart(pos(a)); t.SetEnd(pos(b))
        t.SetWidth(pcbnew.FromMM(TRACE_MM)); t.SetLayer(layers[li])
        t.SetNet(net)
        board.Add(t)
    for pv,kind,side,k in g['vias']:
        v=pcbnew.PCB_VIA(board)
        v.SetPosition(pos(pv))
        v.SetViaType(pcbnew.VIATYPE_THROUGH)
        v.SetLayerPair(pcbnew.F_Cu,pcbnew.B_Cu)
        v.SetWidth(pcbnew.FromMM(VIA_DIAMETER_MM))
        v.SetDrill(pcbnew.FromMM(VIA_DRILL_MM))
        v.SetNet(net)
        board.Add(v)
    pcbnew.Refresh()
    print('ADDED %d segments and %d PTH vias. Save PCB; run DRC.'% (len(g['segments']),len(g['vias'])))


def main():
    geometry=build_geometry()
    describe(geometry)
    try:
        import pcbnew
    except ImportError:
        print('Standalone preview only: pcbnew is unavailable. In KiCad, run with exec(open(...).read()).')
        return
    emit_kicad(geometry,pcbnew)

main()
