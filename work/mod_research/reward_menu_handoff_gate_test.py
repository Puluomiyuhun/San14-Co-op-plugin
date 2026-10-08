"""Owned native archived-Update gate + existing CaptureSession/TLS dedup only.

Requires an explicit private archive path; does not find/open any game process.
No live, install, preflight, record, execute or production-permit entry exists.
"""
from datetime import datetime
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

P=Path(__file__).resolve().parent
ROOT=P.parent.parent
sys.path.insert(0,str(ROOT/'outputs'/'san14-link'))
import reward_menu_handoff_gate_audit as audit

MODES=('unpatched-control','take-once','repeat','duplicate-take','wrong-claim','wrong-generation',
       'change-before-take','change-on-repeat','change-after-take','event-reset','exit-pending','destroy-pending',
       'wrong-world','wrong-viewer','wrong-date','wrong-stack','wrong-layout','wrong-thread','source-tamper','relay-tamper','take-wrong-thread',
       'foreign-call','retire-before','retire-pending','retire-taken','idle','event-one','empty','cycle',
       'duplicate-person','oversize','unreadable-world','rebind','bad-bind-source')
VC=r'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path,data):
    Path(path).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def sources():
    own=['reward_menu_handoff_gate.h','reward_menu_handoff_gate.cpp','reward_menu_handoff_gate_fixture.cpp',
         'reward_menu_handoff_gate_fixture.asm','reward_menu_handoff_gate_audit.py','reward_menu_handoff_gate_test.py']
    deps=['reward_menu_observation_decode.inc','reward_menu_observation_semantic_fixture.cpp',
          'reward_ready_flow_test.py','reward_ready_flow_fixture.py','reward_room_flow_test.py','reward_room_flow_fixture.py']
    protocol=['reward_menu_capture.py','reward_ready_flow.py','reward_room_flow.py','authority_reward.py',
              'authoritative_sync.py','reward_preflight.py','reward_eligibility.py','execution_journal.py','room_session.py','room_transport.py',
              'domestic_reader.py','game_reader.py','readonly_probe.py','sortie_reader.py']
    paths=[P/x for x in own+deps]+[ROOT/'outputs'/'san14-link'/x for x in protocol]
    return {str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in paths}


