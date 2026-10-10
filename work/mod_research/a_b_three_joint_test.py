"""Joint A three control + B chain Session over actual TLS and signed receipts.
The actual observed-room successor preserves HMAC/Journal/loaded validation.
Native save/load/rules are doubles. A frozen finite sampler observes owned
RAM with an idle native Snapshot double; no third-generation ABI proof is claimed.
No completion is fabricated: B GuestCompletion reserves/completes actual journals,
then the unchanged observed HMAC/receipt/world checks call coordinator.loaded.
"""
from copy import deepcopy
from datetime import datetime
import hashlib,io,json,queue,secrets,sys,threading,unittest
from pathlib import Path
from unittest.mock import patch

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];PRIVATE=ROOT.parent/'mod_research'
sys.path[:0]=[str(PRIVATE/'python_deps'),str(ROOT/'outputs/san14-link')]
import b_observed_completion_test as prior
import b_observed_chain_completion_test as chain
import b_warm_room_test as transport
import a_observed_three_control as control_module
from a_observed_three_room import ObservedRoom,ObservedFreshSaveBinding
import a_room_three_protocol as three
import a_observed_room as frozen_observed
import a_save_runtime_contract as wire
import a_save_repeat_contract as repeat
from a_room_three_test import decode_modeled_artifact
from b_observed_chain_completion import GuestCompletion
from b_remote_chain_session import Session
from b_warm_profile_contract import Profile,Date,Identity
from human_rules_world_lifecycle import NextWorldRequest
from b_warm_room import receive_staged
from b_warm_bootstrap_protocol import receive_bootstrap_staged
from room_transport import Client
from authoritative_sync import digest,next_node,scope_from_room
from b_warm_remote_completion import key_check
from observed_completion_contract import packet
import b_warm_world as world

BootstrapFreshSaveBinding=ObservedFreshSaveBinding
ROWS=[]
def sha(raw):return hashlib.sha256(raw).hexdigest()

