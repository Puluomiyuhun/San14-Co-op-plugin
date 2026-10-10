"""Owned RAM / native-report doubles only; no game, native call or archived claim."""
from datetime import datetime
from pathlib import Path
import ctypes as C
import hashlib,io,json,sys,unittest
from unittest.mock import patch
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];PRIVATE=ROOT.parent/'mod_research'
sys.path[:0]=[str(PRIVATE/'python_deps'),str(ROOT/'outputs/san14-link')]
import a_observed_boundary_test as previous
import a_save_runtime_contract as old
import a_save_three_runtime_contract as wire
import a_observed_three_boundary as observed

def complete(f,generation):
    s=f.runtime;s.saveStatus=5;s.saveGeneration=s.mailboxCount=generation
    s.mailboxStates[:]=[5]*generation+[0]*(3-generation)
    s.binds=s.queues=s.workerJoined=s.fileVerified=1;s.phaseMask=31;s.originalReturned=27

class Cases(unittest.TestCase):
    # Reuse unchanged adversarial RAM tests with dedicated successor types.
    test_owned_hooks=previous.Cases.test_owned_hooks_and_real_typed_reports_observed_not_fenced
    test_shared_world=previous.Cases.test_complete_two_tables_match_B_other_view
    test_rebuilt_states=previous.Cases.test_new_user_after_completed_save_is_resampled
    test_pending_native_work=previous.Cases.test_report_queue_pending_command_active_task_and_source_drift_refused
    test_busy_failed_runtime=previous.Cases.test_busy_foreign_or_failed_runtime_never_observed
    test_sampling_race=previous.Cases.test_same_name_address_race_and_table_drift_refused
    def setUp(self):
        a=patch.object(previous,'wire',wire);b=patch.object(previous,'observed',observed)
        a.start();b.start();self.addCleanup(a.stop);self.addCleanup(b.stop)
    def test_all_wire_types_distinct_and_old_replies_refused(self):
        nonce=b'\x45'*32
        self.assertEqual(wire.MAGIC,0x33585241)
        self.assertEqual(C.sizeof(wire.Snapshot),C.sizeof(old.Snapshot)+4)
        for kind,ops in wire.OPERATIONS.items():
            self.assertIsNot(kind,old.TYPES[kind.__name__])
            for op in ops:
                with self.subTest(kind=kind.__name__,op=op):
                    q=wire.envelope(kind,op,nonce);self.assertEqual(bytes(wire.decode(kind,op,nonce,bytes(q))),bytes(q))
                    legacy=old.envelope(old.TYPES[kind.__name__],op,nonce)
                    with self.assertRaises(ValueError):wire.decode(kind,op,nonce,bytes(legacy))
                    q.header.magic=old.MAGIC
                    with self.assertRaises(ValueError):wire.decode(kind,op,nonce,bytes(q))
                    with self.assertRaises(ValueError):wire.envelope(old.TYPES[kind.__name__],op,nonce)
        with self.assertRaises(ValueError):wire.envelope(wire.Plans,'Prepare',nonce)
        with self.assertRaises(ValueError):wire.envelope(wire.Prepare,'Prepare',bytes(32))
    def test_consecutive_all_three_complete_and_fourth_refused(self):
        f=previous.Fixture();f.provider.observe(f.node)
        for g in (1,2,3):
            complete(f,g);ob=f.provider.observe(f.node)
            self.assertEqual(f.provider._last_runtime.saveGeneration,g)
            self.assertFalse(any(ob.coverage.values()))
        f.runtime.saveGeneration=f.runtime.mailboxCount=4
        with self.assertRaises(ValueError):f.provider.observe(f.node)
        self.assertEqual(f.provider.sequence,4)
    def test_bad_third_slot_and_unretired_third_refused(self):
        for field,value in [('third',0),('third',4),('workerJoined',0),('originalReturned',0),('phaseMask',15),('saveActive',1),('parentActive',1),('hostLease',1)]:
            with self.subTest(field=field,value=value):
                f=previous.Fixture();complete(f,3)
                if field=='third':f.runtime.mailboxStates[2]=value
                else:setattr(f.runtime,field,value)
                with self.assertRaises(ValueError):f.provider.observe(f.node)
                self.assertEqual(f.provider.sequence,0)
        f=previous.Fixture();complete(f,2);f.runtime.mailboxStates[2]=5
        with self.assertRaises(ValueError):f.provider.observe(f.node)
    def test_skipped_or_rewound_observed_generations_refused(self):
        for generations in ((0,2),(1,3),(3,2)):
            f=previous.Fixture()
            if generations[0]:complete(f,generations[0])
            f.provider.observe(f.node);complete(f,generations[1])
            with self.assertRaises(ValueError):f.provider.observe(f.node)
            self.assertEqual(f.provider.sequence,1)
    def test_old_plans_snapshot_or_process_identity_refused(self):
        f=previous.Fixture()
        legacy=old.envelope(old.Snapshot,'Snapshot',f.nonce)
        f.provider.runtime_snapshot=lambda:legacy
        with self.assertRaises(ValueError):f.provider.observe(f.node)
        f=previous.Fixture();f.birth+=1
        with self.assertRaises(ValueError):f.provider.observe(f.node)
        f=previous.Fixture();raw=bytearray(bytes(f.plans));raw[:4]=old.MAGIC.to_bytes(4,'little')
        changed=wire.Plans.from_buffer_copy(raw)
        with self.assertRaises(ValueError):observed.AObservedBoundary(f.reader,pid=f.reader.pid,birth=f.birth,
            base=f.reader.memory.base,root=f.reader.root,world_address=f.reader.world,cache=f.cache,force=12,ruler=666,
            nonce=f.nonce,plans=changed,read_birth=lambda:f.birth,runtime_snapshot=f.snapshot,no_new_commands=True)

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def pins():
    paths={Path(m.__file__).resolve() for m in list(sys.modules.values()) if getattr(m,'__file__',None)}|{Path(__file__).resolve()}
    return {str(p):sha(p) for p in sorted(paths) if p.is_relative_to(ROOT) and p.suffix=='.py'}
def main():
    output=PRIVATE/'a_observed_three_boundary_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');output.mkdir(parents=True)
    previous.OUTPUT=output;before=pins();stream=io.StringIO()
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Cases))
    (output/'test.log').write_text(stream.getvalue(),encoding='utf-8');sources=pins();stable=all(sources.get(k)==v for k,v in before.items())
    report=dict(result='PASS' if result.wasSuccessful() and result.testsRun==11 and stable else 'FAIL',tests=result.testsRun,
        sources=sources,inputs_unchanged=stable,game_access=False,native_execution=False,fake_ram=True,fake_runtime=True,
        archive_snapshot_decode_only=False,production_permission=False,failures=[(str(t),d) for t,d in result.failures+result.errors])
    report['artifacts']={str(p):sha(p) for p in output.iterdir() if p.is_file()}
    path=output/'result.json';path.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(result=report['result'],path=str(path),sha256=sha(path))));print(stream.getvalue())
    return int(report['result']!='PASS')
if __name__=='__main__':raise SystemExit(main())
