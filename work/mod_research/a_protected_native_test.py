"""Actual retained Python factory + remote Prepare/Seal + external publisher.
Only owned host processes; archived mapped image/business data are fixture.
"""
from datetime import datetime
from pathlib import Path
import ctypes as C
from ctypes import wintypes as W
import hashlib,json,os,queue,shutil,struct,subprocess,sys,threading

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];PRIVATE=ROOT.parent/'mod_research'
sys.path[:0]=[str(PRIVATE/'python_deps'),str(ROOT/'outputs/san14-link')]
from b_warm_rules_factory import RulesFactory,RulesBuild
from b_warm_rules_capture import RulesWorldCapture
from b_warm_rules_bridge_test import prepare_build,PRIOR,PRIOR_SHA
from human_rules_activation_publish_v2_counter_profile import generate
from b_warm_start_support import open_process_api
from checkpoint_push_start import process_birth
from human_rules_world_lifecycle import NextWorldRequest,Config
from human_rules_activation_room import rules,GAME_SHA
from b_warm_room import WarmRoom
from checkpoint_fresh_save_binding_test import manifest,select_direct
from room_session import digest
import pefile
from unittest.mock import patch
import b_warm_rules_factory as factory_module


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def pins():
    paths={Path(m.__file__).resolve() for m in list(sys.modules.values()) if getattr(m,'__file__',None)}
    paths.add(Path(__file__).resolve())
    paths.update(HERE/n for n in ('a_protected_fixture.inc','human_rules_world_lifecycle_fixture.cpp','human_rules_activation_publish_v2.cpp','human_rules_activation_publish_v2_config.h'))
    return {str(p):sha(p) for p in sorted(paths) if p.is_relative_to(ROOT) and p.suffix in ('.py','.inc','.cpp','.h')}


def build(run):
    sources=prepare_build(run);inputs=run/'inputs'
    # Validate actual copied headers used by this compiler against frozen pins.
    for name,wanted in json.loads((PRIOR/'result.json').read_text())['source_sha256'].items():
        assert sha(PRIOR/'src'/name)==wanted,name
    original=HERE/'human_rules_world_lifecycle_fixture.cpp'
    text=original.read_text();at=text.index(' Instance first=prepareInstance')
    host=run/'host.cpp';host.write_text(text[:at]+(HERE/'a_protected_fixture.inc').read_text(encoding='utf-8-sig'))
    # Frozen includes are copied by the predecessor and also independently pinned.
    include=PRIOR/'src/work/mod_research';private=PRIOR/'src/private'
    vc=r'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat'
    flags=f'/nologo /std:c++17 /EHa /W4 /WX /O2 /MT /I"{run}" /I"{include}" /I"{private}" /I"{PRIOR/"src/outputs/san14-link"}"'
    def execute(label,cmd):
        script=run/f'build-{label}.cmd';script.write_text('@echo off\ncall "'+vc+'" >nul\nif errorlevel 1 exit /b 1\n'+cmd+'\n')
        p=subprocess.run(['cmd','/d','/c',str(script)],cwd=run,capture_output=True,timeout=60)
        (run/f'build-{label}.log').write_bytes(p.stdout+p.stderr)
        assert p.returncode==0,(label,p.stdout.decode(errors='replace'))
    execute('host',f'cl {flags} "{host}" /Fe:"{inputs/"factory-host.exe"}"')
    profile=generate(inputs/'first.dll',run/'human_rules_activation_publish_v2_fixture_counters.h')
    (run/'human_rules_activation_publish_v2_fixture_hashes.h').write_text('#pragma once\nconstexpr unsigned ExpectedFixture=1;\n'+
        'constexpr const char* ApprovedExeSha="'+sha(inputs/'factory-host.exe')+'";\n'+
        'constexpr const char* ApprovedStageSha="'+sha(inputs/'first.dll')+'";\n'+
        'constexpr const char* ApprovedImageSha="'+sha(inputs/'owned_rules_image.dll')+'";\n')
    # Quote-includes search the including file first: copy publisher/config to
    # this run so its fixture headers resolve to our new exact host fingerprint.
    for n in ('human_rules_activation_publish_v2.cpp','human_rules_activation_publish_v2_config.h'):
        shutil.copyfile(HERE/n,run/n)
    cmd=f'cl {flags} /DHUMAN_RULES_ACTIVATION_PUBLISH_FIXTURE '+ ' '.join('"'+str(p)+'"' for p in
        (run/'human_rules_activation_publish_v2.cpp',include/'human_ai_runtime_subject.cpp',include/'human_ai_group_resolver.cpp'))
    execute('publisher',cmd+f' /Fe:"{inputs/"factory-publisher.exe"}"')
    return sources,inputs,profile


