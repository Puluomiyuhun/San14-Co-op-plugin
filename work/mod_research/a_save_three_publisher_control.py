"""Strict publisher call wrapper: unresolved ownership survives logging faults."""
import json,subprocess
from a_save_runtime_control import require,sha,save_new,RemoteCallUnknown

def publish(exe,operation,prep,module,dll,plans_file,snapshot_file,run,label):
    command=[str(exe),operation,str(prep.pid),str(prep.birth),str(prep.base),str(module),
             str(dll),sha(dll),str(plans_file),str(snapshot_file)]
    save_new(run/(label+'-intent.json'),dict(command=command,publisher_sha256=sha(exe),automatic_retry=False))
    child=None;completed=False;detached_known=False;code=None;result=None
    try:
        with (run/(label+'-stdout.log')).open('xb') as out,(run/(label+'-stderr.log')).open('xb') as err:
            child=subprocess.Popen(command,stdout=out,stderr=err,creationflags=subprocess.CREATE_NO_WINDOW)
            save_new(run/(label+'-process.json'),dict(pid=child.pid))
            code=child.wait(timeout=20);completed=True
        rows=[json.loads(s) for s in (run/(label+'-stdout.log')).read_text(encoding='utf-8').splitlines() if s.startswith('{')]
        require(len(rows)==1 and type(rows[0]) is dict,'Publisher result is missing or ambiguous')
        result=rows[0]
        require(all(type(result.get(k)) is bool for k in ('attached','detached','uncertain')),
                'Publisher ownership flags are malformed')
        detached_known=not result['uncertain'] and (not result['attached'] or result['detached'])
        require(detached_known,'Publisher has not proved clean detach')
        save_new(run/(label+'-result.json'),dict(exit=code,report=result))
        expected='INSTALLED' if operation=='install' else 'RESTORED' if operation=='restore' else 'PASS_READ_ONLY'
        if code==3 and result.get('status')=='REJECTED_HELD_NO_WRITES' and result.get('written_mask')==0:
            return result
        require(code==0 and result.get('status')==expected,'Publication did not complete: '+str(result.get('status')))
        return result
    except BaseException as exc:
        # Exit alone is insufficient: a process that touched the debug event
        # must also report a known detach before native cleanup may continue.
        if child is not None and not(completed and detached_known):
            record=dict(controller_pid=child.pid,process_exit_observed=completed,exit=code,
                detach_proven=False,may_own_debug_event=True,must_not_terminate=True,
                automatic_retry=False,error_type=type(exc).__name__)
            try:save_new(run/(label+'-pending.json'),record)
            except BaseException as log_error:record['pending_log_error']=type(log_error).__name__
            raise RemoteCallUnknown('Publisher ownership unresolved; preserve controller and target state',record) from exc
        raise
