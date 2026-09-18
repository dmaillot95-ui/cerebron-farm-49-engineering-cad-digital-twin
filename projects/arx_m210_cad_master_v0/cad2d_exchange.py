"""FARM 49 — traceable 2D CAD exchange generator.
Creates ASCII DXF + SVG from explicit dimensional inputs only.
TBD/unknown values are preserved in the manifest and never invented.
"""
import json, pathlib, sys

ROOT=pathlib.Path(__file__).resolve().parent
OUT=ROOT/"artifacts"; OUT.mkdir(exist_ok=True)
spec=json.loads((ROOT/"cad2d_spec.json").read_text(encoding="utf-8"))
dims=spec["dimensions"]
required=("overall_length_mm","overall_diameter_mm")
missing=[k for k in required if not isinstance(dims.get(k), (int,float))]
manifest={"schema":"cerebron-f49-cad2d-v1","project":spec["project"],"source_evidence":spec.get("evidence_level","UNKNOWN"),"dimensions":dims,"missing_required":missing,"status":"BLOCKED_TBD" if missing else "GENERATED_PROVISIONAL","claim":"CAD exchange geometry is generated from explicit inputs; it is not validated manufacturing geometry."}
(OUT/"cad2d_manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
if missing:
    print(json.dumps(manifest,indent=2)); sys.exit(0)
L=float(dims["overall_length_mm"]); D=float(dims["overall_diameter_mm"]); r=D/2
# Minimal standards-compatible ASCII DXF R12: envelope side view + centerline.
dxf=f"""0
SECTION
2
ENTITIES
0
LINE
8
ENVELOPE
10
0
20
{-r}
11
{L}
21
{-r}
0
LINE
8
ENVELOPE
10
{L}
20
{-r}
11
{L}
21
{r}
0
LINE
8
ENVELOPE
10
{L}
20
{r}
11
0
21
{r}
0
LINE
8
ENVELOPE
10
0
20
{r}
11
0
21
{-r}
0
LINE
8
CENTER
10
0
20
0
11
{L}
21
0
0
ENDSEC
0
EOF
"""
(OUT/"engineering_envelope.dxf").write_text(dxf,encoding="ascii")
pad=max(D*.15,10); vb=f"{-pad} {-r-pad} {L+2*pad} {D+2*pad}"
svg=f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb}"><g fill="none" stroke="black"><rect x="0" y="{-r}" width="{L}" height="{D}"/><line x1="0" y1="0" x2="{L}" y2="0" stroke-dasharray="10 5"/></g><text x="0" y="{-r-pad/3}" font-size="{max(D*.04,4)}">PROVISIONAL — L={L:g} mm — D={D:g} mm</text></svg>'''
(OUT/"engineering_envelope.svg").write_text(svg,encoding="utf-8")
print(json.dumps(manifest,indent=2))
