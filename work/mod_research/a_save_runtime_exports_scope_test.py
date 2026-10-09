"""Reuse the single-period scoped fixture to execute the production cache successors."""
from pathlib import Path
from datetime import datetime
import subprocess,sys,hashlib,json,difflib
P=Path(__file__).resolve().parent;PRIVATE=P.parents[2]/'mod_research'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    run=PRIVATE/'a_save_runtime_exports_scope_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
    old=(P/'a_save_scoped_input_test.py').read_text();s=old.replace('P=Path(__file__).resolve().parent','P=Path('+repr(str(P))+')')
    s=s.replace('from checkpoint_fresh_save_packet import', 'sys.path.insert(0,'+repr(str(P))+')\nfrom checkpoint_fresh_save_packet import')
    s=s.replace("run=PRIVATE/'a_save_scoped_input_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)", 'run=Path('+repr(str(run/'case'))+');run.mkdir(parents=True)')
    s=s.replace("adapter='a_save_parent_adapter.cpp'", "adapter='a_save_runtime_publish_parent.cpp'").replace("parent_bridge='b_reload_parent_bridge.cpp'", "parent_bridge='a_save_runtime_publish_parent_bridge.cpp'")
    marker='    original=(P/'
    pos=s.index(marker);s=s[:pos]+'''    s=s.replace("input_bridge='a_save_action_gate_bridge.cpp'","input_bridge='a_save_runtime_publish_gate.cpp'").replace("bridge='a_reward_save_owner_bridge.cpp'","bridge='a_save_runtime_publish_user.cpp'")
'''+s[pos:]
    marker='    # New generated fixture'
    pos=s.index(marker);s=s[:pos]+'''    helper=(P/'a_save_runtime_exports_scope_fixture.inc').read_text()
    at=fixture.index('static void executionStop(')
    fixture=fixture[:at]+helper+fixture[at:]
    fixture=fixture.replace('parentDispatch();','parentDispatch();verifyPublishCache(host);')
    at=fixture.index(' if(normal)need(h.observations==1')
    fixture=fixture[:at]+' box.Stop();parent.Stop();parentDispatch();verifyPublishCache(host);session->Snapshot(u);need(u.stopped&&cacheSawLease&&cacheChecks>=3,"actual Stop and FINALLY cache preserve drained lease evidence");\\n'+fixture[at:]
'''+s[pos:]
    # Pin this orchestration and the exact injected source as dependencies.
    s=s.replace("python_pins={'checkpoint_fresh_save_packet.py':sha(P/'checkpoint_fresh_save_packet.py')}","python_pins={n:sha(P/n) for n in ('checkpoint_fresh_save_packet.py','a_save_scoped_input_test.py','a_save_runtime_exports_scope_test.py','a_save_runtime_exports_scope_fixture.inc')}")
    script=run/'generated_test.py';script.write_text(s);(run/'generator.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),s.splitlines(True))))
    result={'result':'FAIL','game_access':False}
    try:
        r=subprocess.run([sys.executable,str(script)],capture_output=True,text=True,errors='replace',timeout=220);(run/'driver.log').write_text(r.stdout+r.stderr)
        child=json.loads((run/'case'/'result.json').read_text());result['execution']=child;assert r.returncode==0 and child['result']=='PASS';result['result']='PASS'
    except Exception as e:result['error']=repr(e);(run/'failure.log').write_text(repr(e)+'\n'+str(getattr(e,'stdout',''))+'\n'+str(getattr(e,'stderr','')))
    result['generated_test_sha256']=sha(script);out=run/'result.json';out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'result':result['result'],'path':str(out)}));return 0 if result['result']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
