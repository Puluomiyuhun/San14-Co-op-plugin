"""Build and test only owned observer processes. Never discovers/opens the game."""
from pathlib import Path
from datetime import datetime
import json
import subprocess
import time
import a_save_observation_status as observer

P = Path(__file__).resolve().parent
VC = r'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat'
MODES = ('three-hits','timeout','cancel','wrong-birth','production-refusal','foreign','exceptions','adaptive','adaptive-error')
SEMANTICS = ('save-only','worker-before','overlap','inside','orphan','no-save','wrong-manager','wrong-stream',
             'wrong-save-return','wrong-worker-return','nested-save','duplicate-worker')


def wait(path, event=None, seconds=10):
    until = time.monotonic()+seconds
    while time.monotonic() < until:
        try:
            if event is None: return json.loads(path.read_text(encoding='utf-8'))
            rows = observer.records(path)
            if any(r.get('event') == event for r in rows): return rows
            if any(r.get('event') == 'error' for r in rows): raise RuntimeError(rows)
        except (FileNotFoundError, json.JSONDecodeError): pass
        time.sleep(.03)
    raise RuntimeError('Timed out waiting for '+str(path))


def hardware(run, mode):
    folder = run/mode; folder.mkdir()
    ready, go, trace = (folder/n for n in ('ready.json','go','trace.jsonl'))
    fixture_mode = 'adaptive' if mode == 'adaptive-error' else mode
    fixture = subprocess.Popen([str(run/'submit_probe_fixture.exe'), str(ready), str(go), fixture_mode],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)
    recorder = None
    try:
        info = wait(ready)
        binary = run/('observer.exe' if mode == 'production-refusal' else 'observer-fixture.exe')
        args = [str(binary), str(info['pid']), hex(info['base']), hex(info['rva']), '2' if mode == 'timeout' else '10',
                str(trace), str(observer.birth(int(fixture._handle))+(mode=='wrong-birth')),
                hex(info['rva2']) if mode in ('adaptive','adaptive-error') else '0',
                '1' if mode == 'adaptive-error' else '0', 'owned-hardware']
        recorder = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)
        refused = mode in ('wrong-birth','production-refusal','foreign','adaptive-error')
        if not refused or mode == 'adaptive-error':
            wait(trace, 'armed')
            if mode in ('three-hits','exceptions','adaptive','adaptive-error'): go.write_text('go')
            if mode == 'cancel': Path(str(trace)+'.stop').write_text('stop')
        out, err = recorder.communicate(timeout=20)
        (folder/'stdout.txt').write_bytes(out); (folder/'stderr.txt').write_bytes(err)
        rows = observer.records(trace)
        if refused:
            assert recorder.returncode == 1 and any(r.get('event') == 'error' for r in rows), (mode, rows, err)
            if mode in ('wrong-birth','production-refusal'):
                assert not any(r.get('event') == 'attached' for r in rows)
            else: assert rows[-1].get('event') == 'error_cleanup' and rows[-1]['registers_restored'] and rows[-1]['detached'], rows
        else:
            assert recorder.returncode == (4 if mode in ('timeout','cancel') else 0), (mode, rows, err)
            assert rows[-1].get('event') == 'detached' and rows[-1]['registers_restored'] and rows[-1]['owned_queue_drained'], rows
            assert any(r.get('event') == 'restore_verified' and r['all_six_debug_registers'] for r in rows), rows
        if not go.exists(): go.write_text('go')
        data, errors = fixture.communicate(timeout=10); (folder/'fixture.txt').write_bytes(data+errors)
        assert fixture.returncode == 0, (mode, data, errors)
        actual = json.loads(data)
        assert actual['calls'] == (1024 if mode in ('adaptive','adaptive-error') else 3), actual
        assert actual['value'] == (5121 if mode in ('adaptive','adaptive-error') else 31), actual
        if mode == 'exceptions':
            assert actual['handled'] == 2
            codes = [r['code'] for r in rows if r.get('event') == 'forwarded_exception']
            assert 0xE0421234 in codes and 0x80000003 in codes, rows
        if mode in ('adaptive','adaptive-error'):
            assert actual['second'] == 5121
            for event in ('pending_owned_layout_retained','cleanup_pending_owned_frozen','cleanup_owned_exception_drained'):
                assert any(r.get('event') == event for r in rows), ('No pending-event evidence', mode, event, rows)
        return dict(case=mode, passed=True, kind='owned_hardware_debugger', exit=recorder.returncode)
    finally:
        if recorder and recorder.poll() is None:
            Path(str(trace)+'.stop').write_text('stop')
            print('Cleanup still pending; recorder is NOT terminated:', recorder.pid, trace, flush=True)
        if fixture.poll() is None: go.write_text('go')


