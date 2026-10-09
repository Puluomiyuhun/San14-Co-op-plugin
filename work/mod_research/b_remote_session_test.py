"""TLS/SQLite + real lifecycle predicates; explicit native RAM/publication doubles.

The old formal adapter's verify_held=True is ONLY an outer fixture advancing A
between offers. The new production Session never consumes that boolean, sends
formal completion, or claims a fence. Its sampler executes the unchanged native
planning algorithm against an owned RAM layout on every observation.
"""
from datetime import datetime
from dataclasses import asdict
import hashlib
import io
import json
from pathlib import Path
import sys
import threading
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[1]; PRIVATE=ROOT.parent/'mod_research'
sys.path[:0]=[str(PRIVATE/'python_deps'),str(ROOT/'outputs/san14-link')]
import b_warm_refresh_remote_owner_test as fixture
import b_warm_room_test as transport
import b_warm_world as world
import b_warm_stable_capture as stable
import b_warm_profile_capture as original
import b_warm_stable_refresh_coordinator
import b_warm_pair_diagnostic
import game_reader
import b_remote_session as session_module
from b_warm_profile_capture_test import Reader as PlanningReader
from b_warm_profile_contract import Profile
from b_warm_remote_completion import RemoteGuestCompletion
from b_warm_adapter_key import Native,load_key
from b_remote_session import Session,REQUIRED_SOURCES,verify_sources
import b_remote_session_boundary as boundary_module
from b_remote_session_boundary import DiagnosticBoundary
from b_remote_session_lifecycle import DiagnosticLifecycle,DiagnosticBridge

OUTPUT=None; EVIDENCE=[]; FROZEN_CAPTURE=original.capture_planning


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def source_pins():
    paths={Path(m.__file__).resolve() for m in list(sys.modules.values()) if getattr(m,'__file__',None)}
    paths.update(HERE/n for n in REQUIRED_SOURCES);paths.add(Path(__file__).resolve())
    return {str(p):sha(p) for p in sorted(paths) if p.is_relative_to(ROOT) and p.suffix=='.py'}


