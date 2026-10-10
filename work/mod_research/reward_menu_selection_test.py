"""Bounded owned execution of original selection caller/creator/result branches; no live mode."""
from pathlib import Path
from datetime import datetime
import argparse,hashlib,json,struct,subprocess
import reward_menu_selection_audit as audit
P=Path(__file__).resolve().parent
PRIVATE=P.parents[2]/'mod_research'
VC=r'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat'
RANGES=((0x68F760,0x68FBE3),(0x21ED10,0x21EDF8),(0x21EFB0,0x21F12D),(0x50B690,0x50B6FF),
        (0x22C450,0x22C4FF),(0x509450,0x509455),(0x509EC0,0x509EE2),(0x509E10,0x509EBD),
        (0x2D0350,0x2D036B),(0x4FABD0,0x4FABDC),(0x4F9D30,0x4F9D43),(0x509F50,0x509FD2),(0xEF9F20,0xEF9F41))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--archive-root',type=Path,required=True);args=parser.parse_args()
    run=PRIVATE/'reward_menu_selection_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True,exist_ok=False)
    names=('reward_menu_selection_fixture.cpp','reward_menu_selection_test.py','reward_menu_selection_audit.py','reward_menu_handoff_gate_audit.py')
    sources={n:sha(P/n)for n in names};private={};result=dict(result='FAIL',game_access=False,production_permit=False,cases=[])
    try:
        evidence=audit.inspect(args.archive_root);private=evidence['private_inputs']
        raw=(args.archive_root/'game-runtime-image.bin').read_bytes()
        original_base=struct.unpack_from('<Q',raw,0x1331078+5*8)[0]-0x67A930
        for slot,rva in ((0,0x2D0350),(2,0x4FABD0),(4,0x4F9D30)):
            assert struct.unpack_from('<Q',raw,0x12A7010+slot*8)[0]==original_base+rva,'return callback vtable differs'
        # Exact leaves fix current-state source and callback result destination.
        assert raw[0x509450:0x509455]==bytes.fromhex('488b4148c3')
        assert raw[0x4FABD0:0x4FABDC]==bytes.fromhex('488b12488b4908e974f30000')
        evidence['owned_ranges']=[dict(rva=a,size=b-a,sha256=hashlib.sha256(raw[a:b]).hexdigest())for a,b in RANGES]
        evidence['return_binding']=dict(current_rva=0x509450,current_offset=0x48,callback_vtable=0x12A7010,
            clone=0x2D0350,invoke=0x4FABD0,handler=0x509F50,parent_result_offset=0x58,
            result_one_event=0x7FFFFFFD,result_zero_event=0x7FFFFFFE,other_event='retains previous parent result')
        (run/'archive-audit.json').write_text(json.dumps(evidence,indent=2)+'\n')
        code=run/'owned-code.bin';code.write_bytes(b''.join(raw[a:b]for a,b in RANGES))
        lines=['@echo off',f'call "{VC}" >nul','if errorlevel 1 exit /b 1',
               f'cl /nologo /std:c++17 /EHa /W4 /WX /O2 /MT "{P/"reward_menu_selection_fixture.cpp"}" /Fe:fixture.exe /Fo:fixture.obj',
               'if errorlevel 1 exit /b 1']
        cmd=run/'build.cmd';cmd.write_text('\n'.join(lines)+'\n')
        cp=subprocess.run(['cmd','/c',str(cmd)],cwd=run,capture_output=True,timeout=120);(run/'build.log').write_bytes(cp.stdout+cp.stderr);assert cp.returncode==0,'compile failed'
        for mode in ('accept-result','cancel-result','unknown-result','taskless'):
            cp=subprocess.run([str(run/'fixture.exe'),str(code),mode],cwd=run,capture_output=True,timeout=15)
            (run/(mode+'.log')).write_bytes(cp.stdout+cp.stderr)
            assert cp.returncode==0,(mode,cp.returncode,cp.stderr.decode(errors='replace'))
            row=json.loads(cp.stdout);assert row['passed'] and not row['native_suspend_proven'] and not row['production_permit']
            assert row['original_callback_result_handler']==(mode!='taskless') and row['activation_double']==(mode!='taskless')
            assert row['queue_remaining']==(1 if mode=='taskless'else 0)
            result['cases'].append(row)
        assert all(sha(P/n)==h for n,h in sources.items()),'source changed during run'
        assert all(sha(Path(n))==h for n,h in private.items()),'private input changed during run'
        result['result']='PASS'
    except Exception as exc:result['error']=repr(exc)
    result.update(sources=sources,private_inputs=private,artifacts={str(f.relative_to(run)):sha(f)for f in run.rglob('*')if f.is_file()})
    (run/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(run);print(result['result']);return int(result['result']!='PASS')
if __name__=='__main__':raise SystemExit(main())
