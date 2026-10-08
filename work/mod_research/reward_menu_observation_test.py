"""Build/test owned processes only; never call preflight/record or find SAN14."""
from copy import deepcopy
from datetime import datetime
import json
from pathlib import Path
import subprocess
import sys

import reward_menu_observation as observer
import reward_menu_observation_events as events
import a_save_observation_test as predecessor

P=Path(__file__).resolve().parent
MODES=('matched','selection-change','wrapper-no-common','idle-only','event-one','empty','unreturned',
       'bad-type','wrong-viewer','bad-stack','cycle','duplicate-person','oversize','orphan-common',
       'orphan-return','wrong-rsp','wrong-common-frame','nested','bad-funding','different-ids',
       'bad-predecessor','duplicate-common')
ACCEPT=('matched','selection-change','wrapper-no-common','idle-only','event-one','empty','unreturned')


def check_core():
    expected=(P/'a_save_observation.cpp').read_text(encoding='utf-8')
    expected=expected.replace('// Native Save/army span recorder. Retains the reviewed debugger cleanup loop',
        '// Reward menu recorder. Retains the reviewed debugger cleanup loop')
    expected=expected.replace('a_save_observation_payload.inc','reward_menu_observation_payload.inc').replace('a_save_observation_binding.inc','reward_menu_observation_binding.inc')
    actual=(P/'reward_menu_observation.cpp').read_text(encoding='utf-8')
    # The sole core successor change adds DR6 event ownership on acquisition
    # and cleanup. Freeze the rest by comparing around those explicit deltas.
    actual=actual.replace('#include "reward_menu_observation_debug_status.inc"\n','')
    actual=actual.replace('                    if(!debugStatusVacant(c))throw std::runtime_error("Existing unowned debug status; not clearing it");\n','')
    actual=actual.replace('std::set<DWORD> suspendedByUs,statusWarned;bool warned=false;','std::set<DWORD> suspendedByUs;bool warned=false;')
    actual=actual.replace('                    const auto restoreContext=context(thread.handle,CONTEXT_CONTROL|CONTEXT_DEBUG_REGISTERS);\n                    const auto current=registersOf(restoreContext);',
                          '                    const auto current=registersOf(context(thread.handle,CONTEXT_DEBUG_REGISTERS));')
    start=actual.index('                    const bool deliveredOwned=')
    end=actual.index('                    restore(thread.handle,thread.original);',start)
    assert 'mayRestoreDebugStatus' in actual[start:end] and 'cleanup_foreign_debug_status_retained' in actual[start:end]
    actual=actual[:start]+actual[end:]
    assert actual==expected,'Debugger core changed outside explicit DR6 successor delta'
    expected=(P/'a_save_observation_binding.inc').read_text(encoding='utf-8').replace('a_save_observation_anchors.h','reward_menu_observation_anchors.h')
    expected=expected.replace('rva!=0x2F7C28','rva!=0x67A930').replace('saveObservationAnchors','menuObservationAnchors')
    assert (P/'reward_menu_observation_binding.inc').read_text(encoding='utf-8')==expected,'Binding core changed beyond anchors/entry'
    assert len(observer.anchors())==9
    return dict(case='reviewed-core-exact-successor-delta',passed=True)


def semantic(run,mode):
    folder=run/('semantic-'+mode);folder.mkdir();trace=folder/'trace.jsonl'
    proc=subprocess.run([str(run/'semantic.exe'),str(trace),mode],capture_output=True,timeout=15)
    (folder/'stdout.txt').write_bytes(proc.stdout);(folder/'stderr.txt').write_bytes(proc.stderr)
    data=json.loads(proc.stdout);rejected=mode not in ACCEPT
    assert proc.returncode==int(rejected) and data['rejected']==rejected,(mode,data,proc.stderr)
    rows=observer.records(trace,allow_partial=False);binding=rows[0]
    metadata={k:binding[k] for k in ('pid','birth','base','run_id')}
    metadata.update(capture_complete=not rejected,capture_errors=['sampler rejected'] if rejected else [])
    analysis=events.analyze([r for r in rows if 'seq' in r],metadata)
    expected='INCOMPLETE_CAPTURE' if rejected or mode=='unreturned' else 'MENU_CALL_SOURCE_MATCHED' if mode in ('matched','selection-change') else 'INCONCLUSIVE'
    assert analysis['classification']==expected and not analysis['production_permit'],(mode,analysis)
    if mode=='matched':
        from test_domestic_reader import Fixture
        assert analysis['pairs'][0]['preview']==Fixture('reward').capture()['command_preview']
        assert data['samples']==4,'Identical Update was not deduplicated'
        context=dict(room_id='1'*32,binding_epoch='2'*32,epoch='3'*32,player_id='A',bound_force_id=12,
            main_district_id=11,viewer_force_id=12,attachment_id='4'*32,menu_instance_id='5'*32,
            world_revision=0,draft_revision=1,phase='PLANNING',observed_tick=100,expires_tick=200)
        shadow=events.capture_shadow(analysis,context,now_tick=100)
        assert shadow['network_packet'] is None and not shadow['network_submission_allowed'] and shadow['duplicate_confirmation_same_object']
        context['viewer_force_id']=2
        try:events.capture_shadow(analysis,context,now_tick=100)
        except ValueError:pass
        else:raise AssertionError('Wrong viewer accepted')
        observer.write(folder/'shadow.json',shadow)
    observer.write(folder/'analysis.json',analysis)
    return dict(case=mode,passed=True,kind='owned_memory_native_decoder_and_context_models',classification=analysis['classification'])


