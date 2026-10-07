"""Assert preview/commit boundaries and gaps in the saved economic pipeline.

Static instruction evidence and a read-only planning sample only. This is not
an exhaustive control-flow proof or a replay of the complete city calculation.
"""
import hashlib
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'python_deps'))
import capstone

def main():
    image=(ROOT/'game-runtime-image.bin').read_bytes();md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_64)
    expected={
        0xC11DD:'call 0x20d3b0',0xC11EE:'call 0x20b290',0xC1200:'call 0x20d3b0',0xC120E:'call 0x20b290',
        0xC1216:'sub eax, dword ptr [rsp + 0x50]',0xC121A:'add eax, eax',
        0xC121C:'sub eax, dword ptr [rsp + 0x68]',0xC1220:'add eax, dword ptr [rbp + 0x40]',
        0xC1223:'mov dword ptr [r14 + 0xa0], eax',0xC123A:'mov dword ptr [r14 + 0xa4], eax',
        0x20B2BA:'mov r9d, 1',0x20B2D5:'call 0x28cc70',0x28CC70:'mov dword ptr [rsp + 0x20], r9d',
        0x28CD58:'mov word ptr [rax + 0x4a], di',0x28CD61:'mov word ptr [rax + 0x4c], di',
        0x28CD6A:'mov word ptr [rax + 0x4e], di',0x28CD73:'mov word ptr [rax + 0x50], di',
        0x28CDB5:'call 0x28db70',0x28CDD5:'mov word ptr [rcx + 0x4a], dx',
        0x28CDF4:'call 0x28d750',0x28CE14:'mov word ptr [rcx + 0x4c], dx',
        0x28D28F:'cmp dword ptr [rbp + 0x6f], 0',0x28D293:'jne 0x28d2d4',
        0x28D2D0:'mov word ptr [rcx + 0x52], ax',0x28D2F7:'mov word ptr [rax + 0x4e], cx',
        0x28D401:'cmp dword ptr [rbp + 0x6f], 0',0x28D405:'jne 0x28d441',
        0x28D43D:'mov word ptr [rdi + 0x52], ax',0x28D45D:'mov word ptr [rdi + 0x4e], ax',
        0x28D4BF:'cmp dword ptr [rbp + 0x6f], 0',0x28D4C3:'jne 0x28d6c9',
        0x28D56F:'call qword ptr [rax + 0x98]',0x28D5B4:'call qword ptr [rax + 0xa8]',
        0x28D5FF:'mov dword ptr [rsi + 0x3c], ebx',
        0x20D443:'movzx ecx, byte ptr [rdi + 0x198]',0x20D6F9:'movzx edx, byte ptr [rdi + 0x1f8]',
        0x20D49E:'mov rcx, rdi',0x20D4A1:'call 0x88350',0x20D5E2:'call 0x1d2dc0',
        0x28DDDA:'call 0x284a20',0x28D9C0:'call 0x284a20',
        0x28D12C:'call 0x3cb260',0x28D9F9:'call 0x2f1e80',
    }
    anchors=[]
    for at,text in expected.items():
        ins=next(md.disasm(image[at:at+15],at));actual=ins.mnemonic+' '+ins.op_str
        assert actual==text,(hex(at),actual,text)
        anchors.append({'rva':hex(at),'instruction':actual,'bytes':ins.bytes.hex()})
    load=lambda p:json.loads(p.read_text(encoding='utf-8'))
    sample=load(ROOT/'economy-extended-after-restoration.json');tests=load(ROOT/'economy-reader-tests.json')
    assert tests['result']=='PASS'
    recovery=load(ROOT/'startup-switch-recovery.json');assert recovery['result']=='RESTORED_ZHANG_LU_CHECKPOINT_SAMPLE'
    areas=sample['areas'];order=sample['native_area_order']
    coverage={'area_slots':len(areas),'ordered_active_areas':len(order),'assigned_officer_records':len(sample['assigned_officers']),
              'center_hex_records':len(sample['center_hexes']),
              'active_areas_with_nonzero_4a_50':sum(any(areas[str(i)]['derived_4a_50_raw']) for i in order),
              'includes_previously_unsampled_person_offsets':['0x198','0x1f8'],
              'complete_economy_inputs':False}
    report={'schema':'san14.economy-pipeline-audit.v1','result':'PREVIEW_SIDE_EFFECTS_AND_EXTENDED_COVERAGE_IDENTIFIED',
            'anchors':anchors,'coverage':coverage,'reader_tests':tests,'recovery':recovery,
            'city_field_formula':'For components 0/1: field[A0/A4] = 2*(income(mode0)-cost(mode0)) + income(mode1)-cost(mode1). Retains native integer ordering; labels/time horizon not verified.',
            'preview_mode_evidence':{'wrapper_rva':'0x20b290','core_rva':'0x28cc70','incoming_r9':1,
                'saved_flag':'[entry_rsp+0x20] == [frame_rbp+0x6f]',
                'does_not_imply_read_only':True,
                'unguarded_derived_writes':['area+0x4a','area+0x4c','area+0x4e','area+0x50'],
                'guarded_population_write_sites':['0x28d2d0','0x28d43d'],
                'commit_block_skip':['0x28d4bf','0x28d4c3','0x28d6c9'],
                'scope':'These writes and gates are statically confirmed. Other callees and exceptional paths are not exhaustively audited.'},
            'next_missing_inputs':sample['missing_dependencies'],
            'full_city_delta_replay_verified':False,'native_preview_called_in_game':False,
            'new_live_hooks_installed':False,'game_data_writes_by_this_work':0,
            'source_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in
                             (ROOT/'game-runtime-image.bin',ROOT/'economy-extended-after-restoration.json')},
            'scope':__doc__.strip()}
    (ROOT/'economy-pipeline-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'result':report['result'],'static_anchors':len(anchors),'coverage':coverage,
                      'reader_tests':len(tests['cases']),'game_data_writes':0},ensure_ascii=False))

if __name__=='__main__':main()
