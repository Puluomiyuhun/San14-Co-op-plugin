"""Consumer through actual TLS Room; all business state is owned fixture data."""
from copy import deepcopy
from datetime import datetime
import hashlib, io, json, sys, unittest
from pathlib import Path

HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[1]; PRIVATE=ROOT.parent/'mod_research'
sys.path[:0]=[str(PRIVATE/'python_deps'),str(ROOT/'outputs/san14-link')]
from reward_result_room_test import Harness, KEY, REPORT_KEYS
from reward_result_consumer import ResultConsumer
from reward_result_channel import CAPABILITIES

OUTPUT=None

class FaultControl:
    def __init__(self,client,mode):self.client=client;self.player_id=client.player_id;self.mode=mode;self.calls=0
    def request(self,request):
        self.calls+=1
        response=self.client.request(request)
        if request['action']=='result_ack' and self.mode=='lost_ack':raise OSError('Owned reply loss after server receipt')
        if request['action']=='result_poll' and self.mode=='missing_packet':response.pop('packet')
        return response
    def close(self):self.client.close()

class Tests(unittest.TestCase):
    def harness(self,modes=None):
        h=Harness(OUTPUT/self._testMethodName);self.addCleanup(h.close)
        h.consumers={}
        for p in ('A','B'):
            c=h.clients[p]
            if modes and p in modes:c=FaultControl(c,modes[p])
            h.consumers[p]=ResultConsumer(c,h.channels[p],result_key=KEY,report_key=REPORT_KEYS[p],records=h.folder/(p+'-consumer'))
        return h
    def submit(self,h,p):
        proposal=h.candidate(p);b=proposal['body']
        r=h.consumers[p].submit_completed(b['event_id'],b['delta'])
        return b,r
    def test_two_directions_source_not_reexecuted_and_duplicate_not_reapplied(self):
        h=self.harness();rows=[]
        for seq,p in enumerate(('A','B'),1):
            source=h.consumers[p];other=h.consumers['B' if p=='A' else 'A']
            body,submit=self.submit(h,p)
            attempts=source.status()['network_attempts']
            self.assertTrue(source.submit_completed(body['event_id'],body['delta'])['duplicate'])
            self.assertEqual(source.status()['network_attempts'],attempts)
            # Receiver may finish first. Repeated poll repeats ACK, never application.
            first=other.consume_one();again=other.consume_one()
            self.assertEqual(first['authority']['status'],'WAITING_RECEIPTS')
            self.assertTrue(again['authority']['duplicate'])
            final=source.consume_one();self.assertEqual(final['authority']['status'],'PAIRED')
            self.assertEqual(final['authority']['sequence'],seq)
            self.assertEqual(other.consume_one()['status'],'NO_RESULT_OFFERED')
            rows.append(final)
        self.assertEqual(h.world.calls,2);self.assertEqual([h.sinks[p].calls for p in ('A','B')],[1,1])
        self.assertEqual(h.sinks['A'].value,h.sinks['B'].value)
        self.assertEqual(h.authority.status()['pending'],0)
        self.assertFalse(h.room.view('A')['native_gameplay_enabled'])
        (h.folder/'consumer-results.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
    def test_lost_ack_does_not_repeat_business_or_retry_connection(self):
        h=self.harness({'B':'lost_ack'});self.submit(h,'A');h.consumers['A'].consume_one()
        with self.assertRaises(OSError):h.consumers['B'].consume_one()
        self.assertEqual(h.sinks['B'].calls,1);self.assertEqual(h.authority.status()['pending'],0)
        self.assertTrue(h.consumers['B'].status()['held'])
        n=h.consumers['B'].status()['network_attempts']
        with self.assertRaisesRegex(ValueError,'terminal'):h.consumers['B'].consume_one()
        self.assertEqual(h.consumers['B'].status()['network_attempts'],n)
        self.assertEqual(h.world.calls,1);self.assertEqual(h.channels['B'].status()['events'],1)
        self.assertTrue((h.folder/'B-consumer/0001-ack-intent.json').exists())
        self.assertFalse((h.folder/'B-consumer/0001-ack-reply.json').exists())
    def test_missing_poll_packet_is_not_mistaken_for_idle(self):
        h=self.harness({'B':'missing_packet'})
        with self.assertRaisesRegex(ValueError,'Missing result'):h.consumers['B'].consume_one()
        self.assertTrue(h.consumers['B'].status()['held']);self.assertEqual(h.sinks['B'].calls,0)
    def test_scope_changes_stop_before_local_application(self):
        h=self.harness();self.submit(h,'A');h.observed_scope['timeline_epoch']='e'*32
        with self.assertRaisesRegex(ValueError,'refused'):h.consumers['B'].consume_one()
        self.assertEqual(h.sinks['B'].calls,0);self.assertTrue(h.authority.status()['held'])
    def test_unexpected_local_state_is_held_and_not_overwritten(self):
        h=self.harness();self.submit(h,'A');h.sinks['B'].value['date']['year']=204
        original=deepcopy(h.sinks['B'].value)
        with self.assertRaises(ValueError):h.consumers['B'].consume_one()
        self.assertEqual(h.sinks['B'].value,original);self.assertEqual(h.sinks['B'].calls,0)
        self.assertTrue(h.consumers['B'].status()['held'])
    def test_changed_local_event_is_not_resent(self):
        h=self.harness();b,_=self.submit(h,'A');changed=deepcopy(b['delta']);changed['after_sha256']='f'*64
        n=h.consumers['A'].status()['network_attempts']
        with self.assertRaisesRegex(ValueError,'Changed'):h.consumers['A'].submit_completed(b['event_id'],changed)
        self.assertEqual(h.consumers['A'].status()['network_attempts'],n)
        self.assertEqual(h.authority.status()['sequence'],1);self.assertEqual(h.world.calls,1)

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def sources():
    paths={Path(__file__).resolve()}
    for m in list(sys.modules.values()):
        f=getattr(m,'__file__',None)
        if f:
            p=Path(f).resolve()
            if p.suffix=='.py' and ROOT in p.parents:paths.add(p)
    return {str(p.relative_to(ROOT)):sha(p) for p in sorted(paths)}
def main():
    global OUTPUT
    OUTPUT=PRIVATE/'reward_result_consumer_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');OUTPUT.mkdir(parents=True)
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes,serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    pins=sources();stream=io.StringIO()
    r=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
    (OUTPUT/'tests.log').write_text(stream.getvalue(),encoding='utf-8');unchanged=sources()==pins
    result=dict(result='PASS' if r.wasSuccessful() and unchanged else 'FAIL',tests=r.testsRun,failures=len(r.failures),errors=len(r.errors),
        sources=pins,inputs_unchanged=unchanged,artifacts={str(p.relative_to(OUTPUT)):sha(p) for p in sorted(OUTPUT.rglob('*')) if p.is_file()},
        real_two_seat_tls=True,game_process_access=False,steam_access=False,**CAPABILITIES)
    path=OUTPUT/'result.json';path.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(stream.getvalue());print(json.dumps(dict(result=result['result'],path=str(path),sha256=sha(path))))
    return 0 if result['result']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
