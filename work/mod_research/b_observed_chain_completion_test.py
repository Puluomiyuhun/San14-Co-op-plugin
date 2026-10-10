"""Actual TLS/journals and three B loads; native load/rules/host export are doubles.

Uses original finite planning samplers, actual signed completion and attachment
rotation. Direct owned checkpoint publication deliberately does not claim an A
three-save deployment. Session.open is never patched or called with fake proof.
"""
from copy import deepcopy
from datetime import datetime
import hashlib
import io
import json
from pathlib import Path
import sys
import threading
import unittest

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];PRIVATE=ROOT.parent/'mod_research'
sys.path[:0]=[str(PRIVATE/'python_deps'),str(ROOT/'outputs/san14-link')]
import b_observed_completion_test as prior
import b_warm_room_test as transport
import b_remote_chain_session as session_module
from b_remote_chain_session import Session,REQUIRED_SOURCES
from b_remote_chain_lifecycle import DiagnosticLifecycle,DiagnosticBridge
from b_remote_session_boundary import DiagnosticBoundary
from b_observed_chain_completion import GuestCompletion
from b_warm_profile_contract import Profile,Date,Identity
from b_warm_room import receive_staged
from b_warm_bootstrap_protocol import receive_bootstrap_staged
from b_warm_adapter_key import load_key
from b_warm_staging import Refused
from human_rules_world_lifecycle import NextWorldRequest
from authoritative_sync import CheckpointPackage,canonical,next_node
from room_transport import Client
from observed_completion_contract import ACTION,unpack,packet

OUTPUT=None;ROWS=[]
def sha(raw):return hashlib.sha256(raw).hexdigest()
def pins():
    paths={Path(m.__file__).resolve() for m in list(sys.modules.values()) if getattr(m,'__file__',None)}
    paths.update(HERE/n for n in REQUIRED_SOURCES);paths.add(Path(__file__).resolve())
    return {str(p):sha(p.read_bytes()) for p in sorted(paths) if p.is_relative_to(ROOT) and p.suffix=='.py'}

