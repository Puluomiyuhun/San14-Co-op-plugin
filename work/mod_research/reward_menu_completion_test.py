"""Offline native completion source and read-only authority correlation tests."""
from copy import deepcopy
from datetime import datetime
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

P=Path(__file__).resolve().parent;ROOT=P.parent.parent
sys.path.insert(0,str(ROOT/'outputs'/'san14-link'))
import reward_menu_completion_audit as audit
import reward_menu_completion_analysis as analysis
import reward_menu_handoff_gate_test as predecessor

MODES=('normal','duplicate-pop','late-duplicate','changed-top-push','changed-top-replace','queued-only','empty-consume')


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,value):Path(p).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sources():
    result=predecessor.sources()
    for name in ('reward_menu_completion_audit.py','reward_menu_completion_analysis.py','reward_menu_completion_test.py',
                 'reward_menu_completion_fixture.cpp','reward_menu_completion_fixture.asm'):
        result[str((P/name).relative_to(ROOT)).replace('\\','/')]=sha(P/name)
    return result


def correlate(run,traces):
    from reward_ready_flow_test import Harness
    from reward_ready_flow_fixture import capture_inputs
    from reward_menu_capture import CaptureSession
    h=Harness(run/'tls',None);rows=[]
    try:
        preview,context=capture_inputs(h.flow.host)
        preview['officer_ids']=[97,759]
        capture=CaptureSession();capture.capture(preview,context,capture_id='e'*32,now_tick=100)
        proposal=capture.confirm('e'*32,preview,context,now_tick=100)
        packet=proposal.packet();first=h.checked('A',packet);again=h.checked('A',packet)
        assert first['ordinal']==again['ordinal'] and again['duplicate']
        def obtain(p=preview,attachment=None,request=None,report=None):
            return analysis.read_authority_result(h.flow.host.journal.path,h.flow.scope,attachment or h.port.attachment_id,
                'A',request or packet['request_id'],p,report or h.flow.host.report())
        try:obtain()
        except ValueError:rows.append(dict(case='queued_acceptance_is_not_applied_authority',passed=True,kind='real_TLS_read_only_journal'))
        else:raise AssertionError('Queued command accepted as applied result')
        assert h.flow.pump_one()['sequence']==1 and h.guest.call('consume_reward')['ack']['ok']
        db_before=sha(h.flow.host.journal.path);authority=obtain();assert sha(h.flow.host.journal.path)==db_before
        rows.append(dict(case='real_TLS_once_and_read_only_APPLIED_tip',passed=True,kind='real_TLS_business_models',native_game_execution=False))
        def expect_reader_reject(label,**kwargs):
            try:obtain(**kwargs)
            except ValueError:rows.append(dict(case=label,passed=True,kind='authority_reader_refusal'))
            else:raise AssertionError(label)
        expect_reader_reject('wrong_request',request='0'*32)
        expect_reader_reject('wrong_attachment',attachment='0'*32)
        changed=deepcopy(preview);changed['officer_ids']=[97];expect_reader_reject('different_proposal',p=changed)
        changed=deepcopy(preview);changed['funding_city_id']=20;expect_reader_reject('different_funding_city',p=changed)
        changed=deepcopy(preview);changed['officer_ids']=[True];expect_reader_reject('bool_officer',p=changed)
        report=h.flow.host.report();report['state_sha256']='0'*64;expect_reader_reject('stale_result_state',report=report)
        report=h.flow.host.report();report['sequence']=True;expect_reader_reject('bool_result_sequence',report=report)
        expected={'normal':'MATCHING_TEARDOWN_OBSERVED_WITHOUT_LIFETIME_LEASE','duplicate-pop':'MULTIPLE_POP_OBSERVED',
            'late-duplicate':'MULTIPLE_POP_OBSERVED','changed-top-push':'WRONG_MENU_TORN_DOWN','changed-top-replace':'WRONG_MENU_TORN_DOWN',
            'queued-only':'QUEUED_NOT_CLOSED','empty-consume':'NO_COMPLETION_OBSERVED'}
        sourcekeys=('pid','birth','base','thread','menu','user','root','world')
        for mode,trace in traces.items():
            source={k:trace[k] for k in sourcekeys};result=analysis.analyze(trace,authority,context,source,now_tick=100)
            assert result['classification']==expected[mode] and not result['can_queue_close'] and not result['production_permit'],(mode,result)
            write(run/(mode+'.analysis.json'),result);rows.append(dict(case='analyze_'+mode,passed=True,kind='read_only_correlation',classification=result['classification']))
        baseline=traces['normal'];source={k:baseline[k] for k in sourcekeys}
        variants=[]
        def vary(label,fn):
            t=deepcopy(baseline);c=deepcopy(context);s=deepcopy(source);fn(t,c,s);variants.append((label,t,c,s))
        vary('different_native_thread',lambda t,c,s:t['events'][2].update(thread=s['thread']+1))
        vary('different_native_date',lambda t,c,s:t.update(date=[203,8,21]))
        vary('changed_menu_pointer',lambda t,c,s:s.update(menu=s['menu']+16))
        vary('different_attachment_scope',lambda t,c,s:c.update(attachment_id='0'*32))
        vary('different_epoch_scope',lambda t,c,s:c.update(epoch='0'*32))
        vary('expired_menu_draft',lambda t,c,s:c.update(expires_tick=99))
        vary('sequence_gap',lambda t,c,s:t['events'][2].update(seq=9))
        vary('foreign_return_pc',lambda t,c,s:t['events'][2].update(caller_rva=0x1234))
        vary('fabricated_lifetime_lock',lambda t,c,s:t.update(menu_lifetime_lock=True))
        vary('unknown_event_field',lambda t,c,s:t['events'][2].update(permit=True))
        for label,t,c,s in variants:
            r=analysis.analyze(t,authority,c,s,now_tick=100)
            assert r['classification']=='INCOMPLETE_EVIDENCE' and not r['can_queue_close'],(label,r)
            rows.append(dict(case=label,passed=True,kind='correlation_refusal'))
        # A newer applied command makes this exact old menu/request non-tip.
        h.submit('A');h.flow.pump_one();assert h.guest.call('consume_reward')['ack']['ok']
        expect_reader_reject('old_receipt_after_next_command')
        assert not analysis.analyze(baseline,None,context,source,now_tick=100)['can_queue_close']
        rows.append(dict(case='no_authority_never_authorizes_close',passed=True,kind='correlation_refusal'))
        return rows
    finally:h.close()


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--archive-root',type=Path,required=True);args=parser.parse_args()
    run=P/'reward_menu_completion_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
    result=dict(schema='san14.reward-menu-completion-owned-tests.v1',result='FAIL',sources=sources(),cases=[],game_access=False,production_permit=False)
    image=None
    try:
        evidence,code,image=audit.inspect(args.archive_root);write(run/'archive-audit.json',evidence);result['cases'].extend(evidence['checks']);(run/'owned-code.bin').write_bytes(code)
        flags=f'/nologo /std:c++17 /EHsc /W4 /WX /I"{P}"'
        cmds=[f'ml64 /nologo /c /Focompletion.obj "{P/"reward_menu_completion_fixture.asm"}"',
            f'cl {flags} "{P/"reward_menu_completion_fixture.cpp"}" completion.obj /Fe:fixture.exe /Fo:fixture.obj /link /INCREMENTAL:NO']
        build=run/'build.cmd';build.write_text('@echo off\nsetlocal\ncall "'+predecessor.VC+'" >nul\nif errorlevel 1 exit /b 1\n'+
            '\n'.join(c+'\nif errorlevel 1 exit /b 1' for c in cmds)+'\n',encoding='utf-8')
        p=subprocess.run(['cmd','/c',str(build)],cwd=run,capture_output=True,timeout=120,creationflags=subprocess.CREATE_NO_WINDOW);(run/'build.log').write_bytes(p.stdout+p.stderr)
        if p.returncode:raise RuntimeError('Build failed: '+str(run/'build.log'))
        result['fixture_sha256']=sha(run/'fixture.exe');traces={}
        for mode in MODES:
            p=subprocess.run([str(run/'fixture.exe'),str(run/'owned-code.bin'),mode],capture_output=True,timeout=15,creationflags=subprocess.CREATE_NO_WINDOW)
            (run/(mode+'.stdout.txt')).write_bytes(p.stdout);(run/(mode+'.stderr.txt')).write_bytes(p.stderr)
            if p.returncode:raise RuntimeError(f'{mode}: exit {p.returncode}; {p.stderr!r}')
            trace=json.loads(p.stdout);assert trace['passed'];traces[mode]=trace
            result['cases'].append(dict(case=mode,passed=True,kind='actual_CPU_archive_queue_and_pop_with_explicit_helpers',trace=trace))
        result['cases'].extend(correlate(run,traces));result['result']='PASS'
    except Exception as e:result['error']=repr(e)
    finally:
        result['source_end']=sources();result['sources_unchanged']=result['source_end']==result['sources']
        if image:
            result['image_end_sha256']=sha(image);result['pdata_end_sha256']=sha(image.with_name('runtime-pdata.bin'))
            result['archive_unchanged']=result['image_end_sha256']==audit.IMAGE_SHA and result['pdata_end_sha256']==evidence['pdata_sha256']
        if not result['sources_unchanged'] or not result.get('archive_unchanged'):result['result']='FAIL'
        write(run/'result.json',result)
    print(json.dumps(dict(result=result['result'],checks=len(result['cases']),path=str(run/'result.json'),error=result.get('error'))))
    return int(result['result']!='PASS')


if __name__=='__main__':raise SystemExit(main())
