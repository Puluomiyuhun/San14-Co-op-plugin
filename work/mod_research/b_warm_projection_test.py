"""Real journal/coordinator two-period projection; native samples/load are doubles.
No complete_model, process access, game saves, TLS, native calls or Ready grant.
"""
from copy import deepcopy
from datetime import datetime
import hashlib
import io
import json
from pathlib import Path
import sys
import unittest

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PRIVATE=ROOT.parent/'mod_research'
sys.path.insert(0,str(ROOT/'outputs/san14-link'))
import b_warm_projection as projection
import b_warm_world as world
from b_warm_world_test import Reader, configuration
from b_warm_profile_contract import Date, Profile
from checkpoint_fresh_save_binding_test import manifest,select_direct,run_model,model_artifact,NATIVE_ID,NATIVE_EPOCH
from checkpoint_fresh_save_binding import FreshSaveBinding,LocalWorldObservation
from checkpoint_room_lifecycle import CheckpointRoom
from checkpoint_journal import CheckpointJournal
from authoritative_sync import PeriodCoordinator,scope_from_room,digest,next_node,sha

OUTPUT=None


class Fixture:
    def __init__(self,folder):
        self.folder=folder;folder.mkdir()
        catalog=manifest();catalog['profile']['game_sha256']=world.objects.GAME_SHA256
        self.room=CheckpointRoom(catalog);select_direct(self.room)
        self.c=PeriodCoordinator(scope_from_room(self.room),world.CONTRACT,'d'*64,
            {'A':'a'*32,'B':'b'*32},dict(year=203,month=8,day=1,phase='PLANNING_BOUNDARY'))
        self.room.bind_coordinator(self.c)
        self.artifacts={};self.held=True;self.native_calls=0;self.bad=None
        self.binding=FreshSaveBinding(self.room,self.c,native_room_id=NATIVE_ID,native_room_epoch=NATIVE_EPOCH,
            artifact_reader=lambda generation:self.artifacts[generation],source_kind='FIXTURE_ONLY')
        self.adapter=projection.TrustedProjection(self.c,host_sampler=lambda p,k:self.sample('A',p,k),
            guest_sampler=lambda p,k:self.sample('B',p,k),verify_held=lambda:self.held,
            guest_before=lambda:dict(attachment=self.c.attachments['B'],viewer_force=2,safe_boundary=True),
            native_load=self.native,source_kind='FIXTURE_ONLY')

    def sample(self,side,p,key):
        shared=deepcopy(self.shared)
        if self.bad=='projection' and side=='B':
            shared['object_payload']='01'+shared['object_payload'][2:]
        value=dict(schema='san14.warm-partial-world.v1',shared=shared,partial_sha256=digest(shared),
            binding=dict(scope_sha256=digest(self.c.scope),epoch=self.c.epoch,period=self.c.period,
                profile_sha256=sha(bytes(p)),side=side,receipt_key=key,pid=101 if side=='A' else 202,
                birth=1100 if side=='A' else 1201,viewer_force=12 if side=='A' else 2,viewer_ruler=666 if side=='A' else 952),
            physical_slots=dict(objects=world.objects.SLOT_COUNT,forces=world.forces.SLOT_COUNT),
            repeated_reads_equal=True,complete_selected_tables=True,atomic_world_snapshot=False,
            full_world_verified=False,loaded_authorized=False,ready_authorized=False)
        if self.bad=='scope':value['binding']['scope_sha256']='f'*64
        return value

    def native(self,permit):
        self.native_calls+=1
        assert self.journal.status()['status']=='INTENT'
        assert permit==dict(checkpoint_id=self.journal.identity['checkpoint_id'],intent=self.c.load_intent,native_load_permitted_once=True)
        accepted=dict(result='PASS_WARM_LOAD_RETIRED',receipt_key=sha(('fixture native '+str(self.c.period)).encode()),
            ready_authorized=False,full_world_verified=False,input_exclusion_proven=False,
            source_force=12,source_ruler=666,target_force=2,target_ruler=952)
        return dict(accepted=accepted,profile_sha256='f'*64 if self.bad=='native' else sha(bytes(self.profile)),
            slots_restored=True,pid=202,birth=1201,attempt=self.c.period,
            snapshot=dict(date={k:self.shared['date'][k] for k in ('year','month','day')},player=dict(force_id=2,ruler_id=952)))

    def prepare(self):
        run_model(self.c) # Explicit protocol-only model of both players' Ready + simulation.
        n=next_node(self.c.node);ordinal=self.c.period
        payload=dict(objects=bytes(world.objects.TABLE_PAYLOAD_SIZE),forces=bytes(world.forces.TABLE_PAYLOAD_SIZE))
        self.shared=world.shared(n,payload)
        observed=LocalWorldObservation(self.c.attachments['A'],n['year'],n['month'],n['day'],12,666,world.CONTRACT,digest(self.shared),True)
        reserved=self.binding.reserve(ordinal,f'mp{ordinal:08x}.s14',observed)
        data=('EXPLICIT SAVE DOUBLE '+str(ordinal)).encode()*37
        self.artifacts[ordinal]=model_artifact(reserved.request,ordinal,data=data)
        self.package=self.binding.publish(ordinal,lambda:observed)
        self.profile,_=configuration();p=self.profile
        p.file.size=len(data);p.file.sha256[:]=bytes.fromhex(sha(data))
        p.before=Date(self.c.node['year'],self.c.node['month'],self.c.node['day'])
        p.loaded=Date(n['year'],n['month'],n['day']);p.currentForce=2
        self.journal=CheckpointJournal(self.folder/f'period{ordinal}.sqlite',self.c.scope,self.package.manifest,
            self.package.checkpoint_id,self.c.epoch,self.c.period,self.package.manifest['cut'],self.c.attachments,create=True)
        self.journal.stage_parts(self.package._parts)
        self.receiver=projection.receiver_from_journal(self.journal)
        return self

    def apply(self):
        return self.adapter.apply(self.journal,self.receiver,self.profile,host_receipt_key='4'*64)


