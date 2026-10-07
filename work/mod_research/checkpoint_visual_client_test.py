"""Client fault injection plus optional real helper against our own child window.

No target discovery, game access, injection, capture, or activation. The only real
target is the exact HWND returned by a fixture launched by this test.
"""
from dataclasses import replace
from datetime import datetime
import hashlib
import json
from pathlib import Path
import queue
import sys
import tempfile
import threading
import time
import unittest

HERE=Path(__file__).resolve().parent
OUTPUT=HERE.parents[1]/'outputs'/'san14-link'
sys.path.insert(0,str(OUTPUT))
from checkpoint_visual_client import *
from checkpoint_visual_client_bridge import *
from authoritative_sync import (scope_from_room,PeriodCoordinator,CheckpointPackage,
                                CheckpointReceiver,digest,canonical)
from checkpoint_journal import CheckpointJournal
from checkpoint_presentation import MapWaitGate
from test_authoritative_sync import bound_room,NODE,NEXT,OLD,HOST


SESSION='1'*32
BINDING=TargetBinding(1200,1201,1202,'SyntheticWindow','b'*32,'e'*32,'borderless')


class FakeTransport:
    pid=4000
    def __init__(self):
        self.q=queue.Queue();self.sent=[];self.phase='NEW';self.session='';self.closed=False
        self.hwnd=0;self.retained=False;self.visible=False;self.intercept=None;self.last=None
        self.q.put({**self.base(''), 'event':'READY_NO_TARGET'})
    def base(self,rid):
        return dict(id=rid,session=self.session,ok=True,phase=self.phase,error='',hold_reason='',
                    surface='f'*32,cover_window_visible=self.visible,old_pixels_retained=self.retained,
                    target_binding_lost=False,input_gate_provided=False,
                    physical_monitor_unoccluded_proved=False,native_load_requested=False,
                    gameplay_authorized=False,helper_pid=str(self.pid),helper_birth='4001',
                    cover_class='CheckpointMapWaitHelper',cover_hwnd=str(self.hwnd),cover_activations='0')
    def send(self,value):
        self.sent.append(dict(value));op=value['op'];self.session=value['session'];extra={}
        if op=='bind':self.phase='BOUND';self.binding=value
        elif op=='cover':
            self.phase='COVERED';self.hwnd=4100;self.retained=True;self.visible=True
            extra=dict(old_attachment=self.binding['attachment'],view=self.binding['view'],old_frame='d'*32,
                       old_frame_sha256='a'*64,old_capture_time='100',cover_capture_time='200',
                       cover_observation='OWN_WGC_FRAME_ONLY')
        elif op=='prepare':
            self.phase='PREPARED';self.new=value['new_attachment']
            extra=dict(new_attachment=self.new,view=self.binding['view'],prepared_token='6'*32,
                       new_frame='7'*32,new_frame_sha256='8'*64,capture_time='400',minimum_frame_time='300',
                       world_attribution='CALLER_ASSERTION_ONLY')
        elif op=='reveal':
            self.phase='REVEALED';self.visible=False
            extra=dict(new_attachment=self.new,new_frame='7'*32,prepared_token='6'*32,
                       new_cover_capture_time='600',minimum_frame_time='500',image_release_confirmed=True)
        elif op=='hold':self.phase='HELD';extra=dict(hold_reason=value['message'])
        elif op=='force_stop':self.closed=True;extra=dict(cover_loss_explicit=True)
        elif op=='stop':self.closed=True
        elif op not in ('ping','status'):raise AssertionError(op)
        response={**self.base(value['id']),**extra};self.last=response
        if self.intercept:response=self.intercept(op,response)
        if response is not None:self.q.put(response)
    def receive(self,timeout):
        try:return self.q.get(timeout=timeout)
        except queue.Empty:
            if self.closed:raise TransportEOF('fake EOF')
            raise
    def held(self):
        self.phase='HELD';self.q.put({**self.base(''),'event':'HELD','ok':False,'hold_reason':'TEST_HELD'})
    def close_input(self):self.closed=True
    def wait(self,timeout):
        if not self.closed:raise TimeoutError('still alive')
        return 0
    def terminate(self):self.closed=True


