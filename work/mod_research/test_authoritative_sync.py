"""Protocol adversarial tests. Worlds below are fixtures, never SAN14 state."""
from pathlib import Path
import sys,json,unittest,secrets,base64
from copy import deepcopy
HERE=Path(__file__).resolve().parent;OUT=HERE.parents[1]/'outputs'/'san14-link'
sys.path.insert(0,str(OUT))
from authoritative_sync import *
from room_session import Room

NODE={'year':203,'month':8,'day':11,'phase':'PLANNING_BOUNDARY'}
NEXT={**NODE,'day':21}
OLD={'armies':{'1':{'troops':1000},'2':{'troops':900},'3':{'troops':800},'4':{'troops':700}},'persons':{'5':'free'},'tiles':{'6':12},'tasks':[7]}
HOST={'armies':{'1':{'troops':600},'2':{'troops':500},'3':{'troops':800},'4':{'troops':700}},'persons':{'5':'captured'},'tiles':{'6':2},'tasks':[]}
GUEST={'armies':{'1':{'troops':1000},'2':{'troops':900},'3':{'troops':400}},'persons':{'5':'dead'},'tiles':{'6':12},'tasks':[7]}

def bound_room():
    manifest=json.loads((OUT/'房间势力目录.json').read_text(encoding='utf-8'));r=Room(manifest)
    r.authenticate({'method':'host','credential':r.host_token,'profile':manifest['profile']},'a')
    r.authenticate({'method':'join','credential':r.invite,'profile':manifest['profile']},'b')
    for p,c,f in [('A','a',12),('B','b',2)]:
        assert r.handle(p,c,{'action':'select_force','request_id':secrets.token_hex(16),'expected_revision':r.revision,'force_id':f})['ok']
    for p,c in [('A','a'),('B','b')]:
        assert r.handle(p,c,{'action':'confirm_force','request_id':secrets.token_hex(16),'expected_revision':r.revision})['ok']
    return r

