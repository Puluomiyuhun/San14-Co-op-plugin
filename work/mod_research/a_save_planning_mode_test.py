"""Strict observed A planning mode zero, real Controller/Save regression.

Owned processes only. Frozen inputs remain unchanged; native world/business
fixture data now use the archived real baseline cache mode zero.
"""
from pathlib import Path
from datetime import datetime
import hashlib,json,subprocess,sys,difflib,os
from a_save_initialize_trace_generate import once
P=Path(__file__).resolve().parent;PRIVATE=P.parents[2]/'mod_research'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def input_source():
    old=(P/'a_save_scoped_input.cpp').read_text()
    return '// Explicit observed planning-mode-zero successor; all other checks are unchanged.\n'+once(old,'if(Read<std::uint32_t>(c.load_cache,8)!=1){r.decision=Decision::StateTransition;return r;}','if(Read<std::uint32_t>(c.load_cache,8)!=0){r.decision=Decision::StateTransition;return r;}')
def main():
    run=PRIVATE/'a_save_planning_mode_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
    names=('a_save_planning_mode_test.py','a_save_planning_mode_input.cpp','a_save_initialize_trace_test.py','a_save_scoped_input.cpp')
    pins={n:sha(P/n)for n in names};result=dict(result='FAIL',game_access=False,sources=pins)
    try:
        assert (P/'a_save_planning_mode_input.cpp').read_text()==input_source()
        old=(P/'a_save_initialize_trace_test.py').read_text()
        s=once(old,'P=Path(__file__).resolve().parent;PRIVATE=P.parents[2]/\'mod_research\'','P=Path('+repr(str(P))+');PRIVATE=P.parents[2]/\'mod_research\'')
        s=once(s,'from a_save_initialize_trace_generate import instrument,once','sys.path.insert(0,'+repr(str(P))+')\nfrom a_save_initialize_trace_generate import instrument,once')
        s=once(s,"run=PRIVATE/'a_save_initialize_trace_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)",'run=Path('+repr(str(run/'candidate'))+');run.mkdir(parents=True)')
        s=once(s,"        assert all(sha(P/n)==h for n,h in sources.items())",'        sources.update('+repr(pins)+')\n        assert all(sha(P/n)==h for n,h in sources.items())')
        s=once(s,"            # Compile trace once", "            cmd=cmd.replace('a_save_scoped_input.cpp','a_save_planning_mode_input.cpp')\n            # Compile trace once")
        hook='''                fixture=once(fixture,'cfg.room_epoch=7;', 'put<unsigned>(b+0x290000+8,0);cfg.room_epoch=7;')
                fixture=once(fixture,'if(!RewardData::sample(p,u,actor,out))return false;', 'if(!RewardData::sample(p,u,actor,out))return false;if(traceFault&&traceCase==L"mode1")put<unsigned>(b+0x290000+8,1);if(traceFault&&traceCase==L"mode2")put<unsigned>(b+0x290000+8,2);if(traceFault&&traceCase==L"transition")put<unsigned>(user+0x660,1);')
                fixture=once(fixture,'const LONG expected=traceCase==L"sample"?42:traceCase==L"identity"?43:traceCase==L"bind"?45:traceCase==L"inspect"?46:17;', 'const LONG expected=46;')
                fixture=once(fixture,'need(a.InspectCurrent(c.binding).error==checkpoint_native_input_pending::Error::Pointer,why);', 'const auto inspected=a.InspectCurrent(c.binding);need(inspected.error==checkpoint_native_input_pending::Error::Pointer||(ASaveInitializeFirstFailure.stage==46&&get<unsigned>(user+0x660)==1&&inspected.error==checkpoint_native_input_pending::Error::None&&inspected.decision==checkpoint_native_input_pending::Decision::StateTransition),why);')
                fixture=once(fixture,'need(traceSamples==(traceCase==L"slot"?0u:1u),', 'need(r.input.error==0&&r.input.decision==unsigned(checkpoint_native_input_pending::Decision::StateTransition)&&r.input.stackCount==5&&r.input.queueCount==0&&r.input.userPhase==2,"real transition refusal and original fields");need(traceSamples==(traceCase==L"slot"?0u:1u),')
'''
        s=once(s,"                (folder/'scoped_fixture.cpp').write_text",hook+"                (folder/'scoped_fixture.cpp').write_text")
        s=once(s,"for case in ('normal','slot','sample','identity','bind','inspect'):","for case in ('normal','mode1','mode2','transition'):")
        script=run/'generated_test.py';script.write_text(s,encoding='utf-8')
        (run/'generator.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),s.splitlines(True))),encoding='utf-8')
        env=os.environ.copy();env['PYTHONUTF8']='1'
        p=subprocess.run([sys.executable,str(script)],env=env,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=240)
        (run/'driver.log').write_text(p.stdout+p.stderr,encoding='utf-8')
        child=json.loads((run/'candidate/result.json').read_text());result['execution']=child
        assert p.returncode==0 and child['result']=='PASS'
        assert all(sha(P/n)==h for n,h in pins.items())
        result.update(result='PASS',compatible_build_run=child['compatible_build_run'],production_dll=child['production_dll'])
    except Exception as e:result['error']=repr(e)
    result['inputs_unchanged']=all(sha(P/n)==h for n,h in pins.items())
    result['generated']={str(p.relative_to(run)):sha(p)for p in run.iterdir()if p.is_file()}
    out=run/'result.json';out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(result=result['result'],path=str(out))));return 0 if result['result']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
