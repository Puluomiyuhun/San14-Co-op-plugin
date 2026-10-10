"""Exact A captured packets over real mounted TLS/Room/SQLite authority queue.
Menu lifetime, game RAM and native reward business remain owned doubles.
"""
from datetime import datetime
from dataclasses import replace
from pathlib import Path
import hashlib,io,json,sys,threading,unittest
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];PRIVATE=ROOT.parent/'mod_research'
sys.path[:0]=[str(PRIVATE/'python_deps'),str(ROOT/'outputs/san14-link')]
import a_reward_runtime_mount_test as prior
import a_menu_reward_session as menu
from reward_menu_capture import CaptureSession
from reward_ready_flow_fixture import capture_inputs
import reward_checkpoint_shared_cut,reward_checkpoint_observer,b_warm_remote_completion
OUTPUT=None;ROWS=[]

class Cases(prior.Cases):
    def setUp(self):
        super().setUp();self.opened();self.menu=menu.MenuRewardSession(self.mount);self.sent=[]
        self.original_request=self.a.request
        def request(value):self.sent.append(value.copy());return self.original_request(value)
        self.a.request=request
        preview,context=capture_inputs(self.flow.host);self.capture=CaptureSession()
        self.capture.capture(preview,context,capture_id='e'*32,now_tick=100)
        self.pending=self.capture.confirm('e'*32,preview,context,now_tick=100)
        self.assertIs(self.pending,self.capture.confirm('e'*32,preview,context,now_tick=100))
    def submit(self,pending=None,attachment=None):
        return self.menu.submit_pending(pending or self.pending,attachment_id=attachment or self.mount.attachment)
    def rows(self):
        with self.flow.db() as db:return [dict(r) for r in db.execute('SELECT player,request_id,status,proposal FROM requests')]
    def evidence(self,**extra):
        ROWS.append(dict(case=self._testMethodName,packet=self.pending.packet(),sent=self.sent,rows=self.rows(),
            phase=self.mount.phase,business_calls={p:w.calls for p,w in self.worlds.items()},
            native_menu_permission=False,**extra))
    def assert_no_replay(self):
        n=len(self.sent)
        with self.assertRaises(Exception):self.submit()
        self.assertEqual(len(self.sent),n);self.assertEqual(self.mount.phase,'HELD')

    def test_same_capture_one_tls_packet_one_payment_and_real_shared_cut(self):
        first=self.submit();again=self.submit()
        self.assertFalse(first['local_duplicate']);self.assertTrue(again['local_duplicate'])
        self.assertEqual(first['authority_ack'],again['authority_ack'])
        self.assertFalse(first['native_menu_close_authorized']);self.assertFalse(first['native_execution_verified'])
        self.assertEqual(self.sent,[self.pending.packet()]);self.assertEqual(len(self.rows()),1)
        self.mount.poll();self.guest_cut.poll()
        self.assertEqual({p:w.calls for p,w in self.worlds.items()},{'A':1,'B':1})
        third=self.submit();self.assertTrue(third['local_duplicate']);self.assertEqual(self.sent,[self.pending.packet()])
        self.assertTrue(self.a.request(dict(action='reward_cut_prepare',epoch=self.c.epoch))['ok'])
        self.guest_cut.finish_input();self.mount.poll();self.guest_cut.poll();self.mount.poll()
        self.guest_cut.ready_after_cut();permit=self.c.seal_inputs();self.c.begin_simulation(permit)
        self.mount.validate_seal(permit);self.assertEqual(permit['sequence'],1)
        rows=self.rows();self.assertEqual(rows[0]['player'],'A');self.assertEqual(rows[0]['request_id'],self.pending.request_id)
        self.assertEqual(json.loads(rows[0]['proposal']),self.pending.packet());self.assertEqual(rows[0]['status'],'PAIRED')
        self.evidence(cut=permit)

    def test_same_id_changed_selection_holds_without_second_send(self):
        self.submit()
        with self.assertRaises(Exception):self.submit(replace(self.pending,officer_ids=(98,)))
        self.assertEqual(self.sent,[self.pending.packet()]);self.assert_no_replay();self.evidence()

    def test_accepted_authority_reply_lost_retains_intent_no_retry(self):
        request=self.a.request
        def lost(value):request(value);raise TimeoutError('Owned lost reply after authority committed proposal')
        self.a.request=lost
        with self.assertRaises(TimeoutError):self.submit()
        self.assertEqual(len(self.rows()),1);self.assertEqual(self.rows()[0]['request_id'],self.pending.request_id)
        self.assertEqual(self.menu.rows[self.pending.request_id]['state'],'INTENT')
        self.assert_no_replay();self.assertEqual(self.worlds['A'].calls,0);self.evidence()

    def test_wrong_player_or_stale_epoch_rejected_before_network(self):
        with self.assertRaises(Exception):self.submit(replace(self.pending,player_id='B',epoch='f'*32))
        self.assertFalse(self.sent);self.assertFalse(self.rows());self.assert_no_replay();self.evidence()

    def test_attachment_change_rejected_before_network(self):
        self.c.attachments['A']='f'*32
        with self.assertRaises(Exception):self.submit()
        self.assertFalse(self.sent);self.assertFalse(self.rows());self.assert_no_replay();self.evidence()

    def test_actual_date_sample_drift_rejected_before_network(self):
        w=self.worlds['A'];w.memory.pack(w.world+0x37,'<B',21)
        with self.assertRaises(Exception):self.submit()
        self.assertFalse(self.sent);self.assertFalse(self.rows());self.assert_no_replay();self.evidence()

    def test_finish_after_precheck_gate_rejects_no_lock_across_tls(self):
        entered=threading.Event();resume=threading.Event();failures=[];request=self.a.request
        def delayed(value):
            if value.get('action')=='reward_submit':entered.set();self.assertTrue(resume.wait(3))
            return request(value)
        self.a.request=delayed
        def worker():
            try:self.submit()
            except BaseException as exc:failures.append(type(exc).__name__)
        thread=threading.Thread(target=worker);thread.start()
        try:
            self.assertTrue(entered.wait(3))
            # This real TLS handler takes gate/room/coordinator locks. If the
            # proposal held them across RPC it could not acknowledge this cut.
            self.assertTrue(self.a.request(dict(action='reward_cut_prepare',epoch=self.c.epoch))['ok'])
        finally:resume.set();thread.join(3)
        self.assertFalse(thread.is_alive());self.assertTrue(failures)
        self.assertFalse(self.rows());self.assertEqual(self.worlds['A'].calls,0)
        self.assert_no_replay();self.evidence(failures=failures)

if __name__=='__main__':
    OUTPUT=PRIVATE/'a_menu_reward_session_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');OUTPUT.mkdir(parents=True)
    prior.observed.transport.OUTPUT=OUTPUT
    before=prior.pins();stream=io.StringIO();r=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.TestSuite(Cases(n) for n in Cases.__dict__ if n.startswith('test_')))
    after=prior.pins();(OUTPUT/'test.log').write_text(stream.getvalue(),encoding='utf-8');print(stream.getvalue())
    result=dict(result='PASS' if r.wasSuccessful() and before==after else 'FAIL',tests=r.testsRun,sources=after,
        inputs_unchanged=before==after,cases=ROWS,actual_mount_TLS_Room_Journal_SharedCutGate=True,
        native_menu_lifetime_RAM_reward_business_doubles=True,host_service_constructor_executed=False,
        game_access=False,steam_access=False,native_menu_close_permission=False,ui_refresh_verified=False,
        failures=[(str(t),s) for t,s in r.failures+r.errors])
    result['artifacts']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in OUTPUT.rglob('*') if p.is_file()}
    p=OUTPUT/'result.json';p.write_text(json.dumps(result,indent=2)+'\n');print(p);raise SystemExit(result['result']!='PASS')
