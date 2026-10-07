from pathlib import Path
from datetime import datetime
import hashlib,json,os,shutil,subprocess,sys,time
P=Path(__file__).resolve().parent;ROOT=P.parents[1];SOURCE=ROOT/'outputs'/'two_pc_preflight';EXE=P/'dist'/'SAN14-Connection-Preflight.exe'
RUN=P/'runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');RUN.mkdir(parents=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
package=RUN/'relocated with spaces';package.mkdir();exe=package/EXE.name;shutil.copyfile(EXE,exe);shutil.copyfile(SOURCE/'catalog.json',package/'catalog.json')
# No Python executable or site packages from PATH are available to frozen children.
env=dict(os.environ,PATH='',PYTHONPATH='',PYTHONHOME='')
def launch(args,log):return subprocess.Popen([str(exe),*args],cwd=RUN,stdout=log,stderr=subprocess.STDOUT,env=env,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
host=guest=None;rows=[]
with (RUN/'host.stdout.txt').open('wb') as outA,(RUN/'guest.stdout.txt').open('wb') as outB:
 try:
  host=launch(['host','--bind','127.0.0.1','--port','0','--sample-kib','129','--timeout','45'],outA)
  deadline=time.monotonic()+15;invitations=[]
  while time.monotonic()<deadline and not invitations:
   invitations=list((package/'runs').glob('host-*/invite.json'))
   if host.poll() is not None:raise AssertionError('Frozen host exited before invite')
   time.sleep(.05)
  assert invitations,'No invitation beside EXE'
  invitation=json.loads(invitations[0].read_text(encoding='utf-8'));bad=dict(invitation,fingerprint='0'*64);badpath=RUN/'wrong-pin-invite.json';badpath.write_text(json.dumps(bad),encoding='utf-8')
  with (RUN/'wrong-pin.stdout.txt').open('wb') as log:
   rejected=launch(['guest','--invite',str(badpath),'--timeout','10'],log);assert rejected.wait(15)==1
  rows.append('actual frozen client rejects wrong TLS certificate pin')
  guest=launch(['guest','--invite',str(invitations[0]),'--timeout','30'],outB)
  assert guest.wait(25)==0,'Frozen guest failed';assert host.wait(10)==0,'Frozen host failed'
  reports=[json.loads(f.read_text(encoding='utf-8')) for f in (package/'runs').glob('*/report.json')]
  assert len(reports)==2,reports
  a=next(x for x in reports if x['role']=='A');b=next(x for x in reports if x['role']=='B')
  assert b['payload_bytes']==129*1024 and b['payload_sha256']==a['guest_report']['payload_sha256']
  assert all(r['result']=='NETWORK_BYTES_PASS_WAITING_NATIVE_BACKEND' and not r['native_backend_connected'] and not r['two_computers_proven'] for r in reports)
  disk=next((package/'runs').glob('guest-*/received-diagnostic.bin'));assert sha(disk)==b['payload_sha256']
  assert invitations[0].is_relative_to(package) and len(list((package/'runs').glob('host-*/private-tls/room-key.pem')))==1
  assert not (RUN/'runs').exists(),'Output must not go to CWD'
  rows+=['two independent relocated frozen processes with empty PATH complete TLS/faction/129KiB transfer','written payload SHA256 exactly matches offer/host','invitation/private certificate/report files stay beside EXE, not CWD or transient extraction','game version omitted is NOT_CHECKED and native readiness false']
  assert a['version_check']['status']==b['version_check']['status']=='NOT_CHECKED'
  # External catalog is fixed by wrapper hash; refuse altered profile before listening.
  tampered=RUN/'tampered';tampered.mkdir();shutil.copyfile(EXE,tampered/EXE.name);(tampered/'catalog.json').write_bytes((SOURCE/'catalog.json').read_bytes()+b' ')
  rejected=subprocess.run([str(tampered/EXE.name),'host','--bind','127.0.0.1','--port','0','--timeout','10'],env=env,cwd=RUN,capture_output=True,timeout=15)
  (RUN/'tampered-catalog.stdout.txt').write_bytes(rejected.stdout);assert rejected.returncode==1 and not (tampered/'runs').exists()
  rows.append('modified external catalog rejected before any run output/listener')
 finally:
  for process in (guest,host):
   if process and process.poll() is None:process.terminate();process.wait(5)
result=dict(result='PASS',checks=rows,source_exe_sha256=sha(EXE),wrapper_sha256=sha(P/'two_pc_preflight_portable_entry.py'),catalog_sha256=sha(SOURCE/'catalog.json'),frozen_processes_independent=True,path_empty_in_children=True,python_invoked_by_children=False,two_computers_tested=False,game_access=False,network_settings_changed=False,native_backend_connected=False)
(RUN/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(result_path=str(RUN/'result.json'),**result)))
