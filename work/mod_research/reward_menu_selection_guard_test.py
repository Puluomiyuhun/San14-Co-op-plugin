"""Owned original-selection call-source guard. No live mode or suspend permission."""
from pathlib import Path
from datetime import datetime
import argparse,hashlib,json,subprocess
import reward_menu_selection_audit as audit
from reward_menu_selection_test import RANGES,VC
P=Path(__file__).resolve().parent
PRIVATE=P.parents[2]/'mod_research'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--archive-root',type=Path,required=True);args=parser.parse_args()
    run=PRIVATE/'reward_menu_selection_guard_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True,exist_ok=False)
    names=('reward_menu_selection_guard.h','reward_menu_selection_guard.cpp','reward_menu_selection_guard_fixture.asm','reward_menu_selection_guard_fixture.cpp','reward_menu_selection_guard_test.py',
           'reward_menu_selection_fixture.cpp','reward_menu_selection_test.py','reward_menu_selection_audit.py','reward_menu_handoff_gate_audit.py')
    sources={n:sha(P/n)for n in names};private={};result=dict(result='FAIL',game_access=False,production_permit=False,cases=[])
    try:
        evidence=audit.inspect(args.archive_root);private=evidence['private_inputs'];raw=(args.archive_root/'game-runtime-image.bin').read_bytes()
        evidence['owned_ranges']=[dict(rva=a,size=b-a,sha256=hashlib.sha256(raw[a:b]).hexdigest())for a,b in RANGES]
        evidence['fixture_only_probes']=dict(call_sites=[0x68F9FB,0x21F028,0x21EDBF],tail_jump_replaced_with_owned_call=0x4FABD7,owned_ret_in_original_padding=0x4FABDC)
        evidence['scope']='Finite original call/result observation; task suspension/activation and safe rejection continuation remain unproved'
        (run/'archive-audit.json').write_text(json.dumps(evidence,indent=2)+'\n');code=run/'owned-code.bin';code.write_bytes(b''.join(raw[a:b]for a,b in RANGES))
        flags=f'/nologo /std:c++17 /EHa /W4 /WX /O2 /MT /I"{P}"'
        lines=['@echo off',f'call "{VC}" >nul','if errorlevel 1 exit /b 1',f'ml64 /nologo /c /Fobridge.obj "{P/"reward_menu_selection_guard_fixture.asm"}"','if errorlevel 1 exit /b 1']
        for name in ('reward_menu_selection_guard','reward_menu_selection_guard_fixture'):
            lines.extend([f'cl {flags} /c "{P/(name+".cpp")}" /Fo:{name}.obj','if errorlevel 1 exit /b 1'])
        lines.extend(['link /nologo /OUT:fixture.exe reward_menu_selection_guard.obj reward_menu_selection_guard_fixture.obj bridge.obj','if errorlevel 1 exit /b 1'])
        cmd=run/'build.cmd';cmd.write_text('\n'.join(lines)+'\n');cp=subprocess.run(['cmd','/c',str(cmd)],cwd=run,capture_output=True,timeout=120)
        (run/'build.log').write_bytes(cp.stdout+cp.stderr);assert cp.returncode==0,'compile failed'
        for case in ('accept-result','cancel-result','unknown-result','taskless','missing-callback','foreign-source','wrong-selection'):
            cp=subprocess.run([str(run/'fixture.exe'),str(code),case],cwd=run,capture_output=True,timeout=15)
            (run/(case+'.log')).write_bytes(cp.stdout+cp.stderr);assert cp.returncode==0,(case,cp.returncode,cp.stderr.decode(errors='replace'))
            row=json.loads(cp.stdout);assert row['passed'] and not row['production_permit'] and not row['native_suspend_proven']
            good=case in ('accept-result','cancel-result');assert row['completed']==row['taken']==int(good)
            if good:assert row['error']==0 and row['events']==row['wait_returned']==row['call_returned']==1
            else:assert row['error']!=0
            result['cases'].append(row)
        assert all(sha(P/n)==h for n,h in sources.items()),'source changed during run'
        assert all(sha(Path(n))==h for n,h in private.items()),'private input changed during run'
        result['result']='PASS'
    except Exception as exc:result['error']=repr(exc)
    result.update(sources=sources,private_inputs=private,artifacts={str(f.relative_to(run)):sha(f)for f in run.rglob('*')if f.is_file()})
    (run/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(run);print(result['result']);return int(result['result']!='PASS')
if __name__=='__main__':raise SystemExit(main())
