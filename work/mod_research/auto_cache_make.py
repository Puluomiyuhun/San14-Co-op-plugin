"""Exact code profile for native cache scanner pilot; no game access."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
image=(ROOT/'game-runtime-image.bin').read_bytes()
assert hashlib.sha256(image).hexdigest()=='5a2ef730f2a075f23cd8880c5acb1f83c99c03810ea23c0663ae9f05b6c04268'
ranges=[(0x328D20,0x328D23),(0x836EF0,0x83747A),(0x836DF0,0x836E59),(0x79E130,0x79E196),(0x2F1650,0x2F17FE),(0x3F9B00,0x3F9B20),(0x50B770,0x50B795)]
header='// Generated exact-build anchors; cache scan uses native 328D20 and 836EF0.\n'
header+='static const unsigned char CACHE_EXE_SHA[]={'+','.join(map(str,bytes.fromhex('42d53bb42c033c6027b6da75e8077f4170f4d684abb0f57483a661225d052025')))+'};\n'
for i,(a,z) in enumerate(ranges):header+='static const unsigned char cache_bytes_%d[]={%s};\n'%(i,','.join(map(str,image[a:z])))
header+='struct CacheFingerprint{uint64_t rva;const unsigned char* bytes;size_t size;};\nstatic const CacheFingerprint CACHE_FINGERPRINTS[]={'
header+=','.join('{0x%X,cache_bytes_%d,sizeof cache_bytes_%d}'%(a,i,i) for i,(a,z) in enumerate(ranges))+'};\n'
(ROOT/'auto_cache_profile.h').write_text(header,encoding='utf-8')
(ROOT/'auto_cache_profile.json').write_text(json.dumps({'ranges':[{'start':a,'end':z,'sha256':hashlib.sha256(image[a:z]).hexdigest()} for a,z in ranges],'parameter_meaning':'This build native leaf returns zero; filename generation selects svdexSC normal-save names. No unsupported semantic name inferred.','game_access':False},indent=2)+'\n',encoding='utf-8')
print(json.dumps({'ranges':len(ranges),'game_access':False}))
