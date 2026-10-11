#!/usr/bin/env python3
"""Capture a separate debug ART method identity witness; not a timing benchmark."""
from pathlib import Path
import argparse,subprocess,time,json,hashlib,datetime,struct,os
ROOT=Path(__file__).resolve().parents[1];PKG='staff.android.performance'
p=argparse.ArgumentParser();p.add_argument('--apk',type=Path,default=ROOT/'app/build/outputs/apk/debug/app-debug.apk');p.add_argument('--out',type=Path,required=True);p.add_argument('--serial',default='emulator-5554');p.add_argument('--adb',default=os.environ.get('ADB',str(Path.home()/'Library/Android/sdk/platform-tools/adb')));a=p.parse_args()
a.out.mkdir(parents=True,exist_ok=False);base=[a.adb,'-s',a.serial];commands=[]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(*args):
 started=datetime.datetime.now(datetime.timezone.utc).isoformat();r=subprocess.run(base+list(args),capture_output=True,text=True)
 commands.append({'started_at':started,'ended_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'argv':base+list(args),'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr})
 (a.out/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
 if r.returncode:raise RuntimeError(r.stdout+r.stderr)
 return r.stdout
try:
 run('install','-r',str(a.apk))
 package=run('shell','dumpsys','package',PKG);(a.out/'package.txt').write_text(package)
 assert 'DEBUGGABLE' in package,'Use the documented debug diagnostic variant'
 installed=run('shell','pm','path',PKG).strip().removeprefix('package:')
 run('pull',installed,str(a.out/'installed.apk'));assert sha(a.out/'installed.apk')==sha(a.apk)
 run('shell','am','force-stop',PKG)
 run('shell','am','start','--start-profiler','/data/local/tmp/cg-method.trace','--sampling','1000','--clock-type','dual','-n',PKG+'/.MainActivity','-f','0x10008000','--es','scenario','busy')
 time.sleep(15)
 run('shell','am','profile','stop',PKG)
 previous=-1;stable=0
 for _ in range(30):
  size=int(run('shell','stat','-c','%s','/data/local/tmp/cg-method.trace').strip())
  stable=stable+1 if size==previous and size>0 else 0
  if stable>=3:break
  previous=size;time.sleep(.3)
 assert stable>=3,'Profiler output did not finish flushing'
 run('pull','/data/local/tmp/cg-method.trace',str(a.out/'methods.trace'))
 pid=run('shell','pidof',PKG).strip()
 (a.out/'app.log').write_text(run('logcat','-d','--pid='+pid,'-v','threadtime','CG_DIAG:I','*:S'))
 b=(a.out/'methods.trace').read_bytes();end=b.index(b'*end\n')+5;header=b[:end].decode();binary=b[end:]
 assert 'data-file-overflow=false' in header
 method=next(line for line in header.splitlines() if 'staff.android.performance.catalog.CpuWork\tchecksum\t' in line)
 mid=int(method.split('\t')[0],16);main=int(next(line for line in header.splitlines() if line.endswith('\tmain')).split('\t')[0])
 assert binary[:4]==b'SLOW'
 version,offset=struct.unpack_from('<HH',binary,4);size=struct.unpack_from('<H',binary,16)[0]
 assert version==3 and size==14,'New profiler format needs a reviewed decoder'
 events=[]
 for offset in range(offset,len(binary),size):
  chunk=binary[offset:offset+size];assert len(chunk)==size
  tid,method_id,cpu,wall=struct.unpack('<HIII',chunk)
  if tid==main and method_id&~3==mid:events.append({'action':method_id&3,'thread_clock_raw':cpu,'wall_clock_raw':wall})
 assert {row['action'] for row in events}>={0,1},'Busy method was not captured completely'
 (a.out/'identity.json').write_text(json.dumps({'status':'PASS_METHOD_IDENTITY_ONLY','apk_sha256':sha(a.apk),'trace_sha256':sha(a.out/'methods.trace'),'pid':pid,'method':method,'main_thread_id':main,'events':events,'scope':'Separate debug ART sampled method identity. No method-event count as sample count, percentage attribution or comparison with release timing.'},indent=2)+'\n')
 print('Captured checksum method on the main thread; identity evidence only')
except Exception as error:
 (a.out/'failure.json').write_text(json.dumps({'error':str(error),'status':'FAILED_OR_INCOMPLETE'},indent=2)+'\n');raise
