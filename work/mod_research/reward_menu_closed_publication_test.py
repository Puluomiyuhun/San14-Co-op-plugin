"""Full archived owned dispatcher plus one-shot closed value publication. No live entry."""
from pathlib import Path
from datetime import datetime
import argparse,hashlib,json,struct,subprocess
import reward_menu_completion_audit as audit
P=Path(__file__).resolve().parent
PRIVATE=P.parents[2]/'mod_research'
VC=r'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive-root',type=Path,required=True)
    args=parser.parse_args()
    run=PRIVATE/'reward_menu_closed_publication_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    run.mkdir(parents=True,exist_ok=False)
    names=('reward_menu_closed_publication.h','reward_menu_closed_publication.cpp','reward_menu_closed_publication_fixture.cpp','reward_menu_closed_publication_test.py',
           'reward_menu_dispatch.h','reward_menu_dispatch.cpp','reward_menu_dispatch_bridge.asm','reward_menu_dispatch_fixture.cpp',
           'reward_menu_lifecycle.h','reward_menu_lifecycle.cpp','reward_menu_handoff_gate.h','reward_menu_handoff_gate.cpp',
           'reward_menu_observation_decode.inc','reward_menu_completion_audit.py','reward_menu_completion_fixture.cpp','reward_menu_completion_fixture.asm')
    sources={n:sha(P/n)for n in names};private={}
    result=dict(result='FAIL',game_access=False,production_permit=False,cases=[])
    try:
        evidence,_,image=audit.inspect(args.archive_root)
        pdata=image.with_name('runtime-pdata.bin');private={str(image):sha(image),str(pdata):sha(pdata)}
        raw=image.read_bytes()
        ranges=((0x67A930,0x67A9C1),(0x10A60,0x10AEA),(0x509FE0,0x50B690))+audit.RANGES[3:]+((0xEF9F20,0xEF9F41),(0x17D2400,0x17D2440))
        assert (0x509FE0,0x50B690,0x17D2400) in tuple(struct.iter_unpack('<III',pdata.read_bytes()))
        evidence['full_dispatch_ranges']=[dict(rva=a,size=b-a,sha256=hashlib.sha256(raw[a:b]).hexdigest())for a,b in ranges]
        evidence['fixture_reuse']='unchanged reward_menu_dispatch_fixture.cpp included with test-only owner namespace wrappers'
        code=run/'owned-code.bin';code.write_bytes(b''.join(raw[a:b]for a,b in ranges))
        (run/'archive-audit.json').write_text(json.dumps(evidence,indent=2)+'\n')
        flags=f'/nologo /std:c++17 /EHa /W4 /WX /O2 /MT /I"{P}"'
        lines=['@echo off',f'call "{VC}" >nul','if errorlevel 1 exit /b 1',f'ml64 /nologo /c /Fobridge.obj "{P/"reward_menu_dispatch_bridge.asm"}"','if errorlevel 1 exit /b 1']
        units=('reward_menu_closed_publication','reward_menu_dispatch','reward_menu_lifecycle','reward_menu_handoff_gate','reward_menu_closed_publication_fixture')
        for name in units:
            lines.extend([f'cl {flags} /c "{P/(name+".cpp")}" /Fo:{name}.obj','if errorlevel 1 exit /b 1'])
        lines.extend(['link /nologo /OUT:fixture.exe '+' '.join(n+'.obj'for n in units)+' bridge.obj','if errorlevel 1 exit /b 1'])
        cmd=run/'build.cmd';cmd.write_text('\n'.join(lines)+'\n')
        process=subprocess.run(['cmd','/c',str(cmd)],cwd=run,capture_output=True,timeout=120)
        (run/'build.log').write_bytes(process.stdout+process.stderr);assert process.returncode==0,'compile failed'
        for case in ('normal','normal-freed','wrong-top','duplicate'):
            process=subprocess.run([str(run/'fixture.exe'),str(code),case],cwd=run,capture_output=True,timeout=15)
            (run/(case+'.log')).write_bytes(process.stdout+process.stderr)
            assert process.returncode==0,(case,process.returncode,process.stderr.decode(errors='replace'))
            row=json.loads(process.stdout);assert row['passed']
            assert row['taken']==(1 if case in ('normal','normal-freed')else 0)
            row.update(publication_wrapper_executed=True,pre_return_rejected=True,foreign_thread_rejected=case in ('normal','normal-freed'),
                       foreign_owner_rejected=case in ('normal','normal-freed'),duplicate_publication_rejected=case in ('normal','normal-freed'),
                       cross_thread_immutable_copy=case in ('normal','normal-freed'))
            result['cases'].append(row)
        assert all(sha(P/n)==h for n,h in sources.items()),'source changed during run'
        assert all(sha(Path(n))==h for n,h in private.items()),'private input changed during run'
        result['result']='PASS'
    except Exception as exc:result['error']=repr(exc)
    result.update(sources=sources,private_inputs=private,artifacts={str(f.relative_to(run)):sha(f)for f in run.rglob('*')if f.is_file()})
    (run/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(run);print(result['result']);return int(result['result']!='PASS')
if __name__=='__main__':raise SystemExit(main())
