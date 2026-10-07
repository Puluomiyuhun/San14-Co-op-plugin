"""Exact bodies for the reviewed query dependency graph, including leaf methods."""
from pathlib import Path
ROOT=Path(__file__).resolve().parent
RANGES=((0x1D4270,0x1D4326),(0x2F2BB0,0x2F2BD4),(0x210F50,0x210F61),
        (0x210A20,0x210A89),(0x2970C0,0x29712C),(0x208F80,0x209063),
        (0x208770,0x2087E5),(0x20F830,0x20F92C),(0x2119F0,0x211A2D),
        (0x211420,0x211448),(0x20A660,0x20A6D5),(0x211610,0x211659),
        (0x20B610,0x20B63A),(0x1D4330,0x1D4335),(0x1D4340,0x1D4357),
        (0x2115C0,0x2115CA),(0x20BA50,0x20BA96),(0x20BAA0,0x20BAD9),
        (0x2F0190,0x2F01AC))

def main():
    image=(ROOT/'game-runtime-image.bin').read_bytes()
    rows=['#pragma once','struct EligibilityFingerprint { uintptr_t rva; size_t size; unsigned char bytes[256]; };',
          'static const EligibilityFingerprint ELIGIBILITY_FINGERPRINTS[]={']
    for a,z in RANGES:
        assert 0<z-a<=256
        rows.append('    {0x%X,%d,{%s}},'%(a,z-a,','.join('0x%02X'%b for b in image[a:z])))
    rows.append('};')
    (ROOT/'reward_eligibility_fingerprints.h').write_text('\n'.join(rows)+'\n',encoding='ascii')

if __name__=='__main__':main()
