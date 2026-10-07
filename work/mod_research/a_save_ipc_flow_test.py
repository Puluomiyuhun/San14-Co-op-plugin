"""Dynamic Room reservation -> real owned A IPC -> TLS/journal, never SAN14.

Use --build-run with this turn's explicit a_save_ipc_test_build output. A single
prepared child owns both native saves, and receives each request only AFTER
its Room reservation. World observations and guest completion remain MODEL.
"""
from dataclasses import replace
from datetime import datetime
import argparse
import ctypes as C
from ctypes import wintypes as W
import json
import os
from pathlib import Path
import queue
import re
import secrets
import struct
import subprocess
import threading
import time
import unittest

import a_save_ipc_client as ipc
from checkpoint_fresh_save_binding import FreshSaveBinding
from checkpoint_fresh_save_binding_test import (Fixture, OwnedServer, manifest,
    make_coordinator, model_world, complete_model)
from checkpoint_room_lifecycle import CheckpointRoom
from checkpoint_room_client import RoomConnection
from checkpoint_journal import CheckpointJournal
from checkpoint_transfer import receive_checkpoint
from authoritative_sync import CheckpointReceiver, digest, scope_from_room, sha
from room_transport import Client, make_certificate

HERE = Path(__file__).resolve().parent
BUILD = OUTPUT = BUILD_EVIDENCE = None
EVIDENCE = []
BOOTSTRAP = struct.Struct('<32s32sQ16s')
assert BOOTSTRAP.size == 88


def strict_json(raw):
    def pairs(values):
        result = {}
        for key, value in values:
            if key in result: raise ValueError('Duplicate private bootstrap key')
            result[key] = value
        return result
    def constant(_): raise ValueError('Nonfinite private bootstrap value')
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)


def validate_build(folder):
    raw = (folder / 'result.json').read_bytes()
    report = strict_json(raw)
    ipc.require(report.get('schema') == 'san14.a-save-ipc-build.v1' and report.get('result') == 'PASS'
        and report.get('sources_unchanged') is True and report.get('game_access') is False,
        'Explicit A IPC build is not a passing offline source-stable build')
    sources = report.get('sources')
    required = {'a_save_ipc.cpp', 'a_save_ipc.h', 'a_save_ipc_fixture.cpp', 'a_save_user_owner.cpp'}
    ipc.require(type(sources) is dict and required <= set(sources) and len(sources) <= 128,
        'A IPC build has no complete source fingerprints')
    for name, expected in sources.items():
        ipc.require(type(name) is str and re.fullmatch('[A-Za-z0-9_][A-Za-z0-9_.-]*', name) is not None
            and Path(name).name == name and Path(name).suffix in ('.h', '.cpp', '.asm', '.py')
            and type(expected) is str and re.fullmatch('[0-9a-f]{64}', expected) is not None,
            'Invalid A IPC source identity')
        ipc.require(sha((HERE / name).read_bytes()) == expected, 'A IPC build source changed: ' + name)
    ipc.require(sha((folder / 'fixture.exe').read_bytes()) == report.get('fixture_sha256'),
        'A IPC owned executable changed')
    return dict(result_sha256=sha(raw), fixture_sha256=report['fixture_sha256'],
        source_count=len(sources), sources_match_current=True,
        diagnostic_consistency_only=True, game_access=False)


