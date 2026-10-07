"""Exercise real hardware entry/return pairing before permitting game attachment."""
import collections,hashlib,json,subprocess,tempfile,time
from pathlib import Path
from test_submit_probe import wait_json
ROOT=Path(__file__).resolve().parent
FLAGS=subprocess.CREATE_NO_WINDOW
def wait_file(path,seconds=15):
    until=time.monotonic()+seconds
    while not path.exists():
        assert time.monotonic()<until,f'timed out: {path}'
        time.sleep(.02)
reports=[]
for mode in ('capture','timeout','cancel'):
    with tempfile.TemporaryDirectory(dir=ROOT/'lockstep-fixture',prefix='rng-pair-') as directory:
        folder=Path(directory);ready=folder/'ready.json';go=folder/'go';done=folder/'done';release=folder/'release';log=folder/'trace.jsonl'
        fixture=subprocess.Popen([str(ROOT/'rng_pair_target_fixture.exe'),str(ready),str(go),str(done),str(release)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=FLAGS)
        observer=None
        try:
            info=wait_json(ready)
            observer=subprocess.Popen([str(ROOT/'observe_rng_pairs.exe'),str(info['pid']),hex(info['base']),hex(info['range_address']),hex(info['percentage_address']),hex(info['rng_address']),
                '2' if mode=='timeout' else '20',str(log)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=FLAGS)
            wait_json(log,'armed')
            if mode=='capture':go.write_text('go');wait_file(done);Path(str(log)+'.stop').write_text('stop')
            elif mode=='cancel':Path(str(log)+'.stop').write_text('stop')
            out,err=observer.communicate(timeout=25)
            rows=[json.loads(line) for line in log.read_text().splitlines()]
            assert observer.returncode==(0 if mode=='capture' else 4),(err,rows[-3:])
            end=rows[-1]
            assert end['event']=='detached' and end['registers_restored'] and end['unfinished_calls']==end['abandoned_calls']==0,end
            go.write_text('go');release.write_text('release')
            out,err=fixture.communicate(timeout=5);assert fixture.returncode==0,(out,err)
            result=json.loads(out);assert result['debugger_detached'] and len(result['rows'])==83
            entries=[r for r in rows if r['event']=='rng_entry'];returns=[r for r in rows if r['event']=='rng_return'];writes=[r for r in rows if r['event']=='rng_write']
            if mode=='capture':
                assert len(entries)==len(returns)==83 and len(writes)==81,(len(entries),len(returns),len(writes))
                pairs={r['call_id']:r for r in entries}
                for row in returns:
                    entry=pairs[row['call_id']]
                    assert row['thread']==entry['thread'] and row['entry_rsp']==entry['entry_rsp'] and row['return_rsp']==entry['entry_rsp']+8
                    assert row['caller']==entry['caller'] and row['argument']==entry['argument'] and row['kind']==entry['kind']
                actual=sorted((r['thread'],r['kind'],r['argument'],r['result']) for r in returns)
                expected=sorted((r['thread'],r['kind'],r['argument'],r['result']) for r in result['rows'])
                assert actual==expected,'recorded return registers differ from caller-observed results'
                assert len({r['thread'] for r in entries})==4
                assert len([r for r in writes if r['call_id']==0])==2
                no_draw=[r for r in entries if r['kind']=='range' and r['argument']<2]
                assert len(no_draw)==4 and not any(w['call_id'] in {r['call_id'] for r in no_draw} for w in writes)
                assert all(len(r['stack_hex'])>=128 for r in entries)
            else:assert not entries and not returns and not writes
            reports.append({'case':mode,'result':'PASS','entry_count':len(entries),'return_count':len(returns),'write_count':len(writes),
                'trace':rows,'caller_observations':result})
        finally:
            if observer and observer.poll() is None:Path(str(log)+'.stop').write_text('stop');observer.wait(timeout=25)
            if fixture.poll() is None:go.write_text('go');release.write_text('release');fixture.wait(timeout=5)
p=subprocess.run([str(ROOT/'rng_pair_payload_fixture.exe')],capture_output=True,text=True,timeout=10)
assert p.returncode==0,(p.returncode,p.stderr)
payload=[json.loads(line) for line in p.stdout.splitlines()]
assert [r['event'] for r in payload]==['rng_entry','rng_write','rng_return','unpaired_return_rejected']
assert all(r['date']==[203,8,11] and r['stage']==12 and r['camera']['level']==3 for r in payload[:3])
assert [r['rng_snapshot'] for r in payload[:3]]==[1234,5678,5678]
assert payload[0]['argument']==3 and payload[2]['result']==2 and payload[-1]['result']=='PASS'
assert len(payload[0]['stack_hex'])==len(payload[1]['stack_hex'])==4096
report={'result':'PASS','payload_fixture':payload,'observer_sha256':hashlib.sha256((ROOT/'observe_rng_pairs.exe').read_bytes()).hexdigest(),
        'fixture_sha256':hashlib.sha256((ROOT/'rng_pair_target_fixture.exe').read_bytes()).hexdigest(),'cases':reports,
        'scope':'Real hardware breakpoints on private native helper copies, all caller-observed return values checked. Four threads include two concurrent workers; timeout/cancel restore and detach checked.',
        'limits':['Entry/return RNG values are snapshots, not atomic state transitions when other threads interleave.',
                  'No game instruction replacement, DLL wrapper, or deterministic battlefield claim.',
                  'Debugger changes timing. Unmatched in-flight calls at forced stop must remain explicitly incomplete.']}
(ROOT/'rng-pair-observer-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'result':report['result'],'cases':[{k:v for k,v in r.items() if k not in ('trace','caller_observations')} for r in reports]}))
