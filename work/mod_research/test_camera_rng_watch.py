"""Actual hardware watch tests in an isolated process, including a new thread."""
import json
from pathlib import Path
import subprocess
import tempfile
from test_submit_probe import wait_json
ROOT=Path(__file__).resolve().parent
FLAGS=subprocess.CREATE_NO_WINDOW
results=[]
for mode in ('writes-and-markers','timeout','cancel'):
    with tempfile.TemporaryDirectory(dir=ROOT/'lockstep-fixture') as directory:
        folder=Path(directory);ready=folder/'ready.json';go=folder/'go';log=folder/'trace.jsonl'
        fixture=subprocess.Popen([str(ROOT/'pending_watch_fixture.exe'),str(ready),str(go)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=FLAGS)
        observer=None
        try:
            info=wait_json(ready)
            observer=subprocess.Popen([str(ROOT/'observe_camera_rng_watch.exe'),str(info['pid']),hex(info['base']),hex(info['rvas'][0]),
                '2' if mode=='timeout' else '15',str(log)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=FLAGS)
            wait_json(log,'armed')
            if mode=='writes-and-markers':go.write_text('go')
            if mode=='cancel':Path(str(log)+'.stop').write_text('stop')
            out,err=observer.communicate(timeout=20)
            rows=[json.loads(x) for x in log.read_text().splitlines()]
            captured=mode=='writes-and-markers'
            assert observer.returncode==(0 if captured else 4),(err,rows)
            assert rows[-1]=={'event':'detached','captured':captured,'registers_restored':True},rows
            writes=[r for r in rows if r['event']=='fixture_write']
            actual=[(r['previous_observed'],r['observed_after']) for r in writes]
            expected=[(7,11),(11,11),(11,0x100000b),(0x100000b,0x2000b),(0x2000b,33),(33,66),(66,77)] if captured else []
            assert actual==expected,actual
            if captured:
                assert len({r['thread'] for r in writes})==2
            else:go.write_text('go')
            out,err=fixture.communicate(timeout=5)
            assert fixture.returncode==0,(out,err)
            result=json.loads(out)
            assert result=={'initial_read':16,'value':77,'effect':55,'adjacent':44,'marker':1,'gate':1}
            results.append({'case':mode,'result':'PASS','writes':actual,'fixture':result,'trace':rows})
        finally:
            if observer and observer.poll() is None:
                Path(str(log)+'.stop').write_text('stop');observer.wait(timeout=20)
            if fixture.poll() is None:go.write_text('go');fixture.wait(timeout=5)
(ROOT/'camera-rng-watch-fixtures.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
print(json.dumps([{'case':r['case'],'result':r['result'],'write_events':len(r['writes'])} for r in results]))
