"""Real three-checkpoint service TLS and signed B completions, owned native doubles.

Network service, selection, Ready, bounded epochs, journals, B Session and cleanup
notifications are real. Host saves, B native loads and rule memory are explicit
owned fixtures. No game, launcher installation, cleanup proof or native ABI claim.
"""
from copy import deepcopy
from datetime import datetime
import hashlib,io,json,secrets,sys,time,unittest
from pathlib import Path
from unittest.mock import patch

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];PRIVATE=ROOT.parent/'mod_research'
sys.path[:0]=[str(PRIVATE/'python_deps'),str(ROOT/'outputs/san14-link')]
import observed_three_room_service as service
import observed_room_service as frozen_service
import a_b_three_joint_test as joint
import b_observed_chain_completion_test as chain
import b_observed_completion_test as prior
import b_warm_room_test as transport
from a_observed_three_room import ObservedFreshSaveBinding,ObservedRoom
from a_room_three_protocol import BootstrapCoordinator
from a_room_three_test import decode_modeled_artifact
from authoritative_sync import next_node,digest

OUTPUT=None;ROWS=[]
def sha(raw):return hashlib.sha256(raw).hexdigest()

class Cases(unittest.TestCase):
    host_sample=joint.Cases.host_sample
    host_boundary=joint.Cases.host_boundary
    local=joint.Cases.local
    observation=joint.Cases.observation
    received=joint.Cases.received

    def _network_setup(self):
        self.folder=OUTPUT/self._testMethodName;self.folder.mkdir()
        self.owner=service.HostService(transport.manifest(),dict(year=203,month=8,day=11,phase='PLANNING_BOUNDARY'),
            directory=self.folder/'network',listen_host='127.0.0.1',advertise_host='127.0.0.1',
            control_port=0,download_port=0)
        self.guest_link=service.join_guest(self.owner.invitation)
        self.c=self.owner.wait_bound(5);self.room=self.owner.room
        self.a,self.b=self.owner.control,self.guest_link.control
        self.fp=self.owner.invitation['fingerprint'];self.download=self.owner.invitation['download_port']
        self.artifacts={}
        self.binding=ObservedFreshSaveBinding(self.room,self.c,native_room_id=bytes.fromhex(digest(self.c.scope)),
            native_room_epoch=71,artifact_reader=lambda n:self.artifacts[n],source_kind='FIXTURE_ONLY')

    def setUp(self):
        self.owner=self.guest_link=None
        # Swap only fixture network assembly: production service itself is used.
        with patch.object(transport.RoomTests,'setUp',Cases._network_setup):
            joint.Cases.setUp(self)

    def tearDown(self):
        if self.warm.native_lease:self.warm.native_lease.close()
        self.capture_patch.stop();self.stage_patch.stop()
        if self.guest_link:self.guest_link.close()
        if self.owner:
            result=self.owner.close();self.assertTrue(result['network_closed'],result)

    def wait(self,predicate,message):
        deadline=time.monotonic()+3
        while not predicate() and time.monotonic()<deadline:time.sleep(.02)
        self.assertTrue(predicate(),message)

    def ready(self):
        self.owner.ready_for_turn()
        self.assertTrue(self.b.request(dict(action='period_ready',epoch=self.c.epoch,ready=True))['ok'])
        self.wait(lambda:self.c.phase=='RUNNING','service did not seal both current Ready requests')

    def complete(self,n):
        if n==1:self.c.begin_bootstrap();node=deepcopy(self.c.node)
        else:self.ready();node=next_node(self.c.node)
        prior.put_date(self.host,node)
        reserved=self.binding.reserve(n,f'mp{n:08d}.s14',self.observation(node))
        self.artifacts[n]=decode_modeled_artifact(reserved.request,n,data=('OWNED THREE SERVICE SAVE '+str(n)).encode()*2048)
        self.host_key=sha(('owned Save receipt '+str(n)).encode())
        package=self.binding.publish(n,lambda:self.observation(node))
        r,q,p=self.received(n,package);reply=self.adapter.apply(r,q,p)
        self.assertEqual(r.journal.status()['status'],'COMPLETED')
        self.assertEqual(len(self.c.applied_receipts),n)
        return r,reply

    def finish(self,count,verified=True,retained=False):
        return self.b.request(dict(action='pilot_guest_finished',formal_completions=count,
            native_cleanup_verified=verified,retained_native_state=retained))

    def test_three_formal_loads_finish_barriers_and_socket_drain(self):
        self.assertIs(type(self.c),BootstrapCoordinator);self.assertIs(type(self.room),ObservedRoom)
        rows=[]
        for n in (1,2,3):
            r,reply=self.complete(n);rows.append(dict(reply=reply,journal=r.journal.status()))
        self.assertEqual((self.c.period,self.c.node['month'],self.c.node['day']),(4,9,1))
        self.assertEqual(len(self.owner._host_ready),2);self.assertEqual(len(self.owner._seal_started),2)
        self.assertFalse(self.c.ready)
        with self.assertRaises(ValueError):self.owner.ready_for_turn()
        bad=self.a.request(dict(action='pilot_guest_finished',formal_completions=3,
            native_cleanup_verified=True,retained_native_state=False))
        self.assertFalse(bad['ok']);self.assertIsNone(self.owner.guest_finished)
        self.assertFalse(self.finish(True)['ok']);self.assertFalse(self.finish(3,retained=True)['ok'])
        result=self.finish(3);self.assertTrue(result['ok'])
        self.assertFalse(result['native_cleanup_independently_verified'])
        self.assertEqual(self.owner.wait_guest_finished(1)['formal_completions'],3)
        self.assertFalse(self.finish(3)['ok'])
        self.assertFalse(self.b.request({'action':'pilot_host_finished'})['host_finished'])
        with self.assertRaises(ValueError):self.owner.wait_guest_disconnected(1)
        self.owner.mark_host_finished()
        barrier=self.b.request({'action':'pilot_host_finished'})
        self.assertTrue(barrier['host_finished']);self.assertFalse(barrier['native_cleanup_independently_verified'])
        with self.assertRaises(ValueError):self.owner.mark_host_finished()
        self.guest_link.close();self.assertTrue(self.owner.wait_guest_disconnected(3)['guest_control_disconnected'])
        close=self.owner.close();self.assertTrue(close['network_closed']);self.assertFalse(close['native_cleanup_claimed'])
        ROWS.append(dict(case=self._testMethodName,rows=rows,finish=result,barrier=barrier,close=close,
            native_cleanup_test_message_only=True,owned_loads=self.warm.events))

    def test_two_completions_cannot_claim_successful_finish(self):
        self.complete(1);self.complete(2)
        self.assertEqual(self.c.period,3)
        self.assertFalse(self.finish(2)['ok']);self.assertFalse(self.finish(3)['ok'])
        self.assertIsNone(self.owner.guest_finished);self.assertEqual(self.c.phase,'PLANNING')
        self.assertEqual(self.owner.failure,None)

    def test_ready_requires_fresh_both_seats_each_epoch(self):
        with self.assertRaises(ValueError):self.owner.ready_for_turn()
        self.complete(1);old_epoch=self.c.epoch
        self.owner.ready_for_turn();time.sleep(.1)
        self.assertEqual(self.c.phase,'PLANNING');self.assertFalse(self.owner._seal_started)
        with self.assertRaises(ValueError):self.owner.ready_for_turn()
        self.assertTrue(self.b.request(dict(action='period_ready',epoch=old_epoch,ready=True))['ok'])
        self.wait(lambda:self.c.phase=='RUNNING','first Ready seal absent')
        node=next_node(self.c.node);prior.put_date(self.host,node)
        reserved=self.binding.reserve(2,'mp00000002.s14',self.observation(node))
        self.artifacts[2]=decode_modeled_artifact(reserved.request,2,data=b'owned second generation'*2048)
        self.host_key=sha(b'owned second receipt');package=self.binding.publish(2,lambda:self.observation(node))
        r,q,p=self.received(2,package);self.adapter.apply(r,q,p)
        self.assertNotEqual(old_epoch,self.c.epoch)
        self.assertFalse(self.b.request(dict(action='period_ready',epoch=old_epoch,ready=True))['ok'])
        self.assertTrue(self.b.request(dict(action='period_ready',epoch=self.c.epoch,ready=True))['ok'])
        time.sleep(.1);self.assertEqual(self.c.phase,'PLANNING');self.assertEqual(len(self.owner._seal_started),1)
        self.owner.ready_for_turn();self.wait(lambda:self.c.phase=='RUNNING','second Ready seal absent')
        self.assertEqual(len(self.owner._host_ready),2);self.assertEqual(len(self.owner._seal_started),2)

    def test_disconnect_after_two_holds_and_rejoin_refused(self):
        self.complete(1);self.complete(2);self.guest_link.close()
        self.wait(lambda:self.owner.guest_disconnected.is_set(),'guest disconnect was not observed')
        self.wait(lambda:self.c.phase=='HELD','disconnect did not hold coordinator')
        with self.assertRaises(Exception):service.join_guest(self.owner.invitation)
        with self.assertRaises(Exception):self.owner.ready_for_turn()
        self.assertEqual(len(self.c.applied_receipts),2);self.assertIsNone(self.owner.guest_finished)

    def test_abort_notification_holds_and_never_implies_cleanup(self):
        result=self.finish(0,verified=False,retained=True)
        self.assertTrue(result['ok']);self.assertFalse(result['native_cleanup_independently_verified'])
        self.assertEqual(self.c.phase,'HELD');self.assertFalse(self.c.ready)
        self.assertTrue(self.owner.wait_guest_finished(1)['retained_native_state'])
        with self.assertRaises(Exception):self.owner.ready_for_turn()
        self.assertFalse(self.finish(0,verified=False,retained=True)['ok'])
        self.assertFalse(self.b.request({'action':'pilot_context','extra':True})['ok'])

    def test_three_invitation_is_distinct_and_pinned(self):
        n=self.owner.invitation
        self.assertEqual(n['schema'],'san14.observed-three-pilot-invitation.v1')
        with self.assertRaises(ValueError):frozen_service.validate_invitation(n)
        old=deepcopy(n);old['schema']='san14.observed-pilot-invitation.v1'
        with self.assertRaises(ValueError):service.validate_invitation(old)
        wrong=deepcopy(n);wrong['fingerprint']='0'*64
        with self.assertRaises(Exception):service.join_guest(wrong)
        self.assertEqual(self.guest_link.wait_context(1)['scope'],self.c.scope)

