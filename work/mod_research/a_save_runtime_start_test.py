"""Native offsetof compatibility and captured-config encoding, no game access."""
import argparse
import copy
import ctypes as C
from datetime import datetime
import json
from pathlib import Path
import tempfile
import a_save_runtime_contract as wire
from a_save_runtime_control import sha,save_new
from a_save_runtime_start import validate_schema,verify_sources

P=Path(__file__).resolve().parent;PRIVATE=P.parents[2]/'mod_research'


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--exports-build',type=Path,required=True);parser.add_argument('--capture-record',type=Path,required=True)
    args=parser.parse_args();run=PRIVATE/'a_save_runtime_start_test_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
    pins={n:sha(P/n) for n in ('a_save_runtime_contract.py','a_save_runtime_control.py','a_save_runtime_start.py','a_save_runtime_start_test.py')}
    result=dict(result='FAIL',game_access=False,native_requests=0,sources=pins,cases=[])
    try:
        build=json.loads((args.exports_build/'result.json').read_text(encoding='utf-8'))
        assert build['result']=='PASS' and build['abi_executed'];verify_sources(build['production'])
        for n,h in build['own_sources'].items():assert sha(P/n)==h,n
        schema_path=args.exports_build/'schema.json';assert sha(schema_path)==build['generated']['schema.json']
        schema=json.loads(schema_path.read_text(encoding='utf-8'));validate_schema(schema)
        result['cases'].append('all_native_sizes_and_field_offsets_match')
        bad=copy.deepcopy(schema);bad['structures']['Prepare']['fields']['storage']['offset']+=1
        try:validate_schema(bad)
        except RuntimeError:pass
        else:raise AssertionError('bad offset accepted')
        result['cases'].append('abi_mismatch_rejected')
        capture=json.loads(args.capture_record.read_text(encoding='utf-8'))
        with tempfile.TemporaryDirectory(dir=PRIVATE) as temp:
            q=wire.prepare_from_capture(capture,temp,temp)
            d=wire.decode(wire.Prepare,'Prepare',bytes(q.nonce),bytes(q))
            assert (d.pid,d.birth,d.base)==tuple(capture['planning'][n] for n in ('pid','birth','base'))
            assert list(d.states)==capture['planning']['states'] and d.storage.moduleCount==len(capture['storage']['storageModules'])
            assert bytes(d.storage.contextCode).hex()==capture['storage']['contextCode']
            for i,m in enumerate(capture['storage']['storageModules']):
                assert bytes(d.storage.modules[i].path).decode('utf-16le').rstrip('\0')==m['path']
                assert bytes(d.storage.modules[i].fileSha256).hex()==m['fileSha256']
            assert d.period==d.native.ownerGeneration==1 and (d.year,d.month,d.day,d.force,d.ruler)==(203,8,11,12,666)
            for dst,src in (('contextInit','contextInit'),('exists','exists'),('size','fileSize'),('read','read')):
                assert getattr(d.storage,dst).address==capture['storage'][src]['address']
            result['cases'].append('captured_identity_storage_and_utf16_paths_encoded')
            try:wire.decode(wire.Prepare,'Prepare',bytes(32),bytes(q))
            except ValueError:pass
            else:raise AssertionError('foreign nonce accepted')
            result['cases'].append('foreign_response_rejected')
            bad=copy.deepcopy(capture);bad['planning']['context']['snapshot']['date']['day']=21
            try:wire.prepare_from_capture(bad,temp,temp)
            except ValueError:pass
            else:raise AssertionError('foreign scenario accepted')
            result['cases'].append('wrong_fixed_scenario_rejected')
        assert all(sha(P/n)==h for n,h in pins.items())
        result.update(result='PASS',sources_unchanged=True,native_schema_sha256=sha(schema_path),export_build_sha256=sha(args.exports_build/'result.json'),private_capture_sha256=sha(args.capture_record))
    except Exception as exc:result['error']=repr(exc)
    save_new(run/'result.json',result);print(json.dumps(dict(result=result['result'],path=str(run/'result.json'))))
    return 0 if result['result']=='PASS' else 1


if __name__=='__main__':raise SystemExit(main())
