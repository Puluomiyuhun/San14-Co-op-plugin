"""Actual first-view Journal/TLS + rules lifecycle; native/memory/fence doubles."""
from datetime import datetime
import hashlib
import io
import json
from pathlib import Path
import struct
import sys
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRIVATE = ROOT.parent/'mod_research'
sys.path[:0] = [str(PRIVATE/'python_deps'), str(ROOT/'outputs/san14-link')]
import b_warm_room_test as transport
import b_warm_received_apply_test as apply_test
import b_warm_world as world
from b_warm_world_test import Reader
from b_warm_projection import TrustedProjection, host_observation, receiver_from_journal
from b_warm_received_apply import ReceivedApply
from b_warm_profile_contract import Profile, Date, Identity
from human_rules_world_lifecycle import NextWorldRequest
from checkpoint_fresh_save_binding_test import model_artifact, run_model
from authoritative_sync import PeriodCoordinator, scope_from_room, next_node

OUTPUT = None
EVIDENCE = []


def sha(raw): return hashlib.sha256(raw).hexdigest()


from b_warm_bootstrap_protocol import (BootstrapProjection, FormalBootstrapReceivedApply,
    receive_bootstrap_staged, bootstrap_receiver_from_journal)
from b_warm_bootstrap_test import Cases as FileFixture, WarmDouble
import b_warm_bootstrap_test as bootstrap_test
from b_warm_joint_test import Joint as PriorJoint
from b_warm_room import receive_staged
from b_warm_room_test import Client
from checkpoint_bootstrap_journal import BootstrapCheckpointJournal
from checkpoint_journal import CheckpointJournal


class WarmWithMemory(WarmDouble):
    def load(self, bank, p, raw):
        answer=super().load(bank,p,raw)
        # Explicit memory double follows completion; never assert B before loading.
        b=self.guest_reader; b.force=p.target.force; b.ruler=p.target.ruler
        b.memory.put(b.world+0x34,struct.pack('<HBB',p.loaded.year,p.loaded.month,p.loaded.day)+bytes([0,0,b.force,1]))
        if self.case=='bad-target-receipt':
            answer['snapshot']['player']['force_id']=p.source.force
        return answer


