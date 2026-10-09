"""Offline interface composition: real A client codec, archived diagnostic packets,
and actual owned-process typed export rejection. Never GameReader/ProcessAPI.
"""
import ctypes as C
from datetime import datetime
import hashlib
import io
import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
import a_native_turn_start as start
import a_native_turn_start_control as flow
import a_save_repeat_contract as repeat
import a_save_runtime_contract as wire
import a_save_ipc_client as client

P = Path(__file__).resolve().parent
PRIVATE = P.parents[2] / 'mod_research'
BUILD = PRIVATE/'a_native_turn_runtime_runs/20261009-155107-507427'
ABI = PRIVATE/'a_save_repeat_exports_runs/20261009-155221-088761'
PUBLISHER = PRIVATE/'a_save_repeat_publish_runs/20261009-142815-825524'
PACKETS = PRIVATE/'a_native_turn_runs/20261009-155031-692039/case/normal'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def preparation():
    q = wire.envelope(wire.Prepare, 'Prepare', bytes([7])*32)
    q.pid, q.birth, q.nativeRoomEpoch, q.period, q.epoch = 123, 456, 7, 1, 11
    q.year, q.month, q.day, q.force, q.ruler = 203, 8, 11, 12, 666
    q.roomId[0] = 1
    q.roomInputDigest[0] = 9
    return q


class Transport:
    def __init__(self, endpoint):
        self.endpoint, self.operations, self.generation = endpoint, [], 0
    def close(self):
        pass
    def exchange(self, request, timeout):
        magic, version, op, seq, secret, binding = client.PREFIX.unpack_from(request)
        assert secret == self.endpoint.secret
        self.operations.append(op)
        if op == client.SUBMIT:
            self.generation = int.from_bytes(request[client.PREFIX.size:client.PREFIX.size+8], 'little')
        fields = dict.fromkeys(client.SNAPSHOT_FIELDS, 0)
        fields.update(initialized=1, armed=1, save_status=5, generation=self.generation,
                      completed_requests=self.generation, binds=1, queues=1)
        payload = client.SNAPSHOT_PAYLOAD.pack(*(fields[k] for k in client.SNAPSHOT_FIELDS))
        if op == client.COPY:
            payload += (PACKETS/f'normal-{self.generation}.packet').read_bytes()
        return client.RESPONSE.pack(magic, version, op, seq, client.OK, len(payload), binding) + payload


class Calls:
    def __init__(self, prep, stopped=False):
        self.prep, self.stopped, self.next, self.polls, self.operations = prep, stopped, None, 0, []
    def __call__(self, op, value=None):
        self.operations.append(op)
        if op == 'RequestNext':
            assert self.next is None
            self.next = repeat.decode(repeat.Next, op, bytes(self.prep.nonce), bytes(value))
            return self.next, None
        assert op == 'RepeatSnapshot' and self.next
        self.polls += 1
        q = repeat.envelope(repeat.Snapshot, op, bytes(self.prep.nonce))
        q.request = self.next.request
        q.requested = 1
        q.state = 1 if self.polls == 1 else 3 if self.polls == 2 else 4
        q.activeGeneration = 2 if q.state == 4 else 1
        if q.state >= 3:
            q.hostThread, q.previousArtifactMatched, q.retiredSerial, q.retiredCount = 1, 1, 1, 1
        q.nativeDateMatched = q.state == 4
        q.drainPending = q.state == 3
        if self.stopped and q.state == 3:
            q.stopped = 1
        self.last = q
        return repeat.decode(repeat.Snapshot, op, bytes(self.prep.nonce), bytes(q)), None