class Cases(unittest.TestCase):
    tearDown=chain.Cases.tearDown
    host_sample=chain.Cases.host_sample
    host_boundary=chain.Cases.host_boundary
    local=chain.Cases.local
    observation=prior.Cases.observation
    def setUp(self):
        with patch.object(prior,'BootstrapCoordinator',three.BootstrapCoordinator), \
             patch.object(prior,'ObservedRoom',ObservedRoom), \
             patch.object(prior,'BootstrapFreshSaveBinding',ObservedFreshSaveBinding):
            chain.Cases.setUp(self)

    def received(self,generation,package):
        m=package.manifest
        def connect(token):return Client('127.0.0.1',self.download,self.fp,
            dict(method='checkpoint_download',credential=token,profile=self.room.manifest['profile']))
        receive=receive_bootstrap_staged if generation==1 else receive_staged
        r=receive(self.b,connect,checkpoint_id=package.checkpoint_id,scope=self.c.scope,epoch=self.c.epoch,
            period=self.c.period,cut=m['cut'],attachments=self.c.attachments,directory=self.folder/f'received-{generation}')
        p=Profile();p.file.name=b'svdexccSC03.s14';p.file.slot=63;p.file.size=m['parts']['world.s14']['size']
        p.file.sha256[:]=bytes.fromhex(m['parts']['world.s14']['sha256'])
        p.before=Date(*(self.c.node[k] for k in ('year','month','day')))
        p.loaded=Date(*(m['node'][k] for k in ('year','month','day')))
        p.source=Identity(666,12,11);p.target=Identity(952,2,2);p.currentForce=12 if generation==1 else 2
        q=NextWorldRequest(generation+1,package.checkpoint_id,bytes([0x70+generation])*16,
            m['node']['year'],m['node']['month'],m['node']['day'])
        self.warm.request=q
        if self.session is None:self.local(p)
        return r,q,p

    def test_direct_predecessor_type_and_snapshot_gaps_are_real(self):
        with self.assertRaisesRegex(ValueError,'Exact same-day'):
            frozen_observed.ObservedProjection(self.c,host_sampler=self.host_sample,
                host_boundary=self.host_boundary,source_kind='FIXTURE_ONLY')
        with self.assertRaisesRegex(ValueError,'Trusted coordinator'):
            frozen_observed.ObservedRoom(transport.manifest()).bind_coordinator(self.c)
        s=self.host_fixture.runtime;s.mailboxCount=3;s.saveGeneration=3;s.saveStatus=5
        with self.assertRaisesRegex(ValueError,'mailbox'):self.host_fixture.provider.observe(self.c.node)
        self.assertFalse(self.c.applied_receipts)

    def test_actual_three_control_chain_session_signed_completions(self):
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
                return decode_modeled_artifact(submits[-1].request,generation,data=('owned native Save '+str(generation)).encode()*2100)
            def snapshot(self):return None
        def call(op,value=None):
            if op=='RequestNext':
                self.assertTrue(self.c.bootstrap_completed);self.assertEqual(self.c.phase,'RUNNING')
                self.assertEqual(len(self.c.applied_receipts),len(commands)+1);polls.clear()
                commands.append(value);order.append('request-next');return value,None
            self.assertEqual(op,'RepeatSnapshot');polls.append(op)
            q=repeat.envelope(repeat.Snapshot,op,bytes(prep.nonce));q.request=commands[-1].request
            q.hostThread=q.previousArtifactMatched=1
            q.retiredSerial=q.retiredCount=len(commands)
            q.state=3 if len(polls)<3 else 4;q.activeGeneration=len(commands) if q.state==3 else len(commands)+1
            q.requested=int(q.state==3)
            q.drainPending=int(q.state==3);q.nativeDateMatched=int(q.state==4)
            if q.state==4:prior.put_date(self.host,next_node(self.c.node))
            return q,None
        def drive():
            try:
                answers.append(control.drive(Channel(),prep,['mp00000001.s14','mp00000002.s14','mp00000003.s14'],call,
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
        self.assertEqual(order,['submit-1','loaded-1','sealed-turn','request-next','submit-2','loaded-2','sealed-turn','request-next','submit-3','loaded-3'])
        self.assertEqual((self.c.period,self.c.node['month'],self.c.node['day']),(4,9,1));self.assertEqual(len(self.session.sessions),3)
        self.assertEqual(len(self.session.lifecycle.retained),4);self.assertEqual(len(self.adapter.history),3)
        self.assertEqual(self.adapter.phase,'THREE_COMPLETIONS_RETAINED');self.assertEqual(len(kept),3)
        self.assertTrue(all(j['status']=='COMPLETED' for j in journals));self.assertIsNone(self.room._warm_ack)
        saved=json.loads((self.folder/'received-1'/'observed-adapter-completion.json').read_text())
        duplicate=self.b.request(packet(self.key,saved));self.assertTrue(duplicate['duplicate']);self.assertEqual(self.c.period,4)
        ROWS.append(dict(case=self._testMethodName,order=order,replies=replies,journals=journals,
            warm=self.warm.events,rules=self.rules.events,control=answers[0],same_day_bootstrap=True,
            formal_completions=3,strong_boolean_adapter_used=False))


if __name__=='__main__':
    runpath=PRIVATE/'a_b_three_joint_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');runpath.mkdir(parents=True)
    transport.OUTPUT=runpath;before=chain.pins();before[str(Path(__file__).resolve())]=sha(Path(__file__).read_bytes())
    log=io.StringIO();run=unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Cases))
    (runpath/'test.log').write_text(log.getvalue(),encoding='utf-8')
    after=chain.pins();after[str(Path(__file__).resolve())]=sha(Path(__file__).read_bytes())
    report=dict(result='PASS' if run.wasSuccessful() and before==after else 'FAIL',tests=run.testsRun,
        sources=after,inputs_unchanged=before==after,cases=ROWS,actual_tls=True,actual_b_chain_session=True,
        actual_signed_formal_completion=True,actual_a_three_control=True,actual_journal=True,
        fixture_observed_room_type_wiring=False,native_save_load_rules_snapshot_doubles=True,
        production_observed_room_three_wiring=True,three_native_snapshot_abi=False,
        game_access=False,native_gameplay_enabled=False,full_world_verified=False,
        failures=[(str(t),d) for t,d in run.failures+run.errors])
    report['artifacts']={str(p):sha(p.read_bytes()) for p in runpath.rglob('*') if p.is_file()}
    (runpath/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(log.getvalue());print(runpath/'result.json');raise SystemExit(report['result']!='PASS')