def wait_fault(client):
    until=time.monotonic()+1
    while not client.fault and time.monotonic()<until:time.sleep(.005)
    assert client.fault


def fixture_evidence(request):
    return NativeVisualEvidence(request,'FIXTURE_ONLY',True,True,True,
        request.attachment,request.view,request.viewer_force,request.world_sha256 or '0'*64,
        ('A','B'),request.epoch,1,1,request.frame_time+10,time.monotonic_ns())


class GateFixture:
    def __init__(self,folder):
        scope=scope_from_room(bound_room())
        self.c=PeriodCoordinator(scope,'fixture-map.v1',digest(OLD),{'A':'a'*32,'B':'b'*32},NODE)
        for player in ('A','B'):self.c.set_ready(player,self.c.epoch,True)
        self.c.begin_simulation(self.c.seal_inputs())
        cut={k:self.c.seal[k] for k in ('sequence','prefix_sha256')}
        p=CheckpointPackage(scope,self.c.epoch,1,cut,NEXT,self.c.state_contract,digest(HOST),
            {'world.s14':canonical(HOST),'adapter.json':b'{"fixture":true}'},source_player='A')
        self.c.offer_checkpoint('A',p.manifest)
        receiver=CheckpointReceiver(p.manifest,p.checkpoint_id,scope,self.c.epoch,1,cut)
        for chunk in p.chunks():receiver.accept(chunk)
        self.j=CheckpointJournal(Path(folder)/'checkpoint.sqlite',scope,p.manifest,p.checkpoint_id,
                                 self.c.epoch,1,cut,self.c.attachments,create=True)
        self.j.stage(receiver);self.c.received('B',self.c.epoch,receiver)
        self.g=MapWaitGate(self.c,self.j)
        self.host={'attachment':'a'*32,'world_sha256':digest(HOST),'node':NEXT}
        self.old={'attachment':'b'*32,'viewer_force':2,'safe_boundary':True}
        self.new={**self.old,'attachment':'c'*32,'world_sha256':digest(HOST),'node':NEXT}
    def restore(self):
        permit=self.g.reserve_load(self.host,self.old)
        self.j.complete({'player':'B','epoch':self.g.identity['manifest']['epoch'],
            'checkpoint_id':self.g.identity['checkpoint_id'],'intent':permit['intent'],
            'world_sha256':digest(HOST),'viewer_force':2,'attachment':'c'*32,'host_observation':self.host})
        self.g.world_restored(self.host,self.new)


