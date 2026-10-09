"""One actual parent/Host/Inspector save with native-position current-state models.

Parent boundary=0, Game callback=Game, User callback=User. No game process or
real serializer; upstream business and native-parent source remain fixtures.
"""
from pathlib import Path
from datetime import datetime
import hashlib,json,os,subprocess,sys,difflib
from checkpoint_fresh_save_packet import decode_packet
P=Path(__file__).resolve().parent
PRIVATE=P.parents[2]/'mod_research'
CASES=('normal',)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    run=PRIVATE/'a_save_scoped_input_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
    old=(P/'a_save_held_ipc_build.py').read_text(encoding='utf-8')
    s=old.replace('P = Path(__file__).resolve().parent','P = Path('+repr(str(P))+')')
    s=s.replace("run = P / 'a_save_held_ipc_build_runs' / datetime.now().strftime('%Y%m%d-%H%M%S-%f')",'run = Path('+repr(str(run/'build'))+')')
    s=s.replace("ipc='a_save_held_ipc.cpp', held=", "ipc='a_save_dispatch_ipc.cpp', host='a_save_dispatch_host.cpp', mailbox='a_save_dispatch_mailbox.cpp', adapter='a_save_parent_adapter.cpp', parent_bridge='b_reload_parent_bridge.cpp', held=")
    s=s.replace('a_save_held_ipc_fixture.cpp','a_save_parent_adapter_fixture.cpp').replace('a_save_held_ipc_flow_test.py','a_save_scoped_input_test.py')
    s=s.replace('packet.obj ipc.obj held.obj','packet.obj ipc.obj host.obj mailbox.obj adapter.obj parent_bridge.obj held.obj')

    s=s.replace("asm = dict(input_asm=", "asm = dict(parent_asm='b_reload_parent_bridge.asm', input_asm=")
    s=s.replace("inspector='checkpoint_native_input_pending_adapter.cpp'", "inspector='checkpoint_native_input_pending_empty_queue.cpp'")
    s=s.replace("commands += [f'cl {flags} /DCHECKPOINT_LIVE_STORAGE_BINDING_FIXTURE", 'commands += [f\'cl {flags} /DA_SAVE_PARENT_ADAPTER_FIXTURE /c "{P / units["adapter"]}" /Fo:fixture_adapter.obj\']\n    commands += [f\'cl {flags} /DCHECKPOINT_LIVE_STORAGE_BINDING_FIXTURE')
    s=s.replace("inspector.obj packet.obj ipc.obj host.obj mailbox.obj adapter.obj parent_bridge.obj held.obj fixture.obj", "inspector.obj packet.obj ipc.obj host.obj mailbox.obj fixture_adapter.obj parent_bridge.obj held.obj fixture.obj")
    s=s.replace("bridge_asm.obj driver.obj", "bridge_asm.obj parent_asm.obj driver.obj")
    s=s.replace("input='planning_checkpoint_save_gate.cpp'", "input='a_save_scoped_gate.cpp', scope='a_save_native_input_scope.cpp'")
    s=s.replace("inspector='checkpoint_native_input_pending_empty_queue.cpp'", "inspector='a_save_scoped_input.cpp'")
    s=s.replace('input.obj interlock.obj', 'input.obj scope.obj interlock.obj').replace('fixture_input.obj interlock.obj','fixture_input.obj scope.obj interlock.obj')
    original=(P/'a_save_parent_adapter_fixture.cpp').read_text()
    fixture=original.replace('gameDispatch()', 'scopedGame()').replace('rewardDispatch()', 'scopedUser()').replace('dispatch(0,user)', 'scopedDispatch(0,user)').replace('dispatch(1,b+0x340000)', 'scopedDispatch(1,b+0x340000)')
    end=fixture.index('\n',fixture.index('static void need('))
    fixture=fixture[:end+1]+(P/'a_save_scoped_input_fixture.cpp').read_text()+fixture[end+1:]
    fixture=fixture.replace('gen<=2','gen<=1').replace('if(gen==1)need(WaitForSingleObject(drop,5000)==WAIT_OBJECT_0,"actual next period rebind ready");','')
    begin=fixture.index('  if(normal&&h.state==dh::State::Complete')
    end=fixture.index('  ownedParentWork=[&]{',begin)
    fixture=fixture[:begin]+fixture[end:]
    fixture=fixture.replace('planning_input_interlock::Controller second;auto*current=&interlock;bool rebound=false,triggered=false','bool triggered=false')
    fixture=fixture.replace('need(rebound&&h.observations==2&&h.submits==2&&h.copies==2&&h.releases==2&&d.submits==2&&d.copies==2&&u.save.completed_requests==2&&nativeBinds==2', 'need(h.observations==1&&h.submits==1&&h.copies==1&&h.releases==1&&d.submits==1&&d.copies==1&&u.save.completed_requests==1&&nativeBinds==1')
    fixture=fixture.replace('static void parentDispatch(){auto call=', 'static void parentDispatch(){put<uintptr_t>(b+0x19E7310+0x48,0);auto call=')
    fixture=fixture.replace('if(ownedParentWork)ownedParentWork();return', 'rejectCurrent(0,"parent original body is not a Host boundary");if(ownedParentWork)ownedParentWork();return')
    fixture=fixture.replace('a_save_parent_adapter::Report beforeParent{};', 'rejectCurrent(0,"unclaimed current zero rejected");rejectCurrent(b+0x200000,"wrong current rejected");a_save_parent_adapter::Report beforeParent{};')
    fixture=fixture.replace('!failed,"actual Driver completes and host drains"', '!failed&&nativeScopeRejects>=3,"actual Driver completes and host drains"')
    fixture=fixture.replace('\\"actual_parent_adapter\\":true', '\\"scoped_current_positions\\":true,\\"unclaimed_zero_rejected\\":true,\\"wrong_current_rejected\\":true,\\"original_body_zero_rejected\\":true,\\"actual_parent_adapter\\":true')
    # New generated fixture is pinned separately; original remains frozen.
    (run/'scoped_fixture.cpp').write_text(fixture)
    s=s.replace("run.mkdir(parents=True)", "run.mkdir(parents=True)\n    (run/'scoped_fixture.cpp').write_text("+repr(fixture)+")")
    s=s.replace('"{P / "a_save_parent_adapter_fixture.cpp"}"', '"{run / "scoped_fixture.cpp"}"')
    s=s.replace("'a_save_parent_adapter_fixture.cpp',", "'a_save_parent_adapter_fixture.cpp','a_save_scoped_input_fixture.cpp',")
    script=run/'generated_build.py';script.write_text(s,encoding='utf-8')
    (run/'builder.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),s.splitlines(True),fromfile='frozen-held-builder',tofile='host-builder')),encoding='utf-8')
    env=os.environ.copy();env['SAN14_PRIVATE_FIXTURE_ROOT']=str(PRIVATE)
    rows=[];decoded=[];build={};error=None
    private_pins={n:sha(PRIVATE/n) for n in ('checkpoint_push_profile.h','checkpoint_planning_hold.dll','checkpoint_planning_hold.lib')}
    python_pins={'checkpoint_fresh_save_packet.py':sha(P/'checkpoint_fresh_save_packet.py')}
    try:
        r=subprocess.run([sys.executable,str(script)],env=env,capture_output=True,text=True,errors='replace',timeout=180)
        (run/'builder.log').write_text(r.stdout+r.stderr,encoding='utf-8')
        build=json.loads((run/'build'/'result.json').read_text());assert r.returncode==0 and build['result']=='PASS'
        exe=run/'build'/'fixture.exe';digest=sha(exe)
        for case in CASES:
            folder=run/case;folder.mkdir();out=''
            try:
                r=subprocess.run([str(exe),case,str(folder),digest],cwd=folder,capture_output=True,text=True,errors='replace',timeout=25)
                out=r.stdout+r.stderr;records=[json.loads(x) for x in r.stdout.splitlines() if x.startswith('{')]
                ok=r.returncode==0 and len(records)==1 and records[0].get('passed') is True
                if ok and case=='normal':
                    for gen in (1,):
                        f=folder/f'normal-{gen}.packet';a=decode_packet(f.read_bytes());assert a.request['generation']==a.request['period']==gen and len(a.data)==32 and a.data[0]==(11 if gen==1 else 21)
                        assert a.report['file_bytes_verified'] and a.report['phase_mask']==31 and a.report['worker_joined']==1
                        decoded.append(dict(generation=gen,packet_sha256=sha(f),payload_sha256=a.sha256))
                rows.append(dict(case=case,passed=ok,exit=r.returncode,records=records))
            except Exception as e:
                out+=repr(e);rows.append(dict(case=case,passed=False,error=repr(e)))
                if isinstance(e,subprocess.TimeoutExpired):out+=str(e.stdout)+str(e.stderr)
            (folder/'run.log').write_text(out,encoding='utf-8')
    except Exception as e:
        error=repr(e)
        (run/'failure.log').write_text(error+'\n'+str(getattr(e,'stdout',''))+'\n'+str(getattr(e,'stderr','')),encoding='utf-8')
    pins={**build.get('sources',{}),**python_pins};same=bool(build.get('sources')) and all(sha(P/n)==h for n,h in pins.items()) and all(sha(PRIVATE/n)==h for n,h in private_pins.items())
    generated={p.name:sha(p) for p in (run/'build').glob('*') if p.suffix in ('.inc','.cmd','.cpp')}
    binaries={p.name:sha(p) for p in (run/'build').glob('*') if p.suffix in ('.exe','.lib','.dll','.obj')}
    passed=not error and same and len(rows)==len(CASES) and len(decoded)==1 and all(r['passed'] for r in rows)
    result=dict(result='PASS' if passed else 'FAIL',error=error,cases=rows,decoded=decoded,sources=pins,sources_unchanged=same,generated=generated,binaries=binaries,build_generator_sha256=sha(script),private_inputs=private_pins,private_inputs_unchanged=all(sha(PRIVATE/n)==h for n,h in private_pins.items()),actual_owner=True,actual_controller=True,actual_pipe=True,actual_native_parent=False,real_save_serializer=False,all_writers_proven=False,game_access=False)
    path=run/'result.json';path.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(result=result['result'],path=str(path))));return 0 if passed else 1
if __name__=='__main__':raise SystemExit(main())
