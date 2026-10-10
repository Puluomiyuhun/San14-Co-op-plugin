"""Owned RAM/native-business doubles; actual B Runner/Session/TLS/reward cut.

Both native load and reward business are explicit environment doubles. The same
actual GameReader and byte layout feed B's formal load projection and reward
CheckedPort. No game, Steam, UI, native installer or full-world claim.
"""
from copy import deepcopy
from datetime import datetime
import hashlib, io, json, secrets, struct, sys, threading, time, unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];PRIVATE=ROOT.parent/'mod_research'
sys.path[:0]=[str(PRIVATE/'python_deps'),str(ROOT/'outputs/san14-link')]
import b_observed_start_test as predecessor
import b_observed_start as old
import b_warm_refresh_remote_owner_test as memory_load
import a_reward_runtime_mount as mounting
from a_reward_runtime_mount_test import OwnedPlanningScheduler,prepared
from a_reward_runtime_entry_test import Cases as HostLayout
from reward_checkpoint_fixture import World
from reward_observed_context import ContextSampler,CheckedPort
from reward_room_flow import envelope
from b_warm_adapter_key import Native
from b_warm_profile_capture import SLOTS
from authoritative_sync import next_node
from checkpoint_fresh_save_binding_test import model_artifact
import reward_planning_discovery as discovery_module
import reward_checkpoint_observer,reward_checkpoint_shared_cut

OUTPUT=None;ROWS=[]


class OwnedRewardOwner:
    """Substitute only NativePort.open/Owner; CheckedPort/Journal run unchanged."""
    def __init__(self,case,*,session,guest,profile,scope,records,build):
        self.case=case;self.world=case.b_world;self.session=session;self.guest=guest;self.events=case.owner_events
        case.assertIs(session.reader,self.world.reader)
        case.assertEqual(len(session.sessions),1);case.assertEqual(len(guest.history),1)
        self.unknown=False;self.released=False;self.stopped=False;self.db=None
        self.epoch=scope['timeline_epoch'];self.attachment=guest.attachments['B']
        self.binding=(session.reader.pid,case.birth,self.epoch,self.attachment)
        self.sampler=ContextSampler(session.reader,pid=self.binding[0],birth=self.binding[1],
            epoch=self.epoch,attachment_id=self.attachment,current_binding=lambda:(self.epoch,self.attachment),
            node={k:case.c.node[k] for k in ('year','month','day')},viewer=2,
            players={12:dict(ruler=666,district=11),2:dict(ruler=952,district=2)},read_birth=lambda:case.birth)
        self.checked_port=CheckedPort(self.sampler,self)
        self.slot=self.world.memory.base+0x12CC4D0;self.original=self.world.memory.base+0x3F9B00
        case.assertEqual(int.from_bytes(self.world.memory.read(self.slot,8),'little'),self.original)
        self.world.memory.pack(self.slot,'<Q',0x780001000)
        self.events.append('owner-open-after-first-formal');case.owner=self
    def identity(self):return self.binding
    def attach_journal(self,db):self.db=db;self.events.append('journal-attached')
    def execute(self,command):
        self.case.assertFalse(self.stopped);self.case.assertIsNotNone(self.db)
        self.events.append('reward-execute')
        result=self.world.execute(command)
        if self.case.fault=='reward-unknown':
            self.unknown=True
            raise mounting.RemoteCallUnknown('owned B reward result lost after writes',{'may_have_started':True})
        return result
    def stop_restore(self):
        self.events.append('owner-stop-restore')
        if self.unknown:raise RuntimeError('Unknown reward owner cannot restore')
        self.case.assertEqual(self.db.status()['phase'],'IDLE')
        self.case.assertFalse(self.db.status()['unknown_sequences'])
        self.case.assertEqual(self.case.mount.gate.receipt['cut']['sequence'],1)
        self.case.assertEqual(self.world.calls,1)
        self.stopped=True
        if self.case.fault=='restore-unknown':
            self.unknown=True
            raise mounting.RemoteCallUnknown('owned B restore return lost',{'may_have_started':True})
        if self.case.fault=='restore-incomplete':return dict(restored=False,native_clean=False)
        self.world.memory.pack(self.slot,'<Q',self.original);self.released=True
        return dict(restored=True,native_clean=True)
    def verify_restored(self):
        self.events.append('owner-readback')
        if self.unknown or not self.released or int.from_bytes(self.world.memory.read(self.slot,8),'little')!=self.original:
            raise RuntimeError('Owned B User slot not restored')
        return dict(restored=True,native_clean=True)


