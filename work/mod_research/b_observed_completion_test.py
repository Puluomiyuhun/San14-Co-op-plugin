"""Same-day Room + actual control/Session/TLS/journals; native/RAM doubles.

No strong adapter, verify_held=True, run_model or complete_model is used.
The A fixture reads its owned tables and emits finite typed observations. B uses
the unchanged complete planning sampler on its owned layout and actual Session.
"""
from copy import deepcopy
from datetime import datetime
import hashlib
import io
import json
from pathlib import Path
import queue
import secrets
import struct
import sys
import threading
import unittest
from unittest.mock import patch
from types import SimpleNamespace

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];PRIVATE=ROOT.parent/'mod_research'
sys.path[:0]=[str(PRIVATE/'python_deps'),str(ROOT/'outputs/san14-link')]
import b_warm_room_test as transport
import b_warm_world as world
import b_warm_profile_capture as original
import b_warm_stable_capture as stable
import b_remote_session_boundary as boundary_module
import b_remote_session_test as session_fixture
from b_remote_session_boundary import Observation
from b_warm_refresh_remote_owner_test import ScopedRules,WarmMemory,sync_reader
from b_warm_profile_capture_test import Reader as PlanningReader
from b_warm_world_test import Reader
from b_warm_adapter_key import Native
from b_warm_profile_contract import Profile,Date,Identity
from human_rules_world_lifecycle import WorldGeneration,NextWorldRequest
from b_warm_room import receive_staged
from b_warm_bootstrap_protocol import receive_bootstrap_staged
from room_transport import Client
from checkpoint_fresh_save_binding import LocalWorldObservation
from checkpoint_fresh_save_binding_test import model_artifact
from authoritative_sync import scope_from_room,canonical,digest,next_node
from a_room_bootstrap_protocol import BootstrapCoordinator
from a_observed_room import ObservedRoom,ObservedFreshSaveBinding as BootstrapFreshSaveBinding
from a_observed_boundary_test import Fixture as AFixture
from observed_completion_contract import packet,unpack,ACTION,COVERAGE
from b_observed_completion import GuestCompletion
import a_room_native_control as control_module
import a_save_runtime_contract as wire
import a_save_repeat_contract as repeat

OUTPUT=None;ROWS=[];FROZEN_CAPTURE=original.capture_planning


def sha(raw):return hashlib.sha256(raw).hexdigest()
def put_date(reader,node):
    reader.memory.put(reader.world+0x34,struct.pack('<HBB',node['year'],node['month'],node['day'])+bytes([0,0,reader.force,1]))


