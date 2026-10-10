"""Execute three native-turn saves and the exported ABI in owned processes only.
The production overlay equals the DLL builder; native game business is a fixture.
"""
from datetime import datetime
from pathlib import Path
import hashlib,json,os,subprocess,sys
from a_save_three_exports_sources import sources,replace
import a_save_three_runtime_contract as wire

P=Path(__file__).resolve().parent;PRIVATE=P.parents[2]/'mod_research'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    run=PRIVATE/'a_save_three_exports_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
    overlay=run/'src';overlay.mkdir();original={}
    for p in P.iterdir():
        if p.is_file() and p.suffix in ('.py','.cpp','.h','.inc','.asm','.def'):
            original[p.name]=sha(p);(overlay/p.name).write_bytes(p.read_bytes())
    generated=sources(P)
    for n,s in generated.items():(overlay/n).write_text(s,encoding='utf-8')
    old=(P/'a_native_turn_test.py').read_text(encoding='utf-8')
    script=replace(old,"P=Path(__file__).resolve().parent;PRIVATE=P.parents[2]/'mod_research'",
        'P=Path('+repr(str(overlay))+');PRIVATE=Path('+repr(str(PRIVATE))+')')
    script=replace(script,"run=PRIVATE/'a_native_turn_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)",
        'run=Path('+repr(str(run/'native'))+');run.mkdir(parents=True)')
    script=replace(script,'from a_native_turn_fixture import transform','from a_save_three_exports_fixture import transform')
    script=replace(script,"s=s.replace('for gen in (1,):','for gen in (1,2):').replace('len(decoded)==1','len(decoded)==2')",
        "s=s.replace('for gen in (1,):','for gen in (1,2,3):').replace('len(decoded)==1','len(decoded)==3').replace('(11 if gen==1 else 21)','(11 if gen==1 else 21 if gen==2 else 1)')")
    script=script.replace("s=s.replace('from checkpoint_fresh_save_packet import'", "s=s.replace(\"PRIVATE=P.parents[2]/'mod_research'\",'PRIVATE=Path('+repr(str(PRIVATE))+')')\n    s=s.replace('from checkpoint_fresh_save_packet import'")
    extra='''
    s=s.replace("sampler='a_save_local_binding.cpp'", "sampler='a_save_local_binding.cpp', exports='a_native_turn_exports.cpp'")
    s=s.replace("defines = '","defines = '/DA_SAVE_THREE_EXPORTS_FIXTURE ")
    s=s.replace("commands += [f'cl {flags} /DCHECKPOINT_LIVE_STORAGE_BINDING_FIXTURE", "commands += [f'cl {flags} {defines} /c \\"{P / units[\\"exports\\"]}\\" /Fo:fixture_exports.obj']\\n    commands += [f'cl {flags} /DCHECKPOINT_LIVE_STORAGE_BINDING_FIXTURE")
    s=s.replace('sampler.obj turncontrol.obj fixture_runtime.obj','sampler.obj turncontrol.obj fixture_runtime.obj fixture_exports.obj')
'''
    script=replace(script,"    script=run/'generated_test.py';",
        "    s=s.replace('    # New generated fixture',"+repr(extra)+"+'    # New generated fixture')\n    script=run/'generated_test.py';")
    launcher=run/'run_native.py';launcher.write_text(script,encoding='utf-8')
    env=os.environ.copy();env['PYTHONPATH']=str(overlay);env['PYTHONUTF8']='1';env['PYTHONDONTWRITEBYTECODE']='1'
    result=dict(result='FAIL',game_access=False,native_game_business_fixture=True,actual_native_turn=True,
        actual_exported_snapshot=True,actual_exported_request_next=True,production_dll_executed_three_saves=False,
        capacity=3,abi_magic=wire.MAGIC)
    try:
        proc=subprocess.run([sys.executable,'-B','-X','utf8',str(launcher)],env=env,capture_output=True,text=True,errors='replace',timeout=260)
        (run/'driver.log').write_text(proc.stdout+proc.stderr,encoding='utf-8')
        child=json.loads((run/'native/result.json').read_text());result['execution']=child
        assert proc.returncode==0 and child['result']=='PASS','owned native exports failed'
        rows=[]
        for n in (1,2,3):
            f=run/f'native/case/normal/snapshot-{n}.bin'
            value=wire.decode(wire.Snapshot,'Snapshot',bytes([0x37])*32,f.read_bytes())
            assert value.mailboxCount==value.saveGeneration==n and list(value.mailboxStates)==[5]*n+[0]*(3-n)
            rows.append(dict(generation=n,sha256=sha(f),snapshot=wire.values(value)))
        used=set(child['execution']['sources'])|{'a_save_three_exports_sources.py','a_save_three_exports_fixture.py','a_save_three_exports_test.py','a_save_three_cycle_sources.py','a_save_three_runtime_contract.py'}
        result['sources']={str(P/n):original[n] for n in sorted(used)}
        assert all(sha(Path(n))==h for n,h in result['sources'].items()),'used source changed'
        result.update(result='PASS',snapshots=rows)
    except Exception as e:result['error']=repr(e)
    result['generated_sources']={str(overlay/n):sha(overlay/n) for n in generated}
    result['artifacts']={str(p.relative_to(run)):sha(p) for p in run.rglob('*') if p.is_file() and p!=run/'result.json'}
    path=run/'result.json';path.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(result=result['result'],path=str(path))));return result['result']!='PASS'
if __name__=='__main__':raise SystemExit(main())
