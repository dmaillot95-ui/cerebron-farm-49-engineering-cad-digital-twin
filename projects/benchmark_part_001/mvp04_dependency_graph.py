"""ARCHITECTON CAD Ω — MVP-04.2 dependency graph + selective rebuild.
FARM 49 primary deterministic CAD worker. Semantic namespaces prevent feature/parameter collisions.
"""
from __future__ import annotations
import hashlib, json
from pathlib import Path
import cadquery as cq

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'out_mvp04'; OUT.mkdir(exist_ok=True)
spec=json.loads((ROOT/'spec.json').read_text(encoding='utf-8'))
P=dict(spec['parameters'])

# Namespaced semantic DAG: param:* -> feature:* -> output:*.
DEPS={
 'feature:base':['param:width','param:height','param:thickness'],
 'feature:holes':['feature:base','param:hole_diameter','param:hole_spacing_x','param:hole_spacing_y'],
 'feature:fillets':['feature:holes','param:fillet_radius'],
 'feature:chamfer':['feature:fillets','param:chamfer'],
 'output:mass_properties':['feature:chamfer'],
 'output:step_export':['feature:chamfer'],
}
NODES=['feature:base','feature:holes','feature:fillets','feature:chamfer','output:mass_properties','output:step_export']

def descendants(changed):
    dirty=set(changed); progress=True
    while progress:
        progress=False
        for node,parents in DEPS.items():
            if node not in dirty and any(p in dirty for p in parents):
                dirty.add(node); progress=True
    return [x for x in NODES if x in dirty]

def dag_acyclic():
    visiting=set(); done=set()
    def visit(n):
        if n in visiting: return False
        if n in done: return True
        visiting.add(n)
        for p in DEPS.get(n,[]):
            if p in DEPS and not visit(p): return False
        visiting.remove(n); done.add(n); return True
    return all(visit(n) for n in DEPS)

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
actual_dirty=descendants({'param:hole_diameter'})
expected=['feature:holes','feature:fillets','feature:chamfer','output:mass_properties','output:step_export']
after=build(mut,OUT/'after.step')
checks={
 'semantic_namespaces_distinct': 'feature:chamfer' != 'param:chamfer',
 'dag_is_acyclic': dag_acyclic(),
 'dirty_set_exact': actual_dirty==expected,
 'base_not_rebuilt': 'feature:base' not in actual_dirty,
 'downstream_geometry_rebuilt': all(x in actual_dirty for x in ['feature:holes','feature:fillets','feature:chamfer']),
 'outputs_rebuilt': all(x in actual_dirty for x in ['output:mass_properties','output:step_export']),
 'geometry_changed': before['sha256']!=after['sha256'] and before['volume']!=after['volume'],
 'outer_envelope_preserved': all(abs(a-b)<1e-9 for a,b in zip(before['bbox'],after['bbox'])),
}
status='PASS' if all(checks.values()) else 'FAIL'
report={'gate':'MVP-04.2_NAMESPACED_DEPENDENCY_GRAPH','changed_parameter':'param:hole_diameter','dependency_graph':DEPS,'dirty_nodes':actual_dirty,'expected_dirty_nodes':expected,'before':before,'after':after,'checks':checks,'status':status,'scope':'Namespaced DAG invalidation/selective rebuild proof for one benchmark part; not yet a general industrial dependency engine.'}
(OUT/'mvp04_report.json').write_text(json.dumps(report,indent=2,sort_keys=True),encoding='utf-8')
print(json.dumps(report,indent=2,sort_keys=True))
if status!='PASS': raise SystemExit(1)
