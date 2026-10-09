"""Refresh launcher tests: owned Windows files and explicit native/RAM doubles."""
from contextlib import redirect_stdout
from datetime import datetime
import ctypes as C
import hashlib
import io
import json
from pathlib import Path
import struct
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];PRIVATE=ROOT.parent/'mod_research'
sys.path[:0]=[str(PRIVATE/'python_deps'),str(ROOT/'outputs/san14-link')]
import b_warm_refresh_start_support as support
import b_warm_refresh_coordinator as coordinator
import b_warm_refresh_diagnostic as entry
import b_warm_refresh_contract as wire
import b_warm_profile_contract as warm
from b_warm_profile_capture import profile_from_dict
import b_warm_staging as files
import b_warm_start_support as old_support
import checkpoint_complete_live_capture as capture
import a_save_local_binding as binding
import game_reader,pefile
import run_autonomous_pilot,checkpoint_live_prefetch_start,a_save_runtime_control,b_warm_start_acceptance

OUTPUT=None

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


class PortDouble:
    """Native substitute writes actual target; never claims to execute Steam."""
    def __init__(self,case,fail=None):self.case=case;self.fail=fail;self.events=[];self.current=None;self.aborted=[]
    def open_bank(self,index):self.events.append(('open',index));return dict(index=index)
    def authorize_second(self,bank,p):self.case.assertEqual(self.events[-2],('retired',0));self.events.append(('authorize',1))
    def load(self,bank,profile,raw,*,target,previous,backup):
        self.current=bank;index=bank['index'];self.events.append(('load',index))
        self.case.assertEqual(files.read_file(target)[0],previous)
        self.case.assertEqual(backup.read_bytes(),target.read_bytes())
        if index==self.fail:raise RuntimeError('explicit native failure')
        # Real Windows write must succeed: a stale outer deny-write target lease
        # would make this raise PermissionError.
        with target.open('wb') as out:out.write(raw)
        bank['retired']=True;self.events.append(('retired',index))
        return dict(native_substitute=True,index=index,retired=True)
    def abort(self):self.aborted.append(self.current['index'])
    def finish(self):self.events.append(('finish',2))


