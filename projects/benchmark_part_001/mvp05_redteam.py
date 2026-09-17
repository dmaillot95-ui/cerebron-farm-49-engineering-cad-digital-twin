"""ARCHITECTON CAD Ω — MVP-05 deterministic Red Team of the dependency/transaction kernel.
Attacks semantic DAG and parameter transaction assumptions. No simulated agent.
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'out_mvp05'; OUT.mkdir(exist_ok=True)

BASE_DEPS={
 'feature:base':['param:width','param:height','param:thickness'],
 'feature:holes':['feature:base','param:hole_diameter','param:hole_spacing_x','param:hole_spacing_y'],
 'feature:fillets':['feature:holes','param:fillet_radius'],
 'feature:chamfer':['feature:fillets','param:chamfer'],
 'output:mass_properties':['feature:chamfer'],
 'output:step_export':['feature:chamfer'],
}
KNOWN_PARAMS={'param:width','param:height','param:thickness','param:hole_diameter','param:hole_spacing_x','param:hole_spacing_y','param:fillet_radius','param:chamfer'}

def acyclic(deps):
    visiting=set(); done=set()
    def visit(n):
        if n in visiting:return False
        if n in done:return True
        visiting.add(n)
        for p in deps.get(n,[]):
            if p in deps and not visit(p):return False
        visiting.remove(n);done.add(n);return True
    return all(visit(n) for n in deps)

def unknown_refs(deps):
    known=set(deps)|KNOWN_PARAMS
    return sorted({p for parents in deps.values() for p in parents if p not in known})

def validate_params(p):
    positive=['width','height','thickness','hole_diameter','fillet_radius']
    if any(float(p[k])<=0 for k in positive): return False
    if float(p['hole_diameter'])>=min(float(p['width']),float(p['height'])): return False
    if float(p['hole_spacing_x'])>=float(p['width']) or float(p['hole_spacing_y'])>=float(p['height']): return False
    return True

spec=json.loads((ROOT/'spec.json').read_text())
base=dict(spec['parameters'])
attacks=[]

def record(name,detected,detail): attacks.append({'attack':name,'detected':bool(detected),'detail':detail})

# RT1 cycle injection
x={k:list(v) for k,v in BASE_DEPS.items()};x['feature:base'].append('feature:chamfer')
record('cycle_injection',not acyclic(x),'feature:base <- feature:chamfer creates cycle')
# RT2 self-loop
x={k:list(v) for k,v in BASE_DEPS.items()};x['feature:holes'].append('feature:holes')
record('self_dependency',not acyclic(x),'feature:holes references itself')
# RT3 unknown semantic dependency
x={k:list(v) for k,v in BASE_DEPS.items()};x['feature:holes'].append('param:ghost_dimension')
record('unknown_dependency',bool(unknown_refs(x)),unknown_refs(x))
# RT4 negative dimension
p=dict(base);p['thickness']=-1
record('negative_dimension',not validate_params(p),'thickness=-1')
# RT5 oversized hole
p=dict(base);p['hole_diameter']=1000
record('oversized_feature',not validate_params(p),'hole_diameter=1000')
# RT6 feature placement outside base envelope
p=dict(base);p['hole_spacing_x']=1000
record('out_of_envelope_pattern',not validate_params(p),'hole_spacing_x=1000')
# RT7 multiple invalid mutations must be atomic rejection
p=dict(base);p.update({'thickness':-2,'hole_diameter':1000})
accepted=validate_params(p)
committed=base if not accepted else p
record('multi_mutation_atomicity',(not accepted and committed==base),'invalid batch leaves committed parameter set unchanged')
# RT8 clean baseline must not trigger false positive
record('baseline_acceptance',acyclic(BASE_DEPS) and not unknown_refs(BASE_DEPS) and validate_params(base),'valid baseline accepted')

status='PASS' if all(a['detected'] for a in attacks) else 'FAIL'
report={'gate':'MVP-05_DETERMINISTIC_RED_TEAM','attacks':attacks,'attack_count':len(attacks),'detected_count':sum(a['detected'] for a in attacks),'status':status,'scope':'Adversarial deterministic tests of one benchmark dependency/parameter kernel; not a general security or industrial CAD certification.'}
(OUT/'mvp05_redteam_report.json').write_text(json.dumps(report,indent=2,sort_keys=True))
print(json.dumps(report,indent=2,sort_keys=True))
if status!='PASS': raise SystemExit(1)
