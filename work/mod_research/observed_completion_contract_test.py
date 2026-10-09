"""No game/process/files: finite-observation wire and contract separation."""
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime
import hashlib
import io
import json
from pathlib import Path
import sys
import unittest

P=Path(__file__).resolve().parent
ROOT=P.parents[1]
sys.path[:0]=[str(ROOT/'outputs/san14-link'),str(ROOT.parent/'mod_research/python_deps')]
import observed_completion_contract as wire
from a_observed_room import ObservedRoom
from a_room_bootstrap_protocol import BootstrapCoordinator
from b_remote_session_boundary import Observation
from b_warm_profile_contract import Profile,Date,Identity
import b_warm_remote_completion as strong
from checkpoint_fresh_save_binding_test import manifest,select_direct
from authoritative_sync import CheckpointPackage,digest,scope_from_room,canonical


def fixture():
    room=ObservedRoom(manifest());select_direct(room)
    scope=scope_from_room(room)
    p=Profile();p.file.name=b'svdexccSC03.s14';p.file.slot=63;p.file.size=3
    p.file.sha256[:]=hashlib.sha256(b'own').digest()
    p.before=Date(203,8,11);p.loaded=Date(203,8,21)
    p.source=Identity(666,12,11);p.target=Identity(952,2,2);p.currentForce=12
    package=CheckpointPackage(scope,'c'*32,1,dict(sequence=0,prefix_sha256=digest(scope)),
        dict(year=203,month=8,day=21,phase='PLANNING_BOUNDARY'),'FIXTURE_ONLY','d'*64,
        {'world.s14':b'own','adapter.json':b'{}'},source_player='A')
    context=dict(scope=scope,manifest=package.manifest,checkpoint_id=package.checkpoint_id,
                 attachments=dict(A='a'*32,B='b'*32))
    return room,context,p


def observation(p,kind,side='B',sequence=1):
    observed=wire.expected_profile(p,kind,side)
    return Observation(sequence,123,2**60+17,hashlib.sha256(bytes(observed)).hexdigest(),'e'*64)