class Cases(unittest.TestCase):
    def setUp(self):
        self.folder=OUTPUT/self._testMethodName;self.folder.mkdir()
        self.target=self.folder/files.NAME;self.target.write_bytes(b'old-native-and-physical'*37)
        self.sources=[self.folder/'first-received.s14',self.folder/'second-received.s14']
        for i,p in enumerate(self.sources):p.write_bytes(bytes([40+i])*(901+i*37))
        def profile(p,before,loaded,current):return dict(file=dict(name=files.NAME,slot=63,size=p.stat().st_size,sha256=sha(p)),
            before=dict(year=203,month=8,day=before),loaded=dict(year=203,month=8,day=loaded),
            source=dict(ruler=666,force=12,district=11),target=dict(ruler=952,force=2,district=2),currentForce=current)
        self.raw_profiles=[profile(self.sources[0],11,11,12),profile(self.sources[1],11,21,2)]
        self.profiles=[profile_from_dict(p) for p in self.raw_profiles]
        self.initial=files.read_file(self.target)[0]
        self.plan=dict(profiles=self.raw_profiles,target=str(self.target),sources=[str(p) for p in self.sources],
            initial_target=self.initial,expected_ruler=666,steam_paths={})
        for name in support.STEAM_HASHES:
            p=self.folder/name;p.write_bytes(b'owned fake PE for hash-only preflight '+name.encode());self.plan['steam_paths'][name]=str(p)
        self.steam_hashes={n:sha(p) for n,p in self.plan['steam_paths'].items()}
        self.planpath=self.folder/'plan.json';self.planpath.write_text(json.dumps(self.plan))
        shared=self.folder/'owned-native.cpp';shared.write_text('// explicit owned manifest test source\n')
        self.builds={}
        for name,family in [('helper','san14.b-warm-coordinator.v1'),('pair',support.FAMILY)]:
            d=self.folder/name;d.mkdir();dll=d/'owned.dll';dll.write_bytes(b'explicit non-executable manifest fixture '+name.encode())
            gen=d/'build.txt';gen.write_text('owned manifest data, no production image')
            record=dict(family=family,result='PASS',inputs_unchanged=True,refresh_factory_pair_passed=True,
                sources={str(shared):sha(shared)},generated={str(gen):sha(gen)},binaries={str(dll):sha(dll)},
                production_dll=dict(path=str(dll),sha256=sha(dll)))
            result=d/'result.json';result.write_text(json.dumps(record));self.builds[name]=result
        self.args={k:v for name,p in self.builds.items() for k,v in [(name+'_build',p),(name+'_sha256',sha(p))]}

    def check(self):
        with patch.object(support,'STEAM_HASHES',self.steam_hashes):return support.preflight(self.planpath,**self.args)

    def test_two_files_target_untouched_until_native_and_backup_per_generation(self):
        out=self.folder/'run';out.mkdir();port=PortDouble(self)
        with patch.object(files,'apply',side_effect=AssertionError('physical staging is forbidden')):
            r=coordinator.run_two(port,self.profiles,self.target,self.sources,self.initial,out)
        self.assertEqual(r['result'],'PASS_TWO_WARM_REFRESH_LOADS');self.assertFalse(r['target_written_by_python'])
        self.assertEqual((out/'bank-1-old-target.s14').read_bytes(),b'old-native-and-physical'*37)
        self.assertEqual((out/'bank-2-old-target.s14').read_bytes(),self.sources[0].read_bytes())
        self.assertEqual(self.target.read_bytes(),self.sources[1].read_bytes());self.assertEqual(port.aborted,[])

    def test_changed_old_target_refuses_before_any_bank(self):
        self.target.write_bytes(b'drift');port=PortDouble(self);out=self.folder/'run';out.mkdir()
        with self.assertRaisesRegex(ValueError,'Old target changed'):
            coordinator.run_two(port,self.profiles,self.target,self.sources,self.initial,out)
        self.assertEqual(port.events,[])

    def test_failed_second_preserves_first_and_only_aborts_current(self):
        port=PortDouble(self,fail=1);out=self.folder/'run';out.mkdir()
        with self.assertRaisesRegex(RuntimeError,'explicit native'):
            coordinator.run_two(port,self.profiles,self.target,self.sources,self.initial,out)
        self.assertEqual(port.aborted,[1]);self.assertEqual(self.target.read_bytes(),self.sources[0].read_bytes())
        self.assertNotIn(('finish',2),port.events)

    def config(self):
        w=warm.Config();w.profile=self.profiles[0];w.owner.attempt=17;w.owner.epoch=29;w.owner.generation=31;w.owner.vtableModuleIndex=1
        source=self.folder/'private';source.mkdir();p=source/files.NAME;p.write_bytes(self.sources[0].read_bytes());w.owner.localPath=str(p)
        for name in ('installIntent','requestIntent','identityIntent'):setattr(w.owner,name,str(source/(name+'.intent')))
        b=self.folder/'backup.s14';b.write_bytes(self.target.read_bytes())
        return support.make_config(w,write=dict(address=0x180001000,moduleIndex=1,first32='90'*32),previous=self.initial,
            source_identity=files.read_file(p)[0],target_path=self.target,backup_path=b,refresh_intent=source/'refresh.intent')

    def test_config_exact_identity_and_retired_refresh_receipt(self):
        config=self.config();self.assertEqual(config.previousTargetIdentity.lastWriteLow,self.initial['file_id'][6])
        self.assertEqual(config.previousTargetIdentity.lastWriteHigh,self.initial['file_id'][5])
        r=wire.Report();r.magic=wire.MAGIC;r.size=C.sizeof(r);r.version=1
        for n in ('captured','executeCalls','writeAttempts','writeReturned','intentCreated','intentDurable','matched','leaseReleased','releaseCalls'):setattr(r,n,1)
        r.state=4;r.previousReads=r.newReads=2;r.attempt=17;r.epoch=29;r.generation=31
        r.previousSize=config.previousSize;r.newSize=config.warm.profile.file.size
        r.previousSha256[:]=config.previousSha256;r.newSha256[:]=config.warm.profile.file.sha256;r.stage=b'released_after_native_retirement'
        self.assertTrue(support.validate_completed(bytes(r),config)['leaseReleased'])
        for field,value in [('leaseHeld',1),('leaseReleased',0),('writeAttempts',2),('osError',5),('generation',32),('newSize',r.newSize+1)]:
            altered=wire.Report.from_buffer_copy(bytes(r));setattr(altered,field,value)
            with self.assertRaises(ValueError):support.validate_completed(bytes(altered),config)
        altered=wire.Report.from_buffer_copy(bytes(r));altered.newSha256[0]^=1
        with self.assertRaises(ValueError):support.validate_completed(bytes(altered),config)

    def test_filewrite_exact_pe_rx_and_stable_slot(self):
        base,vt,fn=0x180000000,0x180002000,0x180003000
        binding_value=dict(storageVtable=vt,vtableModuleIndex=0,storageModules=[dict(base=base,sizeOfImage=0x10000,path='owned.dll')])
        reader=SimpleNamespace(memory=SimpleNamespace(read=lambda a,n:struct.pack('<Q',fn) if a==vt else b'\x90'*n))
        fake=SimpleNamespace(get_data=lambda a,n:b'\x90'*n,close=lambda:None)
        with patch.object(old_support,'storage_bindings',return_value=binding_value),patch.object(pefile,'PE',return_value=fake),patch.object(capture,'readable',return_value=None) as rx:
            r=support.storage_bindings(reader,[]);self.assertEqual(r['write']['address'],fn);rx.assert_called_once_with(reader,fn,32,allocation=base,execute=True)
            reader.memory.read=lambda a,n:struct.pack('<Q',fn) if a==vt else b'\x91'*n
            with self.assertRaisesRegex(ValueError,'pinned PE'):support.storage_bindings(reader,[])
            reader.memory.read=lambda a,n:struct.pack('<Q',base+0x20000) if a==vt else b'\x90'*n
            with self.assertRaisesRegex(ValueError,'outside'):support.storage_bindings(reader,[])

    def test_local_preflight_uses_old_target_and_two_independent_sources(self):
        before={str(p):sha(p) for p in self.folder.rglob('*') if p.is_file()}
        r=self.check();self.assertEqual(r['normalized_plan'],self.plan)
        self.assertEqual(before,{str(p):sha(p) for p in self.folder.rglob('*') if p.is_file()})
        pair=self.builds['pair'];v=json.loads(pair.read_text());v['family']='san14.b-warm-factory-pair.v1';pair.write_text(json.dumps(v));self.args['pair_sha256']=sha(pair)
        with self.assertRaisesRegex(ValueError,'Matching successful'):self.check()

    def test_noop_cli_and_readonly_check_never_open_native_owner_or_claim(self):
        with patch.object(entry,'DiagnosticResident',side_effect=AssertionError('no native owner')) as resident,redirect_stdout(io.StringIO()):
            self.assertEqual(entry.main([]),0)
            reader=SimpleNamespace(pid=123,close=lambda:None)
            planning=dict(birth=55)
            cli=['--check','--pid','123','--plan',str(self.planpath)]
            for name in ('helper','pair'):cli+=['--'+name+'-build',str(self.args[name+'_build']),'--'+name+'-sha256',self.args[name+'_sha256']]
            with patch.object(support,'STEAM_HASHES',self.steam_hashes),patch.object(game_reader,'GameReader',return_value=reader),patch.object(capture,'process_birth',return_value=55),patch.object(entry,'capture_planning',return_value=planning),patch.object(entry,'refuse_prior_attempt'),patch.object(entry,'require_original_rules',return_value={'six_sources_original':True}),patch.object(entry,'require_no_debugger'),patch.object(binding,'modules',return_value=[]),patch.object(support,'storage_bindings',return_value={'explicit_double':True}),patch.object(entry,'PRIVATE',self.folder):
                reader.memory=SimpleNamespace(handle=1)
                self.assertEqual(entry.main(cli),0)
            resident.assert_not_called();self.assertFalse((self.folder/'b_warm_start_claims').exists())

    def test_retired_bank_abort_is_noop_unfinished_delegates(self):
        r=coordinator.Resident.__new__(coordinator.Resident);r.current={'warm_load_retired':True}
        with patch.object(coordinator.PreviousResident,'abort') as abort:
            r.abort();abort.assert_not_called();r.current={'install_completed':True};r.abort();abort.assert_called_once()

    def test_per_sample_refresh_failure_saved_without_replay_or_masking_native_error(self):
        report=wire.Report();report.magic=wire.MAGIC;report.size=C.sizeof(report);report.version=1
        report.state=5;report.error=3;report.firstFailure=b'native_size_before';report.osError=17
        bank=dict(folder=self.folder,addresses={'GetBWarmRefreshReport':123})
        calls=SimpleNamespace(uncertain=False,call=lambda *a,**k:(0,bytes(report)))
        trace=[];native=dict(SessionError=7)
        coordinator.record_observation(calls,bank,{'original':b'original native bytes'},native,trace)
        self.assertEqual(trace[0]['refresh_diagnostic']['firstFailure'],'native_size_before')
        self.assertEqual((self.folder/'0000-GetBWarmRefreshReport.bin').read_bytes(),bytes(report))
        self.assertEqual(native,dict(SessionError=7))
        # Known snapshot failure does not hide the original SessionError; the
        # unchanged completion function will raise that original native failure.
        calls.call=lambda *a,**k:(1,None)
        coordinator.record_observation(calls,bank,{},native,trace)
        self.assertIn('snapshot_error',trace[1]['refresh_diagnostic'])
        calls.uncertain=True;calls.call=lambda *a,**k:(_ for _ in ()).throw(AssertionError('No call after uncertain'))
        with self.assertRaisesRegex(RuntimeError,'control uncertain'):
            coordinator.record_observation(calls,bank,{},native,trace)
        self.assertEqual(len(trace),3)