class OwnedFixture:
    """Only an approved child process; its stdio does not carry Submit/Copy."""
    def __init__(self, folder, native_room_id, native_room_epoch, *, mode=None):
        self.process = None
        self.endpoint = self.final = None
        self._pin = None
        self._threads = []
        self._messages = queue.Queue(maxsize=8)
        self._done = threading.Event()
        self._io_error = None
        self._closed = False
        self.stderr_bytes = 0
        self.cleanup_errors = []
        self.k = C.WinDLL('kernel32', use_last_error=True)
        for name, result, args in (
            ('CreateFileW', W.HANDLE, [W.LPCWSTR, W.DWORD, W.DWORD, C.c_void_p, W.DWORD, W.DWORD, W.HANDLE]),
            ('CloseHandle', W.BOOL, [W.HANDLE]),
            ('GetProcessTimes', W.BOOL, [W.HANDLE, C.POINTER(W.FILETIME), C.POINTER(W.FILETIME),
                                        C.POINTER(W.FILETIME), C.POINTER(W.FILETIME)])):
            fn = getattr(self.k, name); fn.restype = result; fn.argtypes = args
        executable = BUILD / 'fixture.exe'
        folder.mkdir(parents=True, exist_ok=False)
        try:
            for item in (executable, *executable.parents):
                info = item.lstat()
                ipc.require(not item.is_symlink() and not (getattr(info, 'st_file_attributes', 0) & 0x400),
                    'Owned IPC executable cannot use reparse paths')
            self._pin = self.k.CreateFileW(str(executable), 0x80000000, 1, None, 3, 0, None)
            ipc.require(self._pin not in (None, C.c_void_p(-1).value), 'Cannot pin own IPC executable')
            ipc.require(sha(executable.read_bytes()) == BUILD_EVIDENCE['fixture_sha256'], 'Pinned IPC binary differs')
            ipc.require(mode in (None, 'permit-stop'), 'Unknown owned fixture mode')
            args = [str(executable), str(folder), BUILD_EVIDENCE['fixture_sha256'], str(os.getpid())]
            if mode is not None: args.append(mode)
            self.process = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                bufsize=0, creationflags=subprocess.CREATE_NO_WINDOW)
            for target in (self._stdout, self._stderr):
                thread = threading.Thread(target=target, daemon=True); self._threads.append(thread); thread.start()
            prepared = self.message()
            birth = self.birth()
            ipc.require(prepared.get('schema') == 'san14.a-save-ipc-fixture.v1' and
                prepared.get('event') == 'PREPARED' and prepared.get('pid') == self.process.pid and
                prepared.get('birth') == str(birth) and prepared.get('game_access') is False,
                'Owned IPC child identity differs')
            secret, nonce = secrets.token_bytes(32), secrets.token_bytes(16)
            bootstrap = BOOTSTRAP.pack(secret, native_room_id, native_room_epoch, nonce)
            ipc.require(self.process.stdin.write(bootstrap) == len(bootstrap), 'Private bootstrap incomplete')
            self.process.stdin.flush()
            ready = self.message()
            pipe = '\\\\.\\pipe\\san14-a-save-' + nonce.hex()
            ipc.require(ready.get('event') == 'READY' and ready.get('pipe_name') == pipe and
                ready.get('pid') == self.process.pid and ready.get('birth') == str(birth) and
                ready.get('source_kind') == 'FIXTURE_ONLY' and ready.get('capabilities') == 0,
                'Prepared native pipe does not match private bootstrap')
            self.endpoint = ipc.Endpoint(pipe, self.process.pid, birth, secret)
            self.endpoint.validate()
        except BaseException:
            self.close()
            raise

    def _stdout(self):
        try:
            while True:
                raw = self.process.stdout.readline(8193)
                if not raw: break
                if len(raw) > 8192 or not raw.endswith(b'\n'):
                    self._io_error = 'BAD_PRIVATE_FRAME'; continue
                row = strict_json(raw)
                if type(row) is not dict: raise ValueError('Bad private event')
                self._messages.put_nowait(row)
        except BaseException:
            self._io_error = 'PRIVATE_OUTPUT_FAILED'
        finally:
            self._done.set()

    def _stderr(self):
        try:
            while True:
                raw = self.process.stderr.read(4096)
                if not raw: return
                self.stderr_bytes += len(raw)
        except BaseException:
            self._io_error = 'PRIVATE_STDERR_FAILED'

    def birth(self):
        b, e, k, u = W.FILETIME(), W.FILETIME(), W.FILETIME(), W.FILETIME()
        ipc.require(self.k.GetProcessTimes(W.HANDLE(int(self.process._handle)),
            C.byref(b), C.byref(e), C.byref(k), C.byref(u)), 'Cannot verify owned process birth')
        return (b.dwHighDateTime << 32) | b.dwLowDateTime

    def message(self, timeout=10):
        deadline = time.monotonic()+timeout
        while time.monotonic() < deadline:
            ipc.require(self._io_error is None, 'Owned IPC output failed; raw output withheld')
            try: return self._messages.get(timeout=.05)
            except queue.Empty:
                ipc.require(not self._done.is_set(), 'Owned IPC ended before expected event')
        raise ipc.ASaveOutcomeUnknown('Owned IPC event timed out')

    def close(self):
        if self._closed: return
        if self.process is not None:
            try:
                if self.process.stdin: self.process.stdin.close()
                self.process.wait(timeout=5)
            except BaseException:
                self.cleanup_errors.append('OWN_FIXTURE_NORMAL_EXIT_UNCONFIRMED')
                if self.process.poll() is None: self.process.terminate()
                try: self.process.wait(timeout=5)
                except BaseException: self.cleanup_errors.append('OWN_FIXTURE_EXIT_UNCONFIRMED')
            for thread in self._threads:
                thread.join(timeout=2)
                if thread.is_alive(): self.cleanup_errors.append('OWN_FIXTURE_READER_UNCONFIRMED')
            while not self._messages.empty():
                row = self._messages.get_nowait()
                if row.get('event') == 'FINAL': self.final = row
            for stream in (self.process.stdout, self.process.stderr):
                if stream: stream.close()
        if self._pin not in (None, C.c_void_p(-1).value): self.k.CloseHandle(self._pin)
        self._closed = True


