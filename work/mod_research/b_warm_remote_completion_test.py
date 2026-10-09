"""A coordinator and a separate B Python process over actual pinned TLS.

Files/SQLite/transport/coordinator are real; Save/native load, RAM and held
boundary are explicit doubles. Child never constructs PeriodCoordinator.
"""
from datetime import datetime
import base64
import hashlib
import io
import json
import os
from pathlib import Path
import secrets
import struct
import subprocess
import sys
import threading
import unittest
import zlib
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRIVATE = ROOT.parent/'mod_research'
sys.path[:0] = [str(PRIVATE/'python_deps'), str(ROOT/'outputs/san14-link')]
import b_warm_room_test as transport
import b_warm_world as world
from b_warm_world_test import Reader
from b_warm_profile_contract import Profile, Date, Identity
from b_warm_remote_completion import RemoteCompletionRoom, RemoteGuestCompletion, ACTION, packet, unpack
from b_warm_projection import host_observation
from b_warm_bootstrap_protocol import receive_bootstrap_staged
from b_warm_room import receive_staged
from authoritative_sync import PeriodCoordinator, scope_from_room, next_node, digest
from checkpoint_fresh_save_binding_test import run_model, model_artifact
from checkpoint_room_client import RoomConnection
from room_transport import Client

OUTPUT = None
EVIDENCE = []


def sha(raw): return hashlib.sha256(raw).hexdigest()


def put_date(reader, node):
    reader.memory.put(reader.world+0x34, struct.pack('<HBB', node['year'], node['month'], node['day'])+
                      bytes([0, 0, reader.force, 1]))


def incompressible_tables(reader):
    # Deterministic SHAKE stream, same ordered opaque fields at different A/B
    # addresses; preserves every vtable and all non-projection memory.
    for name, _, count, _, _, layout in world.TABLES:
        stream = hashlib.shake_256(('remote wire regression '+name).encode()).digest(sum(n for _,n in layout)*count)
        pos = 0
        for address in reader.objects[name]:
            raw = bytearray(reader.memory.spans[address])
            for offset, size in layout:
                raw[offset:offset+size] = stream[pos:pos+size]; pos += size
            reader.memory.put(address, raw)


