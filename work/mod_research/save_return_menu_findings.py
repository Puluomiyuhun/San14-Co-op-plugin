"""Produce bounded, reviewable offline findings for the normal manual save path."""
from pathlib import Path
from datetime import datetime
import sys,json,hashlib,struct
P=Path(__file__).resolve().parent;sys.path.insert(0,str(P));sys.argv=sys.argv[:1]
import disasm_chained as d
image_sha=hashlib.sha256(d.image).hexdigest()
assert image_sha=='5a2ef730f2a075f23cd8880c5acb1f83c99c03810ea23c0663ae9f05b6c04268'
BASE=0x7ff749440000
checks={
0x3FAA12:('lea','rax, [rip + 0xed3b67]'),
0x3FAA40:('call','0x3e0170'),0x3FAA89:('mov','dword ptr [rax + 0x1b0], 0'),
0x3E01A1:('mov','dword ptr [rax - 0x78], r14d'),0x3E01E0:('call','0x792650'),
0x79F97F:('mov','qword ptr [rbp - 0x60], 1'),
0x79F99E:('mov','dword ptr [rbp - 0x5c], 1'),
0x79F9CD:('call','0x411980'),0x79F9D2:('mov','dword ptr [rbx + 0x488], 1'),
0x4119B1:('mov','dword ptr [rax - 0x78], r14d'),0x4119F0:('call','0x426320'),
0x42638B:('call','0x835dd0'),0x426399:('mov','dword ptr [rax + 8], ecx'),
0x4263A6:('mov','dword ptr [rax + 0x3f0], ecx'),
0x4AA23F:('call','0x509640'),0x4AA25C:('mov','esi, dword ptr [rax + 0x170]'),
0x4AA272:('mov','eax, dword ptr [rcx + 8]'),0x4AA277:('je','0x4aa507'),
0x4AA27F:('call','0x836710'),0x4AA287:('test','rax, rax'),
0x4AA306:('call','0x2a1db0'),0x4AA30D:('je','0x4aa5e2'),
0x4AA336:('lea','rdx, [r15 + 0x128]'),0x4AA368:('lea','rdx, [r14 + 0x480]'),
0x4AA39E:('call','0x426930'),0x4AA3A6:('call','0x2fc750'),0x4AA3BD:('call','0x412520'),
0x4AA412:('call','0x2f1650'),0x4AA4C9:('call','0x2fc750'),0x4AA4E0:('call','0x412520'),
0x4AA5E9:('mov','dword ptr [rax + 0x170], 0xffffffff'),
0x465C62:('call','0x10a60'),0x465C69:('mov','dword ptr [rip + 0x1bb909d], 0xffffffff'),
0x79F934:('call','0x10a60'),0x79E627:('cmp','dword ptr [rbx + 0x488], esi'),
0x79E62F:('mov','dword ptr [rbx + 8], 0xb'),0x79E652:('call','qword ptr [rax + 0x10]'),
0x58E520:('ret','0'),0x79ED9B:('call','0x4da420'),0x79E551:('call','0x4b3c50'),
}
anchors=[]
for at,expected in checks.items():
 i=next(d.decoder.disasm(d.image[at:at+15],at));assert(i.mnemonic,i.op_str)==expected,(hex(at),i.mnemonic,i.op_str)
 anchors.append({'rva':hex(at),'instruction':i.mnemonic+' '+i.op_str,'bytes':i.bytes.hex()})
def name_rtti(vt):
 col=struct.unpack_from('<Q',d.image,vt-8)[0]-BASE
 td=struct.unpack_from('<I',d.image,col+12)[0]
 return d.image[td+16:d.image.index(0,td+16)].decode()
