"""Bind final owned-fixture result to sources; no native or process imports."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
frozen=json.loads((HERE/'checkpoint_native_input_handoff.json').read_text(encoding='utf-8-sig'))
verified=[]
for row in frozen['artifacts']:
    p=ROOT/row['path']
    assert sha(p)==row['sha256'],row['path']
    verified.append(dict(path=row['path'],sha256=row['sha256']))
result=json.loads((HERE/'checkpoint_native_input_keyboard_fixture.json').read_text())
audit=json.loads((HERE/'checkpoint_native_input_keyboard_audit.json').read_text())
assert result['result']=='PASS' and result['cases']==14
assert not result['game_accessed'] and not result['full_input_hold_proven']
names=['checkpoint_native_input_keyboard_'+n for n in
    ('audit.py','audit.json','archived.h','bridge.h','bridge.cpp','fixture.cpp',
     'build.cmd','fixture.exe','fixture.json','bridge.obj','core.obj','readme.txt','handoff.py')]
names+=['checkpoint_native_input_core.h','checkpoint_native_input_core.cpp']
report=dict(schema='san14.native-input-keyboard-handoff.v1',created=datetime.now(timezone.utc).isoformat(),
    result='PASS',cases=14,compiler='MSVC x64 /std:c++17 /EHsc /W4 /WX /O2',
    command='cmd /c work\\mod_research\\checkpoint_native_input_keyboard_build.cmd',
    sources_not_edited_after_successful_build=True,
    frozen_input_artifacts_reverified=verified,
    files={n:sha(HERE/n) for n in names},fixture=result,
    archive_sha256=audit['image_sha256'],pdata_sha256=audit['pdata_sha256'],
    actual_machine_code_leaves=len(audit['leaves']),actual_direct_callers=len(audit['callers']),
    production_api='QueryBridge.Bind / Invoke; explicit ScopedRoute plus six audited query wrappers',
    real_game_accessed=False,steam_accessed=False,window_accessed=False,physical_input_accessed=False,
    native_installer_present=False,complete_native_input_hold=False,physical_release_proven=False,
    scope='Production C++ bridge invokes archived leaf machine code in owned memory; no native game installation or owner fence established.',
    limitations=['Caller must independently verify code/ABI, target mapping and owner boundary',
        'Original C++ exception identity proven; arbitrary SEH/foreign unwind not proven',
        'Inline raw reads in 3A3810/3A2DC0, other providers/queues/pending actions remain uncovered',
        'Forward does not mutate; neutral mode changes frozen normal/mouse caches and result AL, never physical raw source',
        'Missing routes are explicit local refusal, not safe transparent global-detour behavior'])
(HERE/'checkpoint_native_input_keyboard_handoff.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(result='PASS',cases=14,frozen_artifacts=len(verified),manifest='checkpoint_native_input_keyboard_handoff.json')))