class Joint(unittest.TestCase):
    setUp=PriorJoint.setUp
    tearDown=PriorJoint.tearDown

    def receive(self, package, name, *, ordinary=False):
        def connect(token):
            return Client('127.0.0.1', self.download, self.fp,
                dict(method='checkpoint_download', credential=token, profile=self.room.manifest['profile']))
        receive=receive_bootstrap_staged if self.c.period==1 and not ordinary else receive_staged
        return receive(self.b,connect,checkpoint_id=package.checkpoint_id,scope=self.c.scope,
            epoch=self.c.epoch,period=self.c.period,cut=package.manifest['cut'],attachments=self.c.attachments,
            directory=self.folder/name)

    def run_flow(self, case='success', count=2):
        bootstrap_test.OUTPUT=self.folder
        fixture=FileFixture().fixture('native')
        _,target,original,sources,records,rules,life,unused_warm,bridge,holds=fixture
        warm=WarmWithMemory(rules,target,case);bridge.warm=warm
        rows=[];readers={'A':Reader('A'),'B':Reader('A',0x1000000000)}
        readers['B'].side='B';readers['B'].pid=rules.pid;birth=rules.birth
        warm.guest_reader=readers['B']
        for generation in range(1,count+1):
            before_epoch,before_attachment=self.c.epoch,self.c.attachments['B']
            node=next_node(self.c.node)
            data=('EXPLICIT MODEL SAVE PERIOD '+str(generation)).encode()*4000
            profile=Profile();profile.file.name=b'svdexccSC03.s14';profile.file.slot=63
            profile.file.size=len(data);profile.file.sha256[:]=bytes.fromhex(sha(data))
            profile.before=Date(self.c.node['year'],self.c.node['month'],self.c.node['day'])
            profile.loaded=Date(node['year'],node['month'],node['day'])
            profile.source=Identity(666,12,11);profile.target=Identity(952,2,2)
            profile.currentForce=readers['B'].force
            # A advances; B still truthfully shows its old viewer/date until warm.load.
            a=readers['A'];a.memory.put(a.world+0x34,struct.pack('<HBB',node['year'],node['month'],node['day'])+bytes([0,0,a.force,1]))
            def sample(side,p,receipt):
                return world.sample(readers[side],scope=self.c.scope,epoch=self.c.epoch,
                    period=self.c.period,profile=p,side=side,receipt_key=receipt,
                    read_birth=lambda:birth if side=='B' else 1001)
            received=request=adapter=None; native_results=[]
            def native_load(permit):
                warm.request=request
                answer=adapter.apply(received,request,profile,observe_loaded=rules.observe,
                    prepare_rules=rules.prepare,reservation=permit,
                    sample_loaded=lambda r,p,c:sample('B',p,c['accepted']['receipt_key']))
                self.assertEqual(received.journal.status()['status'],'INTENT')
                self.assertEqual(self.c.period,generation)
                native_results.append(answer);return answer['completion']
            projection_type=BootstrapProjection if generation==1 else TrustedProjection
            projection=projection_type(self.c,host_sampler=lambda p,key:sample('A',p,key),
                guest_sampler=lambda p,key:sample('B',p,key),verify_held=lambda:True,
                guest_before=lambda:dict(attachment=self.c.attachments['B'],
                    viewer_force=2 if case=='fake-pre-viewer' else readers['B'].force,safe_boundary=True),
                native_load=native_load,source_kind='FIXTURE_ONLY')
            host_receipt=sha(('explicit Save double '+str(generation)).encode())
            run_model(self.c)
            def observe_host():
                return host_observation(self.c,reader=readers['A'],read_birth=lambda:1001,
                                        verify_held=lambda:True,source_ruler=666)
            reservation=self.binding.reserve(generation,f'mp{generation:08d}.s14',observe_host())
            self.artifacts[generation]=model_artifact(reservation.request,generation,data=data)
            package=self.binding.publish(generation,observe_host)
            received=self.receive(package,f'received-{generation}',ordinary=case=='old-journal')
            request=NextWorldRequest(generation+1,package.checkpoint_id,bytes([0x70+generation])*16,
                                     node['year'],node['month'],node['day'])
            control=self.b
            if case=='lost-ack':
                actual=self.b
                class DropReply:
                    player_id='B'
                    def request(_,packet):
                        actual.request(packet)
                        raise EOFError('Explicit lost reply after actual TLS ACK')
                control=DropReply()
            adapter=FormalBootstrapReceivedApply(bridge,control,scope=self.c.scope,epoch=self.c.epoch,
                period=self.c.period,attachments=self.c.attachments,on_hold=lambda reason:holds.append(reason))
            receiver=(bootstrap_receiver_from_journal if type(received.journal) is BootstrapCheckpointJournal
                      else receiver_from_journal)(received.journal)
            if case!='success':
                with self.assertRaises(Exception):
                    projection.apply(received.journal,receiver,profile,host_receipt_key=host_receipt)
                loads=len([e for e in warm.events if e[0]=='load'])
                expected_loads=1 if case in ('lost-ack','bad-target-receipt') else 0
                self.assertEqual(loads,expected_loads)
                self.assertEqual(received.journal.status()['status'],'INTENT' if expected_loads else 'STAGED')
                self.assertEqual((self.c.period,self.c.phase),(1,'RECONCILING'))
                self.assertFalse(self.c.applied_receipts);self.assertTrue(projection.held_reason)
                with self.assertRaises(Exception):
                    projection.apply(received.journal,receiver,profile,host_receipt_key=host_receipt)
                # Reconstructing the projection does not create another durable permit.
                fresh=projection_type(self.c,host_sampler=projection.host_sampler,guest_sampler=projection.guest_sampler,
                    verify_held=projection.verify_held,guest_before=projection.guest_before,
                    native_load=projection.native_load,source_kind='FIXTURE_ONLY')
                with self.assertRaises(Exception):
                    fresh.apply(received.journal,receiver,profile,host_receipt_key=host_receipt)
                self.assertEqual(len([e for e in warm.events if e[0]=='load']),loads)
                EVIDENCE.append(dict(case=case,loads=loads,journal=received.journal.status(),
                    period=self.c.period,held=projection.held_reason,recreated_owner_replayed=False))
                return
            answer=projection.apply(received.journal,receiver,profile,host_receipt_key=host_receipt)
            self.assertEqual(received.journal.status()['status'],'COMPLETED')
            with received.journal._transaction() as db:
                row=received.journal._row(db);intent=received.journal._intent(row['intent']);receipt=json.loads(row['receipt'])
            self.assertEqual(intent['guest_observation']['viewer_force'],12 if generation==1 else 2)
            self.assertEqual(receipt['viewer_force'],2)
            self.assertEqual((self.c.period,self.c.phase),(generation+1,'PLANNING'))
            self.assertNotEqual(self.c.epoch,before_epoch);self.assertNotEqual(self.c.attachments['B'],before_attachment)
            self.assertEqual(len(self.c.applied_receipts),generation);self.assertEqual(len(native_results),1)
            self.assertFalse(self.c.ready)
            self.assertTrue(all(answer[k] is False for k in ('ready_authorized','full_world_verified','native_gameplay_enabled','fence_released')))
            rows.append(dict(period=generation,result=answer,journal=received.journal.status(),
                journal_schema=received.journal.identity['schema'],pre_viewer=intent['guest_observation']['viewer_force'],
                loaded_viewer=receipt['viewer_force'],native_epoch=request.epoch.hex(),wire_epoch=before_epoch,
                next_epoch=self.c.epoch))
        self.assertFalse(holds);self.assertEqual(len(bridge.completed),2);self.assertEqual(len(life.retained),3)
        self.assertEqual(warm.events,[['open',0],['load',0,12,2],['open',1],['handover',1],['load',1,2,2]])
        self.assertEqual(len(list(records.rglob('*.verified-old.s14'))),2)
        EVIDENCE.append(dict(case='bootstrap-then-next-period',periods=rows,warm=warm.events,rules=rules.events,
            actual_tls=True,actual_windows_staging=True,actual_journal_loaded=True,complete_model_called=False,
            native_memory_publisher_load_save='EXPLICIT_DOUBLE',fake_held=True,ready=False))

    def test_first_view_then_next_period(self): self.run_flow()
    def test_fake_target_before_first_load_rejected(self): self.run_flow('fake-pre-viewer',1)
    def test_old_journal_not_reinterpreted(self): self.run_flow('old-journal',1)
    def test_lost_ack_holds_original_intent(self): self.run_flow('lost-ack',1)
    def test_source_viewer_completion_rejected(self): self.run_flow('bad-target-receipt',1)

