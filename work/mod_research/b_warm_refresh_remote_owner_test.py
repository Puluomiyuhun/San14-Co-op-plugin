"""Actual TLS, journals, native-refresh bridge and original rule lifecycle predicates.

Native load, rule memory/publication and boundary are explicit doubles. This
owner-composition suite runs both control seats in one test process; the frozen
remote-completion suite separately covers a distinct B operating-system process.
"""
from datetime import datetime
import hashlib
import io
import json
from pathlib import Path
import secrets
import struct
import sys
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];PRIVATE=ROOT.parent/'mod_research'
sys.path[:0]=[str(PRIVATE/'python_deps'),str(ROOT/'outputs/san14-link')]
import b_warm_room_test as transport
import b_warm_world as world
import b_warm_staging as files
from b_warm_joint_test import Joint as TLSFixture
from b_warm_bootstrap_test import NativeRulesDouble,WarmDouble,writer_blocked
from b_warm_refresh_bootstrap import BootstrapRulesBridge
from b_warm_bootstrap_protocol import receive_bootstrap_staged
from b_warm_room import receive_staged
from b_warm_remote_completion import RemoteCompletionRoom,ACTION,unpack
from b_warm_settled_completion import SettledRemoteCompletionRoom
from b_warm_refresh_remote_owner import RetainedRemoteOwner
from b_warm_world_test import Reader
from b_warm_profile_contract import Profile,Date,Identity
from human_rules_world_lifecycle import WorldGeneration,WorldLifecycle,NextWorldRequest
from checkpoint_fresh_save_binding_test import run_model,model_artifact
from b_warm_projection import host_observation
from authoritative_sync import next_node
from room_transport import Client

OUTPUT=None;EVIDENCE=[]
def sha(raw):return hashlib.sha256(raw).hexdigest()


def sync_reader(reader,c):
    oldroot=reader.root
    for _,offset,count,_,_,_ in world.TABLES:
        raw=reader.memory.read(oldroot+offset,count*8);reader.memory.put(c.root+offset,raw)
    reader.root,reader.world=c.root,c.world
    reader.force=c.viewer;reader.ruler=666 if c.viewer==12 else 952
    reader.memory.put(reader.memory.base+0x1FCA1E0,struct.pack('<Q',c.root))
    reader.memory.put(c.root+0x85130,struct.pack('<Q',c.world))
    reader.memory.put(c.world+0x34,struct.pack('<HBB',c.year,c.month,c.day)+bytes([0,0,c.viewer,1]))


class ScopedRules(NativeRulesDouble):
    def __init__(self,scope):self.scope_value=scope;super().__init__()
    def config(self,*args):
        c=super().config(*args);c.room[:]=bytes.fromhex(self.scope_value['room_id'])
        c.rules_digest[:]=bytes.fromhex(self.scope_value['profile']['rules_sha256']);return c


class WarmMemory(WarmDouble):
    """Explicit native double; actual target write/lease, no Python staging."""
    def __init__(self,rules,target,case,reader):
        super().__init__(rules,target,case);self.reader=reader;self.native_lease=None;self.old_files=[]
    def load(self,bank,p,raw,*,target,previous,backup):
        assert target==self.target and files.read_file(target)[0]==previous
        assert backup.read_bytes()==target.read_bytes() and not writer_blocked(target)
        # The actual ResidentPort restore must already have reinstated sources.
        assert all(self.rules.read(a,16)==bytes([0x90+i])*16 for i,a in enumerate(self.rules.sources))
        self.old_files.append(backup.read_bytes());self.events.append(['load',bank,p.currentForce,p.target.force])
        assert sha(raw)==bytes(p.file.sha256).hex()
        target.write_bytes(raw);self.native_lease=files.Handle(target)
        assert writer_blocked(target)
        req=self.request;self.rules.current=self.rules.config(req.generation,req.day,p.target.force,req.epoch)
        sync_reader(self.reader,self.rules.current)
        if self.case=='load-failed':raise RuntimeError('Explicit load failure after native write')
        self.native_lease.close();self.native_lease=None;assert not writer_blocked(target)
        accepted=dict(result='PASS_WARM_LOAD_RETIRED',receipt_key=str(bank+1)*64,
            source_force=p.source.force,source_ruler=p.source.ruler,target_force=p.target.force,target_ruler=p.target.ruler,
            ready_authorized=False,full_world_verified=False,input_exclusion_proven=False)
        refresh=dict(state=4,error=0,captured=1,executeCalls=1,writeAttempts=1,writeReturned=1,
            intentCreated=1,intentDurable=1,matched=1,leaseHeld=0,leaseReleased=1,releaseCalls=1,
            previousReads=2,newReads=2,osError=0,exceptionCode=0,attempt=bank+1,epoch=bank+10,generation=bank+1,
            previous_size=previous['size'],previous_sha256=previous['sha256'],new_size=len(raw),new_sha256=sha(raw),
            stage='released_after_native_retirement')
        if self.case=='bad-refresh':refresh['leaseReleased']=0
        return dict(accepted=accepted,attempt=bank+1,pid=self.rules.pid,birth=self.rules.birth,
            profile_sha256=sha(bytes(p)),slots_restored=True,target_lease_released=True,refresh=refresh,
            snapshot=dict(date=dict(year=p.loaded.year,month=p.loaded.month,day=p.loaded.day),
                player=dict(force_id=p.target.force,ruler_id=p.target.ruler)))
    def abort(self):
        self.abort_lease=writer_blocked(self.target);self.events.append(['abort'])



