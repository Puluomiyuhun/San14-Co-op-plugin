"""Real samplers on owned bytes plus explicitly synthetic event records."""
from copy import deepcopy
from datetime import datetime
import hashlib,io,json,sys,unittest
from pathlib import Path
import reward_result_evidence as evidence
import reward_result_delta
from reward_observed_fixture import World

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];PRIVATE=ROOT.parent/'mod_research'

def sample(world,start):
    ticks=iter((start,start+1))
    return evidence.capture(world.reader,[12,2],actor=world.viewer,read_birth=lambda:world.birth,
        read_clock=lambda:dict(counter=next(ticks),frequency=10000000))

def fixture():
    world=World(12);before=sample(world,10)
    world.execute(evidence.watch.reward.make_command(evidence.watch.reward.capture_context(world.reader,12),11,[97]))
    world.memory.pack(world.world+0x80,'<I',1)
    after=sample(world,30);i=before['sample']['identity']
    metadata={k:i[k] for k in ('pid','birth','base')};metadata.update(run_id='synthetic-owned-case',capture_complete=True,capture_errors=[])
    preview=dict(kind='reward',force_id=12,district_id=11,funding_city_id=19,officer_ids=[97])
    rows=[]
    for n,(name,rva) in enumerate((('wrapper_call',0x67A993),('common_call',0x626275),('common_return',0x62627A),('wrapper_return',0x67A998)),1):
        rows.append(dict(seq=n,event=name,rva=rva,thread=123,rsp=0x10000 if name.startswith('wrapper') else 0x10000-0x890,
            state=0x20000,root=i['root'],world=i['world'],viewer=12,date=[203,8,11],ui_event_code_raw=2,
            eax=7 if name=='common_return' else 99,preview=deepcopy(preview),counter=20+n,
            pid=i['pid'],birth=i['birth'],base=i['base'],run_id=metadata['run_id'],lost_events=0))
    return before,after,rows,metadata

class Tests(unittest.TestCase):
    def test_bounded_before_return_after_with_raw_result_only(self):
        args=fixture();r=evidence.correlate(*args)
        self.assertEqual(r['native_return_raw'],7);self.assertEqual(r['wrapper_result_raw'],99)
        self.assertTrue(r['samples_enclose_trace']);self.assertTrue(r['business_return_paired'])
        self.assertEqual(r['auxiliary_changes'],{'world_80_u32':{'before':0,'after':1}})
        self.assertFalse(r['native_return_success_verified']);self.assertFalse(r['network_submission_allowed'])
        self.assertFalse(r['exclusive_business_attribution']);self.assertFalse(r['full_reward_effects_verified'])
        self.assertEqual(evidence.correlate(*json.loads(json.dumps(args))),r)
    def test_zero_business_return_not_mistaken_for_success(self):
        args=fixture();args[2][2]['eax']=0;r=evidence.correlate(*args)
        self.assertEqual(r['native_return_raw'],0);self.assertFalse(r['native_return_success_verified'])
    def test_sample_intervals_must_enclose_events(self):
        for target,key,value in ((0,'end',22),(1,'begin',23)):
            args=fixture();args[target][key]['counter']=value
            with self.assertRaisesRegex(ValueError,'enclose'):evidence.correlate(*args)
    def test_trace_different_process_or_native_selection_rejected(self):
        for mode in ('birth','selection','city','world'):
            args=fixture();rows,metadata=args[2:]
            for row in rows:
                if mode=='birth':row['birth']+=1
                elif mode=='selection':row['preview']['officer_ids']=[666]
                elif mode=='city':row['preview']['funding_city_id']=13
                else:row['world']+=8
            if mode=='birth':metadata['birth']+=1
            with self.assertRaises(ValueError):evidence.correlate(*args)
    def test_incomplete_cleanup_or_lost_trace_rejected(self):
        for mode in ('incomplete','missingreturn','lost','secondpair'):
            args=fixture();rows,metadata=args[2:]
            if mode=='incomplete':metadata['capture_complete']=False
            elif mode=='missingreturn':rows.pop(2)
            elif mode=='lost':rows[2]['lost_events']=1
            else:
                tail=deepcopy(rows)
                for row in tail:row['seq']+=4;row['counter']+=4
                rows.extend(tail)
            with self.assertRaisesRegex(ValueError,'Exactly one'):evidence.correlate(*args)
    def test_correct_signed_byte_and_unequal_clocks(self):
        world=World(12);world.memory.pack(world.world+0xBC,'<I',0x123456ff)
        result=sample(world,10)
        self.assertEqual(result['counters']['fields']['world_bc_i8'],-1)
        self.assertNotEqual(result['sample']['auxiliary']['world_bc_i32'],-1)
        args=fixture();args[1]['begin']['frequency']=args[1]['end']['frequency']=99
        with self.assertRaisesRegex(ValueError,'enclose'):evidence.correlate(*args)

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def sources():
    paths={Path(__file__).resolve()}
    for m in list(sys.modules.values()):
        f=getattr(m,'__file__',None)
        if f:
            p=Path(f).resolve()
            if p.suffix=='.py' and ROOT in p.parents:paths.add(p)
    return {str(p):sha(p) for p in sorted(paths)}
if __name__=='__main__':
    folder=PRIVATE/'reward_result_evidence_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');folder.mkdir(parents=True)
    pins=sources();stream=io.StringIO();r=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
    (folder/'tests.log').write_text(stream.getvalue(),encoding='utf-8');stable=pins==sources()
    result=dict(result='PASS' if r.wasSuccessful() and stable else 'FAIL',tests=r.testsRun,sources=pins,inputs_unchanged=stable,
        game_access=False,native_business_executed=False,synthetic_trace=True,actual_readers_on_owned_bytes=True,
        artifacts={'tests.log':sha(folder/'tests.log')},**evidence.FLAGS)
    (folder/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(stream.getvalue());print(folder/'result.json');raise SystemExit(result['result']!='PASS')