class Tests(unittest.TestCase):
    def test_roundtrip_preserves_large_birth_and_false_coverage(self):
        _,c,p=fixture()
        b=wire.boundary_envelope(observation(p,'begin'),c,p,'begin')
        value=dict(kind='begin',boundary=b)
        self.assertEqual(wire.unpack(bytes([7])*32,wire.packet(bytes([7])*32,value)),value)
        self.assertEqual(b['birth'],2**60+17)
        self.assertFalse(b['input_exclusion_proven'] or b['atomic_snapshot'])

    def test_strong_and_observed_domains_cannot_be_substituted(self):
        key=bytes([7])*32;value=dict(kind='begin')
        old=strong.packet(key,value)
        with self.assertRaises(ValueError):wire.unpack(key,old)
        old['action']=wire.ACTION
        with self.assertRaisesRegex(ValueError,'authentication'):wire.unpack(key,old)
        new=wire.packet(key,value);new['action']=strong.ACTION
        with self.assertRaises(ValueError):strong.unpack(key,new)

    def test_guest_post_load_uses_changed_observed_profile(self):
        _,c,p=fixture()
        b=wire.boundary_envelope(observation(p,'complete'),c,p,'complete')
        self.assertNotEqual(b['observed_profile_sha256'],b['profile_sha256'])
        self.assertEqual((b['node']['day'],b['force'],b['ruler']),(21,2,952))
        with self.assertRaisesRegex(ValueError,'observed profile'):
            wire.boundary_envelope(observation(p,'begin'),c,p,'complete')

    def test_authority_uses_actual_manifest_date_and_source_view(self):
        _,c,p=fixture()
        local=asdict(observation(p,'begin','A'))
        local.update(node=c['manifest']['node'],force=12,ruler=666)
        b=wire.boundary_envelope(local,c,p,'begin',side='A')
        self.assertEqual((b['node']['day'],b['force']),(21,12))
        self.assertEqual(b['observed_profile_sha256'],b['profile_sha256'])
        local['node']={**local['node'],'day':11}
        with self.assertRaisesRegex(ValueError,'node differs'):
            wire.boundary_envelope(local,c,p,'begin',side='A')
        local.pop('node')
        local.update(year=203,month=8,day=21)
        wire.boundary_envelope(local,c,p,'begin',side='A')
        local['day']=11
        with self.assertRaisesRegex(ValueError,'observed date'):
            wire.boundary_envelope(local,c,p,'begin',side='A')

    def test_sample_replay_and_process_switch_refused(self):
        _,c,p=fixture()
        a=wire.boundary_envelope(observation(p,'begin'),c,p,'begin')
        b=wire.boundary_envelope(observation(p,'complete',sequence=2),c,p,'complete')
        self.assertEqual(wire.advances(a,b),b)
        with self.assertRaises(ValueError):wire.advances(a,a)
        with self.assertRaises(ValueError):wire.advances(a,{**b,'birth':b['birth']+1})

    def test_false_fence_and_non_boolean_flags_refused(self):
        _,c,p=fixture()
        local=asdict(observation(p,'begin'))
        for bad in (True,0,None):
            with self.assertRaises(ValueError):
                wire.boundary_envelope({**local,'input_exclusion_proven':bad},c,p,'begin')
        b=wire.boundary_envelope(local,c,p,'begin')
        with self.assertRaises(ValueError):
            wire.validate_boundary({**b,'input_exclusion_proven':True},c,p,'begin')

    def test_native_incarnation_and_context_are_exact(self):
        _,c,p=fixture()
        b=wire.boundary_envelope(observation(p,'complete'),c,p,'complete')
        wire.validate_boundary(b,c,p,'complete',native=dict(pid=b['pid'],birth=b['birth']))
        with self.assertRaises(ValueError):
            wire.validate_boundary(b,c,p,'complete',native=dict(pid=b['pid']+1,birth=b['birth']))
        changed=deepcopy(c);changed['checkpoint_id']='f'*64
        with self.assertRaises(ValueError):wire.validate_boundary(b,changed,p,'complete')
        with self.assertRaises(ValueError):wire.validate_boundary({**b,'extra':True},c,p,'complete')

    def test_zero_provenance_and_oversize_payload_refused(self):
        _,c,p=fixture()
        local=asdict(observation(p,'begin'))
        for key,value in (('sequence',True),('pid',0),('birth',0),('sample_sha256','0'*64)):
            with self.assertRaises(ValueError):wire.boundary_envelope({**local,key:value},c,p,'begin')
        with self.assertRaises(ValueError):wire.packet(bytes([7])*32,{'body':'x'*(wire.MAX_RAW+1)})

    def test_observed_room_refuses_old_enrollment_and_action(self):
        room,c,p=fixture()
        with self.assertRaisesRegex(ValueError,'Strong'):room.enroll_adapter(None)
        reply=room.handle('B','b',strong.packet(bytes([7])*32,{'kind':'begin'}))
        self.assertFalse(reply['ok'])


if __name__=='__main__':
    folder=ROOT.parent/'mod_research/observed_completion_contract_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    folder.mkdir(parents=True)
    paths={Path(m.__file__).resolve() for m in list(sys.modules.values()) if getattr(m,'__file__',None)}
    paths.add(Path(__file__).resolve())
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    pins={str(p):sha(p) for p in sorted(paths) if p.is_relative_to(ROOT) and p.suffix=='.py'}
    log=io.StringIO()
    r=unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
    (folder/'test.log').write_text(log.getvalue(),encoding='utf-8')
    stable=all(sha(Path(p))==h for p,h in pins.items())
    result=dict(result='PASS' if r.wasSuccessful() and r.testsRun==9 and stable else 'FAIL',tests=r.testsRun,
        sources=pins,sources_unchanged=stable,game_access=False,native_executed=False,tls_used=False,
        failures=[(str(t),s) for t,s in r.errors+r.failures])
    (folder/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(log.getvalue());print(json.dumps({'result':result['result'],'path':str(folder/'result.json')}))
    raise SystemExit(result['result']!='PASS')
