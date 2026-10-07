"""Version-locked offline save/load audit; optional read-only live inventory.

This does not call the game, save, load, install hooks, or certify full state
coverage. The inventory samples representative RTTI, not record contents.
"""
from pathlib import Path
from bisect import bisect_right
import argparse, hashlib, json, struct, sys

HERE = Path(__file__).resolve().parent
OUT = HERE.parents[1] / 'outputs' / 'san14-link'
sys.path[:0] = [str(HERE/'python_deps'), str(OUT)]
saved_args = sys.argv[:]
sys.argv = sys.argv[:1]
import disasm_chained as d
sys.argv = saved_args
from game_reader import GameReader, DATA_POINTER_RVA, SUPPORTED_SHA256

IMAGE_SHA = '5a2ef730f2a075f23cd8880c5acb1f83c99c03810ea23c0663ae9f05b6c04268'
SAVE34_SHA = 'afd4c6c5f8a30f659ac523b85f522b02b2c03536ed5e55736677ca1927827d95'
SAVE34 = Path(r'C:\Program Files (x86)\Steam\userdata\391007908\872410\remote\svdexSC34.s14')
PLANNING = ['CRootState','CMotorGameState','CGameState','CStrategyState','CUserStrategyState']


def sha(b): return hashlib.sha256(b).hexdigest()
def load(p): return json.loads(p.read_text(encoding='utf-8'))
def write(p, data): p.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def function(at):
    e = d.entries[bisect_right(d.starts, at)-1]
    assert e[0] <= at < e[1]
    return [i for a,z,_ in sorted(set(d.groups[d.primary(e)])) for i in d.decoder.disasm(d.image[a:z], a)]


def one(at): return next(d.decoder.disasm(d.image[at:at+15], at))


