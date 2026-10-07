"""Run the actual C++ rules decoder over read-only game memory or a saved transcript.

The DLL stays in this Python process. No injection, game calls or target writes.
Success establishes observed identity decoding only, never AI installation.
"""
import argparse
from collections import Counter
import ctypes as C
from datetime import datetime
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SOURCES = ['human_rules_readonly_probe.cpp', 'human_ai_runtime_subject.cpp', 'human_ai_group_resolver.cpp']
DEPENDENCIES = SOURCES + ['human_ai_runtime_subject.h', 'human_ai_runtime_profile.h',
    'human_ai_group_resolver.h', 'human_ai_group_resolver_profile.h', 'human_economy_runtime_profile.h']
READ = C.CFUNCTYPE(C.c_bool, C.c_void_p, C.c_uint64, C.c_void_p, C.c_size_t)
DECISIONS = ('NATIVE', 'BYPASS_HUMAN_DECISION', 'HOLD')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def build(folder):
    vc = Path(r'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat')
    script = folder / 'build.cmd'
    script.write_text('@echo off\ncall "' + str(vc) + '" >nul\nif errorlevel 1 exit /b 1\n' +
        'cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /LD /I"' + str(ROOT / 'outputs/san14-link') + '" ' +
        ' '.join('"' + str(HERE / name) + '"' for name in SOURCES) +
        ' /Fe:"' + str(folder / 'human_rules_readonly_probe.dll') + '"\n', encoding='utf-8')
    result = subprocess.run(['cmd', '/d', '/c', str(script)], cwd=folder, capture_output=True)
    (folder / 'build.stdout.txt').write_bytes(result.stdout)
    (folder / 'build.stderr.txt').write_bytes(result.stderr)
    if result.returncode:
        raise RuntimeError(result.stdout.decode(errors='replace') + result.stderr.decode(errors='replace'))
    binary = folder / 'human_rules_readonly_probe.dll'
    record = dict(dll=str(binary), dll_sha256=sha(binary),
        files={str((HERE / n).relative_to(ROOT)):sha(HERE / n) for n in DEPENDENCIES}, game_access=False)
    for name in ('human_ai_policy.h', 'human_economy_policy.h'):
        path = ROOT / 'outputs/san14-link' / name
        record['files'][str(path.relative_to(ROOT))] = sha(path)
    write(folder / 'build.json', record)
    return record


class Transcript:
    def __init__(self, read):
        self.reader = read
        self.reads = {}
        self.errors = []
        self.callback = READ(self.copy)

    def read(self, address, size):
        value = self.reader(address, size)
        if len(value) != size:
            raise ValueError('Partial memory sample')
        key = (address, size)
        if key in self.reads and self.reads[key] != value:
            raise ValueError('Observed data changed during sampling')
        self.reads[key] = value
        return value

    def copy(self, _, address, output, size):
        try:
            C.memmove(output, self.read(address, size), size)
            return True
        except Exception as exc:
            self.errors.append(str(exc))
            return False

    def u64(self, address):
        return struct.unpack('<Q', self.read(address, 8))[0]


