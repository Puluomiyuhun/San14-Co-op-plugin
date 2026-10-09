"""Actual Windows files and rule lifecycle; native publisher/load are doubles."""
from datetime import datetime
import ctypes as C
import hashlib
import io
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];PRIVATE=ROOT.parent/'mod_research'
sys.path[:0]=[str(PRIVATE/'python_deps'),str(ROOT/'outputs/san14-link')]
from b_warm_bootstrap_test import NativeRulesDouble,writer_blocked
from b_warm_profile_contract import Profile,Date,Identity
from b_warm_refresh_bootstrap import BootstrapRulesBridge
from b_warm_refresh_rules_bridge import WarmRulesBridge
from human_rules_world_lifecycle import Config,WorldGeneration,WorldLifecycle,NextWorldRequest
import b_warm_staging as files

OUTPUT=None

def sha(raw):return hashlib.sha256(raw).hexdigest()


class WarmRefreshDouble:
    """Explicit native substitute; real Windows write detects an outer target lock."""
    def __init__(self,rules,target,case='normal'):
        self.rules,self.target,self.case=rules,target,case;self.reader=SimpleNamespace(pid=rules.pid)
        self.events=[];self.request=None;self.source=None;self.current=None;self.abort_source_held=None
    def open_bank(self,index):self.events.append(['open',index]);return index
    def authorize_second(self,bank,profile):
        self.events.append(['handover',bank])
        if self.case=='handover-failed':raise ValueError('Explicit handover rejection')
    def load(self,bank,p,raw,*,target,previous,backup):
        self.current=bank;self.events.append(['load',bank,p.currentForce,p.target.force])
        assert target==self.target and self.rules.events[-1][0]=='restore'
        assert files.read_file(target)[0]==previous and backup.read_bytes()==target.read_bytes()
        assert not writer_blocked(target)
        if self.source is not None:assert writer_blocked(self.source)
        assert sha(raw)==bytes(p.file.sha256).hex()
        with target.open('wb') as out:out.write(raw)
        req=self.request;self.rules.current=self.rules.config(req.generation,req.day,p.target.force,req.epoch)
        if self.case=='load-failed':raise RuntimeError('Explicit native failure after publication')
        accepted=dict(result='PASS_WARM_LOAD_RETIRED',receipt_key=str(bank+1)*64,
            source_force=p.source.force,source_ruler=p.source.ruler,target_force=p.target.force,target_ruler=p.target.ruler,
            ready_authorized=False,full_world_verified=False,input_exclusion_proven=False)
        refresh=dict(state=4,error=0,captured=1,executeCalls=1,writeAttempts=1,writeReturned=1,
            intentCreated=1,intentDurable=1,matched=1,leaseHeld=0,leaseReleased=1,releaseCalls=1,
            previousReads=2,newReads=2,osError=0,exceptionCode=0,attempt=bank+1,generation=bank+1,epoch=17+bank,
            previous_size=previous['size'],previous_sha256=previous['sha256'],new_size=len(raw),new_sha256=sha(raw),
            stage='released_after_native_retirement')
        if self.case=='receipt-held':refresh['leaseHeld']=1;refresh['leaseReleased']=0
        if self.case=='receipt-wrong-old':refresh['previous_sha256']='0'*64
        return dict(accepted=accepted,refresh=refresh,attempt=bank+1,pid=self.rules.pid,birth=self.rules.birth,
            profile_sha256=sha(bytes(p)),slots_restored=True,target_lease_released=True,
            snapshot=dict(date=dict(year=p.loaded.year,month=p.loaded.month,day=p.loaded.day),
                player=dict(force_id=p.target.force,ruler_id=p.target.ruler)))
    def abort(self):
        self.events.append(['abort',self.current]);self.abort_source_held=writer_blocked(self.source) if self.source else None
        assert not writer_blocked(self.target)


def fixture(folder,case='normal'):
    folder.mkdir();directory=folder/'slot';directory.mkdir();target=directory/files.NAME
    original=b'old physical and native CC03'*37;target.write_bytes(original)
    sources=[]
    for i in (1,2):
        p=folder/f'received-{i}.s14';p.write_bytes(bytes([i])*(801+i));sources.append(p)
    records=folder/'records';records.mkdir();rules=NativeRulesDouble()
    old=rules.prepare(WorldGeneration(1,'1'*64,bytes(rules.current)));old.install()
    holds=[];life=WorldLifecycle(old,guard_check=lambda:None,on_hold=lambda reason:holds.append(reason))
    warm=WarmRefreshDouble(rules,target,case);bridge=BootstrapRulesBridge(life,warm,target=target,records=records)
    return SimpleNamespace(folder=folder,target=target,original=original,sources=sources,records=records,
        rules=rules,life=life,warm=warm,bridge=bridge,holds=holds)


def apply(f,index,wrong_current=False):
    req=NextWorldRequest(index+1,str(index+1)*64,bytes([index+0x50])*16,203,8,11 if index==1 else 21)
    p=Profile();p.file.name=files.NAME.encode();p.file.slot=63;raw=f.sources[index-1].read_bytes()
    p.file.size=len(raw);p.file.sha256[:]=bytes.fromhex(sha(raw));p.before=Date(203,8,1 if index==1 else 11)
    p.loaded=Date(req.year,req.month,req.day);p.source=Identity(666,12,11);p.target=Identity(952,2,2)
    p.currentForce=(2 if index==1 else 12) if wrong_current else (12 if index==1 else 2)
    f.warm.request=req;f.warm.source=f.sources[index-1]
    return f.bridge.replace(req,p,f.sources[index-1],observe_loaded=f.rules.observe,prepare_rules=f.rules.prepare)


