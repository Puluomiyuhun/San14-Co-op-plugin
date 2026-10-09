"""Actual TLS authority binding plus real owned remote native rules preparation."""
from datetime import datetime
from copy import deepcopy
from pathlib import Path
import ctypes as C
import hashlib
import io
import json
import struct
import sys
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PRIVATE=ROOT.parent/'mod_research'
sys.path[:0]=[str(PRIVATE/'python_deps'),str(ROOT/'outputs/san14-link')]
import b_warm_room_test as transport
from b_warm_remote_completion import RemoteCompletionRoom
from b_warm_remote_rules import RemoteRulesWorldCapture,RemoteRulesFactory
from b_warm_world_test import Reader
from b_warm_rules_factory_test import Owned,process_birth
from b_warm_rules_factory import RulesBuild
from human_rules_activation_publish_v2_counter_profile import generate
from human_rules_activation_room import rules,GAME_SHA
from human_rules_world_lifecycle import Config,NextWorldRequest
from authoritative_sync import digest

OUTPUT=None
ROWS=[]
NATIVE_RUN=PRIVATE/'b_warm_rules_factory_runs/20261009-193128-959554'
NATIVE_SHA='fadd653391d377f5ffe64752c9660a257bf87dd9a1eae80488918604c20a21c6'


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


class Cases(unittest.TestCase):
    tearDown=transport.RoomTests.tearDown

    def setUp(self):
        original=transport.manifest
        def manifest():
            value=original();value['profile']['game_sha256']=GAME_SHA
            value['profile']['rules_sha256']=digest(rules(1,0));return value
        with patch.object(transport,'WarmRoom',RemoteCompletionRoom),patch.object(transport,'manifest',manifest):
            transport.RoomTests.setUp(self)
        self.held=True;self.birth=1001

    def guard(self):
        if not self.held:raise ValueError('Explicit fixture boundary lost')

    def fixture(self):
        r=Reader('A')
        r.memory.put(r.memory.base+0x1FD0C5C,struct.pack('<i',1))
        r.memory.put(r.memory.base+0x18EB628,struct.pack('<I',1))
        r.memory.put(r.world+0x16A8,bytes(4))
        capture=RemoteRulesWorldCapture(r,self.b,self.c.scope,rules(1,0),pid=r.pid,birth=self.birth,
            read_birth=lambda:self.birth,guard_check=self.guard)
        self.assertFalse(hasattr(capture,'room'));return r,capture

    def request(self,generation=1,day=11):
        return NextWorldRequest(generation,str(generation)*64,bytes([generation])*16,203,8,day)

    def test_tls_binding_captures_local_source_then_target_world(self):
        r,capture=self.fixture();old=capture.capture_loaded(self.request(),side='A',expected_ruler=666)
        r.root+=0x100000;r.world+=0x100000;r.force=2;r.ruler=952
        r.memory.put(r.memory.base+0x1FCA1E0,struct.pack('<Q',r.root))
        r.memory.put(r.root+0x85130,struct.pack('<Q',r.world))
        r.memory.put(r.world+0x34,struct.pack('<HBB',203,8,21)+bytes([0,0,2,1]))
        r.memory.put(r.world+0x16A8,bytes(4))
        new=capture.capture_loaded(self.request(2,21),side='B',expected_ruler=952)
        self.assertEqual(capture.export_current(new,expected_ruler=952),new.config)
        a,b=Config.from_buffer_copy(old.config),Config.from_buffer_copy(new.config)
        self.assertEqual((a.viewer,b.viewer),(12,2));self.assertNotEqual(a.world,b.world)
        self.assertEqual(bytes(a.room),bytes(b.room));self.assertEqual(bytes(a.rules_digest),bytes(b.rules_digest))
        ROWS.append(dict(case='tls-binding-own-memory',viewers=[12,2],actual_tls=True,fake_memory=True,
                         copied_room_or_coordinator=False))

    def test_foreign_scope_and_wrong_seat_rejected(self):
        r,capture=self.fixture();wrong=deepcopy(self.c.scope);wrong['room_id']='e'*32
        with self.assertRaisesRegex(ValueError,'binding unavailable'):
            RemoteRulesWorldCapture(r,self.b,wrong,rules(1,0),pid=r.pid,birth=self.birth,
                read_birth=lambda:self.birth,guard_check=self.guard)
        with self.assertRaisesRegex(ValueError,'authenticated B'):
            RemoteRulesWorldCapture(r,self.a,self.c.scope,rules(1,0),pid=r.pid,birth=self.birth,
                read_birth=lambda:self.birth,guard_check=self.guard)
        self.assertFalse(self.a.request({'action':'warm_rules_binding'})['ok'])
        self.assertFalse(self.b.request({'action':'warm_rules_binding','extra':1})['ok'])
        ROWS.append(dict(case='scope-seat-and-shape-refused',actual_tls=True,native_calls=False))

    def test_local_failure_latches_without_automatic_recovery(self):
        r,capture=self.fixture();self.held=False
        with self.assertRaisesRegex(ValueError,'boundary lost'):capture._check()
        self.held=True
        with self.assertRaisesRegex(ValueError,'capture is held'):capture._check()
        r,capture=self.fixture();self.birth+=1
        with self.assertRaisesRegex(ValueError,'incarnation changed'):capture._check()
        ROWS.append(dict(case='local-incarnation-and-boundary-held',native_calls=False))

    def test_closed_authority_rejects_existing_capture(self):
        r,capture=self.fixture();self.room.close_checkpoints()
        with self.assertRaisesRegex(ValueError,'binding unavailable'):capture._check()
        self.assertTrue(capture.failed)
        ROWS.append(dict(case='authority-closed',native_calls=False))

    def test_actual_factory_two_generations_over_authority_tls_binding(self):
        prior=json.loads((NATIVE_RUN/'result.json').read_text(encoding='utf-8'))
        self.assertEqual(sha(NATIVE_RUN/'result.json'),NATIVE_SHA)
        for field in ('sources','private','generated','binaries','artifacts'):
            for name,wanted in prior[field].items():self.assertEqual(sha(name),wanted,name)
        inputs=NATIVE_RUN/'inputs';own=Owned(self.folder,inputs,'owned-native');factory=None
        try:
            birth=process_birth(own.reader)
            capture=RemoteRulesWorldCapture(own.reader,self.b,self.c.scope,rules(1,0),pid=own.child.pid,birth=birth,
                read_birth=lambda:process_birth(own.reader),guard_check=lambda:None)
            # Recompute exact anchors from the prior pinned native build.
            profile=generate(inputs/'first.dll',self.folder/'fixture-counters.h')
            build=RulesBuild(inputs/'first.dll',inputs/'factory-publisher.exe',sha(inputs/'first.dll'),sha(inputs/'factory-publisher.exe'),
                sha(inputs/'factory-host.exe'),tuple((x['instruction_rva'],bytes.fromhex(x['bytes']),x['value_rva'])
                for x in profile['active_counters']),'OWNED_FIXTURE')
            factory=RemoteRulesFactory(capture,own.api,build,own.folder,rulers={12:12,2:2})
            generations=[]
            for generation in (1,2):
                if generation==2:own.command('n','LOADED')
                world=capture.capture_loaded(self.request(generation,11 if generation==1 else 21),
                    side='A' if generation==1 else 'B',expected_ruler=12 if generation==1 else 2)
                port=factory.prepare_rules(world);own.command('b '+str(port.module.module),'BOUND')
                installed=port.install();executed=own.command('e','EXERCISED');restored=port.restore();port.retired=True
                generations.append(dict(viewer=Config.from_buffer_copy(world.config).viewer,installed=installed,
                    executed=executed,restored=restored))
            self.assertEqual(len(factory.retained),2)
            final=own.finish();self.assertEqual(final['resident_modules'],2)
            ROWS.append(dict(case='actual-native-factory-with-network-binding',generations=generations,
                actual_tls=True,actual_remote_prepare_seal=True,actual_native_publisher=True,
                actual_rpm=True,game_world_and_business_are_fixture=True,native_game_load=False,
                fence_is_owned_host_wait=True,owned_host_normal_exit=True))
        except BaseException:
            if not own.closed and not (factory and factory.uncertain):
                try:own.finish()
                except BaseException:pass
            raise