def decode(binary, transcript, image, root, humans):
    dll = C.CDLL(str(binary))
    dll.HumanRulesProbeVersion.restype = C.c_uint
    if dll.HumanRulesProbeVersion() != 1:
        raise ValueError('Unsupported probe ABI')
    dll.HumanRulesProbeProfile.argtypes = [READ, C.c_void_p, C.c_uint64]
    dll.HumanRulesProbeProfile.restype = C.c_bool
    dll.HumanRulesProbeSubject.argtypes = [READ, C.c_void_p] + [C.c_uint64]*4 + [C.c_uint, C.POINTER(C.c_uint64), C.c_size_t]
    dll.HumanRulesProbeSubject.restype = C.c_bool
    if not dll.HumanRulesProbeProfile(transcript.callback, None, image):
        raise ValueError('Live AI/economy instruction profile mismatch')
    mask = sum(1 << f for f in humans)
    queries = []
    for route, count, table in ((0, 51, 0xDCA0), (1, 51, 0xDE40), (2, 500, 0x7DF60), (3, 500, 0x7F000)):
        for index in range(1, count+1):
            obj = transcript.u64(root+table+8*index)
            if route == 1:
                fields = transcript.read(obj+0x10, 4)
                if not (fields[0] and fields[1] and struct.unpack_from('<H',fields,2)[0]):
                    continue
            if route == 2:
                fields = transcript.read(obj+0x10, 4)
                if not (fields[0] and struct.unpack_from('<H',fields,2)[0]):
                    continue
            raw = (C.c_uint64*65)()
            if not dll.HumanRulesProbeSubject(transcript.callback, None, image, root, mask, obj, route, raw, 65):
                raise ValueError('Probe argument rejection')
            row = dict(route=('force','district','army','group')[route], index=index, object=obj,
                fault=raw[0], group_fault=raw[1], decision=DECISIONS[raw[2]], force=raw[3], district=raw[4],
                identity_verified=bool(raw[5]), viewer=raw[6], special_option=bool(raw[7]),
                repeated_reads_equal=bool(raw[8]), distinct_reads=raw[9],
                human_main_districts={str(f):raw[10+f] for f in humans})
            if route == 3:
                row.update(group_second_error=raw[62], members=raw[63], first_army=raw[64])
            queries.append(row)
    errors = [r for r in queries if r['fault'] or r['group_fault'] or not r['repeated_reads_equal']]
    active = [r for r in queries if r['route'] != 'group' or r['members']]
    unresolved = [r for r in active if not r['identity_verified'] or r['decision']=='HOLD']
    if transcript.errors or errors:
        status = 'REJECTED_OR_UNSTABLE'
    elif unresolved:
        status = 'OBSERVED_WITH_UNRESOLVED_SUBJECTS'
    else:
        status = 'PASS_READONLY_IDENTITIES'
    return dict(result=status, subject_rows=queries, active_count=len(active),
        active_routes=dict(Counter(r['route'] for r in active)),
        active_decisions=dict(Counter(r['decision'] for r in active)),
        unresolved_active_subjects=unresolved, sampling_errors=transcript.errors)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--build', action='store_true')
    mode.add_argument('--capture', action='store_true')
    mode.add_argument('--replay', type=Path)
    parser.add_argument('--build-record', type=Path)
    parser.add_argument('--pid', type=int)
    parser.add_argument('--humans', type=int, nargs=2, default=[12,2])
    args = parser.parse_args()
    if len(set(args.humans)) != 2 or not all(1 <= f <= 51 for f in args.humans):
        parser.error('Two distinct force IDs in 1..51 required')
    folder = HERE / 'human_rules_readonly_probe_runs' / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    folder.mkdir(parents=True)
    if args.build:
        print(json.dumps(build(folder)))
        return
    if not args.build_record:
        parser.error('--build-record required')
    record = json.loads(args.build_record.read_text(encoding='utf-8'))
    binary = Path(record['dll'])
    if sha(binary) != record['dll_sha256'] or any(sha(ROOT / p)!=h for p,h in record['files'].items()):
        raise ValueError('Probe binary or frozen decoder dependency changed')
    reader = None
    try:
        if args.capture:
            sys.path.insert(0, str(ROOT / 'outputs/san14-link'))
            from game_reader import GameReader
            from checkpoint_dispatch_handoff_live import birth
            reader = GameReader(args.pid)
            before = reader.snapshot()
            if before['state_stack'] != ['CRootState','CMotorGameState','CGameState','CStrategyState','CUserStrategyState']:
                raise ValueError('Read only from the idle planning map')
            image = reader.memory.base
            root = reader.pointer(image+0x1FCA1E0)
            owner_birth = birth(reader.memory.handle)
            transcript = Transcript(reader.memory.read)
            observed = decode(binary, transcript, image, root, args.humans)
            after = reader.snapshot()
            stable = before == after and root == reader.pointer(image+0x1FCA1E0) and owner_birth == birth(reader.memory.handle)
            if not stable:
                observed['result'] = 'REJECTED_OR_UNSTABLE'
            sample = dict(base=image, root=root, humans=args.humans, process_birth=owner_birth,
                before=before, after=after, stable=stable,
                reads=[[a,n,v.hex()] for (a,n),v in sorted(transcript.reads.items())])
            write(folder / 'memory-transcript.json', sample)
        else:
            sample = json.loads(args.replay.read_text(encoding='utf-8'))
            memory = {(a,n):bytes.fromhex(v) for a,n,v in sample['reads']}
            transcript = Transcript(lambda a,n:memory[(a,n)])
            observed = decode(binary, transcript, sample['base'], sample['root'], sample['humans'])
        observed.update(game_access=bool(args.capture), game_writes=0, dll_loaded_in_game=False,
            native_ai_executed=False, rules_installed=False, full_world_verified=False,
            atomic_world_snapshot=False, build_record=record,
            readonly_scope='Actual frozen C++ object decoder on copied reads; no native game function execution.')
        write(folder / 'result.json', observed)
        print(json.dumps(dict(folder=str(folder), **{k:observed[k] for k in
            ('result','active_count','active_routes','active_decisions','game_access','rules_installed')})))
        if observed['result'] != 'PASS_READONLY_IDENTITIES':
            raise SystemExit(1)
    finally:
        if reader:
            reader.close()


if __name__ == '__main__':
    main()
