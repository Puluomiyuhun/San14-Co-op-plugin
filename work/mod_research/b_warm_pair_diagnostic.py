"""Explicit rules-free, no-new-command two-file game diagnostic.

Default help performs no process access. --check is read-only. --execute uses
exactly the predecessor's retained Resident/run_two native chain after local
files/builds and live original entries are checked. This is not the strict
RemoteOwner guard, a full input lock, a Room Ready path or playable networking.
"""
import argparse
from datetime import datetime
import ctypes as C
from ctypes import wintypes as W
import json
from pathlib import Path
import sys

from b_warm_coordinator import Resident, run_two
from b_warm_profile_capture import capture_planning, profile_from_dict, integer
from b_warm_start import P, PRIVATE, require, save_new, refuse_prior_attempt, sha
from human_rules_stage_live_start import profiles as rule_profiles, GAME_SHA


def require_original_rules(reader, *, pid, birth, read_birth=None, range_check=None):
    """Read six original rule sources twice, not a process-wide exclusion proof.

    Optional readers are for owned tests; production callers use actual process
    birth/page checks. No restore, Revoke, write or native call occurs here.
    """
    if read_birth is None or range_check is None:
        from checkpoint_complete_live_capture import process_birth, readable
        if read_birth is None: read_birth = lambda: process_birth(reader)
        if range_check is None:
            range_check = lambda address,size: readable(reader,address,size,allocation=reader.memory.base,execute=True)
    integer(pid,1,0xffffffff);integer(birth,1,2**64-1)
    base=reader.memory.base
    integer(base,0x10000,0x7fffffffffff-0x2238000)
    expected=rule_profiles()
    require(len(expected)==6 and len({rva for rva,_,_ in expected})==6,'Six exact rule sources required')
    def take():
        require(reader.pid==pid and read_birth()==birth and reader.memory.base==base and reader.sha256==GAME_SHA,
                'Diagnostic process incarnation/build changed')
        rows=[]
        for rva,_,raw in expected:
            address=base+rva
            require(range_check(address,len(raw)) is None,'Rule source range check did not complete')
            actual=reader.memory.read(address,len(raw))
            require(type(actual) is bytes and actual==raw,'Human-rule source is not original: '+hex(rva))
            rows.append(actual)
        require(reader.pid==pid and read_birth()==birth and reader.memory.base==base,'Diagnostic incarnation changed during sample')
        return rows
    require(take()==take(),'Rule source changed across observations')
    return dict(six_sources_original=True,source_rvas=[hex(rva) for rva,_,_ in expected],
                game_writes=0,native_calls=0,input_exclusion_proven=False,scheduler_fence_proven=False)


def require_no_debugger(reader):
    k=reader.memory.k
    k.CheckRemoteDebuggerPresent.argtypes=[W.HANDLE,C.POINTER(W.BOOL)]
    k.CheckRemoteDebuggerPresent.restype=W.BOOL
    found=W.BOOL()
    require(k.CheckRemoteDebuggerPresent(reader.memory.handle,C.byref(found)) and not found.value,
            'A debugger still owns this process; no diagnostic installation')


