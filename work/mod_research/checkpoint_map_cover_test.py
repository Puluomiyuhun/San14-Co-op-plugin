"""Run only the named own-process window fixture; no external capture target."""
from pathlib import Path
from datetime import datetime
import hashlib,json,subprocess,time
ROOT=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    run=ROOT/'checkpoint_map_cover_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
    unchanged=[ROOT/'transition_visual_win32_fixture.cpp',ROOT/'transition_visual_win32_results.json',ROOT.parent.parent/'outputs/san14-link/checkpoint_presentation.py',ROOT.parent.parent/'outputs/san14-link/transition_visual_surface.py']
    frozen={str(p):sha(p) for p in unchanged}
    start=time.monotonic()
    try:
        result=subprocess.run([str(ROOT/'checkpoint_map_cover_fixture.exe'),str(run)],capture_output=True,text=True,timeout=40)
        (run/'stdout.txt').write_text(result.stdout);(run/'stderr.txt').write_text(result.stderr);exit_code=result.returncode
    except subprocess.TimeoutExpired as error:
        (run/'stderr.txt').write_text('Own fixture timed out and subprocess was terminated; no game process was selected.');exit_code=-1
    elapsed=time.monotonic()-start
    native_path=run/'native-result.json';native=json.loads(native_path.read_text()) if native_path.exists() else {'result':'INCOMPLETE'}
    assert frozen=={str(p):sha(p) for p in unchanged}
    if native['result']=='PASS':
        assert all(native['capture_times'][name]>cut for name,cut in native['minimum_frame_times'].items())
        assert native['capture_times']['unchanged']>native['capture_times']['background']
        assert native['capture_times']['revealed']>native['capture_times']['failure']
    files=['checkpoint_map_cover_capture.h','checkpoint_map_cover_capture.cpp','checkpoint_map_cover_fixture.cpp','checkpoint_map_cover_probe.cpp','checkpoint_map_cover_build.cmd','checkpoint_map_cover_test.py']
    report={'schema':'san14.checkpoint-map-cover-own-visible-window.v1','result':'PASS' if exit_code==0 and native['result']=='PASS' else 'FAIL','native_result':native,'exit_code':exit_code,'elapsed_seconds':elapsed,'source_sha256':{name:sha(ROOT/name) for name in files},'fixture_binary_sha256':sha(ROOT/'checkpoint_map_cover_fixture.exe'),'readonly_probe_binary_sha256':sha(ROOT/'checkpoint_map_cover_probe.exe'),'readonly_probe_executed':False,'capture_object_sha256':sha(ROOT/'checkpoint_map_cover_capture.obj'),'artifacts':{p.name:sha(p) for p in run.glob('*.bmp')},'existing_files_unchanged':frozen,'game_access':False,'external_window_selected':False,'gameplay_enabled':False}
    (run/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'result':report['result'],'report':str(run/'result.json'),'exit_code':exit_code,'elapsed_seconds':elapsed}));return report['result']!='PASS'
if __name__=='__main__':raise SystemExit(main())
