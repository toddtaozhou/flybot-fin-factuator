PCBWay all-1-oz, 6-layer PCB fin actuator — low-loss CW/CCW series pair
=========================================================================
FILE: pcbway_6layer_1oz_low_loss_coil.py

Design intent
-------------
The goal is force per WATT with a continuously held fin, not turns alone.
The design is optimized within the EXISTING spiral / through-via / series
routing topology and PCBWay's NORMAL 1-oz track/spacing limits. It is NOT
proven to be the globally optimum coil; magnet and driver testing are needed.

Six copper layers of 1-oz finished copper (nominal 35 um each), with:
 - Two coil centers at (90,100) and (96,100) mm on existing board.
 - Left winding clockwise, right counterclockwise under series current.
 - 26 turns per coil; 52 turns for both coils in series.
 - Track 0.250 mm; nominal copper gap 0.155 mm.
 - Archimedean pitch 0.410 mm incl. 0.005-mm approximation guard.
 - Outer spiral centerline radius 2.780 mm.
 - Inner via ring radius 0.390 mm, 3 inner vias per coil.
 - Outer through-via radial distance 3.335 mm, 2 outer vias per coil.
 - Ten (10) 0.50-mm pad / 0.20-mm drill standard plated-through vias.
 - Outer bottom vias routed toward CENTER-BOTTOM gap, not board edge.
 - Terminal stubs on F.Cu only (no through-via terminal shorts).
 - Requested PCB thickness 1.0 mm; PCBWay's six-layer NORMAL minimum is 0.9 mm.

Calculated electrical values at 20 degrees C
---------------------------------------------
 - Copper path length: ~631.2 mm, both coils total.
 - Trace-only pair resistance: ~1.244 ohm at 35um copper (nominal).
 - Trace-only pair I^2*R: ~50mW at 0.2A; ~112mW at 0.3A;
                            ~311mW at 0.5A.
These omit vias, temperature rise, etch narrowing, H-bridge losses, and any
layer-to-layer coupling differences. No force value has been measured for this
coil. If the force/turn were unchanged from the measured 24-turn Coil D,
10mN would require ~0.277A and ~95mW in copper, but do NOT take that force
prediction as validated.

Why only 26 turns / coil?
-------------------------
For the same 6-mm footprint, six-layer series topology, 0.5/0.2-mm vias,
and PCBWay normal 1oz manufacturability, more turns require much narrower
traces. Pure copper F^2/P proxy N^2/R in the geometry comparison:
   26 turns / coil, trace 0.25 mm : ~26^2 / 1.244 = 543
   32 turns / coil, trace 0.19 mm : ~32^2 / 1.99 = 514
   38 turns / coil, trace 0.15 mm : ~38^2 / 2.96 = 488
These are IDEALIZED ampere-turns proxy values only. Actual force depends on
coil layer stackup, magnet alignment, radial turn distribution and dynamics.
Higher-turn coils reduce H-bridge current and may win when driver resistance
is substantial. Test coil + H-bridge as a full system at equal force.

PCBWay's published 1oz copper NORMAL limits (check for updates):
  outer width/space >=5/6 mil (~0.127/0.1524 mm)
  inner width/space >=4/5 mil (~0.1016/0.127 mm)
  normal 1oz via annulus >=5 mil, but PCBWay's general via guidance says
      0.15mm; design uses 0.15mm.
  0.20mm drill; normal 6L PCB thickness >=0.9mm
  copper to milled edge normally >=0.25mm
  A separate 1oz GRID-TRACE table is much stricter (>=9/11 mil).
ASK PCBWAY WHETHER THE DENSE SPIRAL IS CLASSIFIED UNDER THE GRID-TRACE RULE.
If they say it is, this 0.155-mm spacing requires revision BEFORE ORDERING.

Sources:
 https://www.pcbway.com/capabilities.html
 https://www.pcbway.com/pcb_prototype/PCB_Manufacturing_tolerances.html

Run in KiCad PCB Editor
-----------------------
1. Save a COPY of your .kicad_pcb first and delete old generated coils/vias.
2. Board Setup: set six copper layers; enter 1 oz on all copper layers in
   Physical Stackup and select PCBWay's approved 1.0-mm stackup.
3. Ensure '/COIL+' exists in PCB; or edit NET_NAME in the script.
4. PCB Editor > Tools > Scripting Console:
   exec(open(r'C:\path\pcbway_6layer_1oz_low_loss_coil.py',encoding='utf-8').read())
5. Script ADDS ~9,389 segments and 10 PTH vias. Connect the two F.Cu terminal
   stubs to the intended H-bridge terminals with correctly handled schematic
   nets (e.g. carefully designed embedded coil / net-tie strategy). Since
   generated copper is on ONE chosen net, DRC alone cannot establish that
   the spiral has no electrical shorts or that both driver pads are correct.
6. Run FULL KiCad DRC with clearance >=0.155 mm, board-edge >=0.25 mm,
   correct via sizes, stackup and all existing footprints/traces.
7. Check that every via pad is completely ON actual laminate, especially
   upper outboard and lower central vias. No board .kicad_pcb file was supplied;
   the board outline cannot be verified from a screenshot.
8. Send complete Gerber/drill/stackup to PCBWay for DFM review; request written
   acceptance for dense spirals and explicit confirmation of 35um finished
   copper on ALL 6 layers and 1.0mm stackup.
9. Measure real pair R, force at fixed current, force/W, response time, and
   steady-state temperature rise before use in the flight hardware.

Independent tests performed
---------------------------
 - Python syntax compile: passed
 - Standalone generation: passed (26 turns/coil, 9,389 segments, 10 PTH vias)
 - Graph connectivity: 1 series path; no branches; only two free terminals
 - Shapely nonlocal track-to-track spacing on each of six layers: passed
   Min tested nonlocal same-layer track gap ~0.1591mm vs 0.155mm target.
 - Via-to-nonattached track copper gap: >=0.1800mm vs 0.155mm target
 - All PTH pad-to-PTH pad copper spacing: >=0.1755mm vs 0.155mm target
 - Simulated KiCad pcbnew API: passed (9,389 tracks, ten PTH vias)
 - Actual KiCad pcbnew / native KiCad DRC: NOT AVAILABLE / NOT EXECUTED
 - Actual board outline, existing part conflicts and PCBWay DFM: NOT VERIFIED

The delivered generator is a fabrication CANDIDATE, not a released production
board. The 2-oz alternative is estimated to dissipate less power at the same
force if the heavier copper PCB passes actual manufacturing DFM.
