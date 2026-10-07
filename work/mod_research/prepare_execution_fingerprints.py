from pathlib import Path
ROOT=Path(__file__).resolve().parent
RANGES=((0x1D6DA0,0x1D7059),(0x22600,0x22680),(0x83E0,0x8447),
        (0x171B0,0x172CA),(0x16B90,0x16C45),(0x16D10,0x16E1A),
        (0x209A00,0x209A2B),(0x20C2E0,0x20C2E4),(0x211540,0x211590),
        (0x18ECF30,0x18ECF34),(0x18ECFE0,0x18ECFE4))
def main():
    image=(ROOT/'game-runtime-image.bin').read_bytes()
    rows=['#pragma once','struct ExecutionFingerprint { uintptr_t rva; size_t size; unsigned char bytes[256]; };',
          'static const ExecutionFingerprint EXECUTION_FINGERPRINTS[]={']
    for a,z in RANGES:
        for b in range(a,z,256):
            data=image[b:min(b+256,z)]
            rows.append('    {0x%X,%d,{%s}},'%(b,len(data),','.join('0x%02X'%v for v in data)))
    rows.append('};')
    (ROOT/'reward_execution_fingerprints.h').write_text('\n'.join(rows)+'\n')
if __name__=='__main__':main()
