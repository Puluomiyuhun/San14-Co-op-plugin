"""Actual captured proposal/TLS/Room/Journal; owned native/menu lifetimes only."""
from datetime import datetime
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch
import hashlib,io,json,sys,unittest
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];PRIVATE=ROOT.parent/'mod_research'
sys.path[:0]=[str(PRIVATE/'python_deps'),str(ROOT/'outputs/san14-link')]
import b_input_reward_runner_test as prior
import b_menu_reward_session as menu
from reward_menu_capture import CaptureSession
from reward_ready_flow_fixture import capture_inputs
OUTPUT=None;ROWS=[]

class Cases(prior.Cases):
    def setUp(self):
        super().setUp();self.menu_case='normal';self.confirmations=[];self.pending=None
        for p in (HERE/'b_menu_reward_session.py',ROOT/'outputs/san14-link/reward_menu_capture.py'):
            self.checked['sources'][str(p.resolve())]=hashlib.sha256(p.read_bytes()).hexdigest()
    def execute(self):
        with patch.object(prior.entry,'Runner',menu.Runner):return super().execute()
    def on_event(self,name,runner):
        self.runner_events.append(name)
        if name!='reward-planning-open':return
        preview,context=capture_inputs(runner.reward.replica);capture=CaptureSession()
        capture.capture(preview,context,capture_id='c'*32,now_tick=100)
        self.pending=capture.confirm('c'*32,preview,context,now_tick=100)
        same=capture.confirm('c'*32,preview,context,now_tick=100)
        self.assertIs(self.pending,same);self.original_packet=self.pending.packet()
        attachment=runner.guest.attachments['B'];pending=self.pending
        if self.menu_case=='epoch':pending=replace(pending,epoch='f'*32)
        if self.menu_case=='attachment':attachment='f'*32
        if self.menu_case=='date':self.b_world.memory.pack(self.b_world.world+0x37,'<B',21)
        if self.menu_case=='lost-reply':
            request=self.link.control.request
            def lost(value):
                result=request(value)
                if value.get('action')=='reward_submit':raise TimeoutError('Owned loss after real authority accepted packet')
                return result
            self.link.control.request=lost
        first=runner.submit_pending(pending,attachment_id=attachment);self.confirmations.append(first)
        if self.menu_case=='changed':runner.submit_pending(replace(pending,officer_ids=(102,)),attachment_id=attachment)
        again=runner.submit_pending(same,attachment_id=attachment);self.confirmations.append(again)
        self.assertEqual(first['authority_ack'],again['authority_ack']);self.assertTrue(again['local_duplicate'])
        self.assertEqual(first['request_id'],pending.request_id)
        self.assertFalse(first['native_menu_close_authorized']);self.assertFalse(first['native_execution_verified'])
        runner.finish_input()
        with self.assertRaises(Exception):runner.submit_pending(same,attachment_id=attachment)
        self.assertTrue(self.a.request(dict(action='reward_cut_prepare',epoch=self.c.epoch))['ok'])

    def evidence(self):
        with self.mount.flow.db() as db:
            requests=[dict(r) for r in db.execute('SELECT player,request_id,status,proposal FROM requests')]
        ROWS.append(dict(case=self._testMethodName,captured_request=self.pending.request_id,
            original_packet=self.original_packet,control_actions=self.control_actions,requests=requests,
            menu_confirmations=self.confirmations,formal_completions=len(self.runner.guest.history),
            business_calls=dict(A=self.a_world.calls,B=self.b_world.calls),
            no_native_menu_permission=True))
        return requests

    def test_same_capture_twice_one_packet_one_payment_then_closed(self):
        self.begin();self.execute();self.assertFalse(self.thread_errors,self.thread_errors)
        self.assertEqual(self.control_actions.count('reward_submit'),1)
        self.assertEqual((self.a_world.calls,self.b_world.calls),(1,1))
        rows=self.evidence();self.assertEqual(len(rows),1);self.assertEqual(rows[0]['request_id'],self.pending.request_id)
        self.assertEqual(json.loads(rows[0]['proposal']),self.original_packet)
        self.assertEqual(rows[0]['status'],'PAIRED');self.assertEqual(len(self.runner.guest.history),2)

    def negative(self,kind,submitted):
        self.menu_case=kind;self.fault='menu-'+kind;self.begin()
        with self.assertRaises(Exception):self.execute()
        self.assertEqual(self.control_actions.count('reward_submit'),int(submitted))
        self.assertEqual(len(self.runner.guest.history),1);self.assertFalse(self.b_world.calls)
        self.assertNotIn('period_ready',self.control_actions);self.assertNotIn('second-native-load',self.owner_events)
        before=list(self.control_actions)
        if hasattr(self.runner,'menu'):
            with self.assertRaises(Exception):self.runner.menu.submit_pending(self.pending,attachment_id=self.runner.guest.attachments['B'])
        self.assertEqual(before,self.control_actions);self.evidence()
    def test_same_request_changed_command_terminal_no_second_send(self):self.negative('changed',True)
    def test_authority_accepted_reply_lost_terminal_no_replay(self):self.negative('lost-reply',True)
    def test_stale_wire_epoch_refused_before_send(self):self.negative('epoch',False)
    def test_wrong_native_attachment_refused_before_send(self):self.negative('attachment',False)
    def test_actual_sample_date_change_refused_before_send(self):self.negative('date',False)

if __name__=='__main__':
    OUTPUT=PRIVATE/'b_menu_reward_session_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');OUTPUT.mkdir(parents=True)
    prior.prior.predecessor.fixture.transport.OUTPUT=OUTPUT
    prior.boot_test.BUILD=prior.BUILD;prior.boot_test.APPROVED=prior.boot.approved(prior.BUILD)
    before=prior.prior.pins();stream=io.StringIO();r=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.TestSuite(Cases(n) for n in Cases.__dict__ if n.startswith('test_')))
    after=prior.prior.pins();(OUTPUT/'test.log').write_text(stream.getvalue(),encoding='utf-8');print(stream.getvalue())
    result=dict(result='PASS' if r.wasSuccessful() and before==after else 'FAIL',tests=r.testsRun,
        sources=after,inputs_unchanged=before==after,private={str(prior.BUILD.run/'result.json'):prior.BUILD.sha256},cases=ROWS,
        actual_PendingReward_Runner_TLS_Room_Journal=True,native_menu_lifetime_and_native_business_RAM_OS_doubles=True,
        game_access=False,steam_access=False,native_menu_permission=False,ui_refresh_verified=False,
        failures=[(str(t),s) for t,s in r.failures+r.errors])
    result['artifacts']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in OUTPUT.rglob('*') if p.is_file()}
    p=OUTPUT/'result.json';p.write_text(json.dumps(result,indent=2)+'\n');print(p);raise SystemExit(result['result']!='PASS')
