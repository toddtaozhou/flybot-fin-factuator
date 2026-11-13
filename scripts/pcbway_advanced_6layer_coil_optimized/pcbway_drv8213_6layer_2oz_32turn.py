"""PCBWay ADVANCED copper 6-layer CW/CCW fin actuator coils.

DEFAULT FOR DRV8213RTER: 2 oz FINISHED Cu on ALL SIX layers, 32 turns PER COIL,
 0.200 mm trace, 0.132 mm copper gap. Both coils in series (64 turns).

Alternative profiles at the top: TWO_OZ_32, MIXED_26, MIXED_32.
 "Best" is constrained to the original 6-mm, two-spiral, 10-PTH-via topology;
 it is NOT a measured global magnetic or force-per-watt optimum.

Run as standalone geometry summary:
   python pcbway_advanced_coil_6layer_optimized.py

KiCad PCB Editor (Tools -> Scripting Console):
   exec(open(r"C:\\path\\pcbway_advanced_coil_6layer_optimized.py", encoding="utf-8").read())

SAFE USE:
* Open six-layer PCB, set NET_NAME to a net that exists.
* SAVE A COPY. Remove previously generated coil copper before running.
* Script ADDS geometry; never silently removes existing copper.
* Script does NOT set actual layer copper thickness, stackup, EDGE.Cuts,
  or pads. Request advanced fabrication and preapprove all six-layer copper.
* Execute KiCad DRC and ask PCBWay for DFM acceptance before manufacturing.
* All 10 vias are plated THROUGH every layer; inter-turn shorts are checked
  geometrically but not independently cleared by same-net KiCad DRC.

PCBWay: https://www.pcbway.com/advanced-pcb-capabilities.html
"""
import math

# -----------------------------------------------------------------------------
# SELECT ONLY ONE PROFILE. Each profile preserves 6 mm coil spacing.
# Manufacturer quoted capabilities from user: MIXED 4mil; TWO_OZ 5mil.
# Units here are millimeters. Gaps exceed nominal mil limits by a few microns.
# -----------------------------------------------------------------------------
PROFILE = "TWO_OZ_32"        # selected for DRV8213RTER total coil + H-bridge power
# PROFILE = "TWO_OZ_26"      # lower coil-only loss and wider trace
# PROFILE = "MIXED_26"       # 1oz outer, 1.5oz inner (alternative fab)
# PROFILE = "MIXED_32"

NUM_LAYERS = 6
NET_NAME = '/COIL+'       # EXISTING KiCad net name; edit to suit PCB
LEFT_CX = 90.0
CY = 100.0
CENTER_DISTANCE = 6.0
SEGMENT_STEP_DEG = 2.0
PITCH_GUARD_MM = 0.005
VIA_DRILL_MM = 0.20
SUGGESTED_FINISHED_BOARD_THICKNESS_MM = 1.0
BLOCK_IF_PRIOR_COIL_COPPER = True

# A 0.20mm finished hole with 0.15/0.18mm annulus is possible in advanced
# manufacturing only when PCBWay accepts the actual finished stackup.
PROFILES = {
    'TWO_OZ_26': dict(base=4, trace=.270, gap=.132, outer=2.790,
                      core=.420, pad=.560, min_annulus=.180,
                      copper_um=(70,70,70,70,70,70)),
    'TWO_OZ_32': dict(base=5, trace=.200, gap=.132, outer=2.800,
                      core=.420, pad=.560, min_annulus=.180,
                      copper_um=(70,70,70,70,70,70)),
    'MIXED_26': dict(base=4, trace=.300, gap=.110, outer=2.770,
                     core=.390, pad=.500, min_annulus=.150,
                     copper_um=(35,50,50,50,50,35)),
    'MIXED_32': dict(base=5, trace=.240, gap=.110, outer=2.810,
                     core=.390, pad=.500, min_annulus=.150,
                     copper_um=(35,50,50,50,50,35)),
}
if PROFILE not in PROFILES:
    raise ValueError('Unknown PROFILE %s' % PROFILE)
