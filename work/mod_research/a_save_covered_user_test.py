"""Reproduce defects using the existing scoped composition, never a game."""
from pathlib import Path
from datetime import datetime
import subprocess,sys,hashlib,json,difflib,os
P=Path(__file__).resolve().parent;PRIVATE=P.parents[2]/'mod_research'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    run=PRIVATE/'a_save_covered_user_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
    old=(P/'a_save_scoped_input_test.py').read_text();s=old.replace('P=Path(__file__).resolve().parent','P=Path('+repr(str(P))+')')
    s=s.replace('from checkpoint_fresh_save_packet import','sys.path.insert(0,'+repr(str(P))+')\nfrom checkpoint_fresh_save_packet import')
    s=s.replace("run=PRIVATE/'a_save_scoped_input_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)",'run=Path('+repr(str(run/'case'))+');run.mkdir(parents=True)')
    final=r''' report::Report rr{};need(report::Snapshot(session,rr),"report snapshot");
 need(writerBlocked&&!writerReleased&&h.lease&&!h.frame&&!u.active_scopes&&!u.save.active&&u.save.status==fs::Status::Uncertain&&u.save.error==54&&!h.copies&&!h.releases&&coveredCalls==5&&rr.entrySuppressed==0&&rr.afterRejected==5&&rr.storageRejected==1&&queuedGateError==6&&queuedOwnerError==0&&queuedOwnerStopped,"FAIL_REPRODUCED exact rejection chain");
 printf("DIAGNOSTIC gate=%u earlyOwner=%u stopped=%u covered=%u afterRejected=%llu storageRejected=%llu status=%u error=%u lease=%u\n",queuedGateError,queuedOwnerError,queuedOwnerStopped,coveredCalls,rr.afterRejected,rr.storageRejected,unsigned(u.save.status),u.save.error,unsigned(h.lease));
'''
    injected='''
    helper=(P/'a_save_covered_user_fixture.inc').read_text()
    at=fixture.index('static void completeOwnedSave()');fixture=fixture[:at]+helper+fixture[at:]
    fixture=fixture.replace('for(unsigned i=0;i<5;++i){\\n  fs::Artifact pending{};', 'for(unsigned i=0;i<5;++i){\\n  coveredUser();\\n  fs::Artifact pending{};')
    fixture=fixture.replace('    completeOwnedSave();','    queuedGame();completeOwnedSave();')
    fixture=fixture.replace('else if(h.state==dh::State::Submitted){','else if(h.state==dh::State::Submitted&&!nativeBinds){')
    fixture=fixture.replace('need(head.status==unsigned(ip::Status::Ok),"Copy status");','if(head.status!=unsigned(ip::Status::Ok)){CloseHandle(pipe);return 0;}')
    begin=fixture.index(' need(writerBlocked&&writerReleased')
    end=fixture.index(' printf(',begin)
    fixture=fixture[:begin]+FINAL+fixture[end:]
'''
    injected=injected.replace('FINAL',repr(final))
    at=s.index('    # New generated fixture');s=s[:at]+injected+s[at:]
    s=s.replace("if ok and case=='normal':","if False:").replace('len(decoded)==1','len(decoded)==0')
    s=s.replace("python_pins={'checkpoint_fresh_save_packet.py':sha(P/'checkpoint_fresh_save_packet.py')}","python_pins={n:sha(P/n) for n in ('checkpoint_fresh_save_packet.py','a_save_scoped_input_test.py','a_save_covered_user_test.py','a_save_covered_user_fixture.inc')}")
    script=run/'generated_test.py';script.write_text(s,encoding='utf-8');(run/'generator.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),s.splitlines(True))),encoding='utf-8')
    result={'result':'FAIL','application_result':'UNPROVEN','game_access':False}
    try:
        env=os.environ.copy();env['PYTHONUTF8']='1';r=subprocess.run([sys.executable,str(script)],env=env,capture_output=True,text=True,errors='replace',timeout=220);(run/'driver.log').write_text(r.stdout+r.stderr,encoding='utf-8')
        child=json.loads((run/'case'/'result.json').read_text());result['execution']=child;assert r.returncode==0 and child['result']=='PASS';result['result']='PASS';result['application_result']='FAIL_REPRODUCED'
    except Exception as e:result['error']=repr(e)
    result['generated_test_sha256']=sha(script);out=run/'result.json';out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'result':result['result'],'path':str(out)}));return 0 if result['result']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
