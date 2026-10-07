"""Guest progress is visible but never grants native/world authority."""
from copy import deepcopy
from datetime import datetime
import hashlib
import json
from pathlib import Path
import unittest

from checkpoint_room_progress import ProgressRoom
from checkpoint_room_artifacts import OUT
from checkpoint_room_lifecycle_test import select_room,coordinator_for,offer,receiver_for,complete_model

HERE=Path(__file__).resolve().parent


class ProgressTests(unittest.TestCase):
    def setUp(self):
        self.room=ProgressRoom(json.loads((OUT/'房间势力目录.json').read_text(encoding='utf-8')))
        select_room(self.room);self.c=coordinator_for(self.room);self.p=offer(self.c)
        self.room.install_offered_checkpoint(self.c,self.p)
        self.total=sum(p['size'] for p in self.p.manifest['parts'].values())
        self.seq=0

    def packet(self,stage='RECEIVING',amount=0,**changes):
        return dict(action='checkpoint_progress',checkpoint_id=self.p.checkpoint_id,epoch=self.c.epoch,
            sequence=self.seq+1,stage=stage,received_bytes=amount,intent=self.c.load_intent,
            reason='WORLD_PROVIDER_MISSING' if stage=='WAITING_WORLD' else 'NONE',**changes)

    def post(self,stage='RECEIVING',amount=0,**changes):
        req=self.packet(stage,amount);req.update(changes)
        reply=self.room.handle('B','b',req)
        if reply['ok'] and not reply['duplicate']:self.seq+=1
        return reply

    def staged(self):
        self.assertTrue(self.post()['ok'])
        self.assertTrue(self.post('STAGED',self.total)['ok'])

    def reserve(self):
        self.staged();r=receiver_for(self.c,self.p)
        for chunk in self.p.chunks():r.accept(chunk)
        self.c.received('B',self.c.epoch,r);self.c.begin_guest_load('B',self.c.epoch)

    def test_progress_visible_to_host_but_never_changes_verified_bytes_or_period(self):
        self.staged()
        self.assertFalse(self.c.bytes_received)
        self.assertIsNone(self.c.load_intent)
        state=self.room.handle('A','a',{'action':'status'})['state']
        self.assertEqual(state['guest_progress']['stage'],'STAGED')
        self.assertFalse(state['guest_progress']['grants_permission'])
        self.assertFalse(state['guest_progress']['full_world_verified'])
        self.assertEqual(self.c.phase,'RECONCILING')

    def test_host_foreign_connection_extra_authority_fields_and_unknown_stage_rejected(self):
        packet=self.packet()
        for who,conn in (('A','a'),('B','foreign')):
            self.assertFalse(self.room.handle(who,conn,packet)['ok'])
        for changes in ({'full_world_verified':True},{'stage':'COMPLETE'},{'sequence':True},
                        {'received_bytes':True},{'reason':'Arbitrary free text'},{'intent':'x'}):
            self.assertFalse(self.room.handle('B','b',{**packet,**changes})['ok'])
        self.assertIsNone(self.room.view('A')['guest_progress'])

    def test_duplicate_is_idempotent_conflict_and_sequence_jump_rejected(self):
        packet=self.packet();self.assertTrue(self.post()['ok'])
        self.assertTrue(self.room.handle('B','b',packet)['duplicate'])
        self.assertFalse(self.room.handle('B','b',{**packet,'received_bytes':1})['ok'])
        self.assertFalse(self.post(sequence=3)['ok'])
        self.assertTrue(self.post(amount=20)['ok'])
        self.assertFalse(self.post(amount=19)['ok'])

    def test_stage_order_complete_bytes_and_local_intent_are_required(self):
        self.assertFalse(self.post('LOAD_REQUESTED',self.total)['ok'])
        self.assertTrue(self.post()['ok'])
        self.assertFalse(self.post('STAGED',self.total-1)['ok'])
        self.assertTrue(self.post('STAGED',self.total)['ok'])
        self.assertFalse(self.post('LOAD_REQUESTED',self.total)['ok'])
        self.assertFalse(self.post('WAITING_WORLD',self.total)['ok'])

    def test_identity_and_waiting_world_do_not_create_completed_receipt_or_enable_ready(self):
        self.reserve()
        self.assertTrue(self.post('LOAD_REQUESTED',self.total)['ok'])
        self.assertFalse(self.post('IDENTITY_RESTORED',self.total,intent='f'*32)['ok'])
        self.assertTrue(self.post('IDENTITY_RESTORED',self.total)['ok'])
        self.assertTrue(self.post('WAITING_WORLD',self.total)['ok'])
        self.assertEqual(self.c.applied_receipts,{})
        self.assertEqual(self.c.period,1)
        self.assertEqual(self.c.phase,'RECONCILING')
        self.assertFalse(self.room.handle('B','b',dict(action='period_ready',epoch=self.c.epoch,ready=True))['ok'])
        self.assertNotIn(self.c.load_intent,json.dumps(self.room.view('A')['guest_progress']))

    def test_held_cannot_be_silently_reset_or_retried(self):
        self.assertTrue(self.post()['ok'])
        self.assertTrue(self.post('HELD',0,reason='TRANSFER_FAILED')['ok'])
        self.assertFalse(self.post()['ok'])
        self.assertEqual(self.room.view('A')['guest_progress']['stage'],'HELD')
        self.assertEqual(self.c.phase,'RECONCILING')

    def test_checkpoint_rotation_clears_progress_and_rejects_old_packets(self):
        old=self.packet();self.assertTrue(self.post()['ok'])
        self.room.install_offered_checkpoint(self.c,self.p)
        self.assertIsNotNone(self.room.view('A')['guest_progress'])
        complete_model(self.c,self.p);new=offer(self.c)
        self.room.install_offered_checkpoint(self.c,new)
        self.assertIsNone(self.room.view('A')['guest_progress'])
        self.assertFalse(self.room.handle('B','b',old)['ok'])

    def test_disconnect_and_room_close_reject_late_progress_without_changing_evidence(self):
        self.assertTrue(self.post()['ok'])
        before=deepcopy(self.room.view('A')['guest_progress'])
        self.room.disconnect('B','b')
        self.assertFalse(self.post(amount=1)['ok'])
        self.assertEqual(self.room.view('A')['guest_progress'],before)
        self.room.close_checkpoints()
        self.assertFalse(self.post(amount=1)['ok'])


if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ProgressTests))
    folder=HERE/'checkpoint_room_progress_tests'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    folder.mkdir(parents=True)
    report=dict(result='PASS' if result.wasSuccessful() else 'FAIL',tests_run=result.testsRun,
        failures=len(result.failures),errors=len(result.errors),game_access=False,
        scope='PURE_ROOM_PROGRESS_AUTHORIZATION_NO_WORLD_AUTHORITY',
        source_sha256={n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in
                      ('checkpoint_room_progress.py','checkpoint_room_progress_test.py')})
    (folder/'result.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(folder/'result.json')
    raise SystemExit(0 if result.wasSuccessful() else 1)
