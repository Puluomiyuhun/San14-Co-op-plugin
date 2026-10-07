"""Offline evidence for a possible producer of army+48. No game access."""
import json, struct
from pathlib import Path
import disasm_chained as d
import pefile
from capstone.x86 import X86_OP_MEM, X86_REG_RIP

ROOT = Path(__file__).resolve().parent
EXE = Path(r'C:\Program Files (x86)\Steam\steamapps\common\Romance_of_the_Three_Kingdoms_14\SAN14PK_SC.exe')
pe = pefile.PE(str(EXE), fast_load=True)
pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_IMPORT']])
imports = {i.address-pe.OPTIONAL_HEADER.ImageBase: i.name.decode() if i.name else str(i.ordinal)
           for dll in pe.DIRECTORY_ENTRY_IMPORT for i in dll.imports}

anchors = [0x16cbb7, 0x16cbcd, 0x16cbd6, 0x16cbdb, 0x16c2d0, 0x16c238,
    0x2cd509, 0x2cd52c, 0x2cd54e, 0x2a9d94, 0x2a9da4, 0x833d92,
    0x834b82, 0x834ba2, 0x834d98, 0x834dad, 0x834db4, 0x83a136, 0x83a1da]
instructions = []
for at in anchors:
    ins = next(d.decoder.disasm(d.image[at:at+15], at))
    row = {'rva': hex(at), 'instruction': ins.mnemonic+' '+ins.op_str, 'bytes': ins.bytes.hex()}
    if ins.operands and ins.operands[0].type == X86_OP_MEM and ins.operands[0].mem.base == X86_REG_RIP:
        target = ins.address + ins.size + ins.operands[0].mem.disp
        row['iat_rva'] = hex(target)
        row['import'] = imports.get(target)
    instructions.append(row)
name_rva = 0x16cbae+0x1122e2a
name_bytes = d.image[name_rva:name_rva+160].split(b'\0',1)[0]
# The runtime image has ASLR relocations applied; derive its recorded base from a known vtable entry.
base = struct.unpack_from('<Q', d.image, 0x12cc4a8+0x28)[0]-0x3f9b00
needle = struct.pack('<Q', base+0x3f8140)
hits=[]; start=0x1230000
while True:
    at=d.image.find(needle, start)
    if at<0:break
    hits.append(hex(at));start=at+1
report = {'candidate_path': ['0x3F8140 -> 0x16CB30',
    '0x16CB30 registers callback 0x16C2C0 through 0x833CB0 and starts work through 0x834B60',
    '0x16C2C0 -> 0x16C1A0 -> 0x2CD3E0 -> 0x1760E0 -> path[1] -> army+0x48'],
    'instructions': instructions, 'worker_label': {'rva': hex(name_rva), 'bytes': name_bytes.hex(),
        'ascii': name_bytes.decode('ascii', errors='replace')},
    'update_pointer_candidates': hits,
    'scope': 'Static callback registration, worker infrastructure and movement data flow. Does not identify the actual I2 writer or demonstrate a data race.',
    'i2_missing_observation': ['army+0x48 write PC and thread', 'worker_90 across the advance',
                               'worker launch and completion events', 'working army list membership at write']}
(ROOT/'movement-worker-static-evidence.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,ensure_ascii=True))