class DiagnosticResident(Resident):
    """Same native implementation; add original-rules checks at local edges."""
    def __init__(self,*args,identity,**kwargs):
        self.diagnostic_identity=identity
        reader=args[0]
        require_original_rules(reader,pid=identity[0],birth=identity[1])
        require_no_debugger(reader)
        super().__init__(*args,**kwargs)
        self.rule_checks=[]

    def check_rules(self):
        value=require_original_rules(self.reader,pid=self.diagnostic_identity[0],birth=self.diagnostic_identity[1])
        self.rule_checks.append(value)
        return value

    def open_bank(self,index):
        self.check_rules()
        return super().open_bank(index)

    def load(self,bank,profile,raw_file):
        # A refused pre-load check must not Stop the previous successful bank.
        self.current=bank
        self.check_rules()
        result=super().load(bank,profile,raw_file)
        bank['diagnostic_load_retired']=True
        self.check_rules()
        return result

    def abort(self):
        # Post-load diagnostics may fail after real retirement already succeeded.
        # Preserve that success; Stop is only for the inherited unfinished path.
        if self.current and self.current.get('diagnostic_load_retired'):
            return
        super().abort()

    def finish(self):
        self.check_rules()
        super().finish()
        self.check_rules()


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group()
    mode.add_argument('--check',action='store_true')
    mode.add_argument('--execute',action='store_true')
    parser.add_argument('--no-new-commands',action='store_true',
        help='Explicit local diagnostic condition: no manual commands/save/load/advance or other mod changes during the run')
    parser.add_argument('--pid',type=int)
    parser.add_argument('--plan',type=Path)
    for name in ('helper','pair'):
        parser.add_argument('--'+name+'-build',type=Path);parser.add_argument('--'+name+'-sha256')
    parser.add_argument('--timeout',type=int,default=180)
    args=parser.parse_args(argv)
    if not args.check and not args.execute:parser.print_help();return 0
    integer(args.pid,1,0xffffffff);integer(args.timeout,30,1800)
    require(not args.execute or args.no_new_commands,'Explicit no-new-command diagnostic condition required')
    from b_warm_pair_preflight import preflight
    kwargs=dict(helper_build=args.helper_build,helper_sha256=args.helper_sha256,
                pair_build=args.pair_build,pair_sha256=args.pair_sha256)
    checked=preflight(args.plan,**kwargs) # Before process open, claim or DLL load.
    plan=checked['normalized_plan'];typed=[profile_from_dict(p) for p in plan['profiles']]
    sys.path[:0]=[str(PRIVATE/'python_deps'),str(P.parents[1]/'outputs/san14-link')]
    from game_reader import GameReader
    from checkpoint_complete_live_capture import process_birth
    from a_save_local_binding import modules,source_hashes
    from b_warm_start_support import storage_bindings
    import run_autonomous_pilot,checkpoint_live_prefetch_start,a_save_runtime_control,b_warm_start_acceptance
    reader=GameReader(pid=args.pid);port=None
    folder=PRIVATE/'b_warm_pair_diagnostic_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');folder.mkdir(parents=True)
    result=dict(result='REFUSED_BEFORE_CLAIM',game_writes=0,native_calls=0,room_ready=False,
        input_exclusion_proven=False,scheduler_fence_proven=False)
    try:
        birth=process_birth(reader);refuse_prior_attempt(reader.pid,birth)
        before=capture_planning(reader,typed[0],plan['expected_ruler'])
        require(before['birth']==birth,'Planning incarnation changed')
        rules=require_original_rules(reader,pid=reader.pid,birth=birth);require_no_debugger(reader)
        storage=storage_bindings(reader,modules(reader.memory.handle),steam_paths=plan['steam_paths'])
        require(capture_planning(reader,typed[0],plan['expected_ruler'])==before,'Planning changed during diagnostic check')
        fresh=preflight(args.plan,**kwargs)
        require(fresh==checked,'Local plan/files/builds changed during live precheck')
        save_new(folder/'preflight.json',dict(local=checked,planning=before,rules=rules,storage=storage))
        if args.check:
            result.update(result='PASS_READ_ONLY_RULES_FREE_PAIR_CHECK',pid=reader.pid,birth=birth,
                execute_authorized=False,no_new_commands_required=True)
        else:
            pins=source_hashes()
            require_original_rules(reader,pid=reader.pid,birth=birth)
            refuse_prior_attempt(reader.pid,birth)
            claims=PRIVATE/'b_warm_start_claims';claims.mkdir(exist_ok=True)
            save_new(claims/f'{reader.pid}-{birth}.json',dict(pid=reader.pid,birth=birth,run=str(folder),
                kind='rules-free-two-bank-diagnostic',automatic_retry_allowed=False,no_new_commands=True))
            result=dict(result='INCOMPLETE_RETAIN_EVIDENCE',native_drained=False,staging_reuse_authorized=False,
                room_ready=False,input_exclusion_proven=False,scheduler_fence_proven=False)
            save_new(folder/'plan.json',plan)
            pair,helper=checked['pair'],checked['helper']
            port=DiagnosticResident(reader,folder,Path(pair['production_dll']['path']),pair['production_dll']['sha256'],
                Path(helper['production_dll']['path']),helper['production_dll']['sha256'],plan['steam_paths'],
                plan['expected_ruler'],args.timeout,identity=(reader.pid,birth))
            result=run_two(port,typed,plan['target'],plan['second_source'],folder)
            require(all(sha(P.parents[1]/n)==h for n,h in pins.items()),'Diagnostic source changed during operation')
            result.update(sources=pins,original_rules_checks=port.rule_checks,
                diagnostic_contract='RULES_FREE_NO_NEW_COMMANDS_TWO_FILES',scheduler_fence_proven=False,
                full_gameplay_enabled=False,no_new_commands=True)
    except BaseException as exc:
        result.update(result='INCOMPLETE_RETAIN_EVIDENCE' if port else result['result'],error=repr(exc),
                      room_ready=False,native_drained=False,staging_reuse_authorized=False)
    finally:
        if port:
            result['control_uncertain']=port.calls.uncertain
            try: port.close()
            except BaseException as exc:
                result.update(result='INCOMPLETE_RETAIN_EVIDENCE',close_error=repr(exc),native_drained=False)
        try: reader.close()
        except BaseException as exc:
            result.update(result='INCOMPLETE_RETAIN_EVIDENCE',reader_close_error=repr(exc))
        save_new(folder/'result.json',result)
    print(json.dumps(dict(result=result['result'],path=str(folder/'result.json'))))
    return 0 if result['result'].startswith('PASS_') else 1


if __name__=='__main__':raise SystemExit(main())
