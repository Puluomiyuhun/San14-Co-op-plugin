"""Verify archived bytes and native start/payload/join instruction relationships.
Offline only. Installed build is separately hashed by the live observer.
"""
from pathlib import Path
import hashlib
import json
import re
import sys
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'python_deps'))
import capstone
import checkpoint_title_join_live as live


def verify():
    image=(ROOT/'game-runtime-image.bin').read_bytes()
    digest=hashlib.sha256(image).hexdigest()
    assert digest==live.prior.offline.IMAGE_SHA
    decoder=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_64)
    records=[]
    for address,byte_text in re.findall(r'\{0x([A-Fa-f0-9]+),\{([^}]+)\}\}',(ROOT/'checkpoint_title_join_live_anchors.h').read_text()):
        rva=int(address,16);raw=bytes(int(x,16) for x in byte_text.split(','))
        assert len(raw)==32 and image[rva:rva+32]==raw
        decoded=list(decoder.disasm(raw,rva))
        records.append(dict(rva=hex(rva),bytes=raw.hex(),instructions=[f'{i.address:x}: {i.mnemonic} {i.op_str}' for i in decoded]))
    assert [int(r['rva'],16) for r in records]==list(live.ANCHORS)
    expected={0x834D98:('call','qword ptr [rax + 0x10]'),0x834D9B:('mov','rcx, qword ptr [rbx + 8]'),
              0x4DA2E3:('call','0x833cb0'),0x4DA2EF:('call','0x834b60'),
              0x4BEEB1:('call','0x833cb0'),0x4BEEBD:('call','0x834b60'),
              0x4BEF1A:('call','0x833cb0'),0x4BEF26:('call','0x834b60'),
              0x4AAF5F:('call','0x834bc0'),0x4AAF84:('call','0x834bc0'),
              0x4F7074:('call','0x834bc0'),0x4FABC0:('jmp','qword ptr [rcx + 8]')}
    for rva,ins in expected.items():
        actual=next(decoder.disasm(image[rva:rva+15],rva));assert (actual.mnemonic,actual.op_str)==ins,(hex(rva),actual.mnemonic,actual.op_str)
    decoder.detail=True
    lea=next(decoder.disasm(image[0x4BEEFE:0x4BEF0D],0x4BEEFE))
    assert lea.mnemonic=='lea' and lea.reg_name(lea.operands[0].reg)=='rdx'
    assert lea.address+lea.size+lea.operands[1].mem.disp==0x466600
    return dict(result='PASS',game_access=False,archive_sha256=digest,exe_sha256=live.EXE_SHA,
                title590_payload_rva='0x466600',roles=[dict(role=i,control_offset=hex(off),payload=hex(live.PAYLOADS[i]),start_return=hex(live.STARTS[i]),join_return=hex(live.JOINS[i])) for i,off in enumerate((0x478,0x520,0x590))],
                anchors=records,limitations=['Static relationships only; live per-run observation still required.','Retained V2 slot can forward original; actual payload entry and full runner return remain separately sampled.'])


if __name__=='__main__':
    result=verify();(ROOT/'checkpoint_title_join_live_profile_result.json').write_text(json.dumps(result,indent=2),encoding='utf8');print(json.dumps(dict(result=result['result'],anchors=len(result['anchors']),game_access=False)))