def pins():
    paths = {Path(m.__file__).resolve() for m in list(sys.modules.values()) if getattr(m, '__file__', None)}
    paths.add(Path(__file__).resolve())
    return {str(p): sha(p.read_bytes()) for p in sorted(paths) if p.is_relative_to(ROOT) and p.suffix == '.py'}


if __name__ == '__main__':
    OUTPUT = PRIVATE/'b_warm_bootstrap_protocol_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f'); OUTPUT.mkdir(parents=True)
    transport.OUTPUT = OUTPUT; before = pins(); stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Joint))
    (OUTPUT/'test.log').write_text(stream.getvalue(), encoding='utf-8')
    sources = pins(); stable = all(sources.get(k) == v for k, v in before.items())
    report = dict(family='san14.b-warm-bootstrap-protocol.v1', result='PASS' if result.wasSuccessful() and result.testsRun==5 and stable else 'FAIL',
        tests=result.testsRun, sources=sources, inputs_unchanged=stable, cases=EVIDENCE,
        game_access=False, native_calls=False, actual_tls=True, ready=False,
        failures=[(str(t), detail) for t, detail in result.failures+result.errors])
    report['artifacts'] = {str(p): sha(p.read_bytes()) for p in OUTPUT.rglob('*') if p.is_file()}
    (OUTPUT/'result.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(OUTPUT/'result.json'); print(stream.getvalue())
    raise SystemExit(0 if report['result']=='PASS' else 1)
