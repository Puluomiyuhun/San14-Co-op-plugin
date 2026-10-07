"""Stage ONE identical A export in a verified empty native CC slot. No load.

The new file is an internal experimental checkpoint, not a user-selected save.
No existing target may be replaced. An uncertain attempt is never retried.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,ctypes as C,json,os,time
from ctypes import wintypes as W
import checkpoint_cc_file_start as probe
from checkpoint_cc_file_fixture_gate import validate_fixture
from checkpoint_push_contract import compare_known_coverage
from checkpoint_live_capture import sample as capture_known
P=Path(__file__).resolve().parent
TARGET=probe.TARGET
INTENT=P/'checkpoint_cc_stage_once.intent'
RESULT=P/'checkpoint_cc_stage_result.json'

def move_new(source,target):
    """Atomic same-volume publish. Intentionally omits REPLACE_EXISTING."""
    k=C.WinDLL('kernel32',use_last_error=True)
    k.MoveFileExW.argtypes=[W.LPCWSTR,W.LPCWSTR,W.DWORD];k.MoveFileExW.restype=W.BOOL
    if not k.MoveFileExW(str(source),str(target),8):
        raise C.WinError(C.get_last_error())

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--absence-evidence',type=Path,required=True)
    args=parser.parse_args()
    a=probe.load(args.absence_evidence)
    assert a['schema']=='san14.checkpoint-cc-file-live.v1' and a['result']=='PASS' and a['mode']=='absent'
    assert a['native_absence_observed_twice'] and not a['load_requested']
    assert a['target']==str(TARGET) and a['dll_sha256']==probe.sha(probe.DLL)
    assert probe.report_ok(a['adapter'],2,a['before']) and a['existing_files_unchanged'] and a['actual_hook_slots_restored']
    validate_fixture(a['fixture']['fixture_path'],probe.DLL)
    assert 0<=time.time()-args.absence_evidence.stat().st_mtime<600,'Absence evidence expired'
    assert not os.path.lexists(TARGET) and not os.path.lexists(INTENT) and not os.path.lexists(RESULT)
    assert TARGET.parent.resolve()==Path(r'C:\Program Files (x86)\Steam\userdata\391007908\872410\remote')
    archive=probe.load(probe.ARCHIVE_RESULT);source=Path(archive['archive'])
    data=source.read_bytes()
    assert len(data)==274880 and probe.hashlib.sha256(data).hexdigest()==probe.SHA
    reader=probe.BattleObserver() if hasattr(probe,'BattleObserver') else None
    if reader is None:
        from battle_observer import BattleObserver
        reader=BattleObserver()
    run=P/'checkpoint_cc_stage_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    run.mkdir(parents=True,exist_ok=False)
    published=False
    try:
        before=probe.precheck(reader)
        assert before==a['after'] and before['result']=='PASS'
        known_before=capture_known();probe.save(run/'known-before.json',known_before)
        assert known_before['save_files']==probe.load(args.absence_evidence.parent/'known-after.json')['save_files']
        assert compare_known_coverage(probe.load(args.absence_evidence.parent/'known-after.json'),known_before)['matched']
        temporary=run/'checkpoint.cc.staging'
        with temporary.open('xb') as stream:
            assert stream.write(data)==len(data)
            stream.flush();os.fsync(stream.fileno())
        assert probe.sha(temporary)==probe.SHA
        probe.save(INTENT,{'schema':'san14.cc-stage-once.v1','created':datetime.now(timezone.utc).isoformat(),'target':str(TARGET),
            'source':str(source),'sha256':probe.SHA,'absence_result':str(args.absence_evidence.resolve()),'absence_sha256':probe.sha(args.absence_evidence),
            'attachment':before,'run':str(run),'overwrite_allowed':False,'load_requested':False})
        assert probe.precheck(reader)==before and not os.path.lexists(TARGET)
        move_new(temporary,TARGET);published=True
        assert probe.sha(TARGET)==probe.SHA
        after=probe.precheck(reader);known_after=capture_known();probe.save(run/'known-after.json',known_after)
        files_before=known_before['save_files'];files_after=known_after['save_files']
        assert set(files_after)-set(files_before)=={TARGET.name}
        assert all(files_after[k]==v for k,v in files_before.items())
        assert files_after[TARGET.name]=={'size':len(data),'sha256':probe.SHA}
        coverage=compare_known_coverage(known_before,known_after)
        assert coverage['matched'] and after==before
        result={'schema':'san14.checkpoint-cc-stage.v1','result':'PASS','run':str(run),'target':str(TARGET),'target_sha256':probe.SHA,
            'native_slot':63,'source_archive':str(source),'bytes':len(data),'original_files':len(files_before),'existing_files_unchanged':True,
            'added_files':[TARGET.name],'game_memory_writes':0,'known_coverage':coverage,'load_requested':False,
            'native_visibility_after_copy_proven':False,'before':before,'after':after,'absence_result_sha256':probe.sha(args.absence_evidence)}
        probe.save(RESULT,result);probe.save(run/'result.json',result)
        print(json.dumps({k:result[k] for k in ('result','target','bytes','original_files','existing_files_unchanged','load_requested')}))
    except BaseException as error:
        failed={'result':'UNCERTAIN_NO_AUTO_RETRY','error':repr(error),'published':published,'target':str(TARGET),'load_requested':False}
        if not RESULT.exists():probe.save(RESULT,failed)
        if not (run/'result.json').exists():probe.save(run/'result.json',failed)
        raise
    finally:reader.close()

if __name__=='__main__':main()
