"""Read-only after-check, keeping the original slot and one-shot journals."""
import json,sys,hashlib,ctypes as C
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]/'outputs'/'san14-link'))
from game_reader import GameReader
load=lambda n:json.loads((HERE/n).read_text(encoding='utf-8'))
before=load('economy-extended-after-restoration.json');after=load('economy-shadow-after-live.json')
keys=('snapshot','areas','area_records','native_area_order','city_area_order','center_hexes','assigned_officers','cities','forces_raw','districts_raw')
same={key:before[key]==after[key] for key in keys}
slot=Path(r'C:\Program Files (x86)\Steam\userdata\391007908\872410\remote\svdexSC34.s14')
slotsha=hashlib.sha256(slot.read_bytes()).hexdigest()
r=GameReader()
try:
    present=C.c_int()
    fn=r.memory.k.CheckRemoteDebuggerPresent;fn.argtypes=[C.c_void_p,C.POINTER(C.c_int)];fn.restype=C.c_int
    if not fn(r.memory.handle,C.byref(present)):raise C.WinError(C.get_last_error())
    snapshot=r.snapshot()
finally:r.close()
ok=all(same.values()) and snapshot==after['snapshot'] and not present.value and slotsha=='afd4c6c5f8a30f659ac523b85f522b02b2c03536ed5e55736677ca1927827d95'
report={'result':'UNCHANGED_SAMPLED_BUSINESS_STATE' if ok else 'REVIEW_REQUIRED','snapshot':snapshot,
        'extended_sample_sections_equal':same,'save34_sha256':slotsha,'debugger_present':bool(present.value),
        'journals_preserved':True,'whole_process_or_rng_equality_claimed':False}
(HERE/'economy-shadow-closeout.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
raise SystemExit(0 if ok else 1)