def main():
    global OUTPUT
    OUTPUT=PRIVATE/'b_warm_refresh_python_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');OUTPUT.mkdir(parents=True)
    names={Path(m.__file__).resolve() for m in tuple(sys.modules.values()) if getattr(m,'__file__',None) and str(Path(m.__file__).resolve()).startswith(str(ROOT)) and str(m.__file__).endswith('.py')}
    names.add(Path(__file__).resolve());pins={str(p):sha(p) for p in names}
    stream=io.StringIO();result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Cases))
    (OUTPUT/'tests.log').write_text(stream.getvalue(),encoding='utf-8')
    report=dict(result='PASS' if result.wasSuccessful() and all(sha(p)==h for p,h in pins.items()) else 'FAIL',tests=result.testsRun,
        sources=pins,inputs_unchanged=all(sha(p)==h for p,h in pins.items()),game_process_access=False,steam_access=False,
        native_RAM_build_approval_fixtures_are_explicit_doubles=True,
        artifacts={str(p):sha(p) for p in OUTPUT.rglob('*') if p.is_file()})
    path=OUTPUT/'result.json';path.write_text(json.dumps(report,indent=2)+'\n');print(stream.getvalue());print(json.dumps(dict(result=report['result'],path=str(path),sha256=sha(path))))
    return report['result']!='PASS'

if __name__=='__main__':raise SystemExit(main())
