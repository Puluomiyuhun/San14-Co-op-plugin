"""Independent native load-menu mode round trip. Default is read-only.

This queues the normal load menu, allows one native no-selection Update,
then requests a single native cancel and observes the SAME User returning.
It never supplies a selected slot, requests a load/save, or registers metadata.
"""
from pathlib import Path
from datetime import datetime
import argparse
import ctypes as C
from ctypes import wintypes as W
import hashlib
import json
import os
import shutil
import struct
import sys
import time

ROOT = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT), str(ROOT / 'python_deps'), str(ROOT.parents[1] / 'outputs/san14-link')]
from checkpoint_load_mode_contract import MAGIC, Report, decode, drained, report_ok
from checkpoint_load_mode_capture import snapshot, pages
from checkpoint_push_contract import compare_known_coverage

DLL = ROOT / 'checkpoint_load_mode_pilot.dll'
SOURCE = ROOT / 'native_file_identity_runs/20261006-211040-957998/result.json'
EXPORT = ROOT / 'checkpoint_push_runs/20261006-203111-687580/result.json'
NATIVE_INTENT = ROOT / 'checkpoint_load_mode_execute_once.intent'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding='utf8'))


def save(path, data, durable=False):
    with Path(path).open('x', encoding='utf8') as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
        stream.flush()
        if durable:
            os.fsync(stream.fileno())


def precheck(reader, initial=True):
    value = snapshot(reader)
    previous = load(SOURCE)
    assert previous['result'] == 'PASS' and previous['two_observed_native_reads_matched']
    for key in ('pid', 'process_birth', 'base', 'pinned_user', 'pinned_game', 'pinned_world', 'global_rng'):
        assert value[key] == previous['after'][key], ('Attachment or source state changed', key)
    from native_file_identity_start import TARGET, SHA
    assert sha(TARGET) == SHA
    if initial:
        assert value['cache_mode'] == 1 and value['cache_slots'] == previous['after']['cache_slots']
    profile = load(ROOT / 'checkpoint_load_mode_profile.json')
    assert profile['exe_sha256'] == reader.sha256
    for a in profile['anchors']:
        code = bytes.fromhex(a['bytes'])
        assert reader.memory.read(reader.memory.base + a['rva'], len(code)) == code, ('Code anchor changed', hex(a['rva']))
    return value


def get_report(api, reader, address):
    allocation = api.k.VirtualAllocEx(api.handle, None, C.sizeof(Report), 0x3000, 4)
    assert allocation
    thread = None
    completed = False
    try:
        tid = W.DWORD()
        thread = api.k.CreateRemoteThread(api.handle, None, 0, address, allocation, 0, C.byref(tid))
        assert thread
        assert api.k.WaitForSingleObject(thread, 10000) == 0, 'Snapshot thread timeout; buffer retained'
        completed = True
        code = W.DWORD()
        assert api.k.GetExitCodeThread(thread, C.byref(code)) and code.value == 0
        return decode(reader.memory.read(allocation, C.sizeof(Report)))
    finally:
        if thread:
            api.k.CloseHandle(thread)
        if completed or not thread:
            assert api.k.VirtualFreeEx(api.handle, allocation, 0, 0x8000)