from b_warm_rules_factory_test import Owned,Reader as BaseReader
from types import SimpleNamespace
from a_protected_rules import ProtectedRulesOwner
from a_observed_boundary import AObservedBoundary,SLOTS,INLINE
from a_observed_room import ObservedRoom
from a_room_bootstrap_protocol import BootstrapCoordinator
from authoritative_sync import scope_from_room
import a_save_runtime_contract as wire
import b_warm_world as world

class Reader(BaseReader):
    def require_type(self,at,name):
        if (name,at) in self.state_objects():return
        if name=='CForceData':assert self.pointer(at)==self.memory.base+0x129FE58;return
        return super().require_type(at,name)


def exercise(run,inputs,profile,name,active_case=False):
    own=Owned(run,inputs,name);own.reader.__class__=Reader;protection=None
    try:
        reader=own.reader;b=reader.memory.base;birth=process_birth(reader);nonce=b'\x31'*32
        setting=rules(1,0);catalog=manifest();catalog['profile']['game_sha256']=GAME_SHA;catalog['profile']['rules_sha256']=digest(setting)
        room=ObservedRoom(catalog);select_direct(room)
        node=dict(year=203,month=8,day=11,phase='PLANNING_BOUNDARY')
        c=BootstrapCoordinator(scope_from_room(room),world.CONTRACT,'d'*64,{'A':'a'*32,'B':'b'*32},node);room.bind_coordinator(c)
        plans=wire.envelope(wire.Plans,'Plans',nonce);plans.pid,plans.birth,plans.base,plans.module=reader.pid,birth,b,0x79000000
        for p,(slot,original) in zip(plans.slots,SLOTS):p.address=b+slot;p.original=b+original;p.hook=reader.pointer(p.address)
        archive=(inputs/'game-runtime-image.bin').read_bytes()
        for p,rva in zip(plans.inlines,INLINE):
            p.address=b+rva;p.size=5;p.relay=b+0x2170100;p.before[:5]=archive[rva:rva+5];p.after[:5]=reader.memory.read(p.address,5)
        for i,p in enumerate(plans.counters):p.startedAddress=0x79008000+i*16;p.activeAddress=p.startedAddress+8
        runtime=wire.envelope(wire.Snapshot,'Snapshot',nonce)
        for k in ('prepared','ownerArmed','sourcesArmed','ready','hostInitialized','hostCacheValid'):setattr(runtime,k,1)
        runtime.hostThread=77;runtime.hostCacheAddress=0x79009000;calls=0
        def snapshot():
            nonlocal calls
            calls+=1;s=wire.Snapshot.from_buffer_copy(bytes(runtime));s.parentBefore=s.parentAfter=s.parentFinally=calls;s.hostCacheSequence=calls*2
            for i,(a,p) in enumerate(zip(s.counters,plans.counters)):a.startedAddress=p.startedAddress;a.activeAddress=p.activeAddress;a.started=calls*(i+1)
            return s
        root=reader.pointer(b+0x1FCA1E0);worldptr=reader.pointer(root+0x85130)
        provider=AObservedBoundary(reader,pid=reader.pid,birth=birth,base=b,root=root,world_address=worldptr,cache=0x75006000,
            force=12,ruler=12,nonce=nonce,plans=plans,read_birth=lambda:process_birth(reader),runtime_snapshot=snapshot,no_new_commands=True)
        prep=wire.envelope(wire.Prepare,'Prepare',nonce);prep.pid,prep.birth,prep.base=reader.pid,birth,b
        prep.root,prep.world,prep.force,prep.ruler,prep.epoch,prep.year,prep.month,prep.day=root,worldptr,12,12,123,203,8,11
        entry=SimpleNamespace(provider=provider,phase='BOUND',room=room,coordinator=c,prep=prep)
        approved=RulesBuild(inputs/'first.dll',inputs/'factory-publisher.exe',sha(inputs/'first.dll'),sha(inputs/'factory-publisher.exe'),
            sha(inputs/'factory-host.exe'),tuple((x['instruction_rva'],bytes.fromhex(x['bytes']),x['value_rva']) for x in profile['active_counters']),'OWNED_FIXTURE')
        protection=ProtectedRulesOwner(entry,own.api,approved,setting,own.folder,threading.RLock())
        initial=provider.observe(node);protection.install();own.command('b '+str(protection.port.module.module),'BOUND')
        first=own.command('e','EXERCISED');active_refused=False
        if active_case:
            own.command('a','ACTIVE')
            try:protection.verify()
            except RuntimeError as exc:assert 'active' in str(exc);active_refused=True
            else:raise AssertionError('Active native callback permitted restore')
            own.command('r','DRAINED')
        else:
            c.phase='RUNNING';old=reader.state_objects();own.command('t','TURN')
            c.node={**c.node,'day':21};c.phase='PLANNING'
            final=provider.observe(c.node);assert final.day==21 and reader.state_objects()[3:]!=old[3:]
            assert reader.pointer(root+0x85130)==worldptr
            second=own.command('e','EXERCISED');protection.verify()
        restored=protection.restore();assert protection.restore_verified and protection.installed_once
        assert len(protection.factory.retained)==1
        own.command('s','SOURCES_RESTORED');last=own.finish()
        return dict(case=name,result='PASS',actual_rules_prepare_seal_publish=True,actual_remote_memory=True,
            a_seven_sources_standins=True,a_runtime_snapshot_double=True,actual_save_runtime_linked=False,
            actual_native_AI_income=True,same_world_new_user=not active_case,old_user_noaccess=not active_case,
            active_refused=active_refused,first=first,second=second if not active_case else None,
            rules=protection.status(),restored=restored,final=last,normal_exit=True)
    except BaseException:
        (own.folder/'host-failed.log').write_bytes(b''.join(own.lines))
        if protection and protection.factory.uncertain:
            (own.folder/'retained.json').write_text(json.dumps(dict(pid=own.child.pid,unknown=True)))
        else:
            try:
                if protection and protection.phase=='INSTALLED':protection.restore()
                own.command('s','SOURCES_RESTORED');own.finish()
            except BaseException:pass
        raise


