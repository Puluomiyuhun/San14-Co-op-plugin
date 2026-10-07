"""Exact-build evidence gate. This module never installs or opens game."""
from pathlib import Path
import hashlib,json,struct
P=Path(__file__).resolve().parent
SOURCES=('checkpoint_cc_publish.h','checkpoint_cc_publish.cpp','checkpoint_cc_publish_guard.h','checkpoint_cc_publish_profile.h',
    'checkpoint_push_bridge.h','checkpoint_push_bridge.cpp','checkpoint_push_bridge.asm',
    'native_storage_read_core.h','native_storage_read_core.cpp','native_storage_publish_core.h','native_storage_publish_core.cpp','checkpoint_cc_publish_binding.h',
    'checkpoint_cc_publish_fixture.cpp','checkpoint_cc_publish_build.cmd','checkpoint_cc_publish_test.py')
CASES=('dry','read','stop-before-claim','stop-during-original','guard-drift-after-original','original-seh','original-cpp',
    'concurrent-delayed-callback','install-publication-race','stop-before-publication','wrong-original-stop','install-exception-after-protect',
    'wrong-self','read-short','read-seh','stop-during-read','write-false','write-seh','stop-during-write','wrong-stage-identity','existing-intent','native-present')
def load(path):return json.loads(Path(path).read_text(encoding='utf8'))
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def validate_binding():
    binding=load(P/'checkpoint_cc_publish_binding.json');a=binding['attachment']
    assert sha(binding['stage'])==binding['stage_sha256']
    assert binding['intent']==str(P/'checkpoint_cc_publish_native_once.intent')
    assert binding['target']==str(Path(r'C:\Program Files (x86)\Steam\userdata\391007908\872410\remote\svdexccSC03.s14'))
    owner=hashlib.sha256(bytes.fromhex(binding['stage_sha256'])+struct.pack('<IQQQ',a['pid'],a['process_birth'],int(a['base'],0),int(a['pinned_user'],0))+binding['intent'].encode('utf-16le')).digest()
    assert owner.hex()==binding['ownerBinding']
    def arr(value):return '{'+','.join('0x%02x'%b for b in value)+'}'
    text='#pragma once\n#include "native_storage_publish_core.h"\n'
    text+='static constexpr wchar_t PUBLISH_INTENT[]=L'+json.dumps(binding['intent'])+';\n'
    text+='static constexpr wchar_t PUBLISH_STAGE_RECEIPT[]=L'+json.dumps(binding['stage'])+';\n'
    text+='static const unsigned char PUBLISH_STAGE_SHA[32]='+arr(bytes.fromhex(binding['stage_sha256']))+';\n'
    text+='static const unsigned char PUBLISH_OWNER[32]='+arr(owner)+';\n'
    text+='static constexpr native_storage_publish::Identity PUBLISH_IDENTITY={%du,%du,%du,{%du,%du}};\n'%tuple(binding['identity'])
    text+='static constexpr DWORD PUBLISH_PID=%du;\n'%a['pid']
    text+='static constexpr unsigned long long PUBLISH_BIRTH=%dull,PUBLISH_BASE=%sull,PUBLISH_USER=%sull;\n'%(a['process_birth'],a['base'],a['pinned_user'])
    assert (P/'checkpoint_cc_publish_binding.h').read_text(encoding='utf8')==text,'JSON binding differs from compiled exact header'
    stage=load(binding['stage'])
    assert stage['result']=='PASS' and stage['target']==binding['target'] and stage['native_slot']==63 and stage['existing_files_unchanged']
    assert all(stage['before'][key]==value for key,value in a.items())
    return binding
def validate_fixture(path,dll):
    value=load(path)
    assert value['schema']=='san14.checkpoint-cc-publish-fixtures.v1' and value['result']=='PASS'
    assert value['game_process_access'] is False and value['native_gameplay_enabled'] is False
    assert value['production_config_bytes']==1104 and value['report_bytes']==680
    assert value['source_sha256']=={name:sha(P/name) for name in SOURCES}
    assert value['dll_sha256']==sha(dll)
    for field,name in [('fixture_dll_sha256','checkpoint_cc_publish_fixture.dll'),('fixture_binary_sha256','checkpoint_cc_publish_fixture.exe')]:assert value[field]==sha(P/name)
    assert [r['case'] for r in value['cases']]==list(CASES)
    assert all(r['passed'] and r['exit_code']==r['failures']==r['callback_active']==0 and r['game_access'] is False for r in value['cases'])
    handoff=load(P/'native_storage_publish_handoff.json')
    core=load(handoff['fixture']);abi=load(handoff['abi'])
    assert sha(handoff['fixture'])==handoff['fixture_sha256'] and sha(handoff['abi'])==handoff['abi_sha256']
    assert core['result']=='PASS' and abi['result']=='PASS'
    for name in ('native_storage_publish_core.h','native_storage_publish_core.cpp'):
        assert handoff['source_sha256'][name]==sha(P/name)
    oldread=load(P/'native_storage_read_fixtures/20261006-204450-769948/result.json')
    assert oldread['result']=='PASS' and len(oldread['cases'])==25
    for name in ('native_storage_read_core.h','native_storage_read_core.cpp'):assert oldread['source_sha256'][name]==sha(P/name)
    bridge=load(P/'checkpoint_push_bridge_fixture.json')
    assert bridge['result']=='PASS' and bridge['checks']==52 and not bridge['game_process_access']
    binding=validate_binding()
    return {'fixture_path':str(Path(path).resolve()),'fixture_sha256':sha(path),'source_sha256':value['source_sha256'],
        'dll_sha256':sha(dll),'cases':len(CASES),'core_handoff_sha256':sha(P/'native_storage_publish_handoff.json'),
        'stage_binding_sha256':sha(P/'checkpoint_cc_publish_binding.json'),'game_access':False}