def fake_reply(raw, *, status=0, snapshot=None, packet=b'', alter=None):
    magic, version, op, seq, _, binding = ipc.PREFIX.unpack_from(raw)
    generation = ipc.SAVE_REQUEST.unpack_from(raw, ipc.PREFIX.size)[0]
    row = dict(owner_error=0, initialized=1, armed=1, stopped=0, save_status=1,
        save_error=0, completed_requests=0, binds=0, queues=0, user_subset_held=0,
        generation=generation, active_scopes=0, capabilities=0)
    row.update(snapshot or {})
    payload = ipc.SNAPSHOT_PAYLOAD.pack(*(row[k] for k in ipc.SNAPSHOT_FIELDS)) + packet
    fields = [magic, version, op, seq, status, len(payload), binding]
    if alter: alter(fields)
    return ipc.RESPONSE.pack(*fields)+payload


class FakeTransport:
    def __init__(self, endpoint, respond=None):
        self.sent=[]; self.closed=False; self.quarantined=False
        self.respond=respond or (lambda raw: fake_reply(raw))
    def exchange(self, raw, timeout):
        self.sent.append(raw)
        return self.respond(raw)
    def close(self): self.closed=True


class ClientTests(unittest.TestCase):
    def make(self, respond=None):
        f=Fixture(); reservation=f.reserve(); faults=[]
        t=FakeTransport(None, respond)
        c=ipc.ASaveClient(ipc.Endpoint('\\\\.\\pipe\\san14-a-save-'+'1'*32, 1, 1, b's'*32),
            on_fault=faults.append, transport_factory=lambda _:t)
        self.addCleanup(c.close)
        return f,reservation,c,t,faults

    def test_lost_submit_reply_consumes_generation_and_holds(self):
        def lost(_): raise ipc.ASaveOutcomeUnknown('Synthetic lost acknowledgement')
        _,r,c,t,faults=self.make(lost)
        with self.assertRaises(ipc.ASaveOutcomeUnknown):c.submit(r)
        with self.assertRaises(ipc.ASaveChannelError):c.submit(r)
        self.assertEqual(len(t.sent),1);self.assertTrue(t.closed);self.assertEqual(len(faults),1)

    def test_stale_sequence_binding_or_unsupported_flags_close_channel(self):
        mutations=(lambda fields:fields.__setitem__(3,fields[3]+1),
            lambda fields:fields.__setitem__(6,b'x'*32))
        for mutate in mutations:
            _,r,c,t,faults=self.make(lambda raw:fake_reply(raw,alter=mutate))
            with self.assertRaises(ipc.ASaveChannelError):c.submit(r)
            self.assertTrue(t.closed);self.assertEqual(len(faults),1)
        for snapshot in ({'capabilities':1},{'stopped':1},{'owner_error':1},{'save_error':1}):
            _,r,c,t,faults=self.make(lambda raw:fake_reply(raw,snapshot=snapshot))
            with self.assertRaises(ipc.ASaveChannelError):c.submit(r)
            self.assertTrue(t.closed)

    def test_copy_not_ready_polls_without_resubmitting(self):
        def respond(raw):
            op=ipc.PREFIX.unpack_from(raw)[2]
            return fake_reply(raw,status=7 if op==ipc.COPY else 0)
        _,r,c,t,_=self.make(respond);c.submit(r)
        self.assertIsNone(c.copy(1));self.assertIsNone(c.copy(1))
        self.assertEqual([ipc.PREFIX.unpack_from(raw)[2] for raw in t.sent],[ipc.SUBMIT,ipc.COPY,ipc.COPY])

    def test_partial_copy_and_wrong_generation_are_terminal(self):
        for response in (lambda raw:fake_reply(raw,packet=b'x'*285),
                         lambda raw:fake_reply(raw,snapshot={'generation':2})):
            _,r,c,t,faults=self.make(response)
            with self.assertRaises(ipc.ASaveChannelError):c.submit(r)
            self.assertTrue(t.closed);self.assertEqual(len(faults),1)

    def test_explicit_stop_notifies_bound_room_and_validates_current_owner(self):
        _,r,c,t,faults=self.make(lambda raw:fake_reply(raw,snapshot={'stopped':1}))
        result=c.stop()
        self.assertEqual(result['stopped'],1);self.assertIn('A_IPC_STOP_REQUESTED',faults)
        with self.assertRaises(ipc.ASaveChannelError):c.submit(r)
        self.assertEqual(len(t.sent),1)

    def test_artifact_timeout_latches_without_native_replay(self):
        def respond(raw):
            return fake_reply(raw,status=7 if ipc.PREFIX.unpack_from(raw)[2]==ipc.COPY else 0)
        _,r,c,t,_=self.make(respond);c.submit(r)
        with self.assertRaises(ipc.ASaveOutcomeUnknown):c.wait_artifact(1,timeout=.02)
        self.assertEqual(sum(ipc.PREFIX.unpack_from(raw)[2]==ipc.SUBMIT for raw in t.sent),1)
        self.assertTrue(t.closed)


