"""Real TLS/shared-cut/session gate; explicit B native lifecycle/owned RAM doubles.

This tests teardown ordering, not the production B export implementation. The
separate native/port suites cover that implementation and its typed wire.
"""
from copy import deepcopy
from datetime import datetime
import hashlib
import io
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import a_reward_runtime_mount_test as fixture
from b_warm_adapter_key import Native
from b_reward_session import RewardSession,discovery_context
from reward_planning_discovery import install,ACTION
from reward_room_flow import envelope

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];PRIVATE=ROOT.parent/'mod_research'
OUTPUT=None;ROWS=[]


class OwnedNative:
    """Native installation/Stop/CAS and its reader binding are environment doubles."""
    world=None
    @classmethod
    def open(cls,*,session,guest,profile,scope,records,build):
        obj=cls();obj.session=session;obj.guest=guest;obj.checked_port=cls.world.port()
        obj.armed=True;obj.stops=0;obj.verifies=0;obj.failure=None;return obj
    def attach_journal(self,j):self.journal=j
    def stop_restore(self):
        self.stops+=1
        assert self.guest._lock._is_owned() and self.session._lock._is_owned(),'Restore must exclude a concurrent checkpoint apply'
        assert self.checked_port.sampler.failed is not None,'Executable queue must retire before restore'
        if self.failure=='unknown':
            self.session.warm.calls.uncertain=True;raise RuntimeError('Owned native restore reply lost')
        self.armed=False
        return dict(nativeClean=True,restoreVerified=True,slotRestored=True,bridgeActive=0,fixture=True)
    def verify_restored(self):
        self.verifies+=1
        if self.armed or self.failure=='drift':raise RuntimeError('Owned User slot not restored')
        return dict(verified=True,fixture=True)


class Cases(fixture.Cases):
    def setUp(self):
        super().setUp()
        import b_reward_native_port as native
        self.service.failure=None;install(self.service,self.mount)
        not_ready=self.b.request(dict(action=ACTION));self.assertIsNone(discovery_context(not_ready))
        self.mount.open(self.artifacts[1],self.room.artifacts,self.prep)
        self.flow=self.mount.flow;self.gate=self.mount.gate
        report=self.folder/'reward-report.key';cut=self.folder/'reward-cut.key'
        Native().write_new(report,self.reward_key);Native().write_new(cut,self.cut_key)
        self.session.warm.calls=SimpleNamespace(uncertain=False)
        OwnedNative.world=self.worlds['B']
        self.native_patch=patch.object(native,'NativePort',OwnedNative);self.native_patch.start();self.addCleanup(self.native_patch.stop)
        self.reward=RewardSession.open(session=self.session,guest=self.adapter,profile=self.profile,
            discovery=self.b.request(dict(action=ACTION)),build='EXPLICIT_OWNED_NATIVE_DOUBLE',
            report_key_path=report,cut_key_path=cut,records=self.folder/'B-reward')

    def collect(self):
        self.assertTrue(self.a.request(envelope(self.flow.scope,'reward_submit',request_id='7'*32,
            district_id=11,officer_ids=[97]))['ok'])
        self.mount.poll();self.reward.poll()
        self.assertTrue(self.a.request(dict(action='reward_cut_prepare',epoch=self.c.epoch))['ok'])
        self.reward.finish_input();self.mount.poll();self.reward.poll();self.mount.poll()
        self.assertEqual(self.gate.state,'RETIRED_SHARED_CUT')

    def evidence(self,**kw):
        ROWS.append(dict(case=self._testMethodName,phase=self.reward.phase,session_phase=self.session.phase,
            native_stops=self.reward.native.stops,native_verifies=self.reward.native.verifies,
            ready=sorted(self.c.ready),warm_events=self.warm.events,**kw))

    def test_second_load_interlocked_until_cut_native_restore_and_fresh_verification(self):
        self.assertEqual(self.session.phase,'REWARD_PLANNING')
        before=list(self.warm.events)
        with self.assertRaisesRegex(ValueError,'consumed/terminal'):self.session.apply_native(None,None,None)
        self.assertEqual(self.warm.events,before)
        with self.assertRaisesRegex(ValueError,'not retired'):self.reward.assert_released()
        # That misuse is deliberately terminal; a separate test exercises the
        # successful path without trying to consume a forbidden permission.
        self.assertEqual(self.session.phase,'TERMINAL');self.assertEqual(self.reward.native.stops,0);self.evidence()

    def test_success_restores_before_ready_and_permits_one_next_load_boundary(self):
        self.collect();self.assertNotIn('B',self.c.ready)
        original=self.reward.cut.ready_after_cut
        def ready():
            self.assertTrue(self.adapter._lock._is_owned());self.assertTrue(self.session._lock._is_owned())
            return original()
        self.reward.cut.ready_after_cut=ready
        self.reward.poll()
        self.assertEqual((self.reward.phase,self.session.phase),('RELEASED','ACTIVE'))
        self.assertFalse(self.reward.native.armed);self.assertIn('B',self.c.ready)
        self.assertTrue(self.reward.replica.port.sampler.failed)
        self.reward.assert_released();self.assertEqual(self.reward.native.stops,1)
        self.assertEqual(self.reward.native.verifies,2)
        self.evidence()

    def test_unknown_restore_never_ready_or_second_load_and_never_retries(self):
        self.collect();self.reward.native.failure='unknown'
        with self.assertRaisesRegex(RuntimeError,'reply lost'):self.reward.poll()
        self.assertNotIn('B',self.c.ready);self.assertEqual(self.session.phase,'TERMINAL')
        with self.assertRaises(Exception):self.reward.poll()
        with self.assertRaises(Exception):self.session.apply_native(None,None,None)
        self.assertEqual(self.reward.native.stops,1);self.evidence()

    def test_restore_receipt_is_not_enough_when_slot_drifts_before_second_load(self):
        self.collect();self.reward.poll();self.reward.native.failure='drift'
        with self.assertRaisesRegex(RuntimeError,'not restored'):self.reward.assert_released()
        self.assertEqual(self.session.phase,'TERMINAL');self.assertEqual(self.reward.native.stops,1);self.evidence()


def pins():
    return {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted({Path(m.__file__).resolve()
        for m in list(sys.modules.values()) if getattr(m,'__file__',None)}) if p.is_relative_to(ROOT) and p.suffix=='.py'}


if __name__=='__main__':
    import b_reward_native_port,reward_checkpoint_shared_cut,reward_checkpoint_observer,b_warm_remote_completion
    OUTPUT=PRIVATE/'b_reward_session_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');OUTPUT.mkdir(parents=True)
    fixture.observed.transport.OUTPUT=OUTPUT
    before=pins();stream=io.StringIO()
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.TestSuite(Cases(n) for n in Cases.__dict__ if n.startswith('test_')))
    after=pins();(OUTPUT/'test.log').write_text(stream.getvalue(),encoding='utf-8')
    report=dict(result='PASS' if result.wasSuccessful() and before==after else 'FAIL',tests=result.testsRun,sources=after,
        inputs_unchanged=before==after,sources_before=before,cases=ROWS,game_access=False,steam_access=False,actual_TLS_Session_Journal_cut=True,
        production_native_port_executed=False,native_lifecycle_RAM_business_doubles=True,
        failures=[(str(t),s) for t,s in result.errors+result.failures])
    report['artifacts']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in OUTPUT.rglob('*') if p.is_file()}
    (OUTPUT/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(OUTPUT/'result.json');print(stream.getvalue());raise SystemExit(report['result']!='PASS')
