"""Bounded three-checkpoint cleanup/file/read-only end checks; no installer."""
import ctypes as C
import re
import a_save_three_runtime_contract as wire
import a_save_three_repeat_contract as repeat
from a_save_runtime_control import require

def cleanup_gate(sample):
    """Repeat retirement is necessary, never sufficient for source restoration.

    Caller must additionally obtain native Snapshot.restoreReady == 1 and use
    the matching strict publisher. Stop may be set; unresolved transitions fail.
    """
    require(type(sample) is repeat.Snapshot,'Dedicated three-generation repeat snapshot required')
    s=repeat.decode(repeat.Snapshot,'RepeatSnapshot',bytes(sample.nonce),bytes(sample))
    require(s.header.result==0 and s.error==0,'Failed repeat state cannot authorize cleanup')
    flags=('requested','stopped','previousArtifactMatched','nativeDateMatched','bLoadedProven',
           'simulationEnabled','lease','frame','drainPending')
    require(all(getattr(s,k) in (0,1) for k in flags),'Invalid repeat flags')
    require(not any((s.bLoadedProven,s.simulationEnabled,s.lease,s.frame,s.drainPending)),
            'Repeat/Running is unresolved or claims unsupported gameplay authority')
    if s.state==0:
        require(s.activeGeneration==1 and s.retiredCount==s.retiredSerial==s.requested==s.hostThread==0 and
                not s.previousArtifactMatched and not s.nativeDateMatched and bytes(s.request)==bytes(repeat.NextData()),
                'Initial stopped state contains a successor attempt')
        return
    require(s.state==4 and s.activeGeneration in (2,3) and s.requested==0 and
            s.retiredCount==s.activeGeneration-1 and s.retiredSerial>0 and s.hostThread>0 and
            s.previousArtifactMatched==s.nativeDateMatched==1,'Successor has no complete retirement/date evidence')
    q=s.request
    require(q.previousGeneration==s.activeGeneration-1 and q.generation==s.activeGeneration and
            q.period>0 and q.epoch>0 and any(q.previousSha256) and any(q.inputDigest) and
            1<=q.year<=9999 and 1<=q.month<=12 and q.day in (1,11,21),'Retired successor request differs')

def compare_three_files(before,after,artifacts):
    require(type(before) is dict and type(after) is dict and type(artifacts) in (list,tuple),'Exact save inventories required')
    for a in artifacts:
        require(type(a) is dict and all(k in a for k in ('generation','filename','sha256','size')) and
                type(a['generation']) is int and type(a['filename']) is str and
                re.fullmatch(r'mp[0-9a-f]{8}\.s14',a['filename']) and type(a['size']) is int and a['size']>0 and
                type(a['sha256']) is str and re.fullmatch(r'[0-9a-f]{64}',a['sha256']),'Malformed native artifact identity')
    expected={a['filename']:a for a in artifacts}
    exact=len(artifacts)==len(expected)==3 and [a['generation'] for a in artifacts]==[1,2,3] and not(set(expected)&set(before))
    changed=sorted(n for n in before if n in after and before[n]!=after[n])
    missing=sorted(set(before)-set(after));added=sorted(set(after)-set(before))
    return dict(changed=changed,missing=missing,added=added,originals_unchanged=not changed and not missing,
        only_expected_new_files=exact and added==sorted(expected),
        new_hashes_match=exact and all(after.get(n,{}).get('sha256')==a['sha256'] and after.get(n,{}).get('size')==a['size'] for n,a in expected.items()),
        native_autosave_changes_are_not_silently_approved=True)

def next_date(year,month,day):
    require(all(type(v) is int for v in (year,month,day)) and 1<=year<=9999 and 1<=month<=12 and day in (1,11,21),'Planning date required')
    if day!=21:return year,month,day+10
    if month!=12:return year,month+1,1
    require(year<9999,'Date overflow');return year+1,1,1

def post_turn_check(reader,prep):
    from startup_identity_reader import capture_startup_context
    from checkpoint_push_start import process_birth
    from ctypes import wintypes as W
    require(type(prep) is wire.Prepare,'Dedicated three-slot preparation required')
    wire.decode(wire.Prepare,'Prepare',bytes(prep.nonce),bytes(prep))
    require(not prep.header.result,'Rejected preparation cannot authorize end checks')
    context=capture_startup_context(reader);snap=context['snapshot']
    expected=next_date(*next_date(prep.year,prep.month,prep.day))
    require((reader.pid,process_birth(reader),reader.memory.base)==(prep.pid,prep.birth,prep.base),'Post-turn attachment changed')
    require(tuple(snap['date'][k] for k in ('year','month','day'))==expected and
            (snap['player']['force_id'],snap['player']['ruler_id'])==(prep.force,prep.ruler),'Post-turn date/identity differs')
    require(snap['state_stack']==['CRootState','CMotorGameState','CGameState','CStrategyState','CUserStrategyState'] and
            context['state_sample']['phase_raw']==2,'Not returned planning')
    kernel=reader.memory.k;kernel.CheckRemoteDebuggerPresent.argtypes=[W.HANDLE,C.POINTER(W.BOOL)]
    kernel.CheckRemoteDebuggerPresent.restype=W.BOOL
    debugging=W.BOOL();require(kernel.CheckRemoteDebuggerPresent(reader.memory.handle,C.byref(debugging)) and not debugging.value,
        'Debugger remained or query failed')
    return dict(result='PASS_READ_ONLY',context=context,game_writes=0,native_calls=0,atomic_snapshot=False)