assert name_rtti(0x1358458)=='.?AVCConfigDlgState@@'
assert name_rtti(0x12DB4C0)=='.?AVCSaveLoadState@@'
assert name_rtti(0x12DC5F8)=='.?AVCSaveState@@'
assert struct.unpack_from('<Q',d.image,0x12CE580+0x10)[0]==BASE+0x58E520
regressions=sorted(P.glob('save_return_menu_regression_*.json'))
regression=json.loads(regressions[-1].read_text(encoding='utf8'))
assert regression['result']=='PASS' and len(regression['cases'])==4
report={
 'schema':'san14.save-return-menu-findings.v1','result':'OFFLINE_MENU_CONTROL_FLOW_AND_QUEUE_APPLY_VERIFIED',
 'game_access':False,'native_export_success':False,'live_execution_allowed':False,
 'image_sha256':image_sha,'anchors':anchors,'regression':regressions[-1].name,
 'states':[
  {'name':'CConfigDlgState','vtable':'0x1358458','constructor':'0x792650','update':'0x79f8c0','push':'0x3e0170','queue_kind':0},
  {'name':'CSaveLoadState','vtable':'0x12db4c0','constructor':'0x426320','update':'0x4aa200','push':'0x411980','queue_kind':0},
  {'name':'CSaveState','vtable':'0x12dc5f8','constructor':'0x4263c0','update':'0x4aa650','replace_menu':'0x412520','queue_kind':2}],
 'manual_path':[
  'Toolbar command6:3FA820/3FAA0A creates callback12CE580 carrying User pointer, invokes3E0170(type0); resets toolbar+1B0. The callback invoke slot+10 is58E520(ret).',
  'Actual apply pushes Config above User. User lifecycle effects are separate work; this regression substitutes callbacks.',
  'Config command1:79F97F builds8-byte{mode1,secondaryBoolean}; secondary is1 when1C1A70 exists and1C0CD0!=-1, otherwise0.411980(type0) constructs/pushes SaveLoad with empty return callback.',
  'SaveLoad constructor426320 invalidates cache via835DD0, writes cache manager+8=mode and+3F0=secondaryBoolean. Config+488=1 is set immediately after queueing the dialog; it is not a save-success indicator.',
  'SaveLoad Update4AA200 requires exact top509640, dialog exists and selected unsigned index<=120. Nonzero cache mode selects save path; mode0 enters separate load path.',
  'Existing-slot header:836710 result nonnull,835D30 validity true, confirmation2A1DB0 true; source filename from header+128. Decline resets dialog+170=-1 and queues nothing.',
  'Empty slot:836710 result null, filename formatter2F1650. Both routes take caption from SaveLoad+480, construct/copy72-byte request426930, bind2FC750, then replace current SaveLoad via412520(type2).',
  'CSave native completion465C10 queues pop10A60, clears request slot/string lengths, invalidates cache. Root/Strategy/User/Config remain; SaveLoad was destroyed by replacement.',
  'Config resume79E130 checks/rebuilds cache and refreshes menu UI. No automatic Config pop occurs on this return. Explicit close key branch79F917..79F939 queues pop; Config finalization writes result0xB if+488 was set and invokes the empty User callback.',
  'Actual queue apply regression yields5->6->7->7->6->5. User is never finalized/destroyed by stack operations.'],
 'differences_from_direct_push':[
  {'item':'Top-stack ownership','manual':'412520/type2 replaces temporary SaveLoad; Config remains below it','candidate':'2DF990/type0 would push Save above existing User; must never reuse412520 from idleUser','requirement':'REQUIRED structural difference'},
  {'item':'Request preparation','manual':'slot lookup/confirmation/name/caption->426930->2FC750','candidate':'prevalidated explicit short name/sentinel request->2FC750; no ordinary-slot UI','requirement':'REQUIRED matching request ABI/ownership and fresh no-overwrite checks'},
  {'item':'User pause/resume','manual':'User paused when Config pushed, resumed only when Config closes','candidate':'User paused when Save pushed, resumed when Save pops','requirement':'REQUIRED native callbacks; root separately audits actual side effects'},
  {'item':'Return callback','manual':'Config callback12CE580 invoke is empty; SaveLoad callback empty','candidate':'2DF990 accepts empty carrier as existing native callsite2E8751 demonstrates','requirement':'No custom User return callback requirement found in this route'},
  {'item':'User phase/cut','manual':'chosen toolbar/menu/request bodies do not explicitly writeUser+470; generic lifecycle excluded','candidate':'stay phase2 and same date/cut, verify callback effects','requirement':'No special phase5/autosave transition should be copied'},
  {'item':'Save/load manager','manual':'SaveLoad constructor invalidates cache; sets+8=1 and+3F0=1 in tested in-game case','candidate':'bypasses menu constructor; Save completion still invalidates cache','requirement':'Observed menu setup, not yet proved a required serializer preamble; do not blindly write globals'},
  {'item':'Config UI/context','manual':'creates layouts and registers UI; optional5086A0 context invokes4DA420/4B3C50 paired counter/flag changes','candidate':'no Config UI state','requirement':'Do not declare all skipped menu actions harmless; conditional context is outside this emulator path'},
  {'item':'Autosave cleanup','manual':'No2E84A0 auto-wrapper in selected direct menu bodies; no direct2EAE80 call there','candidate':'do not call autosave wrapper to mimic save','requirement':'Not a global transitive absence proof; auto wrapper has separate cleanup/rotation/phase5 semantics'}],
 'limits':regression['limits']+[
  'The correct menu classes and queue behavior are established from RTTI and copied instructions, not from a new live menu recording.',
  'No proof of complete game-world equivalence, retained selection, pause/context semantics, worker success, valid checkpoint, or successful storage.',
  'Config resume/cache rebuild and full dialog initialization/destruction are statically inspected but not executed here.',
  'Normal in-game header/filename/confirmation fixtures are synthetic; the existing-slot accept case only copies bytes inside Unicorn and writes no file.',
  'No existing retired launchers, sources, DLLs, once records, or results were changed.']}
stamp=datetime.now().strftime('%Y%m%d-%H%M%S-%f');path=P/f'save_return_menu_findings_{stamp}.json'
with path.open('x',encoding='utf8') as f:json.dump(report,f,indent=2)
print(json.dumps({'result':report['result'],'anchors':len(anchors),'regression_cases':4,'evidence':str(path),'game_access':False}))