def main():
    run=PRIVATE/'a_protected_native_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
    result=dict(result='FAIL',family='san14.a-protected-native.v1',game_access=False,steam_access=False,cases=[])
    before=pins();private={str(PRIOR/'result.json'):PRIOR_SHA};prior=json.loads((PRIOR/'result.json').read_text())
    for n,h in prior['source_sha256'].items():private[str(PRIOR/'src'/n)]=h
    for n,h in prior['binary_sha256'].items():private[str(PRIOR/'inputs'/n)]=h
    try:
        sources,inputs,profile=build(run);before.update(sources)
        result['cases']=[exercise(run,inputs,profile,'same-world-turn'),exercise(run,inputs,profile,'active-refused',True)]
        result['result']='PASS'
    except BaseException as exc:
        import traceback
        result['error']=repr(exc);(run/'failure.txt').write_text(traceback.format_exc());print(traceback.format_exc())
    after=pins();stable=all(after.get(k,sha(k))==v for k,v in before.items())
    for k,v in after.items():before.setdefault(k,v)
    result['sources']=before;result['private']=private
    result['sources_unchanged']=stable and all(Path(k).is_file() and sha(k)==v for k,v in {**before,**private}.items())
    if not result['sources_unchanged']:result['result']='FAIL'
    result['artifacts']={str(p):sha(p) for p in run.rglob('*') if p.is_file()}
    (run/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(run/'result.json')
    return int(result['result']!='PASS')

if __name__=='__main__':raise SystemExit(main())
