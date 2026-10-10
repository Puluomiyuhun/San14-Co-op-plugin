"""Real TLS discovery routing before and after the reward endpoint is mounted."""
import hashlib,io,json,unittest
from datetime import datetime
from pathlib import Path
import a_reward_runtime_mount_test as fixture
import reward_planning_discovery as discovery
class Cases(fixture.Cases):
    def test_wait_then_ready_without_refresh_packet(self):
        self.service.failure=None;discovery.install(self.service,self.mount)
        request=dict(action=discovery.ACTION)
        reply=self.b.request(request);self.assertTrue(reply['ok']);self.assertFalse(reply['ready'])
        self.assertFalse(self.a.request(request)['ok'])
        self.opened()
        reply=self.b.request(request);self.assertTrue(reply['ok']);self.assertTrue(reply['ready'])
        self.assertEqual(reply['context']['scope'],self.flow.scope)
        self.assertEqual(reply['context']['profile_sha256'],hashlib.sha256(bytes(self.profile)).hexdigest())
        # A has been idle across endpoint replacement; its first new request
        # must reach the new owner without a dummy status round trip.
        self.assertTrue(self.a.request(self.proposal('A'))['ok'])
        self.assertFalse(self.b.request(dict(request,unexpected=True))['ok'])
        self.mount.failure='owned terminal';self.assertFalse(self.b.request(request)['ok'])
if __name__=='__main__':
    output=fixture.PRIVATE/'reward_planning_discovery_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');output.mkdir(parents=True)
    fixture.observed.transport.OUTPUT=output
    import reward_checkpoint_shared_cut,reward_checkpoint_observer,b_warm_remote_completion
    before=fixture.pins();stream=io.StringIO()
    r=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.TestSuite([Cases('test_wait_then_ready_without_refresh_packet')]))
    after=fixture.pins();(output/'test.log').write_text(stream.getvalue());print(stream.getvalue())
    result=dict(result='PASS' if r.wasSuccessful() and before==after else 'FAIL',tests=r.testsRun,game_access=False,sources=after,inputs_unchanged=before==after,native_and_RAM_doubles=True)
    result['artifacts']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in output.rglob('*') if p.is_file()}
    (output/'result.json').write_text(json.dumps(result,indent=2));print(output/'result.json');raise SystemExit(result['result']!='PASS')