class Cases(unittest.TestCase):
    def tearDown(self):
        if hasattr(self,'warm') and self.warm.native_lease:self.warm.native_lease.close()
        if hasattr(self,'staging_patch'):self.staging_patch.stop()
        transport.RoomTests.tearDown(self)
    def setUp(self):
        self.settled=self._testMethodName=='test_settled_second_correction_same_owner'
        room_type=SettledRemoteCompletionRoom if self.settled else RemoteCompletionRoom
        with patch.object(transport,'WarmRoom',room_type):TLSFixture.setUp(self)
        self.staging_patch=patch.object(files,'apply',side_effect=AssertionError('Physical staging forbidden'));self.staging_patch.start()
        self.key=secrets.token_bytes(32);self.host=Reader('A');self.host_key='1'*64
        self.room.enroll_adapter(self.key,host_sampler=lambda p,k:world.sample(self.host,scope=self.c.scope,
            epoch=self.c.epoch,period=self.c.period,profile=p,side='A',receipt_key=k,read_birth=lambda:1001),
            verify_held=lambda:True,host_receipt_key=lambda:self.host_key,source_kind='FIXTURE_ONLY')
        slot=self.folder/'owned-slot';slot.mkdir();self.target=slot/files.NAME
        self.original=b'original owned slot 63'*30;self.target.write_bytes(self.original)
        records=self.folder/'bridge-records';records.mkdir();self.records=records
        self.rules=ScopedRules(self.c.scope);self.guest=Reader('A');self.guest.side='B';self.guest.pid=self.rules.pid
        sync_reader(self.guest,self.rules.current)
        initial=self.rules.prepare(WorldGeneration(1,'1'*64,bytes(self.rules.current)));initial.install()
        self.guard_calls=0;self.guard_fail=False;self.holds=[];self.birth=self.rules.birth
        def guard():
            self.guard_calls+=1
            if self.guard_fail:raise RuntimeError('Explicit existing boundary no longer held')
        self.guard=guard
        self.life=WorldLifecycle(initial,guard_check=guard,on_hold=lambda reason:self.holds.append(reason))
        self.warm=WarmMemory(self.rules,self.target,'success',self.guest)
        self.bridge=BootstrapRulesBridge(self.life,self.warm,target=self.target,records=records)
        self.owner=RetainedRemoteOwner(self.bridge,self.b,self.key,scope=self.c.scope,read_birth=lambda:self.birth,
            observe_loaded=self.rules.observe,prepare_rules=self.rules.prepare,guard_check=guard,
            on_hold=lambda reason:self.holds.append(reason))

    def offer(self,generation):
        node=next_node(self.c.node)
        self.host.memory.put(self.host.world+0x34,struct.pack('<HBB',node['year'],node['month'],node['day'])+bytes([0,0,12,1]))
        self.host_key=sha(('owned Save double '+str(generation)).encode());run_model(self.c)
        observe=lambda:host_observation(self.c,reader=self.host,read_birth=lambda:1001,verify_held=lambda:True,source_ruler=666)
        reservation=self.binding.reserve(generation,f'mp{generation:08d}.s14',observe())
        raw=('explicit loaded file '+str(generation)).encode()*3000
        self.artifacts[generation]=model_artifact(reservation.request,generation,data=raw)
        package=self.binding.publish(generation,observe)
        def connect(token):return Client('127.0.0.1',self.download,self.fp,
            dict(method='checkpoint_download',credential=token,profile=self.room.manifest['profile']))
        recv=receive_bootstrap_staged if generation==1 else receive_staged
        received=recv(self.b,connect,checkpoint_id=package.checkpoint_id,scope=self.c.scope,epoch=self.c.epoch,
            period=self.c.period,cut=package.manifest['cut'],attachments=self.c.attachments,directory=self.folder/f'received-{generation}')
        p=Profile();p.file.name=files.NAME.encode();p.file.slot=63;p.file.size=len(raw);p.file.sha256[:]=bytes.fromhex(sha(raw))
        p.before=Date(self.c.node['year'],self.c.node['month'],self.c.node['day'])
        p.loaded=Date(node['year'],node['month'],node['day']);p.source=Identity(666,12,11);p.target=Identity(952,2,2)
        p.currentForce=self.guest.force
        if self.settled and generation==2:
            # Explicit fixture simulation outcome, not a game date write. Keep
            # the old installed module's immutable Config unchanged; only its
            # fresh export/current native-memory double advances in date.
            self.rules.current.year,self.rules.current.month,self.rules.current.day=node['year'],node['month'],node['day']
            sync_reader(self.guest,self.rules.current)
            p.before=Date(node['year'],node['month'],node['day'])
        req=NextWorldRequest(generation+1,package.checkpoint_id,bytes([0x70+generation])*16,node['year'],node['month'],node['day'])
        self.warm.request=req
        return received,req,p

    def test_same_owner_actual_bridge_two_periods(self):
        ids=tuple(map(id,(self.owner,self.warm,self.life,self.bridge,self.guest)));rows=[]
        for n in (1,2):
            received,req,p=self.offer(n);before_view=self.guest.force
            result=self.owner.apply(received,req,p)
            self.assertEqual(tuple(map(id,(self.owner,self.warm,self.life,self.bridge,self.guest))),ids)
            self.assertEqual(received.journal.status()['status'],'COMPLETED');self.assertEqual(self.c.period,n+1)
            self.assertEqual((self.owner.period,self.owner.phase),(n+1,'ACTIVE'));self.assertEqual(self.guest.force,2)
            self.assertEqual(len(self.owner.sessions),n);self.assertEqual(len(self.owner.samples),n)
            self.assertEqual(self.life.current.world, self.rules.ports[-1].world)
            self.assertEqual(self.owner.attachments,self.c.attachments)
            self.assertEqual(self.room._warm_ack['packet']['checkpoint_id'],req.checkpoint)
            rows.append(dict(before=before_view,result=result,journal=received.journal.status()))
        self.assertEqual(len(self.life.retained),3);self.assertEqual(len(self.bridge.completed),2)
        self.assertEqual(self.warm.events,[['open',0],['load',0,12,2],['open',1],['handover',1],['load',1,2,2]])
        backups=self.warm.old_files
        self.assertCountEqual(backups,[self.original,self.artifacts[1].data]);self.assertEqual(self.target.read_bytes(),self.artifacts[2].data)
        self.assertFalse(self.holds);self.assertGreater(self.guard_calls,20)
        EVIDENCE.append(dict(case='settled-second-correction' if self.settled else 'retained-owner-two-periods',
            rows=rows,warm=self.warm.events,rules=self.rules.events,
            retained_rules=3,actual_backups=2,guard_calls=self.guard_calls))

    def test_settled_second_correction_same_owner(self):
        self.test_same_owner_actual_bridge_two_periods()

    def test_lost_formal_reply_keeps_entire_owner_failed(self):
        r,q,p=self.offer(1);original=self.b.request
        def drop(value):
            answer=original(value)
            if value.get('action')==ACTION and unpack(self.key,value)['kind']=='complete':raise EOFError('Actual formal reply lost')
            return answer
        self.b.request=drop
        with self.assertRaises(EOFError):self.owner.apply(r,q,p)
        self.b.request=original
        self.assertEqual(self.c.period,2);self.assertEqual(self.owner.phase,'HELD');self.assertEqual(len(self.life.retained),2)
        self.assertEqual(len(self.bridge.completed),1);self.assertEqual(r.journal.status()['status'],'COMPLETED')
        events=list(self.warm.events)
        with self.assertRaises(Exception):self.owner.apply(r,q,p)
        self.assertEqual(self.warm.events,events);self.assertTrue(self.holds)
        EVIDENCE.append(dict(case='lost-formal-reply',owner_phase=self.owner.phase,loaded_once=True,
            retained_rules=len(self.life.retained),holds=self.holds))

    def test_native_failure_preserves_file_lease_and_no_replay(self):
        r,q,p=self.offer(1);self.warm.case='load-failed'
        with self.assertRaisesRegex(RuntimeError,'Explicit load failure'):self.owner.apply(r,q,p)
        self.assertTrue(self.warm.abort_lease);self.assertEqual(self.owner.phase,'HELD')
        self.assertEqual(r.journal.status()['status'],'INTENT');self.assertEqual(self.c.period,1)
        self.assertFalse(self.c.applied_receipts);self.assertIsNone(self.room._warm_ack)
        events=list(self.warm.events)
        with self.assertRaises(Exception):self.owner.apply(r,q,p)
        self.assertEqual(events,self.warm.events);self.assertEqual(len(self.life.retained),1)
        EVIDENCE.append(dict(case='native-failure',abort_file_lease_held=True,retained_rules=1,warm=events))

    def test_incomplete_refresh_never_acks_or_completes(self):
        r,q,p=self.offer(1);self.warm.case='bad-refresh'
        with self.assertRaisesRegex(files.Refused,'Native refresh'):self.owner.apply(r,q,p)
        self.assertEqual(self.owner.phase,'HELD');self.assertEqual(r.journal.status()['status'],'INTENT')
        self.assertEqual(self.c.period,1);self.assertIsNone(self.room._warm_ack)
        self.assertFalse(self.c.applied_receipts);self.assertEqual(len(self.life.retained),1)
        self.assertEqual(len(self.bridge.completed),0)
        events=list(self.warm.events)
        with self.assertRaises(Exception):self.owner.apply(r,q,p)
        self.assertEqual(self.warm.events,events)
        EVIDENCE.append(dict(case='incomplete-refresh',no_ack=True,no_formal_completion=True,no_retry=True))

    def test_changed_target_before_second_native_load_holds(self):
        r,q,p=self.offer(1);self.owner.apply(r,q,p)
        r,q,p=self.offer(2);self.target.write_bytes(b'unexpected external target change')
        events=list(self.warm.events)
        with self.assertRaisesRegex(files.Refused,'target identity changed'):self.owner.apply(r,q,p)
        self.assertEqual(self.owner.phase,'HELD');self.assertEqual(self.c.period,2)
        self.assertEqual(r.journal.status()['status'],'INTENT');self.assertEqual(self.warm.events,events)
        self.assertEqual(len(self.bridge.completed),1);self.assertEqual(len(self.life.retained),2)
        EVIDENCE.append(dict(case='changed-second-target',second_native_load=False,no_retry=True))

    def test_changed_birth_rejected_before_remote_intent(self):
        r,q,p=self.offer(1);self.birth+=1
        with self.assertRaisesRegex(ValueError,'incarnation'):self.owner.apply(r,q,p)
        self.assertIsNone(self.c.load_intent);self.assertFalse(self.warm.events);self.assertEqual(self.target.read_bytes(),self.original)
        self.assertEqual(self.owner.phase,'HELD');self.assertTrue(self.holds)
        EVIDENCE.append(dict(case='wrong-incarnation',loads=0,remote_intent=False))

    def test_failed_existing_guard_rejected_before_remote_intent(self):
        r,q,p=self.offer(1);self.guard_fail=True
        with self.assertRaisesRegex(RuntimeError,'boundary'):self.owner.apply(r,q,p)
        self.assertIsNone(self.c.load_intent);self.assertFalse(self.warm.events);self.assertEqual(self.owner.phase,'HELD')
        self.assertTrue(self.holds);EVIDENCE.append(dict(case='external-guard-fails',loads=0,remote_intent=False))