class Cases(unittest.TestCase):
    def fixture(self):return Fixture(OUTPUT/self._testMethodName)

    def test_actual_two_period_journals_loaded_and_next_publication(self):
        f=self.fixture();rows=[];attachments=[]
        for period in (1,2):
            f.prepare();old=f.c.epoch;attachments.append(f.c.attachments['B'])
            result=f.apply();rows.append(result)
            self.assertEqual(f.journal.status()['status'],'COMPLETED')
            self.assertEqual(f.c.period,period+1);self.assertNotEqual(f.c.epoch,old)
            self.assertEqual(f.c.phase,'PLANNING');self.assertEqual(len(f.c.applied_receipts),period)
            self.assertFalse(any(result[k] for k in ('native_gameplay_enabled','full_world_verified',
                'native_full_world_coverage_verified','ready_authorized','fence_released')))
            self.assertFalse(bool(f.c.ready))
            self.assertTrue(f.held)
        self.assertEqual(f.native_calls,2);self.assertNotEqual(*attachments)
        (OUTPUT/'two-period.json').write_text(json.dumps(rows,indent=2)+'\n')

    def test_exact_contract_only(self):
        f=self.fixture();f.c.state_contract='san14.full-world.v1'
        with self.assertRaisesRegex(ValueError,'exact partial'):
            projection.TrustedProjection(f.c,host_sampler=f.sample,guest_sampler=f.sample,verify_held=lambda:True,
                guest_before=lambda:None,native_load=f.native,source_kind='FIXTURE_ONLY')
        self.assertEqual(f.native_calls,0)

    def test_mismatch_preserves_intent_and_no_replay(self):
        f=self.fixture().prepare();f.bad='projection'
        with self.assertRaisesRegex(ValueError,'Loaded declared projection differs'):f.apply()
        self.assertEqual(f.journal.status()['status'],'INTENT');self.assertEqual(f.c.period,1)
        with self.assertRaisesRegex(ValueError,'terminally held'):f.apply()
        self.assertEqual(f.native_calls,1);self.assertFalse(f.c.applied_receipts)

    def test_foreign_native_profile_leaves_intent(self):
        f=self.fixture().prepare();f.bad='native'
        with self.assertRaisesRegex(ValueError,'Native load/profile retirement differs'):f.apply()
        self.assertEqual(f.native_calls,1);self.assertEqual(f.journal.status()['status'],'INTENT')
        self.assertFalse(f.c.applied_receipts)

    def test_wrong_scope_and_lost_boundary_refuse_before_native(self):
        f=self.fixture().prepare();f.bad='scope'
        with self.assertRaisesRegex(ValueError,'another context'):f.apply()
        self.assertEqual(f.native_calls,0);self.assertEqual(f.journal.status()['status'],'STAGED')
        other=Fixture(OUTPUT/(self._testMethodName+'-held')).prepare();other.held=False
        with self.assertRaisesRegex(ValueError,'not held'):other.apply()
        self.assertEqual(other.native_calls,0);self.assertEqual(other.journal.status()['status'],'STAGED')

    def test_before_save_observation_does_not_need_future_file_profile(self):
        f=self.fixture();run_model(f.c)
        reader=Reader('A')
        value=projection.host_observation(f.c,reader=reader,read_birth=lambda:1100,verify_held=lambda:True,source_ruler=666)
        self.assertIsInstance(value,LocalWorldObservation)
        self.assertEqual(value.state_contract,world.CONTRACT)
        self.assertEqual(value.day,11);self.assertFalse(f.artifacts)
        p,_=configuration()
        sampled=world.sample(reader,scope=f.c.scope,epoch=f.c.epoch,period=f.c.period,
            profile=p,side='A',receipt_key='4'*64,read_birth=lambda:1100)
        self.assertEqual(value.world_sha256,sampled['partial_sha256'])
        with self.assertRaisesRegex(ValueError,'not held'):
            projection.host_observation(f.c,reader=reader,read_birth=lambda:1100,verify_held=lambda:False,source_ruler=666)


def pins():
    paths={Path(m.__file__).resolve() for m in list(sys.modules.values()) if getattr(m,'__file__',None)}
    paths.add(Path(__file__).resolve())
    return {str(p):sha(p.read_bytes()) for p in sorted(paths) if p.is_relative_to(ROOT) and p.suffix=='.py'}


if __name__=='__main__':
    OUTPUT=PRIVATE/'b_warm_projection_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');OUTPUT.mkdir(parents=True)
    before=pins();stream=io.StringIO()
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Cases))
    (OUTPUT/'test.log').write_text(stream.getvalue(),encoding='utf-8')
    after=pins();stable=before==after
    report=dict(family='san14.b-warm-projection.v1',result='PASS' if result.wasSuccessful() and result.testsRun==6 and stable else 'FAIL',
        tests=result.testsRun,sources=after,inputs_unchanged=stable,game_access=False,native_calls=False,
        actual_tls=False,actual_journal=True,actual_period_coordinator=True,actual_native_sampler_on_fake_memory=True,
        native_gameplay_enabled=False,full_world_verified=False,ready_authorized=False,
        failures=[(str(t),detail) for t,detail in result.failures+result.errors])
    report['artifacts']={str(p):sha(p.read_bytes()) for p in OUTPUT.rglob('*') if p.is_file()}
    (OUTPUT/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(OUTPUT/'result.json');print(stream.getvalue())
    raise SystemExit(0 if report['result']=='PASS' else 1)