def counterexamples(run):
    raw=observer.records(run/'semantic-matched'/'trace.jsonl',allow_partial=False)
    rows=[r for r in raw if 'seq' in r]
    metadata={k:raw[0][k] for k in ('pid','birth','base','run_id')}
    metadata.update(capture_complete=True,capture_errors=[])
    variants=[]
    def altered(name,fn):
        r=deepcopy(rows);m=deepcopy(metadata);fn(r,m);variants.append((name,r,m))
    altered('sequence-gap',lambda r,m:r[2].update(seq=4))
    altered('nonzero-loss',lambda r,m:r[2].update(lost_events=1))
    altered('float-source-rva',lambda r,m:r[2].update(rva=float(r[2]['rva'])))
    altered('wrong-run',lambda r,m:r[2].update(run_id='other'))
    altered('wrong-return-stack',lambda r,m:r[-1].update(rsp=r[-1]['rsp']+8))
    altered('wrong-common-frame',lambda r,m:r[2].update(rsp=r[2]['rsp']+8))
    altered('world-change',lambda r,m:r[-1].update(world=r[-1]['world']+8))
    altered('viewer-change',lambda r,m:r[-1].update(viewer=2))
    altered('date-change',lambda r,m:r[-1].update(date=[203,8,21]))
    altered('null-errors',lambda r,m:m.update(capture_errors=None))
    altered('incomplete',lambda r,m:m.update(capture_complete=False))
    altered('extra-address-field',lambda r,m:r[1]['preview'].update(pointer=0x12345678))
    altered('bool-id',lambda r,m:r[1]['preview'].update(officer_ids=[True]))
    altered('duplicate-id',lambda r,m:r[1]['preview'].update(officer_ids=[620,620]))
    altered('no-update',lambda r,m:r[0].update(event='wrapper_call',rva=0x67A993))
    variants.append(('truncated-return',rows[:-1],metadata))
    result=[]
    for name,r,m in variants:
        analysis=events.analyze(r,m);assert analysis['classification']=='INCOMPLETE_CAPTURE' and not analysis['network_submission_allowed'],(name,analysis)
        result.append(dict(case=name,passed=True,kind='analyzer_counterexample'))
    summary=dict(event='summary',reason='one_wrapper_return_observed',selected_records=len(rows),lost_events=0)
    detached=dict(event='detached',registers_restored=True,owned_queue_drained=True)
    for event in ('cleanup_pending_owned_frozen','cleanup_owned_exception_drained','cleanup_foreign_exception_forwarded','cleanup_process_exit','unowned_debug_status','cleanup_foreign_debug_status_retained'):
        lifecycle,clean=observer.capture_status(rows+[summary,dict(event=event),detached],True,0)
        assert clean and not lifecycle['capture_complete'],event
        result.append(dict(case=event,passed=True,kind='lifecycle_failure_refusal'))
    for reason in ('hardware_event_limit','debug_event_limit'):
        lifecycle,_=observer.capture_status(rows+[dict(summary,reason=reason),detached],True,4)
        assert not lifecycle['capture_complete'];result.append(dict(case=reason,passed=True,kind='limit_refusal'))
    return result


