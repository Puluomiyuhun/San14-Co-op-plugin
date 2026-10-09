"""Actual local TLS startup/closing; no game, process lookup or native calls."""
from datetime import datetime
from pathlib import Path
from copy import deepcopy
import hashlib
import io
import json
import socket
import ssl
import sys
import time
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];PRIVATE=ROOT.parent/'mod_research'
sys.path[:0]=[str(PRIVATE/'python_deps'),str(ROOT/'outputs/san14-link')]
import observed_room_service as service
import observed_host_start as host
from checkpoint_fresh_save_binding_test import manifest
from human_rules_activation_room import GAME_SHA,rules
from authoritative_sync import digest

OUTPUT=None


class Tests(unittest.TestCase):
    def setUp(self):self.owner=None;self.guest=None
    def tearDown(self):
        if self.guest:self.guest.close()
        if self.owner:
            result=self.owner.close();self.assertTrue(result['network_closed'],result)
    def start(self):
        m=manifest();m['profile']['game_sha256']=GAME_SHA;m['profile']['rules_sha256']=digest(rules(0,0))
        self.owner=service.HostService(m,dict(year=203,month=8,day=11,phase='PLANNING_BOUNDARY'),
            directory=OUTPUT/self._testMethodName,listen_host='127.0.0.1',advertise_host='127.0.0.1',
            control_port=0,download_port=0)
        return self.owner
    def connect(self):
        self.guest=service.join_guest(self.owner.invitation)
        return self.owner.wait_bound(5)

    def test_real_tls_selection_context_and_shutdown(self):
        o=self.start();c=self.connect();ctx=self.guest.wait_context(5)
        self.assertEqual(ctx['scope'],c.scope);self.assertEqual(ctx['attachments'],c.attachments)
        self.assertEqual(ctx['phase'],'PLANNING');self.assertIsNone(ctx['manifest'])
        self.assertEqual(c.scope['bindings'],{'A':{'force_id':12,'main_district_id':11},'B':{'force_id':2,'main_district_id':2}})
        self.assertEqual(self.guest.control.player_id,'B')
        self.assertFalse(o._seal_started)
        # Close while the external guest is idle; owned sockets are drained.
        result=o.close();self.assertTrue(result['network_closed'],result);self.assertFalse(result['native_cleanup_claimed'])
        with self.assertRaises(Exception):self.guest.control.request({'action':'status'})

    def test_wrong_fingerprint_rejected_before_guest_admission(self):
        o=self.start();bad=deepcopy(o.invitation);bad['fingerprint']='0'*64
        with self.assertRaises(Exception):service.join_guest(bad)
        self.assertNotIn('B',o.room.players)
        self.connect()

    def raw_tls(self):
        context=ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT);context.check_hostname=False;context.verify_mode=ssl.CERT_NONE
        raw=context.wrap_socket(socket.create_connection(('127.0.0.1',self.owner.invitation['control_port']),timeout=2),server_hostname='127.0.0.1')
        self.assertEqual(hashlib.sha256(raw.getpeercert(binary_form=True)).hexdigest(),self.owner.invitation['fingerprint'])
        return raw

    def test_fragmented_greeting_survives_short_read_timeout(self):
        o=self.start()
        with self.raw_tls() as raw:
            value=dict(method='join',credential=o.invitation['credential'],profile=o.invitation['profile'])
            packet=service.canonical(value)+b'\n';raw.sendall(packet[:10]);time.sleep(.35);raw.sendall(packet[10:])
            reply=bytearray()
            while not reply.endswith(b'\n'):reply.extend(raw.recv(4096))
            self.assertTrue(json.loads(reply)['ok']);self.assertIn('B',o.room.players)

    def test_closing_incomplete_tls_frame_interrupts_owned_reader(self):
        o=self.start()
        with self.raw_tls() as raw:
            raw.sendall(b'{"method":');time.sleep(.05)
            start=time.monotonic();result=o.close()
            self.assertTrue(result['network_closed'],result);self.assertLess(time.monotonic()-start,3)
            self.assertTrue(all(not s.connections for s,t in o.servers))

    def test_ready_cannot_precede_first_formal_load(self):
        o=self.start();c=self.connect()
        with self.assertRaisesRegex(ValueError,'formal first'):o.ready_for_turn()
        reply=self.guest.control.request(dict(action='period_ready',epoch=c.epoch,ready=True))
        self.assertTrue(reply['ok'])
        time.sleep(.15)
        self.assertEqual(c.phase,'PLANNING');self.assertFalse(o._seal_started)
        with self.assertRaises(Exception):c.seal_inputs()

    def test_authenticated_context_exact_shape_and_false_cleanup_refused(self):
        self.start();c=self.connect()
        self.assertFalse(self.guest.control.request({'action':'pilot_context','extra':True})['ok'])
        reply=self.guest.control.request(dict(action='pilot_guest_finished',formal_completions=0,
            native_cleanup_verified=True,retained_native_state=False))
        self.assertFalse(reply['ok']);self.assertIsNone(self.owner.guest_finished)
        reply=self.guest.control.request(dict(action='pilot_guest_finished',formal_completions=0,
            native_cleanup_verified=False,retained_native_state=True))
        self.assertTrue(reply['ok']);self.assertFalse(reply['native_cleanup_independently_verified'])
        self.assertTrue(self.owner.wait_guest_finished(1)['retained_native_state'])
        self.assertEqual(c.phase,'HELD');self.assertFalse(c.ready)
        self.assertFalse(self.guest.control.request(dict(action='pilot_guest_finished',formal_completions=0,
            native_cleanup_verified=False,retained_native_state=True))['ok'])

    def test_disconnect_is_held_and_cannot_rejoin(self):
        o=self.start();c=self.connect();self.guest.close()
        deadline=time.monotonic()+3
        while o.room._held is None and time.monotonic()<deadline:time.sleep(.05)
        self.assertIsNotNone(o.room._held)
        with self.assertRaises(Exception):service.join_guest(o.invitation)
        with self.assertRaises(Exception):o.ready_for_turn()

    def test_finish_barrier_does_not_invent_native_cleanup(self):
        o=self.start();self.connect()
        self.assertFalse(self.guest.control.request({'action':'pilot_host_finished'})['host_finished'])
        with self.assertRaises(ValueError):o.wait_guest_disconnected(1)
        o.mark_host_finished()
        response=self.guest.control.request({'action':'pilot_host_finished'})
        self.assertTrue(response['host_finished']);self.assertFalse(response['native_cleanup_independently_verified'])
        self.assertFalse(o.guest_disconnected.is_set())
        self.guest.close();self.assertTrue(o.wait_guest_disconnected(3)['guest_control_disconnected'])

    def test_cli_default_and_check_do_not_capture_or_join(self):
        with patch.object(host.native,'capture',side_effect=AssertionError('process forbidden')), \
             patch.object(host,'HostService',side_effect=AssertionError('network forbidden')), \
             patch.object(host,'read_config',return_value={}),patch.object(host,'check',return_value=(None,None)):
            with patch('sys.stdout',new=io.StringIO()):
                self.assertEqual(host.main([]),0)
                self.assertEqual(host.main(['--check','--config','unused.json']),0)

    def test_config_refuses_ambiguous_paths_and_mutating_mode_without_condition(self):
        m=manifest();m['profile']['game_sha256']=GAME_SHA;m['profile']['rules_sha256']=digest(rules(0,0))
        c=dict(schema='san14.a-observed-host.v1',manifest=m,rules=rules(0,0),adapter_key_path=str(OUTPUT/'key'),
            network=dict(listen_host='127.0.0.1',advertise_host='127.0.0.1',control_port=42141,download_port=42142,
                directory=str(OUTPUT/'unused-private')),
            native=dict(pid=123,wait_seconds=600,**{k:str(OUTPUT/k) for k in host.NATIVE_PATHS}))
        host.validate_config(c)
        for change in ({'directory':str(ROOT/'bad-private')},{'control_port':42142},{'advertise_host':'0.0.0.0'}):
            bad=deepcopy(c);bad['network'].update(change)
            with self.assertRaises(ValueError):host.validate_config(bad)
        with patch.object(host,'read_config',side_effect=AssertionError('must reject before read')), \
             patch('sys.stderr',new=io.StringIO()),self.assertRaises(SystemExit):
            host.main(['--execute','--config','unused.json'])


if __name__=='__main__':
    OUTPUT=PRIVATE/'observed_room_service_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');OUTPUT.mkdir(parents=True)
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    paths={Path(m.__file__).resolve() for m in list(sys.modules.values()) if getattr(m,'__file__',None)}
    paths.add(Path(__file__).resolve());sources={str(p):sha(p) for p in paths if p.is_relative_to(ROOT) and p.suffix=='.py'}
    stream=io.StringIO();r=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
    (OUTPUT/'test.log').write_text(stream.getvalue(),encoding='utf-8')
    stable=all(sha(Path(p))==h for p,h in sources.items())
    report=dict(result='PASS' if r.wasSuccessful() and r.testsRun==10 and stable else 'FAIL',tests=r.testsRun,
        sources=sources,sources_unchanged=stable,actual_TLS=True,game_access=False,native_execution=False,
        native_startup_executed=False,failures=[(str(t),v) for t,v in r.errors+r.failures])
    report['artifacts']={str(p):sha(p) for p in OUTPUT.rglob('*') if p.is_file()}
    (OUTPUT/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(stream.getvalue());print(OUTPUT/'result.json');raise SystemExit(report['result']!='PASS')