class Tests(unittest.TestCase):
    def test_exact_native_build_and_additive_schema(self):
        args = SimpleNamespace(build_run=BUILD, repeat_abi_run=ABI, publisher_build=PUBLISHER)
        built, _, _ = start.verify_native_build(args)
        self.assertIn('a_native_turn_exports.cpp', built['production']['sources'])
        old = args.build_run
        args.build_run = PRIVATE/'a_save_repeat_runtime_runs/20261009-143818-417144'
        with self.assertRaisesRegex(RuntimeError, 'builder family'):
            start.verify_native_build(args)
        args.build_run = old

    def test_real_client_two_artifact_flow(self):
        prep = preparation()
        endpoint = client.Endpoint('\\\\.\\pipe\\san14-a-save-'+'1'*32, 123, 456, bytes([8])*32)
        instances = []
        def factory(e):
            value = Transport(e)
            instances.append(value)
            return value
        channel = client.ASaveClient(endpoint, on_fault=lambda _: None, transport_factory=factory)
        calls = Calls(prep)
        kept, events = [], []
        result = flow.drive(channel, prep, ['mp00000001.s14','mp00000002.s14'], calls,
                            lambda g,n,a: kept.append((g,n,a.sha256)), lambda k,v: events.append(k), pause=lambda _: None)
        self.assertTrue(result['two_native_artifacts'])
        self.assertEqual([g for g,_,_ in kept], [1,2])
        self.assertEqual(instances[0].operations, [client.SUBMIT,client.COPY,client.SNAPSHOT,client.SNAPSHOT,client.SUBMIT,client.COPY])
        self.assertEqual(calls.operations.count('RequestNext'), 1)
        self.assertIn('running-await-human', events)
        self.assertEqual(bytes(calls.next.request.previousSha256).hex(),kept[0][2])
        self.assertFalse(result['game_advance_called'] or result['b_loaded_proven'])
        flow.cleanup_gate(calls.last)
        channel.close()

    def test_stop_running_no_second_submit_or_restore(self):
        prep = preparation()
        endpoint = client.Endpoint('\\\\.\\pipe\\san14-a-save-'+'2'*32, 123, 456, bytes([8])*32)
        transport = Transport(endpoint)
        channel = client.ASaveClient(endpoint, on_fault=lambda _: None, transport_factory=lambda _: transport)
        calls = Calls(prep, True)
        with self.assertRaisesRegex(RuntimeError, 'stopped or failed'):
            flow.drive(channel,prep,['mp00000001.s14','mp00000002.s14'],calls,lambda *_:None,lambda *_:None,pause=lambda _:None)
        self.assertEqual(transport.operations.count(client.SUBMIT),1)
        with self.assertRaisesRegex(RuntimeError,'unresolved'):
            flow.cleanup_gate(calls.last)
        channel.close()

    def test_owned_production_dll_typed_9_10(self):
        info=start.read(BUILD/'result.json')['execution']
        path=Path(info['dll'])
        self.assertEqual(sha(path),info['production']['binaries'][path.name])
        self.assertEqual(sha(path.parent/'checkpoint_planning_hold.dll'),info['production']['binaries']['checkpoint_planning_hold.dll'])
        with os.add_dll_directory(str(path.parent)):
            dll=C.WinDLL(str(path))
        for op,kind in (('RequestNext',repeat.Next),('RepeatSnapshot',repeat.Snapshot)):
            raw=repeat.envelope(kind,op,bytes([7])*32)
            fn=getattr(dll,'ASaveRuntime'+op);fn.argtypes=[C.c_void_p];fn.restype=C.c_uint32
            code=fn(C.byref(raw))
            decoded=repeat.decode(kind,op,bytes([7])*32,bytes(raw))
            self.assertNotEqual(code,0)
            self.assertNotEqual(decoded.header.result,0) # unprepared owned DLL must not authorize work

    def test_two_files_and_native_autosave_change_reported(self):
        before={'old.s14':dict(size=1,sha256='a')}
        artifacts=[dict(filename='mp00000001.s14',size=2,sha256='b'),dict(filename='mp00000002.s14',size=3,sha256='c')]
        after={**before,**{a['filename']:dict(size=a['size'],sha256=a['sha256']) for a in artifacts}}
        self.assertTrue(start.compare_two_files(before,after,artifacts)['originals_unchanged'])
        after['old.s14']=dict(size=1,sha256='changed-by-native-autosave')
        self.assertFalse(start.compare_two_files(before,after,artifacts)['originals_unchanged'])


if __name__=='__main__':
    run=PRIVATE/'a_native_turn_start_test_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
    source_names=['a_native_turn_start.py','a_native_turn_start_control.py','a_native_turn_start_test.py','a_save_runtime_contract.py','a_save_repeat_contract.py','a_save_runtime_control.py','a_save_failure_diagnostic.py','a_save_ipc_client.py','checkpoint_fresh_save_packet.py','checkpoint_fresh_save_binding.py','checkpoint_session_channel.py']
    pins={n:sha(P/n) for n in source_names}
    log=io.StringIO()
    report=unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
    (run/'test.log').write_text(log.getvalue(),encoding='utf-8')
    print(log.getvalue())
    unchanged=all(sha(P/n)==h for n,h in pins.items())
    result=dict(result='PASS' if report.wasSuccessful() and report.testsRun==5 and unchanged else 'FAIL',tests=report.testsRun,
                failures=len(report.failures),errors=len(report.errors),failure_details=[str(x) for x in report.failures+report.errors],sources=pins,sources_unchanged=unchanged,
                game_access=False,real_client_codec=True,transport_fixture=True,native_turn_executed=False,
                private_inputs={str(p):sha(p) for p in [BUILD/'result.json',ABI/'result.json',PUBLISHER/'result.json',PACKETS/'normal-1.packet',PACKETS/'normal-2.packet']})
    (run/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(result=result['result'],path=str(run/'result.json'))))
    raise SystemExit(result['result']!='PASS')
