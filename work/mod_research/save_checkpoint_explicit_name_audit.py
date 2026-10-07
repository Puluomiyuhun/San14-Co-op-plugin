"""Offline direct-reference audit; never loosens the standard-slot save pilot."""
from pathlib import Path
from bisect import bisect_right
import hashlib,json,struct,sys
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT));sys.argv=sys.argv[:1]
import disasm_chained as d
IMAGE_SHA='5a2ef730f2a075f23cd8880c5acb1f83c99c03810ea23c0663ae9f05b6c04268'
assert hashlib.sha256(d.image).hexdigest()==IMAGE_SHA
targets={0x201ED10,0x201ED18,0x201ED28,0x201ED30,0x201ED38,0x201ED48,0x201ED50}
adjusted={t-s for t in targets for s in (0,1,4)};roots={}
for align in range(4):
 end=0x1200000;data=d.image[align:end-(end-align)%4]
 for index,(value,) in enumerate(struct.iter_unpack('<i',data)):
  position=align+index*4
  if position+4+value in adjusted:
   entry=d.entries[bisect_right(d.starts,position)-1]
   if entry[0]<=position<entry[1]:roots[d.primary(entry)[0]]=d.primary(entry)
references=[]
for root in roots.values():
 for start,end,_ in sorted(set(d.groups[root]+[root])):
  for instruction in d.decoder.disasm(d.image[start:end],start):
   for operand in instruction.operands:
    if operand.type==d.capstone.x86.X86_OP_MEM and operand.mem.base==d.capstone.x86.X86_REG_RIP:
     target=instruction.address+instruction.size+operand.mem.disp
     if target in targets:
      references.append({'function':hex(root[0]),'rva':hex(instruction.address),'instruction':instruction.mnemonic+' '+instruction.op_str,
                         'target':hex(target),'operand_access':operand.access,'bytes':instruction.bytes.hex()})
report={'schema':'san14.explicit-checkpoint-name-static-audit.v1','captured_image_sha256':IMAGE_SHA,
        'references':references,'slot_global_references':[r for r in references if r['target']=='0x201ed10'],
        'scope':'Direct RIP references within unwind-covered functions, with rel32 candidate prescan; indirect aliasing, leaf-only code and data-built references are not exhaustively resolved.',
        'game_access':False,'native_calls':0,'game_writes':0,'standard_slot_gate_changed':False}
report['slot_role_conclusion']={
 'direct_reads_found':False,'direct_writes_found':3,
 'interpretation':'Captured save worker/finalizer path does not require the slot value for its target filename. The broader claim that it is ONLY UI bookkeeping is not proved.',
 'not_proven':['All indirect/alias references to request globals','Real custom-file save completion','Round-trip custom-file load and identity preservation']}
report['explicit_filename_chain']=[
 {'function':'2FC750','evidence':'Copies request.slot to 201ED10; moves filename/caption short strings to 201ED18/201ED38.',
  'source':'save-entry-2fc750.txt'},
 {'function':'508CA0','evidence':'508CB6/508CDA choose filename data; 508CE2 sets EDX=0; 508CE4 calls 2EE740 with R8 filename and R9 caption.',
  'source':'full-508ca0.txt'},
 {'function':'2EE740','evidence':'Input R8 filename retained in RBP; 2EE85D forwards R8=RBP and 2EE866 calls 2F7A10.',
  'source':'full-2ee740.txt'},
 {'function':'2F7A10','evidence':'Nonempty explicit filename branch at 2F7ABC goes to 2F7AE1, bypassing formatter call 2F7AD9 -> 2F1650; 2F7B01 copies name to archive+50; 2F7B2C passes it to 3A90C0 with mode=0.',
  'source':'save-entry-2f7a10.txt'},
 {'function':'3A90C0','evidence':'3A9153 copies supplied filename into stream; write branch reached with mode=0.',
  'source':'save-entry-3a90c0.txt'},
 {'function':'2FCE40','evidence':'2FCE81 calls 3A6A10 for archive stream finalization; no direct slot-global reference.',
  'source':'full-2fce40.txt'},
 {'function':'3A6A10','evidence':'3A6A91 gets Steam context, 3A6A9F..3A6AA6 chooses stream filename, 3A6AB2 invokes storage vtable+0 with filename, buffer and size.',
  'source':'full-3a6a10.txt'}]
report['completion_and_cache']={
 'completion':'465C10 clears request.slot to -1 and filename/caption length to zero; calls 835DD0 on cache manager.',
 'invalidation':'835DD0 calls 836DF0 to clear cached list and 120 pointer entries, then sets manager+3EC=-1. This is cache invalidation, not an immediate rescan or an index-specific slot update.',
 'scan':'836EF0 loops ESI=0..119, passes index to 2F1650, queries FileExists for that generated name, and loads only names found by that loop.',
 'custom_name_visibility':'mpcheck01.s14 is not a generated standard name, so this scanner will not enumerate it in the ordinary slot cache.',
 'load_requirement':'A future independent-name checkpoint route still needs a separately audited load request using an explicit filename, or an explicit controlled staging design.',
 'sources':['save-entry-465c10.txt','full-835dd0.txt','full-836df0.txt','full-836ef0.txt','save-entry-2f1650.txt']}
report['decision']={
 'current_standard_slot_pilot':'NO_EMPTY_SLOT in the parent-observed installation; no existing standard save may be overwritten.',
 'custom_filename':'Supported as a candidate by explicit native filename dataflow, not approved or live-tested by this audit.',
 'future_profile_requirements':['Separate custom-name configuration/profile; do not relax standard-slot gate',
 'New <=15-byte ASCII basename with strict dedicated mod prefix; reject path separators and all native slot/auto-save names',
 'Durable create-new intent before native requests; local and native Steam FileExists absence checks immediately before binder',
 'Choose and audit a sentinel slot policy; -1 is tolerated by copied binder but full real-game lifecycle remains untested',
 'Keep original state-scheduler callback, full guards, single request and native CSaveState ownership',
 'Treat QUEUED as incomplete; observe native success, stable new file and return to planning idle without date/identity drift',
 'Compare all pre-existing save hashes and retain an unambiguous captured-file manifest',
 'Audit matching explicit-name load path and preserve B identity before claiming checkpoint round trip'],
 'race_limit':'FileExists plus local absence is not an atomic create-if-absent operation against concurrent Steam/cloud writers; dedicated unique name reduces collisions but does not turn FileWrite into a compare-and-swap.'}
(ROOT/'save_checkpoint_explicit_name_audit.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report['slot_global_references'],indent=2))
print('referencing functions',sorted({r['function'] for r in references}))
