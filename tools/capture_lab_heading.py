#!/usr/bin/env python3
"""Supplement the font-2 Lab review with small, observed viewport steps."""
from pathlib import Path
from types import SimpleNamespace
import sys,json,hashlib,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'projects/commerce-app/tools'))
from capture_checkpoint_appearance import CaptureSession,bounds,panes,pane_key
p=ROOT/'projects/performance-diagnosis';out=p/'evidence/native-appearance/lab-large-heading';out.mkdir(exist_ok=False)
args=SimpleNamespace(package='staff.android.performance',output=out,serial='emulator-5554',settle_timeout=30,max_scrolls=8)
s=CaptureSession(args);original=s.settings();result={'status':'CAPTURING','originalSettings':original}
try:
 s.adb('shell','settings','put','system','font_scale','2.0')
 s.adb('shell','cmd','uimode','night','no')
 s.adb('shell','am','force-stop',args.package)
 s.adb('shell','am','start','-W','-n',args.package+'/.MainActivity','-f','0x10008000')
 raw=s.tap('Lab controls')
 key=pane_key(panes(ET.fromstring(raw),args.package)[0]);_,raw=s.seek(key,'up',raw=raw)
 for step in range(12):
  tree=ET.fromstring(raw);pane=panes(tree,args.package)[0];x,y,right,bottom=bounds(pane)
  heading=next((n for n in tree.iter('node') if n.get('text')=='Controlled investigation'),None)
  para=next((n for n in tree.iter('node') if n.get('text','').startswith('Local two-product fixture')),None)
  if heading is not None and para is not None and bounds(heading)[1]>y+60 and bounds(para)[3]<bottom-60:
   result.update(status='CAPTURED_NOT_REVIEWED',frame=s.capture('large-heading',raw),appliedSettings=s.settings(),steps=step)
   break
  s.adb('shell','input','swipe',(x+right)//2,y+(bottom-y)*3//5,(x+right)//2,y+(bottom-y)*2//5,650)
  raw=s.settled()
 else: raise RuntimeError('Heading and paragraph did not fit together in bounded small-step scan')
 result['apkSha256']=hashlib.sha256((p/'evidence/candidate1/artifacts/app-release.apk').read_bytes()).hexdigest()
finally:
 s.adb('shell','settings','put','system','font_scale',original['font'])
 s.adb('shell','cmd','uimode','night','yes' if 'yes' in original['night'] else 'no')
 s.adb('shell','am','force-stop',args.package)
 s.adb('shell','am','start','-W','-n',args.package+'/.MainActivity','-f','0x10008000')
 result.update(restoredSettings=s.settings(),commands=s.commands,tapGuards=s.tap_guards)
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print(result['status'])
