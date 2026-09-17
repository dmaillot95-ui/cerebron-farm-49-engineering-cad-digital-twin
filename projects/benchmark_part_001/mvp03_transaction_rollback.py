"""ARCHITECTON CAD Ω — MVP-03 transaction/rollback gate.
Deliberately proposes an impossible edit, rejects it, and proves preservation of the last valid CAD state.
"""
from __future__ import annotations
import hashlib, json, shutil
from pathlib import Path
import cadquery as cq

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'out_mvp03'; OUT.mkdir(exist_ok=True)
spec=json.loads((ROOT/'spec.json').read_text(encoding='utf-8'))
base=dict(spec['parameters'])

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def build_valid(p, target):
    w,h,t=map(float,(p['width'],p['height'],p['thickness']))
    d,sx,sy=map(float,(p['hole_diameter'],p['hole_spacing_x'],p['hole_spacing_y']))
    r,c=map(float,(p['fillet_radius'],p['chamfer']))
    if min(w,h,t,d,r) <= 0: raise ValueError('NON_POSITIVE_GEOMETRY_PARAMETER')
    part=cq.Workplane('XY').box(w,h,t,centered=(True,True,False))
    part=part.faces('>Z').workplane().pushPoints([(-sx/2,-sy/2),(-sx/2,sy/2),(sx/2,-sy/2),(sx/2,sy/2)]).hole(d)
    part=part.edges('|Z').fillet(r)
    part=part.faces('>Z').edges().chamfer(c)
    shape=part.val()
    if not shape.isValid() or len(shape.Solids()) != 1: raise RuntimeError('GEOMETRY_INVALID')
    cq.exporters.export(part,str(target))
    return shape

committed=OUT/'committed.step'
build_valid(base,committed)
before_hash=sha(committed)
before_bytes=committed.read_bytes()

# Transaction proposal: impossible negative thickness.
proposal=dict(base); proposal['thickness']=-5.0
transaction={'state':'PROPOSED','mutation':{'parameter':'thickness','before':base['thickness'],'after':proposal['thickness'],'unit':'mm'}}
rejected=False; error=None
tmp=OUT/'candidate.step'
try:
    build_valid(proposal,tmp)
except Exception as exc:
    rejected=True; error=f'{type(exc).__name__}: {exc}'
    transaction['state']='ROLLBACK'
    if tmp.exists(): tmp.unlink()
else:
    transaction['state']='COMMIT'
    shutil.move(tmp,committed)

after_hash=sha(committed)
after_bytes=committed.read_bytes()
checks={
 'invalid_proposal_rejected': rejected,
 'transaction_rolled_back': transaction['state']=='ROLLBACK',
 'candidate_not_committed': not tmp.exists(),
 'committed_hash_preserved': before_hash==after_hash,
 'committed_bytes_preserved': before_bytes==after_bytes,
}
status='PASS' if all(checks.values()) else 'FAIL'
report={'gate':'MVP-03_TRANSACTION_ROLLBACK','transaction':transaction,'error':error,'before_sha256':before_hash,'after_sha256':after_hash,'checks':checks,'status':status,'scope':'Transaction rejection and preservation of last valid STEP state; not industrial validation.'}
(OUT/'mvp03_report.json').write_text(json.dumps(report,indent=2,sort_keys=True),encoding='utf-8')
print(json.dumps(report,indent=2,sort_keys=True))
if status!='PASS': raise SystemExit(1)
