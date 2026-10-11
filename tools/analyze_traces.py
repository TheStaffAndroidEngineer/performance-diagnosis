#!/usr/bin/env python3
"""Extract per-operation clipped scheduling states and retain exact queries/results."""
from pathlib import Path
import argparse,subprocess,csv,io,json,hashlib
HERE=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('capture',type=Path);a=p.parse_args()
m=json.loads((a.capture/'manifest.json').read_text())
out=a.capture/'analysis';out.mkdir(exist_ok=False)
query="""SELECT s.id,s.name,s.ts,s.dur,t.utid,th.tid,th.name AS thread
FROM slice s JOIN thread_track t ON s.track_id=t.id
JOIN thread th USING(utid)
WHERE s.name GLOB 'CG/*' AND s.dur >= 0 ORDER BY s.ts"""
(out/'slices.sql').write_text(query+'\n')
def sql(trace,q,stem):
 r=subprocess.run(['python3',str(HERE/'trace_processor'),'-Q',q,str(trace)],capture_output=True,text=True,check=True)
 (out/(stem+'.csv')).write_text(r.stdout);(out/(stem+'.stderr')).write_text(r.stderr)
 return list(csv.DictReader(io.StringIO(r.stdout)))
summary={'scope':'Controlled API36 emulator observations from the retained optimized/profileable APK; no representative performance or causal meaning inferred from state letters alone','apk_sha256':m['apk_sha256'],'records':[]}
for run in m['records']:
 trace=Path(run['trace']);name=f"{run['scenario']}-{run['iteration']}"
 assert hashlib.sha256(trace.read_bytes()).hexdigest()==run['trace_sha256']
 slices=sql(trace,query,name+'-slices')
 rows=[]
 for s in slices:
  if s['name'] not in ['CG/blocked/snapshot','CG/blocked/hold','CG/source/load','CG/busy/checksum','CG/repaired/load','CG/repaired/publish']:continue
  ts,dur,utid=map(int,[s['ts'],s['dur'],s['utid']])
  statequery=f"SELECT state,SUM(MIN(ts+dur,{ts+dur})-MAX(ts,{ts})) AS duration_ns FROM thread_state WHERE utid={utid} AND dur>=0 AND ts<{ts+dur} AND ts+dur>{ts} GROUP BY state ORDER BY state"
  (out/(name+'-'+s['id']+'-states.sql')).write_text(statequery+'\n')
  states=sql(trace,statequery,name+'-'+s['id']+'-states')
  budget={x['state']:int(x['duration_ns']) for x in states}
  assert sum(budget.values())<=dur,(s,budget)
  rows.append({**s,'ts':ts,'duration_ns':dur,'states_ns':budget,'uncovered_ns':dur-sum(budget.values())})
 stats=sql(trace,"SELECT name,idx,value,severity FROM stats WHERE value>0 AND severity IN ('error','data_loss') ORDER BY name",name+'-stats')
 summary['records'].append({'scenario':run['scenario'],'iteration':run['iteration'],'pid':run['pid'],'trace_sha256':run['trace_sha256'],'slices':rows,'check_in_slices':sum(s['name']=='CG/main/check-in' for s in slices),'diagnostic_stats':stats})
(out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
