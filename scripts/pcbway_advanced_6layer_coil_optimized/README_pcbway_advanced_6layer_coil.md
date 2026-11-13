# PCBWay Advanced — six-layer CW/CCW fin actuator coil pair

## Purpose and choice

Maintain the previous **6.0-mm center-to-center**, two spiral coils connected
in **one electrical series path**. The lower outer transition vias remain
in the center-bottom web. The generator uses 10 **plated THROUGH vias**
through all 6 copper layers, and two F.Cu terminal stubs (add driver pads).

**Selected default: `TWO_OZ_26`.** It is a low-resistance, comparatively
wide-trace design for lowest coil heating at a required force. Switch to
`TWO_OZ_32` if the real H-bridge/driver has >~0.15 ohm of effective series
resistance or if lower peak supply current is preferred. This crossover is
an idealized equal-coupling estimate; it is not a measured force result.

## Fabrication profiles

| Profile | Finished Cu F/In1/In2/In3/In4/B (um) | Turns/coil | Trace (mm) | Minimum copper gap (mm) | Spiral pitch (mm) | Spiral outer centerline r (mm) | Via pad/drill (mm) | Inner ring r (mm) | Calculated pair R (ohm, 20C) |
|---|---|---:|---:|---:|---:|---:|---|---:|---:|
| TWO_OZ_26 | 70/70/70/70/70/70 | 26 | .270 | .132 | .407 | 2.790 | .56/.20 | .420 | .581 |
| TWO_OZ_32 | 70/70/70/70/70/70 | 32 | .200 | .132 | .337 | 2.800 | .56/.20 | .420 | .957 |
| MIXED_26 | 35/50/50/50/50/35 | 26 | .300 | .110 | .415 | 2.770 | .50/.20 | .390 | .819 |
| MIXED_32 | 35/50/50/50/50/35 | 32 | .240 | .110 | .355 | 2.810 | .50/.20 | .390 | 1.249 |

All options retain 6.0-mm coil centers and a fixed left CW / right CCW
current orientation. Their lower opposing outer via centers are separated by
~1.0-1.1 mm. Outer rim vias are placed at the phase positions used by the
existing center-bottom-via generator.

## How resistance and heating were estimated

Use rho(Cu,20C) = 1.724e-8 ohm*m. The generator sums actual emitted
polyline segment lengths on every layer, with each layer's specified
nominal *finished* copper thickness. Track copper only: no via barrels,
H-bridge, vias' extra constriction, contact resistance, temperature rise, or
actual etched cross-section. Resistance increases when hot.

At 0.3 A copper heating for 2oz26 / 2oz32 / mixed26 / mixed32:
~52 / 86 / 74 / 112 mW respectively.

Your older four-layer Coil D produced ~10 mN at 0.3 A with
3/16 x 1/16-inch magnet and ~0.5mm gap, and a reported 1.2-ohm
series-pair resistance (confirm if 1.2ohm is instead per coil).
In a **highly simplified equal-force-per-turn model**, reaching that force
could take 0.3 x 24/26=0.277 A for a 26-turn profile, or 0.225 A for
32 turns; the actual force depends on layer distance, magnet placement,
field gradient, coil-turn radius and driver operation. These are **not**
force predictions.

## PCBWay process assumptions and caveats

The process constraints supplied by the user are: minimum 4 mil traces and
spacing with 1 oz outer / 1.5 oz inner, and 5 mil with 2 oz on all layers.
This generator uses **.110 mm** or **.132 mm** nominal copper gap, slightly
larger than 4mil=.1016mm and 5mil=.1270mm. Trace widths are wider.
For mixed-copper nominal via pads .50/.20mm give .15mm annulus; for
heavy copper .56/.20mm give .18mm annulus. Verify plating drill tolerance,
minimum hole-to-copper, and the chosen PCB thickness before fabrication.

**The PCB file does not encode finished copper weights.** Request explicit
written approval from PCBWay of the six-layer heavy-copper stackup, a 1.0-mm
board if achievable (or alternate minimum thickness), and the close concentric
copper features. Ask whether the manufacturing team treats dense coils as
"grid traces" subject to a different rule, and review minimum drill aspect
ratio, annuli, masking, and board-edge clearances.

Sources (manufacturer):
- https://www.pcbway.com/advanced-pcb-capabilities.html
- https://www.pcbway.com/capabilities.html
- https://www.pcbway.com/pcb_prototype/PCB_Manufacturing_tolerances.html

## Running it in KiCad

1. Save a copy of the PCB. Configure it for six copper layers and set its
   appropriate physical copper stackup *manually*.
2. Delete the old coil tracks/vias. Script adds copper without deleting items.
3. Verify `NET_NAME` matches an already existing PCB net.
4. In KiCad PCB Editor's scripting console, run:

   ```python
   exec(open(r'C:\path\pcbway_advanced_coil_6layer_optimized.py', encoding='utf-8').read())
   ```

5. The script prints the selected profile, per-layer turns, length, resistance
   estimate, and terminal coordinates. Surface-mount driver pads are **not**
   automatically created. Keep the external electrical netlist consistent.
6. Run actual KiCad DRC for width/spacing/annulus/edge/nearby pads. Confirm
   all ten vias have enough real laminate around them; the provided screenshot
   alone is not enough to verify board-edge clearance.
7. Send stackup, Gerbers, plated-hole data, and DRC report to PCBWay for DFM.

## Tests performed locally

- All four profiles: Python compilation and standalone execution passed.
- Track/via generation executed through a simulated `pcbnew` API.
- Graph continuity: one unbranched series path and exactly two F.Cu ends.
- Independent Shapely near-neighbor tests of all generated copper tracks on
  each of the six layers and through-via-to-track/via checks passed.
- Minimum nonlocal spiral-to-spiral copper gaps: 2oz26 .1362mm,
  2oz32 .1364mm, mixed26 .1141mm, mixed32 .1143mm.
- Minimum via-to-nonattached track gaps: 2oz26 .1472mm,
  2oz32 .1520mm, mixed26 .1300mm, mixed32 .1182mm.

**Not tested:** native KiCad `pcbnew`, whole-board DRC, actual Edge.Cuts,
PCBWay CAM/DFM, measured force, heat or resistance. This is a prototyping
baseline within a constrained geometry, not a manufacturing release.
