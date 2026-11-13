Six-layer dense CW/CCW coil variants, 6.00 mm center-to-center
============================================================
All three variants retain the center-bottom outer transition vias.
Configuration                Turns/coil  Min inner spiral centerline radius
56-turn balanced: 0.14/0.10     56          0.59056 mm
68-turn dense: 0.10/0.10        68          0.58106 mm
74-turn experimental: 0.09/0.095 74         0.56663 mm

Each design uses 0.30 mm via pad / 0.15 mm drill, a 0.25 mm-radius
three-via inner ring, 6 copper layers, and 6.00 mm coil separation.
All variants are modeled and simulated; actual KiCad DRC not performed.

WARNING: These are high-density prototype candidates. Obtain explicit
fabricator approval for finished drill sizes, via annular rings,
coil trace/space geometry, and every-layer PTH via geometry. Verify
board-edge outline and external footprints, and ensure the layer count
is set to 6. Trace widths below 0.15 mm and gaps below 0.15 mm can be
outside a fabricator's trace-coil guidelines, even if their standard
routing minimums appear to permit them.

Run in KiCad PCB Editor Python console, e.g.:
exec(open(r"C:\path\create_cw_ccw_6layer_56turn_balanced.py", encoding="utf-8").read())

The script ADDS tracks and vias. DELETE the earlier generated coil copper
before running a new variant. Ensure existing net /COIL+ is present.
F.Cu terminal stubs do not provide footprint pads.