class SyncTests(unittest.TestCase):
    def setUp(self):
        self.room=bound_room();self.scope=scope_from_room(self.room)
        self.c=PeriodCoordinator(self.scope,'synthetic-complete-world.v1',digest(OLD),{'A':'a'*32,'B':'b'*32},NODE)
    def running(self):
        for p in ('A','B'):self.c.set_ready(p,self.c.epoch,True)
        permit=self.c.seal_inputs();self.c.begin_simulation(permit);return permit
    def package(self,world=HOST,source='A',data=None):
        return CheckpointPackage(self.scope,self.c.epoch,self.c.period,{k:self.c.seal[k] for k in ('sequence','prefix_sha256')},
               NEXT,self.c.state_contract,digest(world),{'world.s14':data or canonical(world),'adapter.json':canonical({'fixture':True,'events':[]})},source_player=source)
    def offered(self,data=None):
        self.running();p=self.package(data=data);self.c.offer_checkpoint('A',p.manifest);return p
    def receiver(self,p):return CheckpointReceiver(p.manifest,p.checkpoint_id,self.scope,self.c.epoch,self.c.period,p.manifest['cut'])
    def ready_load(self):
        p=self.offered();r=self.receiver(p)
        for ch in p.chunks():r.accept(ch)
        self.c.received('B',self.c.epoch,r);token=self.c.begin_guest_load('B',self.c.epoch)
        return p,r,{'player':'B','epoch':self.c.epoch,'checkpoint_id':p.checkpoint_id,'intent':token,
             'world_sha256':digest(HOST),'viewer_force':2,'new_attachment':'c'*32,
             'host_observation':{'attachment':'a'*32,'world_sha256':digest(HOST),'node':NEXT}}
    def test_room_remains_native_disabled(self):
        self.assertEqual(self.room.view('A')['phase'],'WAITING_NATIVE_ADAPTER')
        self.assertFalse(self.c.status()['native_gameplay_enabled'])
    def test_one_ready_cannot_start(self):
        self.c.set_ready('A',self.c.epoch,True)
        with self.assertRaises(SyncError):self.c.seal_inputs()
    def test_pending_local_request_blocks_ready(self):
        self.c.set_pending('A',self.c.epoch,{'1'*32})
        with self.assertRaises(SyncError):self.c.set_ready('A',self.c.epoch,True)
    def test_ready_player_cannot_submit_new_request(self):
        self.c.set_ready('A',self.c.epoch,True)
        with self.assertRaises(SyncError):self.c.set_pending('A',self.c.epoch,{'1'*32})
    def test_other_player_can_continue_while_A_ready(self):
        self.c.set_ready('A',self.c.epoch,True);self.c.set_pending('B',self.c.epoch,{'1'*32})
        for p in ('A','B'):self.c.applied_prefix(p,self.c.epoch,1,'d'*64,'e'*64,self.c.attachments[p])
        self.c.set_pending('B',self.c.epoch,set());self.c.set_ready('B',self.c.epoch,True)
        self.assertEqual(self.c.seal_inputs()['sequence'],1)
    def test_missing_applied_prefix_blocks_seal(self):
        self.c.applied_prefix('A',self.c.epoch,1,'d'*64,'e'*64,'a'*32)
        for p in ('A','B'):self.c.set_ready(p,self.c.epoch,True)
        with self.assertRaises(SyncError):self.c.seal_inputs()
    def test_same_prefix_state_drift_rejected(self):
        with self.assertRaises(SyncError):self.c.applied_prefix('B',self.c.epoch,0,digest(self.scope),'f'*64,'b'*32)
    def test_reloaded_attachment_invalidates_old_prefix(self):
        with self.assertRaises(SyncError):self.c.applied_prefix('B',self.c.epoch,0,digest(self.scope),digest(OLD),'c'*32)
    def test_permit_consumed_once(self):
        p=self.running()
        with self.assertRaises(SyncError):self.c.begin_simulation(p)
    def test_cannot_unready_after_seal(self):
        self.running()
        with self.assertRaises(SyncError):self.c.set_ready('A',self.c.epoch,False)
    def test_B_cannot_publish_final_result(self):
        self.running()
        with self.assertRaises(SyncError):self.package(source='B')
        p=self.package()
        with self.assertRaises(SyncError):self.c.offer_checkpoint('B',p.manifest)
    def test_B_cannot_create_authority_event(self):
        self.running()
        with self.assertRaises(SyncError):self.c.host_event('B','1'*32,'B',('accept',))
    def test_event_waits_for_its_owner_and_authority_application(self):
        self.running();self.c.host_event('A','1'*32,'B',('accept','decline'))
        with self.assertRaises(SyncError):self.c.answer_event('A',self.c.epoch,'1'*32,'accept')
        self.c.answer_event('B',self.c.epoch,'1'*32,'accept')
        self.assertEqual(self.c.phase,'WAITING_EVENT')
        with self.assertRaises(SyncError):self.c.offer_checkpoint('A',self.package().manifest)
        self.c.event_applied('A','1'*32);self.assertEqual(self.c.phase,'RUNNING')
    def test_duplicate_event_answer_does_not_apply_twice(self):
        self.running();self.c.host_event('A','1'*32,'B',('accept','decline'))
        for _ in range(2):self.c.answer_event('B',self.c.epoch,'1'*32,'accept')
        with self.assertRaises(SyncError):self.c.answer_event('B',self.c.epoch,'1'*32,'decline')
        self.c.event_applied('A','1'*32)
        with self.assertRaises(SyncError):self.c.event_applied('A','1'*32)
        self.assertEqual(len(self.c.trace),1)
    def test_chunks_out_of_order_and_duplicate(self):
        p=self.offered(data=b'x'*(CHUNK*2+1));r=self.receiver(p);packets=list(p.chunks())
        for ch in reversed(packets):r.accept(ch)
        self.assertTrue(r.accept(packets[0])['duplicate']);self.assertEqual(r.verified_parts()['world.s14'],b'x'*(CHUNK*2+1))
    def test_missing_chunk_prevents_load(self):
        p=self.offered();r=self.receiver(p);r.accept(next(p.chunks()))
        with self.assertRaises(SyncError):self.c.received('B',self.c.epoch,r)
        with self.assertRaises(SyncError):self.c.begin_guest_load('B',self.c.epoch)
    def test_conflicting_duplicate_rejected(self):
        p=self.offered();r=self.receiver(p);ch=next(p.chunks());r.accept(ch)
        data=bytearray(base64.b64decode(ch['data']));data[0]^=1;ch['data']=base64.b64encode(data).decode()
        with self.assertRaises(SyncError):r.accept(ch)
    def test_corrupted_complete_content_rejected(self):
        p=self.offered();r=self.receiver(p)
        for ch in p.chunks():
            b=bytearray(base64.b64decode(ch['data']));b[0]^=1;ch['data']=base64.b64encode(b).decode();r.accept(ch)
        with self.assertRaises(SyncError):r.verified_parts()
    def test_manifest_tamper_rejected(self):
        p=self.offered();m=p.manifest;m['world_sha256']='f'*64
        with self.assertRaises(SyncError):CheckpointReceiver(m,p.checkpoint_id,self.scope,self.c.epoch,self.c.period,m['cut'])
    def test_foreign_room_and_old_epoch_rejected(self):
        p=self.offered();scope=deepcopy(self.scope);scope['room_id']='0'*32
        for sc,epoch in ((scope,self.c.epoch),(self.scope,'0'*32)):
            with self.assertRaises(SyncError):CheckpointReceiver(p.manifest,p.checkpoint_id,sc,epoch,self.c.period,p.manifest['cut'])
    def test_checkpoint_needs_all_artifacts(self):
        self.running();m=self.package().manifest;del m['parts']['adapter.json']
        with self.assertRaises(SyncError):self.c.offer_checkpoint('A',m)
    def test_file_receipt_does_not_unlock_next_period(self):
        p,r,q=self.ready_load();self.assertEqual(self.c.phase,'RECONCILING');self.assertEqual(self.c.period,1)
        with self.assertRaises(SyncError):self.c.set_ready('B',self.c.epoch,True)
    def test_load_cannot_auto_retry_after_intent(self):
        self.ready_load()
        with self.assertRaises(SyncError):self.c.begin_guest_load('B',self.c.epoch)
    def test_wrong_loaded_world_identity_or_attachment_stays_locked(self):
        _,_,q=self.ready_load()
        for field,bad in [('world_sha256',digest(GUEST)),('viewer_force',12),('new_attachment','b'*32),('intent','9'*32)]:
            with self.assertRaises(SyncError):self.c.loaded(**{**q,field:bad})
            self.assertEqual(self.c.phase,'RECONCILING')
    def test_host_drift_while_B_loads_blocks_release(self):
        _,_,q=self.ready_load();q['host_observation']['world_sha256']=digest(GUEST)
        with self.assertRaises(SyncError):self.c.loaded(**q)
    def test_divergent_guest_replaced_wholesale_then_new_epoch(self):
        p,r,q=self.ready_load();guest=deepcopy(GUEST);self.assertNotEqual(guest,HOST)
        guest=json.loads(r.verified_parts()['world.s14']);self.assertEqual(guest,HOST)
        old=q['epoch'];result=self.c.loaded(**q)
        self.assertEqual(self.c.period,2);self.assertNotEqual(self.c.epoch,old);self.assertFalse(result['native_gameplay_enabled'])
        with self.assertRaises(SyncError):self.c.set_ready('B',old,True)
        self.assertEqual(self.c.attachments['A'],'a'*32);self.assertEqual(self.c.attachments['B'],'c'*32)
    def test_duplicate_load_receipt_does_not_advance_twice(self):
        _,_,q=self.ready_load();self.c.loaded(**q);epoch=self.c.epoch
        self.assertTrue(self.c.loaded(**q)['duplicate']);self.assertEqual(self.c.period,2);self.assertEqual(self.c.epoch,epoch)
        with self.assertRaises(SyncError):self.c.loaded(**{**q,'viewer_force':12})
    def test_transfer_disconnect_can_resume_without_partial_load(self):
        p=self.offered();r=self.receiver(p);packets=list(p.chunks());r.accept(packets[0])
        self.c.connection('B',False)
        with self.assertRaises(SyncError):self.c.begin_guest_load('B',self.c.epoch)
        self.c.connection('B',True)
        for packet in packets:r.accept(packet)
        self.c.received('B',self.c.epoch,r);self.assertEqual(self.c.phase,'RECONCILING')
    def test_simulation_disconnect_never_auto_resumes(self):
        self.running();self.c.connection('B',False);self.c.connection('B',True);self.assertEqual(self.c.phase,'HELD')
    def test_bad_chunk_index_name_and_size_rejected(self):
        p=self.offered();r=self.receiver(p);ch=next(p.chunks())
        for key,value in [('index',True),('index',999999),('part','../outside'),('data','A'*(CHUNK*2))]:
            with self.assertRaises(SyncError):r.accept({**ch,key:value})
    def test_no_full_world_claim_can_be_smuggled_in_manifest(self):
        p=self.offered();m=p.manifest;m['native_coverage_verified']=True
        with self.assertRaises(SyncError):self.c.offer_checkpoint('A',m)
    def test_staging_manifest_cannot_be_modified_after_pinning(self):
        p=self.offered();r=self.receiver(p);r.manifest['world_sha256']='f'*64
        with self.assertRaises(SyncError):r.accept(next(p.chunks()))
        with self.assertRaises(SyncError):r.verified_parts()
    def test_reused_authority_event_cannot_run_again(self):
        self.running();self.c.host_event('A','1'*32,'B',('continue',))
        self.c.answer_event('B',self.c.epoch,'1'*32,'continue');self.c.event_applied('A','1'*32)
        with self.assertRaises(SyncError):self.c.host_event('A','1'*32,'B',('continue',))
    def test_skipped_period_checkpoint_is_rejected(self):
        self.running();m=self.package().manifest;m['node']={**NEXT,'month':9,'day':1}
        with self.assertRaises(SyncError):self.c.offer_checkpoint('A',m)
    def test_month_year_boundaries(self):
        self.assertEqual(next_node({**NODE,'month':12,'day':21}),{'year':204,'month':1,'day':1,'phase':'PLANNING_BOUNDARY'})
        with self.assertRaises(SyncError):next_node({**NODE,'day':12})

if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(SyncTests))
    report={'result':'PASS' if result.wasSuccessful() else 'FAIL','tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
            'world_type':'synthetic fixtures','real_game_processes_opened':0,'native_gameplay_enabled':False}
    (HERE/'authoritative-sync-tests.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    raise SystemExit(0 if result.wasSuccessful() else 1)
