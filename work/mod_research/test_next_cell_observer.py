"""Real mixed hardware breakpoint tests in an isolated child process."""
import hashlib,json,subprocess,tempfile
from pathlib import Path
from test_submit_probe import wait_json
ROOT=Path(__file__).resolve().parent
results=[]
for mode in ('writes-and-markers','timeout','cancel'):
    with tempfile.TemporaryDirectory(dir=ROOT/'lockstep-fixture') as directory:
        folder=Path(directory);ready=folder/'ready.json';go=folder/'go';log=folder/'trace.jsonl'
        fixture=subprocess.Popen([str(ROOT/'next_cell_fixture.exe'),str(ready),str(go)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
        observer=None
        try:
            info=wait_json(ready)
            observer=subprocess.Popen([str(ROOT/'observe_next_cell.exe'),str(info['pid']),hex(info['base']),hex(info['watch']),
                *[hex(x) for x in info['rvas']], '2' if mode=='timeout' else '15',str(log)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
            wait_json(log,'armed')
            if mode=='writes-and-markers':go.write_text('go')
            if mode=='cancel':Path(str(log)+'.stop').write_text('stop')
            out,err=observer.communicate(timeout=20)
            rows=[json.loads(s) for s in log.read_text().splitlines()]
            captured=mode=='writes-and-markers'
            assert observer.returncode==(0 if captured else 4),(err,rows)
            assert rows[-1]=={'event':'detached','captured':captured,'registers_restored':True}
            writes=[r for r in rows if r['event']=='next_cell_write']
            transitions=[(r['previous_observed'],r['observed_after']) for r in writes]
            assert transitions==([(7,11),(11,11),(11,267),(267,33),(33,66)] if captured else []),transitions
            if captured:
                assert len({r['thread'] for r in writes})==2
                assert [r['event'] for r in rows if 'seq' in r]==['next_cell_write']*4+['worker_enter','next_cell_write','worker_return','movement_consume']
                assert writes[-1]['next_cell']==66
            else:go.write_text('go')
            out,err=fixture.communicate(timeout=5)
            assert fixture.returncode==0,(out,err)
            final=json.loads(out)
            assert final=={'initial':7,'value':77,'left':44,'right':55,'entries':1,'returns':1,'consumes':1}
            results.append({'case':mode,'result':'PASS','transitions':transitions,'fixture_result':final})
        finally:
            if observer and observer.poll() is None:
                Path(str(log)+'.stop').write_text('stop');observer.wait(timeout=20)
            if fixture.poll() is None:go.write_text('go');fixture.wait(timeout=5)
report={'result':'PASS','observer_sha256':hashlib.sha256((ROOT/'observe_next_cell.exe').read_bytes()).hexdigest(),
    'scope':'Actual 2-byte hardware watch, same-value, byte and overlapping wider stores, adjacent/read exclusion, new thread coverage, 3 execute markers, timeout/cancel restoration. Not game semantics.',
    'cases':results}
(ROOT/'next-cell-fixtures.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