def semantic(run, mode):
    folder = run/('semantic-'+mode); folder.mkdir(); trace=folder/'trace.jsonl'
    proc = subprocess.run([str(run/'semantic.exe'), str(trace), mode], capture_output=True, timeout=15)
    (folder/'stdout.txt').write_bytes(proc.stdout); (folder/'stderr.txt').write_bytes(proc.stderr)
    data = json.loads(proc.stdout); expected_reject = mode.startswith('wrong-') or mode in ('nested-save','duplicate-worker')
    assert data['rejected'] == expected_reject and proc.returncode == int(expected_reject), (mode,data,proc.stderr)
    if not expected_reject: assert data['complete'] == (mode not in ('orphan','no-save')), data
    from a_save_native_coordination_events import analyze
    rows=observer.records(trace)
    analysis=analyze([r for r in rows if 'seq' in r], dict(pid=123,birth=456,base=0x140000000,
        run_id='owned-semantic',capture_complete=not expected_reject,capture_errors=['sampler rejected'] if expected_reject else []))
    expected=('INCOMPLETE_OR_INCONSISTENT_CAPTURE' if expected_reject or mode=='orphan' else
              'INCONCLUSIVE' if mode=='no-save' else
              'WORKER_SCOPE_OVERLAP_OBSERVED' if mode in ('overlap','inside') else 'NO_WORKER_SCOPE_OVERLAP_OBSERVED')
    assert analysis['classification']==expected and analysis['production_permit'] is False, (mode,analysis)
    observer.write(folder/'analysis.json',analysis)
    return dict(case=mode, passed=True, kind='owned_memory_context_models', details=data,classification=analysis['classification'])


def lifecycle_cases(run):
    """A valid Save pair cannot survive discarded cleanup events or truncation."""
    from a_save_native_coordination_events import analyze
    spans=observer.records(run/'semantic-save-only'/'trace.jsonl', allow_partial=False)
    summary=dict(event='summary', reason='save_span_and_worker_returns_observed', selected_records=sum('seq' in r for r in spans),lost_events=0)
    detached=dict(event='detached',registers_restored=True,owned_queue_drained=True)
    variants=[('complete-save', spans+[summary,detached], 0, 'NO_WORKER_SCOPE_OVERLAP_OBSERVED'),
              ('complete-empty-timeout', [dict(summary,reason='timeout_or_cancel',selected_records=0),detached],4,'INCONCLUSIVE')]
    for event in ('cleanup_pending_owned_frozen','cleanup_owned_exception_drained','cleanup_foreign_exception_forwarded',
                  'cleanup_process_exit','unowned_debug_status','cleanup_foreign_debug_status_retained'):
        variants.append((event,spans+[summary,dict(event=event),detached],0,'INCOMPLETE_OR_INCONSISTENT_CAPTURE'))
    for reason in ('hardware_event_limit','debug_event_limit'):
        variants.append((reason,spans+[dict(summary,reason=reason),detached],4,'INCOMPLETE_OR_INCONSISTENT_CAPTURE'))
    variants.append(('truncated-selected-record',spans[:-1]+[summary,detached],0,'INCOMPLETE_OR_INCONSISTENT_CAPTURE'))
    variants.append(('missing-summary',spans+[detached],0,'INCOMPLETE_OR_INCONSISTENT_CAPTURE'))
    results=[]
    for mode,rows,code,expected in variants:
        lifecycle,clean=observer.capture_status(rows,True,code)
        assert clean
        metadata=dict(pid=123,birth=456,base=0x140000000,run_id='owned-semantic',**lifecycle)
        analysis=analyze([r for r in rows if 'seq' in r],metadata)
        assert analysis['classification']==expected and not analysis['production_permit'],(mode,analysis)
        results.append(dict(case=mode,passed=True,kind='launcher_lifecycle_models',classification=analysis['classification']))
    partial=run/'partial-json.jsonl';partial.write_text('{"event":"partial"',encoding='utf-8')
    assert observer.records(partial,allow_partial=True)==[]
    try: observer.records(partial,allow_partial=False)
    except json.JSONDecodeError: pass
    else: raise AssertionError('A truncated final JSON record was silently ignored')
    results.append(dict(case='truncated-final-json-refused',passed=True,kind='launcher_parser'))
    observer.write(run/'lifecycle-cases.json',results)
    return results


