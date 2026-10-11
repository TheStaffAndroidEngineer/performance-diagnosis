#!/usr/bin/env python3
"""Capture an actual pending frame separately from stable XML observations."""
from pathlib import Path
from types import SimpleNamespace
import sys,json,time,hashlib,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'projects/commerce-app/tools'))
from capture_checkpoint_appearance import CaptureSession,bounds
p=ROOT/'projects/performance-diagnosis';out=p/'evidence/pending-screen';out.mkdir(exist_ok=False)
args=SimpleNamespace(package='staff.android.performance',output=out,serial='emulator-5554',settle_timeout=30,max_scrolls=8)
s=CaptureSession(args);apk=p/'evidence/candidate1/artifacts/app-release.apk'
s.adb('install','-r',apk)
s.adb('shell','am','force-stop',args.package)
s.adb('shell','am','start','-W','-n',args.package+'/.MainActivity','-f','0x10008000')
raw=s.settled();raw=s.tap('Save Camera',raw=raw)
# Seek the visible Refresh action, using the same finite viewport helper.
tree=ET.fromstring(raw);node=s.target(tree,'Refresh collection')
if node is None:
 from capture_checkpoint_appearance import panes,pane_key
 key=pane_key(panes(tree,args.package)[0]);_,raw=s.seek(key,'up',label='Refresh collection',raw=raw)
 node=s.target(ET.fromstring(raw),'Refresh collection')
assert node is not None
(out/'before.xml').write_text(raw)
x,y,r,b=bounds(node);started=time.time_ns()
s.adb('shell','input','tap',(x+r)//2,(y+b)//2)
time.sleep(.15)
(out/'pending.png').write_bytes(s.adb('exec-out','screencap','-p'));captured=time.time_ns()
final=s.settled(exact=['Collection refreshed','Saved Camera'])
(out/'completed.xml').write_text(final)
(out/'completed.png').write_bytes(s.adb('exec-out','screencap','-p'))
(out/'record.json').write_text(json.dumps({'apk_sha256':hashlib.sha256(apk.read_bytes()).hexdigest(),'action':'Save Camera first, then Refresh collection','action_start_host_ns':started,'pending_png_return_host_ns':captured,'scope':'Pending PNG is actual compositor image, independently inspected. before.xml precedes refresh; completed.xml follows completion. There is no claim those XMLs describe the pending frame or that host capture latency measures input responsiveness. Separate instrumented test checks Save action during pending refresh.','commands':s.commands,'tap_guards':s.tap_guards},indent=2)+'\n')
print('Captured pending and completed frames')
