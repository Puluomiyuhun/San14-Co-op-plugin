"""Separate exact-build fingerprints; no process access or old file updates."""
from pathlib import Path
import hashlib,json,struct
P=Path(__file__).resolve().parent
blob=(P/'game-runtime-image.bin').read_bytes()
assert hashlib.sha256(blob).hexdigest()=='5a2ef730f2a075f23cd8880c5acb1f83c99c03810ea23c0663ae9f05b6c04268'
old=json.loads((P/'private_checkpoint_save_profile.json').read_text())
anchors=[item for item in old['anchors'] if not 0x412520<=item['rva']<0x412600]
ranges=[(0x2DF990,0x2DFA70),(0x4263C0,0x42649D),
        (0x3F5530,0x3F5790),(0x3F5920,0x3F5A2C),(0x3F7710,0x3F7969),(0x3F7A70,0x3F7B5D),
        (0x509FE0,0x50B509),(0x50B6B0,0x50B78D)]
for a,b in ranges:
    anchors.append({'rva':a,'bytes':blob[a:b].hex(),'instruction':'type0 queue / native state apply / four User callbacks / Update ABI'})
assert struct.unpack_from('<Q',blob,0x12CC4A8+0x28)[0]-0x7ff749440000==0x3F9B00
sha=bytes.fromhex('42d53bb42c033c6027b6da75e8077f4170f4d684abb0f57483a661225d052025')
rows=['#pragma once','#include <cstddef>','#include <cstdint>',
      'struct SaveFingerprint{uintptr_t rva;const unsigned char* bytes;size_t size;};',
      'static const unsigned char SAVE_EXE_SHA[32]={'+','.join(hex(x) for x in sha)+'};']
for n,item in enumerate(anchors):
    rows.append('static const unsigned char SAVE_BYTES_'+str(n)+'[]={'+','.join(hex(x) for x in bytes.fromhex(item['bytes']))+'};')
rows.append('static const SaveFingerprint SAVE_FINGERPRINTS[]={')
rows.extend('{'+hex(item['rva'])+',SAVE_BYTES_'+str(n)+',sizeof(SAVE_BYTES_'+str(n)+')},' for n,item in enumerate(anchors))
rows.append('};')
(P/'checkpoint_push_profile.h').write_text('\n'.join(rows)+'\n')
report={'schema':'san14.checkpoint-push-profile.v2','anchors':anchors,'exe_sha256':sha.hex(),
        'native_queue_rva':0x2DF990,'queue_kind':0,'callback_carrier_bytes':64,'filename':'mppush01.s14',
        'must_preserve_original_user':True,'old_pilot_reenabled':False,'game_access':False}
(P/'checkpoint_push_profile.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'result':'PASS','anchors':len(anchors),'game_access':False}))
