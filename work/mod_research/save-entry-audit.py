"""Reproducible, version-locked offline save entry audit; no game process I/O."""
from pathlib import Path
import sys,struct,json,hashlib
P=Path(__file__).resolve().parent
sys.path[:0]=[str(P/'python_deps'),str(P)]
import disasm_chained as d
import pefile
SHA='5a2ef730f2a075f23cd8880c5acb1f83c99c03810ea23c0663ae9f05b6c04268'
assert hashlib.sha256(d.image).hexdigest()==SHA
expected={
0x3fa06d:'call 0x2e84a0',0x3fa072:'mov dword ptr [rsi + 0x470], 5',
0x3f9b3f:'mov dword ptr [rsi + 0x470], 6',0x3f9b59:'mov dword ptr [rsi + 0x470], 3',
0x3f9b76:'jmp 0x3e74b0',0x3e75f0:'lea r8, [rip + 0xe9c825]',
0x4030f4:'jmp 0x3ebcb0',0x3e751f:'mov dword ptr [rdi + 0x470], 4',0x3f9b8d:'jmp 0x10a60',
0x2e852d:'call 0x2eae80',0x2e8658:'call 0x2f1650',0x2e8717:'call 0x2fc750',0x2e8751:'call 0x2df990',
0x4aa3a6:'call 0x2fc750',0x4aa3bd:'call 0x412520',0x4aa4c9:'call 0x2fc750',0x4aa4e0:'call 0x412520',
0x2fc77d:'mov dword ptr [rip + 0x1d2258d], eax',0x2fc79d:'call 0x510a0',0x2fc7bc:'call 0x510a0',
0x2fc7c5:'call 0x50d20',0x2fc7cd:'call 0x50d20',0x412587:'call 0x4263c0',
0x426409:'lea rax, [rip + 0xeb61e8]',0x426413:'mov qword ptr [rbx + 0x470], rsi',
0x4aa659:'call 0x509640',0x509667:'cmp qword ptr [rcx + rdx*8 - 8], rbx',
0x4aa6b2:'jmp 0x4da320',0x4da33e:'lea rdx, [rip + 0x2e95b]',0x4da35a:'call 0x833cb0',
0x4da366:'call 0x834b60',0x4da370:'mov dword ptr [rip + 0x1b448b2], 0',0x4da37a:'mov dword ptr [rdi + 0x470], 2',
0x4f7064:'call 0x834460',0x4f7074:'call 0x834bc0',0x4f7079:'mov dword ptr [rbx + 0x470], 3',
0x4aa68d:'mov dword ptr [rbx + 0x470], 4',0x4aa688:'jmp 0x465c10',
0x465c14:'cmp dword ptr [rip + 0x1bb9011], 0',0x465c62:'call 0x10a60',
0x2f7abc:'jne 0x2f7ae1',0x2f7b01:'call 0x511d0',0x2f7b2c:'call 0x3a90c0',
0x3a9153:'call 0x510a0',0x3a6ab2:'call qword ptr [rax]',0x2fcba1:'lea rdx, [rip + 0xfadb10]',
}
anchors=[]
for at,want in expected.items():
 i=next(d.decoder.disasm(d.image[at:at+15],at)); got=i.mnemonic+' '+i.op_str
 assert got==want,(hex(at),got,want)
 anchors.append({'rva':hex(at),'instruction':got,'bytes':i.bytes.hex()})
