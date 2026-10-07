"""Correlate saved startup differences with asserted native arithmetic paths.

Offline only. The exact 18 integer deltas have not been replayed through the
native economic functions. Do not whitelist the fields as local UI state.
"""
import hashlib
import json
import struct
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'python_deps'))
import capstone

def main():
    load=lambda p:json.loads(p.read_text(encoding='utf-8'))
    result=load(ROOT/'startup-switch-live-result.json'); folder=Path(result['directory'])
    before=load(folder/'before.json');after=load(folder/'after.json')
    image=(ROOT/'game-runtime-image.bin').read_bytes()
    md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_64)
    expected={
        0xC119B:'call 0x208d70',0xC11DD:'call 0x20d3b0',0xC11EE:'call 0x20b290',
        0xC1200:'call 0x20d3b0',0xC120E:'call 0x20b290',
        0xC1223:'mov dword ptr [r14 + 0xa0], eax',0xC123A:'mov dword ptr [r14 + 0xa4], eax',
        0x20B2D5:'call 0x28cc70',0x20D3C2:'call 0x2ab640',
        0x28CDB5:'call 0x28db70',0x28CDF4:'call 0x28d750',
        0x28DE69:'call 0x20a470',0x28DE71:'call 0x2110b0',0x28DE78:'je 0x28de92',
        0x28DA9D:'call 0x20a470',0x28DAA5:'call 0x2110b0',0x28DAAC:'je 0x28dac6',
        0x2110CB:'call 0x2f21e0',0x2110E8:'cmp edi, eax',
        0xA7274:'mov eax, dword ptr [r14 + 0xa0]',0xA7289:'mov ecx, dword ptr [r14 + 0xa4]',
    }
    anchors=[]
    for at,text in expected.items():
        ins=next(md.disasm(image[at:at+15],at)); actual=ins.mnemonic+' '+ins.op_str
        assert actual==text,(hex(at),actual,text)
        anchors.append({'rva':hex(at),'instruction':actual,'bytes':ins.bytes.hex()})
    inventory_equal=True;changes=[]
    for i in range(1,52):
        a=bytes.fromhex(before['records'][f'city:{i}']);b=bytes.fromhex(after['records'][f'city:{i}'])
        inventory_equal &= a[0x24:0x30]==b[0x24:0x30]
        av=struct.unpack_from('<ii',a,0x90);bv=struct.unpack_from('<ii',b,0x90)
        if av==bv:continue
        district=a[0x20];force=bytes.fromhex(before['records'][f'district:{district}'])[0]
        assert district==b[0x20]
        changes.append({'city_id':i,'city_name':a[2:10].decode('utf-16-le').rstrip('\0'),
                        'owner_force_id':force,'field_a0':[av[0],bv[0]],'field_a4':[av[1],bv[1]],
                        'gold_food_garrison':list(struct.unpack_from('<III',b,0x24))})
    assert len(changes)==9 and {v['owner_force_id'] for v in changes}=={2,12}
    assert inventory_equal
    assert {row['object'] for row in result['comparison']['other_record_changes']}=={f"city:{x['city_id']}" for x in changes}
    assert all(all(0xA0<=int(o,16)<0xA8 for o in row['offsets']) for row in result['comparison']['other_record_changes'])
    report={'schema':'san14.city-identity-effects-audit.v1','result':'LOCAL_IDENTITY_DEPENDENT_CALCULATION_PATH_FOUND',
            'live_run':str(folder),'game_access':False,'native_anchors':anchors,'city_changes':changes,
            'all_51_cities_gold_food_garrison_equal':inventory_equal,
            'source_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in
                             (folder/'before.json',folder/'after.json',ROOT/'game-runtime-image.bin')},
            'findings':[
                'City +A0/+A4 are recomputed as component[0/1](mode1) plus twice component[0/1](mode0), with a second pair of component outputs subtracted. They are not the stored gold/food inventory fields.',
                'The upstream 28DB70 and 28D750 routines branch on 2110B0, which compares the receiver force ID with the current native local-player force. The two arms apply separate percentage calculations.',
                'The observed changed city set consists exactly of the sampled cities owned by force 2 and force 12. This agrees with the local-identity dependency, but does not by itself prove that every numerical delta is fully explained.',
                'A7160 reads the sign of these fields and branches while using city resource accessors. They cannot be classified as harmless display-only values from this evidence.',
            ],'exact_delta_replay_verified':False,'ui_labels_verified':False,'all_economic_consumers_audited':False,
            'allow_ignoring_fields_in_world_comparison':False,'native_economy_patch_installed':False,
            'required_design':'Use the same room human-force set for audited economic/simulation rules on both replicas; keep the local viewer identity for native menus. Classify call sites, do not globally replace the local-player predicate.',
            'scope':__doc__.strip()}
    (ROOT/'city-identity-effects-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'result':report['result'],'anchors':len(anchors),'changed_cities':len(changes),
                      'current_resource_inventory_equal':inventory_equal,'exact_delta_replay_verified':False},ensure_ascii=False))

if __name__=='__main__':main()
