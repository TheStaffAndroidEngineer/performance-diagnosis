#!/usr/bin/env python3
"""Capture controlled Common Goods scenarios; no representative benchmark claim."""
from pathlib import Path
import argparse,subprocess,json,hashlib,time,datetime,os
ROOT=Path(__file__).resolve().parents[1]
PKG='staff.android.performance'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
p=argparse.ArgumentParser();p.add_argument('--adb',default=os.environ.get('ADB',str(Path.home()/'Library/Android/sdk/platform-tools/adb')));p.add_argument('--serial',default='emulator-5554');p.add_argument('--apk',type=Path,default=ROOT/'evidence/candidate1/artifacts/app-release.apk');p.add_argument('--out',type=Path,required=True);p.add_argument('--iterations',type=int,default=3);p.add_argument('--scenarios',nargs='+',default=['blocked','busy','repaired']);a=p.parse_args()
assert a.iterations>0
assert all(s in ['blocked','busy','repaired'] for s in a.scenarios)
a.out.mkdir(parents=True,exist_ok=False)
base=[a.adb,'-s',a.serial]
def adb(*args,check=True):
 r=subprocess.run(base+list(args),capture_output=True,text=True)
 if check and r.returncode:raise RuntimeError(r.stderr+r.stdout)
 return r.stdout+r.stderr
metadata={'date':datetime.datetime.now(datetime.timezone.utc).isoformat(),'apk':str(a.apk),'apk_sha256':sha(a.apk),'serial':a.serial,'device_getprop':adb('shell','getprop'),'battery':adb('shell','dumpsys','battery'),'thermal':adb('shell','dumpsys','thermalservice'),'perfetto_version':adb('shell','perfetto','--version'),'scenario_policy':'new app process each run; fixed 800ms local source; 90,000,000 checksum rounds; no representative emulator timing claim','warmup':'one untraced invocation per selected scenario before capture','compilation':'cmd package compile -f -m speed; recorded result; same installed optimized/profileable APK','iterations':a.iterations,'records':[]}
metadata['install']=adb('install','-r',str(a.apk))
installed=adb('shell','pm','path',PKG).strip().removeprefix('package:')
adb('pull',installed,str(a.out/'installed.apk'));metadata['installed_sha256']=sha(a.out/'installed.apk');assert metadata['installed_sha256']==metadata['apk_sha256']
metadata['compile']=adb('shell','cmd','package','compile','-f','-m','speed',PKG)
(a.out/'manifest.json').write_text(json.dumps(metadata,indent=2)+'\n')
config='''buffers { size_kb: 8192 fill_policy: RING_BUFFER }
duration_ms: 6000
data_sources { config { name: "linux.ftrace" ftrace_config {
 ftrace_events: "sched/sched_switch"
 ftrace_events: "sched/sched_waking"
 ftrace_events: "sched/sched_process_exit"
 ftrace_events: "task/task_newtask"
 ftrace_events: "binder/binder_transaction"
 ftrace_events: "binder/binder_transaction_received"
 atrace_categories: "am"
 atrace_categories: "view"
 atrace_categories: "dalvik"
 atrace_apps: "staff.android.performance"
} } }
data_sources { config { name: "linux.process_stats" process_stats_config { scan_all_processes_on_start: true } } }
'''
(a.out/'config.pbtxt').write_text(config)
adb('push',str(a.out/'config.pbtxt'),'/data/misc/perfetto-configs/cg-diagnosis.pbtxt')
for scenario in a.scenarios:
 adb('shell','am','force-stop',PKG)
 adb('shell','am','start','-W','-n',PKG+'/.MainActivity','--es','scenario',scenario)
 time.sleep(3)
for iteration in range(1,a.iterations+1):
 for scenario in a.scenarios:
  name=f'{scenario}-{iteration}';dest=a.out/name;dest.mkdir()
  adb('shell','am','force-stop',PKG)
  command=base+['shell','perfetto','--txt','-c','/data/misc/perfetto-configs/cg-diagnosis.pbtxt','-o','/data/misc/perfetto-traces/cg-diagnosis.pftrace']
  (dest/'attempt.json').write_text(json.dumps({'command':command,'scenario':scenario,'iteration':iteration},indent=2)+'\n')
  process=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
  time.sleep(.5)
  launch=adb('shell','am','start','-W','-n',PKG+'/.MainActivity','--es','scenario',scenario)
  pid=adb('shell','pidof',PKG).strip()
  output,_=process.communicate(timeout=15);(dest/'capture.log').write_text(output)
  assert process.returncode==0,output
  adb('pull','/data/misc/perfetto-traces/cg-diagnosis.pftrace',str(dest/'trace.pftrace'))
  logs=adb('logcat','-d','--pid='+pid,'-v','threadtime','CG_DIAG:I','*:S');(dest/'app.log').write_text(logs)
  (dest/'launch.txt').write_text(launch)
  assert f'scenario={scenario}' in logs,logs
  record={'scenario':scenario,'iteration':iteration,'pid':int(pid),'trace':str(dest/'trace.pftrace'),'trace_sha256':sha(dest/'trace.pftrace'),'app_log':str(dest/'app.log'),'app_log_sha256':sha(dest/'app.log'),'command':command}
  metadata['records'].append(record)
  (a.out/'manifest.json').write_text(json.dumps(metadata,indent=2)+'\n')
  print(name,'captured',flush=True)
metadata['completed_at']=datetime.datetime.now(datetime.timezone.utc).isoformat();metadata['thermal_after']=adb('shell','dumpsys','thermalservice');metadata['battery_after']=adb('shell','dumpsys','battery')
(a.out/'manifest.json').write_text(json.dumps(metadata,indent=2)+'\n')
