"""Validate ARCHITECTON benchmark artifacts and emit a hash manifest."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "out"
spec = json.loads((ROOT / "spec.json").read_text(encoding="utf-8"))
props = json.loads((OUT / "geometry_properties.json").read_text(encoding="utf-8"))

errors = []
if not props.get("is_valid"):
    errors.append("shape is not valid")
if props.get("solid_count") != spec["requirements"]["solid_count"]:
    errors.append("unexpected solid count")
if props.get("volume_mm3", 0) <= spec["requirements"]["minimum_volume_mm3"]:
    errors.append("non-positive/too-small volume")

required = [OUT / "benchmark_part_001.step", OUT / "benchmark_part_001.stl", OUT / "geometry_properties.json"]
artifacts = []
for path in required:
    if not path.exists() or path.stat().st_size == 0:
        errors.append(f"missing or empty artifact: {path.name}")
        continue
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    artifacts.append({"name": path.name, "bytes": path.stat().st_size, "sha256": digest})

manifest = {
    "project": spec["project"],
    "claim": "CAD_PIPELINE_EXECUTED" if not errors else "CAD_PIPELINE_FAILED",
    "scope": "Geometry generation/export reproducibility only; not industrial design validation.",
    "artifacts": artifacts,
    "errors": errors,
}
(OUT / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
print(json.dumps(manifest, indent=2, sort_keys=True))
if errors:
    raise SystemExit(1)