class Cases(predecessor.Cases):
    def setUp(self):
        super().setUp()
        self.a_world=World(12);self.b_world=World(12)
        HostLayout._unified_host(self)
        import a_observed_boundary as boundary
        f=self.host_fixture
        f.provider=boundary.AObservedBoundary(f.reader,pid=f.reader.pid,birth=f.birth,base=f.reader.memory.base,
            root=f.reader.root,world_address=f.reader.world,cache=f.cache,force=12,ruler=666,
            nonce=f.nonce,plans=f.plans,read_birth=lambda:f.birth,runtime_snapshot=f.snapshot,no_new_commands=True)
        self.b_world.reader.pid=self.rules.pid;self.b_world.birth=self.birth
        self.guest=self.b_world.reader
        self._sync_owned(self.guest,self.rules.current)
        self.warm=memory_load.WarmMemory(self.rules,self.target,'success',self.guest)
        self.warm.calls=SimpleNamespace(uncertain=False)
        self.config['local']['pid']=self.guest.pid
        self.owner_events=[];self.owner=None;self.fault=None;self.runner_events=[]
        self.report_key=secrets.token_bytes(32);self.cut_key=secrets.token_bytes(32)
        self.report_path=self.folder/'reward-report.key';self.cut_path=self.folder/'reward-cut.key'
        Native().write_new(self.report_path,self.report_key);Native().write_new(self.cut_path,self.cut_key)
        self.mount=mounting.RuntimeMount(self.service,reward_key=self.report_key,guest_cut_key=self.cut_key,
            records=self.folder/'actual-host-mount',wait_seconds=3)
        self.scheduler=OwnedPlanningScheduler(self.a_world)
        self.prep=prepared(self.a_world);self.shared=mounting.SharedCallState(threading.RLock(),lambda e:None)
        self.scheduler.shared=self.shared
        entry=SimpleNamespace(room=self.room,coordinator=self.c,provider=SimpleNamespace(reader=self.host),
            prep=self.prep,hold=lambda e:self.order.append('host-held'),protection=SimpleNamespace(verify=lambda:None))
        dll=self.folder/'owned-A.dll';dll.write_bytes(b'Owned A reward wire transport double')
        with patch.object(mounting,'MountTransport',return_value=self.scheduler):
            self.mount.bind_native(entry,SimpleNamespace(reader=self.host),123,dll,self.prep,
                SimpleNamespace(module=123,nonce=self.prep.nonce),self.shared,lambda:self.a_world.birth)
        discovery_module.install(self.service,self.mount)
        self.sync_patch=patch.object(memory_load,'sync_reader',side_effect=self._sync_owned);self.sync_patch.start()
        self.addCleanup(self.sync_patch.stop)
        self.addCleanup(self.scheduler.close)

    def _sync_owned(self,reader,c):
        self.assertIs(reader,self.b_world.reader);w=self.b_world;m=w.memory
        if c.root!=w.root:
            raw=m.read(w.root,0x86000);m.reserve(c.root,len(raw));m.put(c.root,raw)
            w.root=c.root;w.types[c.root]='CSan14Data'
        if c.world!=w.world:
            raw=m.read(w.world,0x2000);m.reserve(c.world,len(raw));m.put(c.world,raw)
            w.world=c.world;w.types[c.world]='CWorldData'
        reader.root=w.root;reader.world=w.world
        m.pack(m.base+0x1FCA1E0,'<Q',w.root);m.pack(w.root+0x85130,'<Q',w.world)
        m.pack(w.world+0x34,'<HBB4B',c.year,c.month,c.day,0,0,c.viewer,0)
        w.viewer=c.viewer
        for slot,target in SLOTS:m.pack(m.base+slot,'<Q',m.base+target)

    def open_owned(self,runner,context,profile,pins):
        super().open_owned(runner,context,profile,pins)
        apply=self.session.apply_native
        def checked_apply(received,request,p,**kw):
            if request.generation==3:
                self.assertIsNotNone(self.owner);self.assertTrue(self.owner.released)
                self.owner.verify_restored();self.owner_events.append('second-native-load')
            return apply(received,request,p,**kw)
        self.session.apply_native=checked_apply

    def advance_reward_host(self):
        try:
            while self.c.period<2:
                if self.stop.wait(.01):return
            self.mount.open(self.artifacts[1],self.room.artifacts,self.prep)
            while self.c.phase!='RUNNING':
                if self.stop.wait(.01):return
                self.mount.poll()
            self.assertEqual(self.c.seal['sequence'],1)
            self.mount.validate_seal(self.c.seal);self.mount.observe_sealed(self.c.node)
            self.host_fixture.complete_and_rebuild()
            r=self.binding.reserve(2,'mp00000002.s14',self.observation(next_node(self.c.node)))
            self.artifacts[2]=model_artifact(r.request,2,data=b'owned reward second Save'*1600)
            self.complete_host(2);self.binding.publish(2,lambda:self.observation(next_node(self.c.node)))
            while self.service.guest_finished is None:
                if self.stop.wait(.01):return
            if self.service.guest_finished['native_cleanup_verified']:self.service.mark_host_finished()
        except BaseException as exc:
            # A observes B terminal/disconnect in negative cases; never reopens.
            if self.fault is None:self.thread_errors.append(repr(exc))
            else:self.order.append('host-terminal:'+type(exc).__name__)

    def on_event(self,name,runner):
        self.runner_events.append(name)
        if name=='reward-planning-open':
            runner.submit(2,[101]);runner.finish_input()
            reply=self.a.request(dict(action='reward_cut_prepare',epoch=self.c.epoch))
            self.assertTrue(reply['ok'],repr(reply)+' host errors='+repr(self.thread_errors))

    def execute(self):
        import b_reward_runner as start
        import b_reward_native_port as native_port
        self.runner=start.Runner(self.config,self.link,native_build={'owned_business_double':True},
            report_key_path=self.report_path,cut_key_path=self.cut_path,on_event=self.on_event)
        def open_native(**kw):
            env=OwnedRewardOwner(self,**kw)
            native=native_port.NativePort.__new__(native_port.NativePort)
            native.session,native.guest,native.checked_port=env.session,env.guest,env.checked_port
            for name in ('attach_journal','stop_restore','verify_restored'):setattr(native,name,getattr(env,name))
            return native
        with patch.object(start,'preflight',return_value=self.checked), \
             patch.object(native_port,'approved_build',return_value={'owned_approval_double':True}), \
             patch.object(old.Runner,'_open',side_effect=lambda c,p,pins:self.open_owned(self.runner,c,p,pins)), \
             patch.object(old,'require_original_rules',side_effect=self.original_rules), \
             patch.object(old,'require_no_debugger',side_effect=lambda _:self.order.append('no-debugger-double')), \
             patch.object(native_port.NativePort,'open',side_effect=open_native):
            return self.runner.run()

    def begin(self):
        self.offer_first();self.host_thread=threading.Thread(target=self.advance_reward_host);self.host_thread.start()

    def evidence(self,**extra):
        ROWS.append(dict(case=self._testMethodName,events=self.runner_events,owner_events=self.owner_events,
            warm=self.warm.events,cleanup=self.runner.cleanup,host_state=self.c.phase,
            owned_reward_business_calls=dict(A=self.a_world.calls,B=self.b_world.calls),**extra))

    def test_command_cut_then_restore_before_second_load(self):
        self.begin();result=self.execute();self.assertFalse(self.thread_errors,self.thread_errors)
        self.assertEqual(len(self.runner.guest.history),2);self.assertEqual(self.a_world.calls,1);self.assertEqual(self.b_world.calls,1)
        self.assertTrue(result['cleanup']['native_cleanup_verified'])
        self.assertLess(self.owner_events.index('owner-stop-restore'),self.owner_events.index('second-native-load'))
        self.assertEqual(self.mount.gate.receipt['cut']['sequence'],1)
        with self.assertRaises(Exception):self.runner.submit(2,[101])
        with self.assertRaises(Exception):self.runner.reward.replica.port.observe()
        self.assertEqual(self.b_world.calls,1)
        self.evidence(result=result,cut=self.mount.gate.receipt['cut'])

    def test_reward_unknown_retains_owner_and_forbids_second_load(self):
        self.fault='reward-unknown';self.begin()
        with self.assertRaises(Exception):self.execute()
        self.assertEqual(len(self.runner.guest.history),1);self.assertEqual(self.b_world.calls,1)
        self.assertEqual(len([e for e in self.warm.events if e[0]=='load']),1)
        self.assertNotIn('owner-stop-restore',self.owner_events);self.assertNotIn('second-native-load',self.owner_events)
        self.assertTrue(self.runner.cleanup['retained_native_state']);self.assertFalse(self.runner.cleanup['native_cleanup_verified'])
        self.evidence()

    def test_incomplete_restore_forbids_second_load(self):
        self.fault='restore-incomplete';self.begin()
        with self.assertRaises(Exception):self.execute()
        self.assertEqual(len(self.runner.guest.history),1)
        self.assertEqual(len([e for e in self.warm.events if e[0]=='load']),1)
        self.assertIn('owner-stop-restore',self.owner_events);self.assertNotIn('second-native-load',self.owner_events)
        self.assertFalse(self.owner.released);self.assertTrue(self.runner.cleanup['retained_native_state'])
        self.evidence()

    def test_unknown_restore_retains_and_forbids_second_load(self):
        self.fault='restore-unknown';self.begin()
        with self.assertRaises(Exception):self.execute()
        self.assertEqual(len(self.runner.guest.history),1);self.assertTrue(self.owner.unknown)
        self.assertEqual(self.owner_events.count('owner-stop-restore'),1)
        self.assertNotIn('second-native-load',self.owner_events);self.assertTrue(self.runner.cleanup['retained_native_state'])
        self.evidence()


