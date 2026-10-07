"""Read-only breakdown of activation admission; no native calls or writes."""
from pathlib import Path
import json,struct,sys,re
P=Path(__file__).resolve().parent;sys.path.insert(0,str(P))
import human_rules_activation_live_session_v2 as x
r=x.BattleObserver();m=r.memory;b=m.base
checks={};fields={}
def v(a,f='<Q'):return struct.unpack(f,m.read(a,struct.calcsize(f)))[0]
def check(n,a,w,f='<Q'):
 z=v(a,f);checks[n]={'actual':z,'expected':w,'pass':z==w};return z
try:
 root=v(b+0x1FCA1E0);world=v(root+0x85130);manager=b+0x19E7310
 check('manager.stack_count',manager+0x10,5);check('manager.pending',manager+0x30,0)
 stack=v(manager+0x20);states=[v(stack+i*8)for i in range(5)];fields['states']=states
 vt=[0,0x12F22D8,0x12CC9B8,0x12CD400,0x12CC4A8]
 for i,s in enumerate(states):
  fields['name'+str(i)]=m.read(s+0x70,40).split(b'\0')[0].decode()
  check('state'+str(i)+'.68',s+0x68,0,'<I')
  if i:check('state'+str(i)+'.vt',s,b+vt[i])
  if i!=4:check('state'+str(i)+'.50',s+0x50,0)
 u=states[4];g=states[2];toolbar=v(u+0x478);panel=v(g+0x480);control=v(u+0x618)
 fields.update(toolbar=toolbar,panel=panel,control=control)
 check('toolbar.88',toolbar+0x88,-1,'<i');check('game.47c',g+0x47C,0,'<I');check('panel.1b0',panel+0x1B0,0,'<I')
 for o in (0x4A8,0x4B0,0x4B8):check('user.'+hex(o),u+o,0)
 special=v(b+0x201EC70)
 if special:check('special',special,0,'<I')
 check('modal',b+0x1A38EC8+0x28,0,'<I');check('native_input',b+0x19E7510+0x13C,1,'<I')
 fields.update(capacity=v(manager+0x38),data=v(manager+0x40))
 check('root.vt',root,b+0x12AA6B0);check('world.vt',world,b+0x12AA638)
 check('user.phase',u+0x470,2,'<I');check('year',world+0x34,203,'<H');check('month',world+0x36,8,'<B');check('day',world+0x37,11,'<B');check('viewer',world+0x3A,12,'<B');check('world.165d',world+0x165D,1,'<B');check('world.40',world+0x40,1,'<I')
 cache=v(b+0x2025318);fields['cache']=cache
 for off,w,f in ((0x3EC,-1,'<i'),(0x3F0,0,'<I'),(8,0,'<I')):check('cache.'+hex(off),cache+off,w,f)
 text=(P/'human_rules_activation_profile.h').read_text();arr={name:bytes(int(z.strip(),16)for z in vals.split(','))for name,vals in re.findall(r'constexpr unsigned char (a\d+)\[\]=\{([^}]+)\}',text)}
 for rva,name in re.findall(r'\{(0x[0-9a-f]+),(a\d+),sizeof',text):
  raw=m.read(b+int(rva,16),len(arr[name]));checks['anchor.'+rva]={'pass':raw==arr[name],'actual':raw.hex(),'expected':arr[name].hex()}
 result={'fields':fields,'checks':checks,'all_pass':all(z['pass']for z in checks.values()),'game_writes':0,'native_calls':0}
 out=P/'human_rules_activation_live_runs/20261008-000026-982440/admission-readonly.json';out.write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({'path':str(out),'failures':{k:z for k,z in checks.items()if not z['pass']},'fields':fields}))
finally:r.close()
