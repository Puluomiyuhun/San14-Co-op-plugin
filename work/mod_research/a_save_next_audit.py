"""Offline audit of the specific next single-save candidate; never opens a process.

Default prints help. --check hashes only repository/private build archives and
parses PE/ABI metadata. PASS does not authorize installation or prove live idle.
"""
import argparse
import ctypes as C
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sys

P = Path(__file__).resolve().parent
PRIVATE = P.parents[2] / 'mod_research'
RUNTIME = PRIVATE / 'a_save_abort_pending_runtime_runs/20261009-135510-973447'
PUBLISHER = PRIVATE / 'a_save_abort_publish_runs/20261009-135151-357545'
APPROVED = {
    'runtime': '85a2bf2d9c176cf8917ae757d492cb19d64e2ea577003dbf58ac5e1c64148974',
    'abi': '4b6f834e5b35a6860f9ff58bb5e1fd70d856842502b314438fdccc9604e98703',
    'publisher': '9d278c350607379b5e68113ea5181a0d0e539dfa29a10cfb04e9824fbaa4c66f',
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(ok, message):
    if not ok:
        raise ValueError(message)


def exact(path, digest, records):
    p = Path(path).resolve(strict=True)
    require(p.is_file() and sha(p) == digest, 'File identity differs: ' + str(p))
    records[str(p)] = digest
    return p


def named(folder, name, digest, records):
    require(type(name) is str and Path(name).name == name and name not in ('.', '..'), 'Plain artifact name required')
    found = [p for p in Path(folder).rglob(name) if p.is_file()]
    require(len(found) == 1, 'Exactly one artifact required: ' + name)
    return exact(found[0], digest, records)


def source_map(values, records):
    require(type(values) is dict and values, 'Nonempty source manifest required')
    for name, digest in values.items():
        require(Path(name).name == name, 'Plain source name required')
        exact(P / name, digest, records)


def audit():
    records = {}
    reports = {}
    for key, file in (('runtime', RUNTIME / 'result.json'), ('abi', RUNTIME / 'abi/result.json'), ('publisher', PUBLISHER / 'result.json')):
        reports[key] = json.loads(exact(file, APPROVED[key], records).read_text(encoding='utf-8-sig'))
        require(reports[key]['result'] == 'PASS', 'Candidate lacks passing archive: ' + key)
    outer, abi, pub = (reports[k] for k in ('runtime', 'abi', 'publisher'))
    require(outer['execution'] == abi and abi['abi_executed'] is True, 'Outer/ABI result differs')
    prod = abi['production']
    require(prod['result'] == 'PASS' and not prod['game_access'] and not prod['executed'], 'Production build meaning differs')
    for values in (outer['sources'], prod['sources'], abi['own_sources'], pub['sources']):
        source_map(values, records)
    for group, folder in ((prod['binaries'], RUNTIME / 'abi/production'), (prod['generated'], RUNTIME / 'abi/production'),
                          (abi['generated'], RUNTIME / 'abi'), (pub['binaries'], PUBLISHER), (pub['generated'], PUBLISHER)):
        for name, digest in group.items():
            named(folder, name, digest, records)
    for name, digest in prod['private_inputs'].items():
        exact(PRIVATE / name, digest, records)
    exact(RUNTIME / 'generated_exports_build.py', outer['generated_sha256'], records)
    exact(RUNTIME / 'abi/production/generated_build.py', prod['build_generator_sha256'], records)
    require(all(c['owned_child_exited'] for c in pub['cases']) and len(pub['cases']) == 6 and not pub['surviving_owned_pids'], 'Publisher cases incomplete')
    expected = ('a_save_abort_pending_owner.cpp', 'a_save_covered_gate.cpp', 'a_save_abort_host.cpp', 'a_save_abort_runtime_exports.cpp')
    require(all(n in prod['sources'] for n in expected) and 'a_save_abort_publish.cpp' in pub['sources'], 'Wrong cleanup/queued-User implementation')
    sys.path.insert(0, str(PRIVATE / 'python_deps'))
    import pefile
    import a_save_runtime_contract as wire
    dll = named(RUNTIME / 'abi/production', 'a_save_local_runtime.dll', prod['binaries']['a_save_local_runtime.dll'], records)
    pe = pefile.PE(str(dll))
    try:
        exports = {s.name.decode('ascii'): s.address for s in pe.DIRECTORY_ENTRY_EXPORT.symbols if s.name}
        require(all('ASaveRuntime' + name in exports for name in wire.OPS), 'Missing typed Runtime export')
        for name in ('ASaveAbortReceipt', 'ASaveCoveredGateFirstFailure'):
            require(name in exports, 'Missing bounded failure DATA export: ' + name)
            sec = pe.get_section_by_rva(exports[name])
            require(sec is not None and sec.Characteristics & 0x40000000 and sec.Characteristics & 0x80000000 and not sec.Characteristics & 0x20000000,
                    'Expected readable/writable nonexecutable DATA export: ' + name)
        imports = sorted(e.dll.decode('ascii') for e in pe.DIRECTORY_ENTRY_IMPORT)
        require('checkpoint_planning_hold.dll' in imports, 'Expected pinned planning dependency')
    finally:
        pe.close()
    schema = json.loads((RUNTIME / 'abi/schema.json').read_text(encoding='utf-8'))
    for name, kind in wire.TYPES.items():
        entry = schema['structures'][name]
        require(entry['size'] == C.sizeof(kind), 'ABI size: ' + name)
        for field, typ in kind._fields_:
            native = entry['fields'][field]
            require(native['offset'] == getattr(kind, field).offset and native['size'] == C.sizeof(typ), 'ABI field: ' + name + '.' + field)
    # Current launch/control code is recorded, not misrepresented as old native-build input.
    for name in ('a_save_next_audit.py', 'a_save_diagnostic_start.py', 'a_save_runtime_control.py', 'a_save_runtime_contract.py',
                 'a_save_failure_diagnostic.py', 'a_save_local_binding.py', 'a_save_observation_status.py'):
        exact(P / name, sha(P / name), records)
    return dict(result='PASS_OFFLINE_A_SINGLE_SAVE_CANDIDATE', game_access=False, steam_access=False, native_calls=0,
        execution_authorized=False, live_preflight_pending=True, build_run=str(RUNTIME / 'abi'), publisher_build=str(PUBLISHER),
        runtime_dll=str(dll), runtime_sha256=sha(dll), imports=imports, typed_abi_checked=True, aborted_receipt_export=True,
        source_references=10 + len(prod['sources']) + len(abi['own_sources']) + len(pub['sources']),
        production_binaries=len(prod['binaries']), publisher_binaries=len(pub['binaries']),
        private_inputs=len(prod['private_inputs']), pins=records, pin_count=len(records),
        constraints=['fresh process and current PID/birth must be captured', 'read slot34 then idle on Zhang Lu map; no new commands or date advance',
                     'one save only; no automatic native replay', 'success requires artifact and independently restored sources',
                     'uncertain call/debug-event owner must not be killed', 'no multiplayer or all-writer proof'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    if not args.check:
        parser.print_help()
        return 0
    run = PRIVATE / 'a_save_next_audit_runs' / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    run.mkdir(parents=True)
    try:
        result = audit()
    except Exception as error:
        result = dict(result='FAIL', error=repr(error), game_access=False, native_calls=0, execution_authorized=False)
    path = run / 'result.json'
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print(json.dumps(dict(result=result['result'], path=str(path), sha256=sha(path))))
    return 0 if result['result'].startswith('PASS_') else 1


if __name__ == '__main__':
    raise SystemExit(main())
