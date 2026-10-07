"""Generate locked-build native function prefixes from the offline runtime image."""
from pathlib import Path
ROOT=Path(__file__).resolve().parent
RVAS=(0x22600,0x171B0,0x83E0,0x16B90,0x16D10,0x17040,0x3F9B00)

def main():
    image=(ROOT/'game-runtime-image.bin').read_bytes()
    rows=['#pragma once', 'struct RewardFingerprint { uintptr_t rva; unsigned char bytes[32]; };',
          'static const RewardFingerprint REWARD_FINGERPRINTS[]={']
    for rva in RVAS:
        prefix=image[rva:rva+32]
        assert len(prefix)==32
        rows.append('    {0x%X,{%s}},' % (rva,','.join('0x%02X'%b for b in prefix)))
    rows.append('};')
    (ROOT/'reward_probe_fingerprints.h').write_text('\n'.join(rows)+'\n',encoding='ascii')

if __name__=='__main__': main()