def z(at):return d.image[at:].split(b'\0',1)[0].decode('ascii')
strings={hex(at):z(at) for at in [0x1283e1c,0x12aa6b8,0x12aa7c8,0x12aa7d8,0x12aa800,0x12aa810,0x12aa820,0x12aa838,0x12aa848,0x12aa8e0]}
assert strings['0x1283e1c']=='AI'
assert strings['0x12aa6b8']=='STEAMREMOTESTORAGE_INTERFACE_VERSION014'
exe=Path(r'C:\Program Files (x86)\Steam\steamapps\common\Romance_of_the_Three_Kingdoms_14\SAN14PK_SC.exe')
assert hashlib.sha256(exe.read_bytes()).hexdigest()=='42d53bb42c033c6027b6da75e8077f4170f4d684abb0f57483a661225d052025'
pe=pefile.PE(str(exe)); imports={hex(i.address-pe.OPTIONAL_HEADER.ImageBase):(e.dll.decode(),i.name.decode() if i.name else i.ordinal) for e in pe.DIRECTORY_ENTRY_IMPORT for i in e.imports if i.address-pe.OPTIONAL_HEADER.ImageBase in (0x123cb28,0x123cb30,0x123cb00)}
assert imports['0x123cb28'][1]=='SteamInternal_ContextInit'
base=struct.unpack_from('<Q',d.image,0x12cd408)[0]-0x3f69f0
assert [struct.unpack_from('<Q',d.image,0x12dc5f8+off)[0]-base for off in (8,0x10,0x28)]==[0x4a29d0,0x497a00,0x4aa650]
report={
'schema':'san14.native-save-entry-audit.v1','result':'OFFLINE_ENTRY_BINDER_STATE_MACHINE_AND_STORAGE_NAMESPACE_VERIFIED',
'captured_image_sha256':SHA,'anchors':anchors,'strings':strings,'imports':imports,
'CSaveState':{'vtable':'0x12dc5f8','constructor':'0x4263c0','object_size':'0x4f0','phase_offset':'0x470','thread_offset':'0x478','progress_ui_offset':'0x4e8','initialize':'0x4a29d0','update':'0x4aa650','deinitialize':'0x497a00'},
'request':{'binder':'0x2fc750','layout':{'slot_or_category_dword':0,'filename_std_string':8,'caption_std_string':40},'size':72,'global_copy':['0x201ed10','0x201ed18','0x201ed38'],'source_strings_consumed':True,'do_not_reuse_moved_from_request':True,'queue_push_manual':'0x412520','queue_push_with_callback_auto':'0x2df990'},
'auto_save':{'entry':'0x2e84a0','callsite':'0x3fa06d','timing':'Before leaving player planning; not after period simulation.',
'proof':'call -> user phase5 -> phase6 -> phase3 -> named AI task -> phase4 -> queued player-state pop',
'guards':['native setting key0x24 must be nonzero','world+0x16a8 bit0x100 must be clear','0x5086a0 guard must be absent or zero'],
'side_effects':['calls world-wide cleanup 0x2eae80','rotates settings-manager index +0x3e8 or +0x3f8','selects autosave file ranges 50..59 or110..119'],
'not_suitable_as_unconditional_period_end_entry':True},
'storage':{'kind':'SteamRemoteStorage interface v014, filename namespace','arbitrary_windows_directory_supported':False,'custom_basename_supported':'Not tested in storage backend','standard_filename':'svdexSC%02d.s14 for base slots <50',
'filename_path':'request+8 -> global0x201ed18 -> worker R8 -> archive+0x50 -> stream std::string -> SteamRemoteStorage vtable+0',
'caption_path':'request+0x28 -> global0x201ed38 -> archive+0x30','nonempty_filename_bypasses_slot_formatter':True},
'state_sequence':['queue request on native owner/update thread','native scheduler makes CSaveState top; update checks exact top identity','phase0 -> phase1; phase1 native creates/resumes worker then clears status and sets phase2','phase2 polls worker completion; when done joins/releases and sets phase3','phase3 -> phase4','phase4 handles worker result and queues pop; then clears request globals and refreshes save list','native scheduler pops/deinitializes CSaveState; confirm return to same idle planning state'],
'candidate_minimal_controlled_route':['Before any game call: exact build/anchors, top state and phase2 idle planning, no queued transition, no pending event, no save/load/AI worker, room epoch and input cut frozen, slot protection checked and single-use durable intent recorded.',
'On original main/update thread after or before a known safe native tick (not reentrantly inside serialization): construct 72-byte short-string request using reserved supported slot filename and empty caption.',
'Call binder0x2fc750 then queue helper0x412520 with native state-manager rcx, name CSaveState at0x12aa8e0 and r8=0, following the verified manual-save tail; leave worker start/join and pop to native scheduler.',
'Observe specific save-state instance, matching worker, success0x508CFD EAX=0, finished-state teardown, same date/identity/cut, then read/hash completed expected file. Never treat a preexisting success flag as this request completion.'],
'unknowns_before_live_enable':['Main-thread safe dispatch thunk and busy/transition-queue guards are not implemented or validated in real game.','No live experiment has yet proved pushing CSaveState directly above idle CUserStrategyState needs no extra manual-dialog preamble.','End-of-period completion detector must wait through all reports/events into stable planning; 0x3FA06D is wrong timing.','Native full save coverage and guest post-load world validation remain separate.','Slot enumeration is native-index based. Do not promise arbitrary path or hidden custom basename is reloadable.','Do not call auto entry solely to force a save: it has cleanup/rotation/setting dependencies.'],
'native_save_performed':False,'live_game_calls':0,'game_memory_writes':0,'live_attachment':False,
'binder_shadow':json.loads((P/'save-entry-binder-shadow.json').read_text(encoding='utf8'))}
(P/'save-entry-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps({'result':report['result'],'anchors':len(anchors),'binder_shadow_cases':len(report['binder_shadow']['cases']),'auto_save_is_period_end':False,'storage_namespace':'SteamRemoteStorage14','game_calls':0}))
