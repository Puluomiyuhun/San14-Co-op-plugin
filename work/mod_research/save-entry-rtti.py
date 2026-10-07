from pathlib import Path
import sys,struct,json
P=Path(__file__).resolve().parent
sys.path.insert(0,str(P))
import disasm_chained as d
base=struct.unpack_from('<Q',d.image,0x12cd408)[0]-0x3f69f0
print('base',hex(base))
needle=b'.?AVCSaveState@@\0'
pos=d.image.find(needle);td=pos-16
print('type',hex(pos), 'td',hex(td))
cols=[];x=0
while True:
 x=d.image.find(struct.pack('<I',td),x)
 if x<0:break
 start=x-12
 if start>=0 and struct.unpack_from('<I',d.image,start)[0]==1 and struct.unpack_from('<I',d.image,start+20)[0]==start:cols.append(start)
 x+=1
for col in cols:
 needle=struct.pack('<Q',base+col); x=0
 while True:
  x=d.image.find(needle,x)
  if x<0:break
  vt=x+8
  print('col/vt',hex(col),hex(vt))
  for i in range(16):print(hex(i*8),hex(struct.unpack_from('<Q',d.image,vt+8*i)[0]-base))
  x+=1
