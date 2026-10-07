"""Archived native load-menu chain, initial cache mode 0 or 1; no game access."""
from datetime import datetime
import hashlib,json
from pathlib import Path
from checkpoint_load_mode_native_chain import LoadModeHarness,ROOT,BASE
from unicorn import UC_HOOK_MEM_READ,UC_HOOK_MEM_WRITE
from unicorn.x86_const import UC_X86_REG_RIP

def main():
    cases=[]
    for mode in (0,1):
        for capacity in (0,64):
            for present in (False,True):
                h=LoadModeHarness(capacity,present)
                h.put32(h.cache+8,mode);observed=[]
                def trace(uc,access,address,size,value,data):
                    if address<=h.cache+8<address+size:
                        observed.append(dict(phase=h.phase,access=access,rva=hex(uc.reg_read(UC_X86_REG_RIP)-BASE),
                            size=size,value=value if access==17 else None))
                h.u.hook_add(UC_HOOK_MEM_READ|UC_HOOK_MEM_WRITE,trace)
                row=h.run_chain('method')
                assert row['result']=='PASS' and row['mode_after']==0
                cases.append(dict(initial_mode=mode,initial_capacity=capacity,fake_file_present=present,
                    result=row['result'],mode_accesses=observed,original_user_same_object=row['original_user_same_object'],
                    world_prefix_date_rng_unchanged=row['world_prefix_date_rng_unchanged'],
                    required_native_entries=row['required_native_entries'],instructions=row['instructions']))
    result=dict(schema='san14.load-initial-cache-mode-audit.v1',result='PASS',cases=cases,game_access=False,
        native_image_sha256=hashlib.sha256((ROOT/'game-runtime-image.bin').read_bytes()).hexdigest(),
        source_sha256={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in
            ('checkpoint_load_initial_mode_audit.py','checkpoint_load_mode_native_chain.py','checkpoint_push_native_chain.py')},
        conclusion='Actual archived load-menu push/init/cancel/pop supports initial cache mode0 and mode1, including empty queue capacity0. Pin actual initial mode per attempt; do not rewrite native mode to satisfy guards.',
        limits=['Unicorn isolated memory only; UI/storage/allocator primitives retain the explicit doubles documented by LoadModeHarness.',
                'No native world load or actual OS window. Mode equality is one boundary guard, never proof of idle input or authorization.',
                'Queue capacity0 may become a new native allocation; no pre-existing fake queue span may be supplied.'])
    path=ROOT/('checkpoint_load_initial_mode_audit_'+datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.json')
    with path.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
    print(json.dumps(dict(result='PASS',cases=len(cases),path=str(path))))

if __name__=='__main__':main()
