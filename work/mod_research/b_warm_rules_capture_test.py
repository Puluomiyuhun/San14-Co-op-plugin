"""Actual rules Config capture against fake memory and authenticated local Rooms.
No process access, native Prepare/Seal, DLL publication or game IO.
"""
from datetime import datetime
import hashlib
import io
import json
from pathlib import Path
import struct
import sys
import unittest

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PRIVATE=ROOT.parent/'mod_research'
sys.path.insert(0,str(ROOT/'outputs/san14-link'))
from b_warm_rules_capture import RulesWorldCapture
from b_warm_world_test import Reader
from b_warm_room import WarmRoom
from checkpoint_fresh_save_binding_test import manifest,select_direct
from human_rules_activation_room import Config,rules,GAME_SHA
from human_rules_world_lifecycle import NextWorldRequest
from room_session import digest

OUTPUT=None


def sha(raw):return hashlib.sha256(raw).hexdigest()


class Fixture:
    def __init__(self):
        self.reader=Reader('A');self.settings=rules(1,0);self.birth=1001;self.held=True
        catalog=manifest();catalog['profile']['game_sha256']=GAME_SHA
        catalog['profile']['rules_sha256']=digest(self.settings)
        self.room=WarmRoom(catalog);select_direct(self.room)
        r=self.reader;r.memory.put(r.memory.base+0x1FD0C5C,struct.pack('<i',1))
        r.memory.put(r.memory.base+0x18EB628,struct.pack('<I',1));r.memory.put(r.world+0x16A8,bytes(4))
        self.capture=RulesWorldCapture(r,self.room,self.settings,pid=r.pid,birth=self.birth,
            read_birth=lambda:self.birth,guard_check=self.guard)

    def guard(self):
        if not self.held:raise ValueError('Actual fixture boundary not held')

    def request(self,generation=1,day=11):
        return NextWorldRequest(generation,str(generation)*64,bytes([generation])*16,203,8,day)

    def replace_memory_with_B(self,day=21):
        r=self.reader;r.root+=0x100000;r.world+=0x100000;r.force=2;r.ruler=952
        r.memory.put(r.memory.base+0x1FCA1E0,struct.pack('<Q',r.root))
        r.memory.put(r.root+0x85130,struct.pack('<Q',r.world))
        r.memory.put(r.world+0x34,struct.pack('<HBB',203,8,day)+bytes([0,0,2,1]))
        r.memory.put(r.world+0x16A8,bytes(4))


