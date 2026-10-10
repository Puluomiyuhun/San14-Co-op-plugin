"""Fixed sortie admission over actual three-room TLS; no native sortie executor.

Real signed fixture bootstrap/checkpoint drives epochs and attachments. Game RAM,
save/load/rules are owned substitutes; admission cannot execute a native sortie.
"""
from copy import deepcopy
from datetime import datetime
import hashlib,io,json,sys,unittest
from pathlib import Path
from unittest.mock import patch

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];PRIVATE=ROOT.parent/'mod_research'
sys.path[:0]=[str(PRIVATE/'python_deps'),str(ROOT/'outputs/san14-link')]
import observed_three_room_service_test as fixture
import sortie_room_admission as gate
from pilot_request import WORDS,BASELINE_SHA,GAME_SHA

OUTPUT=None;ROWS=[]
def sha(raw):return hashlib.sha256(raw).hexdigest()

class Cases(unittest.TestCase):
    host_sample=fixture.Cases.host_sample
    host_boundary=fixture.Cases.host_boundary
    local=fixture.Cases.local
    observation=fixture.Cases.observation
    received=fixture.Cases.received
    ready=fixture.Cases.ready
    complete=fixture.Cases.complete
    wait=fixture.Cases.wait
    _network_setup=fixture.Cases._network_setup
    tearDown=fixture.Cases.tearDown

    def setUp(self):
        fixture.OUTPUT=OUTPUT;old=fixture.transport.manifest
        def manifest():
            m=old();m['profile']['checkpoint_sha256']=BASELINE_SHA;return m
        with patch.object(fixture.transport,'manifest',manifest):fixture.Cases.setUp(self)
        self.complete(1) # actual signed completion, journal and B attachment rotation
        self.admission=gate.Admission(self.folder/'sortie-admission.sqlite',self.room,self.c)
        server=self.owner.servers[0][0];self.original_endpoint=server.room
        server.room=gate.Endpoint(server.room,self.admission)

    def proposal(self,request_id='1'*32,scope=None):
        payload=dict(schema='san14.pilot-submit.v1',request_id=request_id,game_sha256=GAME_SHA,
            baseline_sha256=BASELINE_SHA,force_id=12,source_city_id=19,command_words=WORDS.copy())
        return gate.envelope(scope or self.admission.scope,'sortie_propose',payload=payload)

    def test_duplicate_admission_blocks_ready_and_remote_success_cannot_release(self):
        request=self.proposal();first=self.a.request(request);again=self.a.request(request)
        self.assertTrue(first['ok']);self.assertFalse(first['duplicate']);self.assertTrue(again['duplicate'])
        self.assertEqual(len(self.admission.status()['rows']),1)
        self.assertFalse(first['native_execution_authorized']);self.assertFalse(first['current_world_legality_verified'])
        self.assertEqual(self.c.inflight['A'],{'1'*32})
        self.assertFalse(self.a.request(dict(action='period_ready',epoch=self.c.epoch,ready=True))['ok'])
        self.assertTrue(self.b.request(dict(action='period_ready',epoch=self.c.epoch,ready=True))['ok'])
        with self.assertRaises(Exception):self.c.seal_inputs()
        fake=gate.envelope(self.admission.scope,'sortie_complete',request_id='1'*32,executed=True)
        self.assertFalse(self.a.request(fake)['ok'])
        with self.assertRaisesRegex(ValueError,'not connected'):self.admission.execute(request)
        self.assertEqual(self.c.inflight['A'],{'1'*32})
        rejected=self.admission.reject_local('A','1'*32,'Native adapter not connected')
        self.assertEqual(rejected['native_calls'],0);self.assertFalse(self.c.inflight['A'])
        self.assertEqual(self.a.request(request)['status'],'REJECTED')
        self.owner.ready_for_turn();self.wait(lambda:self.c.phase=='RUNNING','Rejected proposal did not release its marker')
        ROWS.append(dict(case=self._testMethodName,first=first,duplicate=again,rejected=rejected,
            pending_prevented_seal=True,native_sortie_calls=0))

    def test_signed_next_checkpoint_requires_explicit_rebind_rejects_old_epoch(self):
        old=self.proposal();self.assertTrue(self.a.request(old)['ok'])
        self.admission.reject_local('A','1'*32,'No native executor')
        old_scope=deepcopy(self.admission.scope);self.complete(2)
        self.assertFalse(self.a.request({'action':'sortie_scope'})['ok'])
        fresh=self.admission.bind_current();self.assertEqual(fresh['period'],old_scope['period']+1)
        self.assertNotEqual(fresh['epoch'],old_scope['epoch']);self.assertNotEqual(fresh['attachments']['B'],old_scope['attachments']['B'])
        self.assertFalse(self.a.request(old)['ok'])
        self.assertFalse(self.a.request(self.proposal())['ok']) # same request id cannot be assigned to new period
        second=self.a.request(self.proposal('2'*32));self.assertTrue(second['ok'])
        self.assertFalse(second['native_execution_authorized']);self.assertFalse(second['current_world_legality_verified'])
        self.assertEqual(self.c.inflight['A'],{'2'*32})
        ROWS.append(dict(case=self._testMethodName,old_scope=old_scope,new_scope=fresh,
            old_command_rejected=True,native_sortie_calls=0,current_legality_proven=False))

    def test_wrong_seat_words_attachment_or_scope_type_refused(self):
        self.assertFalse(self.b.request(self.proposal())['ok'])
        changed=self.proposal();changed['payload']['command_words'][2]=1500
        self.assertFalse(self.a.request(changed)['ok'])
        changed=self.proposal();changed['scope']['attachments']['A']='9'*32
        self.assertFalse(self.a.request(changed)['ok'])
        changed=self.proposal();changed['scope']['period']=float(changed['scope']['period'])
        self.assertFalse(self.a.request(changed)['ok'])
        self.assertFalse(self.admission.status()['rows']);self.assertFalse(any(self.c.inflight.values()))

    def test_other_pending_owner_preserved_and_lost_marker_holds(self):
        self.c.set_pending('B',self.c.epoch,{'f'*32})
        self.assertTrue(self.a.request(self.proposal())['ok'])
        self.admission.reject_local('A','1'*32,'Unsupported native execution')
        self.assertEqual(self.c.inflight['B'],{'f'*32})
        self.assertFalse(self.b.request(dict(action='period_ready',epoch=self.c.epoch,ready=True))['ok'])
        self.assertTrue(self.a.request(self.proposal('2'*32))['ok'])
        # Explicit faulty other-owner overwrite: endpoint catches missing marker before Ready.
        self.c.set_pending('A',self.c.epoch,set())
        self.assertFalse(self.b.request(dict(action='period_ready',epoch=self.c.epoch,ready=True))['ok'])
        self.assertEqual(self.c.phase,'HELD');self.assertIsNotNone(self.admission.held)
        self.assertEqual(self.admission.status()['rows'][-1]['status'],'UNKNOWN')

    def test_unknown_is_terminal_and_durable(self):
        self.assertTrue(self.a.request(self.proposal())['ok'])
        self.admission.hold_local('Owned uncertain local adapter outcome')
        self.assertEqual(self.c.phase,'HELD');self.assertEqual(self.c.inflight['A'],{'1'*32})
        self.assertFalse(self.a.request(self.proposal())['ok'])
        with self.assertRaises(ValueError):self.admission.reject_local('A','1'*32,'Retry forbidden')
        with self.admission.db() as db:
            self.assertEqual(db.execute('SELECT held FROM metadata').fetchone()[0],'Owned uncertain local adapter outcome')
            self.assertEqual(db.execute('SELECT status FROM proposals').fetchone()[0],'UNKNOWN')

    def test_disconnect_holds_without_clearing_pending(self):
        self.assertTrue(self.a.request(self.proposal())['ok']);self.guest_link.close()
        self.wait(lambda:self.admission.held is not None,'Disconnect did not hold sortie owner')
        self.assertEqual(self.c.phase,'HELD');self.assertEqual(self.c.inflight['A'],{'1'*32})
        self.assertEqual(self.admission.status()['rows'][0]['status'],'UNKNOWN')

    def test_failure_evidence_io_error_still_holds_coordinator(self):
        self.assertTrue(self.a.request(self.proposal())['ok'])
        with patch.object(self.admission,'db',side_effect=OSError('Owned disk unavailable')):
            with self.assertRaisesRegex(OSError,'disk unavailable'):self.admission.hold_local('Unknown local status')
        self.assertEqual(self.c.phase,'HELD');self.assertEqual(self.room._held,'SORTIE_ADMISSION_UNCERTAIN')
        self.assertEqual(self.c.inflight['A'],{'1'*32});self.assertFalse(self.c.ready)
        self.assertFalse(self.a.request(self.proposal())['ok'])

    def test_fresh_journal_required_and_ready_rejects_new_proposal(self):
        with self.assertRaises(FileExistsError):gate.Admission(self.admission.path,self.room,self.c)
        self.owner.ready_for_turn()
        self.assertFalse(self.a.request(self.proposal())['ok']);self.assertFalse(self.admission.status()['rows'])

