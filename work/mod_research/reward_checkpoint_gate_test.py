"""Actual observed bootstrap/room/TLS + reward journals; native/RAM doubles.

No game or native installer. The reward byte layout is separate from the
checkpoint fixture layout: a nonzero reward cut intentionally stops in HELD.
"""
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import hashlib
import io
import json
from pathlib import Path
import secrets
import sys
import threading
import unittest

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];PRIVATE=ROOT.parent/'mod_research'
sys.path[:0]=[str(PRIVATE/'python_deps'),str(ROOT/'outputs/san14-link')]
import b_observed_completion_test as observed
from reward_checkpoint_gate import CheckpointGate
from reward_observed_flow import ObservedRewardFlow,GuestConsumer
from reward_observed_fixture import World
from reward_room_flow import Replica,envelope
import execution_journal as journal

OUTPUT=None;ROWS=[]


class Cases(observed.Cases):
    def setUp(self):
        super().setUp()
        r,q,p=self.first();reply=self.adapter.apply(r,q,p)
        self.assertTrue(reply['ok']);self.assertTrue(self.c.bootstrap_completed)
        self.assertEqual((self.c.period,self.c.phase),(2,'PLANNING'))
        self.worlds={p:World(f) for p,f in (('A',12),('B',2))}
        for p,w in self.worlds.items():w.attachment=self.c.attachments[p]
        self.reward_ports={p:w.port() for p,w in self.worlds.items()}
        self.reward_key=secrets.token_bytes(32)
        self.flow=ObservedRewardFlow(self.folder/'rewards',self.room,self.reward_ports['A'],
            self.reward_ports['B'].attachment_id,deepcopy(self.c.node),guest_report_key=self.reward_key)
        self.gate=CheckpointGate(self.room,self.c,self.flow)
        # Existing retained authenticated sockets now route to the real composed
        # endpoint. No room/coordinator or signed completion is replaced.
        self.servers[0][0].room=self.gate
        self.replica=Replica(self.folder/'reward-B.sqlite',self.flow.scope,'B',self.reward_ports['B'])
        self.consumer=GuestConsumer(self.b,self.replica,self.reward_key);self.consumer.report()

    def proposal(self,p='A'):
        return envelope(self.flow.scope,'reward_submit',request_id=secrets.token_hex(16),
                        district_id=11 if p=='A' else 2,officer_ids=[97] if p=='A' else [101])

    def assert_blocked(self):
        for p,client in (('A',self.a),('B',self.b)):
            self.assertFalse(client.request(dict(action='period_ready',epoch=self.c.epoch,ready=True))['ok'])
            with self.assertRaises(ValueError):self.c.set_ready(p,self.c.epoch,True)
        with self.assertRaises(ValueError):self.c.seal_inputs()
        with self.assertRaises(ValueError):self.binding.validate_context()
        with self.assertRaises(ValueError):self.c.native_binding(123)
        self.assertFalse(self.c.ready)

    def evidence(self,**kw):
        ROWS.append(dict(case=self._testMethodName,gate=self.gate.status(),
            native_reward_calls={p:w.calls for p,w in self.worlds.items()},
            actual_formal_bootstrap_receipts=len(self.c.applied_receipts),**kw))

    def test_queued_and_unconfirmed_block_original_ready_save(self):
        self.assertTrue(self.a.request(self.proposal())['ok']);self.assert_blocked()
        with self.assertRaisesRegex(ValueError,'awaiting'):self.gate.retire_drained()
        self.assertEqual(self.gate.state,'ACTIVE')
        self.assertEqual(self.gate.pump_one()['status'],'AWAITING_B');self.assert_blocked()
        with self.assertRaisesRegex(ValueError,'awaiting'):self.gate.retire_drained()
        self.assertEqual(self.worlds['A'].calls,1);self.assertEqual(self.worlds['B'].calls,0)
        self.consumer.consume_one();proof=self.gate.retire_drained()
        self.assertEqual(proof['reward_sequence'],1)
        self.assertEqual(proof['state'],'RETIRED_NEEDS_SHARED_CUT')
        self.assertFalse(proof['zero_command_control_may_continue']);self.assertFalse(proof['save_authorized'])
        self.assertEqual(self.c.phase,'HELD');self.assert_blocked()
        self.assertTrue(all(self.c.inflight.values()))
        self.assertEqual(self.c.reports['A']['sequence'],0) # explicitly NOT promoted/usable
        self.evidence(proof=proof)

    def test_empty_retire_releases_original_zero_command_protocol(self):
        self.assert_blocked();proof=self.gate.retire_drained()
        self.assertEqual(proof['state'],'RETIRED_EMPTY');self.assertFalse(any(self.c.inflight.values()))
        self.assertFalse(self.a.request(self.proposal())['ok'])
        with self.assertRaisesRegex(ValueError,'retired'):self.gate.pump_one()
        with self.assertRaisesRegex(ValueError,'retired'):self.gate.retire_drained()
        with self.assertRaisesRegex(ValueError,'already attempted'):CheckpointGate(self.room,self.c,self.flow)
        for client in (self.a,self.b):
            self.assertTrue(client.request(dict(action='period_ready',epoch=self.c.epoch,ready=True))['ok'])
        permit=self.c.seal_inputs();self.c.begin_simulation(permit)
        self.assertEqual(self.binding.validate_context()['cut']['sequence'],0)
        self.assertEqual(self.c.native_binding(123)['generation'],2)
        self.evidence(proof=proof,original_no_command_control_available=True)

    def test_two_seats_share_queue_and_only_actual_paired_prefix_retires(self):
        a,b=self.proposal('A'),self.proposal('B')
        with ThreadPoolExecutor(2) as pool:
            replies=list(pool.map(lambda row:row[0].request(row[1]),((self.a,a),(self.b,b))))
        self.assertTrue(all(r['ok'] for r in replies));self.assertEqual(sorted(r['ordinal'] for r in replies),[1,2])
        for sequence in (1,2):
            self.assertEqual(self.gate.pump_one()['sequence'],sequence)
            self.consumer.consume_one()
        proof=self.gate.retire_drained()
        self.assertEqual(proof['reward_sequence'],2)
        self.assertEqual(proof['host_report']['prefix_sha256'],proof['guest_report']['prefix_sha256'])
        self.assertEqual(proof['host_report']['state_sha256'],proof['guest_report']['state_sha256'])
        for client,value in ((self.a,a),(self.b,b)):
            self.assertFalse(client.request(value)['ok']) # even old duplicate cannot reopen epoch
        with self.assertRaises(ValueError):self.flow.pump_one()
        self.assertEqual([w.calls for w in self.worlds.values()],[2,2]);self.assert_blocked()
        self.evidence(proof=proof)

    def test_unknown_native_effect_holds_both_flows_without_retry(self):
        self.worlds['A'].failure='after-write';self.assertTrue(self.a.request(self.proposal())['ok'])
        with self.assertRaises(journal.ExecutionHeld):self.gate.pump_one()
        self.assertEqual((self.gate.state,self.c.phase),('HELD','HELD'))
        with self.assertRaises(ValueError):self.gate.pump_one()
        with self.assertRaises(ValueError):self.gate.retire_drained()
        self.assertEqual(self.worlds['A'].calls,1);self.assert_blocked()
        self.assertTrue(self.flow.host.journal.status()['unknown_sequences'])
        self.evidence()

    def test_checkpoint_drift_is_sticky_and_foreign_connection_cannot_submit(self):
        proposal=self.proposal();self.assertFalse(self.gate.handle('A','not-current',proposal)['ok'])
        original=self.c.epoch;self.c.epoch=secrets.token_hex(16)
        self.assertFalse(self.a.request(proposal)['ok']);self.assertEqual(self.gate.state,'HELD')
        self.c.epoch=original
        self.assertFalse(self.a.request(proposal)['ok'])
        self.assertEqual([w.calls for w in self.worlds.values()],[0,0]);self.assert_blocked()
        self.evidence()

    def test_drain_race_cannot_release_while_native_owner_is_active(self):
        entered=threading.Event();release=threading.Event();original=self.worlds['A'].execute
        def native(command):
            entered.set()
            if not release.wait(5):raise TimeoutError('Owned test release missing')
            return original(command)
        self.worlds['A'].execute=native;self.assertTrue(self.a.request(self.proposal())['ok'])
        done=threading.Event();results=[];errors=[]
        def drain():
            try:results.append(self.gate.retire_drained())
            except Exception as exc:errors.append(str(exc))
            finally:done.set()
        with ThreadPoolExecutor(2) as pool:
            pumping=pool.submit(self.gate.pump_one);self.assertTrue(entered.wait(3));waiting=pool.submit(drain)
            self.assertFalse(done.wait(.1));release.set()
            self.assertEqual(pumping.result(5)['status'],'AWAITING_B');waiting.result(5)
        self.assertEqual(results,[]);self.assertTrue(any('awaiting' in x for x in errors))
        self.assertEqual(self.gate.state,'ACTIVE');self.assert_blocked()
        self.consumer.consume_one();proof=self.gate.retire_drained()
        self.assertEqual(proof['state'],'RETIRED_NEEDS_SHARED_CUT');self.evidence(proof=proof)


