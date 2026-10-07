"""Offline data-only resolver correlation. Never imports game readers or executes game bytes."""
import ast
import hashlib
import json
import re
import subprocess
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
OLD = ROOT / 'outputs' / 'san14-link'


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    run = HERE / 'human_ai_group_resolver_runs' / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    run.mkdir(parents=True)
    cases = HERE / 'troops-native-cases.txt'
    previous = json.loads((HERE / 'troops-fixture-results.json').read_text(encoding='utf-8'))
    assert digest(cases) == previous['test_input_sha256']
    profile = (HERE / 'human_ai_group_resolver_profile.h').read_text(encoding='utf-8')
    image = (HERE / 'game-runtime-image.bin').read_bytes()
    byte_arrays = {int(index): bytes(map(int, values.split(','))) for index, values in
                   re.findall(r'ProfileBytes(\d+)\[\]=\{([\d,]+)\}', profile)}
    anchor_count = 0
    for rva, index in re.findall(r'\{(0x[0-9a-f]+),ProfileBytes(\d+),sizeof ProfileBytes\d+\}', profile):
        start, data = int(rva, 16), byte_arrays[int(index)]
        assert image[start:start + len(data)] == data
        anchor_count += 1
    assert anchor_count == 11
    names = {'person_valid', 'army_valid', 'leader_district', 'army_force', 'excluded_armies', 'resolve_groups'}
    source = ast.parse((OLD / 'troops_reader.py').read_text(encoding='utf-8-sig'))
    functions = [n for n in source.body if isinstance(n, ast.FunctionDef) and n.name in names]
    assert len(functions) == len(names)
    namespace = {}
    exec(compile(ast.Module(body=functions, type_ignores=[]), 'archived_pure_semantics_only', 'exec'), namespace)
    values = iter(map(int, cases.read_text(encoding='utf-8').split()))
    count = next(values)
    lines = []
    for _ in range(count):
        model = {'persons': {}, 'armies': [], 'districts': [], 'order': [], 'excluded': [], 'relations': []}
        for _ in range(next(values)):
            slot, identity, district, rank = [next(values) for _ in range(4)]
            model['persons'][slot] = dict(slot=slot, id=identity, district=district, rank=rank)
        for i in range(501):
            flag, leader, group = [next(values) for _ in range(3)]
            model['armies'].append(dict(id=i, flag=flag, leader=leader, group=group))
        for i in range(52):
            force, kind, leader = [next(values) for _ in range(3)]
            model['districts'].append(dict(id=i, force=force, kind=kind, leader=leader))
        for key in ['order', 'excluded']:
            model[key] = [next(values) for _ in range(next(values))]
        for _ in range(next(values)):
            model['relations'].append([None if n < 0 else n for n in [next(values) for _ in range(3)]])
        expected = [next(values) for _ in range(501)]
        rows = namespace['resolve_groups'](model)
        assert [r['district_id'] for r in rows] == expected
        for row in rows:
            f, d = row['force_id'], row['district_id']
            decision = 2 if not row['owner_resolved'] else (1 if {2: 2, 12: 11}.get(f) == d else 0)
            first = row['first_member_id']
            lines.append(f"{first if first is not None else -1} {len(row['member_ids'])} {f} {decision}")
    assert next(values, None) is None
    gold = run / 'pure_expected.txt'
    gold.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    vc = Path(r'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat')
    exe = run / 'human_ai_group_resolver_fixture.exe'
    build = run / 'build.cmd'
    build.write_text(f'@echo off\ncall "{vc}" >nul\nif errorlevel 1 exit /b 1\ncl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /I"{OLD}" "{HERE / "human_ai_group_resolver.cpp"}" "{HERE / "human_ai_group_resolver_fixture.cpp"}" /Fe:"{exe}"\n', encoding='utf-8')
    proc = subprocess.run(['cmd.exe', '/d', '/c', str(build)], cwd=run, text=True, encoding='utf-8', errors='replace', capture_output=True)
    (run / 'build.txt').write_text(proc.stdout + proc.stderr, encoding='utf-8')
    if proc.returncode:
        raise RuntimeError(f'build failed: {run}\n{proc.stdout}\n{proc.stderr}')
    proc = subprocess.run([str(exe), str(cases), str(gold)], cwd=run, text=True, encoding='utf-8', errors='replace', capture_output=True)
    (run / 'stdout.txt').write_text(proc.stdout + proc.stderr, encoding='utf-8')
    if proc.returncode:
        raise RuntimeError(f'fixture failed: {run}\n{proc.stdout}\n{proc.stderr}')
    result = json.loads(proc.stdout.strip().splitlines()[-1])
    files = [HERE / f'human_ai_group_resolver{s}' for s in ['.h', '.cpp', '_profile.h', '_fixture.cpp', '_test.py']]
    files += [cases, HERE / 'troops-fixture-results.json', HERE / 'troops-live-model.json', OLD / 'troops_reader.py', OLD / 'human_ai_policy.h', HERE / 'game-runtime-image.bin']
    result.update(source_sha256={str(p.relative_to(ROOT)): digest(p) for p in files}, archived_live_model_included=True,
                  nonempty_live_relations_proven=False, installed_in_game=False, atomic_snapshot=False,
                  scenario_names=previous['scenario_names'], expected_pure_sha256=digest(gold),
                  archived_code_anchors_verified=anchor_count, runtime_query_code_anchors=10,
                  outer_wrapper_anchor_preinstall_only=True)
    (run / 'result.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'result': 'PASS', 'path': str(run / 'result.json')}))


if __name__ == '__main__':
    main()