def pins():
    return {str(p):sha(p.read_bytes()) for p in sorted({Path(m.__file__).resolve() for m in list(sys.modules.values())
        if getattr(m,'__file__',None)}) if p.is_relative_to(ROOT) and p.suffix=='.py'}

if __name__=='__main__':
    OUTPUT=PRIVATE/'sortie_room_admission_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');OUTPUT.mkdir(parents=True)
    before=pins();log=io.StringIO();run=unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Cases))
    (OUTPUT/'test.log').write_text(log.getvalue(),encoding='utf-8');after=pins()
    report=dict(result='PASS' if run.wasSuccessful() and before==after else 'FAIL',tests=run.testsRun,sources=after,
        inputs_unchanged=before==after,cases=ROWS,actual_tls=True,actual_room_coordinator=True,
        actual_sqlite_admission=True,actual_bootstrap_and_checkpoint_signed_completion=True,
        native_save_load_rules_and_snapshot_doubles=True,native_sortie_calls=0,game_access=False,**gate.FLAGS,
        failures=[(str(t),d) for t,d in run.errors+run.failures])
    report['artifacts']={str(p):sha(p.read_bytes()) for p in OUTPUT.rglob('*') if p.is_file()}
    (OUTPUT/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(log.getvalue());print(OUTPUT/'result.json');raise SystemExit(report['result']!='PASS')