def child():
    control = guest = None; loads = 0
    try:
        for line in sys.stdin:
            q = json.loads(line)
            try:
                if q['op'] == 'init':
                    control = RoomConnection(q['host'], q['port'], q['fingerprint'], q['greeting'])
                    key = bytes.fromhex(q['key'])
                    guest = RemoteGuestCompletion(control, key, verify_held=lambda: True)
                    out = dict(player_id=control.player_id, child_pid=os.getpid())
                elif q['op'] == 'request': out = control.request(q['packet'])
                elif q['op'] == 'close':
                    control.close(); print(json.dumps(dict(ok=True)), flush=True); return
                elif q['op'] == 'run':
                    p = Profile.from_buffer_copy(base64.b64decode(q['profile']))
                    ctx = q['context']; m = ctx['manifest']; mode = q.get('mode', 'normal')
                    def connect(token):
                        return Client('127.0.0.1', q['download'], q['fingerprint'],
                            dict(method='checkpoint_download', credential=token, profile=ctx['scope']['profile']))
                    receive = receive_bootstrap_staged if q['bootstrap'] else receive_staged
                    received = receive(control, connect, checkpoint_id=ctx['checkpoint_id'], scope=ctx['scope'],
                        epoch=m['epoch'], period=m['period'], cut=m['cut'], attachments=ctx['attachments'], directory=q['directory'])
                    reader = Reader('B', 0x1000000000); reader.pid = os.getpid(); put_date(reader, m['node'])
                    if mode == 'incompressible': incompressible_tables(reader)
                    birth = 2**60+7
                    def native(permit):
                        nonlocal loads
                        loads += 1
                        assert received.journal.status()['status'] == 'INTENT'
                        if mode == 'native-fail': raise RuntimeError('Explicit native load double fails')
                        a = dict(result='PASS_WARM_LOAD_RETIRED', receipt_key=sha(('native double '+str(loads)).encode()),
                            source_force=12, source_ruler=666, target_force=2, target_ruler=952,
                            ready_authorized=False, full_world_verified=False, input_exclusion_proven=False)
                        c = dict(accepted=a, profile_sha256=sha(bytes(p)), attempt=2**63+loads, pid=os.getpid(), birth=birth,
                            slots_restored=True, snapshot=dict(date={k:m['node'][k] for k in ('year','month','day')},
                            player=dict(force_id=2, ruler_id=952)))
                        s = world.sample(reader, scope=ctx['scope'], epoch=m['epoch'], period=m['period'], profile=p,
                            side='B', receipt_key=a['receipt_key'], read_birth=lambda: birth)
                        return dict(completion=c, sample=s)
                    original = control.request
                    def request(value):
                        if value.get('action') == ACTION:
                            b = unpack(key, value)
                            if mode == 'bad-key': value = packet(b'\x55'*32, b)
                            if b['kind'] == 'complete' and mode == 'drift':
                                b['completion']['snapshot']['player']['force_id'] = 12
                                value = packet(key, b)
                            result = original(value)
                            if b['kind'] == 'complete' and mode == 'lost-reply': raise EOFError('Delivered completion reply lost locally')
                            return result
                        return original(value)
                    control.request = request
                    try:
                        result = guest.apply(received, p, guest_before=lambda: dict(attachment=ctx['attachments']['B'],
                            viewer_force=12 if q['bootstrap'] else 2, safe_boundary=True), apply_received=native)
                        out = dict(ok=True, result=result, loads=loads, journal=received.journal.status(), child_pid=os.getpid())
                    except BaseException as exc:
                        retry = False
                        try:
                            RemoteGuestCompletion(control, key, verify_held=lambda: True).apply(received, p,
                                guest_before=lambda: None, apply_received=native)
                            retry = True
                        except Exception: pass
                        out = dict(ok=False, error=str(exc), loads=loads, journal=received.journal.status(),
                                   retry_succeeded=retry, child_pid=os.getpid())
                    finally: control.request = original
                else: raise ValueError('Bad owned child command')
            except BaseException as exc: out = dict(ok=False, error=type(exc).__name__+': '+str(exc))
            print(json.dumps(out), flush=True)
    finally:
        if control: control.close()


class ChildControl:
    def __init__(self, host, port, fingerprint, greeting, key, folder):
        self.log = (folder/'child-stderr.log').open('w', encoding='utf-8')
        self.proc = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), '--child'], stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=self.log, text=True, encoding='utf-8', creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        self.closed = False
        response = self.send(dict(op='init', host=host, port=port, fingerprint=fingerprint, greeting=greeting, key=key.hex()))
        self.player_id = response['player_id']; self.pid = response['child_pid']
    def send(self, q):
        self.proc.stdin.write(json.dumps(q)+'\n'); self.proc.stdin.flush()
        line = self.proc.stdout.readline()
        if not line: raise RuntimeError('Owned B child exited: '+str(self.proc.poll()))
        return json.loads(line)
    def request(self, packet): return self.send(dict(op='request', packet=packet))
    def close(self):
        if not self.closed:
            try: self.send(dict(op='close'))
            finally:
                self.proc.wait(timeout=15); self.proc.stdin.close(); self.proc.stdout.close(); self.log.close(); self.closed=True