class Cases(fixture.Cases):
    def setUp(self):
        super().setUp()
        self.private_key=self.folder/'adapter.key';Native().write_new(self.private_key,self.key)
        self.plan_memory=PlanningReader();self.plan_memory.pid=self.guest.pid
        self.plan_memory.birth=self.birth
        def capture(reader,p,ruler,**kw):
            # Explicit planning-memory fixture + real world date/viewer memory.
            fake=self.plan_memory;fake.profile=Profile.from_buffer_copy(bytes(p));fake.ruler=ruler
            def inner(r,profile,expected_ruler):
                return FROZEN_CAPTURE(r,profile,expected_ruler,
                    context_reader=lambda _:dict(snapshot=reader.snapshot()),
                    birth_reader=lambda _:self.birth,range_check=lambda r,a,n:r.memory.span(a,n))
            with patch.object(original,'capture_planning',side_effect=inner):
                return stable.capture_planning(fake,p,ruler,**kw,birth_reader=lambda _:self.birth)
        self.capture_patch=patch.object(boundary_module,'capture_planning',side_effect=capture)
        self.capture_patch.start()
        self.remote=RemoteGuestCompletion(self.b,self.key,verify_held=lambda:True) # explicit outer fixture only
        self.session=None

    def tearDown(self):
        if self.session:
            EVIDENCE.append(dict(case=self._testMethodName,status=self.session.status(),
                boundary=self.session.boundary.records,warm=self.warm.events,rules=self.rules.events,
                journal_completed_by_session=False,formal_sent_by_session=False))
        self.capture_patch.stop();super().tearDown()

    def local(self,p):
        boundary=DiagnosticBoundary(self.guest,p,pid=self.guest.pid,birth=self.birth,no_new_commands=True)
        boundary.observe()
        life=DiagnosticLifecycle(self.life.current,boundary)
        bridge=DiagnosticBridge(life,self.warm,target=self.target,records=self.records)
        # Private fixture construction, not Session.open production validation.
        s=Session.__new__(Session);s.reader=self.guest;s.control=self.b;s._control_owner=self.b
        s._key=load_key(self.private_key);s.boundary=boundary;s.records=self.folder;s.scope=self.c.scope
        s.phase='ACTIVE';s.sessions=[];s._lock=threading.RLock();s.source_pins=source_pins()
        s.native_identity=(self.rules.pid,self.rules.birth);s.read_birth=lambda:self.birth
        s.warm=self.warm;s.factory=None;s.lifecycle=life;s.bridge=bridge
        s.observe_loaded=self.rules.observe;s.prepare_rules=self.rules.prepare
        s._owners=(s.reader,s.control,s.warm,s.lifecycle,s.bridge,s.boundary,s.factory)
        s._scope_bytes=session_module.canonical(s.scope)
        self.session=s;return s

    def apply_formal_fixture(self,r,q,p):
        # Deliberately separate fixture protocol driver. It is NOT installed in
        # Session and does not prove the new diagnostic completion seam exists.
        return self.remote.apply(r,p,
            guest_before=lambda:dict(attachment=r.context()['attachments']['B'],viewer_force=self.guest.force,safe_boundary=True),
            apply_received=lambda permit:self.session.apply_native(r,q,p,reservation=permit))

    def test_retained_two_loads_actual_tls_and_predicates(self):
        r,q,p=self.offer(1);s=self.local(p)
        ids=tuple(map(id,(s,s.reader,s.control,s.warm,s.lifecycle,s.bridge)))
        self.apply_formal_fixture(r,q,p)
        self.assertEqual(self.c.period,2);self.assertEqual(s.phase,'ACTIVE')
        r,q,p=self.offer(2);self.apply_formal_fixture(r,q,p)
        self.assertEqual(self.c.period,3);self.assertEqual(s.phase,'TWO_LOADS_RETAINED')
        self.assertEqual(ids,tuple(map(id,(s,s.reader,s.control,s.warm,s.lifecycle,s.bridge))))
        self.assertEqual(len(s.lifecycle.retained),3);self.assertEqual(len(s.sessions),2)
        self.assertEqual(self.warm.events,[['open',0],['load',0,12,2],['open',1],['handover',1],['load',1,2,2]])
        self.assertIsNone(self.room._warm_ack) # Session sent neither advisory nor formal ACK.
        for row in s.sessions:
            self.assertFalse(row['result']['formal_completion_sent']);self.assertFalse(row['result']['journal_completed'])
            self.assertFalse(row['result']['boundary']['input_exclusion_proven'])
        self.assertNotIn(self.key.hex(),json.dumps(s.status()))

    def test_local_completion_leaves_journal_staged_and_room_unadvanced(self):
        r,q,p=self.offer(1);s=self.local(p);result=s.apply_native(r,q,p)
        self.assertEqual(r.journal.status()['status'],'STAGED');self.assertEqual(self.c.period,1)
        self.assertFalse(result['formal_completion_sent']);self.assertIsNone(self.room._warm_ack)
        self.assertEqual(len(s.bridge.completed),1)
        events=list(self.warm.events)
        with self.assertRaises(Exception):s.apply_native(r,q,p)
        self.assertEqual(self.warm.events,events);self.assertEqual(s.phase,'TERMINAL')

    def test_pending_input_rejected_before_native_and_terminal(self):
        r,q,p=self.offer(1);s=self.local(p)
        self.plan_memory.memory.put(self.plan_memory.states[4]+0x660,1,'<I')
        with self.assertRaisesRegex(ValueError,'Pending input'):s.apply_native(r,q,p)
        self.assertFalse(self.warm.events);self.assertEqual(s.phase,'TERMINAL')
        self.plan_memory.memory.put(self.plan_memory.states[4]+0x660,0,'<I')
        with self.assertRaisesRegex(ValueError,'terminal'):s.apply_native(r,q,p)
        self.assertFalse(self.warm.events)

    def test_birth_change_before_load_rejected(self):
        r,q,p=self.offer(1);s=self.local(p);self.birth+=1
        with self.assertRaisesRegex(ValueError,'incarnation'):s.apply_native(r,q,p)
        self.assertFalse(self.warm.events);self.assertEqual(s.phase,'TERMINAL')

    def test_native_failure_retains_objects_and_write_lease(self):
        r,q,p=self.offer(1);s=self.local(p);self.warm.case='load-failed'
        write=session_module.write_once
        def failed_log(path,value):
            if path.name=='diagnostic-native-failed.json':raise OSError('Owned disk-error injection')
            return write(path,value)
        with patch.object(session_module,'write_once',side_effect=failed_log):
            with self.assertRaisesRegex(RuntimeError,'Explicit load failure') as caught:s.apply_native(r,q,p)
        self.assertIn('disk-error',caught.exception.record_error)
        self.assertTrue(self.warm.abort_lease);self.assertEqual(s.phase,'TERMINAL')
        self.assertEqual(len(s.lifecycle.retained),1);self.assertIs(s.warm,self.warm)
        events=list(self.warm.events)
        with self.assertRaises(Exception):s.apply_native(r,q,p)
        self.assertEqual(events,self.warm.events)

    def test_source_drift_refused_before_native(self):
        r,q,p=self.offer(1);s=self.local(p)
        s.source_pins[str(HERE/'b_remote_session.py')]='0'*64
        with self.assertRaisesRegex(ValueError,'source drift'):s.apply_native(r,q,p)
        self.assertFalse(self.warm.events)

    def test_no_new_commands_is_required_not_a_fence(self):
        r,q,p=self.offer(1)
        with self.assertRaisesRegex(ValueError,'no-new-command'):
            DiagnosticBoundary(self.guest,p,pid=self.guest.pid,birth=self.birth,no_new_commands=False)
        s=self.local(p);obs=asdict(s.boundary.observe())
        self.assertTrue(obs['human_no_new_commands']);self.assertFalse(obs['input_exclusion_proven'])
        self.assertFalse(obs['scheduler_fence_proven']);self.assertFalse(obs['atomic_snapshot'])

    def test_production_factory_refuses_bad_target_before_claim_or_api(self):
        r,q,p=self.offer(1);records=self.folder/'open-records';records.mkdir()
        wrong=self.folder/'not-native-target.s14';wrong.write_bytes(b'owned target')
        import b_warm_start as start
        with patch.object(start,'refuse_prior_attempt',side_effect=AssertionError('claim path entered')) as claim, \
             patch.object(b_warm_stable_refresh_coordinator,'Resident',side_effect=AssertionError('API opened')) as resident:
            with self.assertRaisesRegex(ValueError,'Exact target'):
                Session.open(reader=self.guest,control=self.b,scope=self.c.scope,settings={},profile=p,
                    initial_request=q,target=wrong,initial_target={},records=records,adapter_key_path=self.private_key,
                    pair_build=None,pair_sha256=None,helper_build=None,helper_sha256=None,rules_build=None,
                    steam_paths={},source_pins=source_pins(),no_new_commands=True)
            claim.assert_not_called();resident.assert_not_called()
        self.assertFalse(list(records.iterdir()))
        EVIDENCE.append(dict(case=self._testMethodName,actual_factory_entry=True,pre_native_rejection=True))


