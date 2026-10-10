"""Real RoomTurnControl successor and bootstrap protocol; planning/native doubles.
The paired-reward gate and native OpenPlanning have their own integration suites.
"""
from pathlib import Path
from datetime import datetime
from dataclasses import replace
from copy import deepcopy
import hashlib,io,json,sys,unittest
P=Path(__file__).resolve().parent;ROOT=P.parents[1]
sys.path[:0]=[str(ROOT/'outputs/san14-link'),str(ROOT.parent/'mod_research/python_deps')]
import a_room_native_control_test as base
from a_reward_room_native_control import RewardRoomTurnControl
from a_save_runtime_control import require
from authoritative_sync import digest

class Planning:
    def __init__(self,f,mode):self.f=f;self.mode=mode;self.opened=False;self.polls=0;self.seal=None
    def unlocked(self):
        assert not self.f.room.lock._is_owned() and not self.f.c.lock._is_owned(), "Planning lock order inverted"
    def open(self,artifact,package,prep):
        self.unlocked()
        f=self.f;c=f.c
        require(not self.opened and c.bootstrap_completed and len(c.applied_receipts)==1 and
                c.phase=='PLANNING' and c.period==2,'Formal loaded required')
        require(package.checkpoint_id in c.applied_receipts and artifact.sha256==f.kept[0][2].sha256,
                'Actual first artifact required')
        self.opened=True;f.order.append('open-planning')
        if self.mode=='open-error':raise RuntimeError('owned planning open failure')
        sequence=0 if self.mode=='empty' else 1
        prefix=digest(c.scope) if not sequence else 'f'*64
        value=f.world.world_sha256 if not sequence else '9'*64
        f.world=replace(f.world,world_sha256=value)
        for side in ('A','B'):c.applied_prefix(side,c.epoch,sequence,prefix,value,c.attachments[side])
        self.seal=deepcopy(c.reports['A'])
        if self.mode=='pending':c.set_pending('B',c.epoch,{'still-awaiting-B'})
    def poll(self):
        self.unlocked()
        self.polls+=1
        if self.mode=='poll-error':raise RuntimeError('owned planning uncertain')
    def validate_seal(self,seal):
        self.unlocked()
        require(self.opened and self.mode!='bad-seal' and
                {k:seal[k] for k in self.seal}==self.seal,'Paired planning seal differs')
    def observe_sealed(self,node):
        self.unlocked()
        f=self.f;require(node==f.c.node,'Node changed')
        return replace(f.world,world_sha256='8'*64) if self.mode=='changed' else f.world

class Fixture(base.Fixture):
    def __init__(self,mode='normal',channel_mode='normal'):
        super().__init__(channel_mode)
        self.planning=Planning(self,mode);self.owner=RewardRoomTurnControl(self.planning)
        self.binding._reader=self.owner.copy_artifact

class Tests(unittest.TestCase):
    def test_nonzero_cut_reaches_second_save_and_two_formal_completions(self):
        f=Fixture();r=f.drive()
        self.assertEqual([x.request['cut'] for x in f.submits],[0,1])
        self.assertEqual(f.order,['submit-1','loaded-1','open-planning','sealed-turn','request-next','submit-2','loaded-2'])
        self.assertEqual(r['formal_completions'],2);self.assertTrue(r['reward_planning_connected'])
        self.assertFalse(r['full_world_verified'] or r['two_game_ready'])
        with self.assertRaisesRegex(RuntimeError,'already attempted'):f.drive()
    def test_empty_period_still_valid(self):
        f=Fixture('empty');f.drive();self.assertEqual([x.request['cut'] for x in f.submits],[0,0])
    def test_unconfirmed_bootstrap_cannot_open_planning(self):
        f=Fixture(channel_mode='ack-only')
        with self.assertRaisesRegex(RuntimeError,'timed out'):f.drive()
        self.assertFalse(f.planning.opened);self.assertEqual(f.calls,[])
    def test_bad_seal_and_changed_projection_stop_before_request_next(self):
        for mode in ('bad-seal','changed'):
            with self.subTest(mode=mode):
                f=Fixture(mode)
                with self.assertRaises(RuntimeError):f.drive()
                self.assertEqual(f.calls,[]);self.assertEqual(len(f.submits),1)
    def test_pending_guest_prevents_turn(self):
        f=Fixture('pending')
        with self.assertRaises((RuntimeError,ValueError)):f.drive()
        self.assertEqual(f.calls,[])
    def test_planning_open_or_poll_failure_never_retries(self):
        for mode in ('open-error','poll-error'):
            with self.subTest(mode=mode):
                f=Fixture(mode)
                with self.assertRaises(RuntimeError):f.drive()
                self.assertEqual(len(f.submits),1);self.assertEqual(f.calls,[])
                with self.assertRaisesRegex(RuntimeError,'already attempted'):f.drive()

def pins():
    paths={Path(m.__file__).resolve() for m in list(sys.modules.values()) if getattr(m,'__file__',None)}
    return {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths if p.is_relative_to(ROOT) and p.suffix=='.py'}
if __name__=='__main__':
    run=ROOT.parent/'mod_research/a_reward_room_native_control_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
    before=pins();stream=io.StringIO();r=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
    (run/'tests.log').write_text(stream.getvalue());print(stream.getvalue())
    stable=before==pins();d=dict(result='PASS' if r.wasSuccessful() and stable else 'FAIL',tests=r.testsRun,sources=before,
        sources_unchanged=stable,game_access=False,native_and_planning_are_doubles=True)
    (run/'result.json').write_text(json.dumps(d,indent=2));print(run/'result.json');raise SystemExit(d['result']!='PASS')
