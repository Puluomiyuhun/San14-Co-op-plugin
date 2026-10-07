"""Version-pinned static assertions. No process/window/native invocation."""
from pathlib import Path
from hashlib import sha256
import json, struct, sys
P=Path(__file__).resolve().parent
sys.path.insert(0,str(P/'python_deps'))
import capstone
d=(P/'game-runtime-image.bin').read_bytes()
assert sha256(d).hexdigest()=='5a2ef730f2a075f23cd8880c5acb1f83c99c03810ea23c0663ae9f05b6c04268'
c=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_64)
b=struct.unpack_from('<Q',d,0x12cd408)[0]-0x3f69f0
anchors=[
 (0x51234a,'call 0x510be0','WndProc dispatch'),
 (0x510c1c,'call 0x3a39d0','mouse movement preprocessing before message dispatch'),
 (0x510ce1,'cmp r12, 0xd','Enter special handling'),
 (0x510d59,'mov edx, 0x201','Enter is reposted as WM_LBUTTONDOWN'),
 (0x510d7c,'mov edx, 0x202','Enter release is reposted as WM_LBUTTONUP'),
 (0x510d92,'cmp r12, 8','Backspace special handling'),
 (0x510d98,'cmp r12, 0x1b','Escape special handling'),
 (0x510e0f,'mov edx, 0x204','Backspace/Escape repost right button'),
 (0x14b5ff,'call 0x838356','DirectInput8Create thunk'),
 (0xe3f2d2,'call 0xafe570','engine calls device polling manager'),
 (0xafe5ee,'call 0xf4a9d0','controller polling'),
 (0xafec86,'call 0xf4c8b0','keyboard polling'),
 (0xafedff,'call 0xf4b3e0','mouse polling'),
 (0xf4c8e6,'call qword ptr [rax + 0xc8]','keyboard IDirectInputDevice Poll'),
 (0xf4c93c,'mov edx, 0x18','buffered keyboard event record size 24'),
 (0xf4c948,'call qword ptr [rax + 0x50]','keyboard GetDeviceData'),
 (0xf4ca62,'call 0xf4bf50','consume buffered keyboard event'),
 (0xf4b3f4,'call qword ptr [rax + 0xc8]','mouse Poll'),
 (0xf4b450,'mov edx, 0x14','mouse GetDeviceState length 20'),
 (0xf4b458,'call qword ptr [rax + 0x48]','mouse GetDeviceState'),
 (0xf4aaee,'call qword ptr [rax + 0xc8]','controller Poll'),
 (0xf4ab0b,'mov edx, 0x110','controller state size 272'),
 (0xf4ab13,'call qword ptr [rax + 0x48]','controller GetDeviceState'),
 (0xf4aab9,'call qword ptr [rax + 8]','controller alternate source callback; not covered by DI-only interception'),
 (0x509b9e,'mov rdi, qword ptr [rax + 0x70]','input wrapper from global manager'),
 (0x509ba7,'mov rdi, qword ptr [rdi + 0x20]','runtime polling manager pointer'),
 (0x509bb8,'call 0xafe3b0','get controller index zero'),
 (0x509bc5,'call 0xafe2f0','get keyboard index zero'),
 (0x509bd2,'call 0xafe310','get mouse index zero'),
 (0x509bea,'call 0x3a35d0','translate keyboard/controller into game cache'),
 (0x509bfa,'call 0x3a3210','translate mouse into game cache'),
 (0x3a36b6,'mov qword ptr [rcx], r9','cache retains raw keyboard pointer'),
 (0x3a3853,'cmp byte ptr [rax + r8 + 0x158], 1','keyboard conversion reads raw key state'),
 (0x3a3443,'mov dword ptr [rbx + rcx*4], edx','mouse conversion publishes button state'),
 (0x3a270f,'mov qword ptr [rax + 0x14], rbx','native input flush clears game button buffers'),
 (0x3a2748,'mov qword ptr [rax + 0x58], rbx','native flush clears game key buffers'),
 (0x3a2789,'mov qword ptr [r8 + rcx*4], rbx','native flush clears mouse buffers'),
 (0x3a2da9,'test byte ptr [rax + 0x50], 0x22','raw keyboard modifier read bypasses normalized buffers'),
 (0x3f9dc6,'mov dword ptr [rax + 0x88], 0xffffffff','User command consumed before later dispatch'),
 (0x3f9f9d,'cmp dword ptr [rax + 0x1b0], 1','latched advance request'),
 (0x3f9fa6,'cmp dword ptr [rbx + 0x47c], ebp','second advance flag'),
 (0x3fa06d,'call 0x2e84a0','advance starts native save'),
 (0x3fa09a,'call 0x3fc270','planning command dispatch'),
]
verified=[]
for rva,expected,meaning in anchors:
 i=next(c.disasm(d[rva:rva+15],rva));actual=f'{i.mnemonic} {i.op_str}'.strip()
 assert actual==expected,(hex(rva),actual,expected)
 verified.append({'rva':hex(rva),'instruction':actual,'bytes':i.bytes.hex(),'meaning':meaning})