def pins():
    paths={Path(m.__file__).resolve() for m in list(sys.modules.values()) if getattr(m,'__file__',None)}
    paths.add(Path(__file__).resolve())
    return {str(p):sha(p) for p in sorted(paths) if p.is_relative_to(ROOT) and p.suffix=='.py'}


if __name__=='__main__':
    OUTPUT=PRIVATE/'b_warm_remote_rules_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');OUTPUT.mkdir(parents=True)
    transport.OUTPUT=OUTPUT;before=pins();stream=io.StringIO()
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Cases))
    (OUTPUT/'test.log').write_text(stream.getvalue(),encoding='utf-8')
    sources=pins();stable=all(sources.get(k)==v for k,v in before.items())
    prior=json.loads((NATIVE_RUN/'result.json').read_text(encoding='utf-8'))
    private={str(NATIVE_RUN/'result.json'):NATIVE_SHA}
    for field in ('private','generated','binaries','artifacts'):private.update(prior[field])
    stable=stable and all(sha(p)==h for p,h in {**private,**prior['sources']}.items())
    report=dict(result='PASS' if result.wasSuccessful() and result.testsRun==5 and stable else 'FAIL',
        family='san14.b-warm-remote-rules.v1',tests=result.testsRun,sources=sources,inputs_unchanged=stable,
        private=private,build_sources=prior['sources'],cases=ROWS,game_access=False,actual_tls=True,
        artifacts={str(p):sha(p) for p in OUTPUT.rglob('*') if p.is_file()},
        failures=[(str(t),detail) for t,detail in result.failures+result.errors])
    (OUTPUT/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(OUTPUT/'result.json');print(stream.getvalue())
    raise SystemExit(0 if report['result']=='PASS' else 1)
