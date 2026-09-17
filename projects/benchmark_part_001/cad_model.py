"""ARCHITECTON CAD Ω — Benchmark Part 001.
Deterministic parametric geometry benchmark. Units: mm.
"""
from __future__ import annotations
import json
from pathlib import Path
import cadquery as cq

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "out"
OUT.mkdir(exist_ok=True)

spec = json.loads((ROOT / "spec.json").read_text(encoding="utf-8"))
p = spec["parameters"]

w = float(p["width"])
h = float(p["height"])
t = float(p["thickness"])
d = float(p["hole_diameter"])
sx = float(p["hole_spacing_x"])
sy = float(p["hole_spacing_y"])
r = float(p["fillet_radius"])
c = float(p["chamfer"])

# Base plate, four-hole rectangular pattern, then edge finishing.
part = cq.Workplane("XY").box(w, h, t, centered=(True, True, False))
part = (
    part.faces(">Z")
    .workplane()
    .pushPoints([(-sx/2, -sy/2), (-sx/2, sy/2), (sx/2, -sy/2), (sx/2, sy/2)])
    .hole(d)
)

# Apply vertical-edge fillets and top-edge chamfer as separate deterministic features.
part = part.edges("|Z").fillet(r)
part = part.faces(">Z").edges().chamfer(c)

shape = part.val()
if not shape.isValid():
    raise RuntimeError("GEOMETRY_INVALID")

cq.exporters.export(part, str(OUT / "benchmark_part_001.step"))
cq.exporters.export(part, str(OUT / "benchmark_part_001.stl"), tolerance=0.05, angularTolerance=0.1)

bb = shape.BoundingBox()
props = {
    "project": spec["project"],
    "status": "GEOMETRY_VALID",
    "is_valid": bool(shape.isValid()),
    "solid_count": len(shape.Solids()),
    "volume_mm3": float(shape.Volume()),
    "area_mm2": float(shape.Area()),
    "bounding_box_mm": {"x": bb.xlen, "y": bb.ylen, "z": bb.zlen},
    "parameters": p
}
(OUT / "geometry_properties.json").write_text(json.dumps(props, indent=2, sort_keys=True), encoding="utf-8")
print(json.dumps(props, indent=2, sort_keys=True))
