"""Control-channel protocol tests; no game or window access."""
from dataclasses import replace
from datetime import datetime
import hashlib
import json
from pathlib import Path
import unittest

from checkpoint_session_channel import *
import checkpoint_session_channel as channel_module

HERE=Path(__file__).resolve().parent
BOUND=Endpoint(r'\\.\pipe\san14-checkpoint-synthetic',4000,4001,b's'*32,b'a'*16,b'i'*16)


class FakeTransport:
    def __init__(self,endpoint):
        self.endpoint=endpoint;self.ops=[];self.closed=False
        self.fields=dict.fromkeys(FIELDS,0);self.fields['state']=1
        self.mutate=lambda wire:wire
        self.fail=False
    def exchange(self,raw,timeout):
        magic,ver,op,seq,secret,attempt,intent=REQUEST.unpack(raw)
        assert magic==MAGIC and ver==VERSION and secret==self.endpoint.secret
        assert attempt==self.endpoint.attempt and intent==self.endpoint.intent
        self.ops.append((op,seq))
        if op==ARM_ONCE:self.fields.update(armed=1,state=2)
        if op==STOP_KEEP_OBSERVING:self.fields.update(stop_requested=1,state=9)
        if self.fail:raise OutcomeUnknown('Synthetic response lost after execution')
        return self.mutate(RESPONSE.pack(MAGIC,VERSION,op,seq,attempt,*[self.fields[f] for f in FIELDS]))
    def close(self):self.closed=True