def pins():
    return {str(p):sha(p.read_bytes()) for p in sorted({Path(m.__file__).resolve() for m in list(sys.modules.values())
        if getattr(m,'__file__',None)}) if p.is_relative_to(ROOT) and p.suffix=='.py'}

if __name__=='__main__':
    OUTPUT=PRIVATE/'observed_three_room_service_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');OUTPUT.mkdir(parents=True)
    before=pins();log=io.StringIO();run=unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Cases))
    (OUTPUT/'test.log').write_text(log.getvalue(),encoding='utf-8');after=pins()
    report=dict(result='PASS' if run.wasSuccessful() and before==after else 'FAIL',tests=run.testsRun,sources=after,
        inputs_unchanged=before==after,cases=ROWS,actual_tls_service=True,actual_journals=True,
        actual_signed_formal_completion=True,actual_b_chain_session=True,actual_ready_and_cleanup_handshake=True,
        native_save_load_rules_and_host_snapshot_doubles=True,native_cleanup_proven=False,
        game_access=False,native_gameplay_enabled=False,full_world_verified=False,
        failures=[(str(t),d) for t,d in run.errors+run.failures])
    report['artifacts']={str(p):sha(p.read_bytes()) for p in OUTPUT.rglob('*') if p.is_file()}
    (OUTPUT/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(log.getvalue());print(OUTPUT/'result.json');raise SystemExit(report['result']!='PASS')
