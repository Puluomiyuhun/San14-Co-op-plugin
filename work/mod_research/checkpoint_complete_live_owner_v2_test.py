"""Production build, real own-process factory and retained Owner chain tests.

Never discovers or opens SAN14/Steam; child processes are this fixture and a
Python process loading our DLL solely for Describe/config-refusal ABI tests.
"""
from pathlib import Path
from datetime import datetime
import hashlib
import json
import shutil
import subprocess
import sys
import checkpoint_complete_live_owner_contract as abi

P = Path(__file__).resolve().parent
ARCHIVE = P / 'checkpoint_push_archives/20261006-204306-581930/mppush01.s14'
SHA = '88ddc39fd2fd76c0c4b130bd9a2dad12effa9cfd20a1cb333981d541e8761b8c'
CASES = ('factory-arm-player-refusal', 'success-new', 'success-game-reused-load',
         'report-state', 'user-exception', 'stop-during-load')
MODULES = ('checkpoint_load_worker_bridge', 'checkpoint_load_dispatch_bridge',
           'native_storage_read_core', 'checkpoint_cc_load_observer',
           'checkpoint_cc_load_lifecycle', 'checkpoint_title_identity_adapter',
           'checkpoint_identity_pair_commit', 'checkpoint_load_request_commit',
           'checkpoint_load_input_boundary', 'checkpoint_load_hook_set',
           'checkpoint_forward_native_session', 'checkpoint_forward_planning_observer_v2',
           'checkpoint_bound_input_pending_adapter', 'checkpoint_native_input_hwbp',
           'checkpoint_authorized_forward_admission_controller', 'checkpoint_native_queue_adapter_core',
           'checkpoint_live_storage_binding', 'checkpoint_serialized_storage_gate',
           'checkpoint_live_runtime_guards_v2')

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def fingerprint():
    names = set()
    for stem in MODULES:
        for ext in ('.h', '.cpp'):
            if (P / (stem + ext)).is_file():
                names.add(stem + ext)
    names.update('checkpoint_complete_live_owner_v2' + suffix for suffix in (
        '.cpp', '_build.cmd', '_fixture_build.cmd',
        '_fixture.cpp', '_chain_body.inc', '_chain_authorized.inc', '_test.py'))
    names.update(('checkpoint_complete_live_owner.h', 'checkpoint_complete_live_owner_abi.cpp', 'checkpoint_complete_live_owner_contract.py', 'checkpoint_forward_planning_observer.h', 'checkpoint_live_runtime_guards_core.h', 'checkpoint_native_queue_adapter_profile.h', 'checkpoint_live_runtime_guards_profile.h',
                  'checkpoint_push_bridge.h', 'checkpoint_native_input_pending_adapter.h',
                  'checkpoint_native_input_core.h', 'checkpoint_load_worker_bridge.asm',
                  'checkpoint_load_dispatch_bridge.asm', 'checkpoint_authorized_forward_admission_bridge.asm',
                  'checkpoint_guest_native_session_fixture.asm', 'checkpoint_native_input_hwbp_fixture.asm',
                  'checkpoint_native_input_prefetch_archived.inc', 'checkpoint_live_storage_binding_fixture.asm',
                  'checkpoint_load_input_boundary_fixture_layout.h', 'checkpoint_authorized_forward_admission_setup.inc'))
    # Pin transitive archived profile files used by guards.
    import re
    for inc in re.findall(r'#include "([^"]+)"', (P / 'checkpoint_live_runtime_guards_profile.h').read_text()):
        names.add(inc)
    return {n: sha(P / n) for n in sorted(names)}

