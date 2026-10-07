"""Hash-pin unified router and exact frozen dependencies, no game access."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
frozen={}
for name in ('checkpoint_native_input_handoff.json','checkpoint_native_input_consumer_handoff.json'):
    manifest=json.loads((HERE/name).read_text(encoding='utf-8-sig'))
    for row in manifest['artifacts']:
        p=ROOT/row['path'];assert sha(p)==row['sha256'],row['path']
        frozen[row['path']]=row['sha256']
for name,key in (('checkpoint_native_input_keyboard_handoff.json','files'),
                 ('checkpoint_native_input_action_handoff.json','source_and_artifact_sha256')):
    manifest=json.loads((HERE/name).read_text(encoding='utf-8-sig'))
    for file,expected in manifest[key].items():
        p=HERE/file;assert sha(p)==expected,file
        frozen[str(p.relative_to(ROOT)).replace('\\','/')]=expected
fixture=json.loads((HERE/'checkpoint_native_input_router_fixture.json').read_text())
assert fixture['result']=='PASS' and fixture['cases']==14
assert not fixture['full_input_hold'] and not fixture['authorize_release']
names=['checkpoint_native_input_router_'+n for n in
    ('core.h','core.cpp','fixture.cpp','build.cmd','fixture.exe','fixture.json','base.obj',
     'mouse.obj','keyboard.obj','action.obj','core.obj','readme.txt','handoff.py')]
report=dict(schema='san14.native-input-router-handoff.v1',created=datetime.now(timezone.utc).isoformat(),
    result='PASS',cases=14,fixture=fixture,compiler='MSVC x64 /std:c++17 /EHsc /W4 /WX /O2',
    command='cmd /c work\\mod_research\\checkpoint_native_input_router_build.cmd',
    sources_not_changed_after_successful_build=True,
    source_and_artifact_sha256={n:sha(HERE/n) for n in names},
    frozen_dependencies_sha256=frozen,all_frozen_hashes_match=True,
    production_interface='Config.source -> Router.Bind; per-call ScopedRoute/Request -> eight native-ABI entries -> Router.Invoke -> frozen bridges',
    default_mode='ForwardUntouched',cycle='nonzero strictly increasing across every route; post-claim failure stays consumed',
    partial_binding='one-shot and unusable after any bind failure',
    game_accessed=False,steam_accessed=False,window_accessed=False,physical_input_accessed=False,
    native_hook_installed=False,complete_input_hold=False,physical_release_proven=False,authorize_release=False,
    limitations=['Current thread and source ownership/lifetimes, full build, attachment and targets need native installer verification',
        'No Session/controller/IPC or global hook set is modified',
        'Successful query paths execute archived native code; C++ probes inject exception/reentry cases explicitly',
        'Native foreign SEH/finally is unproved; provider/message/other direct readers and physical release remain missing'])
(HERE/'checkpoint_native_input_router_handoff.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(result='PASS',cases=14,frozen_dependencies=len(frozen),manifest='checkpoint_native_input_router_handoff.json')))
