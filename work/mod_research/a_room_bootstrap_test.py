"""Real TLS, separate B, real SQLite and formal loaded; native/RAM/held doubles."""
from copy import deepcopy
from datetime import datetime
import base64
import io
import json
import os
import queue
import threading
from pathlib import Path
import secrets
import sys
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PRIVATE=ROOT.parent/'mod_research'
sys.path[:0]=[str(PRIVATE/'python_deps'),str(ROOT/'outputs/san14-link')]
import a_room_native_control as native_control
import a_save_runtime_contract as wire
import a_save_repeat_contract as repeat
import b_warm_remote_completion_test as prior
import b_warm_room_test as transport
from a_room_bootstrap_protocol import BootstrapCoordinator, BootstrapRoom, BootstrapFreshSaveBinding, host_observation
from checkpoint_room_client import RoomConnection
from authoritative_sync import scope_from_room, next_node, digest
from checkpoint_fresh_save_binding import LocalWorldObservation
from checkpoint_fresh_save_binding_test import model_artifact
from b_warm_profile_contract import Profile, Date, Identity
from b_warm_remote_completion import packet
import b_warm_world as world
from b_warm_world_test import Reader

OUTPUT=None
ROWS=[]


class Cases(unittest.TestCase):
    tearDown=transport.RoomTests.tearDown
    def setUp(self):
        self.key=secrets.token_bytes(32);self.host_reader=Reader('A');self.host_key='1'*64
        original_manifest=transport.manifest
        def manifest():
            v=original_manifest();v['profile']['game_sha256']=world.objects.GAME_SHA256;return v
        def coordinator(room):
            c=BootstrapCoordinator(scope_from_room(room),world.CONTRACT,'d'*64,
                {'A':'a'*32,'B':'b'*32},dict(year=203,month=8,day=11,phase='PLANNING_BOUNDARY'))
            room.bind_coordinator(c)
            return c
        def control(host,port,fingerprint,greeting):
            if greeting['method']=='join':
                return prior.ChildControl(host,port,fingerprint,greeting,self.key,self.folder)
            return RoomConnection(host,port,fingerprint,greeting)
        with patch.object(transport,'manifest',manifest),patch.object(transport,'make_coordinator',coordinator), \
             patch.object(transport,'WarmRoom',BootstrapRoom),patch.object(transport,'FreshSaveBinding',BootstrapFreshSaveBinding), \
             patch.object(transport,'RoomConnection',control):
            transport.RoomTests.setUp(self)
        self.room.enroll_adapter(self.key,host_sampler=lambda p,k:world.sample(self.host_reader,
            scope=self.c.scope,epoch=self.c.epoch,period=self.c.period,profile=p,side='A',receipt_key=k,read_birth=lambda:1001),
            verify_held=lambda:True,host_receipt_key=lambda:self.host_key,source_kind='FIXTURE_ONLY')
        self.assertNotEqual(self.b.pid,os.getpid())
        self.assertTrue(self.b.request(dict(action='warm_rules_binding'))['ok'])

    def observation(self):
        return host_observation(self.binding,reader=self.host_reader,read_birth=lambda:1001,
            verify_held=lambda:True,source_ruler=666)

    def offer(self,generation):
        # Caller already selected the exact real protocol stage. No run_model,
        # no synthetic change to c.node, no manually installed loaded receipt.
        node=self.binding.validate_context()['node']
        data=('explicit native Save double '+str(generation)).encode()*2100
        p=Profile();p.file.name=b'svdexccSC03.s14';p.file.slot=63;p.file.size=len(data)
        p.file.sha256[:]=bytes.fromhex(prior.sha(data))
        p.before=Date(*(self.c.node[k] for k in ('year','month','day')))
        p.loaded=Date(*(node[k] for k in ('year','month','day')))
        p.source=Identity(666,12,11);p.target=Identity(952,2,2);p.currentForce=12 if generation==1 else 2
        self.host_key=prior.sha(('A retained Save receipt double '+str(generation)).encode())
        reserved=self.binding.reserve(generation,f'mp{generation:08d}.s14',self.observation())
        self.artifacts[generation]=model_artifact(reserved.request,generation,data=data)
        package=self.binding.publish(generation,self.observation)
        return p,package

    def deliver(self,generation,p,package,mode='normal'):
        context=dict(scope=self.c.scope,manifest=package.manifest,checkpoint_id=package.checkpoint_id,
                     attachments=self.c.attachments.copy())
        return self.b.send(dict(op='run',profile=base64.b64encode(bytes(p)).decode(),context=context,
            bootstrap=generation==1,download=self.download,fingerprint=self.fp,
            directory=str(self.folder/f'received-{generation}'),mode=mode))

    def test_same_day_then_real_protocol_next_node(self):
        original=deepcopy(self.c.node);first_epoch=self.c.epoch
        self.c.begin_bootstrap();first=self.c.native_binding(123)
        self.assertEqual((first['generation'],first['period'],first['epoch'],first['node']),(1,1,123,original))
        with self.assertRaises(ValueError):self.c.seal_inputs()
        p,package=self.offer(1)
        self.assertEqual(package.manifest['node'],original)
        with self.assertRaises(ValueError):self.c.native_binding(123)
        with self.assertRaises(ValueError):self.binding.reserve(2,'mp00000002.s14',self.observation())
        r=self.deliver(1,p,package);self.assertTrue(r['ok'],r)
        self.assertEqual(r['journal']['status'],'COMPLETED')
        self.assertEqual((self.c.period,self.c.phase,self.c.node),(2,'PLANNING',original))
        self.assertTrue(self.c.bootstrap_completed);self.assertNotEqual(self.c.epoch,first_epoch)
        self.assertEqual(len(self.c.applied_receipts),1);self.assertFalse(self.c.ready)
        with self.assertRaises(ValueError):self.c.native_binding(123)
        for client in (self.a,self.b):
            self.assertTrue(client.request(dict(action='period_ready',epoch=self.c.epoch,ready=True))['ok'])
        permit=self.c.seal_inputs();self.c.begin_simulation(permit)
        second=self.c.native_binding(123)
        self.assertEqual((second['generation'],second['period'],second['epoch']),(2,2,124))
        self.assertNotEqual(first['input_digest'],second['input_digest'])
        self.assertEqual(self.c.node,original)
        old_ob=host_observation(self.binding,reader=self.host_reader,read_birth=lambda:1001,
            verify_held=lambda:True,source_ruler=666,expected_node=original)
        self.assertEqual(old_ob.day,11)
        with self.assertRaises(ValueError):
            host_observation(self.binding,reader=self.host_reader,read_birth=lambda:1001,
                verify_held=lambda:True,source_ruler=666,expected_node=next_node(next_node(original)))
        # External fake RAM observation of the completed turn, not a native
        # date writer or coordinator node mutation. No game is accessed.
        prior.put_date(self.host_reader,next_node(original))
        self.room._warm_ack={'explicit_fixture_previous_ack':True}
        p2,package2=self.offer(2)
        self.assertIsNone(self.room._warm_ack)
        r2=self.deliver(2,p2,package2)
        self.assertTrue(r2['ok'],r2);self.assertEqual(r2['loads'],2)
        self.assertEqual((self.c.period,self.c.phase,self.c.node),(3,'PLANNING',next_node(original)))
        self.assertEqual(len(self.c.applied_receipts),2)
        self.assertEqual(self.binding.status()['remaining_reservations'],0)
        saved=json.loads((self.folder/'received-1'/'remote-adapter-completion.json').read_text())
        self.assertTrue(self.b.request(packet(self.key,saved))['duplicate'])
        self.assertEqual(self.c.period,3)
        ROWS.append(dict(case=self._testMethodName,native_bindings=[first,second],loads=[r,r2],
                         trace=self.c.trace,final_node=self.c.node,first_node=original))

    def test_room_native_control_actual_tls_two_completions(self):
        control=native_control.RoomTurnControl()
        self.binding=BootstrapFreshSaveBinding(self.room,self.c,
            native_room_id=bytes.fromhex(digest(self.c.scope)),native_room_epoch=71,
            artifact_reader=control.copy_artifact,source_kind='FIXTURE_ONLY')
        self.c.begin_bootstrap()
        raw=wire.envelope(wire.Prepare,'Prepare',bytes([9])*32)
        raw.pid,raw.birth,raw.epoch=101,1001,123
        raw.year,raw.month,raw.day,raw.force,raw.ruler=203,8,11,12,666
        prep=native_control.prepare_from_room(raw,self.binding)
        owner=self;events=queue.Queue();ordered=[];submits=[];kept=[];answers=[];errors=[]
        class Channel:
            def submit(self,reservation):
                submits.append(reservation);ordered.append('submit-'+str(reservation.generation))
            def wait_artifact(self,generation,timeout):
                owner.host_key=prior.sha(('live-channel-double-'+str(generation)).encode())
                return model_artifact(submits[-1].request,generation,
                    data=('explicit owned native channel '+str(generation)).encode()*1800)
            def snapshot(self):return None
        channel=Channel();commands=[];polls=[]
        def call(op,value=None):
            if op=='RequestNext':
                self.assertTrue(self.c.bootstrap_completed)
                self.assertEqual(self.c.phase,'RUNNING')
                self.assertEqual(len(self.c.applied_receipts),1)
                self.assertFalse(commands);commands.append(value);ordered.append('request-next')
                return value,None
            self.assertEqual(op,'RepeatSnapshot');polls.append(op)
            q=repeat.envelope(repeat.Snapshot,op,bytes(prep.nonce));q.request=commands[0].request
            q.requested=q.hostThread=q.previousArtifactMatched=q.retiredSerial=q.retiredCount=1
            q.state=3 if len(polls)<3 else 4
            q.activeGeneration=1 if q.state==3 else 2
            q.drainPending=int(q.state==3);q.nativeDateMatched=int(q.state==4)
            if q.state==4:prior.put_date(self.host_reader,dict(year=203,month=8,day=21,phase='PLANNING_BOUNDARY'))
            return q,None
        def observe(node):
            return host_observation(self.binding,reader=self.host_reader,read_birth=lambda:1001,
                verify_held=lambda:True,source_ruler=666,expected_node=node)
        def run():
            try:
                answers.append(control.drive(channel,prep,['mp00000001.s14','mp00000002.s14'],call,
                    lambda *args:kept.append(args),lambda k,v:events.put((k,v)),self.binding,observe,wait_seconds=20))
            except BaseException as exc:errors.append(repr(exc))
            finally:events.put(('done',None))
        worker=threading.Thread(target=run);worker.start();replies=[]
        try:
            while True:
                kind,value=events.get(timeout=30)
                if kind=='done':break
                if kind.startswith('await-b-'):
                    generation=int(kind[-1]);package=self.room.artifacts;m=package.manifest
                    p=Profile();p.file.name=b'svdexccSC03.s14';p.file.slot=63
                    p.file.size=m['parts']['world.s14']['size'];p.file.sha256[:]=bytes.fromhex(m['parts']['world.s14']['sha256'])
                    p.before=Date(*(self.c.node[k] for k in ('year','month','day')))
                    p.loaded=Date(*(m['node'][k] for k in ('year','month','day')))
                    p.source=Identity(666,12,11);p.target=Identity(952,2,2);p.currentForce=12 if generation==1 else 2
                    reply=self.deliver(generation,p,package);replies.append(reply)
                    self.assertTrue(reply['ok'],reply);ordered.append('loaded-'+str(generation))
                elif kind=='await-room-turn':
                    for client in (self.a,self.b):
                        self.assertTrue(client.request(dict(action='period_ready',epoch=self.c.epoch,ready=True))['ok'])
                    permit=self.c.seal_inputs();self.c.begin_simulation(permit);ordered.append('sealed-turn')
        finally:
            worker.join(timeout=25)
        self.assertFalse(worker.is_alive());self.assertEqual(errors,[])
        self.assertEqual(ordered,['submit-1','loaded-1','sealed-turn','request-next','submit-2','loaded-2'])
        self.assertEqual(len(kept),2);self.assertEqual(len(commands),1)
        self.assertEqual(answers[0]['formal_completions'],2)
        self.assertEqual((self.c.period,self.c.node['day']),(3,21))
        self.assertEqual([q.request['day'] for q in submits],[11,21])
        self.assertEqual(bytes(commands[0].request.previousSha256).hex(),kept[0][2].sha256)
        ROWS.append(dict(case=self._testMethodName,result=answers[0],order=ordered,replies=replies,
                         a_pid=os.getpid(),b_pid=self.b.pid,submits=2,request_next=1))

    def test_wrong_initial_date_and_nonzero_prefix_refused(self):
        self.c.begin_bootstrap();ob=self.observation();d=next_node(self.c.node)
        wrong=LocalWorldObservation(ob.attachment,d['year'],d['month'],d['day'],ob.force,ob.ruler,
            ob.state_contract,ob.world_sha256,True)
        with self.assertRaises(ValueError):self.binding.reserve(1,'mp00000001.s14',wrong)
        self.assertFalse(self.artifacts);self.assertIsNone(self.c.manifest)
        c=BootstrapCoordinator(self.c.scope,world.CONTRACT,'d'*64,{'A':'a'*32,'B':'b'*32},self.c.node)
        for side in ('A','B'):c.applied_prefix(side,c.epoch,1,'e'*64,'d'*64,c.attachments[side])
        with self.assertRaises(ValueError):c.begin_bootstrap()
        self.assertEqual(c.phase,'PLANNING')
        ROWS.append(dict(case=self._testMethodName,offered=False,native_loads=0))

    def test_bad_target_completion_does_not_unlock_bootstrap(self):
        self.c.begin_bootstrap();p,package=self.offer(1);r=self.deliver(1,p,package,'drift')
        self.assertFalse(r['ok']);self.assertFalse(r['retry_succeeded'])
        self.assertEqual(r['loads'],1);self.assertEqual(self.c.phase,'HELD')
        self.assertFalse(self.c.bootstrap_completed);self.assertFalse(self.c.applied_receipts)
        self.assertEqual((self.c.period,self.c.node['day']),(1,11))
        with self.assertRaises(ValueError):self.c.native_binding(123)
        ROWS.append(dict(case=self._testMethodName,reply=r,phase=self.c.phase))

    def test_lost_reply_preserves_completed_intent_no_replay(self):
        self.c.begin_bootstrap();p,package=self.offer(1);r=self.deliver(1,p,package,'lost-reply')
        self.assertFalse(r['ok']);self.assertEqual(r['loads'],1);self.assertFalse(r['retry_succeeded'])
        self.assertEqual(r['journal']['status'],'COMPLETED')
        self.assertEqual((self.c.period,self.c.node['day']),(2,11));self.assertTrue(self.c.bootstrap_completed)
        self.assertFalse(self.c.ready)
        with self.assertRaises(ValueError):self.c.native_binding(123)
        ROWS.append(dict(case=self._testMethodName,reply=r,period=self.c.period))