class NativeFlowTests(unittest.TestCase):
    def setUp(self):
        if BUILD is None: self.skipTest('Explicit --build-run required for owned native IPC checks')

    def closed_owner(self,fixture,submits,completed=None):
        self.assertEqual(fixture.cleanup_errors,[])
        self.assertEqual(fixture.process.returncode,0)
        self.assertIsNotNone(fixture.final)
        self.assertEqual(fixture.final['result'],'PASS')
        self.assertIs(fixture.final['game_access'],False)
        self.assertEqual(fixture.final['submits'],submits)
        if completed is not None:self.assertEqual(fixture.final['completed'],completed)
        self.assertEqual(fixture.final['owner_stopped'],1)
        self.assertEqual(fixture.final['active'],0)
        self.assertEqual(fixture.final['checks_failed'],0)
        self.assertIs(fixture.final['ipc_closed'],True)

    def test_room_reserve_precedes_two_native_submits_then_tls_and_sqlite(self):
        folder=OUTPUT/'two-period-flow';folder.mkdir()
        room=CheckpointRoom(manifest());servers=[];clients=[];fixture=channel=None
        trace=[];periods=[];holder={}
        cert,key,fp=make_certificate(folder/'tls')
        def serve(owner):
            server=OwnedServer(('127.0.0.1',0),owner,cert,key)
            thread=threading.Thread(target=server.serve_forever,kwargs={'poll_interval':.02},daemon=True)
            servers.append((server,thread));thread.start();return server.server_address[1]
        def connect(port,method,credential):
            cls=Client if method=='checkpoint_download' else RoomConnection
            c=cls('127.0.0.1',port,fp,dict(method=method,credential=credential,profile=room.manifest['profile']))
            clients.append(c);return c
        def local_copy(generation):
            trace.append(dict(event='COPY_FROM_CURRENT_NATIVE_OWNER',generation=generation))
            return holder['channel'].wait_artifact(generation)
        try:
            port=serve(room);download_port=serve(room.download_endpoint)
            a=connect(port,'host',room.host_token);b=connect(port,'join',room.invite)
            for cl,force in ((a,12),(b,2)):
                self.assertTrue(cl.request(dict(action='select_force',force_id=force,
                    request_id=secrets.token_hex(16),expected_revision=room.revision))['ok'])
            for cl in (a,b):
                self.assertTrue(cl.request(dict(action='confirm_force',request_id=secrets.token_hex(16),
                    expected_revision=room.revision))['ok'])
            coordinator=make_coordinator(room)
            native_id=bytes.fromhex(digest(scope_from_room(room)));native_epoch=secrets.randbits(64) or 1
            binding=FreshSaveBinding(room,coordinator,native_room_id=native_id,native_room_epoch=native_epoch,
                artifact_reader=local_copy,source_kind='FIXTURE_ONLY')
            fixture=OwnedFixture(folder/'native',native_id,native_epoch)
            channel=ipc.ASaveClient(fixture.endpoint,on_fault=binding.hold);holder['channel']=channel
            initial=channel.snapshot();self.assertEqual(initial['completed_requests'],0)
            self.assertEqual(initial['binds'],0);self.assertEqual(initial['queues'],0)
            original_connections={p:r['connection'] for p,r in room.players.items()}
            for generation in (1,2):
                for cl in (a,b):
                    self.assertTrue(cl.request(dict(action='period_ready',epoch=coordinator.epoch,ready=True))['ok'])
                coordinator.begin_simulation(coordinator.seal_inputs());world=model_world(coordinator)
                reservation=binding.reserve(generation,f'mp{generation:08x}.s14',world)
                trace.append(dict(event='ROOM_RESERVED',generation=generation,binding_sha256=reservation.binding_sha256))
                submitted=channel.submit(reservation)
                self.assertEqual(submitted['generation'],generation)
                trace.append(dict(event='NATIVE_SUBMIT_ACK',generation=generation))
                def observe():
                    current=channel.snapshot()
                    self.assertEqual(current['stopped'],0);self.assertEqual(current['owner_error'],0)
                    trace.append(dict(event='MODEL_WORLD_OBSERVATION_AFTER_NATIVE_COPY',generation=generation))
                    return world
                package=binding.publish(generation,observe)
                trace.append(dict(event='ROOM_PUBLISHED',generation=generation,checkpoint_id=package.checkpoint_id))
                ticket=b.request(dict(action='checkpoint_download_offer',checkpoint_id=package.checkpoint_id))
                self.assertTrue(ticket['ok'])
                transfer_channel=connect(download_port,'checkpoint_download',ticket['download_token'])
                receiver=CheckpointReceiver(ticket['manifest'],package.checkpoint_id,coordinator.scope,
                    coordinator.epoch,coordinator.period,package.manifest['cut'])
                transfer=receive_checkpoint(transfer_channel,receiver,action='checkpoint_chunk')
                self.assertEqual(transfer['parts'],package._parts)
                path=folder/f'guest-{generation}.sqlite'
                journal=CheckpointJournal(path,coordinator.scope,package.manifest,package.checkpoint_id,
                    coordinator.epoch,coordinator.period,package.manifest['cut'],coordinator.attachments,create=True)
                journal.stage(receiver)
                reopened=CheckpointJournal(path,coordinator.scope,package.manifest,package.checkpoint_id,
                    coordinator.epoch,coordinator.period,package.manifest['cut'],coordinator.attachments)
                self.assertEqual(reopened.status()['status'],'STAGED')
                self.assertEqual(reopened.verified_parts(),transfer['parts'])
                self.assertEqual({p:r['connection'] for p,r in room.players.items()},original_connections)
                for cl in (a,b):self.assertTrue(cl.request({'action':'status'})['ok'])
                periods.append(dict(generation=generation,checkpoint_id=package.checkpoint_id,
                    save_sha256=package.manifest['parts']['world.s14']['sha256'],
                    bytes=len(transfer['parts']['world.s14']),journal='STAGED_REOPEN_VERIFIED',
                    world_observation='MODEL_ONLY',guest_load_receipt='MODEL_ONLY'))
                complete_model(coordinator,package,receiver)
            self.assertEqual(coordinator.period,3)
            self.assertNotEqual(periods[0]['save_sha256'],periods[1]['save_sha256'])
            end=channel.snapshot();self.assertEqual(end['completed_requests'],2)
            self.assertEqual(channel.status()['submitted_generations'],[1,2])
            self.assertEqual([row['event'] for row in trace],
                ['ROOM_RESERVED','NATIVE_SUBMIT_ACK','COPY_FROM_CURRENT_NATIVE_OWNER',
                 'MODEL_WORLD_OBSERVATION_AFTER_NATIVE_COPY','ROOM_PUBLISHED']*2)
            channel.stop()
        finally:
            if channel:channel.close()
            if fixture:fixture.close()
            room.close_checkpoints()
            for cl in reversed(clients):cl.close()
            for server,thread in reversed(servers):
                server.shutdown();thread.join(timeout=5)
                self.assertFalse(thread.is_alive());self.assertTrue(server.wait_handlers());server.server_close()
        self.closed_owner(fixture,2,2)
        EVIDENCE.append(dict(case='DYNAMIC_TWO_PERIOD_OWNER_PIPE_TLS_JOURNAL',trace=trace,periods=periods,
            native_child_count=1,native_submits=2,packets_precreated=False,
            dynamic_fixture_submit_binding_validated=True,game_access=False,actual_two_games=False,
            native_game_business='TEST_DOUBLES',full_world_verified=False,native_gameplay_enabled=False,
            resources_closed=True,owner_final=fixture.final))

    def test_lost_real_submit_ack_holds_room_and_never_resubmits(self):
        f=Fixture();reservation=f.reserve();fixture=OwnedFixture(OUTPUT/'lost-submit',
            reservation.request['room_id'],reservation.request['room_epoch'])
        sends=[]
        class LostAck(ipc.ASavePipeTransport):
            def exchange(self,raw,timeout):
                result=super().exchange(raw,timeout)
                op=ipc.PREFIX.unpack_from(raw)[2];sends.append(op)
                if op==ipc.SUBMIT:raise ipc.ASaveOutcomeUnknown('Owned test drops acknowledged Submit reply')
                return result
        channel=ipc.ASaveClient(fixture.endpoint,on_fault=f.binding.hold,transport_factory=LostAck)
        try:
            with self.assertRaises(ipc.ASaveOutcomeUnknown):channel.submit(reservation)
            with self.assertRaises(ipc.ASaveChannelError):channel.submit(reservation)
            self.assertEqual(sends.count(ipc.SUBMIT),1)
            self.assertIsNotNone(f.binding.status()['held_reason'])
            self.assertTrue(f.room.checkpoint_status()['closed'])
        finally:
            channel.close();fixture.close()
        self.closed_owner(fixture,1)
        self.assertIn(fixture.final['completed'],(0,1))
        EVIDENCE.append(dict(case='REAL_SUBMIT_ACK_LOST',native_submit_frames=1,
            automatic_retry=False,room_closed=True,game_access=False,owner_final=fixture.final))

    def test_current_owner_stop_invalidates_previously_completed_artifact(self):
        f=Fixture();reservation=f.reserve();fixture=OwnedFixture(OUTPUT/'stop-after-save',
            reservation.request['room_id'],reservation.request['room_epoch'])
        channel=ipc.ASaveClient(fixture.endpoint,on_fault=f.binding.hold)
        try:
            channel.submit(reservation);artifact=channel.wait_artifact(1)
            self.assertEqual(artifact.report['stop_after_commit'],0)
            self.assertEqual(artifact.report['status'],5)
            channel.stop()
            with self.assertRaises(ipc.ASaveChannelError):channel.copy(1)
            self.assertTrue(f.room.checkpoint_status()['closed'])
        finally:
            channel.close();fixture.close()
        self.closed_owner(fixture,1,1)
        EVIDENCE.append(dict(case='OWNER_STOP_REVOKES_OLD_COMPLETE_PACKET',game_access=False,
            room_closed=True,old_packet_republished=False,owner_final=fixture.final))

    def test_kernel_server_identity_is_verified_before_any_native_command(self):
        for field in ('server_pid','server_birth'):
            f=Fixture();reservation=f.reserve();fixture=OwnedFixture(OUTPUT/('wrong-'+field),
                reservation.request['room_id'],reservation.request['room_epoch'])
            try:
                bad=replace(fixture.endpoint,**{field:getattr(fixture.endpoint,field)+1})
                with self.assertRaises(RuntimeError):ipc.ASaveClient(bad,on_fault=f.binding.hold)
                self.assertTrue(f.room.checkpoint_status()['closed'])
            finally:fixture.close()
            self.closed_owner(fixture,0,0)

    def test_real_secret_and_sequence_replay_rejections_hold_room(self):
        for fault in ('secret','sequence'):
            f=Fixture();reservation=f.reserve();fixture=OwnedFixture(OUTPUT/('invalid-'+fault),
                reservation.request['room_id'],reservation.request['room_epoch'])
            endpoint=replace(fixture.endpoint,secret=b'z'*32) if fault=='secret' else fixture.endpoint
            channel=ipc.ASaveClient(endpoint,on_fault=f.binding.hold)
            try:
                if fault=='sequence':
                    channel.snapshot()
                    channel._sequence=0  # Own client fault injection, not a production API.
                with self.assertRaises(RuntimeError):channel.snapshot()
                self.assertTrue(f.room.checkpoint_status()['closed'])
            finally:channel.close();fixture.close()
            self.closed_owner(fixture,0,0)

    def test_shutdown_during_native_permit_prevents_submit(self):
        f=Fixture();reservation=f.reserve();fixture=OwnedFixture(OUTPUT/'permit-stop',
            reservation.request['room_id'],reservation.request['room_epoch'],mode='permit-stop')
        channel=ipc.ASaveClient(fixture.endpoint,on_fault=f.binding.hold)
        try:
            with self.assertRaises(RuntimeError):channel.submit(reservation)
            self.assertTrue(f.room.checkpoint_status()['closed'])
            with self.assertRaises(ipc.ASaveChannelError):channel.submit(reservation)
        finally:channel.close();fixture.close()
        self.closed_owner(fixture,0,0)
        EVIDENCE.append(dict(case='SHUTDOWN_DURING_PERMIT',native_submits=0,native_completed=0,
            room_closed=True,game_access=False,owner_final=fixture.final))


