import json
from pathlib import Path
import subprocess
import tempfile
import time

ROOT=Path(__file__).resolve().parent
FLAGS=subprocess.CREATE_NO_WINDOW

def wait_json(path, wanted=None, deadline=10):
    end=time.monotonic()+deadline
    while time.monotonic()<end:
        try:
            text=path.read_text(encoding='utf-8')
            if wanted is None:
                return json.loads(text)
            rows=[json.loads(line) for line in text.splitlines() if line]
            if any(row.get('event')==wanted for row in rows):return rows
            if any(row.get('event')=='error' for row in rows):raise RuntimeError(rows)
        except (FileNotFoundError,json.JSONDecodeError):pass
        time.sleep(.05)
    raise RuntimeError(f'Timeout waiting for {path.name}: {wanted}')

def run_case(should_hit):
    with tempfile.TemporaryDirectory(dir=ROOT,prefix='probe-test-') as directory:
        root=Path(directory);ready=root/'ready.json';go=root/'go';log=root/'trace.jsonl'
        fixture=subprocess.Popen([str(ROOT/'submit_probe_fixture.exe'),str(ready),str(go)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=FLAGS)
        tracer=None
        try:
            info=wait_json(ready)
            tracer=subprocess.Popen([str(ROOT/'observe_submit.exe'),str(info['pid']),hex(info['base']),hex(info['rva']),'10' if should_hit else '2',str(log)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=FLAGS)
            wait_json(log,'armed')
            if should_hit:go.write_text('go')
            _,err=tracer.communicate(timeout=15)
            expected=0 if should_hit else 4
            if tracer.returncode!=expected:raise RuntimeError(f'tracer exit {tracer.returncode}: {err!r}; {log.read_text()}')
            rows=[json.loads(line) for line in log.read_text().splitlines()]
            assert rows[-1]=={'event':'detached','captured':should_hit,'registers_restored':True}
            if should_hit:
                entry=next(row for row in rows if row['event']=='submit_entry')
                assert entry['words'][0]==666 and entry['words'][2]==1300 and entry['flags']==1
            else:go.write_text('go')
            out,err=fixture.communicate(timeout=5)
            assert fixture.returncode==0,(out,err)
            original=json.loads(out)
            assert original=={'calls':1,'original_function_returned':True}
            return {'case':'capture' if should_hit else 'timeout-cleanup','result':'PASS','trace':rows,'fixture':original}
        finally:
            if tracer and tracer.poll() is None:
                # Normal bounded timeout cleans up; avoid terminating a live debugger.
                tracer.wait(timeout=20)
            if fixture.poll() is None:fixture.terminate();fixture.wait(timeout=5)

if __name__=='__main__':
    report=[run_case(True),run_case(False)]
    (ROOT/'probe-self-test.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))
