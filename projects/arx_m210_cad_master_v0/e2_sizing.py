"""ARX-M210 Omega — E2 PRELIMINARY SIZING SWEEP.
Deterministic conceptual calculation only. NOT manufacturing data and NOT validated design.
Inputs tagged TARGET/ASSUMPTION; outputs tagged CALCULATED_E2_CANDIDATE.
"""
from math import pi, sqrt
import json
from pathlib import Path

F = 2.10e6       # N, TARGET approximate thrust class
Pc = 18.0e6      # Pa, TARGET from S03-D-0001

# Broad conceptual sweep, deliberately not a frozen design.
OF = [3.4, 3.6, 3.8]
CSTAR = [1750.0, 1800.0, 1850.0]       # m/s ASSUMPTION; requires thermochemistry closure
CF = [1.45, 1.50, 1.55]                # ASSUMPTION; requires nozzle/ambient closure
EPS = [25.0, 35.0, 45.0]               # ASSUMPTION; within historical LOX/CH4 study envelope
LSTAR = [0.9, 1.1, 1.3]                # m ASSUMPTION; requires combustion/stability evidence
CONTRACTION = [2.5, 3.0, 3.5]          # ASSUMPTION

rows=[]
for of in OF:
  for cstar in CSTAR:
    for cf in CF:
      for eps in EPS:
        for ls in LSTAR:
          for cr in CONTRACTION:
            At=F/(Pc*cf)
            Dt=sqrt(4*At/pi)
            mdot=Pc*At/cstar
            mf=mdot/(1+of)
            mo=mdot-mf
            Ae=eps*At
            De=sqrt(4*Ae/pi)
            Ac=cr*At
            Dc=sqrt(4*Ac/pi)
            Vc=ls*At
            rows.append({
              'OF':of,'cstar_m_s':cstar,'Cf':cf,'epsilon':eps,'Lstar_m':ls,'contraction_ratio':cr,
              'throat_area_m2':At,'throat_diameter_m':Dt,
              'mass_flow_total_kg_s':mdot,'mass_flow_LOX_kg_s':mo,'mass_flow_CH4_kg_s':mf,
              'exit_area_m2':Ae,'exit_diameter_m':De,
              'chamber_area_m2':Ac,'chamber_diameter_m':Dc,'characteristic_chamber_volume_m3':Vc
            })

def span(key):
  vals=[r[key] for r in rows]
  return {'min':min(vals),'max':max(vals)}

# Center point is a bookkeeping reference only, not an optimum.
center=min(rows,key=lambda r: abs(r['OF']-3.6)+abs(r['cstar_m_s']-1800)/100+abs(r['Cf']-1.50)*10+abs(r['epsilon']-35)/10+abs(r['Lstar_m']-1.1)*5+abs(r['contraction_ratio']-3.0))
report={
 'gate':'ARX-M210_E2_PRELIMINARY_SIZING',
 'status':'CALCULATED_E2_CANDIDATE',
 'target_inputs':{'thrust_N':F,'chamber_pressure_Pa':Pc},
 'sweep_cases':len(rows),
 'center_reference_NOT_OPTIMUM':center,
 'ranges':{k:span(k) for k in ['throat_diameter_m','mass_flow_total_kg_s','mass_flow_LOX_kg_s','mass_flow_CH4_kg_s','exit_diameter_m','chamber_diameter_m','characteristic_chamber_volume_m3']},
 'blocking_unknowns':['thermochemistry/CEA-equivalent closure','sea-level nozzle separation margin','combustion stability','regenerative cooling','wall/material stress','injector pressure drop','ORSC turbomachinery','engine envelope and mass'],
 'claim':'This sweep constrains a conceptual geometry search space. It does not establish correct, safe, manufacturable, qualified, or flight-ready dimensions.'
}
out=Path(__file__).with_name('e2_sizing_report.json')
out.write_text(json.dumps(report,indent=2,sort_keys=True))
print(json.dumps(report,indent=2,sort_keys=True))
