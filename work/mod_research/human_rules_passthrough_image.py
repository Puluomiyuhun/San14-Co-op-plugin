"""Build an owned no-entry/no-import PE fixture from archived code, never a game executable."""
import hashlib,struct
from pathlib import Path
IMAGE_SHA='5a2ef730f2a075f23cd8880c5acb1f83c99c03810ea23c0663ae9f05b6c04268'
PDATA_RVA=0x2180000
FUNCTIONS=[(0xC6580,0xC65E3,0x1778018),(0xC65F0,0xC6653,0x1778018),
    (0xC6660,0xC669C,0x17AB260),(0xC66A0,0xC6703,0x1778018),
    (0x2110B0,0x211109,0x17ab260),(0x28DAA1,0x28DAAF,0x2170000),(0x28DE6D,0x28DE7B,0x2170000)]
def build(archive,folder):
    image=bytearray(Path(archive).read_bytes())
    if hashlib.sha256(image).hexdigest()!=IMAGE_SHA:raise ValueError('archived image changed')
    pdata=b''.join(struct.pack('<III',*f) for f in FUNCTIONS);image[PDATA_RVA:PDATA_RVA+len(pdata)]=pdata
    headers=bytearray(0x200);headers[:2]=b'MZ';struct.pack_into('<I',headers,0x3c,0x80)
    marker=b'OWNED HUMAN RULES PROFILE FIXTURE';headers[0x40:0x40+len(marker)]=marker
    headers[0x80:0x84]=b'PE\0\0';struct.pack_into('<HHIIIHH',headers,0x84,0x8664,1,0,0,0,240,0x2023)
    op=0x98;struct.pack_into('<H',headers,op,0x20b)
    struct.pack_into('<I',headers,op+4,len(image)-0x1000)
    struct.pack_into('<I',headers,op+20,0x1000);struct.pack_into('<Q',headers,op+24,0x10000000)
    struct.pack_into('<II',headers,op+32,0x1000,0x200)
    struct.pack_into('<HH',headers,op+40,6,0);struct.pack_into('<HH',headers,op+48,6,0)
    struct.pack_into('<II',headers,op+56,len(image),0x200)
    struct.pack_into('<HH',headers,op+68,3,0x100)
    struct.pack_into('<QQQQ',headers,op+72,0x100000,0x1000,0x100000,0x1000)
    struct.pack_into('<I',headers,op+108,16);struct.pack_into('<II',headers,op+112+3*8,PDATA_RVA,len(pdata))
    section=op+240;headers[section:section+8]=b'.owned\0\0'
    struct.pack_into('<IIIIIIHHI',headers,section+8,len(image)-0x1000,0x1000,len(image)-0x1000,0x200,0,0,0,0,0x60000020)
    target=Path(folder)/'owned_rules_image.dll';target.write_bytes(headers+image[0x1000:])
    digest=hashlib.sha256(target.read_bytes()).digest()
    (Path(folder)/'human_rules_stage_fixture_image_profile.h').write_text('#pragma once\ninline constexpr unsigned char FixtureImageSha[]={'+','.join(str(v) for v in digest)+'};\n',encoding='ascii')
    return target
