"""Actual TLS and three-chain receipts; owned input RPC and native world doubles."""
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
import hashlib, io, json, threading, unittest
import b_observed_chain_completion_test as chain
import observed_three_room_service_test as service
import player_input_rebind_port_test as window
import b_chain_input_transition as transition
import player_input_rebind_port as inputs

OUTPUT=None

class Cases(service.Cases):
    def input(self):
        self.body=window.Body();b=self.body.s.binding
        b.room[:]=bytes.fromhex(self.c.scope['room_id']);b.epoch[:]=bytes.fromhex(self.c.epoch)
        b.attachment[:]=bytes.fromhex(self.c.attachments['B']);b.period=self.c.period;b.seat=1
        self.body.s.pid=self.guest.pid;self.body.s.birth=self.birth
        transport=inputs.Transport.__new__(inputs.Transport)
        transport.state=inputs.common.SharedCallState(threading.RLock(),lambda exc:None)
        transport._perform=self.body.call
        self.lease=inputs.InputLease(transport,nonce=self.body.nonce,binding=b,pid=self.guest.pid,birth=self.birth,
            window=self.body.s.window,records=self.folder/'input',wait_seconds=.1)

    def first(self):
        self.input();self.warm.calls=SimpleNamespace(uncertain=False)
        self.complete(1)

    def rebind(self,n):
        return transition.rebind_after_load(self.session,self.adapter,self.lease,records=self.folder/f'input-world-{n}')

    def test_three_formal_completions_rebind_same_owner_under_hold(self):
        self.first();owner=id(self.lease);rows=[self.rebind(1)]
        for n in (2,3):
            self.complete(n);rows.append(self.rebind(n))
            self.assertEqual(id(self.lease),owner)
        self.assertEqual(self.body.calls.count('PlayerInputRebind'),3)
        self.assertNotIn('PlayerInputRequest',self.body.calls)
        self.assertEqual(self.lease.binding.period,4)
        self.assertEqual(bytes(self.lease.binding.attachment).hex(),self.adapter.attachments['B'])
        self.assertTrue(all(not x['input_planning_open'] for x in rows))
        self.assertEqual(self.body.s.publicationWrites,1);self.assertEqual(self.body.s.phase,2)
        self.assertTrue(self.body.s.held)
        self.assertEqual((self.session.phase,self.adapter.phase),('THREE_LOADS_RETAINED','THREE_COMPLETIONS_RETAINED'))

    def test_duplicate_rebind_refused_without_another_rpc(self):
        self.first();self.rebind(1);calls=list(self.body.calls)
        with self.assertRaisesRegex(ValueError,'already attempted'):self.rebind(1)
        self.assertEqual(calls,self.body.calls)

    def test_skipped_first_rebind_cannot_jump_period(self):
        self.first();self.complete(2)
        with self.assertRaisesRegex(ValueError,'Prior input'):self.rebind(2)
        self.assertNotIn('PlayerInputRebind',self.body.calls)

    def test_stale_room_epoch_refuses_before_native_write(self):
        self.first();self.c.epoch='f'*32
        with self.assertRaisesRegex(ValueError,'settled'):self.rebind(1)
        self.assertNotIn('PlayerInputRebind',self.body.calls)
        self.assertEqual(self.session.phase,'TERMINAL')

    def test_changed_formal_native_receipt_refuses(self):
        self.first();self.adapter.history[0]['native_receipt']='f'*64
        with self.assertRaisesRegex(ValueError,'another native receipt'):self.rebind(1)
        self.assertNotIn('PlayerInputRebind',self.body.calls)

    def test_rules_must_belong_to_latest_loaded_world(self):
        self.first();self.session.lifecycle.current.retired=True
        with self.assertRaisesRegex(ValueError,'human rules'):self.rebind(1)
        self.assertNotIn('PlayerInputRebind',self.body.calls)

    def test_second_unknown_rebind_never_retries_or_opens(self):
        self.first();self.rebind(1);self.complete(2)
        self.body.fault='unknown'
        with self.assertRaises(inputs.common.RemoteCallUnknown):self.rebind(2)
        count=len(self.body.calls)
        with self.assertRaisesRegex(ValueError,'already attempted'):self.rebind(2)
        with self.assertRaises(Exception):self.lease.request_phase(0)
        self.assertEqual(len(self.body.calls),count)
        self.assertTrue(self.lease.state.unknown);self.assertTrue(self.body.s.held)
        self.assertNotIn('PlayerInputRequest',self.body.calls)

    def test_window_cannot_report_open_on_rebind(self):
        self.first();self.body.fault='open'
        with self.assertRaisesRegex(Exception,'lost LOAD'):self.rebind(1)
        self.assertEqual(self.session.phase,'TERMINAL')

if __name__=='__main__':
    OUTPUT=chain.PRIVATE/'b_chain_input_transition_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    OUTPUT.mkdir(parents=True);chain.OUTPUT=OUTPUT;chain.prior.transport.OUTPUT=OUTPUT;service.OUTPUT=OUTPUT
    before=chain.pins();stream=io.StringIO()
    suite=unittest.TestSuite(Cases(n) for n in Cases.__dict__ if n.startswith('test_'))
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    after=chain.pins();(OUTPUT/'tests.log').write_text(stream.getvalue(),encoding='utf-8')
    data=dict(result='PASS' if result.wasSuccessful() and before==after else 'FAIL',tests=result.testsRun,
        sources=after,inputs_unchanged=before==after,actual_TLS_and_three_chain_completions=True,
        native_load_rules_window_RPC_doubles=True,game_access=False,**transition.FLAGS)
    data['artifacts']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in OUTPUT.rglob('*') if p.is_file()}
    path=OUTPUT/'result.json';path.write_text(json.dumps(data,indent=2),encoding='utf-8')
    print(stream.getvalue());print(path);raise SystemExit(data['result']!='PASS')