def pins():
    paths={Path(m.__file__).resolve() for m in list(sys.modules.values()) if getattr(m,'__file__',None)}
    paths.add(Path(__file__).resolve())
    return {str(p):sha(p.read_bytes()) for p in sorted(paths) if p.is_relative_to(ROOT) and p.suffix=='.py'}


if __name__=='__main__':
    OUTPUT=PRIVATE/'b_warm_refresh_remote_owner_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');OUTPUT.mkdir(parents=True)
    transport.OUTPUT=OUTPUT;before=pins();stream=io.StringIO()
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Cases))
    (OUTPUT/'test.log').write_text(stream.getvalue(),encoding='utf-8');sources=pins();stable=all(sources.get(k)==v for k,v in before.items())
    report=dict(result='PASS' if result.wasSuccessful() and result.testsRun==8 and stable else 'FAIL',tests=result.testsRun,
        sources=sources,inputs_unchanged=stable,cases=EVIDENCE,actual_tls=True,actual_native_double_file_write=True,physical_staging_forbidden=True,actual_rule_predicates=True,
        game_access=False,native_calls=False,fake_memory=True,fake_publish_load=True,fake_guard=True,
        failures=[(str(t),detail) for t,detail in result.failures+result.errors])
    report['artifacts']={str(p):sha(p.read_bytes()) for p in OUTPUT.rglob('*') if p.is_file()}
    (OUTPUT/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(OUTPUT/'result.json');print(stream.getvalue());raise SystemExit(0 if report['result']=='PASS' else 1)
