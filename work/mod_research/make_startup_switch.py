"""Prepare a one-shot title selection handoff; does not access the game."""
import hashlib
import json
from pathlib import Path
import re
import struct
from make_identity_pair_fixture import RANGES
ROOT=Path(__file__).resolve().parent
image=(ROOT/'game-runtime-image.bin').read_bytes()
base=struct.unpack_from('<Q',image,0x12CC4A8+0x28)[0]-0x3F9B00

def vtable(name):
    descriptor=image.index(f'.?AV{name}@@\0'.encode())-16
    matches=[]
    for hit in re.finditer(re.escape(struct.pack('<I',descriptor)),image):
        loc=hit.start()-12
        if loc<0:continue
        sig,offset,_,_,_,own=struct.unpack_from('<6I',image,loc)
        if sig!=1 or offset!=0 or own!=loc:continue
        for ref in re.finditer(re.escape(struct.pack('<Q',base+loc)),image):
            vt=ref.start()+8
            first=struct.unpack_from('<Q',image,vt)[0]-base
            if 0x1000<=first<0x123bacf:matches.append(vt)
    assert len(matches)==1,(name,matches)
    return matches[0]

types={name:vtable(name) for name in ('CTitleState','CPersonData','CForceData','CDistrictData','CWorldData')}
assert types['CTitleState']==0x12DAAF0
blocks=RANGES+[('title_worker',0x4DA390,0x4DA3CF),('handoff_preparer',0x4BDD90,0x4BDE5E)]
blocks += [(f'point_{at:x}',at,at+32) for at in (0x2EE64C,0x508BC2,0x3F69F0,0x3F72C0,0x3F9B00)]
header='// Generated exact-build profile. No patch data or game calls.\n'
header+='\n'.join(f'constexpr uint64_t vt_{name}=0x{vt:X};' for name,vt in types.items())+'\n'
meta=[]
for name,a,z in blocks:
    body=image[a:z]
    header+=f'static const unsigned char fingerprint_{name}[]={{'+','.join(map(str,body))+'};\n'
    meta.append({'name':name,'start_rva':a,'end_rva':z,'sha256':hashlib.sha256(body).hexdigest()})
header+='struct SwitchFingerprint {uint64_t rva;const unsigned char* data;size_t size;};\n'
header+='static const SwitchFingerprint switchFingerprints[]={'
header+=','.join('{0x%X,fingerprint_%s,sizeof fingerprint_%s}'%(a,n,n) for n,a,z in blocks)+'};\n'
baseline_path=ROOT/'startup-load-boundary-baseline.json'
baseline=json.loads(baseline_path.read_text(encoding='utf-8'))
assert baseline['stage']=='title_selection_boundary' and baseline['rva']==0x4DA3B2 and baseline['new_excluded_fields']==[]
tables={'person':0x148,'city':0xDAA8,'district':0xDE40,'force':0xDCA0,'army':0x7DF60}
records=[]
for number,(key,hx) in enumerate(baseline['records'].items()):
    kind,identity=key.split(':');body=bytes.fromhex(hx)
    header+=f'static const unsigned char checkpoint_{number}[]={{'+','.join(map(str,body))+'};\n'
    records.append((number,tables[kind],int(identity),kind=='army'))
header+='struct CheckpointRecord {uint64_t table;unsigned id;bool army;const unsigned char* bytes;size_t size;};\n'
header+='static const CheckpointRecord checkpointRecords[]={'
header+=','.join('{0x%X,%d,%s,checkpoint_%d,sizeof checkpoint_%d}'%(table,i,'true' if army else 'false',n,n)
                 for n,table,i,army in records)+'};\n'
(ROOT/'startup_switch_profile.h').write_text(header,encoding='utf-8')
(ROOT/'startup-switch-profile.json').write_text(json.dumps({'types':types,'code_ranges':meta,
    'game_sha256':'42d53bb42c033c6027b6da75e8077f4170f4d684abb0f57483a661225d052025',
    'entry_rva':0x4DA3B2,'native_entry_rva':0x2FC850,'native_return_rva':0x4DA3BE,
    'source_force':12,'source_ruler':666,'target_force':2,'target_ruler':952,
    'checkpoint_sample_records':len(records),'checkpoint_sample_sha256':hashlib.sha256(baseline_path.read_bytes()).hexdigest(),
    'checkpoint_sample_stage':baseline['stage'],'checkpoint_sample_source':str(baseline_path),
    'checkpoint_sample_scope':'783 partial records from the same load boundary; only army+148..150 display pointer excluded. Not a full-world hash.'},indent=2)+'\n',encoding='utf-8')
s=(ROOT/'observe_startup_identity.cpp').read_text(encoding='utf-8')
s=s.replace('// Observation-only combat gate logger. No game code/data writes or game calls. RNG writers are observed before the native store.',
    '// One-shot title selection handoff. Only the two selected-object pointers may be written; native initialization continues normally.')
s=s.replace('#include "startup_identity_observe.inc"','#include "startup_identity_switch.inc"')
s=s.replace('if(argc!=expectedArgc)', 'if(argc!=expectedArgc && argc!=8)')
s=s.replace('DWORD pid=wcstoul', '''if(argc==8){
        if(std::wcscmp(argv[6],L"execute")&&std::wcscmp(argv[6],L"dry"))return 2;
        executeHandoff=std::wcscmp(argv[6],L"execute")==0;reservationPath=argv[7];
        if(executeHandoff&&reservationPath.empty())return 2;
    }
    DWORD pid=wcstoul''')
s=s.replace('DWORD access=PROCESS_QUERY_INFORMATION|PROCESS_VM_READ;',
    'DWORD access=PROCESS_QUERY_INFORMATION|PROCESS_VM_READ; if(executeHandoff)access|=PROCESS_VM_WRITE|PROCESS_VM_OPERATION;')
s=s.replace('check(process!=nullptr,"OpenProcess read-only");','check(process!=nullptr,"OpenProcess bounded handoff");')
s=s.replace('if(!fixtureMode && rva!=0x2EE64C)', 'if(!fixtureMode && (argc!=8 || rva!=0x2EE64C))')
s=s.replace('check(DebugActiveProcess(pid),"DebugActiveProcess");',
    'if(!fixtureMode)verifySwitchProfile(process,base);\n        check(DebugActiveProcess(pid),"DebugActiveProcess");')
s=s.replace('if(oldEpoch!=pointEpoch)', 'if(oldEpoch!=pointEpoch)')
s=s.replace('std::fclose(log); return result;', 'std::fclose(log); return result;')
assert 'startup_identity_switch.inc' in s and 'verifySwitchProfile(process,base)' in s
(ROOT/'startup_identity_switch.cpp').write_text(s,encoding='utf-8')
t=(ROOT/'test_load_rng_observer.py').read_text(encoding='utf-8')
t=t.replace('observe_load_rng.exe','startup_identity_switch.exe').replace('load-rng-fixtures.json','startup-switch-lifecycle-tests.json')
(ROOT/'test_startup_switch_lifecycle.py').write_text(t,encoding='utf-8')
print(json.dumps({'types':types,'fingerprint_ranges':len(blocks),'generated':True,'game_access':False}))