def audit():
    assert sha(d.image) == IMAGE_SHA, 'Unrecognized captured image'
    expected = {
        0x508CE4:'call 0x2ee740', 0x508CE9:'test rax, rax',
        0x508CEC:'je 0x508d02', 0x508CF8:'call 0x2fce40',
        0x508CFD:'test eax, eax', 0x508CFF:'sete bl',
        0x508D1C:'mov dword ptr [rip + 0x1b15f0a], ebx',
        0x2EE866:'call 0x2f7a10', 0x2EE8A3:'jns 0x2ee8c8',
        0x2F7B38:'call 0x2f7b50', 0x2F7C28:'call 0x2e7d30',
        0x2F7959:'call 0x2e7d30',
        0x2FCE81:'call 0x3a6a10', 0x2FCE8A:'mov dword ptr [rbx + 0x24], 0xfffffed4',
        0x2FCEEB:'call 0x3a55d0',
        0x2FCF36:'mov eax, edi',
        0x3A6AB2:'call qword ptr [rax]', 0x3A6AD9:'test dil, dil',
        0x3A6B0E:'call qword ptr [rax + 0x58]',
        0x3A6B1C:'call qword ptr [rax + 0x68]',
        0x2E7DA8:'call 0x1d7740', 0x1D7875:'call qword ptr [rax + 0x28]',
        0x2E82EE:'call qword ptr [r8 + 8]', 0x2E835B:'call qword ptr [rax + 0x28]',
        0x2F9A24:'call 0x3aa390', 0x2F9A6D:'call 0x3aa3e0',
        0x2EE647:'call 0x2f76c0', 0x2EE69D:'call 0x2f3410',
        0x2EE6A5:'call 0x2eae80', 0x4DA3B9:'call 0x2fc850',
    }
    anchors=[]
    for at,wanted in expected.items():
        i=one(at);actual=i.mnemonic+' '+i.op_str
        assert actual==wanted,(hex(at),actual,wanted)
        anchors.append({'rva':at,'instruction':actual,'bytes':i.bytes.hex()})
    arrays=[];off=None
    for i in function(0x2E7D30):
        if i.mnemonic=='add' and i.op_str.startswith('r9, 0x'):
            off=i.operands[1].imm
        if off is not None and i.mnemonic=='call' and i.operands[0].type==d.capstone.x86.X86_OP_IMM:
            wrapper=i.operands[0].imm
            wi=function(wrapper)
            inner=next(x.operands[0].imm for x in wi if x.mnemonic=='call')
            ii=function(inner)
            counts=[x.operands[1].imm for x in ii if x.mnemonic=='mov' and x.op_str.startswith('dword ptr [rsp + 0x38],')]
            assert len(counts)==1 and 0<counts[0]<50000
            assert sum(x.mnemonic=='call' and x.op_str=='qword ptr [rax + 0x28]' for x in ii)==2
            assert any(x.mnemonic=='lea' and x.op_str=='rdi, [rdi + 8]' for x in ii)
            arrays.append({'root_offset':off,'count':counts[0],'wrapper_rva':wrapper,
                           'loop_rva':inner,'callsite_rva':i.address})
            off=None
    assert len(arrays)==39 and sum(x['count'] for x in arrays)==60070
    assert len(set(x['root_offset'] for x in arrays))==39
    assert all(a['root_offset']+8*a['count']<=b['root_offset'] for a,b in zip(arrays,arrays[1:]))
    gates=[x.operands[1].imm for x in function(0x2E7D30)
           if x.mnemonic=='cmp' and x.op_str.startswith('dword ptr [rbx + 0x88],')]
    assert gates==[0xF,0x46,0x47,0x4B]
    assert all(0x5C>x for x in gates)
    assert one(0x2F7A95).op_str=='edx, 0x5c'
    assert d.image[0x217CF0:0x217CF9].hex()=='33c03942500f94c0c3'
    traces=[]
    for rel,key in [('camera-near-rng-k2/rng-writes-unwound.json',None),('pending-run-g/pending-analysis.json','save_markers')]:
        rows=load(HERE/'lockstep-traces'/rel)
        if key: rows=rows[key]
        row=next(x for x in rows if 'CSaveState' in x.get('states',[]))
        pcs=[f['pc_rva'] for f in row['unwind']['frames']]
        required=['0x2f9a72','0x2e835e','0x2f7c2d','0x2f7b3d','0x2ee86b','0x508ce9']
        assert [x for x in pcs if x in required]==required
        traces.append({'file':rel,'sha256':sha((HERE/'lockstep-traces'/rel).read_bytes()),
                       'states':row['states'],'thread':row['thread'],'call_stack':pcs})
    return {'schema':'san14.native-checkpoint-audit.v1','game_sha256':SUPPORTED_SHA256,
        'captured_image_sha256':IMAGE_SHA,'result':'STATIC_SAVE_LOAD_PATHS_AND_EXISTING_SAVE_STACKS_VERIFIED',
        'format_version':0x5C,'anchors':anchors,'arrays':arrays,'fixed_pointer_slots':60070,
        'version_thresholds':gates,'historical_save_calls':traces,
        'shared_dispatcher_rva':0x2E7D30,'dynamic_registry_root_offset':0x85128,
        'world_root_offset':0x85130,'world_serializer_rva':0x2F9610,
        'status_only_serializer_rva':0x217CF0,
        'save_observation_points':[
            {'rva':0x508CA0,'meaning':'worker_entry'},
            {'rva':0x508CE9,'meaning':'prepared_archive_or_null; NOT storage completion'},
            {'rva':0x508CFD,'meaning':'storage finalizer returned; EAX zero means this worker will report success'},
            {'rva':0x508D22,'meaning':'worker result flag published at 0x201ec2c; may still be in CSaveState'}],
        'candidate_export_requirements':['fresh adapter save request and expected slot/path binding',
            'commands locked and authoritative events resolved at native planning boundary',
            'matching worker instance completes, finalizer result is zero',
            'save state leaves, world identity/date/input cut still match',
            'completed file read, size/hash, original slots protected; no reliance on stale success flag'],
        'native_full_coverage_verified':False,'automatic_export_implemented':False,
        'automatic_guest_reload_implemented':False,'game_memory_writes':0,
        'limits':['A dispatch entry does not prove all fields are serialized.',
            'Some table methods only report stream status and write no record payload.',
            'Dynamic registry, additional manager serializer, post-load reconstruction and sidecar coverage remain to audit.',
            'Archive success is not a proof of hardware power-loss durability or Steam Cloud completion.',
            'No current native save/load operation was requested by this tool.']}