def pins():
    paths={Path(m.__file__).resolve() for m in list(sys.modules.values()) if getattr(m,'__file__',None)}
    paths.add(Path(__file__).resolve())
    return {str(p):prior.sha(p.read_bytes()) for p in sorted(paths) if p.is_relative_to(ROOT) and p.suffix=='.py'}


if __name__=='__main__':
    OUTPUT=PRIVATE/'a_room_bootstrap_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    OUTPUT.mkdir(parents=True);transport.OUTPUT=OUTPUT;before=pins();stream=io.StringIO()
    run=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Cases))
    (OUTPUT/'test.log').write_text(stream.getvalue(),encoding='utf-8');sources=pins()
    stable=all(sources.get(k)==v for k,v in before.items())
    report=dict(result='PASS' if run.wasSuccessful() and run.testsRun==5 and stable else 'FAIL',tests=run.testsRun,
        sources=sources,inputs_unchanged=stable,cases=ROWS,actual_tls=True,independent_guest_process=True,
        native_save_load=False,fake_reader=True,fake_boundary=True,game_access=False,
        failures=[(str(t),detail) for t,detail in run.failures+run.errors])
    report['artifacts']={str(p):prior.sha(p.read_bytes()) for p in OUTPUT.rglob('*') if p.is_file()}
    (OUTPUT/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(OUTPUT/'result.json');print(stream.getvalue());raise SystemExit(0 if report['result']=='PASS' else 1)