def pins():
    paths={Path(m.__file__).resolve() for m in list(sys.modules.values()) if getattr(m,'__file__',None)}
    return {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths) if p.is_relative_to(ROOT) and p.suffix=='.py'}

if __name__=='__main__':
    import b_reward_runner,b_reward_session,b_reward_native_port
    OUTPUT=PRIVATE/'b_reward_runner_test_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');OUTPUT.mkdir(parents=True)
    predecessor.fixture.transport.OUTPUT=OUTPUT
    before=pins();stream=io.StringIO()
    suite=unittest.TestSuite(Cases(n) for n in Cases.__dict__ if n.startswith('test_'))
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite);after=pins()
    (OUTPUT/'test.log').write_text(stream.getvalue(),encoding='utf-8')
    report=dict(result='PASS' if result.wasSuccessful() and before==after else 'FAIL',tests=result.testsRun,sources=after,
        sources_unchanged=before==after,cases=ROWS,game_access=False,steam_access=False,
        actual_runner_session_TLS_reward_journal_and_shared_cut=True,same_GameReader_reward_and_world=True,
        native_owner_installation_executed=False,native_load_reward_business_RAM_RTTI_doubles=True,
        full_world_verified=False,input_exclusion_proven=False,production_Session_open_executed=False,
        failures=[(str(t),s) for t,s in result.failures+result.errors])
    report['artifacts']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in OUTPUT.rglob('*') if p.is_file()}
    (OUTPUT/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(OUTPUT/'result.json');print(stream.getvalue());raise SystemExit(report['result']!='PASS')
