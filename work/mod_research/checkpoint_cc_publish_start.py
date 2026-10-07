"""Publish the exact owned CC03 test checkpoint through native Steam FileWrite.

--dry forwards one User Update with no native Storage calls.
--execute requires an exact-binary dry result, publishes once, then verifies two
complete native reads. No world serialization, load, or date advance is issued.
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
MAGIC = 0x53414E1443435031
SHA = '88ddc39fd2fd76c0c4b130bd9a2dad12effa9cfd20a1cb333981d541e8761b8c'
SOURCE_RESULT = ROOT / 'checkpoint_push_runs/20261006-203111-687580/result.json'
ARCHIVE_RESULT = ROOT / 'checkpoint_push_archives/20261006-204306-581930/result.json'
TARGET = Path(r'C:\Program Files (x86)\Steam\userdata\391007908\872410\remote\svdexccSC03.s14')
DLL = ROOT / 'checkpoint_cc_publish.dll'


class BridgeStats(C.Structure):
    _fields_ = [(k, C.c_uint64) for k in ('started', 'native_started', 'native_returned', 'before_calls', 'after_calls', 'abnormal_exits', 'active')] + [('configured', C.c_uint32), ('module_pinned', C.c_uint32)]


class PublishPart(C.Structure):
    _fields_=[(k,C.c_uint32) for k in ('state','osError','exceptionCode','existsCalls','writeAttempts','writeReturned','nativeWriteReturn','intentCreated','intentDurable','localPinReleased','sourceMatched','matched','publishAttempts','sizeCalls')]
    _fields_ += [('writeMethod',C.c_uint64),('sourceSha256',C.c_ubyte*32),('stage',C.c_char*64)]

class Report(C.Structure):
    _fields_ = [('magic', C.c_uint64), ('size', C.c_uint32), ('version', C.c_uint32), ('state', C.c_int32), ('error', C.c_int32)]
    _fields_ += [(k, C.c_uint32) for k in ('mode', 'stopRequested', 'exceptionCode', 'osError')]
    _fields_ += [(k, C.c_uint64) for k in ('base', 'user', 'slot', 'original', 'hook', 'claimCallId', 'caller', 'originalRax')]
    _fields_ += [(k, C.c_uint32) for k in ('installerThread', 'executorThread', 'originalReturned', 'verifyAttempts', 'slotRestored', 'protectionRestored', 'initialProtection', 'observedProtection')]
    _fields_ += [('observedSlot', C.c_uint64)]
    _fields_ += [(k, C.c_uint32) for k in ('contextCalls', 'existsCalls', 'sizeCalls', 'readCalls')]
    _fields_ += [('sizes', C.c_int32 * 3), ('readReturns', C.c_int32 * 2)]
    _fields_ += [(k, C.c_uint32) for k in ('expectedSize', 'verifiedSize', 'identityMatched', 'localPinReleased', 'callbackActive', 'callbackFaults', 'reentrantClaims')]
    _fields_ += [(k, C.c_uint64) for k in ('storage', 'storageVtable', 'existsMethod', 'sizeMethod', 'readMethod')]
    _fields_ += [('expectedSha256', C.c_ubyte * 32), ('localSha256', C.c_ubyte * 32), ('nativeSha256', (C.c_ubyte * 32) * 2), ('stage', C.c_char * 64), ('bridge', BridgeStats)]
    _fields_ += [(k, C.c_uint32) for k in ('bridgeDrainedSnapshot', 'modulePinned', 'nativeLoadAuthorized', 'fullWorldVerified')]
    _fields_ += [('publish',PublishPart)]


assert C.sizeof(Report) == 680 and C.sizeof(PublishPart)==160 and C.sizeof(BridgeStats) == 64


def decode(raw):
    assert len(raw) == C.sizeof(Report)
    report = Report.from_buffer_copy(raw)
    assert report.magic == MAGIC and report.size == 680 and report.version == 1
    value = {k: getattr(report, k) for k, _ in Report._fields_}
    value['sizes'] = list(report.sizes)
    value['readReturns'] = list(report.readReturns)
    for k in ('expectedSha256', 'localSha256'):
        value[k] = bytes(getattr(report, k)).hex()
    value['nativeSha256'] = [bytes(x).hex() for x in report.nativeSha256]
    value['stage'] = report.stage.decode('ascii')
    value['bridge'] = {k: getattr(report.bridge, k) for k, _ in BridgeStats._fields_}
    part=report.publish
    value['publish']={k:getattr(part,k) for k,_ in PublishPart._fields_}
    value['publish']['sourceSha256']=bytes(part.sourceSha256).hex()
    value['publish']['stage']=part.stage.decode('ascii')
    return value


def load(p):
    return json.loads(Path(p).read_text(encoding='utf8'))


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def save(p, value):
    with Path(p).open('x', encoding='utf8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())


def precheck(reader):
    from checkpoint_load_mode_capture import snapshot
    before=snapshot(reader)
    handoff=load(ROOT/'checkpoint_load_mode_verified_handoff.json')
    old=load(handoff['mode_result'])
    assert old['result']=='PASS' and sha(handoff['mode_result'])==handoff['mode_result_sha256']
    for key,value in handoff['current_game'].items():
        assert before[key]==value, ('Planning attachment changed',key)
    assert before['cache_graph']==handoff['current_cache_graph']
    archive=load(ARCHIVE_RESULT)
    assert sha(archive['archive'])==archive['sha256']==SHA
    image=(ROOT/'game-runtime-image.bin').read_bytes()
    assert hashlib.sha256(image).hexdigest()=='5a2ef730f2a075f23cd8880c5acb1f83c99c03810ea23c0663ae9f05b6c04268'
    for rva,size in ((0x2FCB90,0x30),(0x3A90C0,0x1C0)):
        assert reader.memory.read(reader.memory.base+rva,size)==image[rva:rva+size]
    return before


def get_report(api, reader, address):
    # Allocate the report destination ourselves so it can be read before release.
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


def report_ok(r, mode, before):
    base, user = int(before['base'], 0), int(before['pinned_user'], 0)
    expected = {'state': 5 if mode else 4, 'mode': mode, 'error': 0, 'stopRequested': 0,
        'exceptionCode': 0, 'callbackFaults': 0, 'callbackActive': 0, 'reentrantClaims': 0,
        'base': base, 'user': user, 'slot': base + 0x12CC4A8 + 0x28,
        'original': base + 0x3F9B00, 'caller': base + 0x50B785,
        'originalReturned': 1, 'slotRestored': 1, 'protectionRestored': 1,
        'observedSlot': base + 0x3F9B00, 'initialProtection': before['hook_pages']['user']['protect'],
        'observedProtection': before['hook_pages']['user']['protect'],
        'bridgeDrainedSnapshot': 1, 'modulePinned': 1, 'nativeLoadAuthorized': 0, 'fullWorldVerified': 0}
    if not all(r.get(k) == v for k, v in expected.items()):
        return False
    if not all(r.get(k, 0) > 0 for k in ('installerThread', 'executorThread', 'claimCallId', 'hook')):
        return False
    b = r['bridge']
    if b != dict(started=1, native_started=1, native_returned=1, before_calls=1, after_calls=1,
                 abnormal_exits=0, active=0, configured=1, module_pinned=1):
        return False
    p=r['publish']
    if not mode:
        if any(p[k] for k in ('writeAttempts','intentCreated','intentDurable','publishAttempts','matched','writeMethod')):return False
        return all(r[k] == 0 for k in ('verifyAttempts', 'contextCalls', 'existsCalls', 'sizeCalls', 'readCalls', 'identityMatched'))
    if not (p['state']==5 and p['osError']==p['exceptionCode']==0 and p['existsCalls']==p['sizeCalls']==3
        and all(p[k]==1 for k in ('writeAttempts','writeReturned','nativeWriteReturn','intentCreated','intentDurable','localPinReleased','sourceMatched','matched','publishAttempts'))
        and p['writeMethod']>=0x10000 and p['sourceSha256']==SHA and p['stage']=='published_and_observed_twice'):
        return False
    return (r['verifyAttempts'] == 1 and r['contextCalls'] == 1 and r['existsCalls'] == 3
        and r['sizeCalls'] == 3 and r['readCalls'] == 2 and r['sizes'] == [274880] * 3
        and r['readReturns'] == [274880] * 2 and r['expectedSize'] == r['verifiedSize'] == 274880
        and r['identityMatched'] == r['localPinReleased'] == 1
        and r['expectedSha256'] == r['localSha256'] == SHA and r['nativeSha256'] == [SHA, SHA])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    mode = p.add_mutually_exclusive_group()
    mode.add_argument('--dry', action='store_true')
    mode.add_argument('--execute', action='store_true')
    p.add_argument('--fixture-evidence', type=Path)
    p.add_argument('--dry-evidence', type=Path)
    args = p.parse_args()
    requested_mode=int(args.execute)
    mode_name='publish' if args.execute else 'dry'
    from battle_observer import BattleObserver
    from run_autonomous_pilot import ProcessAPI, pefile
    from checkpoint_push_start import hook_pages
    from checkpoint_live_capture import sample as capture_known
    from checkpoint_push_contract import compare_known_coverage
    run = ROOT / 'checkpoint_cc_publish_runs' / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
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
            print(json.dumps({'result': before['result'], 'path': str(run / 'result.json'), 'game_writes': 0}))
            return
        binding=load(ROOT/'checkpoint_cc_publish_binding.json')
        stage=load(ROOT/'checkpoint_cc_stage_result.json')
        assert stage['result']=='PASS' and sha(ROOT/'checkpoint_cc_stage_result.json')==binding['stage_sha256']
        assert stage['target']==str(TARGET) and stage['target_sha256']==sha(TARGET)==SHA
        assert not os.path.lexists(binding['intent']),'Native publication intent already consumed'
        # Exact probe binary/source fixtures must be supplied by its test driver.
        assert args.fixture_evidence
        from checkpoint_cc_publish_gate import validate_fixture
        fixture = validate_fixture(args.fixture_evidence, DLL)
        full_before = capture_known()
        save(run / 'known-before.json', full_before)
        source_coverage = compare_known_coverage(load(SOURCE_RESULT.parent / 'known-after.json'), full_before)
        save(run / 'source-covered-domains.json', source_coverage)
        assert source_coverage['matched'], 'Covered source state changed since the passing A export'
        assert precheck(reader) == before
        if requested_mode:
            assert args.dry_evidence
            dry = load(args.dry_evidence)
            assert dry['result'] == 'PASS' and dry['mode'] == 'dry'
            assert dry['dll_sha256'] == sha(DLL) and dry['fixture_sha256'] == sha(args.fixture_evidence)
            assert report_ok(dry['adapter'], 0, dry['before'])
            for key in ('pid', 'process_birth', 'base', 'pinned_user', 'pinned_game', 'pinned_world', 'global_rng', 'cache_mode', 'cache_slots'):
                assert dry['after'][key] == before[key], key
            assert compare_known_coverage(load(Path(args.dry_evidence).parent / 'known-after.json'), full_before)['matched']
        intent = ROOT / ('checkpoint_cc_publish_' + (mode_name) + '_once.json')
        save(intent, {'schema': 'san14.checkpoint-cc-publish-once.v1', 'run': str(run),
            'pid': before['pid'], 'process_birth': before['process_birth'], 'base': before['base'],
            'dll_sha256': sha(DLL), 'target_sha256': SHA, 'source_result_sha256': sha(SOURCE_RESULT),
            'mode': mode_name, 'native_load_requested': False,'native_write_requested':bool(args.execute)})
        copied = run / DLL.name
        shutil.copyfile(DLL, copied)
        assert sha(copied) == sha(DLL)
        pe = pefile.PE(str(copied))
        exports = {s.name.decode(): s.address for s in pe.DIRECTORY_ENTRY_EXPORT.symbols if s.name}
        pe.close()
        assert all(x in exports for x in ('InstallCheckpointCcPublishProbe', 'StopCheckpointCcPublishProbe', 'GetCheckpointCcPublishReport'))
        api = ProcessAPI(reader)
        api.call_adapter(api.load_library_address(), str(copied).encode('utf-16le') + bytes(2))
        modules = [base for base, path in api.modules() if str(path).lower() == str(copied).lower()]
        assert len(modules) == 1
        module = modules[0]
        stop_address = module + exports['StopCheckpointCcPublishProbe']
        report_address = module + exports['GetCheckpointCcPublishReport']
        wide = str(TARGET).encode('utf-16le') + bytes(2)
        assert len(wide) <= 1024
        config = struct.pack('<QIIIIQQQ', MAGIC, 1104, 1, requested_mode, before['pid'], before['process_birth'], int(before['base'], 0), int(before['pinned_user'], 0)) + wide.ljust(1024, b'\0') + bytes(32)
        assert len(config) == 1104
        installed = api.call_adapter(module + exports['InstallCheckpointCcPublishProbe'], config)
        deadline = time.monotonic() + 30
        trace = []
        terminal_snapshot = None
        while True:
            value = get_report(api, reader, report_address)
            trace.append({'observed_monotonic': time.monotonic(), 'adapter': value})
            terminal = value['state'] >= 4 and value['bridge']['active'] == value['callbackActive'] == 0
            # The report lock and bridge counters are separate snapshots. Require
            # two equal terminal samples so a mid-transition read cannot decide PASS.
            stable_terminal = terminal and terminal_snapshot == value
            terminal_snapshot = value if terminal else None
            if installed or stable_terminal or time.monotonic() >= deadline:
                break
            time.sleep(.2)
        save(run / 'trace.json', trace)
        assert sha(TARGET)==SHA
        if not report_ok(value, requested_mode, before):
            api.call_adapter(stop_address)
            value = get_report(api, reader, report_address)
        after = full_after = None
        pages_after = hook_pages(reader)
        slots_after = {name: struct.unpack('<Q', reader.memory.read(reader.memory.base + rva, 8))[0] for name, rva in (('user', 0x12CC4A8 + 0x28), ('save', 0x12DC5F8 + 0x28))}
        slots_expected = {'user': reader.memory.base + 0x3F9B00, 'save': reader.memory.base + 0x4AA650}
        restored = pages_after == before['hook_pages'] and slots_after == slots_expected
        if not value['bridge']['active'] and not value['callbackActive'] and restored:
            after = precheck(reader)
            save(run / 'after.json', after)
            if after['result'] == 'PASS':
                full_after = capture_known()
                save(run / 'known-after.json', full_after)
        coverage = compare_known_coverage(full_before, full_after)
        files_equal = bool(full_after is not None and full_before['save_files'] == full_after['save_files'])
        passed = stable_terminal and installed == 0 and report_ok(value, requested_mode, before) and restored and after and after['result'] == 'PASS' and coverage['matched'] and files_equal
        result = {'schema': 'san14.checkpoint-cc-publish-live.v1', 'result': 'PASS' if passed else 'INCOMPLETE_NO_AUTO_RETRY',
            'mode': mode_name, 'adapter': value, 'before': before, 'after': after,
            'dll_sha256': sha(copied), 'fixture_sha256': sha(args.fixture_evidence), 'fixture': fixture,
            'install_exit': installed, 'actual_hook_slots_restored': restored, 'hook_pages_after': pages_after, 'hook_slots_after': slots_after,
            'known_coverage': coverage, 'source_known_coverage': source_coverage, 'stage_receipt_sha256':binding['stage_sha256'], 'native_intent':binding['intent'],
            'stable_terminal_observed': stable_terminal, 'existing_files_unchanged': files_equal,
            'two_observed_native_reads_matched': bool(passed and args.execute),
            'native_publish_complete':bool(passed and args.execute), 'target':str(TARGET),
            'game_file_writes_requested':bool(args.execute), 'load_requested': False, 'B_load_authorized': False,
            'future_load_byte_identity_proven': False, 'full_world_verified': False,
            'module_remains_until_process_exit': True}
        save(run / 'result.json', result)
        print(json.dumps({k: result[k] for k in ('result', 'mode', 'two_observed_native_reads_matched', 'actual_hook_slots_restored', 'existing_files_unchanged')}))
        print(run / 'result.json')
    except BaseException as error:
        cleanup = {'attempted': bool(api and stop_address), 'stop_error': None, 'snapshot_error': None,
                   'stop_exit': None, 'snapshot_acquired': False, 'actual_slots': None, 'actual_pages': None}
        if api and stop_address:
            try:
                cleanup['stop_exit'] = api.call_adapter(stop_address)
            except BaseException as cleanup_error:
                cleanup['stop_error'] = repr(cleanup_error)
            if report_address:
                try:
                    value = get_report(api, reader, report_address)
                    cleanup['snapshot_acquired'] = True
                except BaseException as cleanup_error:
                    cleanup['snapshot_error'] = repr(cleanup_error)
            try:
                cleanup['actual_slots'] = {name: struct.unpack('<Q', reader.memory.read(reader.memory.base + rva, 8))[0]
                    for name, rva in (('user', 0x12CC4A8 + 0x28), ('save', 0x12DC5F8 + 0x28))}
                cleanup['actual_pages'] = hook_pages(reader)
            except BaseException as cleanup_error:
                cleanup['memory_query_error'] = repr(cleanup_error)
        if not (run / 'result.json').exists():
            save(run / 'result.json', {'result': 'ERROR_NO_AUTO_RETRY', 'error': str(error), 'adapter': value,
                'cleanup': cleanup, 'load_requested': False, 'two_observed_native_reads_matched': False})
        raise
    finally:
        if api:
            api.close()
        if reader:
            reader.close()


if __name__ == '__main__':
    main()
