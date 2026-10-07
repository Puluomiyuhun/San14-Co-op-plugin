"""Offline fingerprint/header preparation for the bounded native save pilot."""
from pathlib import Path
import hashlib,json,struct,sys
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'python_deps'))
from capstone import Cs,CS_ARCH_X86,CS_MODE_64
image=(ROOT/'game-runtime-image.bin').read_bytes()
assert hashlib.sha256(image).hexdigest()=='5a2ef730f2a075f23cd8880c5acb1f83c99c03810ea23c0663ae9f05b6c04268'
audit=json.loads((ROOT/'save-entry-audit.json').read_text(encoding='utf-8'))
decoder=Cs(CS_ARCH_X86,CS_MODE_64)
expected={0x836F76:'lea rcx, [rip + 0x109993b]',0x836F7D:'call qword ptr [rip + 0xa05ba5]',
          0x836F83:'mov rcx, qword ptr [rax]',0x836F86:'mov r8, qword ptr [rcx]',
          0x836F89:'mov rdx, rbx',0x836F8C:'call qword ptr [r8 + 0x68]',
          0x836F90:'test al, al',0x50B782:'call qword ptr [rax + 0x28]',
          0xF704:'lea rax, [rip + 0x19d7c05]'}
anchors=[]
for at,text in expected.items():
 i=next(decoder.disasm(image[at:at+15],at));assert i.mnemonic+' '+i.op_str==text
 anchors.append({'rva':at,'bytes':i.bytes.hex(),'instruction':text})
assert struct.unpack_from('<Q',image,0x18D08B8)[0]-0x7FF749440000==0x2FCB90
assert 0xF70B+0x19D7C05==0x19E7310
for a in audit['anchors']:
 at=int(a['rva'],0);data=bytes.fromhex(a['bytes']);assert image[at:at+len(data)]==data
 anchors.append({'rva':at,'bytes':a['bytes'],'instruction':a['instruction']})
for at,length in [(0x2FC750,0x9A),(0x412520,0x101),(0x4263C0,0x80),(0x2FCB90,0x27),(0x3F9B00,32)]:
 anchors.append({'rva':at,'bytes':image[at:at+length].hex(),'instruction':'native body/prefix'})
rows=['#pragma once','#include <cstddef>','#include <cstdint>',
      'struct SaveFingerprint{uintptr_t rva;const unsigned char* bytes;size_t size;};']
sha=bytes.fromhex('42d53bb42c033c6027b6da75e8077f4170f4d684abb0f57483a661225d052025')
rows.append('static const unsigned char SAVE_EXE_SHA[32]={'+','.join(hex(x) for x in sha)+'};')
for n,a in enumerate(anchors):
 rows.append('static const unsigned char SAVE_BYTES_'+str(n)+'[]={'+','.join(hex(x) for x in bytes.fromhex(a['bytes']))+'};')
rows.append('static const SaveFingerprint SAVE_FINGERPRINTS[]={')
rows.extend('{'+hex(a['rva'])+',SAVE_BYTES_'+str(n)+',sizeof(SAVE_BYTES_'+str(n)+')},' for n,a in enumerate(anchors))
rows.append('};')
(ROOT/'save_checkpoint_profile.h').write_text('\n'.join(rows)+'\n',encoding='utf-8')
report={'schema':'san14.save-checkpoint-pilot-preparation.v1','anchors':anchors,'native_callback':'0x50B785',
        'state_manager_rva':0x19E7310,'root_vtable_rva':0x12AA6B0,'world_vtable_rva':0x12AA638,
        'request_size':72,'sso_offsets':[8,40],'manual_queue_arguments':['base+19E7310','base+12AA8E0',0],
        'file_exists_sequence':{'context_token_rva':0x18D08B8,'context_callback_rva':0x2FCB90,'context_init_iat_rva':0x123CB28,'interface':'SteamRemoteStorage v014','vtable_offset':0x68},
        'game_calls':0,'game_memory_writes':0,'native_queued':False,'native_saved':False,
        'limits':['Owner/update callback is proven by native caller, not claimed Windows primary thread.',
                  'Direct CSaveState queue above idle UserStrategy remains a bounded live hypothesis.',
                  'Steam FileExists is checked on callback immediately before binder; external changes racing after check are not made transactional.',
                  'The pilot reports queued, not worker completion or final file success.']}
(ROOT/'save_checkpoint_preparation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'anchors':len(anchors),'result':'OFFLINE_PREPARATION_PASS','game_access':False}))