def main():
    global BUILD,OUTPUT,BUILD_EVIDENCE
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build-run','--ipc-run',dest='build_run',type=Path)
    args=parser.parse_args()
    if args.build_run:
        BUILD=args.build_run.resolve()
        try:BUILD_EVIDENCE=validate_build(BUILD)
        except (OSError,ValueError,ipc.ASaveChannelError) as exc:parser.error(str(exc))
    OUTPUT=HERE/'a_save_ipc_flow_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    OUTPUT.mkdir(parents=True)
    source_names=('a_save_ipc_client.py','a_save_ipc_flow_test.py','checkpoint_fresh_save_binding.py',
        'checkpoint_fresh_save_packet.py','checkpoint_session_channel.py')
    if BUILD is not None:source_names+=('a_save_ipc.cpp','a_save_ipc.h','a_save_ipc_fixture.cpp')
    before={name:sha((HERE/name).read_bytes()) for name in source_names}
    suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(cls)
        for cls in (ClientTests,NativeFlowTests))
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    unchanged=all(sha((HERE/name).read_bytes())==expected for name,expected in before.items())
    passed=result.wasSuccessful() and unchanged
    report=dict(schema='san14.a-save-ipc-flow.v1',result='PASS' if passed else 'FAIL',
        tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),
        build_evidence=BUILD_EVIDENCE,cases=EVIDENCE,game_access=False,actual_two_games=False,
        complete_game_pipeline_validated=False,native_gameplay_enabled=False,full_world_verified=False,
        test_methods=[cls.__name__+'.'+name for cls in (ClientTests,NativeFlowTests)
            for name in unittest.defaultTestLoader.getTestCaseNames(cls)],
        sources_unchanged=unchanged,source_sha256=before)
    path=OUTPUT/'result.json';path.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(result=report['result'],path=str(path))))
    return 0 if passed else 1


if __name__=='__main__':raise SystemExit(main())