P = PROFILES[PROFILE]
BASE_TURNS_PER_LAYER = P['base']
TRACE_MM = P['trace']
CLEARANCE_MM = P['gap']
OUTER_TRACE_RADIUS_MM = P['outer']
INNER_VIA_RING_RADIUS_MM = P['core']
VIA_DIAMETER_MM = P['pad']
REQUIRED_FINISHED_COPPER_UM = P['copper_um']
MIN_ANNULUS_MM = P['min_annulus']
MIN_TRACE_MM = .127 if PROFILE.startswith('TWO_OZ') else .1016
MIN_SPACING_MM = .127 if PROFILE.startswith('TWO_OZ') else .1016
PITCH_MM = TRACE_MM + CLEARANCE_MM + PITCH_GUARD_MM
OUTER_VIA_RING_RADIUS_MM = (OUTER_TRACE_RADIUS_MM +
    (VIA_DIAMETER_MM + TRACE_MM)/2 + CLEARANCE_MM + .020)
TERMINAL_RADIUS_MM = OUTER_TRACE_RADIUS_MM + .150
PAIR_COUNT = NUM_LAYERS//2

# Keep upper transition vias above/outboard, and TWO lower transition vias in
# the board's central lower web. The user's actual outline must be DRC checked.
LEFT_BOUNDARIES_DEG = (20.0, 120.0, 318.0, 380.0)
LEFT_CORE_PHASES_DEG = (-81.0, 39.0, 159.0)


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
    if TRACE_MM < MIN_TRACE_MM or CLEARANCE_MM < MIN_SPACING_MM:
        raise ValueError('Trace/spacing below selected advanced-process minimum')
    if (VIA_DIAMETER_MM - VIA_DRILL_MM)/2 < MIN_ANNULUS_MM-1e-9:
        raise ValueError('Via annular ring below required minimum')
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
    # Use BASE_TURNS_PER_LAYER plus fractional turns on each layer.
    # Balance low winding heat against driver and current requirements.
    # By combining an OUT->IN and an IN->OUT spiral in each pair,
    # the two outer boundaries obey delta = 360 - 720 * frac.
    pair_turns = []
    for a,b in zip(LEFT_BOUNDARIES_DEG,LEFT_BOUNDARIES_DEG[1:]):
        pair_turns.append(BASE_TURNS_PER_LAYER + (360.0 - (b-a))/720.0)
    pair_first_turns = []
    pair_second_turns = []
    inner_radii = []
    for k in range(3):
        phase_diff = (LEFT_BOUNDARIES_DEG[k] - LEFT_CORE_PHASES_DEG[k])%360
        first = BASE_TURNS_PER_LAYER + phase_diff/360.0
        second = 2.0*pair_turns[k] - first
        if second < 1 or first < 1:
            raise ValueError('Illegal signed winding count')
        pair_first_turns.append(first)
        pair_second_turns.append(second)
        inner_radii.append((OUTER_TRACE_RADIUS_MM-PITCH_MM*first,
                            OUTER_TRACE_RADIUS_MM-PITCH_MM*second))
    total_turns = sum(a+b for a,b in zip(pair_first_turns,pair_second_turns))
    if abs(total_turns-(6*BASE_TURNS_PER_LAYER+2))>1e-6:
        raise ValueError('Topology no longer makes the intended number of turns')

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
    # THROUGH VIA pads exist on ALL layers. Check every nonattached track
    # against each via regardless of which pair the via actually connects.
    # Connected end spiral is deliberately excluded, since its radial lead
    # connects that via on its pair of layers; radial separation is checked.
    def point_segment_dist(p,a,b):
        dx=b[0]-a[0]; dy=b[1]-a[1]
        den=dx*dx+dy*dy
        if den<=1e-18: return distance(p,a)
        u=max(0., min(1., ((p[0]-a[0])*dx+(p[1]-a[1])*dy)/den))
        return math.hypot(p[0]-a[0]-u*dx,p[1]-a[1]-u*dy)
    min_via_to_other_track = float('inf')
    for pv,kind,side,k in vias:
        attached_layers=((2*k,2*k+1) if kind=='inner'
                         else (2*k-1,2*k))
        for li,a,b,skind,sside,sk in segments:
            if sside==side and li in attached_layers and (
                 (kind=='inner' and skind in ('inner-lead','spiral')) or
                 (kind=='outer' and skind in ('outer-lead','spiral'))):
                continue
            # Quick radial bounding box reject avoids checking distant tracks.
            if (pv[0] < min(a[0],b[0])-(VIA_DIAMETER_MM+TRACE_MM)/2-CLEARANCE_MM-.03 or
                pv[0] > max(a[0],b[0])+(VIA_DIAMETER_MM+TRACE_MM)/2+CLEARANCE_MM+.03 or
                pv[1] < min(a[1],b[1])-(VIA_DIAMETER_MM+TRACE_MM)/2-CLEARANCE_MM-.03 or
                pv[1] > max(a[1],b[1])+(VIA_DIAMETER_MM+TRACE_MM)/2+CLEARANCE_MM+.03):
                continue
            clearance=point_segment_dist(pv,a,b)-(VIA_DIAMETER_MM+TRACE_MM)/2
            min_via_to_other_track=min(clearance,min_via_to_other_track)
            if clearance < CLEARANCE_MM-1e-7:
                raise ValueError('Through-via overlaps nonattached copper: %.4fmm'%clearance)

    return {'segments':segments, 'vias':vias, 'turns':total_turns,
            'layer_turns':layer_turns, 'total_lengths':total_copper_lengths,
            'inner_radii':inner_radii, 'core_clearance':core_clear,
            'min_nonattached_via_track_clearance':min_via_to_other_track,
            'outer_via_clearance':outer_via_clearance,
            'core_via_center_spacing':core_pitch,
            'lower_outer_center_spacing':distance(bottom_l,bottom_r),
            'input_tip':input_pt, 'output_tip':output_pt,
            'terminal_gap':top_terminal_gap,
            'spiral_disk_gap':CENTER_DISTANCE-2*OUTER_TRACE_RADIUS_MM-TRACE_MM}


