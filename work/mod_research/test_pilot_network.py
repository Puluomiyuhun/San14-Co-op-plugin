"""Offline protocol/duplicate/crash guards. Executors here are simulated."""
import copy
import hashlib
import hmac
from pathlib import Path
import tempfile
import unittest
from pilot_request import canonical,authenticate,sign,WORDS,BASELINE_SHA,GAME_SHA
from pilot_network import Journal


class NetworkTests(unittest.TestCase):
    def setUp(self):
        self.payload={'schema':'san14.pilot-submit.v1','request_id':'ab'*16,'game_sha256':GAME_SHA,
                      'baseline_sha256':BASELINE_SHA,'force_id':12,'source_city_id':19,'command_words':WORDS.copy()}
        self.key=b'test-session-key'
        self.temp=tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent,prefix='network-test-')
        self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'journal.jsonl'
        self.calls=0

    def executor(self,payload):
        self.calls+=1
        return {'soldiers':payload['command_words'][2],'simulated':True}

    def packet_without_client_validation(self,payload):
        return {'payload':payload,'mac':hmac.new(self.key,canonical(payload),hashlib.sha256).hexdigest()}

    def test_valid_and_duplicate(self):
        payload=authenticate(sign(self.payload,self.key),self.key)
        journal=Journal(self.path)
        first=journal.execute(payload,self.executor)
        second=journal.execute(payload,self.executor)
        self.assertEqual(second,{**first,'duplicate':True})
        self.assertEqual(self.calls,1)

    def test_persisted_receipt_after_receiver_restart(self):
        Journal(self.path).execute(self.payload,self.executor)
        replay=Journal(self.path).execute(self.payload,self.executor)
        self.assertTrue(replay['duplicate'])
        self.assertEqual(self.calls,1)

    def test_wrong_session_key(self):
        with self.assertRaisesRegex(ValueError,'authentication'):
            authenticate(sign(self.payload,self.key),b'other-session')

    def test_changed_payload(self):
        packet=sign(copy.deepcopy(self.payload),self.key)
        packet['payload']['command_words'][2]=1400
        with self.assertRaisesRegex(ValueError,'authentication'):
            authenticate(packet,self.key)

    def test_authenticated_wrong_owner(self):
        self.payload['force_id']=13
        with self.assertRaisesRegex(ValueError,'ownership'):
            authenticate(self.packet_without_client_validation(self.payload),self.key)

    def test_authenticated_stale_baseline(self):
        self.payload['baseline_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'baseline'):
            authenticate(self.packet_without_client_validation(self.payload),self.key)

    def test_unknown_fields_cannot_pass(self):
        self.payload['function_pointer']=123
        with self.assertRaisesRegex(ValueError,'envelope'):
            authenticate(self.packet_without_client_validation(self.payload),self.key)

    def test_crash_after_intent_never_auto_replays(self):
        Journal(self.path).append({'request_id':self.payload['request_id'],
                                  'payload_sha256':hashlib.sha256(canonical(self.payload)).hexdigest(),
                                  'state':'IN_PROGRESS'})
        result=Journal(self.path).execute(self.payload,self.executor)
        self.assertEqual(result['status'],'UNKNOWN_NO_AUTO_RETRY')
        self.assertEqual(self.calls,0)

    def test_executor_error_never_auto_replays(self):
        def fail(payload):
            self.calls+=1
            raise RuntimeError('Simulated uncertain adapter outcome')
        Journal(self.path).execute(self.payload,fail)
        result=Journal(self.path).execute(self.payload,self.executor)
        self.assertEqual(result['status'],'UNKNOWN_NO_AUTO_RETRY')
        self.assertEqual(self.calls,1)


if __name__=='__main__':unittest.main(verbosity=2)