class Cases(unittest.TestCase):
    def create(self,case):return fixture(OUTPUT/self._testMethodName,case)
    def test_bootstrap_then_regular_two_generations_no_physical_stage(self):
        f=self.create('normal')
        with patch.object(files,'apply',side_effect=AssertionError('physical stage prohibited')):
            one=apply(f,1);two=apply(f,2)
        self.assertTrue(one['bootstrap']);self.assertFalse(two['ready']);self.assertEqual(f.bridge.phase,'ACTIVE')
        self.assertEqual(Config.from_buffer_copy(f.life.current.world.config).viewer,2)
        self.assertEqual([e[0] for e in f.rules.events],['install','restore','observe','install','restore','observe','install'])
        self.assertEqual(f.warm.events,[['open',0],['load',0,12,2],['open',1],['handover',1],['load',1,2,2]])
        self.assertEqual((f.records/'generation-2/previous-target.s14').read_bytes(),f.original)
        self.assertEqual((f.records/'generation-3/previous-target.s14').read_bytes(),f.sources[0].read_bytes())
        self.assertEqual(f.target.read_bytes(),f.sources[1].read_bytes());self.assertEqual(len(f.life.retained),3)

    def test_wrong_bootstrap_viewer_never_calls_warm(self):
        f=self.create('normal')
        with self.assertRaises(Exception):apply(f,1,wrong_current=True)
        self.assertFalse(f.warm.events);self.assertEqual(f.target.read_bytes(),f.original)
        self.assertEqual(f.bridge.phase,'HELD');self.assertTrue(f.holds)

    def test_initial_target_changed_refuses_before_bank_and_holds(self):
        f=self.create('normal');f.target.write_bytes(b'foreign target modification')
        with self.assertRaisesRegex(files.Refused,'identity changed'):apply(f,1)
        self.assertFalse(f.warm.events);self.assertEqual(f.life.phase,'HELD')

    def test_native_failure_keeps_backup_no_new_rules_no_retry(self):
        f=self.create('load-failed')
        with self.assertRaisesRegex(RuntimeError,'native failure'):apply(f,1)
        self.assertTrue(f.warm.abort_source_held);self.assertEqual(len(f.rules.ports),1)
        self.assertEqual(f.life.phase,'HELD');self.assertTrue((f.records/'generation-2/previous-target.s14').is_file())
        events=list(f.warm.events)
        with self.assertRaises(Exception):apply(f,1)
        self.assertEqual(f.warm.events,events);self.assertEqual(f.target.read_bytes(),f.sources[0].read_bytes())

    def test_second_handover_failure_preserves_first_and_stays_held(self):
        f=self.create('handover-failed');apply(f,1)
        with self.assertRaisesRegex(ValueError,'handover rejection'):apply(f,2)
        self.assertEqual(f.target.read_bytes(),f.sources[0].read_bytes());self.assertEqual(len(f.bridge.completed),1)
        self.assertEqual(len(f.rules.ports),2);self.assertEqual(f.life.phase,'HELD')
        events=list(f.warm.events)
        with self.assertRaises(Exception):apply(f,2)
        self.assertEqual(events,f.warm.events)

    def test_invalid_refresh_receipt_blocks_rules_reinstall(self):
        for case in ('receipt-held','receipt-wrong-old'):
            f=fixture(OUTPUT/(self._testMethodName+'-'+case),case)
            with self.assertRaises(files.Refused):apply(f,1)
            self.assertEqual(len(f.rules.ports),1);self.assertEqual(f.life.phase,'HELD')
            self.assertFalse(f.bridge.completed)


def file_sha(p):return sha(Path(p).read_bytes())


def main():
    global OUTPUT
    OUTPUT=PRIVATE/'b_warm_refresh_rules_bridge_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');OUTPUT.mkdir(parents=True)
    names={Path(m.__file__).resolve() for m in tuple(sys.modules.values()) if getattr(m,'__file__',None)
        and Path(m.__file__).resolve().is_relative_to(ROOT) and str(m.__file__).endswith('.py')}
    names.add(Path(__file__).resolve());pins={str(p):file_sha(p) for p in names}
    stream=io.StringIO();result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Cases))
    (OUTPUT/'tests.log').write_text(stream.getvalue());unchanged=all(file_sha(p)==h for p,h in pins.items())
    report=dict(result='PASS' if result.wasSuccessful() and unchanged else 'FAIL',tests=result.testsRun,sources=pins,
        inputs_unchanged=unchanged,game_process_access=False,steam_access=False,actual_windows_files=True,
        actual_resident_port_world_lifecycle=True,native_memory_publisher_loader='EXPLICIT_DOUBLES',input_guard='EXPLICIT_TEST_NOOP',
        artifacts={str(p):file_sha(p) for p in OUTPUT.rglob('*') if p.is_file()})
    path=OUTPUT/'result.json';path.write_text(json.dumps(report,indent=2)+'\n');print(stream.getvalue());print(json.dumps(dict(result=report['result'],path=str(path),sha256=file_sha(path))))
    return report['result']!='PASS'

if __name__=='__main__':raise SystemExit(main())
