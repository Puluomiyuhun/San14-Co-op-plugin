"""Actual Python-to-C++ pipe tests against our explicitly launched Session fixture.

Never enumerates or attaches to the game. Secret handshake stays in memory and
is excluded from all result files, exceptions and subprocess command arguments.
"""
from dataclasses import replace
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import queue
import subprocess
import threading
import time
import unittest

from checkpoint_session_channel import *
import checkpoint_session_channel as channel_module

HERE=Path(__file__).resolve().parent
EXE=HERE/'checkpoint_session_ipc_fixture.exe'


class Fixture:
    def __init__(self,*,idle_ms=5000):
        self.p=subprocess.Popen([str(EXE),'--client-pid',str(os.getpid()),'--idle-ms',str(idle_ms),
                                 '--lifetime-ms','15000'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                                creationflags=subprocess.CREATE_NO_WINDOW)
        self.stderr_bytes=0
        def drain():
            while True:
                data=self.p.stderr.read(4096)
                if not data:return
                self.stderr_bytes+=len(data)
        threading.Thread(target=drain,daemon=True).start()
        q=queue.Queue()
        def ready():q.put(self.p.stdout.readline(8193))
        threading.Thread(target=ready,daemon=True).start()
        try:
            line=q.get(timeout=10)
            require(len(line)<=8192 and line.endswith(b'\n'),'Fixture ready unavailable')
            obj=json.loads(line)
            require(obj.get('ready') is True,'Fixture refused initialization')
            self.endpoint=Endpoint(obj['pipe'],obj['server_pid'],int(obj['server_birth']),
                bytes.fromhex(obj['secret']),bytes.fromhex(obj['attempt']),bytes.fromhex(obj['intent']))
            require(self.endpoint.server_pid==self.p.pid,'Fixture PID did not match launched child')
            self.endpoint.validate()
        except BaseException:
            self.close();raise
    def close(self):
        if self.p.poll() is None:self.p.terminate()
        self.p.wait(timeout=5)
        if self.p.stdout:self.p.stdout.close()
        if self.p.stderr:self.p.stderr.close()


class NativeTests(unittest.TestCase):
    def fixture(self,**kwargs):
        f=Fixture(**kwargs);self.addCleanup(f.close);return f
    def channel(self,f,**kwargs):
        c=SessionChannel(f.endpoint,**kwargs);self.addCleanup(c.close);return c
    def reconnect(self,c):
        # Explicit observation reconnection, no command resend. A server may
        # still be draining its preceding local connection for a few ms.
        end=time.monotonic()+2
        while True:
            try:return c.reconnect_for_observation()
            except ChannelError:
                if c.transport is not None or time.monotonic()>=end:raise
                time.sleep(.02)

    def test_actual_session_arm_progress_stop_over_pipe(self):
        f=self.fixture();c=self.channel(f)
        before=c.snapshot()
        self.assertEqual(before.fields['armed'],0)
        armed=c.arm_once()
        self.assertEqual(armed.fields['armed'],1)
        end=time.monotonic()+3
        report=armed
        while not report.fields['identity_ready'] and time.monotonic()<end:
            time.sleep(.02);report=c.snapshot()
        self.assertEqual(report.fields['identity_ready'],1)
        self.assertEqual(report.fields['lifecycle_ready'],1)
        self.assertEqual(report.fields['bytes_ready'],1)
        self.assertFalse(report.progress()['native_load_complete'])
        stopped=c.stop_keep_observing()
        self.assertEqual(stopped.fields['stop_requested'],1)
        self.assertEqual(c.snapshot().fields['hooks_restored'],0)

    def test_lost_arm_ack_reconnect_only_observes_real_session(self):
        f=self.fixture()
        class DropArmReply(WinPipeTransport):
            def exchange(self,raw,timeout):
                result=super().exchange(raw,timeout)
                if REQUEST.unpack(raw)[2]==ARM_ONCE:
                    raise OutcomeUnknown('Injected lost acknowledgement after real server execution')
                return result
        c=self.channel(f,transport_factory=DropArmReply)
        with self.assertRaises(OutcomeUnknown):c.arm_once()
        report=self.reconnect(c)
        self.assertEqual(report.fields['stop_requested'],1)
        with self.assertRaises(ChannelError):c.arm_once()
        self.assertEqual(report.fields['hooks_restored'],0)

    def test_server_independently_rejects_second_arm(self):
        f=self.fixture();c=self.channel(f);c.arm_once()
        with self.assertRaises(NativeRejected):c._request(ARM_ONCE)
        self.assertEqual(c.last.fields['status'],5)

    def test_server_rejects_wrong_secret(self):
        f=self.fixture();t=WinPipeTransport(f.endpoint);self.addCleanup(t.close)
        req=REQUEST.pack(MAGIC,VERSION,SNAPSHOT,1,b'x'*32,f.endpoint.attempt,f.endpoint.intent)
        result=RESPONSE.unpack(t.exchange(req,2))
        self.assertEqual(result[5],2)
        self.assertEqual(result[9],0) # armed

    def test_server_rejects_wrong_intent(self):
        f=self.fixture();t=WinPipeTransport(f.endpoint);self.addCleanup(t.close)
        req=REQUEST.pack(MAGIC,VERSION,ARM_ONCE,1,f.endpoint.secret,f.endpoint.attempt,b'x'*16)
        self.assertEqual(RESPONSE.unpack(t.exchange(req,2))[5],3)

    def test_server_rejects_replayed_sequence(self):
        f=self.fixture();c=self.channel(f);c.snapshot()
        req=REQUEST.pack(MAGIC,VERSION,ARM_ONCE,1,f.endpoint.secret,f.endpoint.attempt,f.endpoint.intent)
        self.assertEqual(RESPONSE.unpack(c.transport.exchange(req,2))[5],4)

    def test_client_checks_server_birth_before_sending_secret(self):
        f=self.fixture()
        with self.assertRaises(ChannelError):
            WinPipeTransport(replace(f.endpoint,server_birth=f.endpoint.server_birth+1))

    def test_client_checks_server_pid_before_sending_secret(self):
        f=self.fixture()
        with self.assertRaises(ChannelError):
            WinPipeTransport(replace(f.endpoint,server_pid=os.getpid()))

    def test_idle_deadline_stops_and_preserves_observation(self):
        f=self.fixture(idle_ms=200);c=self.channel(f);c.snapshot()
        time.sleep(.35)
        with self.assertRaises(ChannelError):c.snapshot()
        report=self.reconnect(c)
        self.assertEqual(report.fields['stop_requested'],1)
        self.assertEqual(report.fields['armed'],0)
        with self.assertRaises(ChannelError):c.arm_once()

    def test_partial_frame_disconnect_never_arms(self):
        f=self.fixture();t=WinPipeTransport(f.endpoint)
        req=REQUEST.pack(MAGIC,VERSION,ARM_ONCE,1,f.endpoint.secret,f.endpoint.attempt,f.endpoint.intent)
        raw=C.create_string_buffer(req[:40]);t._io(True,raw,40,time.monotonic()+1);t.close()
        time.sleep(.05)
        c=self.channel(f);report=c.snapshot()
        self.assertEqual(report.fields['armed'],0)
        self.assertEqual(report.fields['stop_requested'],1)

    def test_real_pending_read_timeout_is_canceled_before_buffer_release(self):
        f=self.fixture();t=WinPipeTransport(f.endpoint);self.addCleanup(t.close)
        before=set(channel_module._PINNED_IO)
        # No request sent: server and client both wait to read, so this executes
        # actual ERROR_IO_PENDING/CancelIoEx instead of a fake timeout.
        with self.assertRaises(OutcomeUnknown):
            t._io(False,C.create_string_buffer(96),96,time.monotonic()+.05)
        self.assertFalse(t.quarantined)
        self.assertEqual(set(channel_module._PINNED_IO),before)


if __name__=='__main__':
    require(EXE.is_file(),'Own Session IPC fixture must be built first')
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(NativeTests))
    folder=HERE/'checkpoint_session_channel_native_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    folder.mkdir(parents=True)
    names=['checkpoint_session_channel.py','checkpoint_session_channel_native_test.py',
           'checkpoint_session_ipc.h','checkpoint_session_ipc.cpp',
           'checkpoint_session_ipc_fixture.cpp','checkpoint_session_ipc_fixture.exe']
    report={'result':'PASS' if result.wasSuccessful() else 'FAIL','tests_run':result.testsRun,
        'failures':len(result.failures),'errors':len(result.errors),
        'game_access':False,'own_child_processes_only':True,
        'transport':'actual Windows named pipe to actual Session with synthetic game objects',
        'secret_handshake_logged':False,'full_native_port_implemented':False,
        'source_sha256':{f:hashlib.sha256((HERE/f).read_bytes()).hexdigest() for f in names}}
    (folder/'result.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({'report':str(folder/'result.json'),**report}))
    raise SystemExit(0 if result.wasSuccessful() else 1)
