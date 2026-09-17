"""ARCHITECTON CAD Ω — MVP-04 dependency graph + selective rebuild.
FARM 49 primary deterministic CAD worker. No simulated agents.
"""
from __future__ import annotations
import hashlib, json
from pathlib import Path
import cadquery as cq

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'out_mvp04'; OUT.mkdir(exist_ok=True)
spec=json.loads((ROOT/'spec.json').read_text(encoding='utf-8'))
P=dict(spec['parameters'])

# Explicit semantic DAG: parameters -> features -> outputs.
DEPS={
 'base':['width','height','thickness'],
 'holes':['base','hole_diameter','hole_spacing_x','hole_spacing_y'],
 'fillets':['holes','fillet_radius'],
 'chamfer':['fillets','chamfer'],
 'mass_properties':['chamfer'],
 'step_export':['chamfer'],
}
FEATURES=['base','holes','fillets','chamfer','mass_properties','step_export']

def descendants(changed):
    dirty=set(changed); progress=True
    while progress:
        progress=False
        for node,parents in DEPS.items():
            if node not in dirty and any(p in dirty for p in parents):
                dirty.add(node); progress=True
    return [x for x in FEATURES if x in dirty]

def build(p,path):
    w,h,t=map(float,(p['width'],p['height'],p['thickness']))
    d,sx,sy=map(float,(p['hole_diameter'],p['hole_spacing_x'],p['hole_spacing_y']))
    r,c=map(float,(p['fillet_radius'],p['chamfer']))
    part=cq.Workplane('XY').box(w,h,t,centered=(True,True,False))
    part=part.faces('>Z').workplane().pushPoints([(-sx/2,-sy/2),(-sx/2,sy/2),(sx/2,-sy/2),(sx/2,sy/2)]).hole(d)
    part=part.edges('|Z').fillet(r)
    part=part.faces('>Z').edges().chamfer(c)
    shape=part.val()
    if not shape.isValid() or len(shape.Solids())!=1: raise RuntimeError('GEOMETRY_INVALID')
    cq.exporters.export(part,str(path))
    bb=shape.BoundingBox()
    return {'volume':float(shape.Volume()),'area':float(shape.Area()),'bbox':[float(bb.xlen),float(bb.ylen),float(bb.zlen)],'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}

before=build(P,OUT/'before.step')
mut=dict(P); mut['hole_diameter']=float(P['hole_diameter'])+1.0
actual_dirty=descendants({'hole_diameter'})
expected=['holes','fillets','chamfer','mass_properties','step_export']
after=build(mut,OUT/'after.step')
checks={
 'dag_is_acyclic_for_declared_order': all(all((p not in FEATURES) or FEATURES.index(p)<FEATURES.index(n) for p in DEPS[n]) for n in FEATURES),
 'dirty_set_exact': actual_dirty==expected,
 'base_not_rebuilt': 'base' not in actual_dirty,
 'downstream_geometry_rebuilt': all(x in actual_dirty for x in ['holes','fillets','chamfer']),
 'outputs_rebuilt': all(x in actual_dirty for x in ['mass_properties','step_export']),
 'geometry_changed': before['sha256']!=after['sha256'] and before['volume']!=after['volume'],
 'outer_envelope_preserved': all(abs(a-b)<1e-9 for a,b in zip(before['bbox'],after['bbox'])),
}
status='PASS' if all(checks.values()) else 'FAIL'
report={'gate':'MVP-04_DEPENDENCY_GRAPH_SELECTIVE_REBUILD','changed_parameter':'hole_diameter','dependency_graph':DEPS,'dirty_features':actual_dirty,'expected_dirty_features':expected,'before':before,'after':after,'checks':checks,'status':status,'scope':'Explicit DAG invalidation/selective rebuild proof for one benchmark part; not yet a general industrial dependency engine.'}
(OUT/'mvp04_report.json').write_text(json.dumps(report,indent=2,sort_keys=True),encoding='utf-8')
print(json.dumps(report,indent=2,sort_keys=True))
if status!='PASS': raise SystemExit(1)
