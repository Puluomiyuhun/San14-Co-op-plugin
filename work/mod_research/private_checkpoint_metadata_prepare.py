"""Offline exact-build native ABI/profile and remaining integration contract."""
from pathlib import Path
from datetime import datetime
from bisect import bisect_right
import hashlib,json,sys
ROOT=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT),str(ROOT/'python_deps')];sys.argv=sys.argv[:1]
import disasm_chained as d
IMAGE_SHA='5a2ef730f2a075f23cd8880c5acb1f83c99c03810ea23c0663ae9f05b6c04268'
assert hashlib.sha256(d.image).hexdigest()==IMAGE_SHA
functions={0x2E32A0:'header constructor',0x3A5120:'auxiliary stream owner constructor',0x3A56A0:'auxiliary owner destructor',
 0x3A4FC0:'native stream constructor',0x3A55D0:'native stream destructor',0x3A90C0:'native stream open',
 0x3A9330:'native stream read',0x3A97F0:'set stream format version',0x2FAAD0:'native header parser',0x3A6340:'close native stream',
 0x511D0:'native short string assign',0x50D20:'native short string destructor',0x2E0E80:'native list-node copy constructor',
 0x2FD150:'native node allocation and initial links',0x2E2A40:'native header/filename copy',0x3A58B0:'native heap free',
 0x2F1650:'native slot basename formatter',0x836710:'bounded native slot getter',0x836DF0:'native whole-cache clear',0x837E80:'native list cleanup'}
guards=[]
for rva,label in functions.items():
    e=d.entries[bisect_right(d.starts,rva)-1]
    if e[0]<=rva<e[1]:
        root=d.primary(e)
        for a,z,_ in sorted(set(d.groups[root]+[root])):
            guards.append({'rva':hex(a),'end':hex(z),'role':label,'sha256':hashlib.sha256(d.image[a:z]).hexdigest(),'bytes_hex':d.image[a:z].hex()})
    else:
        instructions=[]
        for ins in d.decoder.disasm(d.image[rva:rva+128],rva):
            instructions.append(ins)
            if ins.mnemonic=='ret':break
        if rva==0x836710:end=0x836721
        else:
            assert instructions[-1].mnemonic=='ret',hex(rva)
            end=instructions[-1].address+instructions[-1].size
        guards.append({'rva':hex(rva),'end':hex(end),'role':label,'sha256':hashlib.sha256(d.image[rva:end]).hexdigest(),'bytes_hex':d.image[rva:end].hex()})
for a,z,label in ((0x8370F9,0x837137,'scanner node/list ownership registration'),(0x837315,0x83731D,'scanner slot pointer registration'),
                  (0x508B6B,0x508B8C,'worker explicit filename/slot forwarding'),(0x2F7750,0x2F77CF,'archive explicit basename/read mode'),
                  (0x4BDDB0,0x4BDDD3,'positive title slot required for default identity restore')):
    guards.append({'rva':hex(a),'end':hex(z),'role':label,'sha256':hashlib.sha256(d.image[a:z]).hexdigest(),'bytes_hex':d.image[a:z].hex()})
shadow=json.loads((ROOT/'private_checkpoint_metadata_shadow.json').read_text())
fixtures=json.loads((ROOT/'private_checkpoint_metadata_fixture_results.json').read_text())
report={
 'schema':'san14.private-checkpoint-metadata-preparation.v1','created':datetime.now().astimezone().isoformat(),
 'status':'CORE_AND_OFFLINE_PROOFS_READY_LIVE_ADAPTER_BLOCKED','eligible_live_execution':False,
 'game_exe_sha256':'42d53bb42c033c6027b6da75e8077f4170f4d684abb0f57483a661225d052025','captured_image_sha256':IMAGE_SHA,
 'guard_ranges':guards,'fixed_test_contract':{'basename':'mpckpt01.s14','world_date':[203,8,11],'force':12,'ruler':666,'allowed_slot_range':[63,109],
 'slot_rule':'Must be null in the table, absent in the native formatter-selected local file path AND native Steam FileExists. Do not assume a cleared cache means a free physical slot.',
 'once_scope':'private_checkpoint_metadata_mpckpt01_once.json','default_execute':False,'writes_pending':False,'loads_world':False},
 'ownership':{'temporary_header_size':'0x150','native_node_size':'0x160','node_payload_offset':'0x10','filename_in_payload':'0x128',
  'construction':'Native 2E32A0 then native stream header parser 2FAAD0; filename assigned by 511D0; 2E0E80 uses 2FD150/2E2A40 to allocate a game-owned copy.',
  'before_commit':'Pinned file hash, native/local slot absence, strict planning guard, unchanged validated list graph, private filename and parsed header snapshot must all pass.',
  'commit':'Replicate scanner stores: count+1, head.prev=node, old_tail.next=node, slot=payload. No pending request. Original nodes remain owned by native list.',
  'unlinked_cleanup':'Temporary header/string/streams belong to core. Unregistered native node is destroyed via native string destructor plus native heap free.',
  'registered_cleanup':'Never free the committed node in core. Native 836DF0->837E80 owns eventual removal. Uncertain partial commit cannot be automatically rolled back or retried.'},
 'proofs':{'copied_native_load_abi_cases':14,'copied_native_metadata_cases':len(shadow['cases']),'compiled_core_fixture_cases':len(fixtures['cases']),
  'native_header_bytes_consumed_from_backup':shadow['cases'][0]['bytes_consumed'],'fixture_binary_sha256':fixtures['binary_sha256'],
  'native_parser_scope':'2FAAD0 and its field helpers execute; only primitive stream Read replaced by source bytes. Existing34 backup is a test input, not a private save or live attempt.',
  'compiled_core_scope':fixtures['scope']},
 'remaining_gates':[
  'No live adapter/injector/scheduler hook is present. Need exact-build function/VT guards and a proven main UserStrategy Update caller/thread lifecycle before integrating the core.',
  'Need the independently exported mpckpt01.s14 manifest, exact new SHA/size, and matching offline parsed-header snapshot. Existing34 backup fixture is not eligible input for a live operation.',
  'Local pinned-file SHA does not prove bytes served by native Steam storage. Exact parsed-header snapshot equality narrows header ambiguity only; full native file identity must be bound before final B load.',
  'Need live stream open/close/parser and native allocator behavior under the integration guard; arbitrary native SEH/C++ exceptions and concurrent container consumers are not proven by these fixtures.',
  'Cache invalidation/refresh between metadata registration and eventual request must be detected. A future load requester must revalidate the registered node, positive slot and explicit filename before pending is set; never fall back to34.',
  'Need full native load completion observer with semantic indices checked only after native worker rebuilding, then B identity restoration at the established title-to-strategy boundary.',
  'Current core only supports fixed203-08-11 ZhangLu test input. It is not a generic every-turn checkpoint implementation.'
 ],
 'rejected_design':'pending34 followed by delayed debugger filename substitution is fail-open and is not implemented.',
 'game_access':False,'old_auto_reload_once_reused':False,
}
(ROOT/'private_checkpoint_metadata_preparation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'status':report['status'],'ranges':len(guards),'metadata_cases':len(shadow['cases']),'core_cases':len(fixtures['cases']),'eligible_live_execution':False,'game_access':False}))
