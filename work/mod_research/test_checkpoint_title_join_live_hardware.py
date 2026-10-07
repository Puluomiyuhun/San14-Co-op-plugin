"""Own-process debug/restore fixtures and offline live-trace adaptation tests.

Never discovers or opens SAN14. Production binary is tested only for rejecting
the dedicated fixture's process name before attachment.
"""
from pathlib import Path
from datetime import datetime
import copy
import json
import subprocess
import unittest
import checkpoint_title_join_live as live
from test_submit_probe import wait_json
ROOT=Path(__file__).resolve().parent
RESULTS=[]


def native_case(mode):
    folder=ROOT/'checkpoint_title_join_live_fixture_runs'/(datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'-'+mode)
    folder.mkdir(parents=True)
    ready,go,log=(folder/x for x in ('ready.json','go','trace.jsonl'))
    own=mode in ('exceptions','foreign','adaptive','adaptive-error')
    path=ROOT/('checkpoint_dispatch_handoff_live_native_fixture/submit_probe_fixture.exe' if own else 'lockstep-fixture/submit_probe_fixture.exe')
    command=[str(path),str(ready),str(go)]+(['adaptive' if mode=='adaptive-error' else mode] if own else [])
    fixture=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
    observer=None
    try:
        info=wait_json(ready)
        binary=ROOT/('checkpoint_title_join_live.exe' if mode=='production-refusal' else 'checkpoint_title_join_live_fixture.exe')
        args=[str(binary),str(info['pid']),hex(info['base']),hex(info['rva']),
              '2' if mode=='timeout' else '10',str(log),
              str(live.birth(int(fixture._handle))+(mode=='wrong-birth')),
              hex(info['rva2']) if mode in ('adaptive','adaptive-error') else '0','1' if mode=='adaptive-error' else '0','svdexSC34.s14']
        observer=subprocess.Popen(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
        refused=mode in ('wrong-birth','production-refusal','foreign','adaptive-error')
        if not refused or mode=='adaptive-error':
            wait_json(log,'armed')
            if mode in ('three-hits','exceptions','adaptive','adaptive-error'):go.write_text('go')
            if mode=='cancel':Path(str(log)+'.stop').write_text('stop')
        out,err=observer.communicate(timeout=18)
        rows=[json.loads(x) for x in log.read_text().splitlines() if x]
        if refused:
            assert observer.returncode==1 and any(r.get('event')=='error' for r in rows),(mode,rows,err)
            if mode not in ('foreign','adaptive-error'):assert not any(r.get('event')=='attached' for r in rows)
            else:assert rows[-1].get('event')=='error_cleanup' and rows[-1]['registers_restored'] and rows[-1]['detached'],rows
        else:
            assert observer.returncode==(4 if mode in ('timeout','cancel') else 0),(mode,rows,err)
            assert rows[-1].get('event')=='detached' and rows[-1]['registers_restored'],rows
            assert any(r.get('event')=='restore_verified' and r['all_six_debug_registers'] for r in rows),rows
        if not go.exists():go.write_text('go')
        data,errors=fixture.communicate(timeout=8)
        assert fixture.returncode==0,(mode,data,errors)
        actual=json.loads(data)
        assert actual['calls']==(1024 if mode in ('adaptive','adaptive-error') else 3),actual
        assert actual['value']==(5121 if mode in ('adaptive','adaptive-error') else 31),actual
        if mode in ('adaptive','adaptive-error'):assert actual['second']==5121,actual
        if mode=='exceptions':
            assert actual['handled']==2,actual
            codes=[r['code'] for r in rows if r.get('event')=='forwarded_exception']
            assert 0xE0421234 in codes and 0x80000003 in codes,rows
        late=sum(r.get('event')=='owned_old_layout_consumed' for r in rows)
        retained=sum(r.get('event')=='pending_owned_layout_retained' for r in rows)
        if mode in ('adaptive','adaptive-error'):
            assert len([r for r in rows if r.get('event')=='fixture_hit'])>=64,rows
            assert retained,('No real pending-old-layout evidence; inconclusive',rows)
            assert any(r.get('event')=='cleanup_pending_owned_frozen' for r in rows),rows
            assert any(r.get('event')=='cleanup_owned_exception_drained' for r in rows),rows
        result=dict(case=mode,result='PASS',trace=str(log),old_layout_consumed=late,pending_layout_retained=retained)
        RESULTS.append(result)
        return result
    finally:
        if observer and observer.poll() is None:
            Path(str(log)+'.stop').write_text('stop')
            print('Recorder still running; no forced debugger termination:',observer.pid,log)
        if fixture.poll() is None:go.write_text('go')


class RecorderTests(unittest.TestCase):
    def test_hardware_three_hits(self):native_case('three-hits')
    def test_timeout_detaches_with_readback(self):native_case('timeout')
    def test_cancel_detaches_with_readback(self):native_case('cancel')
    def test_wrong_process_birth_refused(self):native_case('wrong-birth')
    def test_production_refuses_fixture_before_attach(self):native_case('production-refusal')
    def test_foreign_breakpoint_is_not_replaced(self):native_case('foreign')
    def test_unknown_seh_and_game_int3_pass_through(self):native_case('exceptions')
    def test_two_threads_adaptive_old_pending_traps(self):native_case('adaptive')
    def test_two_threads_pending_cleanup_after_sampling_error(self):native_case('adaptive-error')


if __name__=='__main__':
    result=unittest.main(verbosity=2,exit=False).result
    data=dict(result='PASS' if result.wasSuccessful() else 'FAIL',tests=result.testsRun,game_access=False,cases=RESULTS,
              production_sha256=live.sha(ROOT/'checkpoint_title_join_live.exe'),fixture_sha256=live.sha(ROOT/'checkpoint_title_join_live_fixture.exe'))
    (ROOT/'checkpoint_title_join_live_hardware_result.json').write_text(json.dumps(data,indent=2),encoding='utf8')
    raise SystemExit(0 if result.wasSuccessful() else 1)
