"""Read-only 16-frame CApp observer. Default help only; explicit PID required."""
import argparse,json,secrets,subprocess,time
from pathlib import Path
from datetime import datetime
import a_save_observation_status as old
P=Path(__file__).resolve().parent
PRIVATE=P.parents[2]/'mod_research'
SOURCES=tuple(dict.fromkeys(old.SOURCES+('a_save_parent_live.py','a_save_parent_live_test.py','a_save_parent_live_payload.inc','a_save_parent_live_semantic.cpp')))
def tested_build(folder):
    folder=Path(folder).resolve();r=json.loads((folder/'result.json').read_text())
    if r.get('schema')!='san14.a-save-parent-live.tests.v1' or r.get('result')!='PASS' or set(r['sources'])!=set(SOURCES):raise RuntimeError('Missing passing exact build')
    for n,h in r['sources'].items():
        if old.sha(P/n)!=h:raise RuntimeError('Changed source '+n)
    for n,h in r['generated'].items():
        if old.sha(folder/n)!=h:raise RuntimeError('Changed generated source '+n)
    if old.sha(folder/'observer.exe')!=r['production_sha256']:raise RuntimeError('Changed observer binary')
    return folder,r
def preflight(pid,folder):
    f,r=tested_build(folder);before=old.preflight(pid)
    if before['result']!='PASS_READ_ONLY':return before
    from game_reader import GameReader
    reader=GameReader(pid)
    try:
        if old.birth(reader.memory.handle)!=before['birth'] or reader.memory.base!=before['base']:raise RuntimeError('Process changed between preflights')
        for a,h in r['anchors'].items():
            raw=bytes.fromhex(h)
            if reader.memory.read(before['base']+int(a),len(raw))!=raw:raise RuntimeError('Changed parent source '+a)
    finally:reader.close()
    return before
def record(folder,pid,seconds):
    folder,tests=tested_build(folder);before=preflight(pid,folder)
    run=PRIVATE/'a_save_parent_live_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
    old.write(run/'before.json',before)
    if before['result']!='PASS_READ_ONLY':print(json.dumps(before));return 2
    trace=run/'trace.jsonl';nonce=secrets.token_hex(16);ready=False;error=None
    old.write(run/'intent.json',dict(tested_build=str(folder),production_sha256=tests['production_sha256'],sources=tests['sources'],run_id=nonce,game_data_writes=0,native_requests=0))
    with (run/'stdout.log').open('xb') as out,(run/'stderr.log').open('xb') as err:
        proc=subprocess.Popen([str(folder/'observer.exe'),str(pid),hex(before['base']),'0x13dc09',str(seconds),str(trace),str(before['birth']),str(before['user']),str(before['stack']),nonce],stdout=out,stderr=err,creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            end=time.monotonic()+seconds+25
            while proc.poll() is None and time.monotonic()<end:
                ready=ready or any(x.get('event')=='armed' for x in old.records(trace));time.sleep(.05)
            if proc.poll() is None:raise RuntimeError('Deadline; requesting clean stop')
        except BaseException as exc:error=repr(exc)
        finally:
            if proc.poll() is None:
                Path(str(trace)+'.stop').write_text('stop')
                try:proc.wait(timeout=20)
                except subprocess.TimeoutExpired:error='Cleanup pending; do not terminate observer'
    rows=old.records(trace);ready=ready or any(x.get('event')=='armed' for x in rows)
    lifecycle,clean=old.capture_status(rows,ready,proc.poll())
    complete=bool(lifecycle['capture_complete'] and any(x.get('event')=='summary' and x.get('chain_complete') for x in rows))
    old.write(run/'result.json',dict(result='CAPTURED' if complete else 'INCOMPLETE',lifecycle=lifecycle,cleanup_verified=clean,cleanup_pending=proc.poll() is None,error=error,observer_exit=proc.poll(),all_workers_complete_proved=False,all_writers_excluded=False,production_permit=False))
    print(json.dumps(dict(result='CAPTURED' if complete else 'INCOMPLETE',run=str(run),cleanup_pending=proc.poll() is None)));return 0 if complete else 1
def main():
    p=argparse.ArgumentParser(description=__doc__);a=p.add_mutually_exclusive_group();a.add_argument('--preflight',action='store_true');a.add_argument('--record',action='store_true');p.add_argument('--pid',type=int);p.add_argument('--tested-build',type=Path);p.add_argument('--seconds',type=int,default=20);v=p.parse_args()
    if not(v.preflight or v.record):p.print_help();return 0
    if not v.pid or v.pid<0 or not v.tested_build:p.error('explicit --pid and --tested-build required')
    if not 1<=v.seconds<=60:p.error('seconds must be 1..60')
    if v.preflight:r=preflight(v.pid,v.tested_build);print(json.dumps(r,ensure_ascii=False,indent=2));return 0 if r['result']=='PASS_READ_ONLY' else 2
    return record(v.tested_build,v.pid,v.seconds)
if __name__=='__main__':raise SystemExit(main())
