"""Read current game once, then run native commands in independent local copies.

This is a paired-process feasibility experiment, not two actual SAN14 clients.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
ROOT=Path(__file__).resolve().parent
OUT=ROOT.parents[1]/'outputs'/'san14-link'
sys.path.insert(0,str(OUT))
from battle_observer import BattleObserver
from domestic_reader import DomesticDecoder
from reward_eligibility import pool_values
from authority_reward import capture_context,make_command,validate_reward
from run_second_force_reward import capture as world_capture
from make_identity_pair_fixture import RANGES

def save(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def capture_input(reader,path):
    d=DomesticDecoder(reader);b=d.memory.base;root=d.root
    world=d.ptr(root+0x85130);data=bytearray(struct.pack('<I',0x1414FACE)+d.read(world,0x1700))
    assert d.uint(world+0x3A,1)==12 and d.uint(world+0xBC,1)==255
    image=(ROOT/'game-runtime-image.bin').read_bytes()
    for _,a,z in RANGES:assert d.read(b+a,z-a)==image[a:z],f'Native code changed at {a:#x}'
    ids=[0,97,101,264,411,666,759,904,952]
    data.extend(struct.pack('<I',len(ids)))
    for identity in ids:
        p=d.ptr(root+0x148+identity*8);d.require_type(p,'CPersonData')
        assert d.ptr(d.ptr(p)+0x18)==b+0x2119F0
        data.extend(struct.pack('<I',identity)+d.read(p,0x200))
    for table,stride,name in [(0xDCA0,0x1D0,'CForceData'),(0xDE40,0x28,'CDistrictData'),
                              (0xDAA8,0x168,'CCityData'),(0x6D808,0x20,'CObjectData')]:
        first=d.ptr(root+table)
        for identity in range(52):
            p=d.ptr(root+table+identity*8);assert p==first+identity*stride
            d.require_type(p,name);data.extend(d.read(p,stride))
    first=d.ptr(root+0x77BB8)
    for identity in range(13):
        p=d.ptr(root+0x77BB8+identity*8);assert p==first+identity*0xB8
        d.require_type(p,'CRankData');assert d.ptr(d.ptr(p)+0x18)==b+0x211B80
        data.extend(d.read(p,0xB8))
    assert d.uint(world+0x40)==1 and d.ptr(d.ptr(world)+0x18)==b+0x665CD0
    targets={0x129FD10:{0x18:0x211540,0x80:0x209A00,0x90:0x20C2E0,0x98:0x21D7C0,0xB0:0x20A8E0,0xB8:0x20BDF0},
             0x129FE58:{0x18:0x211710,0x60:0x20B610},0x129FEC8:{0x18:0x211610},
             0x129FDF0:{0x18:0x2119C0},0x129FB70:{8:0x2F6330}}
    for vt,entries in targets.items():
        for offset,target in entries.items():assert d.ptr(b+vt+offset)==b+target
    district0=d.ptr(root+0xDE40)
    ordered=pool_values(d,root+0xC8,0x123F3F8,0x201D3A0,0x14000,51,8)
    order=[(p-district0)//0x28 for p in ordered]
    assert all(1<=i<=51 and d.ptr(root+0xDE40+i*8)==p for i,p in zip(order,ordered))
    data.extend(struct.pack('<I',len(order))+struct.pack('<%dI'%len(order),*order))
    source=json.loads((ROOT/'identity-pair-native-source.json').read_text(encoding='utf-8'))
    for addr in source['data_slots']:
        rva=int(addr,16)
        if 0x18EC000<=rva<0x18ED000 or rva==0x201E830:
            assert d.read(b+rva,8)==image[rva:rva+8],f'Native capacity/reward constant changed at {rva:#x}'
    d.verify_stable();path.write_bytes(data)
    return {'persons':ids,'ordered_districts':order,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}

def launch(input_path,folder,viewer,mode,sequence):
    output=folder/f'{mode}-{sequence}-{viewer}.bin'
    process=subprocess.run([str(ROOT/'identity_pair_fixture.exe'),str(input_path),str(viewer),mode,sequence,str(output)],
                           capture_output=True,text=True,timeout=20,creationflags=subprocess.CREATE_NO_WINDOW)
    assert process.returncode==0,(viewer,mode,sequence,process.returncode,process.stdout,process.stderr)
    result=json.loads(process.stdout);assert result['result']=='PASS'
    save(output.with_suffix('.json'),result)
    return result,output.read_bytes()

def main():
    folder=ROOT/'identity-pair-traces'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');folder.mkdir(parents=True)
    reader=BattleObserver()
    try:
        before=world_capture(reader);assert before==world_capture(reader)
        contexts={}
        for force,district,ids in [(12,11,[97,759,904]),(2,2,[101,264,411])]:
            context=capture_context(reader,force);command=make_command(context,district,ids)
            validate_reward(command,context,force);contexts[str(force)]={'context':context,'command':command}
        save(folder/'authority-inputs.json',contexts)
        input_path=folder/'input.bin';input_meta=capture_input(reader,input_path)
        pairs=[]
        for mode,sequence in [('normal','B'),('normal','A'),('normal','AB'),('normal','BA'),('normal','BB'),
                              ('counter','B'),('native_init','B'),('native_init','A')]:
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures=[pool.submit(launch,input_path,folder,v,mode,sequence) for v in (12,2)]
                results=[f.result() for f in futures]
            (a,ab),(b,bb)=results;assert a['pid']!=b['pid']
            assert a['viewer']==12 and a['main_district']==11 and b['viewer']==2 and b['main_district']==2
            assert len(ab)==len(bb)
            differences=[i for i,(x,y) in enumerate(zip(ab,bb)) if x!=y]
            if mode=='normal':assert not differences,(sequence,differences)
            elif mode=='counter':
                assert differences==[0x80],differences
                assert a['counter_delta']==0 and b['counter_delta']==1
            else:
                assert differences==[0x165D],differences
                assert a['initializer_changed_world_bytes']==0 and b['initializer_changed_world_bytes']==2
                assert a['rank_derived_field']==2 and b['rank_derived_field']==1
            ac,bc=sequence.count('A'),sequence.count('B')
            for row in [a,b]:
                assert row['gold_A']==83308-ac*300 and row['gold_B']==20804-bc*300
                assert row['actions_A']==18-ac and row['actions_B']==10-bc
                assert row['native_reward_calls']==len(sequence) and row['policy_effect_stub_calls']==len(sequence)*2
            if sequence=='B':
                assert a['loyalty_B']==b['loyalty_B']==[97,95,100]
                assert a['loyalty_A']==b['loyalty_A']==[90,94,92]
                assert a['flags_B']==b['flags_B']==[130,130,130]
            pairs.append({'mode':mode,'commands':sequence,'client_A_copy':a,'client_B_copy':b,
                          'normalized_sample_equal':not differences,'different_offsets':differences,
                          'normalized_sample_bytes':len(ab),'sample_sha256_A':hashlib.sha256(ab).hexdigest(),
                          'sample_sha256_B':hashlib.sha256(bb).hexdigest()})
        assert before==world_capture(reader),'Live game changed during isolated experiments'
        result={'schema':'san14.fixed-local-identity-feasibility.v1','created':datetime.now().astimezone().isoformat(),
                'result':'BOUNDED_REWARD_PASS_IDENTITY_DEPENDENT_PATHS_REQUIRE_ADAPTATION','directory':str(folder),
                'input':input_meta,'pairs':pairs,'source':json.loads((ROOT/'identity-pair-native-source.json').read_text(encoding='utf-8')),
                'game_memory_writes':0,'game_native_command_calls':0,'actual_SAN14_clients_sampled':1,
                'actual_SAN14_clients_executing_test_commands':0,
                'isolated_fixture_processes':len(pairs)*2,'native_reward_execution_location':'fixture processes only',
                'sampled_live_records_unchanged':len(before['records']),'known_live_rng_and_pools_unchanged':True,
                'scope':'Same captured data in independent processes with fixed viewers 12/2, native identity getters, initializer and reward body. The normal cases set only local identity in the copy. Native-initializer cases additionally retain and expose the rank-derived field difference. One policy-effect boundary stub is used only in the fourth capacity output; money/loyalty writes and selected identity branches use copied native code. Original policy-query side effects, UI rendering, native menu creation, input capture, execution legality, actual game replication and turn progression are not tested.',
                'counterexamples':['With synthetic context mode 0, the reward local-context counter world+0x80 changes only on the owning viewer. Meaning is not assumed.',
                                   'When reached, the special combat-pair filter rejects a controlled gate target only for the local attacker. This does not establish that the outer filter is enabled in the current scenario or explain original run A.']}
        save(folder/'result.json',result);save(ROOT/'identity-pair-results.json',result)
        print(json.dumps({k:v for k,v in result.items() if k not in ('pairs','source')},ensure_ascii=True,indent=2))
    finally:reader.close()

if __name__=='__main__':main()
