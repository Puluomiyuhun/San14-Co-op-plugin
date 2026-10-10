"""Actual loopback TLS only. No game, real Room, native or public listeners."""
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
import contextlib,hashlib,io,json,queue,socket,ssl,subprocess,sys,threading,time,unittest

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];PRIVATE=ROOT.parent/'mod_research'
import remote_link_probe as probe
from b_warm_adapter_key import Native
OUTPUT=None;ROWS=[]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


class Cases(unittest.TestCase):
    def setUp(self):
        self.folder=OUTPUT/self._testMethodName;self.folder.mkdir();self.owner=None
    def tearDown(self):
        if self.owner is not None:
            self.owner.close();r=self.owner.report()
            self.assertTrue(r['closed']);self.assertEqual(r['active_connections'],0)
            self.assertEqual(r['listener_threads_alive'],0);self.assertEqual(r['worker_threads_alive'],0)
    def start(self,**kw):
        self.owner=probe.serve(bind='127.0.0.1',advertise='127.0.0.1',control_port=0,download_port=0,
            output=self.folder/'private-host',lifetime=kw.pop('lifetime',30),timeout=kw.pop('timeout',.5),**kw)
        return self.owner
    def evidence(self,**row):ROWS.append(dict(case=self._testMethodName,**row))

    def test_both_paths_actual_tls_nonces_and_private_credentials(self):
        host=self.start();invite=probe.read_invitation(host.folder/'invite.json');report=probe.check(invite,timeout=1)
        self.assertEqual(report['result'],'PASS_NETWORK_BOTH_PATHS')
        self.assertTrue(all(x['certificate_pinned'] and x['nonce_roundtrip'] for x in report['channels']))
        host.close();counts=host.report()['channels'];self.assertEqual([counts[c]['completed'] for c in probe.CHANNELS],[1,1])
        private=Native()
        for name in ('probe-key.pem','probe-cert.pem','invite.json'):
            handle=private.k.CreateFileW(private.path(host.folder/name),0x80000000|0x20000,1,None,3,0x80|0x200000,None)
            try:private.file_check(handle);private.acl(handle)
            finally:private.k.CloseHandle(handle)
        self.assertNotIn(invite['token'],json.dumps(report));self.assertNotIn(invite['token'],(host.folder/'host-report.json').read_text())
        self.assertFalse(report['two_games']);self.assertFalse(report['room_joined']);self.evidence(client=report,host=host.report(),private_acl_verified=True)

    def test_wrong_fingerprint_refused_before_authentication_proof(self):
        host=self.start();invite=deepcopy(host.invitation);invite['fingerprint']='0'*64
        with patch.object(host,'_response',wraps=host._response) as response:
            report=probe.check(invite,timeout=.5);host.close();self.assertEqual(response.call_count,0)
        self.assertTrue(all(row['stage']=='fingerprint' for row in report['channels']))
        self.assertNotIn(host.invitation['token'],json.dumps(report));self.evidence(client=report,proofs_sent=0)

    def test_swapped_ports_and_wrong_token_cannot_pass(self):
        host=self.start();invite=deepcopy(host.invitation);invite['ports']={c:host.invitation['ports'][probe.CHANNELS[1-i]] for i,c in enumerate(probe.CHANNELS)}
        swapped=probe.check(invite,timeout=.5);self.assertEqual(swapped['result'],'FAIL_NETWORK_PATHS')
        wrong=deepcopy(host.invitation);wrong['token']='0'*64
        denied=probe.check(wrong,timeout=.5);self.assertEqual(denied['result'],'FAIL_NETWORK_PATHS')
        host.close();self.assertEqual(sum(x['completed'] for x in host.report()['channels'].values()),0)
        self.evidence(swapped_ports=swapped,wrong_token=denied)

    def test_closed_port_fails_only_that_path_and_real_other_path_passes(self):
        host=self.start();invite=deepcopy(host.invitation)
        occupied=socket.socket();occupied.bind(('127.0.0.1',0))
        try:
            invite['ports']['download']=occupied.getsockname()[1]
            report=probe.check(invite,timeout=.3)
        finally:occupied.close()
        self.assertEqual(report['channels'][0]['result'],'PASS');self.assertEqual(report['channels'][1]['stage'],'connect')
        self.assertEqual(report['result'],'FAIL_NETWORK_PATHS');self.evidence(client=report)

    def test_authenticated_wrong_nonce_response_rejected(self):
        host=self.start();original=host._response
        def wrong(channel,request):
            result=original(channel,request);row={k:v for k,v in result.items() if k!='proof'};row['client_nonce']='f'*64
            return probe._signed(host.invitation['token'],'challenge',row)
        with patch.object(host,'_response',side_effect=wrong):report=probe.check(host.invitation,timeout=.5)
        self.assertEqual(report['result'],'FAIL_NETWORK_PATHS');self.assertTrue(all(r['stage']=='challenge' for r in report['channels']))
        self.evidence(client=report,valid_mac_wrong_nonce_refused=True)

    def test_slow_response_timeout_and_close_interrupts_pending_tls_read(self):
        host=self.start(timeout=.3);original=host._response
        def slow(channel,request):time.sleep(.25);return original(channel,request)
        started=time.monotonic()
        with patch.object(host,'_response',side_effect=slow):report=probe.check(host.invitation,timeout=.1)
        self.assertLess(time.monotonic()-started,2);self.assertTrue(all(r['error_type']=='TimeoutError' for r in report['channels']))
        raw=socket.create_connection(('127.0.0.1',host.invitation['ports']['control']),timeout=1)
        context=ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT);context.check_hostname=False;context.verify_mode=ssl.CERT_NONE
        idle=context.wrap_socket(raw,server_hostname='127.0.0.1')
        idle.sendall(b'{"schema":');started=time.monotonic();host.close();elapsed=time.monotonic()-started;idle.close()
        self.assertLess(elapsed,2);self.assertTrue(json.loads((host.folder/'host-report.json').read_text())['cleanup_complete'])
        self.evidence(client=report,close_ms=round(elapsed*1000),host=host.report())

    def test_expiry_automatically_closes_both_listeners(self):
        host=self.start(lifetime=1);self.assertTrue(host.closed.wait(3))
        for port in host.invitation['ports'].values():
            with self.assertRaises(OSError):socket.create_connection(('127.0.0.1',port),timeout=.2)
        with self.assertRaisesRegex(ValueError,'expired'):probe.check(host.invitation,timeout=.2)
        self.evidence(host=host.report(),expired_invitation_refused=True)

    def test_default_help_and_real_room_invitation_have_no_network(self):
        with patch.object(socket,'socket',side_effect=AssertionError('No listener')), \
             patch.object(socket,'create_connection',side_effect=AssertionError('No connection')), \
             contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(probe.main([]),0)
            with self.assertRaisesRegex(ValueError,'Independent diagnostic'):probe.check({'schema':'san14.observed-room-invite.v1','token':'not diagnostic'})
        self.assertIn('serve',output.getvalue());self.evidence(network_opened=False)

    def test_client_only_isolated_without_cryptography_or_runtime_packages(self):
        host=self.start();code='''import importlib.abc,json,runpy,sys
class Refuse(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  if fullname.split('.')[0] in ('cryptography','pefile','capstone','unicorn','room_session','room_transport'):
   raise AssertionError('Unexpected dependency: '+fullname)
sys.meta_path.insert(0,Refuse());script=sys.argv[1];sys.argv=sys.argv[1:];runpy.run_path(script,run_name='__main__')
'''
        child=subprocess.run([sys.executable,'-I','-S','-B','-c',code,str(HERE/'remote_link_probe.py'),'check','--invite',str(host.folder/'invite.json'),'--timeout','1'],
            capture_output=True,text=True,timeout=10,cwd=self.folder)
        self.assertEqual(child.returncode,0,child.stdout+child.stderr);report=json.loads(child.stdout)
        self.assertEqual(report['result'],'PASS_NETWORK_BOTH_PATHS');self.assertNotIn(host.invitation['token'],child.stdout)
        self.evidence(client=report,client_only_stdlib=True,actual_child_process=True)

    def test_standalone_cli_serve_then_isolated_cli_check(self):
        folder=self.folder/'standalone-private';lines=queue.Queue()
        host=subprocess.Popen([sys.executable,'-B',str(HERE/'remote_link_probe.py'),'serve',
            '--bind','127.0.0.1','--advertise','127.0.0.1','--control-port','0','--download-port','0',
            '--output',str(folder),'--lifetime','3','--timeout','.5'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,
            text=True,cwd=self.folder,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        reader=threading.Thread(target=lambda:lines.put(host.stdout.readline()),daemon=True);reader.start()
        try:
            first=lines.get(timeout=5);opened=json.loads(first);self.assertEqual(opened['event'],'DIAGNOSTIC_LISTENING')
            client=subprocess.run([sys.executable,'-I','-S','-B',str(HERE/'remote_link_probe.py'),'check',
                '--invite',str(folder/'invite.json'),'--timeout','1'],capture_output=True,text=True,timeout=5,cwd=self.folder)
            self.assertEqual(client.returncode,0,client.stdout+client.stderr);result=json.loads(client.stdout)
            self.assertEqual(result['result'],'PASS_NETWORK_BOTH_PATHS')
            rest,error=host.communicate(timeout=6);self.assertEqual(host.returncode,0,error)
            final=json.loads(rest);self.assertTrue(final['closed']);self.assertEqual(final['active_connections'],0)
            self.assertEqual([final['channels'][c]['completed'] for c in probe.CHANNELS],[1,1])
            self.assertNotIn(probe._json((folder/'invite.json').read_bytes())['token'],first+rest+error+client.stdout)
            self.evidence(actual_standalone_serve=True,actual_isolated_check=True,client=result,host=final)
        finally:
            if host.poll() is None:host.terminate();host.communicate(timeout=3)
            reader.join(1)


if __name__=='__main__':
    OUTPUT=PRIVATE/'remote_link_probe_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');OUTPUT.mkdir(parents=True)
    sources={str(HERE/n):sha(HERE/n) for n in ('remote_link_probe.py','remote_link_probe_test.py','b_warm_adapter_key.py')}
    stream=io.StringIO();r=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Cases))
    unchanged=all(sha(p)==h for p,h in sources.items());(OUTPUT/'test.log').write_text(stream.getvalue(),encoding='utf-8');print(stream.getvalue())
    result=dict(result='PASS' if r.wasSuccessful() and unchanged else 'FAIL',tests=r.testsRun,sources=sources,inputs_unchanged=unchanged,cases=ROWS,
        actual_loopback_TLS=True,public_listener_opened=False,firewall_modified=False,**probe.FLAGS,
        failures=[(str(t),s) for t,s in r.failures+r.errors])
    # These are private test artifacts, including disposable diagnostic keys;
    # only hashes and sanitized case summaries belong in shared evidence.
    result['artifacts']={str(p):sha(p) for p in OUTPUT.rglob('*') if p.is_file()}
    path=OUTPUT/'result.json';path.write_text(json.dumps(result,indent=2)+'\n');print(path);raise SystemExit(result['result']!='PASS')