class Cases(unittest.TestCase):
    tearDown = transport.RoomTests.tearDown
    def setUp(self):
        self.key = secrets.token_bytes(32); self.host_reader = Reader('A'); self.host_key = '1'*64
        oldmanifest = transport.manifest
        def manifest():
            v = oldmanifest(); v['profile']['game_sha256'] = world.objects.GAME_SHA256; return v
        def coordinator(room):
            c = PeriodCoordinator(scope_from_room(room), world.CONTRACT, 'd'*64,
                {'A':'a'*32,'B':'b'*32}, dict(year=203,month=8,day=1,phase='PLANNING_BOUNDARY'))
            room.bind_coordinator(c)
            for s in ('A','B'): c.applied_prefix(s,c.epoch,9,'e'*64,'d'*64,c.attachments[s])
            return c
        def control(host, port, fingerprint, greeting):
            if greeting['method'] == 'join': return ChildControl(host,port,fingerprint,greeting,self.key,self.folder)
            return RoomConnection(host,port,fingerprint,greeting)
        with patch.object(transport,'manifest',manifest), patch.object(transport,'make_coordinator',coordinator), \
             patch.object(transport,'WarmRoom',RemoteCompletionRoom), patch.object(transport,'RoomConnection',control):
            transport.RoomTests.setUp(self)
        self.room.enroll_adapter(self.key, host_sampler=lambda p,k: world.sample(self.host_reader,scope=self.c.scope,
            epoch=self.c.epoch,period=self.c.period,profile=p,side='A',receipt_key=k,read_birth=lambda:1001),
            verify_held=lambda:True,host_receipt_key=lambda:self.host_key,source_kind='FIXTURE_ONLY')
        self.assertNotEqual(self.b.pid, os.getpid())
        self.assertTrue(self.b.request(dict(action='warm_rules_binding'))['ok'])
        self.assertFalse(self.a.request(dict(action='warm_rules_binding'))['ok'])

    def one(self, generation, mode='normal'):
        node = next_node(self.c.node); put_date(self.host_reader,node)
        if mode == 'incompressible': incompressible_tables(self.host_reader)
        data = ('explicit Save double '+str(generation)).encode()*3000
        p=Profile(); p.file.name=b'svdexccSC03.s14';p.file.slot=63;p.file.size=len(data);p.file.sha256[:]=bytes.fromhex(sha(data))
        p.before=Date(*(self.c.node[k] for k in ('year','month','day')));p.loaded=Date(*(node[k] for k in ('year','month','day')))
        p.source=Identity(666,12,11);p.target=Identity(952,2,2);p.currentForce=12 if generation==1 else 2
        self.host_key=sha(('A actual receipt model '+str(generation)).encode())
        run_model(self.c)
        observe=lambda:host_observation(self.c,reader=self.host_reader,read_birth=lambda:1001,verify_held=lambda:True,source_ruler=666)
        reserved=self.binding.reserve(generation,f'mp{generation:08d}.s14',observe())
        self.artifacts[generation]=model_artifact(reserved.request,generation,data=data)
        package=self.binding.publish(generation,observe)
        context=dict(scope=self.c.scope,manifest=package.manifest,checkpoint_id=package.checkpoint_id,attachments=self.c.attachments.copy())
        result=self.b.send(dict(op='run',profile=base64.b64encode(bytes(p)).decode(),context=context,bootstrap=generation==1,
            download=self.download,fingerprint=self.fp,directory=str(self.folder/f'received-{generation}'),mode=mode))
        return result, package

    def test_bootstrap_and_second_period_in_independent_guest(self):
        rows=[]
        for n in (1,2):
            r,p=self.one(n); self.assertTrue(r['ok'],r);self.assertEqual(r['loads'],n)
            self.assertEqual((self.c.period,self.c.phase),(n+1,'PLANNING'))
            self.assertEqual(r['journal']['status'],'COMPLETED');self.assertFalse(self.c.ready)
            saved=json.loads((self.folder/f'received-{n}'/'remote-adapter-completion.json').read_text())
            self.assertNotIn('local_context',saved['sample'])
            duplicate=self.b.request(packet(self.key,saved));self.assertTrue(duplicate['duplicate'])
            self.assertEqual(self.c.period,n+1);rows.append(r)
        self.assertEqual(len(self.c.applied_receipts),2)
        EVIDENCE.append(dict(case='two-periods-separate-B',a_pid=os.getpid(),b_pid=self.b.pid,rows=rows))

    def test_bad_adapter_key_cannot_reserve_or_load(self):
        r,_=self.one(1,'bad-key');self.assertFalse(r['ok']);self.assertEqual(r['loads'],0)
        self.assertIsNone(self.c.load_intent);self.assertEqual(self.c.period,1);self.assertFalse(r['retry_succeeded'])
        EVIDENCE.append(dict(case='bad-key',guest=r))

    def test_conflicting_native_completion_holds_without_loaded(self):
        r,_=self.one(1,'drift');self.assertFalse(r['ok']);self.assertEqual(r['loads'],1)
        self.assertEqual((self.c.period,self.c.phase),(1,'HELD'));self.assertFalse(r['retry_succeeded'])
        self.assertFalse(self.c.applied_receipts);EVIDENCE.append(dict(case='wrong-viewer',guest=r))

    def test_lost_completion_reply_never_reloads(self):
        r,_=self.one(1,'lost-reply');self.assertFalse(r['ok']);self.assertEqual(r['loads'],1)
        self.assertEqual(self.c.period,2);self.assertEqual(len(self.c.applied_receipts),1)
        self.assertFalse(r['retry_succeeded']);self.assertEqual(r['journal']['status'],'COMPLETED')
        EVIDENCE.append(dict(case='lost-reply',guest=r))

    def test_low_compressibility_full_tables_use_bounded_witness(self):
        r,_=self.one(1,'incompressible');self.assertTrue(r['ok'],r)
        self.assertEqual((self.c.period,self.c.phase),(2,'PLANNING'));self.assertEqual(r['loads'],1)
        saved=json.loads((self.folder/'received-1'/'remote-adapter-completion.json').read_text())
        self.assertNotIn('shared',saved['sample']);self.assertNotIn('object_payload',saved['sample'])
        encoded=packet(self.key,saved)
        encoded_size=len(json.dumps(encoded).encode())
        self.assertLess(encoded_size,8192)
        # Preserve a direct reproduction of the old wire-capacity blocker.
        p=Profile.from_buffer_copy(base64.b64decode(json.loads((self.folder/'received-1'/'remote-adapter-begin.json').read_text())['profile']))
        ctx=self.room._remote['rows'][saved['checkpoint_id']]['context'];m=ctx['manifest']
        full=world.sample(self.host_reader,scope=ctx['scope'],epoch=m['epoch'],period=m['period'],profile=p,
            side='A',receipt_key=self.host_key,read_birth=lambda:1001)
        old_body={**saved,'sample':full};old_packed=zlib.compress(__import__('authoritative_sync').canonical(old_body))
        old_wire=len(base64.b64encode(old_packed))+150
        self.assertGreater(old_wire,65536)
        EVIDENCE.append(dict(case='incompressible-full-tables',guest=r,compact_wire_bytes=encoded_size,
            previous_full_wire_bytes=old_wire,objects_bytes=world.objects.TABLE_PAYLOAD_SIZE,
            forces_bytes=world.forces.TABLE_PAYLOAD_SIZE,partial_digest=full['partial_sha256']))