def tls_composition(run,claimed):
    from reward_ready_flow_test import Harness
    from reward_ready_flow_fixture import capture_inputs
    from reward_menu_capture import CaptureSession
    h=Harness(run/'tls-composition',None)  # Existing explicit business model, real TLS/separate B process.
    try:
        _,context=capture_inputs(h.flow.host)
        context['menu_instance_id']=claimed['menu_id']
        context['draft_revision']=claimed['generation']
        preview=claimed['preview']
        session=CaptureSession()
        capture_id='f'*32
        session.capture(preview,context,capture_id=capture_id,now_tick=100)
        pending=session.confirm(capture_id,preview,context,now_tick=100)
        first=h.checked('A',pending.packet())
        again=h.checked('A',session.confirm(capture_id,preview,context,now_tick=100).packet())
        assert first['ordinal']==again['ordinal'] and again['duplicate']
        assert h.flow.status()['request_count']==1
        assert h.flow.pump_one()['sequence']==1
        assert h.guest.call('consume_reward')['ack']['ok']
        assert h.port.calls==1 and h.guest.call('sample')['calls']==1
        assert h.port.sample()==h.guest.call('sample')['sample']
        h.both_ready();h.flow.begin_seal();assert h.guest.call('consume_fence')['ack']['ok']
        final=h.flow.complete_seal()
        assert final['cut']['sequence']==1 and not final['native_simulation_permit']
        return dict(case='native-claimed-ids_to_CaptureSession_to_real_TLS_once',passed=True,
            kind='owned_archive_gate_then_real_TLS_with_business_and_context_models',
            authoritative_commands=1,host_model_applications=1,guest_model_applications=1,
            preview=preview,repeat_request_deduplicated=True,
            menu_lifetime_context='explicit fixture source; no production context/IPC producer',
            native_game_execution=False,production_permit=False)
    finally:
        h.close()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive-root',type=Path,required=True)
    args=parser.parse_args()
    run=P/'reward_menu_handoff_gate_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    run.mkdir(parents=True)
    result=dict(schema='san14.reward-menu-handoff-gate-owned-tests.v1',result='FAIL',cases=[],
        sources={},game_access=False,production_permit=False)
    image_path=None
    try:
        result['sources']=sources()
        evidence,code,image_path=audit.inspect(args.archive_root)
        write(run/'archive-audit.json',evidence)
        result['cases'].extend(evidence['checks'])
        (run/'owned-code.bin').write_bytes(code)  # private ignored run folder only
        flags='/nologo /std:c++17 /EHsc /W4 /WX /I"'+str(P)+'"'
        commands=[f'ml64 /nologo /c /Fobridge.obj "{P/"reward_menu_handoff_gate_fixture.asm"}"',
            f'cl {flags} /c "{P/"reward_menu_handoff_gate.cpp"}" /Fo:gate.obj',
            f'cl {flags} "{P/"reward_menu_handoff_gate_fixture.cpp"}" gate.obj bridge.obj /Fe:fixture.exe /Fo:fixture.obj /link /INCREMENTAL:NO']
        build=run/'build.cmd'
        build.write_text('@echo off\nsetlocal\ncall "'+VC+'" >nul\nif errorlevel 1 exit /b 1\n'+
            '\n'.join(c+'\nif errorlevel 1 exit /b 1' for c in commands)+'\n',encoding='utf-8')
        built=subprocess.run(['cmd','/c',str(build)],cwd=run,capture_output=True,timeout=120,creationflags=subprocess.CREATE_NO_WINDOW)
        (run/'build.log').write_bytes(built.stdout+built.stderr)
        if built.returncode:raise RuntimeError('Build failed: '+str(run/'build.log'))
        result['fixture_sha256']=sha(run/'fixture.exe')
        claimed=None
        for mode in MODES:
            proc=subprocess.run([str(run/'fixture.exe'),str(run/'owned-code.bin'),mode],capture_output=True,timeout=15,creationflags=subprocess.CREATE_NO_WINDOW)
            (run/(mode+'.stdout.txt')).write_bytes(proc.stdout);(run/(mode+'.stderr.txt')).write_bytes(proc.stderr)
            if proc.returncode:raise RuntimeError(f'{mode} exit {proc.returncode}: {proc.stderr!r}')
            observation=json.loads(proc.stdout)
            assert observation['passed'] and not observation['production_permit']
            if mode=='take-once':claimed=observation['proposal']
            result['cases'].append(dict(case=mode,passed=True,kind='actual_archived_CPU_methods_and_explicit_service_doubles',observation=observation))
        assert claimed is not None
        result['cases'].append(tls_composition(run,claimed))
        result['result']='PASS'
    except Exception as error:
        result['error']=repr(error)
    finally:
        result['source_end']=sources()
        result['sources_unchanged']=result['sources']==result['source_end']
        if image_path is not None:
            result['archive_end_sha256']=sha(image_path)
            result['archive_unchanged']=result['archive_end_sha256']==audit.ARCHIVE_SHA256
            result['pdata_end_sha256']=sha(image_path.with_name('runtime-pdata.bin'))
            result['pdata_unchanged']=result['pdata_end_sha256']==evidence['pdata_sha256']
        if not result['sources_unchanged'] or result.get('archive_unchanged') is not True or result.get('pdata_unchanged') is not True:
            result['result']='FAIL'
        write(run/'result.json',result)
    print(json.dumps(dict(result=result['result'],checks=len(result['cases']),path=str(run/'result.json'),error=result.get('error'))))
    return int(result['result']!='PASS')


if __name__=='__main__':
    raise SystemExit(main())
