"""Compose queued Save and covered User successors in the existing scoped host."""
from pathlib import Path
from datetime import datetime
import subprocess,sys,hashlib,json,difflib,os
P=Path(__file__).resolve().parent;PRIVATE=P.parents[2]/'mod_research'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    run=PRIVATE/'a_save_abort_pending_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
    old=(P/'a_save_scoped_input_test.py').read_text();s=old.replace('P=Path(__file__).resolve().parent','P=Path('+repr(str(P))+')')
    s=s.replace('from checkpoint_fresh_save_packet import','sys.path.insert(0,'+repr(str(P))+')\nfrom checkpoint_fresh_save_packet import')
    s=s.replace("run=PRIVATE/'a_save_scoped_input_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)",'run=Path('+repr(str(run/'case'))+');run.mkdir(parents=True)')
    s=s.replace("CASES=('normal',)","CASES=('normal','cursor-drift')")
    s=s.replace("input='a_save_scoped_gate.cpp'","input='a_save_covered_gate.cpp'")
    s=s.replace("host='a_save_dispatch_host.cpp'","host='a_save_abort_host.cpp'")
    at=s.index('    original=(P/')
    s=s[:at]+'''    s=s.replace("owner='planning_checkpoint_save_owner.cpp'","owner='a_save_abort_pending_owner.cpp'")
    s=s.replace("input_fixture_asm='a_save_upstream_fixture.asm'","input_fixture_asm='a_save_covered_integration_fixture.asm'")
    s=s.replace("defines = '","defines = '/DA_SAVE_PENDING_USER_SUCCESS ")
'''+s[at:]
    final=r''' report::Report rr{};need(report::Snapshot(session,rr),"report snapshot");a_save_covered_owner::Report cr{};need(a_save_covered_owner::Snapshot(session,cr),"covered counters");
 if(coveredCase==L"normal"){
  need(writerBlocked&&writerReleased&&!h.lease&&!h.frame&&!u.active_scopes&&!u.save.active&&u.save.status==fs::Status::Complete&&!failed&&coveredCalls==5&&queuedWindows==1&&!rr.revoked&&!rr.afterRejected&&!rr.storageRejected,"three windows complete and release");
  need(h.observations==1&&h.submits==1&&h.copies==1&&h.releases==1&&d.submits==1&&d.copies==1&&u.save.completed_requests==1&&nativeBinds==1&&cr.selected==5&&cr.claimed==5&&cr.returned==5&&cr.finally==5&&!cr.rejected,"one complete Controller Owner IPC save");
 }else if(coveredCase==L"cursor-drift")need(writerBlocked&&writerReleased&&!h.lease&&!h.frame&&!u.active_scopes&&!u.save.active&&!h.copies&&h.releases==1&&!u.save_lane&&rr.revoked&&u.save.status==fs::Status::Uncertain&&u.save.error==54&&!u.save.file_bytes_verified&&!ASaveCoveredGateFirstFailure.stage,"report drift aborted-drained with unchanged failure and no artifact");
 else need(writerBlocked&&writerReleased&&!h.lease&&!h.frame&&!u.active_scopes&&!u.save.active&&!h.copies&&h.releases==1&&u.save.status==fs::Status::Complete&&u.save.file_bytes_verified&&m.records[0].state==mb::State::Unknown&&ASaveCoveredGateFirstFailure.stage==4,"rejected queue drains bound native work without delivering");
'''
    injected='''
    helper=(P/'a_save_pending_user_fixture.inc').read_text()
    at=fixture.index('static void completeOwnedSave()');fixture=fixture[:at]+helper+fixture[at:]
    fixture=fixture.replace('for(unsigned i=0;i<5;++i){\\n  fs::Artifact pending{};', 'for(unsigned i=0;i<5;++i){\\n  coveredUser();\\n  fs::Artifact pending{};')
    fixture=fixture.replace('    completeOwnedSave();','    queuedGame();pendingUser();completeOwnedSave();')
    fixture=fixture.replace('else if(h.state==dh::State::Submitted){','else if(h.state==dh::State::Submitted&&!nativeBinds){')
    fixture=fixture.replace('const bool normal=caseName==L"normal";','coveredCase=caseName;const bool normal=true;')
    fixture=fixture.replace('const bool normal=clientMode==L"normal";','const bool normal=true;')
    fixture=fixture.replace('parentReport.error==a_save_parent_adapter::Error::None&&','(parentReport.error==a_save_parent_adapter::Error::None||(coveredCase==L"cursor-drift"&&parentReport.error==a_save_parent_adapter::Error::Host))&&')
    fixture=fixture.replace('need(head.status==unsigned(ip::Status::Ok),"Copy status");','if(head.status!=unsigned(ip::Status::Ok)){CloseHandle(pipe);return 0;}')
    begin=fixture.index(' need(writerBlocked&&writerReleased')
    end=fixture.index(' printf(',begin)
    fixture=fixture[:begin]+FINAL+fixture[end:]
'''
    injected+='\n    fixture=\'#include "a_save_abort_owner.h"\\n\'+fixture\n    fixture=fixture.replace(\'bool triggered=false,writerBlocked=false,writerReleased=false;\', \'bool triggered=false,writerBlocked=false,writerReleased=false,abortBlocked=false;\')\n    fixture=fixture.replace(\'queuedGame();pendingUser();completeOwnedSave();\',\'queuedGame();pendingUser();completeOwnedSave();if(coveredCase==L"cursor-drift"){put<uintptr_t>(user+0x50,1);box.Stop();}\')\n    fixture=fixture.replace(\'host.Snapshot(h);if(h.releases\', \'host.Snapshot(h);if(coveredCase==L"cursor-drift"&&nativeBinds&&!abortBlocked){a_save_abort::Receipt receipt{};need(h.lease&&!a_save_abort::Snapshot(b,1,GetCurrentThreadId(),receipt),"active native task prevents retirement");bool foreign=true;std::thread wrongAbort([&]{foreign=a_save_abort::Retire(*session,1);});wrongAbort.join();need(!foreign&&!a_save_abort::Retire(*session,1),"wrong TID and outside Parent boundary cannot retire");put<uintptr_t>(user+0x50,0);abortBlocked=true;}if(h.releases\')\n    fixture=fixture.replace(\'if(WaitForSingleObject(serverDone,0)==WAIT_OBJECT_0)break;\', \'if(WaitForSingleObject(serverDone,0)==WAIT_OBJECT_0&&!h.lease)break;\')\n    fixture=fixture.replace(\'report::Report rr{};\', \'a_save_abort::Receipt abortReceipt{};if(coveredCase==L"cursor-drift")need(abortBlocked&&a_save_abort::Snapshot(b,1,GetCurrentThreadId(),abortReceipt)&&abortReceipt.ownerError==unsigned(u.error)&&abortReceipt.driverError==u.save.error&&abortReceipt.thread==h.lastReleaseThread&&m.records[0].state==mb::State::Unknown,"real terminal receipt retains error and unknown mailbox");report::Report rr{};\')\n'
    injected=injected.replace('FINAL',repr(final));at=s.index('    # New generated fixture');s=s[:at]+injected+s[at:]
    s=s.replace("python_pins={'checkpoint_fresh_save_packet.py':sha(P/'checkpoint_fresh_save_packet.py')}","python_pins={n:sha(P/n) for n in ('checkpoint_fresh_save_packet.py','a_save_scoped_input_test.py','a_save_covered_integration_test.py','a_save_pending_user_fixture.inc','a_save_abort_pending_test.py','a_save_abort_owner.h')}")
    script=run/'generated_test.py';script.write_text(s,encoding='utf-8');(run/'generator.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),s.splitlines(True))),encoding='utf-8')
    result={'result':'FAIL','game_access':False}
    try:
        env=os.environ.copy();env['PYTHONUTF8']='1';r=subprocess.run([sys.executable,str(script)],env=env,capture_output=True,text=True,errors='replace',timeout=220);(run/'driver.log').write_text(r.stdout+r.stderr,encoding='utf-8')
        child=json.loads((run/'case'/'result.json').read_text());result['execution']=child;assert r.returncode==0 and child['result']=='PASS';result['result']='PASS'
    except Exception as e:result['error']=repr(e)
    result['generated_test_sha256']=sha(script);out=run/'result.json';out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'result':result['result'],'path':str(out)}));return 0 if result['result']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