def live_inventory(report):
    save_before=sha(SAVE34.read_bytes())
    r=GameReader()
    try:
        m=r.memory;before=r.snapshot()
        assert before['state_stack']==PLANNING,'Requires idle planning map'
        for a in report['anchors']:
            expected=bytes.fromhex(a['bytes'])
            assert m.read(m.base+a['rva'],len(expected))==expected,'Live code differs'
        root=r.pointer(m.base+DATA_POINTER_RVA);r.require_type(root,'CSan14Data')
        type_cache={}
        def describe(p):
            vt=r.pointer(p)
            assert m.base<=vt<m.base+m.image_size
            if vt not in type_cache:
                loc=r.pointer(vt-8)
                assert m.base<=loc<m.base+m.image_size-24
                sig,_,_,td,_,own=struct.unpack('<6I',m.read(loc,24))
                assert sig==1 and own==loc-m.base and td<m.image_size-144
                name=m.read(m.base+td+16,128).split(b'\0')[0].decode('ascii')
                assert name.startswith('.?AV') and name.endswith('@@')
                method=struct.unpack('<Q',m.read(vt+0x28,8))[0]
                assert m.base<=method<m.base+m.image_size
                type_cache[vt]={'type':name[4:-2],'vtable_rva':vt-m.base,'serializer_rva':method-m.base,
                               'status_only':method-m.base==0x217CF0}
            return type_cache[vt]
        tables=[];samples=[]
        for row in report['arrays']:
            address=root+row['root_offset'];raw=m.read(address,row['count']*8)
            pointers=struct.unpack('<'+'Q'*row['count'],raw)
            assert all(0x10000<=p<0x7FFFFFFFFFFF and p%8==0 for p in pointers)
            indices=sorted({0,row['count']//2,row['count']-1})
            samples.append(row|{'representatives':[{'index':i,**describe(pointers[i])} for i in indices]})
            tables.append((address,raw))
        registry=r.pointer(root+0x85128);world=r.pointer(root+0x85130)
        world_type=describe(world);assert world_type['type']=='CWorldData'
        assert world_type['serializer_rva']==0x2F9610
        # The registry is NOT assumed to have an RTTI vtable at byte zero.
        registry_head=m.read(registry,0x30)
        assert all(m.read(a,len(raw))==raw for a,raw in tables),'Pointer tables changed'
        assert r.pointer(m.base+DATA_POINTER_RVA)==root
        assert r.pointer(root+0x85128)==registry and m.read(registry,0x30)==registry_head
        assert r.pointer(root+0x85130)==world
        after=r.snapshot();assert before==after,'Planning location changed'
        save_after=sha(SAVE34.read_bytes());assert save_before==save_after==SAVE34_SHA
        result={'schema':'san14.native-checkpoint-inventory.v1','result':'READ_ONLY_POINTER_TABLE_AND_REPRESENTATIVE_RTTI_CHECKS_PASS',
            'before':before,'after':after,'arrays':samples,'world':world_type,
            'fixed_arrays':len(samples),'pointer_slots':sum(x['count'] for x in samples),
            'representative_objects':sum(len(x['representatives']) for x in samples),
            'status_only_array_samples':sum(all(v['status_only'] for v in x['representatives']) for x in samples),
            'same_pointer_tables_two_reads':True,'save34_sha256':save_after,
            'registry_layout':'non-RTTI manager; only header/pointer stability observed',
            'game_memory_writes':0,'game_calls':0,'game_debugger_attached_by_tool':False,
            'complete_world_verified':False,
            'limits':['60070 means table slots, not 60070 active or fully saved objects.',
                'Only three representative objects per table have their RTTI/method checked.',
                'Matching pointers/date does not prove all pointed-to payloads remained unchanged.',
                'Save file was not changed or reloaded; coverage is structural, not a full checkpoint roundtrip.']}
        return result
    finally:r.close()


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--live',action='store_true');args=ap.parse_args()
    report=audit();write(HERE/'native-checkpoint-audit.json',report)
    summary={'static_anchors':len(report['anchors']),'fixed_arrays':len(report['arrays']),
             'fixed_pointer_slots':report['fixed_pointer_slots'],'historical_save_stacks':len(report['historical_save_calls'])}
    if args.live:
        result=live_inventory(report);write(HERE/'native-checkpoint-inventory.json',result)
        summary['live']={k:result[k] for k in ('result','representative_objects','status_only_array_samples','complete_world_verified')}
    print(json.dumps(summary,ensure_ascii=True))


if __name__=='__main__':main()