def main():
    run=P/'reward_menu_observation_test_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
    sources={n:observer.sha(P/n) for n in observer.SOURCES}
    result=dict(schema='san14.reward-menu-observation-owned-tests.v1',result='FAIL',sources=sources,cases=[],
                game_access=False,native_menu_interception=False,production_permit=False)
    flags='/nologo /std:c++17 /EHsc /W4 /WX /I"'+str(P)+'"'
    commands=[f'cl {flags} "{P/"reward_menu_observation.cpp"}" /Fe:observer.exe /Fo:production.obj /link /INCREMENTAL:NO',
        f'cl {flags} /DA_SAVE_OBSERVATION_FIXTURE "{P/"reward_menu_observation.cpp"}" /Fe:observer-fixture.exe /Fo:fixture.obj /link /INCREMENTAL:NO',
        f'cl {flags} "{P/"a_save_observation_debug_fixture.cpp"}" /Fe:submit_probe_fixture.exe /Fo:debug-fixture.obj /link /INCREMENTAL:NO',
        f'cl {flags} "{P/"reward_menu_observation_semantic_fixture.cpp"}" /Fe:semantic.exe /Fo:semantic.obj /link /INCREMENTAL:NO',
        f'cl {flags} "{P/"reward_menu_observation_status_fixture.cpp"}" /Fe:status-fixture.exe /Fo:status-fixture.obj /link /INCREMENTAL:NO']
    build=run/'build.cmd';build.write_text('@echo off\nsetlocal\ncall "'+predecessor.VC+'" >nul\nif errorlevel 1 exit /b 1\n'+'\n'.join(c+'\nif errorlevel 1 exit /b 1' for c in commands)+'\n',encoding='utf-8')
    try:
        result['cases'].append(check_core())
        proc=subprocess.run(['cmd','/c',str(build)],cwd=run,capture_output=True)
        (run/'build.log').write_bytes(proc.stdout+proc.stderr)
        if proc.returncode:raise RuntimeError('Build failed: '+str(run/'build.log'))
        status=subprocess.run([str(run/'status-fixture.exe'),str(run/'status-cases.jsonl')],capture_output=True,timeout=15)
        (run/'status-fixture.stdout.txt').write_bytes(status.stdout);(run/'status-fixture.stderr.txt').write_bytes(status.stderr)
        status_result=json.loads(status.stdout)
        assert status.returncode==0 and status_result['passed'] and status_result['checks']==26,status_result
        result['cases'].append(dict(status_result,case='dr6-os-roundtrips-and-modeled-event-ownership'))
        for mode in predecessor.MODES:
            result['cases'].append(predecessor.hardware(run,mode));print('hardware',mode,'PASS',flush=True)
        for mode in MODES:
            result['cases'].append(semantic(run,mode));print('semantic',mode,'PASS',flush=True)
        result['cases'].extend(counterexamples(run))
        proc=subprocess.run([sys.executable,str(P/'reward_menu_observation.py')],capture_output=True,timeout=10)
        assert proc.returncode==0 and b'--preflight' in proc.stdout
        result['cases'].append(dict(case='default-help-no-process-access',passed=True))
        proc=subprocess.run([sys.executable,str(P/'reward_menu_observation.py'),'--preflight'],capture_output=True,timeout=10)
        assert proc.returncode==2 and b'explicit --pid required' in proc.stderr
        result['cases'].append(dict(case='explicit-pid-required-before-preflight',passed=True))
        for pid in (None,True,0,-1):
            try:observer.preflight(pid)
            except ValueError as error:assert 'Explicit positive PID required' in str(error)
            else:raise AssertionError('Invalid PID reached game reader')
        result['cases'].append(dict(case='invalid-pid-refused-by-api-before-reader-import',passed=True))
        result.update(production_sha256=observer.sha(run/'observer.exe'),fixture_sha256=observer.sha(run/'observer-fixture.exe'),
            semantic_sha256=observer.sha(run/'semantic.exe'),debug_fixture_sha256=observer.sha(run/'submit_probe_fixture.exe'))
        result['status_fixture_sha256']=observer.sha(run/'status-fixture.exe')
        assert all(observer.sha(P/n)==v for n,v in sources.items()),'Source changed during tests'
        result['sources_unchanged']=True;result['result']='PASS'
    except Exception as error:
        result['error']=type(error).__name__+': '+str(error);raise
    finally:
        observer.write(run/'result.json',result)
        print(json.dumps(dict(result=result['result'],cases=len(result['cases']),path=str(run/'result.json'))),flush=True)


if __name__=='__main__':main()
