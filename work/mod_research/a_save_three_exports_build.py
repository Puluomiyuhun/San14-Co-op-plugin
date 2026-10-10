"""Build a dedicated three-save production DLL and execute owned ABI checks.
No discovery, game process access or installation. Private overlays only.
"""
from datetime import datetime
import ctypes
import hashlib,json,os,shutil,subprocess,sys
from pathlib import Path
from a_save_three_exports_sources import sources,replace
import a_save_three_runtime_contract as contract

P=Path(__file__).resolve().parent
PRIVATE=P.parents[2]/'mod_research'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    run=PRIVATE/'a_save_three_exports_build_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
    overlay=run/'src';overlay.mkdir()
    original={}
    for p in P.iterdir():
        if p.is_file() and p.suffix in ('.py','.cpp','.h','.inc','.asm','.def'):
            original[p.name]=sha(p);(overlay/p.name).write_bytes(p.read_bytes())
    generated=sources(P)
    for n,s in generated.items():(overlay/n).write_text(s,encoding='utf-8')
    old=(P/'a_native_turn_runtime_build.py').read_text(encoding='utf-8')
    s=replace(old,'P = Path(__file__).resolve().parent','P = Path('+repr(str(overlay))+')')
    s=replace(s,"PRIVATE = P.parents[2] / 'mod_research'",'PRIVATE = Path('+repr(str(PRIVATE))+')')
    s=replace(s,"run = PRIVATE / 'a_native_turn_runtime_runs' / datetime.now().strftime('%Y%m%d-%H%M%S-%f')",'run = Path('+repr(str(run/'production'))+')')
    marker="    script = run / 'generated_exports_build.py'"
    injection="    source = source.replace(\"PRIVATE=P.parents[2]/'mod_research'\", 'PRIVATE=Path('+repr(str(PRIVATE))+')')\n"
    s=replace(s,marker,injection+marker)
    launcher=run/'build_production.py';launcher.write_text(s,encoding='utf-8')
    env=os.environ.copy();env['PYTHONPATH']=str(overlay);env['PYTHONDONTWRITEBYTECODE']='1';env['PYTHONUTF8']='1'
    result=dict(result='FAIL',schema='san14.a-three-runtime-exports-build.v1',game_access=False,
        abi_magic=contract.MAGIC,capacity=3,installed=False,native_three_gameplay_verified=False)
    try:
        child=subprocess.run([sys.executable,'-B','-X','utf8',str(launcher)],env=env,capture_output=True,text=True,errors='replace',timeout=300)
        (run/'driver.log').write_text(child.stdout+child.stderr,encoding='utf-8')
        report=json.loads((run/'production/result.json').read_text());result['execution']=report
        assert child.returncode==0 and report['result']=='PASS','production export build/ABI failed'
        abi=report['execution'];native_schema=json.loads(Path(abi['schema']).read_text())
        for name,kind in contract.TYPES.items():
            row=native_schema['structures'][name];assert row['size']==ctypes.sizeof(kind),name
            assert set(row['fields'])=={n for n,_ in kind._fields_},name
            for field,typ in kind._fields_:
                assert row['fields'][field]['offset']==getattr(kind,field).offset,(name,field)
                assert row['fields'][field]['size']==ctypes.sizeof(typ),(name,field)
        dll=Path(abi['dll']);result['production_dll']=dict(path=str(dll),sha256=sha(dll))
        result['schema_snapshot']=dict(path=abi['schema'],sha256=sha(Path(abi['schema'])))
        dependency=dll.parent/'checkpoint_planning_hold.dll'
        result['dependency_dll']=dict(path=str(dependency),sha256=sha(dependency))
        # Same DLL and same generated header, separate owned ABI subprocess.
        repeat=(P/'a_save_repeat_exports_test.py').read_text(encoding='utf-8')
        repeat=replace(repeat,'import a_save_repeat_contract as wire','import a_save_three_repeat_contract as wire')
        a=repeat.index('def contract_checks(schema):');b=repeat.index('\ndef main():',a)
        repeat=repeat[:a]+'''def contract_checks(schema):
    for name,kind in wire.TYPES.items():
        native=schema['structures'][name]
        assert native['size']==C.sizeof(kind),name
        assert set(native['fields'])=={f for f,_ in kind._fields_}
        for field,typ in kind._fields_:
            assert native['fields'][field]==dict(offset=getattr(kind,field).offset,size=C.sizeof(typ)),(name,field)
    nonce=bytes([0x37])*32
    q=wire.envelope(wire.Snapshot,'RepeatSnapshot',nonce)
    assert wire.decode(wire.Snapshot,'RepeatSnapshot',nonce,bytes(q)).header.magic==0x33585241
    q.header.magic=0x31585241
    try:wire.decode(wire.Snapshot,'RepeatSnapshot',nonce,bytes(q))
    except ValueError:pass
    else:raise AssertionError('Old repeat header accepted')

'''+repeat[b:]
        repeat=replace(repeat,'P = Path(__file__).resolve().parent','P = Path('+repr(str(overlay))+')')
        repeat=replace(repeat,"run = PRIVATE / 'a_save_repeat_exports_runs' / datetime.now().strftime('%Y%m%d-%H%M%S-%f')",'run = Path('+repr(str(run/'repeat'))+')')
        check=run/'repeat_check.py';check.write_text(repeat,encoding='utf-8')
        proc=subprocess.run([sys.executable,'-B','-X','utf8',str(check),'--dll',str(dll)],env=env,capture_output=True,text=True,errors='replace',timeout=120)
        (run/'repeat-driver.log').write_text(proc.stdout+proc.stderr,encoding='utf-8')
        rep_path=run/'repeat/result.json';rep=json.loads(rep_path.read_text())
        assert proc.returncode==0 and rep['result']=='PASS','additive ABI failed'
        result['repeat_abi_checks']=dict(path=str(rep_path),sha256=sha(rep_path))
        result['schema_repeat']=dict(path=str(run/'repeat/schema.json'),sha256=sha(run/'repeat/schema.json'))
        pub=(P/'a_save_repeat_publish_test.py').read_text(encoding='utf-8')
        pub=replace(pub,'P=Path(__file__).resolve().parent','P=Path('+repr(str(overlay))+')')
        pub=replace(pub,"run=P.parents[2]/'mod_research'/'a_save_repeat_publish_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')",'run=Path('+repr(str(run/'publisher'))+')')
        pub=replace(pub,"            publish('inspect','REJECTED_PREFLIGHT',True)",'''            plan=(folder/'plans.bin').read_bytes();snap=(folder/'snapshot.bin').read_bytes()
            (folder/'plans.bin').write_bytes((0x31585241).to_bytes(4,'little')+plan[4:])
            publish('inspect','REJECTED_PREFLIGHT');(folder/'plans.bin').write_bytes(plan)
            (folder/'snapshot.bin').write_bytes((0x31585241).to_bytes(4,'little')+snap[4:])
            publish('inspect','REJECTED_PREFLIGHT');(folder/'snapshot.bin').write_bytes(snap[:-4])
            publish('inspect','REJECTED_PREFLIGHT');(folder/'snapshot.bin').write_bytes(snap)
            publish('inspect','REJECTED_PREFLIGHT',True)''')
        check=run/'publisher_check.py';check.write_text(pub,encoding='utf-8')
        proc=subprocess.run([sys.executable,'-B','-X','utf8',str(check)],env=env,capture_output=True,text=True,errors='replace',timeout=180)
        (run/'publisher-driver.log').write_text(proc.stdout+proc.stderr,encoding='utf-8')
        pub_path=run/'publisher/result.json';pub=json.loads(pub_path.read_text())
        assert proc.returncode==0 and pub['result']=='PASS' and len(pub['cases'])==8 and not pub['surviving_owned_pids'],'strict publisher checks failed'
        publisher=run/'publisher/publisher.exe';result['publisher']=dict(path=str(publisher),sha256=sha(publisher))
        result['publisher_checks']=dict(path=str(pub_path),sha256=sha(pub_path))
        proc=subprocess.run([sys.executable,'-B','-X','utf8',str(P/'a_save_three_exports_test.py')],capture_output=True,text=True,errors='replace',timeout=300)
        (run/'native-three-driver.log').write_text(proc.stdout+proc.stderr,encoding='utf-8')
        tail=json.loads(proc.stdout.strip().splitlines()[-1]);native_path=Path(tail['path']);native=json.loads(native_path.read_text())
        assert proc.returncode==0 and native['result']=='PASS','three-save native exports test failed'
        by_name={Path(n).name:h for n,h in native['generated_sources'].items()}
        assert by_name=={n:sha(overlay/n) for n in generated},'native three fixture and DLL generated code differ'
        # Preserve the original evidence bytes and provenance, while packaging
        # its entire artifact tree in the approved bundle (no external component).
        for name,h in native['artifacts'].items():
            evidence=(native_path.parent/name).resolve(strict=True)
            assert evidence.is_relative_to(native_path.parent) and sha(evidence)==h,'native evidence artifact drift'
        packaged=run/'native-three-evidence'
        shutil.copytree(native_path.parent,packaged)
        assert sha(packaged/'result.json')==sha(native_path),'native evidence copy drift'
        result['native_three_origin']=dict(path=str(native_path),sha256=sha(native_path))
        result['native_three_checks']=dict(path=str(packaged/'result.json'),sha256=sha(packaged/'result.json'))
        used=set(abi['production']['sources'])|set(report['sources'])|set(rep['sources'])|set(pub['sources'])|{'a_save_three_exports_sources.py','a_save_three_exports_build.py','a_save_three_exports_test.py','a_save_three_exports_fixture.py','a_save_three_cycle_sources.py','a_save_three_runtime_contract.py','a_save_three_repeat_contract.py'}
        result['sources']={str(P/n):original[n] for n in sorted(used)}
        assert all(sha(Path(n))==h for n,h in result['sources'].items()),'used predecessor source changed'
        result.update(result='PASS',schema_fields_verified=True,production_abi_executed=True)
    except Exception as e:result['error']=repr(e)
    result['generated_sources']={str(overlay/n):sha(overlay/n) for n in generated}
    result['artifacts']={str(p.relative_to(run)):sha(p) for p in run.rglob('*') if p.is_file() and p!=run/'result.json'}
    (run/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(result=result['result'],path=str(run/'result.json'))));return result['result']!='PASS'
if __name__=='__main__':raise SystemExit(main())
