"""Hand-constructed stack layouts test metadata unwind independently of the game."""
import struct
from unwind_rng_stack import Unwinder

BASE=0x180000000
image=bytearray(0x4000)

def info(address, slots, flags=0, frame=0, chain=None):
    image[address:address+4]=bytes((1|(flags<<3),16,len(slots),frame))
    for i,slot in enumerate(slots):
        image[address+4+2*i:address+6+2*i]=bytes(slot)
    if chain:
        struct.pack_into('<III',image,address+4+2*((len(slots)+1)&~1),*chain)

# push rbx; sub rsp,32; save rsi at fixed rsp+16.
info(0x1000,[(12,0x64),(2,0),(5,0x32),(1,0x30)])
# Large 0x200 allocation; saved RBP in incoming stack frame.
info(0x1100,[(12,0x54),(0x41,0),(7,0x01),(0x40,0)])
# Chained fragment additionally saved RSI at fixed rsp+8.
info(0x1200,[(4,0x64),(1,0)],flags=4,chain=(0x100,0x180,0x1000))
# push rbp; sub rsp,32; lea rbp,[rsp+16]; saved rsi at rsp+8.
info(0x1300,[(16,0x64),(1,0),(12,3),(5,0x32),(1,0x50)],frame=0x15)
pdata=b''.join(struct.pack('<III',*e) for e in [(0x100,0x180,0x1000),(0x200,0x280,0x1100),(0x300,0x380,0x1200),(0x400,0x480,0x1300)])
u=Unwinder(image,pdata,BASE)

def run(pc,rsp,stack,**regs):
    return u.unwind_one({'rip':BASE+pc,'rsp':rsp,**regs},stack.__getitem__)

r,slot=run(0x120,0x10000,{0x10010:0x111,0x10020:0x222,0x10028:BASE+0x220})
assert slot==0x10028 and r['rsp']==0x10030 and r['rsi']==0x111 and r['rbx']==0x222 and r['rip']==BASE+0x220
r,slot=run(0x220,0x20000,{0x20208:0x333,0x20200:BASE+0x120})
assert slot==0x20200 and r['rbp']==0x333
r,slot=run(0x320,0x10000,{0x10008:0x444,0x10010:0x111,0x10020:0x222,0x10028:BASE+0x220})
assert slot==0x10028 and r['rsi']==0x111 and r['rbx']==0x222
# Dynamic stack usage: fixed rsp is 0x30000, current rsp is lower.
r,slot=run(0x420,0x2ffe0,{0x30008:0x555,0x30020:0x666,0x30028:BASE+0x120},rbp=0x30010)
assert slot==0x30028 and r['rsi']==0x555 and r['rbp']==0x666
# Only push has executed at prolog offset 1.
r,slot=run(0x101,0x40000,{0x40000:0x777,0x40008:BASE+0x220})
assert slot==0x40008 and r['rbx']==0x777
# Independently verified stackless RNG leaf.
r,slot=run(0x3aa805,0x50000,{0x50000:BASE+0x120})
assert slot==0x50000 and r['rsp']==0x50008
print('PASS: ordinary frame, large allocation, chained info, dynamic frame, partial prolog, RNG leaf')
