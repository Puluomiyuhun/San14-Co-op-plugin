"""Hash-bind final action adapter evidence, without native/game access."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
core=json.loads((HERE/'checkpoint_native_input_handoff.json').read_text(encoding='utf-8-sig'))
for row in core['artifacts']:assert sha(ROOT/row['path'])==row['sha256'],row['path']
keyboard=json.loads((HERE/'checkpoint_native_input_keyboard_handoff.json').read_text())
for name,expected in keyboard['files'].items():assert sha(HERE/name)==expected,name
fixture=json.loads((HERE/'checkpoint_native_input_action_fixture.json').read_text())
audit=json.loads((HERE/'checkpoint_native_input_action_audit.json').read_text())
assert fixture['result']=='PASS' and fixture['cases']==14
names=['checkpoint_native_input_action_'+n for n in
    ('audit.py','audit.json','archived.h','bridge.h','bridge.cpp','fixture.cpp','build.cmd',
     'fixture.exe','fixture.json','core.obj','bridge.obj','readme.txt','handoff.py')]
names+=['checkpoint_native_input_core.h','checkpoint_native_input_core.cpp']
report=dict(schema='san14.native-input-action-handoff.v1',created=datetime.now(timezone.utc).isoformat(),
    result='PASS',cases=14,fixture=fixture,
    compiler='MSVC x64 /std:c++17 /EHsc /W4 /WX /O2',
    command='cmd /c work\\mod_research\\checkpoint_native_input_action_build.cmd',
    sources_not_changed_after_successful_build=True,
    source_and_artifact_sha256={name:sha(HERE/name) for name in names},
    frozen_core_artifact_count=len(core['artifacts']),frozen_keyboard_file_count=len(keyboard['files']),
    all_frozen_hashes_match=True,original_action_stubbed=False,original_getter_stubbed=False,
    native_function_bytes=[dict(name=r['name'],sha256=r['sha256'],rva=r['rva']) for r in audit['regions']],
    observed_direct_callers=len(audit['callers']),rip_sources=audit['rip_sources_derived_from_machine_code'],
    development_failure=dict(owned_process_exit_code=-1073741819,result='ACCESS_VIOLATION',
        finding='Wrong manually calculated mapping pointer RVA; corrected to disassembler-derived 1FD1678 and enforced by static_assert',
        wrong_build_accessed_game=False),
    game_accessed=False,steam_accessed=False,physical_input_accessed=False,window_accessed=False,
    native_hook_installed=False,complete_input_hold=False,physical_release_proven=False,
    limits=['Own executable static TLS and buffers are synthetic sources; the original native code executes without stubs',
        'Whole-game build, attachment, owner-thread exclusion, source extents/lifetimes and safe installed routing remain external obligations',
        'Before/after source sampling is not a global fence or proof against racing ABA',
        '3A3810 conversion, other readers/providers/queues/pending inputs and release grant remain outside scope',
        'Native fast-path exceptions/foreign SEH unwind are not established by these fixtures'])
(HERE/'checkpoint_native_input_action_handoff.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(result='PASS',cases=14,all_frozen_hashes_match=True,manifest='checkpoint_native_input_action_handoff.json')))