class ChannelTests(unittest.TestCase):
    def setUp(self):
        self.transports=[]
        def factory(endpoint):
            t=FakeTransport(endpoint);self.transports.append(t);return t
        self.c=SessionChannel(BOUND,transport_factory=factory)
        self.t=self.transports[-1]
        self.addCleanup(self.c.close)

    def test_exact_packed_wire_sizes_and_roundtrip(self):
        self.assertEqual((REQUEST.size,RESPONSE.size),(80,96))
        self.assertEqual(self.c.snapshot().fields['state'],1)
        self.assertEqual(self.c.arm_once().fields['armed'],1)
        self.assertEqual(self.c.stop_keep_observing().fields['stop_requested'],1)
        self.assertEqual(self.t.ops,[(1,1),(2,2),(3,3)])

    def test_repeated_arm_rejected_before_transport(self):
        self.c.arm_once()
        with self.assertRaises(ChannelError):self.c.arm_once()
        self.assertEqual(self.t.ops,[(2,1)])

    def test_arm_reply_timeout_never_rearms_and_reconnect_preserves_sequence(self):
        self.t.fail=True
        with self.assertRaises(OutcomeUnknown):self.c.arm_once()
        self.assertTrue(self.t.closed)
        with self.assertRaises(ChannelError):self.c.arm_once()
        self.assertEqual(self.c.reconnect_for_observation().sequence,2)
        with self.assertRaises(ChannelError):self.c.arm_once()
        self.assertEqual(self.transports[-1].ops,[(1,2)])
        self.assertEqual(self.c.stop_keep_observing().sequence,3)

    def test_even_snapshot_disconnect_makes_reconnect_read_only(self):
        self.t.fail=True
        with self.assertRaises(OutcomeUnknown):self.c.snapshot()
        self.c.reconnect_for_observation()
        with self.assertRaises(ChannelError):self.c.arm_once()

    def test_stop_before_arm_permanently_disables_arm(self):
        self.c.stop_keep_observing()
        with self.assertRaises(ChannelError):self.c.arm_once()
        self.assertEqual(self.t.ops,[(3,1)])

    def test_existing_armed_or_in_flight_session_cannot_be_armed_again(self):
        self.t.fields.update(armed=1,state=2)
        self.c.snapshot()
        with self.assertRaises(ChannelError):self.c.arm_once()
        self.assertEqual(self.t.ops,[(1,1)])

    def test_identity_receipt_is_never_full_load_or_world_proof(self):
        self.t.fields.update(state=8,identity_ready=1,lifecycle_ready=1,bytes_ready=1,
                             may_have_published=1,cas_published=1)
        r=self.c.snapshot().progress()
        self.assertTrue(r['identity_receipt_only'])
        for flag in ('native_load_complete','native_input_barrier_proved','full_world_verified','planning_ready'):
            self.assertFalse(r[flag])
        with self.assertRaises(ChannelError):self.c.arm_once()

    def corrupt_header(self,index,value):
        def mutate(raw):
            fields=list(RESPONSE.unpack(raw));fields[index]=value
            return RESPONSE.pack(*fields)
        self.t.mutate=mutate
        with self.assertRaises(ChannelError):self.c.snapshot()
        self.assertTrue(self.t.closed)

    def test_wrong_sequence_rejected(self):self.corrupt_header(3,99)
    def test_wrong_attempt_rejected(self):self.corrupt_header(4,b'x'*16)
    def test_wrong_opcode_rejected(self):self.corrupt_header(2,2)
    def test_wrong_version_rejected(self):self.corrupt_header(1,2)
    def test_wrong_magic_rejected(self):self.corrupt_header(0,1)

    def test_truncated_reply_cannot_be_success(self):
        self.t.mutate=lambda raw:raw[:-1]
        with self.assertRaises(ChannelError):self.c.arm_once()
        self.assertTrue(self.c.arm_consumed)

    def test_unsupported_world_capability_claim_rejected(self):
        self.t.fields['capabilities']=1
        with self.assertRaises(ChannelError):self.c.snapshot()

    def test_inconsistent_cas_evidence_rejected(self):
        self.t.fields.update(cas_published=1,may_have_published=0)
        with self.assertRaises(ChannelError):self.c.snapshot()

    def test_native_refusal_keeps_observation_but_no_second_arm(self):
        self.t.fields['status']=6
        with self.assertRaises(NativeRejected):self.c.arm_once()
        self.t.fields['status']=0
        self.assertEqual(self.c.snapshot().sequence,2)
        with self.assertRaises(ChannelError):self.c.arm_once()

    def test_endpoint_does_not_expose_secret_in_repr(self):
        self.assertNotIn("b'sssss",repr(BOUND))
        self.assertNotIn(BOUND.secret.hex(),repr(BOUND))

    def test_remote_pipe_and_empty_binding_rejected(self):
        for endpoint in (replace(BOUND,pipe=r'\\remote\pipe\san14-checkpoint-x'),
                         replace(BOUND,pipe=BOUND.pipe+'\0truncated'),
                         replace(BOUND,pipe=BOUND.pipe+'\\subpath'),
                         replace(BOUND,secret=b'\0'*32),replace(BOUND,attempt=b'\0'*16),
                         replace(BOUND,server_pid=True)):
            with self.assertRaises(ChannelError):endpoint.validate()

    def test_explicit_close_cannot_reconnect_or_arm(self):
        self.c.close()
        with self.assertRaises(ChannelError):self.c.reconnect_for_observation()
        with self.assertRaises(ChannelError):self.c.arm_once()

    def interrupted_transport(self,*,completed):
        class KernelDouble:
            calls=[]
            def CreateEventW(self,*args):return 17
            def ReadFile(self,*args):
                self.calls.append('submitted')
                raise KeyboardInterrupt('Synthetic interruption after kernel accepted I/O')
            def CancelIoEx(self,*args):self.calls.append('cancel');return True
            def WaitForSingleObject(self,*args):return 0 if completed else 258
            def GetOverlappedResult(self,*args):
                self.calls.append('completion_checked')
                C.set_last_error(995 if completed else 996)
                return False
            def CloseHandle(self,*args):self.calls.append('close');return True
        t=WinPipeTransport.__new__(WinPipeTransport)
        t.k=KernelDouble();t.handle=16;t.quarantined=False
        return t

    def test_interrupt_after_submission_cancels_and_proves_drain_before_release(self):
        t=self.interrupted_transport(completed=True)
        before=set(channel_module._PINNED_IO)
        with self.assertRaises(KeyboardInterrupt):
            t._io(False,C.create_string_buffer(96),96,time.monotonic()+1)
        self.assertEqual(t.k.calls,['submitted','cancel','completion_checked','close'])
        self.assertFalse(t.quarantined)
        self.assertEqual(set(channel_module._PINNED_IO),before)

    def test_unfinished_cancellation_pins_memory_and_does_not_close_handles(self):
        t=self.interrupted_transport(completed=False)
        before=set(channel_module._PINNED_IO)
        with self.assertRaises(KeyboardInterrupt):
            t._io(False,C.create_string_buffer(96),96,time.monotonic()+1)
        self.assertTrue(t.quarantined)
        t.close()
        self.assertNotIn('close',t.k.calls)
        pinned=set(channel_module._PINNED_IO)-before
        self.assertEqual(len(pinned),1)
        # This test used no kernel I/O. Only remove our own synthetic pin.
        for key in pinned:channel_module._PINNED_IO.pop(key)

    def test_quarantined_transport_forbids_reconnect(self):
        self.t.fail=True;self.t.quarantined=True
        with self.assertRaises(OutcomeUnknown):self.c.arm_once()
        with self.assertRaises(ChannelError):self.c.reconnect_for_observation()
        self.assertTrue(self.c.status()['io_quarantined'])


if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ChannelTests))
    folder=HERE/'checkpoint_session_channel_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    folder.mkdir(parents=True)
    report={'result':'PASS' if result.wasSuccessful() else 'FAIL','tests_run':result.testsRun,
        'failures':len(result.failures),'errors':len(result.errors),'game_access':False,
        'transport':'synthetic','full_native_port_implemented':False,
        'source_sha256':{f:hashlib.sha256((HERE/f).read_bytes()).hexdigest() for f in
                         ('checkpoint_session_channel.py','checkpoint_session_channel_test.py')}}
    (folder/'result.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({'report':str(folder/'result.json'),**report}))
    raise SystemExit(0 if result.wasSuccessful() else 1)
