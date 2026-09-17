"""ARCHITECTON CAD Ω — MVP-02 parametric propagation gate.
Build baseline and mutated variants, prove dependency propagation by geometry properties and hashes.
Units: mm.
"""
from __future__ import annotations
import hashlib, json
from pathlib import Path
import cadquery as cq

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "out_mvp02"
OUT.mkdir(exist_ok=True)
spec = json.loads((ROOT / "spec.json").read_text(encoding="utf-8"))
base = dict(spec["parameters"])
mut = dict(base)
mut["hole_diameter"] = float(base["hole_diameter"]) + 2.0


def build(p, stem):
    w,h,t = map(float,(p["width"],p["height"],p["thickness"]))
    d,sx,sy = map(float,(p["hole_diameter"],p["hole_spacing_x"],p["hole_spacing_y"]))
    r,c = map(float,(p["fillet_radius"],p["chamfer"]))
    part = cq.Workplane("XY").box(w,h,t,centered=(True,True,False))
    part = part.faces(">Z").workplane().pushPoints([(-sx/2,-sy/2),(-sx/2,sy/2),(sx/2,-sy/2),(sx/2,sy/2)]).hole(d)
    part = part.edges("|Z").fillet(r)
    part = part.faces(">Z").edges().chamfer(c)
    shape = part.val()
    if not shape.isValid() or len(shape.Solids()) != 1:
        raise RuntimeError(f"{stem}: GEOMETRY_INVALID")
    step = OUT / f"{stem}.step"
    cq.exporters.export(part, str(step))
    bb = shape.BoundingBox()
    return {
        "parameters": p,
        "valid": True,
        "solid_count": len(shape.Solids()),
        "volume_mm3": float(shape.Volume()),
        "area_mm2": float(shape.Area()),
        "bbox_mm": [float(bb.xlen),float(bb.ylen),float(bb.zlen)],
        "step_sha256": hashlib.sha256(step.read_bytes()).hexdigest(),
        "step_bytes": step.stat().st_size,
    }

before = build(base, "before")
after = build(mut, "after")

checks = {
    "only_requested_input_changed": all(base[k] == mut[k] for k in base if k != "hole_diameter"),
    "hole_diameter_changed": base["hole_diameter"] != mut["hole_diameter"],
    "both_geometries_valid": before["valid"] and after["valid"],
    "volume_changed": abs(before["volume_mm3"] - after["volume_mm3"]) > 1e-9,
    "area_changed": abs(before["area_mm2"] - after["area_mm2"]) > 1e-9,
    "step_hash_changed": before["step_sha256"] != after["step_sha256"],
    "outer_bbox_preserved": all(abs(a-b) < 1e-9 for a,b in zip(before["bbox_mm"], after["bbox_mm"])),
}
status = "PASS" if all(checks.values()) else "FAIL"
report = {
    "project": "benchmark_part_001",
    "gate": "MVP-02_PARAMETRIC_PROPAGATION",
    "mutation": {"parameter":"hole_diameter","before":base["hole_diameter"],"after":mut["hole_diameter"],"unit":"mm"},
    "before": before,
    "after": after,
    "checks": checks,
    "status": status,
    "scope": "Parametric rebuild and observable dependency propagation only; not industrial design validation."
}
(OUT / "mvp02_report.json").write_text(json.dumps(report,indent=2,sort_keys=True),encoding="utf-8")
print(json.dumps(report,indent=2,sort_keys=True))
if status != "PASS":
    raise SystemExit(1)