NAMES=('test_retained_two_loads_actual_tls_and_predicates',
       'test_local_completion_leaves_journal_staged_and_room_unadvanced',
       'test_pending_input_rejected_before_native_and_terminal','test_birth_change_before_load_rejected',
       'test_native_failure_retains_objects_and_write_lease','test_source_drift_refused_before_native',
       'test_no_new_commands_is_required_not_a_fence',
       'test_production_factory_refuses_bad_target_before_claim_or_api')

if __name__=='__main__':
    OUTPUT=PRIVATE/'b_remote_session_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');OUTPUT.mkdir(parents=True)
    transport.OUTPUT=OUTPUT;before=source_pins();stream=io.StringIO()
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.TestSuite(Cases(n) for n in NAMES))
    (OUTPUT/'test.log').write_text(stream.getvalue(),encoding='utf-8')
    after=source_pins();unchanged=before==after
    report=dict(result='PASS' if result.wasSuccessful() and unchanged else 'FAIL',tests=result.testsRun,
        sources=after,inputs_unchanged=unchanged,cases=EVIDENCE,actual_tls=True,actual_journal=True,
        actual_rule_transition_predicates=True,actual_planning_sampler=True,owned_fake_RAM=True,
        native_load_publish_doubles=True,production_factory_executed=False,
        formal_adapter_fixture_only=True,diagnostic_formal_adapter_implemented=False,game_access=False,
        failures=[(str(t),d) for t,d in result.errors+result.failures])
    report['artifacts']={str(p):sha(p) for p in OUTPUT.rglob('*') if p.is_file()}
    (OUTPUT/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(OUTPUT/'result.json');print(stream.getvalue());raise SystemExit(0 if report['result']=='PASS' else 1)
