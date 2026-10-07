"""Offline native cleanup with borrowed/non-owned save-menu table entries.

The 50 values are copied from the saved diagnostic into private VM memory;
their destinations are deliberately unmapped. No game memory is accessed.
"""
from datetime import datetime
import hashlib,json
from checkpoint_push_native_chain import ChainHarness, ROOT, BASE, MEM
import checkpoint_push_native_chain_modes as mode_cases
from unicorn import UC_HOOK_MEM_READ,UC_HOOK_MEM_WRITE
from unicorn.x86_const import UC_X86_REG_RIP

DIAGNOSTIC=ROOT/'checkpoint_push_cache_precheck_diagnostic.json'
diagnostic=json.loads(DIAGNOSTIC.read_text(encoding='utf-8'))
slots={int(i):int(p,16) for i,p in diagnostic['nonzero_slots']}
assert sorted(slots)==list(range(50))
assert all(slots[i+1]-slots[i]==0x1E0 for i in range(49))

class ResidueHarness(ChainHarness):
    last=None
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.table_reads=[];self.table_writes=[]
        for i,pointer in slots.items():
            # These raw addresses from the diagnostic are not mapped into the VM.
            assert not BASE<=pointer<BASE+0x3000000 and not MEM<=pointer<MEM+0x200000
            self.putq(self.cache+0x20+i*8,pointer)
        self.before_table=bytes(self.u.mem_read(self.cache+0x20,120*8))
        self.u.hook_add(UC_HOOK_MEM_READ,self.table_watch)
        self.u.hook_add(UC_HOOK_MEM_WRITE,self.table_watch)
        ResidueHarness.last=self
    def table_watch(self,u,access,address,size,value,data):
        if address<self.cache+0x3E0 and address+size>self.cache+0x20:
            row={'phase':self.phase,'rva':hex(self.reg(UC_X86_REG_RIP)-BASE),
                 'offset':hex(address-self.cache),'size':size,'value':hex(value)}
            # UC_MEM_READ=16 / UC_MEM_WRITE=17; hook constants differ.
            (self.table_reads if access==16 else self.table_writes).append(row)
    def assert_zeroed(self):
        assert bytes(self.u.mem_read(self.cache+0x20,120*8))==bytes(120*8)
        assert not self.table_reads and len(self.table_writes)==120
        assert all(row['value']=='0x0' and row['size']==8 for row in self.table_writes)
        assert sorted(int(row['offset'],16) for row in self.table_writes)==list(range(0x20,0x3E0,8))
    def table_summary(self):
        return {'initial_nonzero_entries':50,'initial_stride':'0x1e0',
          'initial_destinations_unmapped':True,'native_table_reads':self.table_reads,
          'native_table_write_count':len(self.table_writes),
          'native_table_write_pcs':sorted(set(row['rva'] for row in self.table_writes))}

def main():
    rows=[]
    for capacity in (0,64):
        for success in (0,1):
            h=ResidueHarness(1,0,capacity)
            original=h.run_chain(success);h.assert_zeroed()
            rows.append({'case':'complete_native_state_chain','result':'PASS','initial_pending_capacity':capacity,
              'synthetic_worker_success':bool(success),'original_user_retained':original['original_user_retained'],
              'final_user_phase':original['after']['user_phase'],**h.table_summary()})
    # Reuse the real worker path with only its harness class changed in this VM.
    # The source of the existing mode report and its older evidence are untouched.
    previous=mode_cases.ChainHarness
    try:
        mode_cases.ChainHarness=ResidueHarness
        for success in (True,False):
            original=mode_cases.worker_case(1,0,success);h=ResidueHarness.last
            assert not h.table_reads and not h.table_writes
            assert bytes(h.u.mem_read(h.cache+0x20,120*8))==h.before_table
            rows.append({'case':'native_worker_explicit_name_path','result':'PASS','storage_ok':success,
              'open':original['opens'],'table_unchanged':True,**h.table_summary(),
              'stubs':original['boundaries']})
    finally:mode_cases.ChainHarness=previous
    for entry in (0x835DD0,0x836DF0,0x837E80):
        h=ResidueHarness(1,0);h.phase='isolated_native_clear'
        h.put32(h.cache+0x3EC,34)
        h.run(entry,args=(h.cache+0x10 if entry==0x837E80 else h.cache,))
        if entry==0x837E80:
            assert bytes(h.u.mem_read(h.cache+0x20,120*8))==h.before_table
            assert not h.table_reads and not h.table_writes
        else:h.assert_zeroed()
        assert h.readq(h.cache_head)==h.cache_head and h.readq(h.cache_head+8)==h.cache_head
        assert h.readq(h.cache+0x18)==0
        assert h.read32(h.cache+0x3EC)==(0xFFFFFFFF if entry==0x835DD0 else 34)
        assert h.read32(h.cache+8)==1 and h.read32(h.cache+0x3F0)==0
        rows.append({'case':'isolated_native_clear','entry':hex(entry),'result':'PASS',**h.table_summary()})
    functions=(0x835DD0,0x836DF0,0x837E80)
    report={'schema':'san14.checkpoint-push-cache-residue.v1','result':'PASS','cases':rows,
      'source_diagnostic':DIAGNOSTIC.name,'source_diagnostic_sha256':hashlib.sha256(DIAGNOSTIC.read_bytes()).hexdigest(),
      'game_access':False,'save_files_written':False,'old_evidence_modified':False,
      'native_clear_instructions':{hex(at):[f'{i.address:#x}: {i.mnemonic} {i.op_str}' for i in mode_cases.function(at)] for at in functions},
      'conclusion':['The native ownership clear traverses only cache+10 head.next, not the 120-pointer array. An empty self-linked list bypasses all node destructor/free calls.',
        '836DF0 directly stores zero into all120 pointer slots without reading their old values or pointed objects.50 nonzero pointers to entirely unmapped destinations safely clear under actual native instructions.',
        'The executed explicit-filename worker path neither reads nor writes the120 table entries and opens mppush01.s14 in write mode with requested slot=-1.',
        'A requirement that all120 entries start empty is unnecessarily strict for this demonstrated menu residue. Keep a valid self-linked empty list, pending=-1 and the pinned mode/secondary.',
        'For this controlled profile, permit the exact captured pre-submit table pattern (slots0..49 at1e0 stride,50..119 zero), pin the values through submission, and expect all120 zero after native completion; do not edit the live table to satisfy a guard.'],
      'limits':['The actual current table entries were not dereferenced. Their owner/type/lifetime is not identified by this diagnostic. Native clear does not need their pointee ownership when its owned linked list is empty.',
        'Full world serialization, sidecars and peripheral UI/OS/storage callees are explicit stubs in the worker/control-chain harness. Therefore this is not a blanket proof that every transitive game function can never read the table.',
        'The four complete state-chain cases use synthetic worker publication; the two separate worker cases run actual worker/preparation/open/finalizer control with the listed stubs.',
        'No root candidate source/guard was changed by this audit; any broader relaxation beyond the captured menu residue requires its own review.']}
    path=ROOT/('checkpoint_push_native_chain_cache_residue_'+datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.json')
    with path.open('x',encoding='utf-8') as f:json.dump(report,f,ensure_ascii=False,indent=2)
    print(json.dumps({'result':'PASS','cases':len(rows),'path':str(path),'game_access':False}))

if __name__=='__main__':main()