class ClientTests(unittest.TestCase):
    def setUp(self):
        self.t=FakeTransport();self.v=VisualClient(self.t,session=SESSION,timeout=.3)
        self.addCleanup(self.close)
    def close(self):
        if not self.v._closed:self.v.terminate_helper(accept_cover_loss=True)
    def covered(self):self.v.bind(BINDING);return self.v.cover()
    def prepared(self):self.covered();return self.v.prepare(new_attachment='c'*32,after_time=200)
    def gate(self):
        tmp=tempfile.TemporaryDirectory(prefix='checkpoint_visual_client_',dir=HERE)
        self.addCleanup(tmp.cleanup)
        return GateFixture(tmp.name)
    def test_normal_typed_receipts_and_acknowledged_stop_eof(self):
        prepared=self.prepared();released=self.v.reveal(prepared,controller_grant='9'*32)
        self.assertIsInstance(released,RevealReceipt)
        self.assertTrue(self.v.cleanup()['helper_exited'])
        self.assertIsNone(self.v.fault)
    def test_wrong_session_reply_is_terminal(self):
        self.t.intercept=lambda op,r:{**r,'session':'0'*32}
        with self.assertRaises(VisualError):self.v.bind(BINDING)
        self.assertTrue(self.v.fault)
    def test_wrong_request_id_is_terminal(self):
        self.t.intercept=lambda op,r:{**r,'id':'999'}
        with self.assertRaises(VisualError):self.v.bind(BINDING)
        self.assertTrue(self.v.fault)
    def test_helper_authority_claim_is_rejected(self):
        self.t.intercept=lambda op,r:{**r,'input_gate_provided':True}
        with self.assertRaises(VisualError):self.v.bind(BINDING)
    def test_timeout_late_reply_never_restores_or_reveals(self):
        self.v.bind(BINDING);self.t.intercept=lambda op,r:None
        with self.assertRaises(VisualError):self.v.cover()
        self.t.q.put(self.t.last);time.sleep(.05)
        with self.assertRaises(VisualError):self.v.prepare(new_attachment='c'*32,after_time=200)
        self.assertNotIn('reveal',[r['op'] for r in self.t.sent])
    def test_unsolicited_held_is_drained_without_request(self):
        self.covered();self.t.held();wait_fault(self.v)
        with self.assertRaises(VisualError):self.v.prepare(new_attachment='c'*32,after_time=200)
        self.assertEqual(self.v.snapshot.phase,'HELD')
    def test_eof_cannot_trigger_reveal_or_implicit_termination(self):
        prepared=self.prepared();self.t.closed=True;wait_fault(self.v)
        with self.assertRaises(VisualError):self.v.reveal(prepared,controller_grant='9'*32)
        self.assertNotIn('reveal',[r['op'] for r in self.t.sent])
        with self.assertRaises(VisualError):self.v.cleanup()
    def test_wrong_helper_identity_or_cover_handle_rejected(self):
        self.covered();self.t.intercept=lambda op,r:{**r,'helper_birth':'4002'}
        with self.assertRaises(VisualError):self.v.ping()
    def test_lost_cover_visibility_invalidates_old_receipt(self):
        cover=self.covered();self.t.intercept=lambda op,r:{**r,'cover_window_visible':False}
        with self.assertRaises(VisualError):self.v.ping()
        with self.assertRaises(VisualError):self.v.assert_current(cover,('COVERED',))
    def test_duplicate_response_is_terminal_even_between_calls(self):
        self.covered();self.t.q.put(self.t.last);wait_fault(self.v)
        with self.assertRaises(VisualError):self.v.ping()
    def test_stale_frame_timestamp_rejected(self):
        self.covered();self.t.intercept=lambda op,r:{**r,'capture_time':'300'}
        with self.assertRaises(VisualError):self.v.prepare(new_attachment='c'*32,after_time=200)
    def test_forged_prepared_receipt_cannot_reveal(self):
        prepared=self.prepared()
        with self.assertRaises(VisualError):self.v.reveal(replace(prepared,token='a'*32),controller_grant='9'*32)
        self.assertNotIn('reveal',[r['op'] for r in self.t.sent])
    def test_explicit_hold_needs_explicit_cleanup(self):
        self.covered();self.v.hold('USER_CONTROLLER_HOLD')
        with self.assertRaises(VisualError):self.v.cleanup()
        self.assertTrue(self.v.cleanup(accept_cover_loss=True)['cover_loss_accepted'])
    def test_missing_native_evidence_does_not_advance_gate(self):
        f=self.gate();cover=self.covered()
        with self.assertRaises(VisualError):GateVisualBridge(self.v).accept_cover(f.g,cover)
        self.assertEqual(f.g.phase,'WAITING_FOR_COVER');self.assertEqual(f.j.status()['status'],'STAGED')
    def test_fixture_evidence_rejected_without_explicit_mode(self):
        f=self.gate();cover=self.covered()
        with self.assertRaises(VisualError):GateVisualBridge(self.v,evidence_provider=fixture_evidence).accept_cover(f.g,cover)
    def test_bad_native_or_display_evidence_is_not_wgc_substituted(self):
        f=self.gate();cover=self.covered()
        for changes in ({'input_blocked':False},{'display_usable':False},{'native_planning_map':False},
                        {'native_attachment':'0'*32},{'native_force':999},{'map_stable_since':101},
                        {'connected':('A',)},{'epoch':99}):
            with self.subTest(changes=changes):
                bridge=GateVisualBridge(self.v,evidence_provider=lambda q:replace(fixture_evidence(q),**changes),allow_fixture_evidence=True)
                with self.assertRaises(VisualError):bridge.accept_cover(f.g,cover)
        self.assertEqual(f.g.phase,'WAITING_FOR_COVER')
    def test_real_gate_journal_ordering_with_explicit_synthetic_proof(self):
        f=self.gate();cover=self.covered();bridge=GateVisualBridge(self.v,evidence_provider=fixture_evidence,allow_fixture_evidence=True)
        bridge.accept_cover(f.g,cover);f.restore()
        prepared=self.v.prepare(new_attachment='c'*32,after_time=200)
        bridge.accept_prepared(f.g,prepared)
        grant=f.g.begin_reveal(f.host,f.new)
        self.assertFalse(f.g.status()['accept_planning_intents'])
        bridge.reveal(f.g,grant)
        self.assertTrue(f.g.status()['accept_planning_intents'])
        self.assertFalse(f.g.status()['native_gameplay_enabled'])
    def test_disconnect_during_native_evidence_blocks_gate(self):
        f=self.gate();cover=self.covered()
        def provider(q):
            evidence=fixture_evidence(q);f.c.connection('B',False);return evidence
        with self.assertRaises(VisualError):GateVisualBridge(self.v,evidence_provider=provider,allow_fixture_evidence=True).accept_cover(f.g,cover)
        self.assertEqual(f.g.phase,'WAITING_FOR_COVER')
    def test_disconnect_after_helper_reveal_reply_cannot_open_gate(self):
        f=self.gate();cover=self.covered();bridge=GateVisualBridge(self.v,evidence_provider=fixture_evidence,allow_fixture_evidence=True)
        bridge.accept_cover(f.g,cover);f.restore();prepared=self.v.prepare(new_attachment='c'*32,after_time=200)
        bridge.accept_prepared(f.g,prepared);grant=f.g.begin_reveal(f.host,f.new)
        def intercept(op,r):
            if op=='reveal':f.c.connection('B',False)
            return r
        self.t.intercept=intercept
        with self.assertRaises(VisualError):bridge.reveal(f.g,grant)
        self.assertEqual(f.g.phase,'HELD');self.assertFalse(f.g.status()['accept_planning_intents'])
    def test_transition_surface_will_not_receive_dummy_pixels_or_presented(self):
        with self.assertRaises(VisualError):GateVisualBridge.transition_surface_receipt(self.covered())
    def test_transport_drains_stderr_and_rejects_duplicate_json_keys(self):
        script='import sys\nsys.stderr.buffer.write(b"x"*262144)\nsys.stderr.flush()\nprint(\'{"value":1,"value":2}\',flush=True)\n'
        process=subprocess.Popen([sys.executable,'-u','-c',script],stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,stderr=subprocess.PIPE,bufsize=0,
            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        transport=PopenJsonTransport(process)
        self.assertEqual(transport.wait(5),0)
        transport._reader.join(1);transport._stderr.join(1)
        with self.assertRaises(VisualError):transport.receive(.1)
        self.assertIn('Duplicate JSON key',transport._io_fault)
        self.assertTrue(transport.stderr_tail)
        self.assertLessEqual(sum(len(s) for s in transport.stderr_tail),64*2048)
    def test_transport_overflow_is_explicit_failure_not_silent_drop(self):
        script='for i in range(400):\n print(\'{"n":%d}\'%i,flush=True)\n'
        process=subprocess.Popen([sys.executable,'-u','-c',script],stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,stderr=subprocess.PIPE,bufsize=0,
            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        transport=PopenJsonTransport(process)
        self.assertEqual(transport.wait(5),0);transport._reader.join(1)
        with self.assertRaises(VisualError):transport.receive(.1)
        self.assertTrue(transport._io_fault)


def own_helper_test(out):
    approved=json.loads((HERE/'checkpoint_map_wait_helper_handoff.json').read_text())
    target=PopenJsonTransport.start(HERE/'checkpoint_map_wait_helper_fixture.exe',expected_sha256=approved['fixture_binary_sha256'])
    helper=None;client=None;log=[]
    try:
        r=target.receive(8);require(r['event']=='FIXTURE_READY' and uint(r['pid'])==target.pid and r['class']=='CheckpointMapWaitHelperFixture','Own target binding rejected')
        helper=PopenJsonTransport.start(approved['helper'],expected_sha256=approved['helper_sha256'])
        client=VisualClient(helper,session=SESSION,timeout=8)
        target_binding=TargetBinding(uint(r['hwnd']),target.pid,uint(r['birth']),r['class'],BINDING.attachment,BINDING.view,'borderless')
        client.bind(target_binding);old=client.cover();log.append({'cover':old.__dict__})
        client.ping()
        target.send({'id':'1','op':'world','revision':1});require(target.receive(8)['ok'],'Own world mutation failed')
        new=client.prepare(new_attachment='c'*32,after_time=old.capture_time)
        require(old.sha256!=new.sha256,'Fixture world did not change');log.append({'prepared':new.__dict__})
        with tempfile.TemporaryDirectory(prefix='checkpoint_visual_client_',dir=HERE) as folder:
            f=GateFixture(folder)
            # No native/display provider: real WGC alone cannot authorize a gate.
            try:GateVisualBridge(client).accept_cover(f.g,old)
            except VisualError:pass
            else:raise AssertionError('WGC unexpectedly authorized native gate')
            require(f.g.phase=='WAITING_FOR_COVER','Gate advanced without evidence')
        # This explicit synthetic grant exercises helper pixels only; no native
        # adapter, game, room gameplay, or input gate is present in the test.
        shown=client.reveal(new,controller_grant='9'*32);log.append({'revealed':shown.__dict__})
        require(not client.snapshot.visible,'Own cover not hidden')
        cleanup=client.cleanup();require(client.fault is None,'Clean acknowledged stop became EOF failure')
        log.append({'cleanup':cleanup})
        return {'case':'own_window_frozen_helper_cycle','passed':True,'target_pid':target.pid,
                'helper_pid':helper.pid,'separate_processes':helper.pid!=target.pid,
                'old_frame_sha256':old.sha256,'new_frame_sha256':new.sha256,
                'real_game_access':False,'native_input_gate':False,'usable_physical_display_proved':False}
    finally:
        if client and not client._closed:client.terminate_helper(accept_cover_loss=True)
        elif helper and not client:helper.terminate();helper.wait(3)
        target.send({'id':'2','op':'quit'});target.receive(8);target.wait(3)
        (out/'own-helper-exchange.json').write_text(json.dumps(log,indent=2)+'\n')


def main():
    out=HERE/'checkpoint_visual_client_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');out.mkdir(parents=True)
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    frozen=[OUTPUT/'checkpoint_presentation.py',OUTPUT/'transition_visual_surface.py',
            HERE/'checkpoint_map_wait_helper.exe',HERE/'checkpoint_map_wait_helper_fixture.exe',
            HERE/'checkpoint_map_wait_helper.cpp',HERE/'checkpoint_map_wait_helper_common.h']
    before={str(p):sha(p) for p in frozen}
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(ClientTests)
    with (out/'unittest.txt').open('w',encoding='utf8') as stream:
        result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    own=own_helper_test(out) if '--own-helper' in sys.argv else {'case':'own_window_frozen_helper_cycle','skipped':True}
    require(before=={str(p):sha(p) for p in frozen},'Frozen source/binary changed')
    sources=['checkpoint_visual_client.py','checkpoint_visual_client_bridge.py','checkpoint_visual_client_test.py']
    report={'schema':'san14.visual-client-fixtures.v1','result':'PASS' if result.wasSuccessful() and not own.get('failed') else 'FAIL',
            'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
            'own_helper':own,'source_sha256':{n:sha(HERE/n) for n in sources},'frozen_unchanged':before,
            'game_access':False,'target_enumeration':False,'input_injected':False,'native_gameplay_enabled':False,
            'native_evidence_provider':'SYNTHETIC_IN_TESTS_ONLY; NONE_IMPLEMENTED',
            'physical_unoccluded_display_proved':False}
    (out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'result':report['result'],'path':str(out/'result.json'),'tests':result.testsRun,'own_helper':own}))
    if not result.wasSuccessful():print((out/'unittest.txt').read_text())
    return not result.wasSuccessful()


if __name__=='__main__':raise SystemExit(main())