def main():
    run=P/'a_save_observation_status_test_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
    sources={n:observer.sha(P/n) for n in observer.SOURCES}
    result=dict(schema='san14.a-save-observation-status-owned-tests.v1', result='FAIL', sources=sources,
                cases=[], game_access=False, actual_save_load=False, production_permit=False)
    flags='/nologo /std:c++17 /EHsc /W4 /WX /I"'+str(P)+'"'
    commands=[
        f'cl {flags} "{P / "a_save_observation_status.cpp"}" /Fe:observer.exe /Fo:production.obj /link /INCREMENTAL:NO',
        f'cl {flags} /DA_SAVE_OBSERVATION_FIXTURE "{P / "a_save_observation_status.cpp"}" /Fe:observer-fixture.exe /Fo:fixture.obj /link /INCREMENTAL:NO',
        f'cl {flags} "{P / "a_save_observation_debug_fixture.cpp"}" /Fe:submit_probe_fixture.exe /Fo:debug-fixture.obj /link /INCREMENTAL:NO',
        f'cl {flags} "{P / "a_save_observation_status_semantic_fixture.cpp"}" /Fe:semantic.exe /Fo:semantic.obj /link /INCREMENTAL:NO',
        f'cl {flags} "{P / "reward_menu_observation_status_fixture.cpp"}" /Fe:status-fixture.exe /Fo:status-fixture.obj /link /INCREMENTAL:NO']
    build=run/'build.cmd';build.write_text('@echo off\nsetlocal\ncall "'+VC+'" >nul\nif errorlevel 1 exit /b 1\n'+'\n'.join(c+'\nif errorlevel 1 exit /b 1' for c in commands)+'\n')
    try:
        expected=(P/'reward_menu_observation.cpp').read_text(encoding='utf-8').replace('Reward menu recorder.', 'Native Save/army span recorder.').replace('reward_menu_observation_payload.inc','a_save_observation_payload.inc').replace('reward_menu_observation_binding.inc','a_save_observation_binding.inc')
        assert (P/'a_save_observation_status.cpp').read_text(encoding='utf-8')==expected,'Production debugger core diverged from reviewed shared guard'
        expected_semantic=(P/'a_save_observation_semantic_fixture.cpp').read_text(encoding='utf-8').replace('"a_save_observation.cpp"','"a_save_observation_status.cpp"')
        assert (P/'a_save_observation_status_semantic_fixture.cpp').read_text(encoding='utf-8')==expected_semantic
        result['cases'].append(dict(case='shared-debugger-core-and-frozen-payload',passed=True,kind='source_composition'))
        proc=subprocess.run(['cmd','/c',str(build)],cwd=run,capture_output=True)
        (run/'build.log').write_bytes(proc.stdout+proc.stderr)
        if proc.returncode:raise RuntimeError('Build failed; see '+str(run/'build.log'))
        status=subprocess.run([str(run/'status-fixture.exe'),str(run/'status-cases.jsonl')],capture_output=True,timeout=15)
        (run/'status-fixture.stdout.txt').write_bytes(status.stdout);(run/'status-fixture.stderr.txt').write_bytes(status.stderr)
        status_result=json.loads(status.stdout)
        assert status.returncode==0 and status_result['passed'],status_result
        result['cases'].append(dict(case='shared-dr6-status-guard',kind='os-roundtrips-and-explicit-context-models',**status_result))
        for mode in MODES:
            result['cases'].append(hardware(run,mode));print(mode,'PASS',flush=True)
        for mode in SEMANTICS:
            result['cases'].append(semantic(run,mode));print('semantic-'+mode,'PASS',flush=True)
        result['cases'].extend(lifecycle_cases(run))
        proc=subprocess.run(['py','-3',str(P/'a_save_observation_status.py')],capture_output=True,timeout=10)
        assert proc.returncode==0 and b'--preflight' in proc.stdout
        result['cases'].append(dict(case='default-help-only',passed=True,kind='launcher'))
        proc=subprocess.run(['py','-3',str(P/'a_save_observation_status.py'),'--preflight'],capture_output=True,timeout=10)
        assert proc.returncode==2 and b'explicit --pid required' in proc.stderr
        result['cases'].append(dict(case='explicit-pid-required',passed=True,kind='launcher'))
        for pid in (None,True,0,-1):
            try:observer.preflight(pid)
            except ValueError as error:assert 'Explicit positive PID required' in str(error)
            else:raise AssertionError('Invalid PID reached reader')
        result['cases'].append(dict(case='invalid-pid-before-import',passed=True,kind='launcher'))
        result.update(status_fixture_sha256=observer.sha(run/'status-fixture.exe'),production_sha256=observer.sha(run/'observer.exe'),fixture_sha256=observer.sha(run/'observer-fixture.exe'),
                      semantic_sha256=observer.sha(run/'semantic.exe'),debug_fixture_sha256=observer.sha(run/'submit_probe_fixture.exe'))
        assert all(observer.sha(P/n)==h for n,h in sources.items()), 'Source changed while test was running'
        result['sources_unchanged']=True; result['result']='PASS'
    except Exception as error:
        result['error']=type(error).__name__+': '+str(error);raise
    finally:
        observer.write(run/'result.json',result)
        print(json.dumps(dict(result=result['result'],cases=len(result['cases']),path=str(run/'result.json'))),flush=True)


if __name__=='__main__':main()
