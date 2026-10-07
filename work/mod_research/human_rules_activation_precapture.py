"""Read-only current-game inputs for the new room rule activation candidate."""
from pathlib import Path
from datetime import datetime
import json,struct,sys
P=Path(__file__).resolve().parent
sys.path[:0]=[str(P),str(P/'python_deps'),str(P.parents[1]/'outputs/san14-link')]
from battle_observer import BattleObserver
from checkpoint_push_start import process_birth
from startup_identity_reader import capture_startup_context
from human_rules_stage_live_start import profiles,GAME_SHA

def main():
 reader=BattleObserver()
 try:
  assert reader.sha256==GAME_SHA
  m=reader.memory;b=m.base
  def val(address,fmt):return struct.unpack(fmt,m.read(address,struct.calcsize(fmt)))[0]
  root=val(b+0x1FCA1E0,'<Q');world=val(root+0x85130,'<Q')
  before=capture_startup_context(reader)
  data={'pid':reader.pid,'birth':process_birth(reader),'image':b,'root':root,'world':world,
   'context':before,'income_singleton_guard':val(b+0x1FD0C5C,'<i'),
   'income_key5':val(b+0x18EB628,'<I'),'world_option8':(val(world+0x16A8,'<I')>>8)&1,
   'forces':{},'six_sources_original':all(m.read(b+rva,len(raw))==raw for rva,_,raw in profiles()),
   'game_writes':0,'native_calls':0,'rules_enabled':False}
  for force in (12,2):
   f=val(root+0xDCA0+force*8,'<Q')
   data['forces'][str(force)]={'address':f,'first48':m.read(f,48).hex(),'ruler':val(f+0x10,'<H')}
  after=capture_startup_context(reader)
  data['same_context_after']=before==after
  assert data['same_context_after'] and val(b+0x1FCA1E0,'<Q')==root and val(root+0x85130,'<Q')==world
  out=P/'human_rules_activation_precaptures'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');out.mkdir(parents=True)
  (out/'result.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
  print(json.dumps({'result':'PASS_READ_ONLY','path':str(out/'result.json'),'pid':reader.pid,'key5':data['income_key5'],'option8':data['world_option8'],'sources_original':data['six_sources_original'],'native_calls':0},ensure_ascii=False))
 finally:reader.close()
if __name__=='__main__':main()