def describe(g):
    print('\n=== PCBWAY ADVANCED 6L / %s / CW-CCW COIL PAIR ===' % PROFILE)
    print('Turns: %.3f per coil, %.3f both coils in SERIES'%(g['turns'],2*g['turns']))
    print('Turns by layer LEFT:',[round(g['layer_turns']['L',i],4) for i in range(6)])
    print('Turns by layer RIGHT:',[round(g['layer_turns']['R',i],4) for i in range(6)])
    print('Trace %.3f / nominal gap %.3f / path pitch %.3f mm'%(TRACE_MM,CLEARANCE_MM,PITCH_MM))
    print('Vias %.3f pad / %.3f drill; annulus %.3f mm'%(VIA_DIAMETER_MM,VIA_DRILL_MM,(VIA_DIAMETER_MM-VIA_DRILL_MM)/2))
    print('Min radial gaps: core %.4f; outer vias %.4f; coil disks %.4f mm'%
          (g['core_clearance'],g['outer_via_clearance'],g['spiral_disk_gap']))
    print('Min unrelated via-track copper gap %.4f mm'%g['min_nonattached_via_track_clearance'])
    print('Via center pitch: core %.4f; lower opposing outer %.4f mm'%
          (g['core_via_center_spacing'],g['lower_outer_center_spacing']))
    print('Terminal tip copper gap %.4f mm'%g['terminal_gap'])
    lengths=g['total_lengths']
    print('Copper path length: %.1f mm per left+right pair'%(sum(lengths)))
    # Copper resistivity at ~20 C, nominal finished trace section only.
    R_est=sum(L*1.724e-5/(TRACE_MM*(cu_um/1000)) for L,cu_um in zip(lengths,REQUIRED_FINISHED_COPPER_UM))
    print('Estimated 20 C DC pair R ~%.3f ohm (traces only, not vias/etch)'%R_est)
    print('Ideal P @ 0.2 / 0.3 / 0.5 A: %.0f / %.0f / %.0f mW'%
          tuple(1000*R_est*i*i for i in (0.2,0.3,0.5)))
    print('Idealized 10mN benchmark using Coil D 24 turns / 0.3A:')
    i_ideal=.3*24.0/g['turns']
    print('Current %.3f A, trace-only loss %.1f mW (NOT a force prediction)'%(i_ideal,1000*i_ideal*i_ideal*R_est))
    print('F.Cu IN %.4f,%.4f; OUT %.4f,%.4f (connect to real surface pads)'%
          (g['input_tip']+g['output_tip']))
    print('Requested finished Cu in um by layer:', REQUIRED_FINISHED_COPPER_UM)
    print('WARNING: Copper thickness is only a fabrication request, NOT encoded in tracks.')
    print('WARNING: PCBWay stackup/DFM acceptance + actual KiCad DRC are mandatory.')
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