def main():
    assert ARCHIVE.stat().st_size == 274880 and sha(ARCHIVE) == SHA
    run = P / 'checkpoint_complete_live_owner_v2_runs' / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    run.mkdir(parents=True, exist_ok=False)
    before = fingerprint()
    for kind in ('build', 'fixture_build'):
        b = subprocess.run(['cmd', '/c', str(P / f'checkpoint_complete_live_owner_v2_{kind}.cmd')], cwd=P, capture_output=True, timeout=120)
        (run / f'{kind}.log').write_bytes(b.stdout + b.stderr)
        if b.returncode:
            print(b.stdout.decode(errors='replace')[-4000:]);return 1
    rows = []
    for case in CASES:
        d = run / case;d.mkdir();local = d / 'svdexccSC03.s14';shutil.copyfile(ARCHIVE, local)
        r = subprocess.run([str(P / 'checkpoint_complete_live_owner_v2_fixture.exe'), case, str(local), str(d / 'request.intent'), str(d / 'identity.intent'), str(d / 'report.bin')], capture_output=True, timeout=25)
        (d / 'stdout.txt').write_bytes(r.stdout);(d / 'stderr.txt').write_bytes(r.stderr)
        lines = [x for x in r.stdout.decode(errors='replace').splitlines() if x.startswith('{')]
        row = json.loads(lines[-1]) if lines else {'passed': False}
        row.update(case=case, exit_code=r.returncode, archive_unchanged=sha(local) == SHA)
        row['passed'] = bool(row['passed'] and r.returncode == 0 and row['archive_unchanged'])
        if (d / 'report.bin').is_file():
            decoded = abi.decode_report((d / 'report.bin').read_bytes())
            (d / 'decoded.json').write_text(json.dumps(decoded, indent=2), encoding='utf8')
            row['binary_report_sha256'] = sha(d / 'report.bin')
            row['capabilities_remain_zero'] = not any(decoded[n] for n in ('ReadyAuthorized', 'FullWorldVerified', 'InputExclusionProven', 'PixelPresentationProven'))
            row['passed'] &= row['capabilities_remain_zero']
        else:
            row['passed'] = False
        rows.append(row)
    child = r'''
import ctypes as C,json,sys
from pathlib import Path
sys.path.insert(0,sys.argv[1]);import checkpoint_complete_live_owner_contract as a
lib=C.WinDLL(str(Path(sys.argv[1])/'checkpoint_complete_live_owner_v2.dll'))
for n in ['DescribeCheckpointCompleteLiveOwner','InstallCheckpointCompleteLiveOwner','GetCheckpointCompleteLiveOwnerReport','StopCheckpointCompleteLiveOwner']:
 f=getattr(lib,n);f.argtypes=[C.c_void_p];f.restype=C.c_uint32
d=a.Description();assert lib.DescribeCheckpointCompleteLiveOwner(C.byref(d))==0
desc=a.decode_description(bytes(d));assert desc['module']==lib._handle
c=a.Config();assert lib.InstallCheckpointCompleteLiveOwner(C.byref(c))!=0
r=a.Report();assert lib.GetCheckpointCompleteLiveOwnerReport(C.byref(r))==0
raw=bytes(r);Path(sys.argv[2]).write_bytes(raw);report=a.decode_report(raw)
assert not report['Armed'] and not report['CasPublished'] and not report['QueueNativeCalls'] and report['OwnerError']
assert lib.StopCheckpointCompleteLiveOwner(None)==0
print(json.dumps({'case':'production-dll-own-process-abi-refusal','passed':True,'game_access':False,'description':desc}))
'''
    d = run / 'production-dll-own-process-abi-refusal';d.mkdir()
    r = subprocess.run([sys.executable, '-c', child, str(P), str(d / 'report.bin')], capture_output=True, timeout=15)
    (d / 'stdout.txt').write_bytes(r.stdout);(d / 'stderr.txt').write_bytes(r.stderr)
    row = json.loads(r.stdout) if r.returncode == 0 else {'case': d.name, 'passed': False}
    row['exit_code'] = r.returncode;rows.append(row)
    after = fingerprint()
    ok = all(x['passed'] for x in rows) and before == after
    result = {'schema': 'san14.complete-live-owner-v2-fixtures.v1', 'passed': ok, 'cases': rows,
              'source_sha256': after, 'source_unchanged_during_build_and_run': before == after,
              'dll_sha256': sha(P / 'checkpoint_complete_live_owner_v2.dll'),
              'fixture_exe_sha256': sha(P / 'checkpoint_complete_live_owner_v2_fixture.exe'),
              'config_bytes': abi.CONFIG_SIZE, 'report_bytes': abi.REPORT_SIZE, 'description_bytes': abi.DESCRIPTION_SIZE,
              'game_access': False, 'steam_access': False, 'fresh_game_process_required': True, 'v1_abi_unchanged': True,
              'factory_scope': 'Actual production Owner configure order, real runtime guards + serialized storage Gate + actual components + durable install intent + six-hook Arm + one original User/HWBP call rejected by pending player command + pre-CAS restoration. Fixture adapts fake game memory, one owned PE storage module and original/site/caller addresses. It does not bypass validators or submit a load.',
              'chain_scope': 'Same Owner members and production Stop/Restore/report exports, actual Session-produced bytes/lifecycle/identity/planning, actual OS worker/join/HWBP and atomic request/pair commits. Native world/menu/FileRead and environment guards are the prior explicit owned fixture doubles; this separately covers postqueue lifetime and serialization, not all production validators end-to-end.',
              'live_test_performed': False, 'fullworld_or_ready_authorized': False}
    (run / 'result.json').write_text(json.dumps(result, indent=2), encoding='utf8')
    print(json.dumps({'passed': ok, 'cases': len(rows), 'failed': [x['case'] for x in rows if not x['passed']], 'result': str(run / 'result.json')}))
    return 0 if ok else 1

if __name__ == '__main__':
    raise SystemExit(main())
