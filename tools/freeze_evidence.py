#!/usr/bin/env python3
"""Freeze current source inputs and bind retained execution evidence; run once."""
from pathlib import Path
import hashlib,json,os,shutil,datetime,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'evidence/final-source'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert not OUT.exists(),'Existing source freeze must never be overwritten'
sources=[]
for directory,dirs,names in os.walk(ROOT):
 dirs[:]=[d for d in dirs if d not in ['evidence','build','.gradle','.kotlin','__pycache__','.git']]
 for name in names:
  p=Path(directory)/name
  if name in ['local.properties','verification.md','README.md'] or name.endswith('.log'):continue
  rel=p.relative_to(ROOT);copy=OUT/rel;copy.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,copy)
  sources.append({'path':str(rel),'snapshot':str(copy.relative_to(ROOT)),'sha256':sha(p)})
evidence=[]
for p in sorted((ROOT/'evidence').rglob('*')):
 if p.is_file() and 'final-source' not in p.parts and p.name!='runtime-freeze.json':
  evidence.append({'path':str(p.relative_to(ROOT)),'sha256':sha(p)})
candidate=json.loads((ROOT/'evidence/candidate1/manifest.json').read_text())
for rel,h in candidate['sources'].items():assert sha(ROOT/rel)==h,rel
for rel,h in candidate['artifacts'].items():assert sha(ROOT/rel)==h,rel
artifacts=[{'path':p,'sha256':h} for p,h in candidate['artifacts'].items()]
pending=ROOT/'evidence/pending-refresh-test/app-debug-androidTest.apk'
artifacts.append({'path':str(pending.relative_to(ROOT)),'sha256':sha(pending),'scope':'Separate one-case Android invocation against the unchanged candidate app; original four-case test APK retained above.'})
manifest={'date':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'FROZEN_FOR_INDEPENDENT_REVIEW','sources':sources,'artifacts':artifacts,'evidence_files':evidence,'scope':'Recorded raw evidence and final source identity. Individual reports establish test, trace, method-identity and native-appearance scopes separately; freezing is not a pass itself.'}
(ROOT/'evidence/runtime-freeze.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({'sources':len(sources),'evidence_files':len(evidence),'artifacts':len(artifacts)}))