class Cases(unittest.TestCase):
    tearDown=prior.Cases.tearDown
    host_sample=prior.Cases.host_sample
    host_boundary=prior.Cases.host_boundary

    def setUp(self):
        prior.Cases.setUp(self)
        self.warm.authorize_next=self.warm.authorize_second
        old_config=self.rules.config
        def config(*args):
            value=old_config(*args)
            # Owned native business substitute, including month rollover.
            if self.warm.request:
                value.year,value.month,value.day=(getattr(self.warm.request,k) for k in ('year','month','day'))
            return value
        self.rules.config=config

    def local(self,p):
        boundary=DiagnosticBoundary(self.guest,p,pid=self.guest.pid,birth=self.birth,no_new_commands=True)
        boundary.observe();life=DiagnosticLifecycle(self.life.current,boundary)
        bridge=DiagnosticBridge(life,self.warm,target=self.target,records=self.records)
        s=Session.__new__(Session) # owned fixture only; no production factory bypass claim
        s.reader=self.guest;s.control=self.b;s._control_owner=self.b;s._key=load_key(self.private_key)
        s.boundary=boundary;s.records=self.folder;s.scope=deepcopy(self.c.scope);s.phase='ACTIVE'
        s.sessions=[];s._lock=threading.RLock();s.source_pins=pins()
        s.native_identity=(self.rules.pid,self.rules.birth);s.read_birth=lambda:self.birth
        s.warm=self.warm;s.factory=None;s.lifecycle=life;s.bridge=bridge
        s.observe_loaded=self.rules.observe;s.prepare_rules=self.rules.prepare
        s._owners=(s.reader,s.control,s.warm,s.lifecycle,s.bridge,s.boundary,s.factory)
        s._scope_bytes=canonical(s.scope);self.session=s;self.adapter=GuestCompletion(s)

    def offer(self,n):
        if n==1:
            self.c.begin_bootstrap();node=deepcopy(self.c.node)
        else:
            for client in (self.a,self.b):
                self.assertTrue(client.request(dict(action='period_ready',epoch=self.c.epoch,ready=True))['ok'])
            permit=self.c.seal_inputs();self.c.begin_simulation(permit);node=next_node(self.c.node)
        prior.put_date(self.host,node)
        observed=self.host_fixture.provider.world_observation(node,self.c.attachments['A'])
        cut={k:self.c.seal[k] for k in ('sequence','prefix_sha256')}
        raw=('OWNED CHECKPOINT PUBLICATION '+str(n)).encode()*2048
        package=CheckpointPackage(self.c.scope,self.c.epoch,self.c.period,cut,node,self.c.state_contract,
            observed.world_sha256,{'world.s14':raw,'adapter.json':canonical(dict(source_kind='FIXTURE_ONLY',native_save_executed=False))},source_player='A')
        self.c.offer_checkpoint('A',package.manifest);self.room.install_offered_checkpoint(self.c,package)
        self.host_key=sha(('owned host receipt '+str(n)).encode())
        def connect(token):return Client('127.0.0.1',self.download,self.fp,
            dict(method='checkpoint_download',credential=token,profile=self.room.manifest['profile']))
        receive=receive_bootstrap_staged if n==1 else receive_staged
        r=receive(self.b,connect,checkpoint_id=package.checkpoint_id,scope=self.c.scope,epoch=self.c.epoch,
            period=self.c.period,cut=cut,attachments=self.c.attachments,directory=self.folder/f'received-{n}')
        p=Profile();p.file.name=b'svdexccSC03.s14';p.file.slot=63;p.file.size=len(raw);p.file.sha256[:]=bytes.fromhex(sha(raw))
        p.before=Date(*(self.c.node[k] for k in ('year','month','day')))
        p.loaded=Date(*(node[k] for k in ('year','month','day')))
        p.source=Identity(666,12,11);p.target=Identity(952,2,2);p.currentForce=12 if n==1 else 2
        q=NextWorldRequest(n+1,package.checkpoint_id,bytes([0x70+n])*16,node['year'],node['month'],node['day'])
        self.warm.request=q
        if self.session is None:self.local(p)
        return r,q,p

    def two(self):
        for n in (1,2):
            r,q,p=self.offer(n);self.adapter.apply(r,q,p)
        self.assertEqual((self.session.phase,self.adapter.phase),('ACTIVE','ACTIVE'))

    def test_three_actual_tls_loads_rollover_and_fourth_refused(self):
        rows=[];identity=None
        for n in (1,2,3):
            r,q,p=self.offer(n)
            graph=tuple(map(id,(self.session,self.adapter,self.session.warm,self.session.lifecycle,self.session.bridge)))
            if identity is None:identity=graph
            self.assertEqual(identity,graph)
            old_attachment=self.c.attachments['B'];result=self.adapter.apply(r,q,p)
            self.assertNotEqual(old_attachment,self.c.attachments['B'])
            self.assertEqual(self.adapter.attachments,self.c.attachments)
            self.assertEqual(r.journal.status()['status'],'COMPLETED')
            self.assertEqual(len(self.session.lifecycle.retained),n+1)
            self.assertEqual(self.c.period,n+1);self.assertFalse(self.c.ready)
            rows.append(dict(date=self.c.node,result=result,journal=r.journal.status()))
        self.assertEqual(self.c.node,dict(year=203,month=9,day=1,phase='PLANNING_BOUNDARY'))
        self.assertEqual(self.session.phase,'THREE_LOADS_RETAINED')
        self.assertEqual(self.adapter.phase,'THREE_COMPLETIONS_RETAINED')
        events=list(self.warm.events)
        with self.assertRaisesRegex(ValueError,'consumed'):self.adapter.apply(r,q,p)
        self.assertEqual(self.warm.events,events)
        self.assertEqual([e[1] for e in events if e[0]=='open'],[0,1,2])
        self.assertEqual([e[1] for e in events if e[0]=='handover'],[1,2])
        body=json.loads((r.directory/'observed-adapter-completion.json').read_text())
        duplicate=self.b.request(packet(self.key,body));self.assertTrue(duplicate['duplicate'])
        self.assertEqual(self.c.period,4)
        ROWS.append(dict(case=self._testMethodName,rows=rows,warm=events,rules=self.rules.events))

    def test_third_native_failure_retains_intent_and_no_retry(self):
        self.two();r,q,p=self.offer(3);self.warm.case='load-failed'
        with self.assertRaisesRegex(RuntimeError,'Explicit load failure'):self.adapter.apply(r,q,p)
        self.assertEqual(r.journal.status()['status'],'INTENT')
        self.assertEqual(self.c.period,3);self.assertEqual(self.session.phase,'TERMINAL')
        self.assertEqual(len(self.session.sessions),2);self.assertTrue(self.warm.abort_lease)
        events=list(self.warm.events)
        with self.assertRaises(Exception):self.adapter.apply(r,q,p)
        self.assertEqual(events,self.warm.events)

    def test_third_lost_complete_reply_does_not_reload(self):
        self.two();r,q,p=self.offer(3);request=self.b.request
        def lose(value):
            result=request(value)
            if value.get('action')==ACTION and unpack(self.key,value)['kind']=='complete':raise EOFError('Owned third reply lost')
            return result
        self.b.request=lose
        with self.assertRaisesRegex(EOFError,'third reply'):self.adapter.apply(r,q,p)
        self.b.request=request
        self.assertEqual(r.journal.status()['status'],'COMPLETED');self.assertEqual(self.c.period,4)
        self.assertEqual(len(self.session.sessions),3);self.assertEqual(len(self.adapter.history),2)
        self.assertEqual(self.adapter.phase,'TERMINAL');events=list(self.warm.events)
        with self.assertRaises(Exception):self.adapter.apply(r,q,p)
        self.assertEqual(events,self.warm.events)

    def test_changed_third_target_refuses_before_open(self):
        self.two();r,q,p=self.offer(3);events=list(self.warm.events)
        self.target.write_bytes(b'foreign target bytes')
        with self.assertRaisesRegex(Refused,'target identity changed'):self.adapter.apply(r,q,p)
        self.assertEqual(events,self.warm.events);self.assertEqual(r.journal.status()['status'],'INTENT')

    def test_third_pending_input_refuses_before_remote_begin(self):
        self.two();r,q,p=self.offer(3);events=list(self.warm.events)
        self.plan_memory.memory.put(self.plan_memory.states[4]+0x660,1,'<I')
        with self.assertRaisesRegex(ValueError,'Pending input'):self.adapter.apply(r,q,p)
        self.assertEqual(events,self.warm.events);self.assertIsNone(self.c.load_intent)
        self.assertEqual(r.journal.status()['status'],'STAGED')

    def test_second_adapter_reconstruction_and_old_session_rejected(self):
        self.two()
        with self.assertRaises(ValueError):GuestCompletion(self.session)
        from b_observed_completion import GuestCompletion as OldGuest
        with self.assertRaises(ValueError):OldGuest(self.session)

if __name__=='__main__':
    OUTPUT=PRIVATE/'b_observed_chain_completion_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');OUTPUT.mkdir(parents=True)
    transport.OUTPUT=OUTPUT;before=pins();stream=io.StringIO()
    run=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Cases))
    (OUTPUT/'test.log').write_text(stream.getvalue(),encoding='utf-8');sources=pins()
    report=dict(result='PASS' if run.wasSuccessful() and before==sources else 'FAIL',tests=run.testsRun,
        inputs_unchanged=before==sources,sources=sources,cases=ROWS,actual_tls=True,actual_journal=True,
        actual_b_session=True,actual_planning_sampler=True,actual_signed_formal_completion=True,
        owned_native_load_rule_and_host_publication_doubles=True,production_factory_executed=False,
        game_access=False,native_gameplay_enabled=False,full_world_verified=False,ready_authorized=False,
        failures=[(str(t),d) for t,d in run.errors+run.failures])
    report['artifacts']={str(p):sha(p.read_bytes()) for p in OUTPUT.rglob('*') if p.is_file()}
    (OUTPUT/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(OUTPUT/'result.json');print(stream.getvalue());raise SystemExit(0 if report['result']=='PASS' else 1)