class Cases(unittest.TestCase):
    local=session_fixture.Cases.local

    def setUp(self):
        self.key=secrets.token_bytes(32);self.host_fixture=AFixture();self.host=self.host_fixture.reader;self.host_key='1'*64
        original_manifest=transport.manifest
        def manifest():
            v=original_manifest();v['profile']['game_sha256']=world.objects.GAME_SHA256;return v
        def coordinator(room):
            c=BootstrapCoordinator(scope_from_room(room),world.CONTRACT,'d'*64,{'A':'a'*32,'B':'b'*32},
                dict(year=203,month=8,day=11,phase='PLANNING_BOUNDARY'))
            room.bind_coordinator(c);return c
        with patch.object(transport,'manifest',manifest),patch.object(transport,'make_coordinator',coordinator), \
             patch.object(transport,'WarmRoom',ObservedRoom),patch.object(transport,'FreshSaveBinding',BootstrapFreshSaveBinding):
            transport.RoomTests.setUp(self)
        put_date(self.host,self.c.node)
        self.room.enroll_observed_adapter(self.key,host_sampler=self.host_sample,host_boundary=self.host_boundary,
            host_receipt_key=lambda:self.host_key,source_kind='FIXTURE_ONLY')
        self.private_key=self.folder/'adapter.key';Native().write_new(self.private_key,self.key)
        slot=self.folder/'slot';slot.mkdir();self.target=slot/'svdexccSC03.s14';self.target.write_bytes(b'old owned target'*40)
        self.records=self.folder/'bridge';self.records.mkdir()
        self.rules=ScopedRules(self.c.scope);self.rules.current.day=11
        self.guest=Reader('A');self.guest.side='B';self.guest.pid=self.rules.pid
        sync_reader(self.guest,self.rules.current)
        initial=self.rules.prepare(WorldGeneration(1,'1'*64,bytes(self.rules.current)));initial.install()
        self.life=SimpleNamespace(current=initial)
        self.warm=WarmMemory(self.rules,self.target,'success',self.guest);self.birth=self.rules.birth
        self.plan_memory=PlanningReader();self.plan_memory.pid=self.guest.pid;self.plan_memory.birth=self.birth
        def capture(reader,p,ruler,**kw):
            fake=self.plan_memory;fake.profile=Profile.from_buffer_copy(bytes(p));fake.ruler=ruler
            def inner(r,profile,expected_ruler):
                return FROZEN_CAPTURE(r,profile,expected_ruler,context_reader=lambda _:dict(snapshot=reader.snapshot()),
                    birth_reader=lambda _:self.birth,range_check=lambda r,a,n:r.memory.span(a,n))
            with patch.object(original,'capture_planning',side_effect=inner):
                return stable.capture_planning(fake,p,ruler,**kw,birth_reader=lambda _:self.birth)
        self.capture_patch=patch.object(boundary_module,'capture_planning',side_effect=capture);self.capture_patch.start()
        self.stage_patch=patch('b_warm_staging.apply',side_effect=AssertionError('Physical staging forbidden'));self.stage_patch.start()
        self.session=None;self.adapter=None

    def tearDown(self):
        if self.warm.native_lease:self.warm.native_lease.close() # owned fixture only
        self.capture_patch.stop();self.stage_patch.stop()
        transport.RoomTests.tearDown(self)

    def host_sample(self,p,k):
        return self.host_fixture.provider.sample(scope=self.c.scope,epoch=self.c.epoch,period=self.c.period,
            profile=p,receipt_key=k)

    def host_boundary(self,p,kind):
        node=dict(year=p.loaded.year,month=p.loaded.month,day=p.loaded.day,phase='PLANNING_BOUNDARY')
        return self.host_fixture.provider.observe(node,p)

    def observation(self,node=None):
        bound=self.binding.validate_context();node=node or bound['node']
        self.assertIn(node,(bound['node'],self.c.node))
        return self.host_fixture.provider.world_observation(node,bound['attachments']['A'])

    def complete_host(self,generation):
        s=self.host_fixture.runtime;s.saveStatus=5;s.saveGeneration=s.mailboxCount=generation
        s.mailboxStates[:]=[5]*generation+[0]*(2-generation)
        s.binds=s.queues=s.workerJoined=s.fileVerified=1;s.phaseMask=31;s.originalReturned=27

    def received(self,generation,package):
        m=package.manifest
        def connect(token):
            return Client('127.0.0.1',self.download,self.fp,
                dict(method='checkpoint_download',credential=token,profile=self.room.manifest['profile']))
        receive=receive_bootstrap_staged if generation==1 else receive_staged
        r=receive(self.b,connect,checkpoint_id=package.checkpoint_id,scope=self.c.scope,epoch=self.c.epoch,
            period=self.c.period,cut=m['cut'],attachments=self.c.attachments,directory=self.folder/f'received-{generation}')
        p=Profile();p.file.name=b'svdexccSC03.s14';p.file.slot=63;p.file.size=m['parts']['world.s14']['size']
        p.file.sha256[:]=bytes.fromhex(m['parts']['world.s14']['sha256'])
        p.before=Date(*(self.c.node[k] for k in ('year','month','day')))
        p.loaded=Date(*(m['node'][k] for k in ('year','month','day')))
        p.source=Identity(666,12,11);p.target=Identity(952,2,2);p.currentForce=12 if generation==1 else 2
        request=NextWorldRequest(generation+1,package.checkpoint_id,bytes([0x70+generation])*16,
            m['node']['year'],m['node']['month'],m['node']['day'])
        self.warm.request=request
        if self.session is None:self.local(p);self.adapter=GuestCompletion(self.session)
        return r,request,p

    def first(self):
        self.c.begin_bootstrap();reservation=self.binding.reserve(1,'mp00000001.s14',self.observation())
        self.artifacts[1]=model_artifact(reservation.request,1,data=b'explicit same-date owned native Save'*2400)
        self.complete_host(1)
        package=self.binding.publish(1,self.observation)
        return self.received(1,package)

    def test_actual_room_control_two_session_loads(self):
        control=control_module.RoomTurnControl()
        self.binding=BootstrapFreshSaveBinding(self.room,self.c,native_room_id=bytes.fromhex(digest(self.c.scope)),
            native_room_epoch=71,artifact_reader=control.copy_artifact,source_kind='FIXTURE_ONLY')
        self.c.begin_bootstrap();raw=wire.envelope(wire.Prepare,'Prepare',bytes([9])*32)
        raw.pid,raw.birth,raw.epoch=101,1001,123;raw.year,raw.month,raw.day,raw.force,raw.ruler=203,8,11,12,666
        prep=control_module.prepare_from_room(raw,self.binding)
        owner=self;events=queue.Queue();order=[];submits=[];kept=[];answers=[];errors=[];commands=[];polls=[]
        class Channel:
            def submit(self,reservation):submits.append(reservation);order.append('submit-'+str(reservation.generation))
            def wait_artifact(self,generation,timeout):
                owner.host_key=sha(('actual-channel-double-'+str(generation)).encode())
                owner.complete_host(generation)
                return model_artifact(submits[-1].request,generation,data=('owned native Save '+str(generation)).encode()*2100)
            def snapshot(self):return None
        def call(op,value=None):
            if op=='RequestNext':
                self.assertTrue(self.c.bootstrap_completed);self.assertEqual(self.c.phase,'RUNNING')
                self.assertEqual(len(self.c.applied_receipts),1);self.assertFalse(commands)
                commands.append(value);order.append('request-next');return value,None
            self.assertEqual(op,'RepeatSnapshot');polls.append(op)
            q=repeat.envelope(repeat.Snapshot,op,bytes(prep.nonce));q.request=commands[0].request
            q.requested=q.hostThread=q.previousArtifactMatched=q.retiredSerial=q.retiredCount=1
            q.state=3 if len(polls)<3 else 4;q.activeGeneration=1 if q.state==3 else 2
            q.drainPending=int(q.state==3);q.nativeDateMatched=int(q.state==4)
            if q.state==4:self.host_fixture.complete_and_rebuild()
            return q,None
        def drive():
            try:
                answers.append(control.drive(Channel(),prep,['mp00000001.s14','mp00000002.s14'],call,
                    lambda *a:kept.append(a),lambda k,v:events.put((k,v)),self.binding,self.observation,wait_seconds=20))
            except BaseException as exc:errors.append(repr(exc))
            finally:events.put(('done',None))
        worker=threading.Thread(target=drive);worker.start();replies=[];journals=[];identities=None
        try:
            while True:
                kind,value=events.get(timeout=30)
                if kind=='done':break
                if kind.startswith('await-b-'):
                    generation=int(kind[-1]);r,q,p=self.received(generation,self.room.artifacts)
                    graph=tuple(map(id,(self.session,self.session.warm,self.session.lifecycle,self.session.bridge,self.adapter)))
                    if identities is None:identities=graph
                    self.assertEqual(identities,graph)
                    reply=self.adapter.apply(r,q,p);replies.append(reply);journals.append(r.journal.status())
                    order.append('loaded-'+str(generation))
                    if generation==1:
                        self.assertEqual(self.c.node['day'],11);self.assertFalse(self.c.ready)
                elif kind=='await-room-turn':
                    for client in (self.a,self.b):
                        self.assertTrue(client.request(dict(action='period_ready',epoch=self.c.epoch,ready=True))['ok'])
                    permit=self.c.seal_inputs();self.c.begin_simulation(permit);order.append('sealed-turn')
        finally:worker.join(timeout=25)
        self.assertFalse(worker.is_alive());self.assertEqual(errors,[])
        self.assertEqual(order,['submit-1','loaded-1','sealed-turn','request-next','submit-2','loaded-2'])
        self.assertEqual((self.c.period,self.c.node['day']),(3,21));self.assertEqual(len(self.session.sessions),2)
        self.assertEqual(len(self.session.lifecycle.retained),3);self.assertEqual(len(self.adapter.history),2)
        self.assertEqual(self.adapter.phase,'TWO_COMPLETIONS_RETAINED');self.assertEqual(len(kept),2)
        self.assertTrue(all(j['status']=='COMPLETED' for j in journals));self.assertIsNone(self.room._warm_ack)
        saved=json.loads((self.folder/'received-1'/'observed-adapter-completion.json').read_text())
        duplicate=self.b.request(packet(self.key,saved));self.assertTrue(duplicate['duplicate']);self.assertEqual(self.c.period,3)
        ROWS.append(dict(case=self._testMethodName,order=order,replies=replies,journals=journals,
            warm=self.warm.events,rules=self.rules.events,control=answers[0],same_day_bootstrap=True,
            formal_completions=2,strong_boolean_adapter_used=False))

    def test_lost_begin_reply_is_terminal_without_native_load(self):
        r,q,p=self.first();request=self.b.request
        def lose(value):
            result=request(value)
            if value.get('action')==ACTION and unpack(self.key,value)['kind']=='begin':raise EOFError('Owned lost begin reply')
            return result
        self.b.request=lose
        with self.assertRaisesRegex(EOFError,'lost begin'):self.adapter.apply(r,q,p)
        self.b.request=request
        self.assertFalse(self.warm.events);self.assertIsNotNone(self.c.load_intent)
        self.assertEqual(r.journal.status()['status'],'STAGED');self.assertEqual(self.session.phase,'TERMINAL')
        with self.assertRaises(Exception):self.adapter.apply(r,q,p)
        with self.assertRaises(Exception):GuestCompletion(self.session)
        ROWS.append(dict(case=self._testMethodName,native_loads=0,journal=r.journal.status(),status=self.adapter.status()))

    def test_lost_complete_reply_retains_success_without_reload(self):
        r,q,p=self.first();request=self.b.request
        def lose(value):
            result=request(value)
            if value.get('action')==ACTION and unpack(self.key,value)['kind']=='complete':raise EOFError('Owned lost complete reply')
            return result
        self.b.request=lose
        with self.assertRaisesRegex(EOFError,'lost complete'):self.adapter.apply(r,q,p)
        self.b.request=request;events=list(self.warm.events)
        self.assertEqual((self.c.period,self.c.node['day']),(2,11));self.assertFalse(self.c.ready)
        self.assertEqual(r.journal.status()['status'],'COMPLETED');self.assertEqual(len(self.session.sessions),1)
        with self.assertRaises(Exception):self.adapter.apply(r,q,p)
        self.assertEqual(events,self.warm.events);self.assertEqual(self.session.phase,'TERMINAL')
        ROWS.append(dict(case=self._testMethodName,native_loads=1,journal=r.journal.status(),status=self.adapter.status()))

    def test_pending_input_refuses_before_signed_begin(self):
        r,q,p=self.first();self.plan_memory.memory.put(self.plan_memory.states[4]+0x660,1,'<I')
        with self.assertRaisesRegex(ValueError,'Pending input'):self.adapter.apply(r,q,p)
        self.assertIsNone(self.c.load_intent);self.assertFalse(self.warm.events)
        self.assertFalse((r.directory/'observed-adapter-begin.json').exists())
        ROWS.append(dict(case=self._testMethodName,native_loads=0,signed_begin=False))

    def test_fence_claim_in_signed_boundary_is_rejected(self):
        r,q,p=self.first();request=self.b.request
        def tamper(value):
            if value.get('action')==ACTION:
                body=unpack(self.key,value);body['boundary']['input_exclusion_proven']=True;value=packet(self.key,body)
            return request(value)
        self.b.request=tamper
        with self.assertRaises(ValueError):self.adapter.apply(r,q,p)
        self.b.request=request;self.assertFalse(self.warm.events);self.assertIsNone(self.c.load_intent)
        ROWS.append(dict(case=self._testMethodName,native_loads=0,false_fence_rejected=True))