def pins():
    paths={Path(m.__file__).resolve() for m in list(sys.modules.values()) if getattr(m,'__file__',None)}
    paths.add(Path(__file__).resolve())
    return {str(p):sha(p.read_bytes()) for p in sorted(paths) if p.is_relative_to(ROOT) and p.suffix=='.py'}


if __name__=='__main__':
    if '--child' in sys.argv: child();raise SystemExit(0)
    OUTPUT=PRIVATE/'b_warm_remote_completion_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');OUTPUT.mkdir(parents=True)
    transport.OUTPUT=OUTPUT;before=pins();stream=io.StringIO()
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Cases))
    (OUTPUT/'test.log').write_text(stream.getvalue(),encoding='utf-8');sources=pins()
    stable=all(sources.get(k)==v for k,v in before.items())
    report=dict(result='PASS' if result.wasSuccessful() and result.testsRun==5 and stable else 'FAIL',tests=result.testsRun,
        sources=sources,inputs_unchanged=stable,cases=EVIDENCE,actual_tls=True,independent_guest_process=True,
        game_access=False,native_save_load=False,fake_reader=True,fake_boundary=True,
        failures=[(str(t),detail) for t,detail in result.failures+result.errors])
    report['artifacts']={str(p):sha(p.read_bytes()) for p in OUTPUT.rglob('*') if p.is_file()}
    (OUTPUT/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(OUTPUT/'result.json');print(stream.getvalue());raise SystemExit(0 if report['result']=='PASS' else 1)