def pins():
    paths={Path(m.__file__).resolve() for m in list(sys.modules.values()) if getattr(m,'__file__',None)}
    paths.add(Path(__file__).resolve())
    return {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)
            if p.is_relative_to(ROOT) and p.suffix=='.py'}


if __name__=='__main__':
    OUTPUT=PRIVATE/'reward_checkpoint_gate_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');OUTPUT.mkdir(parents=True)
    observed.transport.OUTPUT=OUTPUT;before=pins();stream=io.StringIO()
    # Run only this successor's concrete composition cases, not inherited suites.
    suite=unittest.TestSuite(Cases(name) for name in Cases.__dict__ if name.startswith('test_'))
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    (OUTPUT/'test.log').write_text(stream.getvalue(),encoding='utf-8');after=pins()
    report=dict(result='PASS' if result.wasSuccessful() and before==after else 'FAIL',tests=result.testsRun,
        sources=after,inputs_unchanged=before==after,cases=ROWS,
        actual_observed_room_and_bootstrap_coordinator=True,actual_formal_bootstrap_completion=True,
        actual_TLS_and_SQLite=True,actual_reward_context_sampling=True,
        native_RAM_save_load_reward_publish_doubles=True,separate_fixture_world_projections=True,
        shared_checkpoint_cut_installed=False,production_native_reward_port=False,
        physical_input_fence=False,save_authorized=False,native_gameplay_enabled=False,game_access=False,
        failures=[(str(t),detail) for t,detail in result.errors+result.failures])
    report['artifacts']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in OUTPUT.rglob('*') if p.is_file()}
    (OUTPUT/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(OUTPUT/'result.json');print(stream.getvalue());raise SystemExit(report['result']!='PASS')
