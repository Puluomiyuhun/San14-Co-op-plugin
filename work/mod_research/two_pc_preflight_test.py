from pathlib import Path
from datetime import datetime
import sys,json,hashlib,subprocess,time,unittest,base64,shutil
P=Path(__file__).resolve().parent;PACKAGE=P.parents[1]/'outputs'/'two_pc_preflight';sys.path.insert(0,str(PACKAGE))
import two_pc_preflight as pf
RUN=P/'two_pc_preflight_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');RUN.mkdir(parents=True)
class Cases(unittest.TestCase):
 def setUp(self):
  self.manifest=json.loads((PACKAGE/'catalog.json').read_text(encoding='utf-8'));self.room=pf.PreflightRoom(self.manifest,b'x'*70001)
 def bound(self):
  r=self.room;r.authenticate(dict(method='host',credential=r.host_token,profile=self.manifest['profile']),'a');r.authenticate(dict(method='join',credential=r.invite,profile=self.manifest['profile']),'b')
  for p,c,f in [('A','a',12),('B','b',2)]:self.assertTrue(r.handle(p,c,dict(action='select_force',force_id=f,expected_revision=r.revision,request_id=pf.secrets.token_hex(16)))['ok'])
  for p,c in [('A','a'),('B','b')]:self.assertTrue(r.handle(p,c,dict(action='confirm_force',expected_revision=r.revision,request_id=pf.secrets.token_hex(16)))['ok'])
  return r
 def offer(self):
  r=self.bound();o=r.handle('B','b',{'action':'preflight_offer'});self.assertTrue(o['ok']);return r,o
 def test_ip_limits(self):
  for ip in ['127.0.0.1','192.168.3.2','100.101.102.103']:self.assertEqual(pf.private_ip(ip),ip)
  for ip in ['0.0.0.0','8.8.8.8','::1']:
   with self.assertRaises(pf.RoomError):pf.private_ip(ip)
 def test_version_actual_file(self):
  f=RUN/'fake-exe.bin';f.write_bytes(b'not a game');profile=dict(self.manifest['profile'],game_sha256=pf.sha(f.read_bytes()))
  self.assertEqual(pf.version_check(f,profile)['status'],'EXACT_SHA256_MATCH')
  with self.assertRaises(pf.RoomError):pf.version_check(f,self.manifest['profile'])
  self.assertEqual(pf.version_check(None,profile)['status'],'NOT_CHECKED')
 def test_profile_rejected(self):
  with self.assertRaises(pf.RoomError):self.room.authenticate(dict(method='join',credential=self.room.invite,profile={}), 'bad')
 def test_duplicate_force(self):
  r=self.bound();self.assertNotEqual(r.bindings['A']['force_id'],r.bindings['B']['force_id']);self.assertFalse(r.handle('B','b',dict(action='select_force',force_id=12,request_id='x',expected_revision=r.revision))['ok'])
 def test_no_native_start(self):
  r=self.bound();self.assertFalse(r.handle('A','a',dict(action='start_game',request_id='x'))['ok']);self.assertFalse(r.view('B')['native_gameplay_enabled'])
 def test_download_restrict_and_single_issue(self):
  r=self.bound();self.assertFalse(r.handle('A','a',dict(action='preflight_offer'))['ok']);self.assertTrue(r.handle('B','b',dict(action='preflight_offer'))['ok']);self.assertFalse(r.handle('B','b',dict(action='preflight_offer'))['ok'])
 def test_ticket_once_and_expiry(self):
  r,o=self.offer();g=dict(method='preflight_download',credential=o['download_token'],profile=self.manifest['profile']);r.authenticate(g,'download')
  with self.assertRaises(pf.RoomError):r.authenticate(g,'again')
  r.channels['download']=time.monotonic()-1;self.assertFalse(r.handle('PREFLIGHT_DOWNLOAD','download',dict(action='preflight_chunk',checkpoint_id=o['checkpoint_id'],part='world.s14',index=0))['ok'])
 def test_disconnect_invalidates(self):
  r,o=self.offer();r.disconnect('B','b')
  with self.assertRaises((pf.RoomError,pf.SyncError)):r.authenticate(dict(method='preflight_download',credential=o['download_token'],profile=self.manifest['profile']),'down')
 def test_bytes_corruption_and_incomplete(self):
  r,o=self.offer();m=o['manifest'];recv=pf.CheckpointReceiver(m,o['checkpoint_id'],o['scope'],m['epoch'],m['period'],m['cut'])
  chunks=list(r.package.chunks())
  with self.assertRaises(pf.SyncError):recv.verified_parts()
  for c in chunks:
   if c['part']=='world.s14' and c['index']==0:c=dict(c,data=base64.b64encode(b'Z'*32768).decode())
   recv.accept(c)
  with self.assertRaises(pf.SyncError):recv.verified_parts()
 def test_foreign_checkpoint_and_fake_completion(self):
  r,o=self.offer();self.assertFalse(r.handle('B','b',dict(action='preflight_received',checkpoint_id='0'*64,payload_sha256=pf.sha(r.sample),version_check='NOT_CHECKED'))['ok']);self.assertIsNone(r.done)
 def test_real_two_cli_processes_loopback(self):
  target=RUN/'cli';target.mkdir();portable=target/'relocated-package';portable.mkdir()
  for f in PACKAGE.iterdir():
   if f.is_file() and f.suffix in ('.py','.json'):shutil.copyfile(f,portable/f.name)
  hostlog=(target/'host.log').open('wb');guestlog=(target/'guest.log').open('wb')
  host=subprocess.Popen([sys.executable,str(portable/'two_pc_preflight.py'),'host','--bind','127.0.0.1','--port','0','--timeout','30','--sample-kib','129','--output',str(target)],stdout=hostlog,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
  guest=None
  try:
   deadline=time.monotonic()+10;invites=[]
   while not invites and time.monotonic()<deadline:
    invites=list(target.glob('host-*/invite.json'));time.sleep(.05)
   self.assertTrue(invites)
   invitation=json.loads(invites[0].read_text(encoding='utf-8'))
   with self.assertRaises(pf.RoomError):pf.Client(invitation['host'],invitation['port'],'0'*64,dict(method='join',credential=invitation['invite'],profile=invitation['profile']))
   guest=subprocess.Popen([sys.executable,str(portable/'two_pc_preflight.py'),'guest','--invite',str(invites[0]),'--timeout','30','--output',str(target)],stdout=guestlog,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
   self.assertEqual(guest.wait(20),0);self.assertEqual(host.wait(10),0)
   reports=[json.loads(x.read_text(encoding='utf-8')) for x in target.glob('*/report.json')];self.assertEqual(len(reports),2)
   for r in reports:self.assertEqual(r['result'],'NETWORK_BYTES_PASS_WAITING_NATIVE_BACKEND');self.assertFalse(r['native_backend_connected']);self.assertFalse(r['two_computers_proven']);self.assertTrue(r['same_computer_loopback'])
   a=next(r for r in reports if r['role']=='A');b=next(r for r in reports if r['role']=='B');self.assertEqual(a['guest_report']['payload_sha256'],b['payload_sha256']);self.assertEqual(b['payload_bytes'],129*1024)
  finally:
   for proc in [host,guest]:
    if proc and proc.poll() is None:proc.terminate();proc.wait(5)
   hostlog.close();guestlog.close()
if __name__=='__main__':
 before={f.name:pf.file_hash(f) for f in PACKAGE.iterdir() if f.suffix in ('.py','.json')}
 with (RUN/'tests.txt').open('w',encoding='utf-8') as stream:result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Cases))
 evidence=dict(result='PASS' if result.wasSuccessful() else 'FAIL',tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),source_sha256=before,sources_unchanged=before=={n:pf.file_hash(PACKAGE/n) for n in before},real_local_processes=2,two_computers_tested=False,game_access=False,network_configuration_changed=False,native_backend_connected=False)
 (RUN/'result.json').write_text(json.dumps(evidence,indent=2)+'\n');print(json.dumps(dict(evidence,path=str(RUN/'result.json'))));raise SystemExit(not result.wasSuccessful())
