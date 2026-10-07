"""Offline preparation of a separate fixed-name profile; never accesses SAN14."""
from pathlib import Path
import hashlib,json,struct
ROOT=Path(__file__).resolve().parent
IMAGE_SHA='5a2ef730f2a075f23cd8880c5acb1f83c99c03810ea23c0663ae9f05b6c04268'
image=(ROOT/'game-runtime-image.bin').read_bytes();assert hashlib.sha256(image).hexdigest()==IMAGE_SHA
prior=json.loads((ROOT/'save_checkpoint_preparation.json').read_text())
anchors=prior['anchors'][:]
for start,end in [(0x4AA650,0x4AA6D2),(0x4DA320,0x4DA38A),(0x4F7050,0x4F70A4),
                  (0x465C10,0x465CC3),(0x508CA0,0x508D28),(0x835DD0,0x835DEE),
                  (0x836DF0,0x836E59),(0x2F7A10,0x2F7B50),(0x3A6A10,0x3A6B39),
                  (0x1479B0,0x147B03),(0x8388D0,0x838906),(0x12C840,0x12C860),(0x12C290,0x12C2B0)]:
    anchors.append({'rva':start,'bytes':image[start:end].hex(),'instruction':'audited native save lifecycle/explicit filename body'})
assert struct.unpack_from('<Q',image,0x12DC5F8+0x28)[0]-0x7FF749440000==0x4AA650
rows=['#pragma once','#include <cstddef>','#include <cstdint>',
      'struct SaveFingerprint{uintptr_t rva;const unsigned char* bytes;size_t size;};']
sha=bytes.fromhex('42d53bb42c033c6027b6da75e8077f4170f4d684abb0f57483a661225d052025')
rows.append('static const unsigned char SAVE_EXE_SHA[32]={'+','.join(hex(x) for x in sha)+'};')
for n,a in enumerate(anchors):rows.append('static const unsigned char SAVE_BYTES_'+str(n)+'[]={'+','.join(hex(x) for x in bytes.fromhex(a['bytes']))+'};')
rows.append('static const SaveFingerprint SAVE_FINGERPRINTS[]={')
rows.extend('{'+hex(a['rva'])+',SAVE_BYTES_'+str(n)+',sizeof(SAVE_BYTES_'+str(n)+')},' for n,a in enumerate(anchors));rows.append('};')
(ROOT/'private_checkpoint_save_profile.h').write_text('\n'.join(rows)+'\n')
result={'schema':'san14.private-checkpoint-save-profile.v1','anchors':anchors,'captured_image_sha256':IMAGE_SHA,
        'exe_sha256':sha.hex(),'filename':'mpckpt01.s14','slot_sentinel':-1,'save_update_slot_rva':0x12DC5F8+0x28,
        'save_update_rva':0x4AA650,'state_manager_rva':0x19E7310,'callback_return_rva':0x50B785,
        'pending_allocator':{'vtable_rva':0x1283498,'allocate_rva':0x12C840,'aligned_allocate_rva':0x12C290,'zero_allocate_rva':0x8388D0,'reallocate_rva':0x1479B0},
        'game_access':False,'native_saved':False}
(ROOT/'private_checkpoint_save_profile.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'result':'PASS','anchors':len(anchors),'game_access':False}))