def pins():
    paths={Path(m.__file__).resolve() for m in list(sys.modules.values()) if getattr(m,'__file__',None)}
    paths.add(Path(__file__).resolve())
    return {str(p):sha(p.read_bytes()) for p in sorted(paths) if p.is_relative_to(ROOT) and p.suffix=='.py'}


if __name__=='__main__':
    OUTPUT=PRIVATE/'b_observed_completion_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');OUTPUT.mkdir(parents=True)
    transport.OUTPUT=OUTPUT;before=pins();stream=io.StringIO()
    run=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Cases))
    (OUTPUT/'test.log').write_text(stream.getvalue(),encoding='utf-8');sources=pins();unchanged=before==sources
    report=dict(result='PASS' if run.wasSuccessful() and unchanged else 'FAIL',tests=run.testsRun,sources=sources,
        inputs_unchanged=unchanged,cases=ROWS,actual_tls=True,actual_journal=True,actual_room_turn_control=True,
        actual_retained_session=True,actual_planning_sampler=True,native_RAM_save_load_publish_doubles=True,
        actual_a_observed_boundary=True,
        strong_boolean_adapter_used=False,same_day_bootstrap=True,game_access=False,independent_guest_process=False,
        failures=[(str(t),d) for t,d in run.errors+run.failures])
    report['artifacts']={str(p):sha(p.read_bytes()) for p in OUTPUT.rglob('*') if p.is_file()}
    (OUTPUT/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(OUTPUT/'result.json');print(stream.getvalue());raise SystemExit(0 if report['result']=='PASS' else 1)