assert struct.unpack_from('<Q',d,0x12f2350+0x28)[0]-b==0x509b40
col=struct.unpack_from('<Q',d,0x12f2348)[0]-b
td=struct.unpack_from('<I',d,col+12)[0]
assert d[td+16:td+16+len(b'.?AVCRootState@@\0')]==b'.?AVCRootState@@\0'
sdk=Path(r'C:\Program Files (x86)\Windows Kits\10\Include\10.0.22621.0\um\dinput.h')
report={'scope':'offline static only','game_process_access':False,'native_hook_installed':False,
 'visible_window_created':False,'image_sha256':sha256(d).hexdigest(),'anchors_pass':len(verified),
 'anchors':verified,'root_state_update':{'vtable':'0x12f2350','slot':'0x28','target':'0x509b40'},
 'sdk_header':str(sdk),'sdk_sha256':sha256(sdk.read_bytes()).hexdigest(),
 'candidate_gate':{'preferred_research_boundary':'CRootState input translation section 509B97..509BFF; preserve its preceding lifecycle work and all engine/state updates',
 'native_flush':'3A2700 is a cache flush, not a complete input gate',
 'additional_required':'window-message filtering, raw keyboard/controller bypass coverage, pending command barrier, held-key release/quarantine',
 'sufficient_live_gate_proved':False},
 'minimum_live_reads':[
  {'name':'game HWND','address':'base+19055D0+18','size':'8'},
  {'name':'input runtime','chain':'*[base+201D4C8] -> *[+70] -> *[+20]','fields':'counts +0/+4/+8, device pointer arrays +18/+20/+28; index 0 is used by CRootState'},
  {'name':'keyboard device','fields':'+10 COM ptr; +50 modifier bits; +54 event count; +58 event cache; +154..+157 repeat/last-key; +158..+257 key-state bytes'},
  {'name':'mouse device','fields':'+10 COM ptr; +48..+5F previous state; +60 valid; +64..+77 current 20-byte state'},
  {'name':'controller device','fields':'+10 COM ptr; +15C valid; +160..+26F state; +290/+298 alternate source/output wrappers; +2A0 conversion callback'},
  {'name':'normalized keyboard/controller cache','address':'base+1FCA0A0','size':'0x78','fields':'+0 raw keyboard ptr; +8/+C indices; +14/+18 button masks; +24..+57 analog/repeat; +58/+5C key; +60 repeat; +64 one-shot/repeat flag; +68..+77 special repeat counters'},
  {'name':'normalized mouse cache','address':'base+19E1D30','size':'0x68','fields':'+0/+4 indices; +0C..+23 button state; +24..+32 repeat; +34..+43 coordinates; +44..+63 wheel/drag; +64 active'},
  {'name':'planning side-effect guards','fields':'current User+470=2, User+478->+88 pending command; Game+47C and Game+480->+1B0 pending advance; loaded attachment/world/date unchanged'},
 ],'unproved':['thread/order of poll to root translation to UI consumer','all direct raw input/script consumers','focus and buffered-event replay behavior','actual device population','input-neutral load completion without side effects']}
(P/'transition_input_gate_audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({'anchors_pass':len(verified),'root_vtable_verified':True,'sufficient_live_gate_proved':False}))