class Cases(unittest.TestCase):
    def test_actual_warm_room_old_A_new_B_and_new_world_pointers(self):
        f=Fixture();initial_epoch=f.room.binding_epoch
        old=f.capture.capture_loaded(f.request(),side='A',expected_ruler=666)
        before=Config.from_buffer_copy(old.config)
        self.assertEqual(before.viewer,12);self.assertEqual(f.capture.export_current(old,expected_ruler=666),old.config)
        f.replace_memory_with_B()
        new=f.capture.capture_loaded(f.request(2,21),side='B',expected_ruler=952)
        after=Config.from_buffer_copy(new.config)
        self.assertEqual(after.viewer,2);self.assertNotEqual(after.world,before.world);self.assertNotEqual(after.root,before.root)
        self.assertEqual(after.image,before.image);self.assertEqual(bytes(after.epoch),bytes([2])*16)
        self.assertEqual(f.room.binding_epoch,initial_epoch)
        self.assertNotEqual(bytes(after.epoch).hex(),initial_epoch)
        self.assertEqual(bytes(after.room),bytes(before.room));self.assertEqual(bytes(after.rules_digest),bytes(before.rules_digest))
        self.assertEqual(list(after.force),[12,2]);self.assertEqual(list(after.main_district),[11,2])
        self.assertEqual(f.capture.export_current(new,expected_ruler=952),new.config)
        (OUTPUT/'capture.json').write_text(json.dumps(dict(old_world=before.world,new_world=after.world,
            old_viewer=before.viewer,new_viewer=after.viewer,native_epoch=bytes(after.epoch).hex(),
            room_binding_epoch=initial_epoch,config_hex=new.config.hex(),permission=False),indent=2)+'\n')

    def test_actual_settings_and_singleton_refusal(self):
        f=Fixture();r=f.reader;r.memory.put(r.memory.base+0x18EB628,struct.pack('<I',2))
        with self.assertRaisesRegex(ValueError,'settings differ'):f.capture.capture_loaded(f.request(),side='A',expected_ruler=666)
        f=Fixture();r=f.reader;r.memory.put(r.memory.base+0x1FD0C5C,struct.pack('<i',-1))
        with self.assertRaisesRegex(ValueError,'not initialized'):f.capture.capture_loaded(f.request(),side='A',expected_ruler=666)

    def test_wrong_viewer_date_and_native_drift_refuse(self):
        f=Fixture()
        with self.assertRaisesRegex(ValueError,'Date/viewer'):f.capture.capture_loaded(f.request(),side='B',expected_ruler=952)
        with self.assertRaisesRegex(ValueError,'loaded date'):f.capture.capture_loaded(f.request(2,21),side='A',expected_ruler=666)
        f.reader.memory.mutate=(f.reader.world+0x16A8,4,1)
        with self.assertRaises(ValueError):f.capture.capture_loaded(f.request(),side='A',expected_ruler=666)

    def test_room_connection_incarnation_and_fence_refuse(self):
        f=Fixture();f.birth+=1
        with self.assertRaisesRegex(ValueError,'incarnation'):f.capture.capture_loaded(f.request(),side='A',expected_ruler=666)
        f=Fixture();f.reader.pid+=1
        with self.assertRaisesRegex(ValueError,'incarnation'):f.capture.capture_loaded(f.request(),side='A',expected_ruler=666)
        f=Fixture();f.room.players['B']['connection']='new-peer'
        with self.assertRaisesRegex(ValueError,'scope/connection'):f.capture.capture_loaded(f.request(),side='A',expected_ruler=666)
        f=Fixture();f.held=False
        with self.assertRaisesRegex(ValueError,'not held'):f.capture.capture_loaded(f.request(),side='A',expected_ruler=666)

    def test_settings_room_identity_preserved_and_date_advance_only_observed(self):
        f=Fixture();old=f.capture.capture_loaded(f.request(),side='A',expected_ruler=666)
        f.reader.memory.put(f.reader.world+0x34,struct.pack('<HBB',203,8,21)+bytes([0,0,12,1]))
        current=Config.from_buffer_copy(f.capture.export_current(old,expected_ruler=666))
        self.assertEqual(current.day,21);self.assertEqual(Config.from_buffer_copy(old.config).day,11)
        f.room.manifest['profile']['rules_sha256']='f'*64
        with self.assertRaisesRegex(ValueError,'scope/connection'):f.capture.export_current(old,expected_ruler=666)


def pins():
    paths={Path(m.__file__).resolve() for m in list(sys.modules.values()) if getattr(m,'__file__',None)}
    paths.add(Path(__file__).resolve())
    return {str(p):sha(p.read_bytes()) for p in sorted(paths) if p.is_relative_to(ROOT) and p.suffix=='.py'}


if __name__=='__main__':
    OUTPUT=PRIVATE/'b_warm_rules_capture_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');OUTPUT.mkdir(parents=True)
    before=pins();stream=io.StringIO()
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Cases))
    (OUTPUT/'test.log').write_text(stream.getvalue(),encoding='utf-8')
    sources=pins();stable=before==sources
    report=dict(family='san14.b-warm-rules-capture.v1',result='PASS' if result.wasSuccessful() and result.testsRun==5 and stable else 'FAIL',
        tests=result.testsRun,sources=sources,inputs_unchanged=stable,game_access=False,process_access=False,
        native_calls=False,config_capture_only=True,actual_room=True,synthetic_memory=True,
        actual_native_prepare=False,actual_native_publication=False,ready_authorized=False,
        failures=[(str(t),detail) for t,detail in result.failures+result.errors])
    report['artifacts']={str(p):sha(p.read_bytes()) for p in OUTPUT.rglob('*') if p.is_file()}
    (OUTPUT/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(OUTPUT/'result.json');print(stream.getvalue())
    raise SystemExit(0 if report['result']=='PASS' else 1)