def fixture_gate(path):
    from checkpoint_load_mode_test import CASES, fingerprint
    evidence = load(path)
    assert evidence['result'] == 'PASS' and evidence['game_process_access'] is False
    assert evidence['schema'] == 'san14.checkpoint-load-mode-fixtures.v1'
    assert evidence['production_config_bytes'] == 1104 and evidence['report_bytes'] == C.sizeof(Report)
    assert evidence['dll_sha256'] == sha(DLL)
    assert evidence['source_sha256'] == fingerprint()
    assert evidence['fixture_dll_sha256'] == sha(ROOT / 'checkpoint_load_mode_fixture.dll')
    assert evidence['fixture_binary_sha256'] == sha(ROOT / 'checkpoint_load_mode_fixture.exe')
    assert [row['case'] for row in evidence['cases']] == list(CASES)
    assert len(CASES) >= 10 and all(row['passed'] and row['exit_code'] == 0 for row in evidence['cases'])
    proofs = [ROOT / 'checkpoint_push_bridge_fixture.json',
        ROOT / 'checkpoint_load_mode_native_chain_20261006-213454-426568.json',
        ROOT / 'checkpoint_load_mode_dispatch_audit_20261006-214321-461404.json']
    for proof in proofs:
        assert load(proof)['result'] == 'PASS'
    return {'path': str(Path(path).resolve()), 'sha256': sha(path), 'cases': len(CASES), 'dll_sha256': evidence['dll_sha256'],
            'source_sha256': evidence['source_sha256'], 'offline_proofs': {p.name: sha(p) for p in proofs}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--dry', action='store_true')
    mode.add_argument('--execute', action='store_true')
    parser.add_argument('--fixture-evidence', type=Path)
    parser.add_argument('--dry-evidence', type=Path)
    args = parser.parse_args()
    from battle_observer import BattleObserver
    from run_autonomous_pilot import ProcessAPI, pefile
    from checkpoint_live_capture import sample as capture_known
    run = ROOT / 'checkpoint_load_mode_runs' / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    run.mkdir(parents=True, exist_ok=False)
    reader = api = None
    report_address = stop_address = None
    value = None
    try:
        reader = BattleObserver()
        before = precheck(reader)
        save(run / 'before.json', before)
        if not (args.dry or args.execute) or before['result'] != 'PASS':
            save(run / 'result.json', before)
            print(json.dumps({'result': before['result'], 'reasons': before['reasons'], 'path': str(run / 'result.json'), 'game_writes': 0}))
            return
        assert args.fixture_evidence
        fixture = fixture_gate(args.fixture_evidence)
        approved_dll_sha = fixture['dll_sha256']
        full_before = capture_known()
        save(run / 'known-before.json', full_before)
        source_coverage = compare_known_coverage(load(EXPORT.parent / 'known-after.json'), full_before)
        assert source_coverage['matched'], 'Known world differs from exported checkpoint'
        assert precheck(reader) == before
        if args.execute:
            assert args.dry_evidence
            dry = load(args.dry_evidence)
            assert dry['result'] == 'PASS' and dry['mode'] == 'dry' and dry['stable_terminal_observed']
            assert dry['dll_sha256'] == approved_dll_sha and dry['fixture']['sha256'] == fixture['sha256']
            assert report_ok(dry['adapter'], False, dry['before'])
            for key in ('pid', 'process_birth', 'base', 'pinned_user', 'pinned_game', 'pinned_world', 'global_rng', 'cache_graph'):
                assert dry['after'][key] == before[key]
            assert compare_known_coverage(load(Path(args.dry_evidence).parent / 'known-after.json'), full_before)['matched']
            assert not os.path.lexists(NATIVE_INTENT)
        mode_name = 'execute' if args.execute else 'dry'
        claim = ROOT / ('checkpoint_load_mode_' + mode_name + '_claim.json')
        save(claim, {'run': str(run), 'mode': mode_name, 'pid': before['pid'], 'process_birth': before['process_birth'],
              'dll_sha256': approved_dll_sha, 'load_requested': False, 'launcher_sha256': sha(__file__)}, durable=True)
        copied = run / DLL.name
        shutil.copyfile(DLL, copied)
        assert sha(copied) == approved_dll_sha, 'Copied DLL differs from the exact validated fixture binary'
        pe = pefile.PE(str(copied))
        exports = {s.name.decode(): s.address for s in pe.DIRECTORY_ENTRY_EXPORT.symbols if s.name}
        pe.close()
        assert all(name in exports for name in ('InstallCheckpointLoadMode', 'StopCheckpointLoadMode', 'GetCheckpointLoadModeReport'))
        assert sha(copied) == approved_dll_sha, 'Copied DLL changed before LoadLibrary'
        api = ProcessAPI(reader)
        api.call_adapter(api.load_library_address(), str(copied).encode('utf-16le') + bytes(2))
        modules = [base for base, path in api.modules() if str(path).lower() == str(copied).lower()]
        assert len(modules) == 1
        module = modules[0]
        report_address = module + exports['GetCheckpointLoadModeReport']
        stop_address = module + exports['StopCheckpointLoadMode']
        wide = str(NATIVE_INTENT).encode('utf-16le') + bytes(2)
        assert len(wide) <= 1024
        config = struct.pack('<QIIIIQQQ', MAGIC, 1104, 1, int(args.execute), before['pid'], before['process_birth'],
             int(before['base'], 0), int(before['pinned_user'], 0)) + wide.ljust(1024, b'\0') + bytes(32)
        assert len(config) == 1104
        installed = api.call_adapter(module + exports['InstallCheckpointLoadMode'], config)
        deadline, terminal_previous = time.monotonic() + 30, None
        trace = []
        stable = False
        while True:
            value = get_report(api, reader, report_address)
            trace.append({'observed_monotonic': time.monotonic(), 'adapter': value})
            terminal = value['state'] in (3, 7, 8, 9, 10) and drained(value)
            stable = terminal and terminal_previous == value
            terminal_previous = value if terminal else None
            if installed or stable or time.monotonic() >= deadline:
                break
            time.sleep(.2)
        save(run / 'trace.json', trace)
        if not (stable and report_ok(value, args.execute, before)):
            api.call_adapter(stop_address)
            value = get_report(api, reader, report_address)
        after = full_after = None
        actual_pages = pages(reader)
        restored = actual_pages == before['mode_hook_pages']
        if drained(value) and restored:
            after = precheck(reader, initial=not args.execute)
            save(run / 'after.json', after)
            if after['result'] == 'PASS':
                full_after = capture_known()
                save(run / 'known-after.json', full_after)
        coverage = compare_known_coverage(full_before, full_after)
        files_equal = full_after is not None and full_before['save_files'] == full_after['save_files']
        passed = bool(stable and installed == 0 and report_ok(value, args.execute, before) and restored and
                      after and after['result'] == 'PASS' and coverage['matched'] and files_equal and
                      (after['cache_mode'] == 0 if args.execute else after['cache_graph'] == before['cache_graph']))
        result = {'schema': 'san14.checkpoint-load-mode-live.v1', 'result': 'PASS' if passed else 'INCOMPLETE_NO_AUTO_RETRY',
            'mode': mode_name, 'adapter': value, 'before': before, 'after': after, 'fixture': fixture,
            'dll_sha256': sha(copied), 'launcher_sha256': sha(__file__), 'install_exit': installed,
            'stable_terminal_observed': stable, 'actual_hook_slots_and_pages_restored': restored,
            'actual_pages': actual_pages, 'known_coverage': coverage, 'source_known_coverage': source_coverage,
            'existing_save_files_unchanged': files_equal, 'load_mode_round_trip_verified': passed and args.execute,
            'load_requested': False, 'save_requested': False, 'metadata_registration_requested': False,
            'full_world_verified': False, 'B_loaded': False, 'module_remains_until_process_exit': True}
        save(run / 'result.json', result)
        print(json.dumps({k: result[k] for k in ('result', 'mode', 'load_mode_round_trip_verified', 'actual_hook_slots_and_pages_restored', 'existing_save_files_unchanged')}))
        print(run / 'result.json')
    except BaseException as error:
        cleanup = {'attempted': bool(api and stop_address)}
        if api and stop_address:
            try:
                cleanup['stop_exit'] = api.call_adapter(stop_address)
            except BaseException as problem:
                cleanup['stop_error'] = repr(problem)
            try:
                value = get_report(api, reader, report_address)
                cleanup['actual_pages'] = pages(reader)
            except BaseException as problem:
                cleanup['snapshot_error'] = repr(problem)
        if not (run / 'result.json').exists():
            save(run / 'result.json', {'result': 'ERROR_NO_AUTO_RETRY', 'error': repr(error), 'adapter': value,
                'cleanup': cleanup, 'load_requested': False, 'save_requested': False})
        raise
    finally:
        if api:
            api.close()
        if reader:
            reader.close()


if __name__ == '__main__':
    main()
